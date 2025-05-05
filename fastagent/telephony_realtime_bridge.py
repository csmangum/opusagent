"""Bridge between telephony WebSocket and OpenAI Realtime API for handling real-time audio communication.

This module provides functionality to bridge between a telephony WebSocket connection
and the OpenAI Realtime API, enabling real-time audio communication with AI agents.
It handles bidirectional audio streaming, session management, and event processing.
"""

import json
import logging
import os
import uuid
from typing import Optional

import websockets
from dotenv import load_dotenv
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

# Configure logging
logger = logging.getLogger(__name__)

# Import AudioCodes models
from fastagent.models.audiocodes_api import (
    PlayStreamChunkMessage,
    PlayStreamStartMessage,
    PlayStreamStopMessage,
    SessionAcceptedResponse,
    UserStreamStartedResponse,
    UserStreamStoppedResponse,
)

# Import OpenAI Realtime API models
from fastagent.models.openai_api import (
    ConversationItemContentParam,
    ConversationItemCreateEvent,
    ConversationItemParam,
    InputAudioBufferAppendEvent,
    InputAudioBufferCommitEvent,
    LogEventType,
    MessageRole,
    ResponseAudioDeltaEvent,
    ResponseCreateEvent,
    ResponseCreateOptions,
    ResponseDoneEvent,
    ResponseTextDeltaEvent,
    ServerEventType,
    SessionConfig,
    SessionCreatedEvent,
    SessionUpdatedEvent,
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
        conversation_id (Optional[str]): Unique identifier for the current conversation
        media_format (Optional[str]): Audio format being used for the session
        active_stream_id (Optional[str]): Identifier for the current audio stream being played
        session_initialized (bool): Whether the OpenAI Realtime API session has been initialized
        speech_detected (bool): Whether speech is currently being detected
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
        self.conversation_id: Optional[str] = None
        self.media_format: Optional[str] = None
        self.active_stream_id: Optional[str] = None
        self.session_initialized = False
        self.speech_detected = False
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
        various events including session initiation, audio streaming, and disconnections.

        Supports the AudioCodes API format messages.

        Raises:
            WebSocketDisconnect: When the telephony client disconnects
            Exception: For any other errors during processing
        """
        try:
            async for message in self.telephony_websocket.iter_text():
                logger.info(f"Received telephony message: {message}")
                if self._closed:
                    break

                data = json.loads(message)
                msg_type = data["type"]

                # Handle session.initiate
                if msg_type == "session.initiate":
                    print(f"Session initiate received: {data}")
                    self.conversation_id = data.get("conversationId") or str(
                        uuid.uuid4()
                    )
                    print(f"Conversation started: {self.conversation_id}")

                    # Get media format
                    self.media_format = data.get(
                        "supportedMediaFormats", ["raw/lpcm16"]
                    )[0]

                    # Initialize the OpenAI Realtime API session and wait for SessionCreatedEvent
                    if not self.session_initialized:
                        await initialize_session(self.realtime_websocket)
                        # We'll wait for SessionCreatedEvent in receive_from_realtime before continuing
                        # Set a flag to indicate we're waiting for session acceptance
                        self.waiting_for_session_creation = True
                        self.session_initialized = True

                        # Don't send session.accepted here - it will be sent after SessionCreatedEvent is received

                # Handle userStream.start
                elif msg_type == "userStream.start":
                    print(f"User stream start received: {data}")
                    # Send userStream.started response
                    stream_started = UserStreamStartedResponse(
                        type="userStream.started", conversationId=self.conversation_id
                    )
                    await self.telephony_websocket.send_json(
                        stream_started.model_dump()
                    )
                    print(
                        f"User stream started for conversation: {self.conversation_id}"
                    )

                # Handle userStream.chunk (audio data)
                elif (
                    msg_type == "userStream.chunk"
                    and not self._closed
                    and self.realtime_websocket.close_code is None
                ):
                    # Use our Pydantic model for buffer append
                    audio_append = InputAudioBufferAppendEvent(
                        type="input_audio_buffer.append", audio=data["audioChunk"]
                    )
                    print(
                        f"Sending audio to realtime-websocket (size: {len(data['audioChunk'])} bytes)"
                    )
                    await self.realtime_websocket.send(audio_append.model_dump_json())

                # Handle userStream.stop
                elif msg_type == "userStream.stop":
                    print(
                        f"User stream stop received for conversation: {self.conversation_id}"
                    )
                    # Commit the audio buffer to signal end of speech
                    if not self._closed and self.realtime_websocket.close_code is None:
                        buffer_commit = InputAudioBufferCommitEvent(
                            type="input_audio_buffer.commit"
                        )
                        await self.realtime_websocket.send(
                            buffer_commit.model_dump_json()
                        )
                        print("Audio buffer committed")

                        # Send userStream.stopped response
                        stream_stopped = UserStreamStoppedResponse(
                            type="userStream.stopped",
                            conversationId=self.conversation_id,
                        )
                        await self.telephony_websocket.send_json(
                            stream_stopped.model_dump()
                        )

                # Handle session.end
                elif msg_type == "session.end":
                    print(
                        f"Session end received: {data.get('reason', 'No reason provided')}"
                    )
                    await self.close()
                    print(f"Telephony-Realtime bridge closed")
                    break

        except WebSocketDisconnect:
            print("Client disconnected.")
            await self.close()
        except Exception as e:
            print(f"Error in receive_from_telephony: {e}")
            await self.close()

    async def receive_from_realtime(self):
        """Receive and process events from the OpenAI Realtime API.

        This method continuously listens for messages from the OpenAI Realtime API,
        processes them, and forwards responses to the telephony WebSocket. It handles
        various events including audio responses, session updates, and transcripts.

        Supports sending responses in AudioCodes API format.

        Raises:
            Exception: For any errors during processing
        """
        try:
            async for openai_message in self.realtime_websocket:
                if self._closed:
                    break

                response_dict = json.loads(openai_message)
                response_type = response_dict["type"]
                print(f"Received OpenAI message type: {response_type}")

                # Handle log events
                if response_type in [event.value for event in LOG_EVENT_TYPES]:
                    print(f"Log event: {response_type}")

                    # Enhanced error logging
                    if response_type == "error":
                        error_code = response_dict.get("code", "unknown")
                        error_message = response_dict.get(
                            "message", "No message provided"
                        )
                        error_details = response_dict.get("details", {})
                        print(
                            f"ERROR DETAILS: code={error_code}, message='{error_message}'"
                        )
                        if error_details:
                            print(
                                f"ERROR ADDITIONAL DETAILS: {json.dumps(error_details)}"
                            )

                        # Log the full error response for debugging
                        print(f"FULL ERROR RESPONSE: {json.dumps(response_dict)}")

                # Handle session updates
                if response_type == ServerEventType.SESSION_UPDATED:
                    print("Session updated successfully")
                elif response_type == ServerEventType.SESSION_CREATED:
                    print("Session created successfully")
                    # Send session.accepted to telephony client now that OpenAI session is created
                    if (
                        hasattr(self, "waiting_for_session_creation")
                        and self.waiting_for_session_creation
                    ):
                        session_accepted = SessionAcceptedResponse(
                            type="session.accepted",
                            conversationId=self.conversation_id,
                            mediaFormat=self.media_format,
                        )
                        await self.telephony_websocket.send_json(
                            session_accepted.model_dump()
                        )
                        print(f"Session accepted with format: {self.media_format}")
                        self.waiting_for_session_creation = False

                # Handle speech detection events
                elif response_type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
                    print("Speech started detected")
                    self.speech_detected = True
                elif response_type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
                    print("Speech stopped detected")
                    self.speech_detected = False
                elif response_type == ServerEventType.INPUT_AUDIO_BUFFER_COMMITTED:
                    print("Audio buffer committed")

                # Handle response creation events
                elif response_type == ServerEventType.RESPONSE_CREATED:
                    print("Response creation started")

                # Handle audio response delta
                elif response_type == ServerEventType.RESPONSE_AUDIO_DELTA:
                    try:
                        # Parse using our updated model - note the "delta" field instead of "audio"
                        audio_delta = ResponseAudioDeltaEvent(**response_dict)

                        if not self._closed and self.conversation_id:
                            # Start a new audio stream if needed
                            if not self.active_stream_id:
                                # Start a new audio stream
                                self.active_stream_id = str(uuid.uuid4())
                                stream_start = PlayStreamStartMessage(
                                    type="playStream.start",
                                    conversationId=self.conversation_id,
                                    streamId=self.active_stream_id,
                                    mediaFormat=self.media_format or "raw/lpcm16",
                                )
                                await self.telephony_websocket.send_json(
                                    stream_start.model_dump()
                                )
                                print(f"Started play stream: {self.active_stream_id}")

                            # Send audio chunk with the delta value as the audio data
                            stream_chunk = PlayStreamChunkMessage(
                                type="playStream.chunk",
                                conversationId=self.conversation_id,
                                streamId=self.active_stream_id,
                                audioChunk=audio_delta.delta,  # Use delta field for audio data
                            )
                            await self.telephony_websocket.send_json(
                                stream_chunk.model_dump()
                            )
                            print(
                                f"Sent audio chunk to client (size: {len(audio_delta.delta)} bytes)"
                            )
                    except Exception as e:
                        print(f"Error processing audio data: {e}")
                        if not self._closed:
                            await self.close()

                # Handle audio response completion
                elif response_type == ServerEventType.RESPONSE_AUDIO_DONE:
                    print("Audio response completed")
                    # Stop the play stream
                    if self.active_stream_id and self.conversation_id:
                        stream_stop = PlayStreamStopMessage(
                            type="playStream.stop",
                            conversationId=self.conversation_id,
                            streamId=self.active_stream_id,
                        )
                        await self.telephony_websocket.send_json(
                            stream_stop.model_dump()
                        )
                        print(f"Stopped play stream: {self.active_stream_id}")
                        self.active_stream_id = None

                # Handle text and transcript events
                elif response_type == ServerEventType.RESPONSE_TEXT_DELTA:
                    text_delta = ResponseTextDeltaEvent(**response_dict)
                    print(f"Text delta received: {text_delta.delta}")
                elif response_type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA:
                    print(
                        f"Received audio transcript delta: {response_dict.get('delta', '')}"
                    )

                # Handle response completion
                elif response_type == ServerEventType.RESPONSE_DONE:
                    response_done = ResponseDoneEvent(**response_dict)
                    print("Response completed")
                    # Stop the current play stream if active
                    if self.active_stream_id and self.conversation_id:
                        stream_stop = PlayStreamStopMessage(
                            type="playStream.stop",
                            conversationId=self.conversation_id,
                            streamId=self.active_stream_id,
                        )
                        await self.telephony_websocket.send_json(
                            stream_stop.model_dump()
                        )
                        print(
                            f"Stopped play stream at end of response: {self.active_stream_id}"
                        )
                        self.active_stream_id = None
        except Exception as e:
            print(f"Error in receive_from_realtime: {e}")
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
        type="conversation.item.create",
        item=ConversationItemParam(
            type="message",
            role=MessageRole.USER,
            content=[
                ConversationItemContentParam(
                    type="input_text",
                    text="Hello! Please introduce yourself and tell me a joke.",
                )
            ],
        ),
    )

    print("Sending initial conversation item:", initial_conversation.model_dump_json())
    await realtime_websocket.send(initial_conversation.model_dump_json())

    # Create response using our model with default options
    response_create = ResponseCreateEvent(
        type="response.create",
        response=ResponseCreateOptions(
            modalities=["text", "audio"],
            voice=VOICE,
            instructions=SYSTEM_MESSAGE,
            output_audio_format="pcm16",
            temperature=0.8,
            max_output_tokens=4096,  # Maximum allowed value
            tool_choice="none",  # Disable function calling
        ),
    )
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
        turn_detection={
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 200,
            "create_response": True,
            "interrupt_response": True,
        },
        input_audio_format="pcm16",
        output_audio_format="pcm16",
        voice=VOICE,
        instructions=SYSTEM_MESSAGE,
        modalities=["text", "audio"],
        temperature=0.8,
        model="gpt-4o-realtime-preview-2024-10-01",
        tools=[],
        input_audio_noise_reduction={"type": "near_field"},
        input_audio_transcription={"model": "whisper-1"},
        max_response_output_tokens=4096,  # Maximum allowed value
        tool_choice="auto",
    )

    session_update = SessionUpdateEvent(type="session.update", session=session_config)

    print("Sending session update:", session_update.model_dump_json())
    await realtime_websocket.send(session_update.model_dump_json())

    # Have the AI speak first
    await send_initial_conversation_item(realtime_websocket)
