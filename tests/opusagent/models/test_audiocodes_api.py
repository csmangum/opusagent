"""
Unit tests for the message schemas.

These tests validate that the Pydantic models correctly validate message data
and that the validation rules work as expected.
"""

import base64

import pytest
from pydantic import ValidationError

from opusagent.models.audiocodes_api import (
    ActivitiesMessage,
    ActivityEvent,
    BaseMessage,
    ConnectionValidatedResponse,
    ConnectionValidateMessage,
    PlayStreamChunkMessage,
    PlayStreamStartMessage,
    PlayStreamStopMessage,
    SessionAcceptedResponse,
    SessionEndMessage,
    SessionErrorResponse,
    SessionInitiateMessage,
    SessionResumeMessage,
    TelephonyEventType,
    UserStreamChunkMessage,
    UserStreamHypothesisResponse,
    UserStreamSpeechCommittedResponse,
    UserStreamSpeechStartedResponse,
    UserStreamSpeechStoppedResponse,
    UserStreamStartedResponse,
    UserStreamStartMessage,
    UserStreamStopMessage,
    UserStreamStoppedResponse,
)


class TestBaseMessage:
    """Tests for the BaseMessage class."""

    def test_valid_base_message(self):
        """Test that a valid base message can be created."""
        message = BaseMessage(
            type="test.message", conversationId=None, participant="caller"
        )
        assert message.type == "test.message"
        assert message.conversationId is None

    def test_valid_base_message_with_conversation_id(self):
        """Test that a base message with a conversation ID can be created."""
        message = BaseMessage(
            type="test.message",
            conversationId="550e8400-e29b-41d4-a716-446655440000",
            participant="caller",
        )
        assert message.type == "test.message"
        assert message.conversationId == "550e8400-e29b-41d4-a716-446655440000"

    def test_valid_base_message_with_participant(self):
        """Test that a base message with participant field can be created."""
        message = BaseMessage(
            type="test.message",
            conversationId="550e8400-e29b-41d4-a716-446655440000",
            participant="caller",
        )
        assert message.type == "test.message"
        assert message.conversationId == "550e8400-e29b-41d4-a716-446655440000"
        assert message.participant == "caller"

    def test_missing_type(self):
        """Test that a message without a type raises a validation error."""
        with pytest.raises(ValidationError):
            BaseMessage(type="", conversationId="test-id", participant="caller")


