"""
Unit tests for AudioCodes mock client session manager.

This module tests the session state management and lifecycle handling
for the AudioCodes mock client.
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from opusagent.local.audiocodes.models import (
    ConversationState,
    SessionConfig,
    SessionStatus,
    StreamStatus,
)
from opusagent.local.audiocodes.session_manager import SessionManager


class TestSessionManager:
    """Test SessionManager class."""

    @pytest.fixture
    def config(self):
        """Create a test session configuration."""
        return SessionConfig(
            bridge_url="ws://localhost:8080", bot_name="TestBot", caller="+15551234567"
        )

    @pytest.fixture
    def session_manager(self, config):
        """Create a test session manager."""
        return SessionManager(config)

    def test_session_manager_initialization(self, session_manager, config):
        """Test SessionManager initialization."""
        assert session_manager.config == config
        assert session_manager.session_state.status == SessionStatus.DISCONNECTED
        assert session_manager.stream_state.user_stream == StreamStatus.INACTIVE
        assert session_manager.conversation_state is None

    def test_create_session_with_generated_id(self, session_manager):
        """Test creating a session with auto-generated conversation ID."""
        conv_id = session_manager.create_session()

        assert conv_id is not None
        assert len(conv_id) > 0
        assert session_manager.session_state.conversation_id == conv_id
        assert session_manager.session_state.status == SessionStatus.CONNECTED
        assert session_manager.conversation_state is not None
        assert session_manager.conversation_state.conversation_id == conv_id

    def test_create_session_with_custom_id(self, session_manager):
        """Test creating a session with custom conversation ID."""
        custom_id = "test-conversation-123"
        conv_id = session_manager.create_session(custom_id)

        assert conv_id == custom_id
        assert session_manager.session_state.conversation_id == custom_id
        assert session_manager.conversation_state.conversation_id == custom_id

    def test_initiate_session_message(self, session_manager):
        """Test session initiation message creation."""
        conv_id = session_manager.create_session("test-123")
        message = session_manager.initiate_session()

        assert message["type"] == "session.initiate"
        assert message["conversationId"] == conv_id
        assert message["botName"] == "TestBot"
        assert message["caller"] == "+15551234567"
        assert message["expectAudioMessages"] is True
        assert message["supportedMediaFormats"] == ["raw/lpcm16"]
        assert session_manager.session_state.status == SessionStatus.INITIATING

    def test_initiate_session_auto_create(self, session_manager):
        """Test session initiation auto-creates session if needed."""
        message = session_manager.initiate_session()

        assert message["type"] == "session.initiate"
        assert message["conversationId"] is not None
        assert session_manager.session_state.conversation_id is not None

    def test_resume_session_message(self, session_manager):
        """Test session resume message creation."""
        conv_id = "resume-test-123"
        message = session_manager.resume_session(conv_id)

        assert message["type"] == "session.resume"
        assert message["conversationId"] == conv_id
        assert message["botName"] == "TestBot"
        assert message["caller"] == "+15551234567"
        assert session_manager.session_state.status == SessionStatus.RESUMING
        assert session_manager.session_state.conversation_id == conv_id

    def test_validate_connection_message(self, session_manager):
        """Test connection validation message creation."""
        conv_id = session_manager.create_session("validate-test-123")
        message = session_manager.validate_connection()

        assert message["type"] == "connection.validate"
        assert message["conversationId"] == conv_id
        assert session_manager.session_state.validation_pending is True

    def test_validate_connection_no_conversation_id(self, session_manager):
        """Test connection validation without conversation ID raises error."""
        with pytest.raises(ValueError, match="No conversation ID available"):
            session_manager.validate_connection()

    def test_end_session_message(self, session_manager):
        """Test session end message creation."""
        conv_id = session_manager.create_session("end-test-123")
        reason = "Test completed"
        message = session_manager.end_session(reason)

        assert message["type"] == "session.end"
        assert message["conversationId"] == conv_id
        assert message["reasonCode"] == "normal"
        assert message["reason"] == reason
        assert session_manager.session_state.status == SessionStatus.ENDED

    def test_end_session_no_conversation_id(self, session_manager):
        """Test session end without conversation ID raises error."""
        with pytest.raises(ValueError, match="No conversation ID available"):
            session_manager.end_session("Test")

    def test_handle_session_accepted(self, session_manager):
        """Test handling session.accepted message."""
        conv_id = session_manager.create_session("accept-test-123")
        data = {"conversationId": conv_id, "mediaFormat": "raw/lpcm8"}

        session_manager.handle_session_accepted(data)

        assert session_manager.session_state.accepted is True
        assert session_manager.session_state.status == SessionStatus.ACTIVE
        assert session_manager.session_state.media_format == "raw/lpcm8"
        assert session_manager.session_state.last_activity is not None

    def test_handle_session_accepted_default_format(self, session_manager):
        """Test handling session.accepted with default media format."""
        conv_id = session_manager.create_session("accept-default-test-123")
        data = {"conversationId": conv_id}

        session_manager.handle_session_accepted(data)

        assert session_manager.session_state.media_format == "raw/lpcm16"

    def test_handle_session_resumed(self, session_manager):
        """Test handling session.resumed message."""
        conv_id = session_manager.create_session("resume-test-123")
        data = {"conversationId": conv_id}

        session_manager.handle_session_resumed(data)

        assert session_manager.session_state.resumed is True
        assert session_manager.session_state.status == SessionStatus.ACTIVE
        assert session_manager.session_state.last_activity is not None

    def test_handle_session_error(self, session_manager):
        """Test handling session.error message."""
        conv_id = session_manager.create_session("error-test-123")
        data = {"conversationId": conv_id, "reason": "Test error message"}

        session_manager.handle_session_error(data)

        assert session_manager.session_state.error is True
        assert session_manager.session_state.status == SessionStatus.ERROR
        assert session_manager.session_state.error_reason == "Test error message"
        assert session_manager.session_state.last_activity is not None

    def test_handle_session_error_default_reason(self, session_manager):
        """Test handling session.error with default reason."""
        conv_id = session_manager.create_session("error-default-test-123")
        data = {"conversationId": conv_id}

        session_manager.handle_session_error(data)

        assert session_manager.session_state.error_reason == "Unknown error"

    def test_handle_connection_validated(self, session_manager):
        """Test handling connection.validated message."""
        conv_id = session_manager.create_session("validate-test-123")
        session_manager.session_state.validation_pending = True
        data = {"conversationId": conv_id}

        session_manager.handle_connection_validated(data)

        assert session_manager.session_state.connection_validated is True
        assert session_manager.session_state.validation_pending is False
        assert session_manager.session_state.last_activity is not None

    def test_send_dtmf_event(self, session_manager):
        """Test DTMF event message creation."""
        conv_id = session_manager.create_session("dtmf-test-123")
        message = session_manager.send_dtmf_event("5")

        assert message["type"] == "activities"
        assert message["conversationId"] == conv_id
        assert len(message["activities"]) == 1
        assert message["activities"][0]["type"] == "event"
        assert message["activities"][0]["name"] == "dtmf"
        assert message["activities"][0]["value"] == "5"

    def test_send_dtmf_event_no_conversation_id(self, session_manager):
        """Test DTMF event without conversation ID raises error."""
        with pytest.raises(ValueError, match="No conversation ID available"):
            session_manager.send_dtmf_event("1")

    def test_send_hangup_event(self, session_manager):
        """Test hangup event message creation."""
        conv_id = session_manager.create_session("hangup-test-123")
        message = session_manager.send_hangup_event()

        assert message["type"] == "activities"
        assert message["conversationId"] == conv_id
        assert len(message["activities"]) == 1
        assert message["activities"][0]["type"] == "event"
        assert message["activities"][0]["name"] == "hangup"

    def test_send_hangup_event_no_conversation_id(self, session_manager):
        """Test hangup event without conversation ID raises error."""
        with pytest.raises(ValueError, match="No conversation ID available"):
            session_manager.send_hangup_event()

    def test_send_custom_activity(self, session_manager):
        """Test custom activity message creation."""
        conv_id = session_manager.create_session("custom-test-123")
        activity = {"type": "event", "name": "custom_event", "value": "test_value"}
        message = session_manager.send_custom_activity(activity)

        assert message["type"] == "activities"
        assert message["conversationId"] == conv_id
        assert len(message["activities"]) == 1
        assert message["activities"][0] == activity

    def test_send_custom_activity_no_conversation_id(self, session_manager):
        """Test custom activity without conversation ID raises error."""
        activity = {"type": "event", "name": "test"}
        with pytest.raises(ValueError, match="No conversation ID available"):
            session_manager.send_custom_activity(activity)

    def test_reset_session_state(self, session_manager):
        """Test resetting session state."""
        # Set up some state
        conv_id = session_manager.create_session("reset-test-123")
        session_manager.session_state.accepted = True
        session_manager.stream_state.user_stream = StreamStatus.ACTIVE

        # Reset state
        session_manager.reset_session_state()

        assert session_manager.session_state.status == SessionStatus.DISCONNECTED
        assert session_manager.session_state.accepted is False
        assert session_manager.session_state.conversation_id is None
        assert session_manager.stream_state.user_stream == StreamStatus.INACTIVE
        assert session_manager.conversation_state is None

    def test_get_session_status(self, session_manager):
        """Test getting session status information."""
        conv_id = session_manager.create_session("status-test-123")
        session_manager.session_state.accepted = True
        session_manager.session_state.connection_validated = True
        session_manager.stream_state.user_stream = StreamStatus.ACTIVE

        status = session_manager.get_session_status()

        assert status["conversation_id"] == conv_id
        assert status["status"] == SessionStatus.CONNECTED.value
        assert status["accepted"] is True
        assert status["connection_validated"] is True
        assert status["user_stream_active"] is True
        assert status["play_stream_active"] is False
        assert status["speech_active"] is False
        assert status["conversation_turn_count"] == 0
        assert status["activities_count"] == 0
        assert status["created_at"] is not None

    def test_is_session_active(self, session_manager):
        """Test session active status check."""
        # Initially not active
        assert session_manager.is_session_active() is False

        # Create and accept session
        session_manager.create_session("active-test-123")
        session_manager.session_state.accepted = True
        session_manager.session_state.status = SessionStatus.ACTIVE

        assert session_manager.is_session_active() is True

        # Error state should not be active
        session_manager.session_state.error = True
        assert session_manager.is_session_active() is False

    def test_is_connected(self, session_manager):
        """Test connection status check."""
        # Initially disconnected
        assert session_manager.is_connected() is False

        # Create session (sets status to CONNECTED)
        session_manager.create_session("connect-test-123")
        assert session_manager.is_connected() is True

        # Reset to disconnected
        session_manager.session_state.status = SessionStatus.DISCONNECTED
        assert session_manager.is_connected() is False

    def test_get_conversation_id(self, session_manager):
        """Test getting conversation ID."""
        # Initially None
        assert session_manager.get_conversation_id() is None

        # After creating session
        conv_id = session_manager.create_session("conv-test-123")
        assert session_manager.get_conversation_id() == conv_id
