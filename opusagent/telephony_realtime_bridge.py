"""Bridge between telephony WebSocket and OpenAI Realtime API for handling real-time audio communication.

This module provides functionality to bridge between a telephony WebSocket connection
and the OpenAI Realtime API, enabling real-time audio communication with AI agents.
It handles bidirectional audio streaming, session management, and event processing.
"""

import json
import os
import time
import uuid
from typing import Optional

import websockets
from dotenv import load_dotenv
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from opusagent.audio_stream_handler import AudioStreamHandler
from opusagent.call_recorder import CallRecorder
from opusagent.config.logging_config import configure_logging
from opusagent.event_router import EventRouter
from opusagent.function_handler import FunctionHandler

# Import AudioCodes models
from opusagent.models.audiocodes_api import (
    SessionAcceptedResponse,
    TelephonyEventType,
    UserStreamStartedResponse,
    UserStreamStoppedResponse,
)

# Import OpenAI Realtime API models
from opusagent.models.openai_api import LogEventType
from opusagent.pure_prompt import SESSION_PROMPT
from opusagent.realtime_handler import RealtimeHandler
from opusagent.session_manager import SessionManager
from opusagent.transcript_manager import TranscriptManager

load_dotenv()

# Configure logging
logger = configure_logging("telephony_realtime_bridge")

DEFAULT_MODEL = "gpt-4o-realtime-preview-2024-10-01"
MINI_MODEL = "gpt-4o-mini-realtime-preview-2024-12-17"
FUTURE_MODEL = "gpt-4o-realtime-preview-2025-06-03"

SELECTED_MODEL = FUTURE_MODEL

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PORT = int(os.getenv("PORT", 6060))
SYSTEM_MESSAGE = (
    "You are a customer service agent. You help customers with their banking needs. "
    "When a customer contacts you, first greet them warmly, then listen to their request and call the call_intent function to identify their intent. "
    "After calling call_intent, use the function result to guide your response:\n"
    "- If intent is 'card_replacement', ask which type of card they need to replace (use the available_cards from the function result)\n"
    "- If intent is 'account_inquiry', ask what specific account information they need\n"
    "- For other intents, ask clarifying questions to better understand their needs\n"
    "Always be helpful, professional, and use the information returned by functions to provide relevant follow-up questions."
)
VOICE = "verse"
LOG_EVENT_TYPES = [
    LogEventType.ERROR,
    LogEventType.RESPONSE_CONTENT_DONE,
    LogEventType.RATE_LIMITS_UPDATED,
    # Removed RESPONSE_DONE so it can be handled by the normal event handler
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
        speech_detected (bool): Whether speech is currently being detected
        _closed (bool): Flag indicating whether the bridge connections are closed
        audio_chunks_sent (int): Number of audio chunks sent to the OpenAI Realtime API
        total_audio_bytes_sent (int): Total number of bytes sent to the OpenAI Realtime API
        input_transcript_buffer (list): Buffer for accumulating input audio transcriptions
        output_transcript_buffer (list): Buffer for accumulating output audio transcriptions
        function_handler (FunctionHandler): Handler for managing function calls from the OpenAI Realtime API
        audio_handler (AudioStreamHandler): Handler for managing audio streams
        session_manager (SessionManager): Handler for managing OpenAI Realtime API sessions
        event_router (EventRouter): Router for handling telephony and realtime events
        transcript_manager (TranscriptManager): Manager for handling transcripts
        realtime_handler (RealtimeHandler): Handler for OpenAI Realtime API communication
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

        # Initialize transcript manager
        self.transcript_manager = TranscriptManager()

        # Initialize audio handler
        self.audio_handler = AudioStreamHandler(
            telephony_websocket=telephony_websocket,
            realtime_websocket=realtime_websocket,
            call_recorder=self.call_recorder,
        )

        # Initialize session manager
        self.session_manager = SessionManager(realtime_websocket)

        # Initialize event router
        self.event_router = EventRouter()

        # Initialize realtime handler
        self.realtime_handler = RealtimeHandler(
            realtime_websocket=realtime_websocket,
            audio_handler=self.audio_handler,
            function_handler=self.function_handler,
            session_manager=self.session_manager,
            event_router=self.event_router,
            transcript_manager=self.transcript_manager,
        )

        # Register telephony event handlers
        self.event_router.register_platform_handler(
            TelephonyEventType.SESSION_INITIATE, self.handle_session_initiate
        )
        self.event_router.register_platform_handler(
            TelephonyEventType.USER_STREAM_START, self.handle_user_stream_start
        )
        self.event_router.register_platform_handler(
            TelephonyEventType.USER_STREAM_CHUNK, self.handle_user_stream_chunk
        )
        self.event_router.register_platform_handler(
            TelephonyEventType.USER_STREAM_STOP, self.handle_user_stream_stop
        )
        self.event_router.register_platform_handler(
            TelephonyEventType.SESSION_END, self.handle_session_end
        )

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

            # Close realtime handler
            await self.realtime_handler.close()

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

        # Initialize session with OpenAI Realtime API
        await self.session_manager.initialize_session()
        await self.session_manager.send_initial_conversation_item()

        # Initialize call recorder
        if self.conversation_id:
            self.call_recorder = CallRecorder(
                conversation_id=self.conversation_id,
                session_id=self.conversation_id,
                base_output_dir="call_recordings",
            )
            await self.call_recorder.start_recording()
            logger.info(
                f"Call recording started for conversation: {self.conversation_id}"
            )

            # Update function handler with call recorder
            self.function_handler.call_recorder = self.call_recorder

            # Update audio handler with call recorder
            self.audio_handler.call_recorder = self.call_recorder

            # Update transcript manager with call recorder
            self.transcript_manager.set_call_recorder(self.call_recorder)

            # Initialize audio stream
            await self.audio_handler.initialize_stream(
                conversation_id=self.conversation_id,
                media_format=self.media_format,
            )

        # Send session.accepted response immediately since session is already initialized
        session_accepted = SessionAcceptedResponse(
            type=TelephonyEventType.SESSION_ACCEPTED,
            conversationId=self.conversation_id,
            mediaFormat=self.media_format,
        )
        await self.telephony_websocket.send_json(session_accepted.model_dump())
        logger.info(f"Session accepted with format: {self.media_format}")

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
        await self.audio_handler.handle_incoming_audio(data)

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

        # Commit the audio buffer
        await self.audio_handler.commit_audio_buffer()

        # Send userStream.stopped response
        stream_stopped = UserStreamStoppedResponse(
            type=TelephonyEventType.USER_STREAM_STOPPED,
            conversationId=self.conversation_id,
        )
        await self.telephony_websocket.send_json(stream_stopped.model_dump())

        # Only trigger response if no active response
        if not self.realtime_handler.response_active:
            logger.info("No active response - creating new response immediately")
            await self.session_manager.create_response()
        else:
            # Queue the user input for processing after current response completes
            self.realtime_handler.pending_user_input = {
                "audio_committed": True,
                "timestamp": time.time(),
            }
            logger.info(
                f"User input queued - response already active (response_id: {self.realtime_handler.response_id_tracker})"
            )

            # Double-check if response became inactive while we were setting pending input
            if not self.realtime_handler.response_active:
                logger.info(
                    "Response became inactive while queuing - processing immediately"
                )
                await self.session_manager.create_response()
                self.realtime_handler.pending_user_input = None

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
                await self.event_router.handle_platform_event(data)

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
        await self.realtime_handler.receive_from_realtime()
