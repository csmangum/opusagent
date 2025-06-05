"""
Unit tests for the OpenAI message schemas.

These tests validate that the Pydantic models correctly validate message data
and that the validation rules work as expected.
"""

import base64
import json

import pytest
from pydantic import ValidationError

from opusagent.models.openai_api import (  # Message models; Session models; Conversation models; Event models; Client events; Server events; Function calling models; Legacy models; New models
    ClientEvent,
    ClientEventType,
    ConversationCreatedEvent,
    ConversationItem,
    ConversationItemContentParam,
    ConversationItemCreatedEvent,
    ConversationItemCreateEvent,
    ConversationItemDeletedEvent,
    ConversationItemDeleteEvent,
    ConversationItemInputAudioTranscriptionCompletedEvent,
    ConversationItemInputAudioTranscriptionDeltaEvent,
    ConversationItemInputAudioTranscriptionFailedEvent,
    ConversationItemParam,
    ConversationItemRetrievedEvent,
    ConversationItemRetrieveEvent,
    ConversationItemStatus,
    ConversationItemTruncatedEvent,
    ConversationItemTruncateEvent,
    ConversationItemType,
    ErrorEvent,
    InputAudioBufferAppendEvent,
    InputAudioBufferClearedEvent,
    InputAudioBufferClearEvent,
    InputAudioBufferCommitEvent,
    InputAudioBufferSpeechStartedEvent,
    InputAudioBufferSpeechStoppedEvent,
    MessageRole,
    OpenAIMessage,
    RateLimitsUpdatedEvent,
    RealtimeBaseMessage,
    RealtimeErrorMessage,
    RealtimeFunctionCall,
    RealtimeFunctionCallOutput,
    RealtimeFunctionMessage,
    RealtimeMessage,
    RealtimeMessageContent,
    RealtimeSessionResponse,
    RealtimeStreamMessage,
    RealtimeTranscriptMessage,
    RealtimeTurnMessage,
    ResponseAudioDeltaEvent,
    ResponseAudioDoneEvent,
    ResponseAudioTranscriptDeltaEvent,
    ResponseAudioTranscriptDoneEvent,
    ResponseCancelEvent,
    ResponseCancelledEvent,
    ResponseContentPartAddedEvent,
    ResponseContentPartDoneEvent,
    ResponseCreatedEvent,
    ResponseCreateEvent,
    ResponseCreateOptions,
    ResponseDoneEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    ResponseOutputItemAddedEvent,
    ResponseOutputItemDoneEvent,
    ResponseTextDeltaEvent,
    ResponseTextDoneEvent,
    ServerEvent,
    ServerEventType,
    SessionConfig,
    SessionCreatedEvent,
    SessionUpdatedEvent,
    SessionUpdateEvent,
    TranscriptionSessionUpdatedEvent,
    TranscriptionSessionUpdateEvent,
    WebSocketErrorResponse,
)


class TestMessageModels:
    """Tests for the message models."""

    def test_message_role_enum(self):
        """Test the MessageRole enum values."""
        assert MessageRole.SYSTEM == "system"
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.FUNCTION == "function"

    def test_valid_openai_message(self):
        """Test that a valid OpenAI message can be created."""
        message = OpenAIMessage(role=MessageRole.USER, content="Hello, world!")
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"

    def test_invalid_openai_message_role(self):
        """Test that an OpenAI message with invalid role raises a validation error."""
        with pytest.raises(ValidationError):
            OpenAIMessage(role="invalid_role", content="Hello, world!")


class TestSessionModels:
    """Tests for session-related models."""

    def test_valid_session_config(self):
        """Test that a valid session config can be created."""
        config = SessionConfig(
            modalities=["text", "audio"],
            model="gpt-4o",
            instructions="Be helpful and concise.",
            voice="alloy",
            input_audio_format="pcm16",
            output_audio_format="pcm16",
            turn_detection={"type": "server_vad"},
        )
        assert "text" in config.modalities
        assert "audio" in config.modalities
        assert config.model == "gpt-4o"
        assert config.instructions == "Be helpful and concise."
        assert config.voice == "alloy"
        assert config.input_audio_format == "pcm16"
        assert config.output_audio_format == "pcm16"
        assert config.turn_detection == {"type": "server_vad"}

    def test_minimal_session_config(self):
        """Test that a minimal session config can be created with defaults."""
        config = SessionConfig()
        assert config.modalities == ["text"]
        assert config.model is None
        assert config.instructions is None

    def test_valid_realtime_session_response(self):
        """Test that a valid realtime session response can be created."""
        response = RealtimeSessionResponse(
            client_secret={"key": "secret_value"},
            expires_at=1672531200,
            id="session-123",
        )
        assert response.client_secret == {"key": "secret_value"}
        assert response.expires_at == 1672531200
        assert response.id == "session-123"


