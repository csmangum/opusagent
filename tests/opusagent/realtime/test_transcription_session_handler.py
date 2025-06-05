"""
Unit tests for the TranscriptionSessionHandler class.

These tests verify the functionality of the transcription session handler,
including validation, configuration updates, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any, Optional

from opusagent.realtime.handlers.client.transcription_session_handler import (
    TranscriptionSessionHandler
)

@pytest.fixture
def mock_send_event():
    """Fixture providing a mock send_event callback."""
    return AsyncMock()

@pytest.fixture
def handler(mock_send_event):
    """Fixture providing a TranscriptionSessionHandler instance."""
    return TranscriptionSessionHandler(mock_send_event)

@pytest.mark.asyncio
async def test_handle_invalid_event_type(handler, mock_send_event):
    """Test handling of invalid event type."""
    event = {
        "type": "invalid_type",
        "event_id": "test_123",
        "session": {}
    }
    
    await handler.handle(event)
    
    mock_send_event.assert_called_once()
    error_response = mock_send_event.call_args[0][0]
    assert error_response["type"] == "error"
    assert error_response["error"]["code"] == "invalid_event_type"

@pytest.mark.asyncio
async def test_handle_invalid_session_config(handler, mock_send_event):
    """Test handling of invalid session configuration."""
    event = {
        "type": "transcription_session.update",
        "event_id": "test_123",
        "session": "not_a_dict"
    }
    
    await handler.handle(event)
    
    mock_send_event.assert_called_once()
    error_response = mock_send_event.call_args[0][0]
    assert error_response["type"] == "error"
    assert error_response["error"]["code"] == "invalid_session_config"

@pytest.mark.asyncio
async def test_handle_invalid_audio_format(handler, mock_send_event):
    """Test handling of invalid audio format."""
    event = {
        "type": "transcription_session.update",
        "event_id": "test_123",
        "session": {
            "input_audio_format": "invalid_format"
        }
    }
    
    await handler.handle(event)
    
    mock_send_event.assert_called_once()
    error_response = mock_send_event.call_args[0][0]
    assert error_response["type"] == "error"
    assert error_response["error"]["code"] == "invalid_audio_format"

@pytest.mark.asyncio
async def test_handle_valid_audio_format(handler, mock_send_event):
    """Test handling of valid audio format."""
    event = {
        "type": "transcription_session.update",
        "event_id": "test_123",
        "session": {
            "input_audio_format": "pcm16"
        }
    }
    
    await handler.handle(event)
    
    mock_send_event.assert_called_once()
    response = mock_send_event.call_args[0][0]
    assert response["type"] == "transcription_session.updated"
    assert response["session"]["input_audio_format"] == "pcm16"

@pytest.mark.asyncio
async def test_handle_invalid_transcription_config(handler, mock_send_event):
    """Test handling of invalid transcription configuration."""
    event = {
        "type": "transcription_session.update",
        "event_id": "test_123",
        "session": {
            "input_audio_transcription": "not_a_dict"
        }
    }
    
    await handler.handle(event)
    
    mock_send_event.assert_called_once()
    error_response = mock_send_event.call_args[0][0]
    assert error_response["type"] == "error"
    assert error_response["error"]["code"] == "invalid_transcription_config"

@pytest.mark.asyncio
async def test_handle_missing_transcription_model(handler, mock_send_event):
    """Test handling of missing transcription model."""
    event = {
        "type": "transcription_session.update",
        "event_id": "test_123",
        "session": {
            "input_audio_transcription": {
                "prompt": "test prompt"
            }
        }
    }
    
    await handler.handle(event)
    
    mock_send_event.assert_called_once()
    error_response = mock_send_event.call_args[0][0]
    assert error_response["type"] == "error"
    assert error_response["error"]["code"] == "missing_transcription_model"

@pytest.mark.asyncio
async def test_handle_valid_transcription_config(handler, mock_send_event):
    """Test handling of valid transcription configuration."""
    event = {
        "type": "transcription_session.update",
        "event_id": "test_123",
        "session": {
            "input_audio_transcription": {
                "model": "gpt-4o-transcribe",
                "prompt": "test prompt",
                "language": "en"
            }
        }
    }
    
    await handler.handle(event)
    
    mock_send_event.assert_called_once()
    response = mock_send_event.call_args[0][0]
    assert response["type"] == "transcription_session.updated"
    transcription_config = response["session"]["input_audio_transcription"]
    assert transcription_config["model"] == "gpt-4o-transcribe"
    assert transcription_config["prompt"] == "test prompt"
    assert transcription_config["language"] == "en"

@pytest.mark.asyncio
async def test_handle_invalid_turn_detection_config(handler, mock_send_event):
    """Test handling of invalid turn detection configuration."""
    event = {
        "type": "transcription_session.update",
        "event_id": "test_123",
        "session": {
            "turn_detection": "not_a_dict"
        }
    }
    
    await handler.handle(event)
    
    mock_send_event.assert_called_once()
    error_response = mock_send_event.call_args[0][0]
    assert error_response["type"] == "error"
    assert error_response["error"]["code"] == "invalid_turn_detection_config"

@pytest.mark.asyncio
async def test_handle_invalid_turn_detection_type(handler, mock_send_event):
    """Test handling of invalid turn detection type."""
    event = {
        "type": "transcription_session.update",
        "event_id": "test_123",
        "session": {
            "turn_detection": {
                "type": "invalid_type"
            }
        }
    }
    
    await handler.handle(event)
    
    mock_send_event.assert_called_once()
    error_response = mock_send_event.call_args[0][0]
    assert error_response["type"] == "error"
    assert error_response["error"]["code"] == "invalid_turn_detection_type"

@pytest.mark.asyncio
async def test_handle_valid_turn_detection_config(handler, mock_send_event):
    """Test handling of valid turn detection configuration."""
    event = {
        "type": "transcription_session.update",
        "event_id": "test_123",
        "session": {
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.7,
                "prefix_padding_ms": 400,
                "silence_duration_ms": 600,
                "create_response": False
            }
        }
    }
    
    await handler.handle(event)
    
    mock_send_event.assert_called_once()
    response = mock_send_event.call_args[0][0]
    assert response["type"] == "transcription_session.updated"
    turn_detection = response["session"]["turn_detection"]
    assert turn_detection["type"] == "server_vad"
    assert turn_detection["threshold"] == 0.7
    assert turn_detection["prefix_padding_ms"] == 400
    assert turn_detection["silence_duration_ms"] == 600
    assert turn_detection["create_response"] is False

@pytest.mark.asyncio
async def test_handle_invalid_noise_reduction_config(handler, mock_send_event):
    """Test handling of invalid noise reduction configuration."""
    event = {
        "type": "transcription_session.update",
        "event_id": "test_123",
        "session": {
            "input_audio_noise_reduction": "not_a_dict"
        }
    }
    
    await handler.handle(event)
    
    mock_send_event.assert_called_once()
    error_response = mock_send_event.call_args[0][0]
    assert error_response["type"] == "error"
    assert error_response["error"]["code"] == "invalid_noise_reduction_config"

@pytest.mark.asyncio
async def test_handle_valid_noise_reduction_config(handler, mock_send_event):
    """Test handling of valid noise reduction configuration."""
    event = {
        "type": "transcription_session.update",
        "event_id": "test_123",
        "session": {
            "input_audio_noise_reduction": {
                "type": "near_field"
            }
        }
    }
    
    await handler.handle(event)
    
    mock_send_event.assert_called_once()
    response = mock_send_event.call_args[0][0]
    assert response["type"] == "transcription_session.updated"
    noise_reduction = response["session"]["input_audio_noise_reduction"]
    assert noise_reduction["type"] == "near_field"

@pytest.mark.asyncio
async def test_handle_invalid_include_config(handler, mock_send_event):
    """Test handling of invalid include configuration."""
    event = {
        "type": "transcription_session.update",
        "event_id": "test_123",
        "session": {
            "include": "not_a_list"
        }
    }
    
    await handler.handle(event)
    
    mock_send_event.assert_called_once()
    error_response = mock_send_event.call_args[0][0]
    assert error_response["type"] == "error"
    assert error_response["error"]["code"] == "invalid_include_config"

@pytest.mark.asyncio
async def test_handle_valid_include_config(handler, mock_send_event):
    """Test handling of valid include configuration."""
    event = {
        "type": "transcription_session.update",
        "event_id": "test_123",
        "session": {
            "include": [
                "item.input_audio_transcription.logprobs",
                "item.input_audio_transcription.timestamps"
            ]
        }
    }
    
    await handler.handle(event)
    
    mock_send_event.assert_called_once()
    response = mock_send_event.call_args[0][0]
    assert response["type"] == "transcription_session.updated"
    include = response["session"]["include"]
    assert len(include) == 2
    assert "item.input_audio_transcription.logprobs" in include
    assert "item.input_audio_transcription.timestamps" in include

@pytest.mark.asyncio
async def test_handle_complete_config(handler, mock_send_event):
    """Test handling of a complete configuration."""
    event = {
        "type": "transcription_session.update",
        "event_id": "test_123",
        "session": {
            "input_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": "gpt-4o-transcribe",
                "prompt": "test prompt",
                "language": "en"
            },
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.7,
                "prefix_padding_ms": 400,
                "silence_duration_ms": 600,
                "create_response": False
            },
            "input_audio_noise_reduction": {
                "type": "near_field"
            },
            "include": [
                "item.input_audio_transcription.logprobs"
            ]
        }
    }
    
    await handler.handle(event)
    
    mock_send_event.assert_called_once()
    response = mock_send_event.call_args[0][0]
    assert response["type"] == "transcription_session.updated"
    session = response["session"]
    
    assert session["input_audio_format"] == "pcm16"
    assert session["input_audio_transcription"]["model"] == "gpt-4o-transcribe"
    assert session["turn_detection"]["type"] == "server_vad"
    assert session["input_audio_noise_reduction"]["type"] == "near_field"
    assert "item.input_audio_transcription.logprobs" in session["include"]

@pytest.mark.asyncio
async def test_handle_null_configurations(handler, mock_send_event):
    """Test handling of null configurations."""
    event = {
        "type": "transcription_session.update",
        "event_id": "test_123",
        "session": {
            "input_audio_transcription": None,
            "turn_detection": None,
            "input_audio_noise_reduction": None
        }
    }
    
    await handler.handle(event)
    
    mock_send_event.assert_called_once()
    response = mock_send_event.call_args[0][0]
    assert response["type"] == "transcription_session.updated"
    session = response["session"]
    
    assert session["input_audio_transcription"] is None
    assert session["turn_detection"] is None
    assert session["input_audio_noise_reduction"] is None 