from unittest.mock import AsyncMock, MagicMock

import pytest

from opusagent.realtime.handlers.client.session_update_handler import (
    SessionUpdateHandler,
)


@pytest.fixture
def session_config():
    return {
        "model": "gpt-4",
        "modalities": ["text"],
        "instructions": "Default instructions",
        "input_audio_format": "pcm16",
        "output_audio_format": "pcm16",
        "tool_choice": "auto",
        "temperature": 0.7,
        "max_response_output_tokens": 1000,
    }


@pytest.fixture
def send_event_mock():
    return AsyncMock()


@pytest.fixture
def handler(session_config, send_event_mock):
    return SessionUpdateHandler(session_config, send_event_mock)


@pytest.mark.asyncio
async def test_valid_session_update(handler, send_event_mock):
    """Test a valid session update with all fields."""
    event = {
        "type": "session.update",
        "event_id": "test-123",
        "session": {
            "modalities": ["text", "audio"],
            "instructions": "New instructions",
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_alaw",
            "tool_choice": "required",
            "temperature": 1.0,
            "max_response_output_tokens": 2000,
        },
    }

    await handler.handle(event)

    # Verify the session was updated
    assert handler.session_config["modalities"] == ["text", "audio"]
    assert handler.session_config["instructions"] == "New instructions"
    assert handler.session_config["input_audio_format"] == "g711_ulaw"
    assert handler.session_config["output_audio_format"] == "g711_alaw"
    assert handler.session_config["tool_choice"] == "required"
    assert handler.session_config["temperature"] == 1.0
    assert handler.session_config["max_response_output_tokens"] == 2000

    # Verify the session.updated event was sent
    send_event_mock.assert_called_once()
    response = send_event_mock.call_args[0][0]
    assert response["type"] == "session.updated"
    assert response["event_id"] == "test-123"


@pytest.mark.asyncio
async def test_clear_instructions(handler, send_event_mock):
    """Test clearing instructions with empty string."""
    event = {"type": "session.update", "session": {"instructions": ""}}

    await handler.handle(event)
    assert handler.session_config["instructions"] == ""


@pytest.mark.asyncio
async def test_invalid_model_change(handler, send_event_mock):
    """Test that model cannot be changed after initialization."""
    event = {
        "type": "session.update",
        "event_id": "test-123",
        "session": {"model": "gpt-3.5-turbo"},
    }

    await handler.handle(event)

    # Verify error response was sent
    send_event_mock.assert_called_once()
    response = send_event_mock.call_args[0][0]
    assert response["type"] == "error"
    assert response["code"] == "invalid_request_error"
    assert "Model cannot be changed" in response["message"]


@pytest.mark.asyncio
async def test_invalid_temperature(handler, send_event_mock):
    """Test temperature validation."""
    event = {
        "type": "session.update",
        "event_id": "test-123",
        "session": {"temperature": 2.0},  # Invalid temperature
    }

    await handler.handle(event)

    send_event_mock.assert_called_once()
    response = send_event_mock.call_args[0][0]
    assert response["type"] == "error"
    assert response["code"] == "invalid_request_error"
    assert "Temperature must be between" in response["message"]


@pytest.mark.asyncio
async def test_invalid_audio_format(handler, send_event_mock):
    """Test audio format validation."""
    event = {
        "type": "session.update",
        "event_id": "test-123",
        "session": {"input_audio_format": "invalid_format"},
    }

    await handler.handle(event)

    send_event_mock.assert_called_once()
    response = send_event_mock.call_args[0][0]
    assert response["type"] == "error"
    assert response["code"] == "invalid_request_error"
    assert "input_audio_format must be one of" in response["message"]


@pytest.mark.asyncio
async def test_invalid_tool_choice(handler, send_event_mock):
    """Test tool choice validation."""
    event = {
        "type": "session.update",
        "event_id": "test-123",
        "session": {"tool_choice": "invalid_choice"},
    }

    await handler.handle(event)

    send_event_mock.assert_called_once()
    response = send_event_mock.call_args[0][0]
    assert response["type"] == "error"
    assert response["code"] == "invalid_request_error"
    assert "tool_choice must be" in response["message"]


@pytest.mark.asyncio
async def test_invalid_modalities(handler, send_event_mock):
    """Test modalities validation."""
    event = {
        "type": "session.update",
        "event_id": "test-123",
        "session": {"modalities": ["invalid_modality"]},
    }

    await handler.handle(event)

    send_event_mock.assert_called_once()
    response = send_event_mock.call_args[0][0]
    assert response["type"] == "error"
    assert response["code"] == "invalid_request_error"
    assert "modalities must only contain values from" in response["message"]


@pytest.mark.asyncio
async def test_invalid_max_tokens(handler, send_event_mock):
    """Test max_response_output_tokens validation."""
    event = {
        "type": "session.update",
        "event_id": "test-123",
        "session": {"max_response_output_tokens": 5000},  # Invalid value
    }

    await handler.handle(event)

    send_event_mock.assert_called_once()
    response = send_event_mock.call_args[0][0]
    assert response["type"] == "error"
    assert response["code"] == "invalid_request_error"
    assert "max_response_output_tokens must be between" in response["message"]


@pytest.mark.asyncio
async def test_valid_max_tokens_inf(handler, send_event_mock):
    """Test that 'inf' is a valid value for max_response_output_tokens."""
    event = {"type": "session.update", "session": {"max_response_output_tokens": "inf"}}

    await handler.handle(event)
    assert handler.session_config["max_response_output_tokens"] == "inf"


@pytest.mark.asyncio
async def test_partial_update(handler, send_event_mock):
    """Test updating only some fields."""
    event = {
        "type": "session.update",
        "session": {"temperature": 0.8, "tool_choice": "none"},
    }

    await handler.handle(event)

    # Verify only specified fields were updated
    assert handler.session_config["temperature"] == 0.8
    assert handler.session_config["tool_choice"] == "none"
    # Verify other fields remain unchanged
    assert handler.session_config["model"] == "gpt-4"
    assert handler.session_config["modalities"] == ["text"]


@pytest.mark.asyncio
async def test_internal_error_handling(handler, send_event_mock):
    """Test handling of unexpected errors."""
    # Force an error by making session_config read-only
    handler.session_config = MagicMock()
    handler.session_config.__setitem__.side_effect = Exception("Test error")

    event = {
        "type": "session.update",
        "event_id": "test-123",
        "session": {"temperature": 0.8},
    }

    await handler.handle(event)

    send_event_mock.assert_called_once()
    response = send_event_mock.call_args[0][0]
    assert response["type"] == "error"
    assert response["code"] == "internal_error"
    assert "Failed to update session" in response["message"]