class TestConversationModels:
    """Tests for conversation-related models."""

    def test_conversation_item_type_enum(self):
        """Test the ConversationItemType enum values."""
        assert ConversationItemType.MESSAGE == "message"
        assert ConversationItemType.FUNCTION_CALL == "function_call"
        assert ConversationItemType.FUNCTION_CALL_OUTPUT == "function_call_output"

    def test_conversation_item_status_enum(self):
        """Test the ConversationItemStatus enum values."""
        assert ConversationItemStatus.COMPLETED == "completed"
        assert ConversationItemStatus.IN_PROGRESS == "in_progress"
        assert ConversationItemStatus.INTERRUPTED == "interrupted"

    def test_valid_conversation_item_content_param(self):
        """Test that a valid conversation item content param can be created."""
        content_param = ConversationItemContentParam(
            type="input_text", text="Hello, world!"
        )
        assert content_param.type == "input_text"
        assert content_param.text == "Hello, world!"
        assert content_param.audio is None

    def test_valid_conversation_item_param(self):
        """Test that a valid conversation item param can be created."""
        content_param = ConversationItemContentParam(type="input_text", text="Hello")
        item_param = ConversationItemParam(
            type="message", role=MessageRole.USER, content=[content_param]
        )
        assert item_param.type == "message"
        assert item_param.role == MessageRole.USER
        assert len(item_param.content) == 1
        assert item_param.content[0].text == "Hello"

    def test_valid_conversation_item(self):
        """Test that a valid conversation item can be created."""
        item = ConversationItem(
            id="item-123",
            object="realtime.item",
            type=ConversationItemType.MESSAGE,
            status=ConversationItemStatus.COMPLETED,
            role=MessageRole.USER,
            content=[{"type": "text", "text": "Hello, world!"}],
            created_at=1672531200,
        )
        assert item.id == "item-123"
        assert item.object == "realtime.item"
        assert item.type == ConversationItemType.MESSAGE
        assert item.status == ConversationItemStatus.COMPLETED
        assert item.role == MessageRole.USER
        assert item.content[0]["text"] == "Hello, world!"
        assert item.created_at == 1672531200


class TestEventModels:
    """Tests for event models."""

    def test_client_event_type_enum(self):
        """Test the ClientEventType enum values."""
        assert ClientEventType.SESSION_UPDATE == "session.update"
        assert ClientEventType.INPUT_AUDIO_BUFFER_APPEND == "input_audio_buffer.append"
        assert ClientEventType.CONVERSATION_ITEM_CREATE == "conversation.item.create"
        assert ClientEventType.RESPONSE_CREATE == "response.create"

    def test_server_event_type_enum(self):
        """Test the ServerEventType enum values."""
        assert ServerEventType.ERROR == "error"
        assert ServerEventType.SESSION_CREATED == "session.created"
        assert ServerEventType.RESPONSE_TEXT_DELTA == "response.text.delta"
        assert ServerEventType.RESPONSE_DONE == "response.done"

    def test_valid_client_event(self):
        """Test that a valid client event can be created."""
        event = ClientEvent(type="test.event")
        assert event.type == "test.event"

    def test_valid_server_event(self):
        """Test that a valid server event can be created."""
        event = ServerEvent(type="test.event")
        assert event.type == "test.event"


