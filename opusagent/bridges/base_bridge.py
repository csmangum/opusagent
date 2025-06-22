"""Base bridge class for handling real-time communication between platforms and OpenAI Realtime API.

This module provides a framework-agnostic base class for bridging between any platform's
WebSocket connection and the OpenAI Realtime API, enabling real-time audio communication
with AI agents. It handles bidirectional audio streaming, session management, and event processing.
"""

import json
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import websockets
from fastapi import WebSocket
from websockets.asyncio.client import ClientConnection

from opusagent.audio_stream_handler import AudioStreamHandler
from opusagent.call_recorder import CallRecorder
from opusagent.config.logging_config import configure_logging
from opusagent.event_router import EventRouter
from opusagent.function_handler import FunctionHandler
from opusagent.models.openai_api import SessionConfig
from opusagent.realtime_handler import RealtimeHandler
from opusagent.session_manager import SessionManager
from opusagent.transcript_manager import TranscriptManager

# Configure logging
logger = configure_logging("base_bridge")


class BaseRealtimeBridge(ABC):
    """Base bridge class for handling bidirectional communication between platforms and OpenAI Realtime API.

    This class manages the WebSocket connections between any platform and the OpenAI Realtime API,
    handling audio streaming, session management, and event processing in both directions.

    Attributes:
        platform_websocket: Platform-specific WebSocket connection (e.g. FastAPI WebSocket)
        realtime_websocket (ClientConnection): WebSocket connection to OpenAI Realtime API
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
        event_router (EventRouter): Router for handling platform and realtime events
        transcript_manager (TranscriptManager): Manager for handling transcripts
        realtime_handler (RealtimeHandler): Handler for OpenAI Realtime API communication
        session_config (SessionConfig): Predefined session configuration for the OpenAI Realtime API
    """

    def __init__(
        self,
        platform_websocket,
        realtime_websocket: ClientConnection,
        session_config: SessionConfig,
    ):
        """Initialize the base realtime bridge.

        Args:
            platform_websocket: WebSocket connection to the platform (Twilio, AudioCodes, etc.)
            realtime_websocket: WebSocket connection to OpenAI Realtime API
            session_config: Predefined session configuration for the OpenAI Realtime API
        """
        self.platform_websocket = platform_websocket
        self.realtime_websocket = realtime_websocket
        self.session_config = session_config
        self._closed = False
        self.conversation_id: Optional[str] = None
        self.media_format: Optional[str] = None
        self.speech_detected = False

        # Audio buffer tracking for debugging
        self.audio_chunks_sent = 0
        self.total_audio_bytes_sent = 0

        # Transcript buffers for logging full transcripts
        self.input_transcript_buffer = []  # User → AI
        self.output_transcript_buffer = []  # AI → User

        # Initialize call recorder
        self.call_recorder: Optional[CallRecorder] = None

        # Initialize function handler
        self.function_handler = FunctionHandler(
            realtime_websocket=realtime_websocket,
            call_recorder=self.call_recorder,
            voice=session_config.voice or "verse",
            hang_up_callback=self.hang_up,
        )

        # Register customer service functions
        from opusagent.customer_service_agent import register_customer_service_functions

        register_customer_service_functions(self.function_handler)

        # Initialize transcript manager
        self.transcript_manager = TranscriptManager()

        # Initialize audio handler
        self.audio_handler = AudioStreamHandler(
            platform_websocket=platform_websocket,
            realtime_websocket=realtime_websocket,
            call_recorder=self.call_recorder,
        )

        # Initialize session manager
        self.session_manager = SessionManager(realtime_websocket, session_config)

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

        # Register platform-specific event handlers
        self.register_platform_event_handlers()

    @abstractmethod
    def register_platform_event_handlers(self):
        """Register platform-specific event handlers with the event router.

        This method should be implemented by subclasses to register their specific
        event types and handlers with the event router.
        """
        pass

    @abstractmethod
    async def send_platform_json(self, payload: dict):
        """Send JSON payload to the platform WebSocket.

        Args:
            payload (dict): The JSON payload to send
        """
        pass

    async def close(self):
        """Safely close both WebSocket connections.

        This method ensures both the platform and OpenAI Realtime API WebSocket connections
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
                if self.platform_websocket and not self._is_websocket_closed():
                    await self.platform_websocket.close()
            except Exception as e:
                logger.error(f"Error closing platform connection: {e}")

    def _is_websocket_closed(self):
        """Check if platform WebSocket is closed.

        Returns True if the WebSocket is closed or in an unusable state.
        """
        try:
            from starlette.websockets import WebSocketState

            return (
                not self.platform_websocket
                or self.platform_websocket.client_state == WebSocketState.DISCONNECTED
            )
        except ImportError:
            # Fallback check without WebSocketState
            return not self.platform_websocket

    @abstractmethod
    async def handle_session_start(self, data: Dict[str, Any]):
        """Handle session start from platform.

        This method should be implemented by subclasses to handle their specific
        session start event and initialize the conversation.

        Args:
            data (Dict[str, Any]): Session start message data
        """
        pass

    @abstractmethod
    async def handle_audio_start(self, data: Dict[str, Any]):
        """Handle start of audio stream from platform.

        Args:
            data (Dict[str, Any]): Audio start message data
        """
        pass

    @abstractmethod
    async def handle_audio_data(self, data: Dict[str, Any]):
        """Handle audio data from platform.

        Args:
            data (Dict[str, Any]): Audio data message
        """
        pass

    @abstractmethod
    async def handle_audio_end(self, data: Dict[str, Any]):
        """Handle end of audio stream from platform.

        Args:
            data (Dict[str, Any]): Audio end message data
        """
        pass

    @abstractmethod
    async def handle_session_end(self, data: Dict[str, Any]):
        """Handle end of session from platform.

        Args:
            data (Dict[str, Any]): Session end message data
        """
        pass

    async def initialize_conversation(self, conversation_id: Optional[str] = None):
        #! Agent should do this
        """Initialize a new conversation with OpenAI.

        Args:
            conversation_id (Optional[str]): Optional conversation ID to use
        """
        self.conversation_id = conversation_id or str(uuid.uuid4())
        logger.info(f"Conversation started: {self.conversation_id}")

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

            # Update handlers with call recorder
            self.function_handler.call_recorder = self.call_recorder
            self.audio_handler.call_recorder = self.call_recorder
            self.transcript_manager.set_call_recorder(self.call_recorder)

            # Initialize audio stream
            await self.audio_handler.initialize_stream(
                conversation_id=self.conversation_id,
                media_format=self.media_format or "pcm16",
            )

    async def handle_audio_commit(self):
        """Handle committing audio buffer and triggering response."""
        # Commit the audio buffer
        await self.audio_handler.commit_audio_buffer()

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

    async def receive_from_platform(self):
        """Receive and process data from the platform WebSocket.

        This method continuously listens for messages from the platform WebSocket,
        processes them, and forwards them to the OpenAI Realtime API. It handles
        various events including session initiation, audio streaming, and disconnections.

        Raises:
            Exception: For any errors during processing
        """
        try:
            async for message in self.platform_websocket.iter_text():
                if self._closed:
                    break

                data = json.loads(message)
                await self.event_router.handle_platform_event(data)

        except Exception as e:
            logger.error(f"Error in receive_from_platform: {e}")
            await self.close()

    async def receive_from_realtime(self):
        """Receive and process events from the OpenAI Realtime API.

        This method continuously listens for messages from the OpenAI Realtime API,
        processes them, and forwards responses to the platform WebSocket.

        Raises:
            Exception: For any errors during processing
        """
        await self.realtime_handler.receive_from_realtime()

    async def hang_up(self, reason: str = "Call completed"):
        """
        Hang up the call by ending the session.

        This method is called when the AI determines the call should end,
        either through completion of tasks or transfer to human.

        Args:
            reason: The reason for hanging up the call
        """
        if self._closed:
            logger.info(f"Bridge already closed, ignoring hang-up request: {reason}")
            return

        logger.info(f"🔚 Hanging up call: {reason}")

        try:
            # Send session end to platform if supported
            await self.send_session_end(reason)

            # Close the bridge connections
            await self.close()

            logger.info("✅ Call hang-up completed successfully")

        except Exception as e:
            logger.error(f"❌ Error during hang-up: {e}")
            # Still try to close connections
            await self.close()

    async def send_session_end(self, reason: str):
        """
        Send session end message to the platform.

        This method should be implemented by subclasses to send platform-specific
        session end messages. Base implementation does nothing.

        Args:
            reason: The reason for ending the session
        """
        logger.info(f"Base bridge send_session_end called with reason: {reason}")
        # Subclasses should override this to send platform-specific session end messages
        pass
