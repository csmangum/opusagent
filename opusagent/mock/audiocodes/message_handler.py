"""
Message handling for the AudioCodes mock client.

This module provides WebSocket message processing and event handling for the
AudioCodes mock client. It processes incoming messages from the bridge server
and updates the session state accordingly.
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from .models import MessageEvent, MessageType
from .session_manager import SessionManager


class MessageHandler:
    """
    WebSocket message handler for the AudioCodes mock client.

    This class processes incoming WebSocket messages from the bridge server,
    updates session state, and triggers appropriate callbacks for different
    message types.

    Attributes:
        logger (logging.Logger): Logger instance for debugging
        session_manager (SessionManager): Session manager instance
        received_messages (List[Dict[str, Any]]): List of received messages
        event_handlers (Dict[str, List[Callable]]): Registered event handlers
    """

    def __init__(
        self, session_manager: SessionManager, logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the MessageHandler.

        Args:
            session_manager (SessionManager): Session manager instance
            logger (Optional[logging.Logger]): Logger instance for debugging
        """
        self.logger = logger or logging.getLogger(__name__)
        self.session_manager = session_manager
        self.received_messages: List[Dict[str, Any]] = []
        self.event_handlers: Dict[str, List[Callable]] = {}

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default message handlers."""
        handlers = {
            MessageType.SESSION_ACCEPTED: [
                self.session_manager.handle_session_accepted
            ],
            MessageType.SESSION_RESUMED: [self.session_manager.handle_session_resumed],
            MessageType.SESSION_ERROR: [self.session_manager.handle_session_error],
            MessageType.CONNECTION_VALIDATED: [
                self.session_manager.handle_connection_validated
            ],
            MessageType.USER_STREAM_STARTED: [self._handle_user_stream_started],
            MessageType.USER_STREAM_STOPPED: [self._handle_user_stream_stopped],
            MessageType.PLAY_STREAM_START: [self._handle_play_stream_start],
            MessageType.PLAY_STREAM_CHUNK: [self._handle_play_stream_chunk],
            MessageType.PLAY_STREAM_STOP: [self._handle_play_stream_stop],
            MessageType.ACTIVITIES: [self._handle_activities],
            MessageType.USER_STREAM_SPEECH_STARTED: [self._handle_speech_started],
            MessageType.USER_STREAM_SPEECH_STOPPED: [self._handle_speech_stopped],
            MessageType.USER_STREAM_SPEECH_COMMITTED: [self._handle_speech_committed],
            MessageType.USER_STREAM_SPEECH_HYPOTHESIS: [self._handle_speech_hypothesis],
        }

        for msg_type, handler_list in handlers.items():
            for handler in handler_list:
                self.register_event_handler(msg_type.value, handler)

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """
        Register an event handler for a specific message type.

        Args:
            event_type (str): Message type to handle
            handler (Callable): Handler function to call
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        self.logger.debug(f"[MESSAGE] Registered handler for {event_type}")

    def process_message(self, message: str) -> Optional[MessageEvent]:
        """
        Process a WebSocket message.

        Args:
            message (str): Raw WebSocket message

        Returns:
            Optional[MessageEvent]: Processed message event or None if error
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if not msg_type:
                self.logger.warning(
                    f"[MESSAGE] Received message without type: {message}"
                )
                return None

            # Store received message
            self.received_messages.append(data)

            # Create message event
            event = MessageEvent(
                type=msg_type, conversation_id=data.get("conversationId"), data=data
            )

            # Log message
            self.logger.info(f"[MESSAGE] Received: {msg_type}")

            # Trigger handlers
            self._trigger_handlers(msg_type, data)

            return event

        except json.JSONDecodeError:
            self.logger.warning(f"[MESSAGE] Received non-JSON message: {message}")
            return None
        except Exception as e:
            self.logger.error(f"[MESSAGE] Error processing message: {e}")
            return None

    def _trigger_handlers(self, msg_type: str, data: Dict[str, Any]) -> None:
        """
        Trigger registered handlers for a message type.

        Args:
            msg_type (str): Message type
            data (Dict[str, Any]): Message data
        """
        if msg_type in self.event_handlers:
            for handler in self.event_handlers[msg_type]:
                try:
                    handler(data)
                except Exception as e:
                    self.logger.error(f"[MESSAGE] Handler error for {msg_type}: {e}")

    def _handle_user_stream_started(self, data: Dict[str, Any]) -> None:
        """Handle userStream.started message."""
        if self.session_manager.conversation_state:
            from .models import StreamStatus

            self.session_manager.stream_state.user_stream = StreamStatus.ACTIVE
            self.logger.info("[MESSAGE] User stream started")

    def _handle_user_stream_stopped(self, data: Dict[str, Any]) -> None:
        """Handle userStream.stopped message."""
        if self.session_manager.conversation_state:
            from .models import StreamStatus

            self.session_manager.stream_state.user_stream = StreamStatus.STOPPED
            self.logger.info("[MESSAGE] User stream stopped")

    def _handle_play_stream_start(self, data: Dict[str, Any]) -> None:
        """Handle playStream.start message."""
        if self.session_manager.conversation_state:
            from .models import StreamStatus

            self.session_manager.stream_state.play_stream = StreamStatus.ACTIVE
            self.session_manager.stream_state.current_stream_id = data.get("streamId")

            # Determine if this is greeting or response
            conv_state = self.session_manager.conversation_state
            if not conv_state.greeting_chunks and not conv_state.collecting_response:
                conv_state.collecting_greeting = True
                self.logger.info("[MESSAGE] Collecting greeting audio...")
            else:
                conv_state.collecting_response = True
                self.logger.info("[MESSAGE] Collecting response audio...")

            self.logger.info(
                f"[MESSAGE] Play stream started: {self.session_manager.stream_state.current_stream_id}"
            )

    def _handle_play_stream_chunk(self, data: Dict[str, Any]) -> None:
        """Handle playStream.chunk message."""
        if not self.session_manager.conversation_state:
            return

        audio_chunk = data.get("audioChunk")
        if not audio_chunk:
            return

        conv_state = self.session_manager.conversation_state

        if conv_state.collecting_greeting:
            conv_state.greeting_chunks.append(audio_chunk)
        elif conv_state.collecting_response:
            conv_state.response_chunks.append(audio_chunk)

        self.logger.debug(
            f"[MESSAGE] Received audio chunk ({len(audio_chunk)} bytes base64)"
        )

    def _handle_play_stream_stop(self, data: Dict[str, Any]) -> None:
        """Handle playStream.stop message."""
        if not self.session_manager.conversation_state:
            return

        conv_state = self.session_manager.conversation_state

        if conv_state.collecting_greeting:
            conv_state.collecting_greeting = False
            self.logger.info(
                f"[MESSAGE] Greeting collected: {len(conv_state.greeting_chunks)} chunks"
            )
        elif conv_state.collecting_response:
            conv_state.collecting_response = False
            self.logger.info(
                f"[MESSAGE] Response collected: {len(conv_state.response_chunks)} chunks"
            )

            from .models import StreamStatus

            self.session_manager.stream_state.play_stream = StreamStatus.STOPPED
        stream_id = self.session_manager.stream_state.current_stream_id
        self.session_manager.stream_state.current_stream_id = None

        self.logger.info(f"[MESSAGE] Play stream stopped: {stream_id}")

    def _handle_activities(self, data: Dict[str, Any]) -> None:
        """Handle activities message."""
        if not self.session_manager.conversation_state:
            return

        activities = data.get("activities", [])
        conv_state = self.session_manager.conversation_state
        conv_state.activities_received.extend(activities)
        conv_state.last_activity = activities[-1] if activities else None

        self.logger.info(f"[MESSAGE] Received activities: {len(activities)} activities")

    def _handle_speech_started(self, data: Dict[str, Any]) -> None:
        """Handle userStream.speech.started message."""
        if self.session_manager.conversation_state:
            self.session_manager.stream_state.speech_active = True
            self.logger.info("[MESSAGE] Speech started detected")

    def _handle_speech_stopped(self, data: Dict[str, Any]) -> None:
        """Handle userStream.speech.stopped message."""
        if self.session_manager.conversation_state:
            self.session_manager.stream_state.speech_active = False
            self.logger.info("[MESSAGE] Speech stopped detected")

    def _handle_speech_committed(self, data: Dict[str, Any]) -> None:
        """Handle userStream.speech.committed message."""
        if self.session_manager.conversation_state:
            self.session_manager.stream_state.speech_committed = True
            self.logger.info("[MESSAGE] Speech committed")

    def _handle_speech_hypothesis(self, data: Dict[str, Any]) -> None:
        """Handle userStream.speech.hypothesis message."""
        if self.session_manager.conversation_state:
            alternatives = data.get("alternatives", [])
            self.session_manager.stream_state.current_hypothesis = alternatives
            self.logger.info(
                f"[MESSAGE] Speech hypothesis: {len(alternatives)} alternatives"
            )

    def get_received_messages(self) -> List[Dict[str, Any]]:
        """
        Get list of received messages.

        Returns:
            List[Dict[str, Any]]: List of received messages
        """
        return self.received_messages.copy()

    def get_message_count(self) -> int:
        """
        Get count of received messages.

        Returns:
            int: Number of received messages
        """
        return len(self.received_messages)

    def clear_message_history(self) -> None:
        """Clear the message history."""
        self.received_messages.clear()
        self.logger.info("[MESSAGE] Message history cleared")

    def get_last_message(self) -> Optional[Dict[str, Any]]:
        """
        Get the last received message.

        Returns:
            Optional[Dict[str, Any]]: Last message or None if no messages
        """
        return self.received_messages[-1] if self.received_messages else None

    def get_messages_by_type(self, msg_type: str) -> List[Dict[str, Any]]:
        """
        Get all messages of a specific type.

        Args:
            msg_type (str): Message type to filter by

        Returns:
            List[Dict[str, Any]]: List of messages of the specified type
        """
        return [msg for msg in self.received_messages if msg.get("type") == msg_type]