class TestClientEventImplementations:
    """Tests for specific client event implementations."""

    def test_valid_session_update_event(self):
        """Test that a valid session update event can be created."""
        event = SessionUpdateEvent(
            session=SessionConfig(modalities=["text", "audio"], model="gpt-4o")
        )
        assert event.type == "session.update"
        assert "text" in event.session.modalities
        assert "audio" in event.session.modalities
        assert event.session.model == "gpt-4o"

    def test_valid_input_audio_buffer_append_event(self):
        """Test that a valid input audio buffer append event can be created."""
        # Create base64 encoded audio data
        audio_data = base64.b64encode(b"test audio data").decode("utf-8")
        event = InputAudioBufferAppendEvent(audio=audio_data)
        assert event.type == "input_audio_buffer.append"
        assert event.audio == audio_data

    def test_valid_input_audio_buffer_commit_event(self):
        """Test that a valid input audio buffer commit event can be created."""
        event = InputAudioBufferCommitEvent()
        assert event.type == "input_audio_buffer.commit"

    def test_valid_conversation_item_create_event(self):
        """Test that a valid conversation item create event can be created."""
        content_param = ConversationItemContentParam(type="input_text", text="Hello")
        item_param = ConversationItemParam(
            type="message", role=MessageRole.USER, content=[content_param]
        )
        event = ConversationItemCreateEvent(item=item_param)
        assert event.type == "conversation.item.create"
        assert event.item.type == "message"
        assert event.item.role == MessageRole.USER

    def test_valid_response_create_event(self):
        """Test that a valid response create event can be created."""
        # Create with default ResponseCreateOptions
        event = ResponseCreateEvent(response=ResponseCreateOptions())
        assert event.type == "response.create"
        assert event.response.modalities == ["text"]  # Default value

        # Create with custom options
        event_with_params = ResponseCreateEvent(
            response=ResponseCreateOptions(
                modalities=["text", "audio"],
                voice="alloy",
                instructions="Test instructions",
            )
        )
        assert event_with_params.type == "response.create"
        assert event_with_params.response.modalities == ["text", "audio"]
        assert event_with_params.response.voice == "alloy"
        assert event_with_params.response.instructions == "Test instructions"

    def test_valid_input_audio_buffer_clear_event(self):
        """Test that a valid input audio buffer clear event can be created."""
        event = InputAudioBufferClearEvent()
        assert event.type == "input_audio_buffer.clear"

    def test_valid_conversation_item_retrieve_event(self):
        """Test that a valid conversation item retrieve event can be created."""
        event = ConversationItemRetrieveEvent(item_id="item-123")
        assert event.type == "conversation.item.retrieve"
        assert event.item_id == "item-123"

    def test_valid_conversation_item_truncate_event(self):
        """Test that a valid conversation item truncate event can be created."""
        event = ConversationItemTruncateEvent(
            item_id="item-123", content_index=0, audio_end_ms=1000
        )
        assert event.type == "conversation.item.truncate"
        assert event.item_id == "item-123"
        assert event.content_index == 0
        assert event.audio_end_ms == 1000

    def test_valid_conversation_item_delete_event(self):
        """Test that a valid conversation item delete event can be created."""
        event = ConversationItemDeleteEvent(item_id="item-123")
        assert event.type == "conversation.item.delete"
        assert event.item_id == "item-123"

    def test_valid_response_cancel_event(self):
        """Test that a valid response cancel event can be created."""
        event = ResponseCancelEvent(response_id="resp-123")
        assert event.type == "response.cancel"
        assert event.response_id == "resp-123"

    def test_valid_transcription_session_update_event(self):
        """Test that a valid transcription session update event can be created."""
        event = TranscriptionSessionUpdateEvent(
            session={"language": "en", "model": "whisper-1"}
        )
        assert event.type == "transcription_session.update"
        assert event.session == {"language": "en", "model": "whisper-1"}


