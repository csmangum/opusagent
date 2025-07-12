"""
Unit tests for opusagent.mock.realtime.utils module.
"""

import pytest
import time
import uuid
from unittest.mock import Mock, patch
from typing import Dict, Any

from opusagent.mock.realtime.utils import (
    validate_response_config,
    create_default_response_config,
    create_error_event,
    create_session_event,
    create_response_event,
    DEFAULT_AUDIO_CHUNK_SIZE,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_CHANNELS,
    DEFAULT_BITS_PER_SAMPLE
)


class TestValidationFunctions:
    """Test validation functions."""

    def test_validate_response_config_valid(self):
        """Test validation of valid response config."""
        config = {
            "text": "Hello world",
            "delay_seconds": 0.05,
            "audio_chunk_delay": 0.2,
            "function_call": {"name": "test", "arguments": {}}
        }
        
        assert validate_response_config(config) is True

    def test_validate_response_config_missing_required_field(self):
        """Test validation of config missing required field."""
        config = {
            "delay_seconds": 0.05
            # Missing "text" field
        }
        
        assert validate_response_config(config) is False

    def test_validate_response_config_invalid_text_type(self):
        """Test validation of config with invalid text type."""
        config = {
            "text": 123,  # Should be string
            "delay_seconds": 0.05
        }
        
        assert validate_response_config(config) is False

    def test_validate_response_config_invalid_delay_type(self):
        """Test validation of config with invalid delay type."""
        config = {
            "text": "Hello world",
            "delay_seconds": "invalid"  # Should be number
        }
        
        assert validate_response_config(config) is False

    def test_validate_response_config_invalid_audio_chunk_delay_type(self):
        """Test validation of config with invalid audio chunk delay type."""
        config = {
            "text": "Hello world",
            "audio_chunk_delay": "invalid"  # Should be number
        }
        
        assert validate_response_config(config) is False

    def test_validate_response_config_invalid_function_call_type(self):
        """Test validation of config with invalid function call type."""
        config = {
            "text": "Hello world",
            "function_call": "invalid"  # Should be dict
        }
        
        assert validate_response_config(config) is False

    def test_validate_response_config_empty_lists(self):
        """Test validation of config with empty lists."""
        config = {
            "text": "Hello world",
            "required_keywords": [],
            "excluded_keywords": []
        }
        
        assert validate_response_config(config) is True

    def test_validate_response_config_complex_function_call(self):
        """Test validation of config with complex function call."""
        config = {
            "text": "Hello world",
            "function_call": {
                "name": "complex_function",
                "arguments": {
                    "list_param": [1, 2, 3],
                    "dict_param": {"nested": "value"},
                    "bool_param": True,
                    "null_param": None
                }
            }
        }
        
        assert validate_response_config(config) is True


class TestDefaultConfigFunctions:
    """Test default configuration functions."""

    def test_create_default_response_config(self):
        """Test creating default response config."""
        config = create_default_response_config()
        
        assert isinstance(config, dict)
        assert "text" in config
        assert "delay_seconds" in config
        assert "audio_chunk_delay" in config
        
        assert config["text"] == "This is a mock text response from the OpenAI Realtime API."
        assert config["delay_seconds"] == 0.05
        assert config["audio_chunk_delay"] == 0.2

    def test_create_default_response_config_structure(self):
        """Test structure of default response config."""
        config = create_default_response_config()
        
        # Check that all required fields are present
        required_fields = ["text", "delay_seconds", "audio_chunk_delay"]
        for field in required_fields:
            assert field in config
        
        # Check that optional fields are not present
        optional_fields = ["audio_file", "audio_data", "function_call"]
        for field in optional_fields:
            assert field not in config