class TestSessionMessages:
    """Tests for session-related message models."""

    def test_valid_session_initiate(self):
        """Test that a valid session.initiate message can be created."""
        message = SessionInitiateMessage(
            type=TelephonyEventType.SESSION_INITIATE,
            conversationId="550e8400-e29b-41d4-a716-446655440000",
            expectAudioMessages=True,
            botName="TestBot",
            caller="+12345678901",
            supportedMediaFormats=["raw/lpcm16", "wav/lpcm16"],
            participant="caller",
        )
        assert message.type == TelephonyEventType.SESSION_INITIATE
        assert message.expectAudioMessages is True
        assert message.botName == "TestBot"
        assert message.caller == "+12345678901"
        assert "raw/lpcm16" in message.supportedMediaFormats

    def test_valid_session_initiate_with_new_formats(self):
        """Test that a valid session.initiate message with new media formats can be created."""
        message = SessionInitiateMessage(
            type=TelephonyEventType.SESSION_INITIATE,
            conversationId="550e8400-e29b-41d4-a716-446655440000",
            expectAudioMessages=True,
            botName="TestBot",
            caller="+12345678901",
            supportedMediaFormats=["raw/lpcm16_24", "wav/lpcm16_24"],
            participant="caller",
        )
        assert message.type == TelephonyEventType.SESSION_INITIATE
        assert message.expectAudioMessages is True
        assert message.botName == "TestBot"
        assert message.caller == "+12345678901"
        assert "raw/lpcm16_24" in message.supportedMediaFormats
        assert "wav/lpcm16_24" in message.supportedMediaFormats

    def test_valid_session_initiate_with_mulaw_formats(self):
        """Test that a valid session.initiate message with mulaw formats can be created."""
        message = SessionInitiateMessage(
            type=TelephonyEventType.SESSION_INITIATE,
            conversationId="550e8400-e29b-41d4-a716-446655440000",
            expectAudioMessages=True,
            botName="TestBot",
            caller="+12345678901",
            supportedMediaFormats=["raw/mulaw", "wav/mulaw"],
            participant="caller",
        )
        assert message.type == TelephonyEventType.SESSION_INITIATE
        assert message.expectAudioMessages is True
        assert message.botName == "TestBot"
        assert message.caller == "+12345678901"
        assert "raw/mulaw" in message.supportedMediaFormats
        assert "wav/mulaw" in message.supportedMediaFormats

    def test_invalid_session_initiate_no_formats(self):
        """Test that a session.initiate without supported formats raises an error."""
        with pytest.raises(ValidationError):
            SessionInitiateMessage(
                type=TelephonyEventType.SESSION_INITIATE,
                conversationId="550e8400-e29b-41d4-a716-446655440000",
                expectAudioMessages=True,
                botName="TestBot",
                caller="+12345678901",
                supportedMediaFormats=[],
                participant="caller",
            )

    def test_invalid_session_initiate_unsupported_format(self):
        """Test that a session.initiate with only unsupported formats raises an error."""
        with pytest.raises(ValidationError):
            SessionInitiateMessage(
                type=TelephonyEventType.SESSION_INITIATE,
                conversationId="550e8400-e29b-41d4-a716-446655440000",
                expectAudioMessages=True,
                botName="TestBot",
                caller="+12345678901",
                supportedMediaFormats=["invalid/format"],
                participant="caller",
            )

    def test_valid_session_accepted(self):
        """Test that a valid session.accepted response can be created."""
        response = SessionAcceptedResponse(
            type=TelephonyEventType.SESSION_ACCEPTED,
            conversationId="550e8400-e29b-41d4-a716-446655440000",
            mediaFormat="raw/lpcm16",
            participant="caller",
        )
        assert response.type == TelephonyEventType.SESSION_ACCEPTED
        assert response.mediaFormat == "raw/lpcm16"

    def test_invalid_session_accepted_format(self):
        """Test that a session.accepted with invalid format raises an error."""
        with pytest.raises(ValidationError):
            SessionAcceptedResponse(
                type=TelephonyEventType.SESSION_ACCEPTED,
                conversationId="550e8400-e29b-41d4-a716-446655440000",
                mediaFormat="invalid/format",
                participant="caller",
            )


class TestVADSpeechEvents:
    """Tests for Voice Activity Detection (VAD) speech event models."""

    def test_valid_speech_started_response(self):
        """Test that a valid speech started response can be created."""
        response = UserStreamSpeechStartedResponse(
            **{
                "type": TelephonyEventType.USER_STREAM_SPEECH_STARTED,
                "conversationId": "550e8400-e29b-41d4-a716-446655440000",
                "participant": "caller",
            }
        )
        assert response.type == TelephonyEventType.USER_STREAM_SPEECH_STARTED
        assert response.conversationId == "550e8400-e29b-41d4-a716-446655440000"
        assert response.participantId is None

    def test_valid_speech_started_response_with_participant(self):
        """Test that a valid speech started response with participant can be created."""
        response = UserStreamSpeechStartedResponse(
            **{
                "type": TelephonyEventType.USER_STREAM_SPEECH_STARTED,
                "conversationId": "550e8400-e29b-41d4-a716-446655440000",
                "participantId": "agent",
                "participant": "caller",
            }
        )
        assert response.type == TelephonyEventType.USER_STREAM_SPEECH_STARTED
        assert response.conversationId == "550e8400-e29b-41d4-a716-446655440000"
        assert response.participantId == "agent"

    def test_valid_speech_stopped_response(self):
        """Test that a valid speech stopped response can be created."""
        response = UserStreamSpeechStoppedResponse(
            **{
                "type": TelephonyEventType.USER_STREAM_SPEECH_STOPPED,
                "conversationId": "550e8400-e29b-41d4-a716-446655440000",
            }
        )
        assert response.type == TelephonyEventType.USER_STREAM_SPEECH_STOPPED
        assert response.conversationId == "550e8400-e29b-41d4-a716-446655440000"
        assert response.participantId is None

    def test_valid_speech_stopped_response_with_participant(self):
        """Test that a valid speech stopped response with participant can be created."""
        response = UserStreamSpeechStoppedResponse(
            **{
                "type": TelephonyEventType.USER_STREAM_SPEECH_STOPPED,
                "conversationId": "550e8400-e29b-41d4-a716-446655440000",
                "participantId": "agent",
            }
        )
        assert response.type == TelephonyEventType.USER_STREAM_SPEECH_STOPPED
        assert response.conversationId == "550e8400-e29b-41d4-a716-446655440000"
        assert response.participantId == "agent"

    def test_valid_speech_committed_response(self):
        """Test that a valid speech committed response can be created."""
        response = UserStreamSpeechCommittedResponse(
            **{
                "type": TelephonyEventType.USER_STREAM_SPEECH_COMMITTED,
                "conversationId": "550e8400-e29b-41d4-a716-446655440000",
            }
        )
        assert response.type == TelephonyEventType.USER_STREAM_SPEECH_COMMITTED
        assert response.conversationId == "550e8400-e29b-41d4-a716-446655440000"
        assert response.participantId is None

    def test_valid_speech_committed_response_with_participant(self):
        """Test that a valid speech committed response with participant can be created."""
        response = UserStreamSpeechCommittedResponse(
            **{
                "type": TelephonyEventType.USER_STREAM_SPEECH_COMMITTED,
                "conversationId": "550e8400-e29b-41d4-a716-446655440000",
                "participantId": "agent",
            }
        )
        assert response.type == TelephonyEventType.USER_STREAM_SPEECH_COMMITTED
        assert response.conversationId == "550e8400-e29b-41d4-a716-446655440000"
        assert response.participantId == "agent"


