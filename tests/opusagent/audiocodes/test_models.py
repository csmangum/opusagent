"""
Unit tests for AudioCodes mock client models.

This module tests the data models, enums, and validation logic
used throughout the AudioCodes mock client system.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from opusagent.mock.audiocodes.models import (
    SessionStatus,
    StreamStatus,
    MessageType,
    SessionConfig,
    SessionState,
    StreamState,
    AudioChunk,
    MessageEvent,
    ConversationState,
    ConversationResult,
)


class TestSessionStatus:
    """Test SessionStatus enum."""

    def test_session_status_values(self):
        """Test that SessionStatus has expected values."""
        assert SessionStatus.DISCONNECTED == "disconnected"
        assert SessionStatus.CONNECTING == "connecting"
        assert SessionStatus.CONNECTED == "connected"
        assert SessionStatus.INITIATING == "initiating"
        assert SessionStatus.ACTIVE == "active"
        assert SessionStatus.RESUMING == "resuming"
        assert SessionStatus.ERROR == "error"
        assert SessionStatus.ENDED == "ended"

    def test_session_status_enumeration(self):
        """Test that SessionStatus can be enumerated."""
        statuses = list(SessionStatus)
        assert len(statuses) == 8
        assert SessionStatus.DISCONNECTED in statuses
        assert SessionStatus.ACTIVE in statuses


class TestStreamStatus:
    """Test StreamStatus enum."""

    def test_stream_status_values(self):
        """Test that StreamStatus has expected values."""
        assert StreamStatus.INACTIVE == "inactive"
        assert StreamStatus.STARTING == "starting"
        assert StreamStatus.ACTIVE == "active"
        assert StreamStatus.STOPPING == "stopping"
        assert StreamStatus.STOPPED == "stopped"

    def test_stream_status_enumeration(self):
        """Test that StreamStatus can be enumerated."""
        statuses = list(StreamStatus)
        assert len(statuses) == 5
        assert StreamStatus.INACTIVE in statuses
        assert StreamStatus.ACTIVE in statuses


class TestMessageType:
    """Test MessageType enum."""

    def test_message_type_values(self):
        """Test that MessageType has expected values."""
        # Session messages
        assert MessageType.SESSION_INITIATE == "session.initiate"
        assert MessageType.SESSION_ACCEPTED == "session.accepted"
        assert MessageType.SESSION_ERROR == "session.error"
        
        # Stream messages
        assert MessageType.USER_STREAM_START == "userStream.start"
        assert MessageType.PLAY_STREAM_CHUNK == "playStream.chunk"
        
        # Activity messages
        assert MessageType.ACTIVITIES == "activities"

    def test_message_type_enumeration(self):
        """Test that MessageType can be enumerated."""
        types = list(MessageType)
        assert len(types) > 10  # Should have many message types
        assert MessageType.SESSION_INITIATE in types
        assert MessageType.ACTIVITIES in types


class TestSessionConfig:
    """Test SessionConfig model."""

    def test_session_config_defaults(self):
        """Test SessionConfig with default values."""
        config = SessionConfig(bridge_url="ws://localhost:8080")
        
        assert config.bridge_url == "ws://localhost:8080"
        assert config.bot_name == "TestBot"
        assert config.caller == "+15551234567"
        assert config.media_format == "raw/lpcm16"
        assert config.supported_media_formats == ["raw/lpcm16"]
        assert config.expect_audio_messages is True

    def test_session_config_custom_values(self):
        """Test SessionConfig with custom values."""
        config = SessionConfig(
            bridge_url="wss://example.com:8080",
            bot_name="CustomBot",
            caller="+1234567890",
            media_format="raw/lpcm8",
            supported_media_formats=["raw/lpcm8", "raw/lpcm16"],
            expect_audio_messages=False
        )
        
        assert config.bridge_url == "wss://example.com:8080"
        assert config.bot_name == "CustomBot"
        assert config.caller == "+1234567890"
        assert config.media_format == "raw/lpcm8"
        assert config.supported_media_formats == ["raw/lpcm8", "raw/lpcm16"]
        assert config.expect_audio_messages is False

    def test_session_config_bridge_url_validation(self):
        """Test SessionConfig bridge URL validation."""
        # Valid URLs
        SessionConfig(bridge_url="ws://localhost:8080")
        SessionConfig(bridge_url="wss://example.com:8080")
        
        # Invalid URLs
        with pytest.raises(ValidationError):
            SessionConfig(bridge_url="http://localhost:8080")
        
        with pytest.raises(ValidationError):
            SessionConfig(bridge_url="ftp://localhost:8080")
        
        with pytest.raises(ValidationError):
            SessionConfig(bridge_url="invalid-url")


class TestSessionState:
    """Test SessionState model."""

    def test_session_state_defaults(self):
        """Test SessionState with default values."""
        state = SessionState()
        
        assert state.conversation_id is None
        assert state.status == SessionStatus.DISCONNECTED
        assert state.accepted is False
        assert state.resumed is False
        assert state.error is False
        assert state.error_reason is None
        assert state.media_format == "raw/lpcm16"
        assert state.connection_validated is False
        assert state.validation_pending is False
        assert isinstance(state.created_at, datetime)

    def test_session_state_custom_values(self):
        """Test SessionState with custom values."""
        state = SessionState(
            conversation_id="test-conv-123",
            status=SessionStatus.ACTIVE,
            accepted=True,
            media_format="raw/lpcm8",
            error_reason="Test error"
        )
        
        assert state.conversation_id == "test-conv-123"
        assert state.status == SessionStatus.ACTIVE
        assert state.accepted is True
        assert state.media_format == "raw/lpcm8"
        assert state.error_reason == "Test error"

    def test_session_state_assignment(self):
        """Test SessionState field assignment."""
        state = SessionState()
        
        # Test assignment (should work due to validate_assignment=False)
        state.status = SessionStatus.ACTIVE
        state.accepted = True
        state.conversation_id = "new-conv-id"
        
        assert state.status == SessionStatus.ACTIVE
        assert state.accepted is True
        assert state.conversation_id == "new-conv-id"


class TestStreamState:
    """Test StreamState model."""

    def test_stream_state_defaults(self):
        """Test StreamState with default values."""
        state = StreamState()
        
        assert state.user_stream == StreamStatus.INACTIVE
        assert state.play_stream == StreamStatus.INACTIVE
        assert state.current_stream_id is None
        assert state.speech_active is False
        assert state.speech_committed is False
        assert state.current_hypothesis is None

    def test_stream_state_custom_values(self):
        """Test StreamState with custom values."""
        hypothesis = [{"text": "test", "confidence": 0.9}]
        state = StreamState(
            user_stream=StreamStatus.ACTIVE,
            play_stream=StreamStatus.STARTING,
            current_stream_id="stream-123",
            speech_active=True,
            current_hypothesis=hypothesis
        )
        
        assert state.user_stream == StreamStatus.ACTIVE
        assert state.play_stream == StreamStatus.STARTING
        assert state.current_stream_id == "stream-123"
        assert state.speech_active is True
        assert state.current_hypothesis == hypothesis


class TestAudioChunk:
    """Test AudioChunk model."""

    def test_audio_chunk_valid(self):
        """Test AudioChunk with valid data."""
        chunk = AudioChunk(
            data="dGVzdCBhdWRpbyBkYXRh",  # base64 encoded "test audio data"
            chunk_index=1,
            size_bytes=16
        )
        
        assert chunk.data == "dGVzdCBhdWRpbyBkYXRh"
        assert chunk.chunk_index == 1
        assert chunk.size_bytes == 16
        assert isinstance(chunk.timestamp, datetime)

    def test_audio_chunk_empty_data_validation(self):
        """Test AudioChunk validation with empty data."""
        with pytest.raises(ValidationError):
            AudioChunk(
                data="",
                chunk_index=1,
                size_bytes=16
            )

    def test_audio_chunk_none_data_validation(self):
        """Test AudioChunk validation with None data."""
        with pytest.raises(ValidationError):
            AudioChunk(
                data=None,  # type: ignore  # Actually test with None
                chunk_index=1,
                size_bytes=16
            )


class TestMessageEvent:
    """Test MessageEvent model."""

    def test_message_event_valid(self):
        """Test MessageEvent with valid data."""
        event = MessageEvent(
            type=MessageType.SESSION_ACCEPTED,
            conversation_id="conv-123",
            data={"test": "data"}
        )
        
        assert event.type == MessageType.SESSION_ACCEPTED
        assert event.conversation_id == "conv-123"
        assert event.data == {"test": "data"}
        assert isinstance(event.timestamp, datetime)

    def test_message_event_string_type(self):
        """Test MessageEvent with string message type."""
        event = MessageEvent(
            type=MessageType.SESSION_ACCEPTED,  # Use enum instead of string
            conversation_id="conv-123"
        )
        
        assert event.type == MessageType.SESSION_ACCEPTED

    def test_message_event_invalid_type(self):
        """Test MessageEvent with invalid message type."""
        with pytest.raises(ValidationError):
            MessageEvent(
                type="invalid.message.type",  # type: ignore  # Use invalid string that's not in MessageType enum
                conversation_id="conv-123"
            )


class TestConversationState:
    """Test ConversationState model."""

    def test_conversation_state_defaults(self):
        """Test ConversationState with default values."""
        state = ConversationState(conversation_id="conv-123")
        
        assert state.conversation_id == "conv-123"
        assert state.turn_count == 0
        assert state.turns == []
        assert state.greeting_chunks == []
        assert state.response_chunks == []
        assert state.collecting_greeting is False
        assert state.collecting_response is False
        assert state.activities_received == []
        assert state.last_activity is None
        assert isinstance(state.started_at, datetime)
        assert state.last_turn_at is None

    def test_conversation_state_custom_values(self):
        """Test ConversationState with custom values."""
        activities = [{"type": "event", "name": "test"}]
        state = ConversationState(
            conversation_id="conv-456",
            turn_count=5,
            greeting_chunks=["chunk1", "chunk2"],
            activities_received=activities
        )
        
        assert state.conversation_id == "conv-456"
        assert state.turn_count == 5
        assert state.greeting_chunks == ["chunk1", "chunk2"]
        assert state.activities_received == activities


class TestConversationResult:
    """Test ConversationResult model."""

    def test_conversation_result_defaults(self):
        """Test ConversationResult with default values."""
        result = ConversationResult(total_turns=3)
        
        assert result.total_turns == 3
        assert result.completed_turns == 0
        assert result.greeting_received is False
        assert result.greeting_chunks == 0
        assert result.success is False
        assert result.error is None
        assert result.turns == []
        assert isinstance(result.start_time, datetime)
        assert result.end_time is None

    def test_conversation_result_custom_values(self):
        """Test ConversationResult with custom values."""
        turns = [{"turn_number": 1, "success": True}]
        result = ConversationResult(
            total_turns=2,
            completed_turns=1,
            greeting_received=True,
            greeting_chunks=5,
            success=True,
            turns=turns
        )
        
        assert result.total_turns == 2
        assert result.completed_turns == 1
        assert result.greeting_received is True
        assert result.greeting_chunks == 5
        assert result.success is True
        assert result.turns == turns

    def test_conversation_result_duration_property(self):
        """Test ConversationResult duration property."""
        from datetime import timedelta
        
        result = ConversationResult(total_turns=1)
        result.end_time = result.start_time + timedelta(seconds=5.5)
        
        assert result.duration == 5.5

    def test_conversation_result_duration_none(self):
        """Test ConversationResult duration property when end_time is None."""
        result = ConversationResult(total_turns=1)
        
        assert result.duration is None

    def test_conversation_result_success_rate_property(self):
        """Test ConversationResult success_rate property."""
        result = ConversationResult(
            total_turns=4,
            completed_turns=3
        )
        
        assert result.success_rate == 75.0

    def test_conversation_result_success_rate_zero_turns(self):
        """Test ConversationResult success_rate property with zero turns."""
        result = ConversationResult(total_turns=0)
        
        assert result.success_rate == 0.0

    def test_conversation_result_success_rate_all_completed(self):
        """Test ConversationResult success_rate property with all turns completed."""
        result = ConversationResult(
            total_turns=2,
            completed_turns=2
        )
        
        assert result.success_rate == 100.0 