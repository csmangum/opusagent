import argparse
import json
import os
from typing import Optional

import uvicorn
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
    def __init__(
        self, websocket: WebSocket, openai_ws: websockets.WebSocketClientProtocol
    ):
        self.websocket = websocket
        self.openai_ws = openai_ws
        self.stream_sid: Optional[str] = None
        self._closed = False

    async def close(self):
        """Safely close both WebSocket connections."""
        if not self._closed:
            self._closed = True
            try:
                if self.openai_ws.close_code is None:
                    await self.openai_ws.close()
            except Exception as e:
                print(f"Error closing OpenAI connection: {e}")
            try:
                await self.websocket.close()
            except Exception as e:
                print(f"Error closing telephony connection: {e}")

    async def receive_from_telephony(self):
        """Receive audio data from telephony and send it to the OpenAI Realtime API."""
        try:
            async for message in self.websocket.iter_text():
                if self._closed:
                    break

                data = json.loads(message)
                if (
                    data["event"] == "media"
                    and not self._closed
                    and self.openai_ws.close_code is None
                ):
                    # Use our Pydantic model for buffer append
                    audio_append = InputAudioBufferAppendEvent(
                        audio=data["media"]["payload"]
                    )
                    await self.openai_ws.send(audio_append.model_dump_json())
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
        """Receive events from the OpenAI Realtime API, send audio back to the telephony."""
        try:
            async for openai_message in self.openai_ws:
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
                            await self.websocket.send_json(audio_delta)
                            print("Sent audio delta to client")
                    except Exception as e:
                        print(f"Error processing audio data: {e}")
                        if not self._closed:
                            await self.close()
        except Exception as e:
            print(f"Error in send_to_telephony: {e}")
            await self.close()


async def send_initial_conversation_item(openai_ws):
    """Send initial conversation so AI talks first."""
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
    await openai_ws.send(initial_conversation.model_dump_json())

    # Create response using our model
    response_create = ResponseCreateEvent()
    await openai_ws.send(response_create.model_dump_json())


async def initialize_session(openai_ws):
    """Control initial session with OpenAI."""
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
    await openai_ws.send(session_update.model_dump_json())

    # Have the AI speak first
    await send_initial_conversation_item(openai_ws)
