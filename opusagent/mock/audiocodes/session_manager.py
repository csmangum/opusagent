"""
Session management for the AudioCodes mock client.

This module provides session state management and lifecycle handling for the
AudioCodes mock client. It tracks session status, conversation state, and
provides methods for session operations.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from .models import (
    ConversationResult,
    ConversationState,
    SessionConfig,
    SessionState,
    SessionStatus,
    StreamState,
)


class SessionManager:
    """
    Session state manager for the AudioCodes mock client.

    This class manages session lifecycle, state tracking, and provides
    methods for session operations like initiation, resumption, and validation.

    Attributes:
        logger (logging.Logger): Logger instance for debugging
        config (SessionConfig): Session configuration
        session_state (SessionState): Current session state
        stream_state (StreamState): Current stream state
        conversation_state (Optional[ConversationState]): Current conversation state
    """

    def __init__(self, config: SessionConfig, logger: Optional[logging.Logger] = None):
        """
        Initialize the SessionManager.

        Args:
            config (SessionConfig): Session configuration
            logger (Optional[logging.Logger]): Logger instance for debugging
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config = config
        self.session_state = SessionState()
        self.stream_state = StreamState()
        self.conversation_state: Optional[ConversationState] = None

    def create_session(self, conversation_id: Optional[str] = None) -> str:
        """
        Create a new session with optional conversation ID.

        Args:
            conversation_id (Optional[str]): Conversation ID to use, or generate new one

        Returns:
            str: The conversation ID for this session
        """
        conv_id = conversation_id or str(uuid.uuid4())

        self.session_state.conversation_id = conv_id
        self.session_state.status = SessionStatus.CONNECTED
        self.session_state.created_at = datetime.now()

        self.conversation_state = ConversationState(conversation_id=conv_id)

        self.logger.info(f"[SESSION] Created session with conversation ID: {conv_id}")
        return conv_id

    def initiate_session(self) -> Dict[str, Any]:
        """
        Prepare session initiation message.

        Returns:
            Dict[str, Any]: Session initiation message
        """
        if not self.session_state.conversation_id:
            self.create_session()

        self.session_state.status = SessionStatus.INITIATING

        message = {
            "type": "session.initiate",
            "conversationId": self.session_state.conversation_id,
            "expectAudioMessages": self.config.expect_audio_messages,
            "botName": self.config.bot_name,
            "caller": self.config.caller,
            "supportedMediaFormats": self.config.supported_media_formats,
        }

        self.logger.info(
            f"[SESSION] Initiating session: {self.session_state.conversation_id}"
        )
        return message

    def resume_session(self, conversation_id: str) -> Dict[str, Any]:
        """
        Prepare session resume message.

        Args:
            conversation_id (str): Conversation ID to resume

        Returns:
            Dict[str, Any]: Session resume message
        """
        self.session_state.conversation_id = conversation_id
        self.session_state.status = SessionStatus.RESUMING

        message = {
            "type": "session.resume",
            "conversationId": conversation_id,
            "expectAudioMessages": self.config.expect_audio_messages,
            "botName": self.config.bot_name,
            "caller": self.config.caller,
            "supportedMediaFormats": self.config.supported_media_formats,
        }

        self.logger.info(f"[SESSION] Resuming session: {conversation_id}")
        return message

    def validate_connection(self) -> Dict[str, Any]:
        """
        Prepare connection validation message.

        Returns:
            Dict[str, Any]: Connection validation message
        """
        if not self.session_state.conversation_id:
            raise ValueError("No conversation ID available for validation")

        self.session_state.validation_pending = True

        message = {
            "type": "connection.validate",
            "conversationId": self.session_state.conversation_id,
        }

        self.logger.info(
            f"[SESSION] Validating connection: {self.session_state.conversation_id}"
        )
        return message

    def end_session(self, reason: str = "Session ended") -> Dict[str, Any]:
        """
        Prepare session end message.

        Args:
            reason (str): Reason for ending the session

        Returns:
            Dict[str, Any]: Session end message
        """
        if not self.session_state.conversation_id:
            raise ValueError("No conversation ID available for session end")

        self.session_state.status = SessionStatus.ENDED

        message = {
            "type": "session.end",
            "conversationId": self.session_state.conversation_id,
            "reasonCode": "normal",
            "reason": reason,
        }

        self.logger.info(
            f"[SESSION] Ending session: {self.session_state.conversation_id} - {reason}"
        )
        return message

    def handle_session_accepted(self, data: Dict[str, Any]) -> None:
        """
        Handle session.accepted message.

        Args:
            data (Dict[str, Any]): Session accepted message data
        """
        self.session_state.accepted = True
        self.session_state.status = SessionStatus.ACTIVE
        self.session_state.media_format = data.get(
            "mediaFormat", self.config.media_format
        )
        self.session_state.last_activity = datetime.now()

        self.logger.info(
            f"[SESSION] Session accepted with format: {self.session_state.media_format}"
        )

    def handle_session_resumed(self, data: Dict[str, Any]) -> None:
        """
        Handle session.resumed message.

        Args:
            data (Dict[str, Any]): Session resumed message data
        """
        self.session_state.resumed = True
        self.session_state.status = SessionStatus.ACTIVE
        self.session_state.last_activity = datetime.now()

        self.logger.info("[SESSION] Session resumed successfully")

    def handle_session_error(self, data: Dict[str, Any]) -> None:
        """
        Handle session.error message.

        Args:
            data (Dict[str, Any]): Session error message data
        """
        self.session_state.error = True
        self.session_state.status = SessionStatus.ERROR
        self.session_state.error_reason = data.get("reason", "Unknown error")
        self.session_state.last_activity = datetime.now()

        self.logger.error(f"[SESSION] Session error: {self.session_state.error_reason}")

    def handle_connection_validated(self, data: Dict[str, Any]) -> None:
        """
        Handle connection.validated message.

        Args:
            data (Dict[str, Any]): Connection validated message data
        """
        self.session_state.connection_validated = True
        self.session_state.validation_pending = False
        self.session_state.last_activity = datetime.now()

        self.logger.info("[SESSION] Connection validated")

    def send_dtmf_event(self, digit: str) -> Dict[str, Any]:
        """
        Prepare DTMF event message.

        Args:
            digit (str): DTMF digit to send

        Returns:
            Dict[str, Any]: DTMF event message
        """
        if not self.session_state.conversation_id:
            raise ValueError("No conversation ID available for DTMF event")

        message = {
            "type": "activities",
            "conversationId": self.session_state.conversation_id,
            "activities": [{"type": "event", "name": "dtmf", "value": digit}],
        }

        self.logger.info(f"[SESSION] Sending DTMF event: {digit}")
        return message

    def send_hangup_event(self) -> Dict[str, Any]:
        """
        Prepare hangup event message.

        Returns:
            Dict[str, Any]: Hangup event message
        """
        if not self.session_state.conversation_id:
            raise ValueError("No conversation ID available for hangup event")

        message = {
            "type": "activities",
            "conversationId": self.session_state.conversation_id,
            "activities": [{"type": "event", "name": "hangup"}],
        }

        self.logger.info("[SESSION] Sending hangup event")
        return message

    def send_custom_activity(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare custom activity message.

        Args:
            activity (Dict[str, Any]): Custom activity data

        Returns:
            Dict[str, Any]: Custom activity message
        """
        if not self.session_state.conversation_id:
            raise ValueError("No conversation ID available for custom activity")

        message = {
            "type": "activities",
            "conversationId": self.session_state.conversation_id,
            "activities": [activity],
        }

        self.logger.info(f"[SESSION] Sending custom activity: {activity}")
        return message

    def reset_session_state(self) -> None:
        """Reset all session-related state variables."""
        self.session_state = SessionState()
        self.stream_state = StreamState()
        self.conversation_state = None

        self.logger.info("[SESSION] Session state reset")

    def get_session_status(self) -> Dict[str, Any]:
        """
        Get current session status information.

        Returns:
            Dict[str, Any]: Session status information
        """
        return {
            "conversation_id": self.session_state.conversation_id,
            "status": self.session_state.status.value,
            "accepted": self.session_state.accepted,
            "resumed": self.session_state.resumed,
            "error": self.session_state.error,
            "error_reason": self.session_state.error_reason,
            "connection_validated": self.session_state.connection_validated,
            "validation_pending": self.session_state.validation_pending,
            "media_format": self.session_state.media_format,
            "user_stream_active": self.stream_state.user_stream.value == "active",
            "play_stream_active": self.stream_state.play_stream.value == "active",
            "speech_active": self.stream_state.speech_active,
            "speech_committed": self.stream_state.speech_committed,
            "created_at": (
                self.session_state.created_at.isoformat()
                if self.session_state.created_at
                else None
            ),
            "last_activity": (
                self.session_state.last_activity.isoformat()
                if self.session_state.last_activity
                else None
            ),
            "conversation_turn_count": (
                self.conversation_state.turn_count if self.conversation_state else 0
            ),
            "activities_count": (
                len(self.conversation_state.activities_received)
                if self.conversation_state
                else 0
            ),
        }

    def is_session_active(self) -> bool:
        """
        Check if the session is currently active.

        Returns:
            bool: True if session is active, False otherwise
        """
        return (
            self.session_state.status in [SessionStatus.ACTIVE]
            and self.session_state.accepted
            and not self.session_state.error
        )

    def is_connected(self) -> bool:
        """
        Check if the session is connected.

        Returns:
            bool: True if connected, False otherwise
        """
        return self.session_state.status != SessionStatus.DISCONNECTED

    def get_conversation_id(self) -> Optional[str]:
        """
        Get the current conversation ID.

        Returns:
            Optional[str]: Current conversation ID or None
        """
        return self.session_state.conversation_id
