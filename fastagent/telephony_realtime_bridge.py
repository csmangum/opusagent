"""Bridge between telephony WebSocket and OpenAI Realtime API for handling real-time audio communication.

This module provides functionality to bridge between a telephony WebSocket connection
and the OpenAI Realtime API, enabling real-time audio communication with AI agents.
It handles bidirectional audio streaming, session management, and event processing.
"""

import json
import os
from typing import Optional

import websockets
from dotenv import load_dotenv
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

# Import our model definitions
from fastagent.models.openai_api import (
    ConversationItemContentParam,
    ConversationItemCreateEvent,
    ConversationItemParam,
    InputAudioBufferAppendEvent,
    LogEventType,
    MessageRole,
    ResponseAudioDeltaEvent,
    ResponseCreateEvent,
    SessionConfig,
    SessionUpdateEvent,
)

load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PORT = int(os.getenv("PORT", 6060))
SYSTEM_MESSAGE = (
    "You are a banking agent. You are able to answer questions about the bank and the services they offer. "
    "You are also able to help with general banking questions and provide information about the bank's products and services."
)
VOICE = "alloy"
LOG_EVENT_TYPES = [
    LogEventType.ERROR,
    LogEventType.RESPONSE_CONTENT_DONE,
    LogEventType.RATE_LIMITS_UPDATED,
    LogEventType.RESPONSE_DONE,
    LogEventType.INPUT_AUDIO_BUFFER_COMMITTED,
    LogEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED,
    LogEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED,
    LogEventType.SESSION_CREATED,
]


class TelephonyRealtimeBridge:
    """Bridge class for handling bidirectional communication between telephony and OpenAI Realtime API.

    This class manages the WebSocket connections between a telephony system and the OpenAI Realtime API,
    handling audio streaming, session management, and event processing in both directions.

    Attributes:
        telephony_websocket (WebSocket): FastAPI WebSocket connection for telephony communication
        realtime_websocket (websockets.WebSocketClientProtocol): WebSocket connection to OpenAI Realtime API
        stream_sid (Optional[str]): Unique identifier for the current audio stream
        _closed (bool): Flag indicating whether the bridge connections are closed
    """

    def __init__(
        self,
        telephony_websocket: WebSocket,
        realtime_websocket: websockets.WebSocketClientProtocol,
    ):
        """Initialize the bridge with WebSocket connections.

        Args:
            telephony_websocket (WebSocket): FastAPI WebSocket connection for telephony
            realtime_websocket (websockets.WebSocketClientProtocol): WebSocket connection to OpenAI Realtime API
        """
        self.telephony_websocket = telephony_websocket
        self.realtime_websocket = realtime_websocket
        self.stream_sid: Optional[str] = None
        self._closed = False

    async def close(self):
        """Safely close both WebSocket connections.

        This method ensures both the telephony and OpenAI Realtime API WebSocket connections
        are properly closed, handling any exceptions that may occur during the process.
        """
        if not self._closed:
            self._closed = True
            try:
                if self.realtime_websocket.close_code is None:
                    await self.realtime_websocket.close()
            except Exception as e:
                print(f"Error closing OpenAI connection: {e}")
            try:
                await self.telephony_websocket.close()
            except Exception as e:
                print(f"Error closing telephony connection: {e}")

    async def receive_from_telephony(self):
        """Receive and process audio data from the telephony WebSocket.

        This method continuously listens for messages from the telephony WebSocket,
        processes audio data, and forwards it to the OpenAI Realtime API. It handles
        various events including media streaming, stream start/stop, and disconnections.

        The method processes the following events:
        - 'media': Audio data to be sent to OpenAI
        - 'start': Stream initialization with streamSid
        - 'stop': Stream termination

        Raises:
            WebSocketDisconnect: When the telephony client disconnects
            Exception: For any other errors during processing
        """
        try:
            async for message in self.telephony_websocket.iter_text():
                if self._closed:
                    break

                data = json.loads(message)
                if (
                    data["event"] == "media"
                    and not self._closed
                    and self.realtime_websocket.close_code is None
                ):
                    # Use our Pydantic model for buffer append
                    audio_append = InputAudioBufferAppendEvent(
                        audio=data["media"]["payload"]
                    )
                    await self.realtime_websocket.send(audio_append.model_dump_json())
                elif data["event"] == "start":
                    self.stream_sid = data["start"]["streamSid"]
                    print(f"Incoming stream has started {self.stream_sid}")
                elif data["event"] == "stop":
                    print(f"Stream {self.stream_sid} stopped")
                    await self.close()
                    break
        except WebSocketDisconnect:
            print("Client disconnected.")
            await self.close()
        except Exception as e:
            print(f"Error in receive_from_telephony: {e}")
            await self.close()

    async def send_to_telephony(self):
        """Process and forward events from OpenAI Realtime API to telephony.

        This method continuously listens for messages from the OpenAI Realtime API,
        processes various events including audio responses, and forwards them to the
        telephony WebSocket. It handles audio streaming, session updates, and logging.

        The method processes the following event types:
        - response.audio.delta: Audio data to be sent to telephony
        - session.updated: Session configuration updates
        - Various log events for monitoring and debugging

        Raises:
            Exception: For any errors during processing
        """
        try:
            async for openai_message in self.realtime_websocket:
                if self._closed:
                    break

                response_dict = json.loads(openai_message)
                response_type = response_dict["type"]

                if response_type in [event.value for event in LOG_EVENT_TYPES]:
                    print(f"Received event: {response_type}", response_dict)
                if response_type == "session.updated":
                    print("Session updated successfully:", response_dict)
                if response_type == "response.audio.delta" and "delta" in response_dict:
                    try:
                        # Parse using our model
                        response = ResponseAudioDeltaEvent(**response_dict)
                        if not self._closed and self.stream_sid:
                            audio_delta = {
                                "event": "media",
                                "streamSid": self.stream_sid,
                                "media": {"payload": response.delta},
                            }
                            await self.telephony_websocket.send_json(audio_delta)
                            print("Sent audio delta to client")
                    except Exception as e:
                        print(f"Error processing audio data: {e}")
                        if not self._closed:
                            await self.close()
        except Exception as e:
            print(f"Error in send_to_telephony: {e}")
            await self.close()


