"""Enhanced Base bridge class with dependency injection for agents.

This module provides an improved base class for bridging between platforms and 
OpenAI Realtime API with dependency injection for agents, enabling better
modularity and testability.
"""

import json
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import websockets
from fastapi import WebSocket
from websockets.asyncio.client import ClientConnection

from opusagent.agents import BaseAgent
from opusagent.audio_stream_handler import AudioStreamHandler
from opusagent.call_recorder import CallRecorder
from opusagent.config.logging_config import configure_logging
from opusagent.event_router import EventRouter
from opusagent.function_handler import FunctionHandler
from opusagent.realtime_handler import RealtimeHandler
from opusagent.session_manager import SessionManager
from opusagent.transcript_manager import TranscriptManager

# Configure logging
logger = configure_logging("enhanced_base_bridge")


class EnhancedBaseRealtimeBridge(ABC):
    """Enhanced base bridge class with dependency injection for agents.

    This class improves upon BaseRealtimeBridge by accepting agents as dependencies
    instead of hardcoding specific agent types, enabling better modularity and
    testability.

    The key improvement is that agents are injected as dependencies, which means:
    - Bridges are no longer coupled to specific agent implementations
    - Different agent types can be used without modifying bridge code
    - Testing is easier with mock agents
    - Configuration can drive agent selection

    Attributes:
        platform_websocket: Platform-specific WebSocket connection
        realtime_websocket: WebSocket connection to OpenAI Realtime API
        agent: The injected agent that handles conversation logic
        conversation_id: Unique identifier for the current conversation
        media_format: Audio format being used for the session
        speech_detected: Whether speech is currently being detected
        _closed: Flag indicating whether the bridge connections are closed
    """

    def __init__(
        self,
        platform_websocket,
        realtime_websocket: ClientConnection,
        agent: BaseAgent,
    ):
        """Initialize the enhanced realtime bridge with dependency injection.

        Args:
            platform_websocket: WebSocket connection to the platform
            realtime_websocket: WebSocket connection to OpenAI Realtime API
            agent: The agent that will handle conversation logic (dependency injection)
        """
        self.platform_websocket = platform_websocket
        self.realtime_websocket = realtime_websocket
        self.agent = agent
        self._closed = False
        self.conversation_id: Optional[str] = None
        self.media_format: Optional[str] = None
        self.speech_detected = False

        # Get session configuration from the injected agent
        self.session_config = agent.get_session_config()

        # Audio buffer tracking for debugging
        self.audio_chunks_sent = 0
        self.total_audio_bytes_sent = 0

        # Transcript buffers for logging full transcripts
        self.input_transcript_buffer = []
        self.output_transcript_buffer = []

        # Initialize call recorder
        self.call_recorder: Optional[CallRecorder] = None

        # Initialize function handler and register agent functions
        self.function_handler = FunctionHandler(
            realtime_websocket=realtime_websocket,
            call_recorder=self.call_recorder,
            voice=self.session_config.voice or "verse",
            hang_up_callback=self.hang_up,
        )

        # Register functions from the injected agent
        agent.register_functions(self.function_handler)

        # Initialize transcript manager
        self.transcript_manager = TranscriptManager()

        # Initialize audio handler
        self.audio_handler = AudioStreamHandler(
            platform_websocket=platform_websocket,
            realtime_websocket=realtime_websocket,
            call_recorder=self.call_recorder,
        )

        # Initialize session manager with agent's session config
        self.session_manager = SessionManager(realtime_websocket, self.session_config)

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

        # Log agent information
        agent_info = agent.get_agent_info()
        logger.info(f"Bridge initialized with agent: {agent_info['name']} (type: {agent_info['agent_type']})")

    @abstractmethod
    def register_platform_event_handlers(self):
        """Register platform-specific event handlers with the event router."""
        pass

    @abstractmethod
    async def send_platform_json(self, payload: dict):
        """Send JSON payload to the platform WebSocket."""
        pass

    async def close(self):
        """Safely close both WebSocket connections."""
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
        """Check if platform WebSocket is closed."""
        try:
            from starlette.websockets import WebSocketState
            return (
                not self.platform_websocket
                or self.platform_websocket.client_state == WebSocketState.DISCONNECTED
            )
        except ImportError:
            return not self.platform_websocket

    @abstractmethod
    async def handle_session_start(self, data: Dict[str, Any]):
        """Handle session start from platform."""
        pass

    @abstractmethod
    async def handle_audio_start(self, data: Dict[str, Any]):
        """Handle start of audio stream from platform."""
        pass

    @abstractmethod
    async def handle_audio_data(self, data: Dict[str, Any]):
        """Handle audio data from platform."""
        pass

    @abstractmethod
    async def handle_audio_end(self, data: Dict[str, Any]):
        """Handle end of audio stream from platform."""
        pass

    @abstractmethod
    async def handle_session_end(self, data: Dict[str, Any]):
        """Handle end of session from platform."""
        pass

    async def initialize_conversation(self, conversation_id: Optional[str] = None):
        """Initialize a new conversation with OpenAI."""
        self.conversation_id = conversation_id or str(uuid.uuid4())
        logger.info(f"Conversation started: {self.conversation_id}")

        # Initialize session with OpenAI Realtime API using agent's configuration
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
            logger.info(f"Call recording started for conversation: {self.conversation_id}")

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
        await self.audio_handler.commit_audio_buffer()

        if not self.realtime_handler.response_active:
            logger.info("No active response - creating new response immediately")
            await self.session_manager.create_response()
        else:
            self.realtime_handler.pending_user_input = {
                "audio_committed": True,
                "timestamp": time.time(),
            }
            logger.info(f"User input queued - response already active (response_id: {self.realtime_handler.response_id_tracker})")

            if not self.realtime_handler.response_active:
                logger.info("Response became inactive while queuing - processing immediately")
                await self.session_manager.create_response()
                self.realtime_handler.pending_user_input = None

    async def receive_from_platform(self):
        """Receive and process data from the platform WebSocket."""
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
        """Receive and process events from the OpenAI Realtime API."""
        await self.realtime_handler.receive_from_realtime()

    async def hang_up(self, reason: str = "Call completed"):
        """Hang up the call by ending the session."""
        if self._closed:
            logger.info(f"Bridge already closed, ignoring hang-up request: {reason}")
            return

        logger.info(f"🔚 Hanging up call: {reason}")

        try:
            await self.send_session_end(reason)
            await self.close()
            logger.info("✅ Call hang-up completed successfully")
        except Exception as e:
            logger.error(f"❌ Error during hang-up: {e}")
            await self.close()

    async def send_session_end(self, reason: str):
        """Send session end message to the platform."""
        logger.info(f"Enhanced bridge send_session_end called with reason: {reason}")

    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the current agent."""
        return self.agent.get_agent_info()

    def swap_agent(self, new_agent: BaseAgent):
        """Swap the current agent with a new one.
        
        This allows for dynamic agent changing during runtime.
        Note: This should be done carefully and may require session reinitialization.
        
        Args:
            new_agent: The new agent to use
        """
        logger.info(f"Swapping agent from {self.agent.get_agent_info()['name']} to {new_agent.get_agent_info()['name']}")
        
        # Update the agent
        self.agent = new_agent
        
        # Update session config
        self.session_config = new_agent.get_session_config()
        
        # Re-register functions (note: function_handler doesn't have clear_functions method)
        # Would need to create a new function_handler or add clear method to existing one
        # For now, we create a new function_handler
        self.function_handler = FunctionHandler(
            realtime_websocket=self.realtime_websocket,
            call_recorder=self.call_recorder,
            voice=self.session_config.voice or "verse",
            hang_up_callback=self.hang_up,
        )
        new_agent.register_functions(self.function_handler)
        
        # Update session manager with new config
        self.session_manager.session_config = self.session_config
        
        logger.info("Agent swap completed successfully")