import pytest
from unittest.mock import AsyncMock, MagicMock
import base64
from opusagent.realtime.handlers.client.input_audio_buffer_handler import InputAudioBufferHandler

@pytest.fixture
def mock_send_event():
    return AsyncMock()

@pytest.fixture
def handler(mock_send_event):
    return InputAudioBufferHandler(mock_send_event)

@pytest.mark.asyncio
async def test_handle_append_valid_audio(handler, mock_send_event):
    # Create a small valid audio chunk (1KB)
    audio_data = b"test_audio_data" * 64  # ~1KB
    base64_audio = base64.b64encode(audio_data).decode()
    
    event = {
        "event_id": "test_event_1",
        "type": "input_audio_buffer.append",
        "audio": base64_audio
    }
    
    await handler.handle_append(event)
    
    # Verify audio was added to buffer
    assert len(handler.audio_buffer) == 1
    assert handler.audio_buffer[0] == base64_audio
    
    # Verify no error was sent
    mock_send_event.assert_not_called()

@pytest.mark.asyncio
async def test_handle_append_invalid_base64(handler, mock_send_event):
    event = {
        "event_id": "test_event_2",
        "type": "input_audio_buffer.append",
        "audio": "invalid_base64_data"
    }
    
    await handler.handle_append(event)
    
    # Verify error was sent
    mock_send_event.assert_called_once()
    error_event = mock_send_event.call_args[0][0]
    assert error_event["type"] == "error"
    assert error_event["event_id"] == "test_event_2"
    assert error_event["code"] == "invalid_request_error"
    assert "Failed to append audio" in error_event["message"]
    
    # Verify buffer is empty
    assert len(handler.audio_buffer) == 0

@pytest.mark.asyncio
async def test_handle_append_exceeds_size_limit(handler, mock_send_event):
    # Create audio data that exceeds 15 MiB
    audio_data = b"x" * (16 * 1024 * 1024)  # 16 MiB
    base64_audio = base64.b64encode(audio_data).decode()
    
    event = {
        "event_id": "test_event_3",
        "type": "input_audio_buffer.append",
        "audio": base64_audio
    }
    
    await handler.handle_append(event)
    
    # Verify error was sent
    mock_send_event.assert_called_once()
    error_event = mock_send_event.call_args[0][0]
    assert error_event["type"] == "error"
    assert error_event["event_id"] == "test_event_3"
    assert error_event["code"] == "invalid_request_error"
    assert "exceeds maximum size" in error_event["message"]
    
    # Verify buffer is empty
    assert len(handler.audio_buffer) == 0

@pytest.mark.asyncio
async def test_handle_commit_success(handler, mock_send_event):
    # First append some audio
    audio_data = b"test_audio_data"
    base64_audio = base64.b64encode(audio_data).decode()
    handler.audio_buffer.append(base64_audio)
    
    event = {
        "event_id": "test_event_4",
        "type": "input_audio_buffer.commit"
    }
    
    await handler.handle_commit(event)
    
    # Verify committed event was sent
    mock_send_event.assert_called_once()
    commit_event = mock_send_event.call_args[0][0]
    assert commit_event["type"] == "input_audio_buffer.committed"
    assert commit_event["event_id"] == "test_event_4"
    
    # Verify buffer was cleared
    assert len(handler.audio_buffer) == 0

@pytest.mark.asyncio
async def test_handle_commit_empty_buffer(handler, mock_send_event):
    event = {
        "event_id": "test_event_5",
        "type": "input_audio_buffer.commit"
    }
    
    await handler.handle_commit(event)
    
    # Verify error was sent
    mock_send_event.assert_called_once()
    error_event = mock_send_event.call_args[0][0]
    assert error_event["type"] == "error"
    assert error_event["event_id"] == "test_event_5"
    assert error_event["code"] == "invalid_request_error"
    assert "No audio data to commit" in error_event["message"]

@pytest.mark.asyncio
async def test_handle_clear(handler, mock_send_event):
    # First append some audio
    audio_data = b"test_audio_data"
    base64_audio = base64.b64encode(audio_data).decode()
    handler.audio_buffer.append(base64_audio)
    
    event = {
        "event_id": "test_event_6",
        "type": "input_audio_buffer.clear"
    }
    
    await handler.handle_clear(event)
    
    # Verify cleared event was sent
    mock_send_event.assert_called_once()
    clear_event = mock_send_event.call_args[0][0]
    assert clear_event["type"] == "input_audio_buffer.cleared"
    assert clear_event["event_id"] == "test_event_6"
    
    # Verify buffer was cleared
    assert len(handler.audio_buffer) == 0 