class TestEventCreationFunctions:
    """Test event creation functions."""

    def test_create_error_event_basic(self):
        """Test creating basic error event."""
        event = create_error_event("TEST_ERROR", "Test error message")
        
        assert event["type"] == "error"
        assert event["code"] == "TEST_ERROR"
        assert event["message"] == "Test error message"
        assert "details" not in event

    def test_create_error_event_with_details(self):
        """Test creating error event with details."""
        details = {"retry_after": 60, "limit": 100}
        event = create_error_event("RATE_LIMIT", "Rate limit exceeded", details)
        
        assert event["type"] == "error"
        assert event["code"] == "RATE_LIMIT"
        assert event["message"] == "Rate limit exceeded"
        assert event["details"] == details

    def test_create_error_event_with_none_details(self):
        """Test creating error event with None details."""
        event = create_error_event("TEST_ERROR", "Test message", None)
        
        assert event["type"] == "error"
        assert event["code"] == "TEST_ERROR"
        assert event["message"] == "Test message"
        assert "details" not in event

    def test_create_session_event_basic(self):
        """Test creating basic session event."""
        session_id = "test_session_123"
        session_config = {
            "model": "gpt-4o-realtime-preview-2025-06-03",
            "voice": "alloy"
        }
        
        event = create_session_event(session_id, session_config)
        
        assert event["type"] == "session.created"
        assert "session" in event
        assert event["session"]["id"] == session_id
        assert event["session"]["model"] == "gpt-4o-realtime-preview-2025-06-03"
        assert event["session"]["voice"] == "alloy"
        assert "created_at" in event["session"]

    def test_create_session_event_timestamp(self):
        """Test that session event has proper timestamp."""
        session_id = "test_session_123"
        session_config = {}
        
        before_time = int(time.time() * 1000)
        event = create_session_event(session_id, session_config)
        after_time = int(time.time() * 1000)
        
        created_at = event["session"]["created_at"]
        assert before_time <= created_at <= after_time

    def test_create_session_event_complex_config(self):
        """Test creating session event with complex config."""
        session_id = "test_session_123"
        session_config = {
            "model": "gpt-4o-realtime-preview-2025-06-03",
            "modalities": ["text", "audio"],
            "voice": "nova",
            "temperature": 0.7,
            "tools": [{"name": "test_tool"}],
            "nested": {"key": "value"}
        }
        
        event = create_session_event(session_id, session_config)
        
        session = event["session"]
        assert session["model"] == "gpt-4o-realtime-preview-2025-06-03"
        assert session["modalities"] == ["text", "audio"]
        assert session["voice"] == "nova"
        assert session["temperature"] == 0.7
        assert session["tools"] == [{"name": "test_tool"}]
        assert session["nested"] == {"key": "value"}

    def test_create_response_event_basic(self):
        """Test creating basic response event."""
        response_id = "test_response_123"
        event_type = "text.delta"
        
        event = create_response_event(response_id, event_type)
        
        assert event["type"] == event_type
        assert event["response_id"] == response_id
        assert "item_id" in event
        assert "output_index" in event
        assert "content_index" in event

    def test_create_response_event_with_kwargs(self):
        """Test creating response event with additional kwargs."""
        response_id = "test_response_123"
        event_type = "text.delta"
        
        event = create_response_event(
            response_id, 
            event_type, 
            delta="Hello",
            final=False
        )
        
        assert event["type"] == event_type
        assert event["response_id"] == response_id
        assert event["delta"] == "Hello"
        assert event["final"] is False

    def test_create_response_event_item_id_generation(self):
        """Test that item_id is generated as UUID."""
        response_id = "test_response_123"
        event_type = "text.delta"
        
        event = create_response_event(response_id, event_type)
        
        # Check that item_id is a valid UUID
        try:
            uuid.UUID(event["item_id"])
        except ValueError:
            pytest.fail("item_id should be a valid UUID")

    def test_create_response_event_index_values(self):
        """Test that output_index and content_index have correct values."""
        response_id = "test_response_123"
        event_type = "text.delta"
        
        event = create_response_event(response_id, event_type)
        
        assert event["output_index"] == 0
        assert event["content_index"] == 0

    def test_create_response_event_complex_kwargs(self):
        """Test creating response event with complex kwargs."""
        response_id = "test_response_123"
        event_type = "function_call_arguments.delta"
        
        event = create_response_event(
            response_id,
            event_type,
            call_id="test_call_123",
            delta='{"param": "value"}',
            complex_param={"nested": {"key": "value"}},
            list_param=[1, 2, 3]
        )
        
        assert event["call_id"] == "test_call_123"
        assert event["delta"] == '{"param": "value"}'
        assert event["complex_param"] == {"nested": {"key": "value"}}
        assert event["list_param"] == [1, 2, 3]


class TestConstants:
    """Test re-exported constants."""

    def test_audio_constants_exported(self):
        """Test that audio constants are properly exported."""
        assert DEFAULT_AUDIO_CHUNK_SIZE is not None
        assert DEFAULT_SAMPLE_RATE is not None
        assert DEFAULT_CHANNELS is not None
        assert DEFAULT_BITS_PER_SAMPLE is not None
        
        # Check that they have reasonable values
        assert isinstance(DEFAULT_AUDIO_CHUNK_SIZE, int)
        assert isinstance(DEFAULT_SAMPLE_RATE, int)
        assert isinstance(DEFAULT_CHANNELS, int)
        assert isinstance(DEFAULT_BITS_PER_SAMPLE, int)
        
        assert DEFAULT_SAMPLE_RATE > 0
        assert DEFAULT_CHANNELS > 0
        assert DEFAULT_BITS_PER_SAMPLE > 0

    def test_audio_constants_values(self):
        """Test specific values of audio constants."""
        # These should match the values from opusagent.config.constants
        assert DEFAULT_SAMPLE_RATE == 16000
        assert DEFAULT_CHANNELS == 1
        assert DEFAULT_BITS_PER_SAMPLE == 16