class TestStreamMessages:
    """Tests for stream-related message models."""

    def test_valid_user_stream_start_with_participant(self):
        """Test that a valid userStream.start message with participant can be created."""
        message = UserStreamStartMessage(
            type=TelephonyEventType.USER_STREAM_START,
            conversationId="550e8400-e29b-41d4-a716-446655440000",
            participant="caller",
        )
        assert message.type == TelephonyEventType.USER_STREAM_START
        assert message.conversationId == "550e8400-e29b-41d4-a716-446655440000"
        assert message.participant == "caller"

    def test_valid_user_stream_chunk_with_participant(self):
        """Test that a valid userStream.chunk message with participant can be created."""
        audio_data = base64.b64encode(b"test audio data").decode("utf-8")
        message = UserStreamChunkMessage(
            type=TelephonyEventType.USER_STREAM_CHUNK,
            conversationId="550e8400-e29b-41d4-a716-446655440000",
            audioChunk=audio_data,
            participant="caller",
        )
        assert message.type == TelephonyEventType.USER_STREAM_CHUNK
        assert message.audioChunk == audio_data
        assert message.participant == "caller"

    def test_valid_user_stream_stop_with_participant(self):
        """Test that a valid userStream.stop message with participant can be created."""
        message = UserStreamStopMessage(
            type=TelephonyEventType.USER_STREAM_STOP,
            conversationId="550e8400-e29b-41d4-a716-446655440000",
            participant="caller",
        )
        assert message.type == TelephonyEventType.USER_STREAM_STOP
        assert message.conversationId == "550e8400-e29b-41d4-a716-446655440000"
        assert message.participant == "caller"

    def test_valid_user_stream_started_with_participant(self):
        """Test that a valid userStream.started response with participant can be created."""
        response = UserStreamStartedResponse(
            type=TelephonyEventType.USER_STREAM_STARTED,
            conversationId="550e8400-e29b-41d4-a716-446655440000",
            participant="caller",
        )
        assert response.type == TelephonyEventType.USER_STREAM_STARTED
        assert response.conversationId == "550e8400-e29b-41d4-a716-446655440000"
        assert response.participant == "caller"

    def test_valid_user_stream_stopped_with_participant(self):
        """Test that a valid userStream.stopped response with participant can be created."""
        response = UserStreamStoppedResponse(
            type=TelephonyEventType.USER_STREAM_STOPPED,
            conversationId="550e8400-e29b-41d4-a716-446655440000",
            participant="caller",
        )
        assert response.type == TelephonyEventType.USER_STREAM_STOPPED
        assert response.conversationId == "550e8400-e29b-41d4-a716-446655440000"
        assert response.participant == "caller"

    def test_valid_play_stream_start(self):
        """Test that a valid playStream.start message can be created."""
        message = PlayStreamStartMessage(
            type=TelephonyEventType.PLAY_STREAM_START,
            conversationId="550e8400-e29b-41d4-a716-446655440000",
            streamId="stream1",
            mediaFormat="raw/lpcm16",
            altText="test alt text",
            activityParams={"expectAnotherBotMessage": "true"},
            participant="caller",
        )
        assert message.type == TelephonyEventType.PLAY_STREAM_START
        assert message.streamId == "stream1"
        assert message.mediaFormat == "raw/lpcm16"

    def test_invalid_play_stream_start_format(self):
        """Test that a playStream.start with invalid format raises an error."""
        with pytest.raises(ValidationError):
            PlayStreamStartMessage(
                type=TelephonyEventType.PLAY_STREAM_START,
                conversationId="550e8400-e29b-41d4-a716-446655440000",
                streamId="stream1",
                mediaFormat="invalid/format",
                altText="test alt text",
                activityParams={"expectAnotherBotMessage": "true"},
                participant="caller",
            )