class TestServerEventImplementations:
    """Tests for specific server event implementations."""

    def test_valid_error_event(self):
        """Test that a valid error event can be created."""
        event = ErrorEvent(
            code="invalid_request",
            message="The request was invalid",
            details={"field": "audio", "reason": "Invalid format"},
        )
        assert event.type == "error"
        assert event.code == "invalid_request"
        assert event.message == "The request was invalid"
        assert event.details == {"field": "audio", "reason": "Invalid format"}

    def test_valid_session_created_event(self):
        """Test that a valid session created event can be created."""
        event = SessionCreatedEvent(
            session={"id": "session-123", "model": "gpt-4o", "created_at": 1672531200}
        )
        assert event.type == "session.created"
        assert event.session["id"] == "session-123"
        assert event.session["model"] == "gpt-4o"

    def test_valid_conversation_item_created_event(self):
        """Test that a valid conversation item created event can be created."""
        event = ConversationItemCreatedEvent(
            item={
                "id": "item-123",
                "type": "message",
                "role": "user",
                "content": [{"type": "text", "text": "Hello"}],
                "status": "completed",
            }
        )
        assert event.type == "conversation.item.created"
        assert event.item["id"] == "item-123"
        assert event.item["type"] == "message"

    def test_valid_response_text_delta_event(self):
        """Test that a valid response text delta event can be created."""
        event = ResponseTextDeltaEvent(
            delta="Hello",
            response_id="resp_123",
            item_id="item_123",
            output_index=0,
            content_index=0,
        )
        assert event.type == "response.text.delta"
        assert event.delta == "Hello"

    def test_valid_response_audio_delta_event(self):
        """Test that a valid response audio delta event can be created."""
        audio_data = base64.b64encode(b"test audio data").decode("utf-8")
        event = ResponseAudioDeltaEvent(
            delta=audio_data,
            response_id="resp_123",
            item_id="item_123",
            output_index=0,
            content_index=0,
        )
        assert event.type == "response.audio.delta"
        assert event.delta == audio_data

    def test_valid_response_function_call_arguments_delta_event(self):
        """Test that a valid response function call arguments delta event can be created."""
        event = ResponseFunctionCallArgumentsDeltaEvent(
            delta='{"key":',
            response_id="resp_123",
            item_id="item_123",
            output_index=0,
            call_id="call_123",
        )
        assert event.type == "response.function_call_arguments.delta"
        assert event.delta == '{"key":'

    def test_valid_response_done_event(self):
        """Test that a valid response done event can be created."""
        event = ResponseDoneEvent(response={"id": "resp_123", "status": "completed"})
        assert event.type == "response.done"

    def test_valid_session_updated_event(self):
        """Test that a valid session updated event can be created."""
        event = SessionUpdatedEvent(
            session={"id": "session-123", "model": "gpt-4o", "updated_at": 1672531200}
        )
        assert event.type == "session.updated"
        assert event.session["id"] == "session-123"
        assert event.session["model"] == "gpt-4o"

    def test_valid_conversation_created_event(self):
        """Test that a valid conversation created event can be created."""
        event = ConversationCreatedEvent(
            conversation={"id": "conv-123", "created_at": 1672531200}
        )
        assert event.type == "conversation.created"
        assert event.conversation["id"] == "conv-123"

    def test_valid_conversation_item_retrieved_event(self):
        """Test that a valid conversation item retrieved event can be created."""
        event = ConversationItemRetrievedEvent(
            item={"id": "item-123", "type": "message", "content": "Hello"}
        )
        assert event.type == "conversation.item.retrieved"
        assert event.item["id"] == "item-123"

    def test_valid_conversation_item_truncated_event(self):
        """Test that a valid conversation item truncated event can be created."""
        event = ConversationItemTruncatedEvent(
            item_id="item-123", content_index=0, audio_end_ms=1000
        )
        assert event.type == "conversation.item.truncated"
        assert event.item_id == "item-123"
        assert event.content_index == 0
        assert event.audio_end_ms == 1000

    def test_valid_conversation_item_deleted_event(self):
        """Test that a valid conversation item deleted event can be created."""
        event = ConversationItemDeletedEvent(item_id="item-123")
        assert event.type == "conversation.item.deleted"
        assert event.item_id == "item-123"

    def test_valid_input_audio_buffer_cleared_event(self):
        """Test that a valid input audio buffer cleared event can be created."""
        event = InputAudioBufferClearedEvent()
        assert event.type == "input_audio_buffer.cleared"

    def test_valid_input_audio_buffer_speech_started_event(self):
        """Test that a valid input audio buffer speech started event can be created."""
        event = InputAudioBufferSpeechStartedEvent(
            audio_start_ms=1000, item_id="item-123"
        )
        assert event.type == "input_audio_buffer.speech_started"
        assert event.audio_start_ms == 1000
        assert event.item_id == "item-123"

    def test_valid_input_audio_buffer_speech_stopped_event(self):
        """Test that a valid input audio buffer speech stopped event can be created."""
        event = InputAudioBufferSpeechStoppedEvent(
            audio_end_ms=2000, item_id="item-123"
        )
        assert event.type == "input_audio_buffer.speech_stopped"
        assert event.audio_end_ms == 2000
        assert event.item_id == "item-123"

    def test_valid_response_created_event(self):
        """Test that a valid response created event can be created."""
        event = ResponseCreatedEvent(
            response={"id": "resp-123", "status": "in_progress"}
        )
        assert event.type == "response.created"
        assert event.response["id"] == "resp-123"

    def test_valid_response_cancelled_event(self):
        """Test that a valid response cancelled event can be created."""
        event = ResponseCancelledEvent(response_id="resp-123")
        assert event.type == "response.cancelled"
        assert event.response_id == "resp-123"

    def test_valid_response_text_done_event(self):
        """Test that a valid response text done event can be created."""
        event = ResponseTextDoneEvent(
            response_id="resp-123",
            item_id="item-123",
            output_index=0,
            content_index=0,
            text="Hello, world!",
        )
        assert event.type == "response.text.done"
        assert event.text == "Hello, world!"

    def test_valid_response_audio_done_event(self):
        """Test that a valid response audio done event can be created."""
        event = ResponseAudioDoneEvent(
            response_id="resp-123", item_id="item-123", output_index=0, content_index=0
        )
        assert event.type == "response.audio.done"

    def test_valid_response_audio_transcript_delta_event(self):
        """Test that a valid response audio transcript delta event can be created."""
        event = ResponseAudioTranscriptDeltaEvent(
            response_id="resp-123",
            item_id="item-123",
            output_index=0,
            content_index=0,
            delta="Hello",
        )
        assert event.type == "response.audio_transcript.delta"
        assert event.delta == "Hello"

    def test_valid_response_audio_transcript_done_event(self):
        """Test that a valid response audio transcript done event can be created."""
        event = ResponseAudioTranscriptDoneEvent(
            response_id="resp-123",
            item_id="item-123",
            output_index=0,
            content_index=0,
            transcript="Hello, world!",
        )
        assert event.type == "response.audio_transcript.done"
        assert event.transcript == "Hello, world!"

    def test_valid_response_function_call_arguments_done_event(self):
        """Test that a valid response function call arguments done event can be created."""
        event = ResponseFunctionCallArgumentsDoneEvent(
            response_id="resp-123",
            item_id="item-123",
            output_index=0,
            call_id="call-123",
            arguments='{"key": "value"}',
        )
        assert event.type == "response.function_call_arguments.done"
        assert event.arguments == '{"key": "value"}'

    def test_valid_rate_limits_updated_event(self):
        """Test that a valid rate limits updated event can be created."""
        event = RateLimitsUpdatedEvent(
            rate_limits=[{"type": "tokens", "limit": 1000, "remaining": 500}]
        )
        assert event.type == "rate_limits.updated"
        assert event.rate_limits[0]["type"] == "tokens"

    def test_valid_response_output_item_added_event(self):
        """Test that a valid response output item added event can be created."""
        event = ResponseOutputItemAddedEvent(
            response_id="resp-123",
            output_index=0,
            item={"id": "item-123", "type": "message"},
        )
        assert event.type == "response.output_item.added"
        assert event.item["id"] == "item-123"

    def test_valid_response_output_item_done_event(self):
        """Test that a valid response output item done event can be created."""
        event = ResponseOutputItemDoneEvent(
            response_id="resp-123",
            output_index=0,
            item={"id": "item-123", "type": "message"},
        )
        assert event.type == "response.output_item.done"
        assert event.item["id"] == "item-123"

    def test_valid_response_content_part_done_event(self):
        """Test that a valid response content part done event can be created."""
        event = ResponseContentPartDoneEvent(
            response_id="resp-123",
            item_id="item-123",
            output_index=0,
            content_index=0,
            part_id="part-123",
            status="completed",
            part={"type": "text", "text": "Hello"},
        )
        assert event.type == "response.content_part.done"
        assert event.part["text"] == "Hello"

    def test_valid_response_content_part_added_event(self):
        """Test that a valid response content part added event can be created."""
        event = ResponseContentPartAddedEvent(
            response_id="resp-123",
            item_id="item-123",
            output_index=0,
            content_index=0,
            part={"type": "text", "text": "Hello"},
        )
        assert event.type == "response.content_part.added"
        assert event.part["text"] == "Hello"

    def test_valid_transcription_session_updated_event(self):
        """Test that a valid transcription session updated event can be created."""
        event = TranscriptionSessionUpdatedEvent(
            session={"id": "trans-123", "status": "active"}
        )
        assert event.type == "transcription_session.updated"
        assert event.session["id"] == "trans-123"

    def test_valid_conversation_item_input_audio_transcription_completed_event(self):
        """Test that a valid conversation item input audio transcription completed event can be created."""
        event = ConversationItemInputAudioTranscriptionCompletedEvent(
            item_id="item-123",
            content_index=0,
            transcript="Hello, world!",
            logprobs=[{"token": "Hello", "logprob": -0.5}],
        )
        assert event.type == "conversation.item.input_audio_transcription.completed"
        assert event.transcript == "Hello, world!"

    def test_valid_conversation_item_input_audio_transcription_delta_event(self):
        """Test that a valid conversation item input audio transcription delta event can be created."""
        event = ConversationItemInputAudioTranscriptionDeltaEvent(
            item_id="item-123",
            content_index=0,
            delta="Hello",
            logprobs=[{"token": "Hello", "logprob": -0.5}],
        )
        assert event.type == "conversation.item.input_audio_transcription.delta"
        assert event.delta == "Hello"

    def test_valid_conversation_item_input_audio_transcription_failed_event(self):
        """Test that a valid conversation item input audio transcription failed event can be created."""
        event = ConversationItemInputAudioTranscriptionFailedEvent(
            item_id="item-123",
            content_index=0,
            error={"code": "transcription_failed", "message": "Failed to transcribe"},
        )
        assert event.type == "conversation.item.input_audio_transcription.failed"
        assert event.error["code"] == "transcription_failed"


