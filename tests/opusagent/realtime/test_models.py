"""
Unit tests for opusagent.mock.realtime.models module.
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from opusagent.mock.realtime.models import (
    ConversationContext,
    ResponseSelectionCriteria,
    LocalResponseConfig,
    MockSessionState
)


class TestConversationContext:
    """Test ConversationContext model."""

    def test_conversation_context_creation(self):
        """Test basic ConversationContext creation."""
        context = ConversationContext(
            session_id="test_session_123",
            conversation_id="test_conv_456"
        )
        
        assert context.session_id == "test_session_123"
        assert context.conversation_id == "test_conv_456"
        assert context.conversation_history == []
        assert context.turn_count == 0
        assert context.detected_intents == []
        assert context.preferred_modalities == ["text", "audio"]
        assert context.function_call_context is None

    def test_conversation_context_with_optional_fields(self):
        """Test ConversationContext with all optional fields."""
        context = ConversationContext(
            session_id="test_session_123",
            conversation_id="test_conv_456",
            last_user_input="Hello there!",
            turn_count=5,
            detected_intents=["greeting", "help_request"],
            preferred_modalities=["text"],
            function_call_context={"tool": "test_tool"}
        )
        
        assert context.last_user_input == "Hello there!"
        assert context.turn_count == 5
        assert context.detected_intents == ["greeting", "help_request"]
        assert context.preferred_modalities == ["text"]
        assert context.function_call_context == {"tool": "test_tool"}

    def test_conversation_context_field_assignment(self):
        """Test that fields can be assigned after creation."""
        context = ConversationContext(
            session_id="test_session_123",
            conversation_id="test_conv_456"
        )
        
        # Test field assignment
        context.last_user_input = "New input"
        context.turn_count = 10
        context.detected_intents = ["new_intent"]
        
        assert context.last_user_input == "New input"
        assert context.turn_count == 10
        assert context.detected_intents == ["new_intent"]

    def test_conversation_context_conversation_history(self):
        """Test conversation history management."""
        context = ConversationContext(
            session_id="test_session_123",
            conversation_id="test_conv_456"
        )
        
        # Add conversation history
        history_item = {
            "type": "user_input",
            "text": "Hello",
            "intents": ["greeting"],
            "timestamp": datetime.now().isoformat()
        }
        context.conversation_history.append(history_item)
        
        assert len(context.conversation_history) == 1
        assert context.conversation_history[0]["text"] == "Hello"


class TestResponseSelectionCriteria:
    """Test ResponseSelectionCriteria model."""

    def test_response_selection_criteria_creation(self):
        """Test basic ResponseSelectionCriteria creation."""
        criteria = ResponseSelectionCriteria()
        
        assert criteria.required_keywords is None
        assert criteria.excluded_keywords is None
        assert criteria.required_intents is None
        assert criteria.min_turn_count is None
        assert criteria.max_turn_count is None
        assert criteria.required_modalities is None
        assert criteria.requires_function_call is None
        assert criteria.priority == 0
        assert criteria.context_patterns is None

    def test_response_selection_criteria_with_all_fields(self):
        """Test ResponseSelectionCriteria with all fields."""
        criteria = ResponseSelectionCriteria(
            required_keywords=["hello", "hi"],
            excluded_keywords=["goodbye"],
            required_intents=["greeting"],
            min_turn_count=1,
            max_turn_count=5,
            required_modalities=["text"],
            requires_function_call=False,
            priority=15,
            context_patterns=[r"hello.*world"]
        )
        
        assert criteria.required_keywords == ["hello", "hi"]
        assert criteria.excluded_keywords == ["goodbye"]
        assert criteria.required_intents == ["greeting"]
        assert criteria.min_turn_count == 1
        assert criteria.max_turn_count == 5
        assert criteria.required_modalities == ["text"]
        assert criteria.requires_function_call is False
        assert criteria.priority == 15
        assert criteria.context_patterns == [r"hello.*world"]

    def test_response_selection_criteria_priority_default(self):
        """Test that priority defaults to 0."""
        criteria = ResponseSelectionCriteria()
        assert criteria.priority == 0

    def test_response_selection_criteria_field_validation(self):
        """Test field validation for ResponseSelectionCriteria."""
        # Test with valid data
        criteria = ResponseSelectionCriteria(
            required_keywords=["test"],
            priority=10
        )
        assert criteria.required_keywords == ["test"]
        assert criteria.priority == 10

        # Test with empty lists
        criteria = ResponseSelectionCriteria(
            required_keywords=[],
            excluded_keywords=[]
        )
        assert criteria.required_keywords == []
        assert criteria.excluded_keywords == []


class TestLocalResponseConfig:
    """Test LocalResponseConfig model."""

    def test_local_response_config_creation(self):
        """Test basic LocalResponseConfig creation."""
        config = LocalResponseConfig()
        
        assert config.text == "This is a mock text response from the OpenAI Realtime API."
        assert config.audio_file is None
        assert config.audio_data is None
        assert config.delay_seconds == 0.05
        assert config.audio_chunk_delay == 0.2
        assert config.function_call is None
        assert config.selection_criteria is None

    def test_local_response_config_with_all_fields(self):
        """Test LocalResponseConfig with all fields."""
        selection_criteria = ResponseSelectionCriteria(priority=10)
        
        config = LocalResponseConfig(
            text="Hello! How can I help?",
            audio_file="audio/greeting.wav",
            audio_data=b"audio_bytes",
            delay_seconds=0.03,
            audio_chunk_delay=0.15,
            function_call={"name": "test_function", "arguments": {"param": "value"}},
            selection_criteria=selection_criteria
        )
        
        assert config.text == "Hello! How can I help?"
        assert config.audio_file == "audio/greeting.wav"
        assert config.audio_data == b"audio_bytes"
        assert config.delay_seconds == 0.03
        assert config.audio_chunk_delay == 0.15
        assert config.function_call == {"name": "test_function", "arguments": {"param": "value"}}
        assert config.selection_criteria == selection_criteria

    def test_local_response_config_delay_validation(self):
        """Test delay validation for LocalResponseConfig."""
        # Test valid delays
        config = LocalResponseConfig(delay_seconds=0.0, audio_chunk_delay=0.0)
        assert config.delay_seconds == 0.0
        assert config.audio_chunk_delay == 0.0

        # Test negative delays (should raise validation error)
        with pytest.raises(ValueError):
            LocalResponseConfig(delay_seconds=-0.1)

        with pytest.raises(ValueError):
            LocalResponseConfig(audio_chunk_delay=-0.1)

    def test_local_response_config_function_call_structure(self):
        """Test function call structure validation."""
        # Valid function call
        config = LocalResponseConfig(
            function_call={
                "name": "test_function",
                "arguments": {"param1": "value1", "param2": 123}
            }
        )
        assert config.function_call is not None
        assert config.function_call["name"] == "test_function"
        assert config.function_call["arguments"]["param1"] == "value1"

        # Function call with complex arguments
        config = LocalResponseConfig(
            function_call={
                "name": "complex_function",
                "arguments": {
                    "list_param": [1, 2, 3],
                    "dict_param": {"nested": "value"},
                    "bool_param": True
                }
            }
        )
        assert config.function_call is not None
        assert config.function_call["arguments"]["list_param"] == [1, 2, 3]
        assert config.function_call["arguments"]["bool_param"] is True

    def test_local_response_config_audio_priority(self):
        """Test that audio_data takes precedence over audio_file."""
        config = LocalResponseConfig(
            audio_file="audio/file.wav",
            audio_data=b"raw_audio_data"
        )
        
        # audio_data should be available and take precedence
        assert config.audio_data == b"raw_audio_data"
        assert config.audio_file == "audio/file.wav"


class TestMockSessionState:
    """Test MockSessionState model."""

    def test_mock_session_state_creation(self):
        """Test basic MockSessionState creation."""
        state = MockSessionState(
            session_id="test_session_123",
            conversation_id="test_conv_456"
        )
        
        assert state.session_id == "test_session_123"
        assert state.conversation_id == "test_conv_456"
        assert state.connected is False
        assert state.active_response_id is None
        assert state.speech_detected is False
        assert state.audio_buffer == []
        assert state.response_audio == []
        assert state.response_text == ""
        assert state.conversation_context is None

    def test_mock_session_state_with_all_fields(self):
        """Test MockSessionState with all fields."""
        context = ConversationContext(
            session_id="test_session_123",
            conversation_id="test_conv_456"
        )
        
        state = MockSessionState(
            session_id="test_session_123",
            conversation_id="test_conv_456",
            connected=True,
            active_response_id="resp_789",
            speech_detected=True,
            audio_buffer=[b"chunk1", b"chunk2"],
            response_audio=[b"resp_chunk1"],
            response_text="Response text",
            conversation_context=context
        )
        
        assert state.connected is True
        assert state.active_response_id == "resp_789"
        assert state.speech_detected is True
        assert state.audio_buffer == [b"chunk1", b"chunk2"]
        assert state.response_audio == [b"resp_chunk1"]
        assert state.response_text == "Response text"
        assert state.conversation_context == context

    def test_mock_session_state_audio_buffer_operations(self):
        """Test audio buffer operations."""
        state = MockSessionState(
            session_id="test_session_123",
            conversation_id="test_conv_456"
        )
        
        # Test adding audio chunks
        state.audio_buffer.append(b"audio_chunk_1")
        state.audio_buffer.append(b"audio_chunk_2")
        
        assert len(state.audio_buffer) == 2
        assert state.audio_buffer[0] == b"audio_chunk_1"
        assert state.audio_buffer[1] == b"audio_chunk_2"

        # Test clearing buffer
        state.audio_buffer.clear()
        assert len(state.audio_buffer) == 0

    def test_mock_session_state_response_management(self):
        """Test response state management."""
        state = MockSessionState(
            session_id="test_session_123",
            conversation_id="test_conv_456"
        )
        
        # Test setting active response
        state.active_response_id = "new_response_123"
        assert state.active_response_id == "new_response_123"

        # Test clearing active response
        state.active_response_id = None
        assert state.active_response_id is None

        # Test response text
        state.response_text = "New response text"
        assert state.response_text == "New response text"

    def test_mock_session_state_speech_detection(self):
        """Test speech detection state."""
        state = MockSessionState(
            session_id="test_session_123",
            conversation_id="test_conv_456"
        )
        
        # Test speech detection toggle
        assert state.speech_detected is False
        
        state.speech_detected = True
        assert state.speech_detected is True
        
        state.speech_detected = False
        assert state.speech_detected is False


class TestModelIntegration:
    """Test integration between different models."""

    def test_response_config_with_selection_criteria(self):
        """Test LocalResponseConfig with ResponseSelectionCriteria."""
        criteria = ResponseSelectionCriteria(
            required_keywords=["hello", "hi"],
            priority=15,
            min_turn_count=1
        )
        
        config = LocalResponseConfig(
            text="Hello! How can I help?",
            selection_criteria=criteria
        )
        
        assert config.selection_criteria == criteria
        assert config.selection_criteria is not None
        assert config.selection_criteria.priority == 15
        assert config.selection_criteria.required_keywords == ["hello", "hi"]

    def test_session_state_with_conversation_context(self):
        """Test MockSessionState with ConversationContext."""
        context = ConversationContext(
            session_id="session_123",
            conversation_id="conv_456",
            last_user_input="Hello there!",
            detected_intents=["greeting"]
        )
        
        state = MockSessionState(
            session_id="session_123",
            conversation_id="conv_456",
            conversation_context=context
        )
        
        assert state.conversation_context == context
        assert state.conversation_context is not None
        assert state.conversation_context.last_user_input == "Hello there!"
        assert state.conversation_context.detected_intents == ["greeting"]

    def test_complex_response_configuration(self):
        """Test complex response configuration with all components."""
        # Create selection criteria
        criteria = ResponseSelectionCriteria(
            required_keywords=["help", "support"],
            excluded_keywords=["goodbye"],
            required_intents=["help_request"],
            min_turn_count=2,
            max_turn_count=10,
            required_modalities=["text", "audio"],
            requires_function_call=False,
            priority=20,
            context_patterns=[r"need.*help", r"can.*assist"]
        )
        
        # Create response config
        config = LocalResponseConfig(
            text="I'd be happy to help you with that!",
            audio_file="audio/help_response.wav",
            delay_seconds=0.03,
            audio_chunk_delay=0.15,
            function_call={
                "name": "get_help_info",
                "arguments": {"category": "general"}
            },
            selection_criteria=criteria
        )
        
        # Verify all components
        assert config.text == "I'd be happy to help you with that!"
        assert config.selection_criteria is not None
        assert config.selection_criteria.priority == 20
        assert config.selection_criteria.required_keywords == ["help", "support"]
        assert config.function_call is not None
        assert config.function_call["name"] == "get_help_info"
        assert config.delay_seconds == 0.03 