class TestActivityMessages:
    """Tests for activity-related message models."""

    def test_valid_activity_event(self):
        """Test that a valid activity event can be created."""
        event = ActivityEvent(
            type="event",
            name="dtmf",
            value="5",
            id="test-id",
            timestamp="2022-07-20T07:15:48.239Z",
            language="en-US",
            parameters={},
            activityParams={},
        )
        assert event.type == "event"
        assert event.name == "dtmf"
        assert event.value == "5"

    def test_valid_hangup_activity(self):
        """Test that a valid hangup activity can be created."""
        event = ActivityEvent(
            type="event",
            name="hangup",
            value=None,
            id="test-id",
            timestamp="2022-07-20T07:15:48.239Z",
            language="en-US",
            parameters={},
            activityParams={},
        )
        assert event.type == "event"
        assert event.name == "hangup"
        assert event.value is None

    def test_invalid_dtmf_value(self):
        """Test that a dtmf activity with invalid value raises an error."""
        with pytest.raises(ValidationError):
            ActivityEvent(
                type="event",
                name="dtmf",
                value="Z",
                id="test-id",
                timestamp="2022-07-20T07:15:48.239Z",
                language="en-US",
                parameters={},
                activityParams={},
            )

    def test_valid_activities_message(self):
        """Test that a valid activities message can be created."""
        events = [
            ActivityEvent(
                type="event",
                name="dtmf",
                value="1",
                id="test-id-1",
                timestamp="2022-07-20T07:15:48.239Z",
                language="en-US",
                parameters={},
                activityParams={},
            ),
            ActivityEvent(
                type="event",
                name="hangup",
                value=None,
                id="test-id-2",
                timestamp="2022-07-20T07:15:48.239Z",
                language="en-US",
                parameters={},
                activityParams={},
            ),
        ]
        message = ActivitiesMessage(
            type=TelephonyEventType.ACTIVITIES,
            conversationId="session123",
            activities=events,
            participant="caller",
        )
        assert message.type == TelephonyEventType.ACTIVITIES
        assert len(message.activities) == 2
        assert message.activities[0].name == "dtmf"
        assert message.activities[1].name == "hangup"

    def test_invalid_empty_activities(self):
        """Test that an activities message with no activities raises an error."""
        with pytest.raises(ValidationError):
            ActivitiesMessage(
                type=TelephonyEventType.ACTIVITIES,
                conversationId="session123",
                activities=[],
                participant="caller",
            )


class TestHypothesisMessages:
    """Tests for hypothesis-related message models."""

    def test_valid_hypothesis(self):
        """Test that a valid hypothesis message can be created."""
        message = UserStreamHypothesisResponse(
            type=TelephonyEventType.USER_STREAM_SPEECH_HYPOTHESIS,
            conversationId="550e8400-e29b-41d4-a716-446655440000",
            alternatives=[{"text": "hello world"}, {"text": "hello word"}],
            participant="caller",
        )
        assert message.type == TelephonyEventType.USER_STREAM_SPEECH_HYPOTHESIS
        assert len(message.alternatives) == 2
        assert message.alternatives[0]["text"] == "hello world"

    def test_invalid_empty_alternatives(self):
        """Test that a hypothesis with no alternatives raises an error."""
        with pytest.raises(ValidationError):
            UserStreamHypothesisResponse(
                type=TelephonyEventType.USER_STREAM_SPEECH_HYPOTHESIS,
                conversationId="550e8400-e29b-41d4-a716-446655440000",
                alternatives=[],
                participant="caller",
            )

    def test_invalid_missing_text(self):
        """Test that a hypothesis with alternative missing text raises an error."""
        with pytest.raises(ValidationError):
            UserStreamHypothesisResponse(
                type=TelephonyEventType.USER_STREAM_SPEECH_HYPOTHESIS,
                conversationId="550e8400-e29b-41d4-a716-446655440000",
                alternatives=[{"confidence": "0.9"}],
                participant="caller",
            )
