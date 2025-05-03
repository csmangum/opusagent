"""
Unit tests for the OpenAI message schemas.

These tests validate that the Pydantic models correctly validate message data
and that the validation rules work as expected.
"""

import base64
import json

import pytest
from pydantic import ValidationError

from fastagent.models.openai_api import (  # Message models; Session models; Conversation models; Event models; Client events; Server events; Function calling models; Legacy models; New models
    ClientEvent,
    ClientEventType,
    ConversationItem,
    ConversationItemContentParam,
    ConversationItemCreatedEvent,
    ConversationItemCreateEvent,
    ConversationItemParam,
    ConversationItemStatus,
    ConversationItemType,
    ErrorEvent,
    InputAudioBufferAppendEvent,
    InputAudioBufferCommitEvent,
    MessageRole,
    OpenAIMessage,
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
    ResponseCreateEvent,
    ResponseCreateOptions,
    ResponseDoneEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
    ResponseTextDeltaEvent,
    ServerEvent,
    ServerEventType,
    SessionConfig,
    SessionCreatedEvent,
    SessionUpdateEvent,
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
        event = ResponseTextDeltaEvent(delta="Hello")
        assert event.type == "response.text.delta"
        assert event.delta == "Hello"

    def test_valid_response_audio_delta_event(self):
        """Test that a valid response audio delta event can be created."""
        audio_data = base64.b64encode(b"test audio data").decode("utf-8")
        event = ResponseAudioDeltaEvent(audio=audio_data)
        assert event.type == "response.audio.delta"
        assert event.audio == audio_data

    def test_valid_response_function_call_arguments_delta_event(self):
        """Test that a valid response function call arguments delta event can be created."""
        event = ResponseFunctionCallArgumentsDeltaEvent(delta='{"key":')
        assert event.type == "response.function_call_arguments.delta"
        assert event.delta == '{"key":'

    def test_valid_response_done_event(self):
        """Test that a valid response done event can be created."""
        event = ResponseDoneEvent()
        assert event.type == "response.done"


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
    """Tests for legacy/compatibility models."""

    def test_valid_realtime_base_message(self):
        """Test that a valid realtime base message can be created."""
        message = RealtimeBaseMessage(type="test.message")
        assert message.type == "test.message"

    def test_valid_realtime_transcript_message(self):
        """Test that a valid realtime transcript message can be created."""
        message = RealtimeTranscriptMessage(
            text="Hello, world!", is_final=True, confidence=0.95
        )
        assert message.type == "transcript"
        assert message.text == "Hello, world!"
        assert message.is_final is True
        assert message.confidence == 0.95

    def test_valid_realtime_turn_message(self):
        """Test that a valid realtime turn message can be created."""
        message = RealtimeTurnMessage(trigger="vad")
        assert message.type == "turn"
        assert message.trigger == "vad"

    def test_valid_realtime_error_message(self):
        """Test that a valid realtime error message can be created."""
        message = RealtimeErrorMessage(
            code="invalid_request",
            message="The request was invalid",
            details={"reason": "Missing required field"},
        )
        assert message.type == "error"
        assert message.code == "invalid_request"
        assert message.message == "The request was invalid"
        assert message.details == {"reason": "Missing required field"}

    def test_valid_realtime_message_content(self):
        """Test that a valid realtime message content can be created."""
        content = RealtimeMessageContent(text="Hello, world!")
        assert content.type == "text"
        assert content.text == "Hello, world!"

    def test_valid_realtime_message_with_string(self):
        """Test that a valid realtime message with string content can be created."""
        message = RealtimeMessage(role=MessageRole.USER, content="Hello, world!")
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"
        assert message.name is None

    def test_valid_realtime_message_with_content_list(self):
        """Test that a valid realtime message with content list can be created."""
        content = RealtimeMessageContent(text="Hello, world!")
        message = RealtimeMessage(role=MessageRole.USER, content=[content])
        assert message.role == MessageRole.USER
        assert isinstance(message.content, list)
        assert message.content[0].text == "Hello, world!"

    def test_valid_realtime_stream_message(self):
        """Test that a valid realtime stream message can be created."""
        content = "I'll help you with that."
        message = RealtimeStreamMessage(
            message=RealtimeMessage(role=MessageRole.ASSISTANT, content=content)
        )
        assert message.type == "message"
        assert message.message.role == MessageRole.ASSISTANT
        assert message.message.content == content

    def test_valid_realtime_function_message(self):
        """Test that a valid realtime function message can be created."""
        function_call = RealtimeFunctionCall(
            name="get_weather", arguments='{"location": "New York"}'
        )
        message = RealtimeFunctionMessage(function_call=function_call)
        assert message.type == "function_call"
        assert message.function_call.name == "get_weather"
        assert message.function_call.arguments == '{"location": "New York"}'

    def test_valid_websocket_error_response(self):
        """Test that a valid websocket error response can be created."""
        error_response = WebSocketErrorResponse(
            error={
                "type": "invalid_request_error",
                "code": "invalid_api_key",
                "message": "The API key provided is invalid",
            }
        )
        assert "type" in error_response.error
        assert error_response.error["code"] == "invalid_api_key"
