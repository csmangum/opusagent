"""Bridge between telephony WebSocket and OpenAI Realtime API for handling real-time audio communication.

This module provides functionality to bridge between a telephony WebSocket connection
and the OpenAI Realtime API, enabling real-time audio communication with AI agents.
It handles bidirectional audio streaming, session management, and event processing.
"""

import asyncio
import base64
import json
import os
import uuid
from typing import Any, Callable, Dict, Optional

import websockets
from dotenv import load_dotenv
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from opusagent.config.logging_config import configure_logging
from opusagent.function_handler import FunctionHandler
from opusagent.models.call_recorder import CallRecorder, AudioChannel, TranscriptType

# Import AudioCodes models
from opusagent.models.audiocodes_api import (
    PlayStreamChunkMessage,
    PlayStreamStartMessage,
    PlayStreamStopMessage,
    SessionAcceptedResponse,
    TelephonyEventType,
    UserStreamStartedResponse,
    UserStreamStoppedResponse,
)

# Import OpenAI Realtime API models
from opusagent.models.openai_api import (
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

# Configure logging
logger = configure_logging("telephony_realtime_bridge")

DEFAULT_MODEL = "gpt-4o-realtime-preview-2024-10-01"
MINI_MODEL = "gpt-4o-mini-realtime-preview-2024-12-17"
FUTURE_MODEL = "gpt-4o-realtime-preview-2025-06-03"

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PORT = int(os.getenv("PORT", 6060))
SYSTEM_MESSAGE = (
    "You are a customer service agent for Bank of Peril. You help customers with their banking needs. "
    "When a customer contacts you, first greet them warmly, then listen to their request and call the call_intent function to identify their intent. "
    "After calling call_intent, use the function result to guide your response:\n"
    "- If intent is 'card_replacement', ask which type of card they need to replace (use the available_cards from the function result)\n"
    "- If intent is 'account_inquiry', ask what specific account information they need\n"
    "- For other intents, ask clarifying questions to better understand their needs\n"
    "Always be helpful, professional, and use the information returned by functions to provide relevant follow-up questions."
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
        audio_chunks_sent (int): Number of audio chunks sent to the OpenAI Realtime API
        total_audio_bytes_sent (int): Total number of bytes sent to the OpenAI Realtime API
        input_transcript_buffer (list): Buffer for accumulating input audio transcriptions
        output_transcript_buffer (list): Buffer for accumulating output audio transcriptions
        function_handler (FunctionHandler): Handler for managing function calls from the OpenAI Realtime API
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

        # Audio buffer tracking for debugging
        self.audio_chunks_sent = 0
        self.total_audio_bytes_sent = 0

        # Transcript buffers for logging full transcripts
        self.input_transcript_buffer = []  # User → AI
        self.output_transcript_buffer = []  # AI → User

        # Initialize function handler
        self.function_handler = FunctionHandler(realtime_websocket)
        
        # Initialize call recorder (will be set up when conversation starts)
        self.call_recorder: Optional[CallRecorder] = None

        # Create event handler mappings for telephony events
        self.telephony_event_handlers = {
            TelephonyEventType.SESSION_INITIATE: self.handle_session_initiate,
            TelephonyEventType.USER_STREAM_START: self.handle_user_stream_start,
            TelephonyEventType.USER_STREAM_CHUNK: self.handle_user_stream_chunk,
            TelephonyEventType.USER_STREAM_STOP: self.handle_user_stream_stop,
            TelephonyEventType.SESSION_END: self.handle_session_end,
        }

        # Create event handler mappings for realtime events
        self.realtime_event_handlers = {
            # Session events
            ServerEventType.SESSION_UPDATED: self.handle_session_update,
            ServerEventType.SESSION_CREATED: self.handle_session_update,
            # Conversation events
            ServerEventType.CONVERSATION_ITEM_CREATED: lambda x: logger.info(
                "Conversation item created"
            ),
            # Speech detection events
            ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED: self.handle_speech_detection,
            ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED: self.handle_speech_detection,
            ServerEventType.INPUT_AUDIO_BUFFER_COMMITTED: self.handle_speech_detection,
            # Response events
            ServerEventType.RESPONSE_CREATED: lambda x: logger.info(
                "Response creation started"
            ),
            ServerEventType.RESPONSE_AUDIO_DELTA: self.handle_audio_response_delta,
            ServerEventType.RESPONSE_AUDIO_DONE: self.handle_audio_response_completion,
            ServerEventType.RESPONSE_TEXT_DELTA: self.handle_text_and_transcript,
            ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA: self.handle_audio_transcript_delta,
            ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DONE: self.handle_audio_transcript_done,
            ServerEventType.RESPONSE_DONE: self.handle_response_completion,
            # Add new handlers for output item and content part events
            ServerEventType.RESPONSE_OUTPUT_ITEM_ADDED: self.handle_output_item_added,
            ServerEventType.RESPONSE_CONTENT_PART_ADDED: self.handle_content_part_added,
            ServerEventType.RESPONSE_CONTENT_PART_DONE: self.handle_content_part_done,
            ServerEventType.RESPONSE_OUTPUT_ITEM_DONE: self.handle_output_item_done,
            # Add handlers for input audio transcription events
            ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_DELTA: self.handle_input_audio_transcription_delta,
            ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED: self.handle_input_audio_transcription_completed,
            # Add new handler for function call events
            ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA: self.function_handler.handle_function_call_arguments_delta,
            ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE: self.function_handler.handle_function_call_arguments_done,
        }

    async def close(self):
        """Safely close both WebSocket connections.

        This method ensures both the telephony and OpenAI Realtime API WebSocket connections
        are properly closed, handling any exceptions that may occur during the process.
        """
        if not self._closed:
            self._closed = True
            
            # Stop and finalize call recording
            if self.call_recorder:
                try:
                    await self.call_recorder.stop_recording()
                    summary = self.call_recorder.get_recording_summary()
                    logger.info(f"Call recording finalized: {summary}")
                except Exception as e:
                    logger.error(f"Error finalizing call recording: {e}")
            
            try:
                if (
                    self.realtime_websocket
                    and self.realtime_websocket.close_code is None
                ):
                    await self.realtime_websocket.close()
            except Exception as e:
                logger.error(f"Error closing OpenAI connection: {e}")
            try:
                if self.telephony_websocket and not self._is_websocket_closed():
                    await self.telephony_websocket.close()
            except Exception as e:
                logger.error(f"Error closing telephony connection: {e}")

    def _is_websocket_closed(self):
        """Check if telephony WebSocket is closed.

        Returns True if the WebSocket is closed or in an unusable state.
        """
        try:
            from starlette.websockets import WebSocketState

            return (
                not self.telephony_websocket
                or self.telephony_websocket.client_state == WebSocketState.DISCONNECTED
            )
        except ImportError:
            # Fallback check without WebSocketState
            return not self.telephony_websocket

    async def handle_session_initiate(self, data):
        """Handle session.initiate message from telephony client.

        This method processes the session initiation request, extracts necessary data,
        and sets up the conversation state.

        Args:
            data (dict): Session initiate message data
        """
        logger.info(f"Session initiate received: {data}")
        self.conversation_id = data.get("conversationId") or str(uuid.uuid4())
        logger.info(f"Conversation started: {self.conversation_id}")

        # Get media format
        self.media_format = data.get("supportedMediaFormats", ["raw/lpcm16"])[0]

        # Set flag to indicate we're waiting for session acceptance
        self.waiting_for_session_creation = True
        self.session_initialized = True

        # Initialize call recorder
        if self.conversation_id:
            self.call_recorder = CallRecorder(
                conversation_id=self.conversation_id,
                session_id=self.conversation_id,
                base_output_dir="call_recordings"
            )
            await self.call_recorder.start_recording()
            logger.info(f"Call recording started for conversation: {self.conversation_id}")

            # Update function handler with call recorder
            self.function_handler.call_recorder = self.call_recorder

        # Send session.accepted response immediately since session is already initialized
        session_accepted = SessionAcceptedResponse(
            type=TelephonyEventType.SESSION_ACCEPTED,
            conversationId=self.conversation_id,
            mediaFormat=self.media_format,
        )
        await self.telephony_websocket.send_json(session_accepted.model_dump())
        logger.info(f"Session accepted with format: {self.media_format}")
        self.waiting_for_session_creation = False

    async def handle_user_stream_start(self, data):
        """Handle userStream.start message from telephony client.

        This method processes the start of an audio stream from the client,
        and sends the appropriate acknowledgment response.

        Args:
            data (dict): UserStream start message data
        """
        logger.info(f"User stream start received: {data}")

        # Reset audio tracking counters for new stream
        self.audio_chunks_sent = 0
        self.total_audio_bytes_sent = 0

        # Send userStream.started response
        stream_started = UserStreamStartedResponse(
            type=TelephonyEventType.USER_STREAM_STARTED,
            conversationId=self.conversation_id,
        )
        await self.telephony_websocket.send_json(stream_started.model_dump())
        logger.info(f"User stream started for conversation: {self.conversation_id}")

    async def handle_user_stream_chunk(self, data):
        """Handle userStream.chunk message containing audio data from telephony client.

        This method processes audio chunks and forwards them to the OpenAI Realtime API
        for processing. It only forwards the audio if the connection is still active.

        Args:
            data (dict): UserStream chunk message data containing audio
        """
        if not self._closed and self.realtime_websocket.close_code is None:
            audio_chunk_b64 = data["audioChunk"]

            # Validate audio chunk meets OpenAI requirements
            try:
                # Decode base64 to get raw audio bytes
                audio_bytes = base64.b64decode(audio_chunk_b64)
                original_size = len(audio_bytes)

                # OpenAI requires at least 100ms of 16kHz 16-bit audio (3200 bytes minimum)
                min_chunk_size = 3200  # 100ms of 16kHz 16-bit mono audio

                # Check if chunk is too small
                if len(audio_bytes) < min_chunk_size:
                    logger.warning(
                        f"Audio chunk too small: {len(audio_bytes)} bytes. "
                        f"OpenAI requires at least {min_chunk_size} bytes (100ms of 16kHz 16-bit audio). "
                        f"Padding with silence."
                    )
                    # Pad with silence to meet minimum requirements
                    padding_needed = min_chunk_size - len(audio_bytes)
                    audio_bytes += b"\x00" * padding_needed

                    # Re-encode to base64
                    audio_chunk_b64 = base64.b64encode(audio_bytes).decode("utf-8")

                # Update tracking counters
                self.audio_chunks_sent += 1
                self.total_audio_bytes_sent += len(audio_bytes)

                # Log audio chunk details
                duration_ms = (
                    len(audio_bytes) / (16000 * 2)
                ) * 1000  # Assuming 16kHz 16-bit
                logger.debug(
                    f"Processing audio chunk #{self.audio_chunks_sent}: {original_size} -> {len(audio_bytes)} bytes "
                    f"(~{duration_ms:.1f}ms of audio). Total sent: {self.total_audio_bytes_sent} bytes"
                )

            except Exception as e:
                logger.error(f"Error processing audio chunk: {e}")
                # Skip this chunk if we can't process it
                return

            # Record caller audio if recorder is available
            if self.call_recorder:
                await self.call_recorder.record_caller_audio(audio_chunk_b64)

            # Use our Pydantic model for buffer append
            audio_append = InputAudioBufferAppendEvent(
                type="input_audio_buffer.append", audio=audio_chunk_b64
            )
            logger.debug(
                f"Sending audio to realtime-websocket (size: {len(audio_chunk_b64)} bytes base64)"
            )
            await self.realtime_websocket.send(audio_append.model_dump_json())
        else:
            logger.warning(
                "Skipping audio chunk - connection closed or websocket unavailable"
            )

    async def handle_user_stream_stop(self, data):
        """Handle userStream.stop message from telephony client.

        This method processes the end of an audio stream from the client,
        commits the audio buffer to OpenAI to signal end of speech,
        and sends the appropriate acknowledgment response.

        Args:
            data (dict): UserStream stop message data
        """
        logger.info(
            f"User stream stop received for conversation: {self.conversation_id}"
        )

        # Log buffer state before committing
        total_duration_ms = (
            (self.total_audio_bytes_sent / (16000 * 2)) * 1000
            if self.total_audio_bytes_sent > 0
            else 0
        )
        logger.info(
            f"Buffer state before commit: {self.audio_chunks_sent} chunks, "
            f"{self.total_audio_bytes_sent} bytes (~{total_duration_ms:.1f}ms of audio)"
        )

        # Commit the audio buffer to signal end of speech - only if we have enough audio data
        if not self._closed and self.realtime_websocket.close_code is None:
            # OpenAI requires at least 100ms of audio (3200 bytes for 16kHz 16-bit mono)
            min_audio_bytes = 3200  # 100ms of 16kHz 16-bit mono audio

            if self.total_audio_bytes_sent >= min_audio_bytes:
                buffer_commit = InputAudioBufferCommitEvent(
                    type="input_audio_buffer.commit"
                )
                try:
                    await self.realtime_websocket.send(buffer_commit.model_dump_json())
                    logger.info(
                        f"realtime_websocket_object: {self.realtime_websocket.send}"
                    )
                    logger.info(
                        f"Audio buffer committed with {self.audio_chunks_sent} chunks ({self.total_audio_bytes_sent} bytes)"
                    )
                    logger.info(
                        f"Audio buffer commit sent: {buffer_commit.model_dump_json()}"
                    )

                    # Since VAD is disabled, manually trigger response generation
                    response_create = {
                        "type": "response.create",
                        "response": {
                            "modalities": ["text", "audio"],
                            "output_audio_format": "pcm16",
                            "temperature": 0.8,
                            "max_output_tokens": 4096,
                            "voice": VOICE,
                        },
                    }
                    await self.realtime_websocket.send(json.dumps(response_create))
                    logger.info("Response creation triggered after audio buffer commit")

                except Exception as e:
                    logger.error(
                        f"Error sending audio buffer commit or response create: {e}"
                    )
            else:
                logger.info(
                    f"Skipping audio buffer commit - insufficient audio data: "
                    f"{self.total_audio_bytes_sent} bytes ({total_duration_ms:.1f}ms) "
                    f"< {min_audio_bytes} bytes (100ms minimum required by OpenAI)"
                )

            # Send userStream.stopped response regardless of commit
            stream_stopped = UserStreamStoppedResponse(
                type=TelephonyEventType.USER_STREAM_STOPPED,
                conversationId=self.conversation_id,
            )
            await self.telephony_websocket.send_json(stream_stopped.model_dump())
        else:
            logger.warning(
                "Cannot commit audio buffer - connection closed or websocket unavailable"
            )

    async def handle_session_end(self, data):
        """Handle session.end message from telephony client.

        This method processes the end of a session, closes all connections,
        and logs the reason for session termination.

        Args:
            data (dict): Session end message data
        """
        logger.info(f"Session end received: {data.get('reason', 'No reason provided')}")
        await self.close()
        logger.info(f"Telephony-Realtime bridge closed")

    async def handle_log_event(self, response_dict):
        """Handle log events from the OpenAI Realtime API.

        This method processes log events, with special handling for error events
        to provide detailed error information for debugging.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        response_type = response_dict["type"]

        # Enhanced error logging
        if response_type == "error":
            error_code = response_dict.get("code", "unknown")
            error_message = response_dict.get("message", "No message provided")
            error_details = response_dict.get("details", {})
            logger.error(f"ERROR DETAILS: code={error_code}, message='{error_message}'")
            if error_details:
                logger.error(f"ERROR ADDITIONAL DETAILS: {json.dumps(error_details)}")

            # Log the full error response for debugging
            logger.error(f"FULL ERROR RESPONSE: {json.dumps(response_dict)}")

        # Handle response.done events to check for quota issues
        elif response_type == "response.done":
            response_data = response_dict.get("response", {})
            status = response_data.get("status")
            status_details = response_data.get("status_details", {})

            if status == "failed":
                error_info = status_details.get("error", {})
                error_type = error_info.get("type")
                error_code = error_info.get("code")

                if (
                    error_type == "insufficient_quota"
                    or error_code == "insufficient_quota"
                ):
                    logger.error("=" * 80)
                    logger.error("🚨 OPENAI API QUOTA EXCEEDED")
                    logger.error("=" * 80)
                    logger.error("❌ Your OpenAI API quota has been exceeded!")
                    logger.error("")
                    logger.error("💡 WHAT THIS MEANS:")
                    logger.error(
                        "   • You've run out of API credits or hit your usage limit"
                    )
                    logger.error(
                        "   • The Realtime API is expensive and uses credits quickly"
                    )
                    logger.error(
                        "   • No audio will be generated until this is resolved"
                    )
                    logger.error("")
                    logger.error("🔧 HOW TO FIX:")
                    logger.error(
                        "   1. Check your OpenAI billing: https://platform.openai.com/account/billing"
                    )
                    logger.error("   2. Add more credits to your account")
                    logger.error("   3. Check/increase your usage limits")
                    logger.error("   4. Consider upgrading your OpenAI plan if needed")
                    logger.error("")
                    logger.error("📊 USAGE INFO:")
                    usage = response_data.get("usage", {})
                    if usage:
                        logger.error(
                            f"   • Total tokens in this request: {usage.get('total_tokens', 0)}"
                        )
                        logger.error(
                            f"   • Input tokens: {usage.get('input_tokens', 0)}"
                        )
                        logger.error(
                            f"   • Output tokens: {usage.get('output_tokens', 0)}"
                        )
                    logger.error("")
                    logger.error(
                        "⚠️  The bridge will now close this session to avoid hanging."
                    )
                    logger.error(
                        "   Please resolve your billing issue and restart the validation."
                    )
                    logger.error("=" * 80)
                    await self.close()
                else:
                    logger.error(
                        f"Response failed with error: {error_info.get('message', 'Unknown error')}"
                    )
                    logger.error(f"Error type: {error_type}, Error code: {error_code}")

    async def handle_session_update(self, response_dict):
        """Handle session update events from the OpenAI Realtime API.

        This method processes session created and updated events.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        response_type = response_dict["type"]

        if response_type == ServerEventType.SESSION_UPDATED:
            logger.info("Session updated successfully")
        elif response_type == ServerEventType.SESSION_CREATED:
            logger.info("Session created successfully")
            # Send initial conversation item immediately when session is created
            try:
                logger.info("Attempting to send initial conversation item...")
                await send_initial_conversation_item(self.realtime_websocket)
                logger.info("Initial conversation item sent successfully")
            except Exception as e:
                logger.error(f"Error sending initial conversation item: {e}")
                logger.error(f"Exception type: {type(e)}")
                import traceback

                logger.error(f"Traceback: {traceback.format_exc()}")

    async def handle_speech_detection(self, response_dict):
        """Handle speech detection events from the OpenAI Realtime API.

        This method processes speech detection events including speech started,
        speech stopped, and audio buffer committed events.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        response_type = response_dict["type"]

        if response_type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
            logger.info("Speech started detected")
            self.speech_detected = True
        elif response_type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
            logger.info("Speech stopped detected")
            self.speech_detected = False
        elif response_type == ServerEventType.INPUT_AUDIO_BUFFER_COMMITTED:
            logger.info("Audio buffer committed")

    async def handle_audio_response_delta(self, response_dict):
        """Handle audio response delta events from the OpenAI Realtime API.

        This method processes audio data chunks, creates audio streams when needed,
        and forwards the audio to the telephony client.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API containing audio
        """
        try:
            # Parse using our updated model - note the "delta" field instead of "audio"
            audio_delta = ResponseAudioDeltaEvent(**response_dict)

            # Check if connections are still active
            if self._closed or not self.conversation_id:
                logger.debug(
                    "Skipping audio delta - connection closed or no conversation ID"
                )
                return

            # Check if telephony websocket is available and not closed
            if not self.telephony_websocket or self._is_websocket_closed():
                logger.debug(
                    "Skipping audio delta - telephony websocket is closed or unavailable"
                )
                return

            # Start a new audio stream if needed
            if not self.active_stream_id:
                try:
                    # Start a new audio stream
                    self.active_stream_id = str(uuid.uuid4())
                    stream_start = PlayStreamStartMessage(
                        type=TelephonyEventType.PLAY_STREAM_START,
                        conversationId=self.conversation_id,
                        streamId=self.active_stream_id,
                        mediaFormat=self.media_format or "raw/lpcm16",
                    )
                    await self.telephony_websocket.send_json(stream_start.model_dump())
                    logger.info(f"Started play stream: {self.active_stream_id}")
                except Exception as e:
                    logger.error(f"Error starting audio stream: {e}")
                    # If we can't start the stream, the connection might be dead
                    logger.warning("Telephony WebSocket appears to be disconnected")
                    self.active_stream_id = None
                    return

            try:
                # Record bot audio if recorder is available
                if self.call_recorder:
                    await self.call_recorder.record_bot_audio(audio_delta.delta)

                # Send audio chunk with the delta value as the audio data
                stream_chunk = PlayStreamChunkMessage(
                    type=TelephonyEventType.PLAY_STREAM_CHUNK,
                    conversationId=self.conversation_id,
                    streamId=self.active_stream_id,
                    audioChunk=audio_delta.delta,  # Use delta field for audio data
                )
                await self.telephony_websocket.send_json(stream_chunk.model_dump())
                logger.debug(
                    f"Sent audio chunk to client (size: {len(audio_delta.delta)} bytes)"
                )
            except Exception as e:
                logger.error(f"Error sending audio chunk: {e}")
                # If we can't send audio chunks, the WebSocket is likely disconnected
                logger.warning(
                    "Telephony WebSocket appears to be disconnected, stopping audio stream"
                )
                self.active_stream_id = None  # Reset stream ID so it can be restarted if connection recovers
                # Don't close the connection here, just log the error
                # The connection will be closed by the main error handler if needed

        except Exception as e:
            logger.error(f"Error processing audio data: {e}")
            # Don't close the connection here, just log the error
            # The connection will be closed by the main error handler if needed

    async def handle_audio_response_completion(self, response_dict):
        """Handle audio response completion events from the OpenAI Realtime API.

        This method processes the completion of audio responses and stops
        any active audio streams to the telephony client.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        logger.info("Audio response completed")
        # Stop the play stream
        if self.active_stream_id and self.conversation_id:
            stream_stop = PlayStreamStopMessage(
                type=TelephonyEventType.PLAY_STREAM_STOP,
                conversationId=self.conversation_id,
                streamId=self.active_stream_id,
            )
            await self.telephony_websocket.send_json(stream_stop.model_dump())
            logger.info(f"Stopped play stream: {self.active_stream_id}")
            self.active_stream_id = None

    async def handle_text_and_transcript(self, response_dict):
        """Handle text and transcript events from the OpenAI Realtime API.

        This method processes text deltas and audio transcript deltas,
        logging them for monitoring and debugging purposes.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        response_type = response_dict["type"]

        if response_type == ServerEventType.RESPONSE_TEXT_DELTA:
            text_delta = ResponseTextDeltaEvent(**response_dict)
            logger.info(f"Text delta received: {text_delta.delta}")
        elif response_type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA:
            logger.info(
                f"Received audio transcript delta: {response_dict.get('delta', '')}"
            )

    async def handle_response_completion(self, response_dict):
        """Handle response completion events from the OpenAI Realtime API.

        This method processes the final completion of a response and ensures
        that any active audio streams are properly stopped.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        response_done = ResponseDoneEvent(**response_dict)
        logger.info("Response completed")
        # Stop the current play stream if active
        if self.active_stream_id and self.conversation_id:
            stream_stop = PlayStreamStopMessage(
                type=TelephonyEventType.PLAY_STREAM_STOP,
                conversationId=self.conversation_id,
                streamId=self.active_stream_id,
            )
            await self.telephony_websocket.send_json(stream_stop.model_dump())
            logger.info(
                f"Stopped play stream at end of response: {self.active_stream_id}"
            )
            self.active_stream_id = None

    async def handle_output_item_added(self, response_dict):
        """Handle response output item added events from the OpenAI Realtime API.

        This method processes when a new output item is added to the response,
        logging the event for monitoring purposes.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        item = response_dict.get("item", {})
        logger.info(f"Output item added: {item}")

        # If this is a function call item, capture the function name for later use
        if item.get("type") == "function_call":
            call_id = item.get("call_id")
            function_name = item.get("name")
            item_id = item.get("id")

            if call_id and function_name:
                # Initialize the function call state with the function name
                if call_id not in self.function_handler.active_function_calls:
                    self.function_handler.active_function_calls[call_id] = {
                        "arguments_buffer": "",
                        "item_id": item_id,
                        "output_index": response_dict.get("output_index", 0),
                        "response_id": response_dict.get("response_id"),
                        "function_name": function_name,
                    }
                else:
                    # Update existing entry with function name
                    self.function_handler.active_function_calls[call_id][
                        "function_name"
                    ] = function_name

                logger.info(
                    f"Captured function call: {function_name} with call_id: {call_id}"
                )

    async def handle_content_part_added(self, response_dict):
        """Handle response content part added events from the OpenAI Realtime API.

        This method processes when a new content part is added to a response,
        logging the event for monitoring purposes.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        logger.info(f"Content part added: {response_dict.get('part', {})}")

    async def handle_audio_transcript_delta(self, response_dict):
        """Handle audio transcript delta events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        delta = response_dict.get("delta", "")
        if delta:
            self.output_transcript_buffer.append(delta)
        logger.debug(f"Received audio transcript delta: {delta}")

    async def handle_audio_transcript_done(self, response_dict):
        """Handle audio transcript completion events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        full_transcript = "".join(self.output_transcript_buffer)
        logger.info(f"Full AI transcript (output audio): {full_transcript}")
        
        # Record transcript if recorder is available
        if self.call_recorder and full_transcript.strip():
            await self.call_recorder.add_transcript(
                text=full_transcript,
                channel=AudioChannel.BOT,
                transcript_type=TranscriptType.OUTPUT
            )
        
        self.output_transcript_buffer.clear()
        logger.info("Audio transcript completed")

    async def handle_content_part_done(self, response_dict):
        """Handle content part completion events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        logger.info("Content part completed")

    async def handle_output_item_done(self, response_dict):
        """Handle output item completion events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        logger.info("Output item completed")

    async def handle_input_audio_transcription_delta(self, response_dict):
        """Handle input audio transcription delta events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        delta = response_dict.get("delta", "")
        if delta:
            self.input_transcript_buffer.append(delta)
        logger.debug(f"Received input audio transcription delta: {delta}")

    async def handle_input_audio_transcription_completed(self, response_dict):
        """Handle input audio transcription completion events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        full_transcript = "".join(self.input_transcript_buffer)
        logger.info(f"Full user transcript (input audio): {full_transcript}")
        
        # Record transcript if recorder is available
        if self.call_recorder and full_transcript.strip():
            await self.call_recorder.add_transcript(
                text=full_transcript,
                channel=AudioChannel.CALLER,
                transcript_type=TranscriptType.INPUT
            )
        
        self.input_transcript_buffer.clear()
        logger.info("Input audio transcription completed")

    def _get_telephony_event_type(self, msg_type_str):
        """Convert a string message type to a TelephonyEventType enum value.

        Args:
            msg_type_str (str): The message type string from the raw message

        Returns:
            TelephonyEventType: The corresponding enum value or None if not found
        """
        try:
            return TelephonyEventType(msg_type_str)
        except ValueError:
            return None

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
                if self._closed:
                    break

                data = json.loads(message)
                msg_type_str = data["type"]

                # Convert string message type to enum
                msg_type = self._get_telephony_event_type(msg_type_str)

                if msg_type:
                    # Log only message type and audio chunk size if present
                    if "audioChunk" in data:
                        logger.info(
                            f"Received telephony message: {msg_type_str} with audio chunk size: {len(data['audioChunk'])} bytes"
                        )
                    else:
                        logger.info(f"Received telephony message: {msg_type_str}")
                    # Dispatch to the appropriate event handler
                    handler = self.telephony_event_handlers.get(msg_type)
                    if handler:
                        await handler(data)
                        # Special case for session.end to break the loop
                        if msg_type == TelephonyEventType.SESSION_END:
                            break
                    else:
                        logger.warning(
                            f"No handler for telephony message type: {msg_type}"
                        )
                else:
                    logger.info(f"Received telephony message: {message}")
                    logger.warning(f"Unknown telephony message type: {msg_type_str}")

        except WebSocketDisconnect:
            logger.info("Client disconnected.")
            await self.close()
        except Exception as e:
            logger.error(f"Error in receive_from_telephony: {e}")
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
                logger.info(f"Received OpenAI message type: {response_type}")

                # Add detailed logging for important events
                if response_type in ["response.created", "response.done"]:
                    logger.info(
                        f"Response event details: {json.dumps(response_dict, indent=2)}"
                    )
                elif response_type == "response.output_item.added":
                    logger.info(
                        f"Output item added: {json.dumps(response_dict.get('item', {}), indent=2)}"
                    )
                elif response_type == "response.content_part.added":
                    logger.info(
                        f"Content part added: {json.dumps(response_dict.get('part', {}), indent=2)}"
                    )
                elif response_type in [
                    "response.audio.delta",
                    "response.audio_transcript.delta",
                ]:
                    logger.info(
                        f"Audio event: {response_type} - delta size: {len(response_dict.get('delta', ''))}"
                    )

                # Handle log events first
                if response_type in [event.value for event in LOG_EVENT_TYPES]:
                    await self.handle_log_event(response_dict)
                    continue

                # Dispatch to the appropriate event handler
                handler = self.realtime_event_handlers.get(response_type)
                if handler:
                    try:
                        # Special logging for function call events
                        if response_type in [
                            "response.function_call_arguments.delta",
                            "response.function_call_arguments.done",
                        ]:
                            logger.info(f"🎯 Routing {response_type} to handler")

                        if asyncio.iscoroutinefunction(handler):
                            await handler(response_dict)
                        else:
                            handler(response_dict)
                    except Exception as e:
                        logger.error(f"Error in event handler for {response_type}: {e}")
                else:
                    logger.warning(f"Unknown OpenAI event type: {response_type}")
                    logger.info(
                        f"Unknown event data: {json.dumps(response_dict, indent=2)}"
                    )

        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"OpenAI WebSocket connection closed: {e}")
            await self.close()
        except TypeError as e:
            logger.error(f"Type error in receive_from_realtime: {e}")
            # Don't attempt to close if there's a NoneType error
            if not self._closed:
                self._closed = True
        except Exception as e:
            logger.error(f"Error in receive_from_realtime: {e}")
            if not self._closed:
                await self.close()


async def send_initial_conversation_item(realtime_websocket):
    """Send the initial conversation item to start the AI interaction.

    This function creates and sends the first conversation item to the OpenAI Realtime API,
    initiating the conversation with a greeting and request for an introduction and joke.

    Args:
        realtime_websocket (websockets.WebSocketClientProtocol): WebSocket connection to OpenAI Realtime API
    """
    try:
        # Create initial conversation item using plain JSON to avoid model validation issues
        initial_conversation = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "You are a customer service agent for Bank of Peril. You are given a task to help the customer with their banking needs. Start by saying 'Hello! How can I help you today?' You will infer the customer's intent from their response and call the call_intent function.",
                    }
                ],
            },
        }

        logger.info(
            "Sending initial conversation item: %s", json.dumps(initial_conversation)
        )
        await realtime_websocket.send(json.dumps(initial_conversation))

        # Wait for the conversation item to be processed
        await asyncio.sleep(2)

        # Create response using the correct structure for OpenAI Realtime API
        response_create = {
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"],
                "output_audio_format": "pcm16",
                "temperature": 0.8,
                "max_output_tokens": 4096,
                "voice": VOICE,
            },
        }

        logger.info("Sending response create: %s", json.dumps(response_create))
        await realtime_websocket.send(json.dumps(response_create))
        logger.info("Initial conversation flow initiated successfully")

    except Exception as e:
        logger.error(f"Error in send_initial_conversation_item: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


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
        # turn_detection removed to disable OpenAI VAD
        input_audio_format="pcm16",
        output_audio_format="pcm16",
        voice=VOICE,
        instructions=SYSTEM_MESSAGE,
        modalities=["text", "audio"],
        temperature=0.8,
        model=DEFAULT_MODEL,
        tools=[
            {
                "type": "function",
                "name": "get_balance",
                "description": "Get the user's account balance.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "type": "function",
                "name": "transfer_funds",
                "description": "Transfer funds to another account.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "number"},
                        "to_account": {"type": "string"},
                    },
                },
            },
            {
                "type": "function",
                "name": "transfer_to_human",
                "description": "Transfer the conversation to a human agent.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "The reason for transferring to a human agent",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "normal", "high"],
                            "description": "The priority level of the transfer",
                        },
                        "context": {
                            "type": "object",
                            "description": "Additional context to pass to the human agent",
                        },
                    },
                    "required": ["reason"],
                },
            },
            {
                "type": "function",
                "name": "call_intent",
                "description": "Get the user's intent.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "enum": ["card_replacement", "account_inquiry", "other"],
                        },
                    },
                    "required": ["intent"],
                },
            },
            {
                "type": "function",
                "name": "member_account_confirmation",
                "description": "Confirm which member account/card needs replacement.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "member_accounts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of available member accounts/cards",
                        },
                        "organization_name": {"type": "string"},
                    },
                },
            },
            {
                "type": "function",
                "name": "replacement_reason",
                "description": "Collect the reason for card replacement.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "card_in_context": {"type": "string"},
                        "reason": {
                            "type": "string",
                            "enum": ["Lost", "Damaged", "Stolen", "Other"],
                        },
                    },
                },
            },
            {
                "type": "function",
                "name": "confirm_address",
                "description": "Confirm the address for card delivery.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "card_in_context": {"type": "string"},
                        "address_on_file": {"type": "string"},
                        "confirmed_address": {"type": "string"},
                    },
                },
            },
            {
                "type": "function",
                "name": "start_card_replacement",
                "description": "Start the card replacement process.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "card_in_context": {"type": "string"},
                        "address_in_context": {"type": "string"},
                    },
                },
            },
            {
                "type": "function",
                "name": "finish_card_replacement",
                "description": "Finish the card replacement process and provide delivery information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "card_in_context": {"type": "string"},
                        "address_in_context": {"type": "string"},
                        "delivery_time": {"type": "string"},
                    },
                },
            },
            {
                "type": "function",
                "name": "wrap_up",
                "description": "Wrap up the call with closing remarks.",
                "parameters": {
                    "type": "object",
                    "properties": {"organization_name": {"type": "string"}},
                },
            },
        ],
        input_audio_noise_reduction={"type": "near_field"},
        input_audio_transcription={"model": "whisper-1"},
        max_response_output_tokens=4096,  # Maximum allowed value
        tool_choice="auto",
    )

    session_update = SessionUpdateEvent(type="session.update", session=session_config)

    logger.info("Sending session update: %s", session_update.model_dump_json())
    await realtime_websocket.send(session_update.model_dump_json())

    # Wait for the session to be updated before proceeding
    # await send_initial_conversation_item(realtime_websocket)