class TestFunctionCallingModels:
    """Tests for function calling models."""

    def test_valid_realtime_function_call(self):
        """Test that a valid realtime function call can be created."""
        function_call = RealtimeFunctionCall(
            name="get_weather", arguments='{"location": "New York", "unit": "celsius"}'
        )
        assert function_call.name == "get_weather"
        assert function_call.arguments == '{"location": "New York", "unit": "celsius"}'

    def test_valid_realtime_function_call_output(self):
        """Test that a valid realtime function call output can be created."""
        function_output = RealtimeFunctionCallOutput(
            name="get_weather", output='{"temperature": 22, "conditions": "sunny"}'
        )
        assert function_output.name == "get_weather"
        assert function_output.output == '{"temperature": 22, "conditions": "sunny"}'


class TestLegacyModels:
    """Tests for legacy OpenAI message models."""

    def test_valid_realtime_base_message(self):
        """Test that a valid RealtimeBaseMessage can be created."""
        message = RealtimeBaseMessage(type="test")
        assert message.type == "test"

    def test_valid_realtime_error_message(self):
        """Test that a valid RealtimeErrorMessage can be created."""
        message = RealtimeErrorMessage(
            code="invalid_request",
            message="The request was invalid",
            details={"field": "audio", "reason": "Invalid format"},
        )
        assert message.type == "error"
        assert message.code == "invalid_request"
        assert message.message == "The request was invalid"
        assert message.details == {"field": "audio", "reason": "Invalid format"}

    def test_valid_realtime_transcript_message(self):
        """Test that a valid RealtimeTranscriptMessage can be created."""
        message = RealtimeTranscriptMessage(
            text="Hello, world!", final=True, created_at=1672531200
        )
        assert message.type == "transcript"
        assert message.text == "Hello, world!"
        assert message.final is True
        assert message.created_at == 1672531200

    def test_valid_realtime_turn_message(self):
        """Test that a valid RealtimeTurnMessage can be created."""
        message = RealtimeTurnMessage(action="start", created_at=1672531200)
        assert message.type == "turn"
        assert message.action == "start"
        assert message.created_at == 1672531200

    def test_valid_realtime_message_content(self):
        """Test that a valid RealtimeMessageContent can be created."""
        content = RealtimeMessageContent(type="text", text="Hello, world!")
        assert content.type == "text"
        assert content.text == "Hello, world!"

    def test_valid_realtime_message(self):
        """Test that a valid RealtimeMessage can be created."""
        message = RealtimeMessage(
            role="user",
            content="Hello, world!",
            name="test_user",
            function_call={"name": "get_weather", "arguments": "{}"},
            created_at=1672531200,
        )
        assert message.type == "message"
        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert message.name == "test_user"
        assert message.function_call == {"name": "get_weather", "arguments": "{}"}
        assert message.created_at == 1672531200

    def test_valid_realtime_stream_message(self):
        """Test that a valid RealtimeStreamMessage can be created."""
        message = RealtimeStreamMessage(
            content="Hello, world!", role="assistant", end=True, created_at=1672531200
        )
        assert message.type == "stream"
        assert message.content == "Hello, world!"
        assert message.role == "assistant"
        assert message.end is True
        assert message.created_at == 1672531200

    def test_valid_realtime_function_message(self):
        """Test that a valid RealtimeFunctionMessage can be created."""
        message = RealtimeFunctionMessage(
            function={"name": "get_weather", "arguments": "{}"}, created_at=1672531200
        )
        assert message.type == "function"
        assert message.function == {"name": "get_weather", "arguments": "{}"}
        assert message.created_at == 1672531200

    def test_valid_websocket_error_response(self):
        """Test that a valid WebSocketErrorResponse can be created."""
        response = WebSocketErrorResponse(
            error="invalid_request", message="The request was invalid"
        )
        assert response.error == "invalid_request"
        assert response.message == "The request was invalid"