async def send_initial_conversation_item(realtime_websocket):
    """Send the initial conversation item to start the AI interaction.

    This function creates and sends the first conversation item to the OpenAI Realtime API,
    initiating the conversation with a greeting and request for an introduction and joke.

    Args:
        realtime_websocket (websockets.WebSocketClientProtocol): WebSocket connection to OpenAI Realtime API
    """
    # Create initial conversation item using our model
    initial_conversation = ConversationItemCreateEvent(
        item=ConversationItemParam(
            type="message",
            role=MessageRole.USER,
            content=[
                ConversationItemContentParam(
                    type="input_text",
                    text="Hello! Please introduce yourself and tell me a joke.",
                )
            ],
        )
    )

    print("Sending initial conversation item:", initial_conversation.model_dump_json())
    await realtime_websocket.send(initial_conversation.model_dump_json())

    # Create response using our model
    response_create = ResponseCreateEvent()
    await realtime_websocket.send(response_create.model_dump_json())


async def initialize_session(realtime_websocket):
    """Initialize the OpenAI Realtime API session with configuration.

    This function sets up the initial session configuration for the OpenAI Realtime API,
    including audio format settings, voice selection, system instructions, and other
    session parameters. It also triggers the initial conversation.

    Args:
        realtime_websocket (websockets.WebSocketClientProtocol): WebSocket connection to OpenAI Realtime API
    """
    # Use our SessionConfig and SessionUpdateEvent models
    session_config = SessionConfig(
        turn_detection={"type": "server_vad"},
        input_audio_format="pcm16",
        output_audio_format="pcm16",
        voice=VOICE,
        instructions=SYSTEM_MESSAGE,
        modalities=["text", "audio"],
        temperature=0.8,
    )

    session_update = SessionUpdateEvent(session=session_config)

    print("Sending session update:", session_update.model_dump_json())
    await realtime_websocket.send(session_update.model_dump_json())

    # Have the AI speak first
    await send_initial_conversation_item(realtime_websocket)