class TestUtilityReExports:
    """Test re-exported utility functions."""

    def test_audio_utils_re_exports(self):
        """Test that AudioUtils functions are re-exported."""
        from opusagent.mock.realtime.utils import (
            create_simple_wav_data,
            chunk_audio_data,
            calculate_audio_duration
        )
        from opusagent.utils.audio_utils import AudioUtils
        
        # These should be the same as the AudioUtils methods
        assert create_simple_wav_data == AudioUtils.create_simple_wav_data
        assert chunk_audio_data == AudioUtils.chunk_audio_data
        assert calculate_audio_duration == AudioUtils.calculate_audio_duration

    def test_websocket_utils_re_exports(self):
        """Test that WebSocketUtils functions are re-exported."""
        from opusagent.mock.realtime.utils import (
            safe_send_event,
            format_event_log
        )
        from opusagent.utils.websocket_utils import WebSocketUtils
        
        # These should be the same as the WebSocketUtils methods
        assert safe_send_event == WebSocketUtils.safe_send_event
        assert format_event_log == WebSocketUtils.format_event_log

    def test_retry_utils_re_exports(self):
        """Test that RetryUtils functions are re-exported."""
        from opusagent.mock.realtime.utils import retry_operation
        from opusagent.utils.retry_utils import RetryUtils
        
        # This should be the same as the RetryUtils method
        assert retry_operation == RetryUtils.retry_operation


class TestIntegration:
    """Test integration between utility functions."""

    def test_create_complete_response_flow(self):
        """Test creating a complete response flow using utility functions."""
        # Create default config
        config = create_default_response_config()
        assert validate_response_config(config)
        
        # Create session event
        session_id = "test_session_123"
        session_config = {"model": "gpt-4o-realtime-preview-2025-06-03"}
        session_event = create_session_event(session_id, session_config)
        
        # Create response events
        response_id = "test_response_123"
        
        # Text delta event
        text_delta_event = create_response_event(
            response_id, 
            "text.delta", 
            delta="Hello"
        )
        
        # Text done event
        text_done_event = create_response_event(
            response_id,
            "text.done",
            text="Hello world"
        )
        
        # Error event (if needed)
        error_event = create_error_event(
            "RESPONSE_FAILED",
            "Response generation failed",
            {"reason": "timeout"}
        )
        
        # Verify all events have correct structure
        assert session_event["type"] == "session.created"
        assert text_delta_event["type"] == "text.delta"
        assert text_done_event["type"] == "text.done"
        assert error_event["type"] == "error"
        
        # Verify response_id consistency
        assert text_delta_event["response_id"] == response_id
        assert text_done_event["response_id"] == response_id

    def test_validation_with_event_creation(self):
        """Test validation with event creation patterns."""
        # Create a config that would be used in a real scenario
        config = {
            "text": "I'll help you with that request.",
            "delay_seconds": 0.03,
            "audio_chunk_delay": 0.15,
            "function_call": {
                "name": "process_request",
                "arguments": {"action": "help", "priority": "high"}
            }
        }
        
        # Validate the config
        assert validate_response_config(config)
        
        # Create events that would use this config
        response_id = "response_123"
        
        # Function call event
        function_event = create_response_event(
            response_id,
            "function_call_arguments.delta",
            delta=config["function_call"]["arguments"]
        )
        
        # Text event
        text_event = create_response_event(
            response_id,
            "text.delta",
            delta=config["text"][0]  # First character
        )
        
        # Verify events are properly structured
        assert function_event["response_id"] == response_id
        assert text_event["response_id"] == response_id
        assert "item_id" in function_event
        assert "item_id" in text_event

    def test_error_handling_integration(self):
        """Test error handling integration patterns."""
        # Simulate a scenario where validation fails
        invalid_config = {
            "delay_seconds": "invalid"  # Should be number
        }
        
        assert not validate_response_config(invalid_config)
        
        # Create error event for the validation failure
        error_event = create_error_event(
            "INVALID_CONFIG",
            "Configuration validation failed",
            {"field": "delay_seconds", "expected": "number", "got": "string"}
        )
        
        # Verify error event structure
        assert error_event["type"] == "error"
        assert error_event["code"] == "INVALID_CONFIG"
        assert error_event["details"]["field"] == "delay_seconds"
        assert error_event["details"]["expected"] == "number" 