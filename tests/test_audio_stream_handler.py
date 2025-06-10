"""Unit tests for the AudioStreamHandler class.

This module contains tests for the AudioStreamHandler class, which manages
audio streams between telephony client and OpenAI Realtime API.
"""

import base64
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.websockets import WebSocketState

from opusagent.audio_stream_handler import AudioStreamHandler
from opusagent.models.audiocodes_api import (
    PlayStreamChunkMessage,
    PlayStreamStartMessage,
    PlayStreamStopMessage,
    TelephonyEventType,
)
from opusagent.models.openai_api import (
    InputAudioBufferAppendEvent,
    InputAudioBufferCommitEvent,
    ResponseAudioDeltaEvent,
)

# Test data
TEST_CONVERSATION_ID = "test-conversation-123"
TEST_MEDIA_FORMAT = "raw/lpcm16"
TEST_STREAM_ID = "test-stream-456"
TEST_RESPONSE_ID = "test-response-789"
TEST_ITEM_ID = "test-item-101"
TEST_OUTPUT_INDEX = 0
TEST_CONTENT_INDEX = 0

# Create a test audio chunk that's already at the minimum required size (3200 bytes)
TEST_AUDIO_CHUNK = b"test audio data" * 200  # 3200 bytes of test data
TEST_AUDIO_CHUNK_B64 = base64.b64encode(TEST_AUDIO_CHUNK).decode("utf-8")
TEST_AUDIO_DELTA = "test audio delta" * 200  # 3200 bytes of test data

@pytest.fixture
def mock_telephony_websocket():
    """Create a mock telephony WebSocket."""
    websocket = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.client_state = WebSocketState.CONNECTED
    return websocket

@pytest.fixture
def mock_realtime_websocket():
    """Create a mock OpenAI Realtime WebSocket."""
    websocket = AsyncMock()
    websocket.send = AsyncMock()
    websocket.close_code = None
    return websocket

@pytest.fixture
def mock_call_recorder():
    """Create a mock call recorder."""
    recorder = AsyncMock()
    recorder.record_caller_audio = AsyncMock()
    recorder.record_bot_audio = AsyncMock()
    return recorder

@pytest.fixture
def audio_handler(mock_telephony_websocket, mock_realtime_websocket, mock_call_recorder):
    """Create an AudioStreamHandler instance with mocked dependencies."""
    return AudioStreamHandler(
        telephony_websocket=mock_telephony_websocket,
        realtime_websocket=mock_realtime_websocket,
        call_recorder=mock_call_recorder,
    )

@pytest.mark.asyncio
async def test_initialize_stream(audio_handler):
    """Test stream initialization."""
    await audio_handler.initialize_stream(TEST_CONVERSATION_ID, TEST_MEDIA_FORMAT)
    
    assert audio_handler.conversation_id == TEST_CONVERSATION_ID
    assert audio_handler.media_format == TEST_MEDIA_FORMAT
    assert audio_handler.audio_chunks_sent == 0
    assert audio_handler.total_audio_bytes_sent == 0

@pytest.mark.asyncio
async def test_handle_incoming_audio_success(audio_handler):
    """Test successful handling of incoming audio."""
    await audio_handler.initialize_stream(TEST_CONVERSATION_ID, TEST_MEDIA_FORMAT)
    
    # Create test data
    data = {"audioChunk": TEST_AUDIO_CHUNK_B64}
    
    # Call the method
    await audio_handler.handle_incoming_audio(data)
    
    # Verify the audio was processed and sent
    assert audio_handler.audio_chunks_sent == 1
    assert audio_handler.total_audio_bytes_sent == 3200  # Should be exactly 3200 bytes
    
    # Verify the audio was sent to OpenAI
    audio_handler.realtime_websocket.send.assert_called_once()
    sent_data = json.loads(audio_handler.realtime_websocket.send.call_args[0][0])
    assert sent_data["type"] == "input_audio_buffer.append"
    assert len(base64.b64decode(sent_data["audio"])) == 3200  # Verify size after decoding
    
    # Verify the audio was recorded - should be the padded version
    audio_handler.call_recorder.record_caller_audio.assert_called_once()
    recorded_audio = audio_handler.call_recorder.record_caller_audio.call_args[0][0]
    assert len(base64.b64decode(recorded_audio)) == 3200  # Verify size after decoding

@pytest.mark.asyncio
async def test_handle_incoming_audio_small_chunk(audio_handler):
    """Test handling of small audio chunks (padding required)."""
    await audio_handler.initialize_stream(TEST_CONVERSATION_ID, TEST_MEDIA_FORMAT)
    
    # Create a small audio chunk (less than 3200 bytes)
    small_chunk = b"small" * 100  # 500 bytes
    small_chunk_b64 = base64.b64encode(small_chunk).decode("utf-8")
    data = {"audioChunk": small_chunk_b64}
    
    # Call the method
    await audio_handler.handle_incoming_audio(data)
    
    # Verify the audio was padded and sent
    assert audio_handler.audio_chunks_sent == 1
    assert audio_handler.total_audio_bytes_sent == 3200  # Should be padded to minimum size
    
    # Verify the padded audio was sent to OpenAI
    audio_handler.realtime_websocket.send.assert_called_once()
    sent_data = json.loads(audio_handler.realtime_websocket.send.call_args[0][0])
    assert sent_data["type"] == "input_audio_buffer.append"
    assert len(base64.b64decode(sent_data["audio"])) == 3200

@pytest.mark.asyncio
async def test_handle_outgoing_audio_success(audio_handler):
    """Test successful handling of outgoing audio."""
    await audio_handler.initialize_stream(TEST_CONVERSATION_ID, TEST_MEDIA_FORMAT)
    
    # Create test data with all required fields
    response_dict = {
        "type": "response.audio.delta",
        "response_id": TEST_RESPONSE_ID,
        "item_id": TEST_ITEM_ID,
        "output_index": TEST_OUTPUT_INDEX,
        "content_index": TEST_CONTENT_INDEX,
        "delta": TEST_AUDIO_DELTA
    }
    
    # Call the method
    await audio_handler.handle_outgoing_audio(response_dict)
    
    # Verify stream was started
    assert audio_handler.active_stream_id is not None
    audio_handler.telephony_websocket.send_json.assert_called()
    
    # Verify the audio was sent to telephony client
    calls = audio_handler.telephony_websocket.send_json.call_args_list
    assert len(calls) >= 2  # Should have at least start and chunk messages
    
    # Verify stream start message
    start_message = calls[0][0][0]
    assert start_message["type"] == TelephonyEventType.PLAY_STREAM_START
    assert start_message["conversationId"] == TEST_CONVERSATION_ID
    assert start_message["mediaFormat"] == TEST_MEDIA_FORMAT
    
    # Verify audio chunk message
    chunk_message = calls[1][0][0]
    assert chunk_message["type"] == TelephonyEventType.PLAY_STREAM_CHUNK
    assert chunk_message["conversationId"] == TEST_CONVERSATION_ID
    assert chunk_message["audioChunk"] == TEST_AUDIO_DELTA
    
    # Verify the audio was recorded
    audio_handler.call_recorder.record_bot_audio.assert_called_once_with(TEST_AUDIO_DELTA)

@pytest.mark.asyncio
async def test_commit_audio_buffer_success(audio_handler):
    """Test successful audio buffer commit."""
    await audio_handler.initialize_stream(TEST_CONVERSATION_ID, TEST_MEDIA_FORMAT)
    
    # Send some audio first
    data = {"audioChunk": TEST_AUDIO_CHUNK_B64}
    await audio_handler.handle_incoming_audio(data)
    
    # Commit the buffer
    await audio_handler.commit_audio_buffer()
    
    # Verify the commit was sent
    audio_handler.realtime_websocket.send.assert_called()
    sent_data = json.loads(audio_handler.realtime_websocket.send.call_args[0][0])
    assert sent_data["type"] == "input_audio_buffer.commit"

@pytest.mark.asyncio
async def test_commit_audio_buffer_insufficient_data(audio_handler):
    """Test audio buffer commit with insufficient data."""
    await audio_handler.initialize_stream(TEST_CONVERSATION_ID, TEST_MEDIA_FORMAT)
    
    # Try to commit without sending any audio
    await audio_handler.commit_audio_buffer()
    
    # Verify no commit was sent
    audio_handler.realtime_websocket.send.assert_not_called()

@pytest.mark.asyncio
async def test_stop_stream_success(audio_handler):
    """Test successful stream stop."""
    await audio_handler.initialize_stream(TEST_CONVERSATION_ID, TEST_MEDIA_FORMAT)
    
    # Start a stream by sending some audio
    response_dict = {
        "type": "response.audio.delta",
        "response_id": TEST_RESPONSE_ID,
        "item_id": TEST_ITEM_ID,
        "output_index": TEST_OUTPUT_INDEX,
        "content_index": TEST_CONTENT_INDEX,
        "delta": TEST_AUDIO_DELTA
    }
    await audio_handler.handle_outgoing_audio(response_dict)
    
    # Stop the stream
    await audio_handler.stop_stream()
    
    # Verify stream was stopped
    assert audio_handler.active_stream_id is None
    audio_handler.telephony_websocket.send_json.assert_called()
    
    # Verify stop message
    stop_message = audio_handler.telephony_websocket.send_json.call_args[0][0]
    assert stop_message["type"] == TelephonyEventType.PLAY_STREAM_STOP
    assert stop_message["conversationId"] == TEST_CONVERSATION_ID

@pytest.mark.asyncio
async def test_close_success(audio_handler):
    """Test successful handler close."""
    await audio_handler.initialize_stream(TEST_CONVERSATION_ID, TEST_MEDIA_FORMAT)
    
    # Start a stream
    response_dict = {
        "type": "response.audio.delta",
        "response_id": TEST_RESPONSE_ID,
        "item_id": TEST_ITEM_ID,
        "output_index": TEST_OUTPUT_INDEX,
        "content_index": TEST_CONTENT_INDEX,
        "delta": TEST_AUDIO_DELTA
    }
    await audio_handler.handle_outgoing_audio(response_dict)
    
    # Close the handler
    await audio_handler.close()
    
    # Verify handler is closed
    assert audio_handler._closed
    assert audio_handler.active_stream_id is None

@pytest.mark.asyncio
async def test_handle_incoming_audio_closed_connection(audio_handler):
    """Test handling incoming audio with closed connection."""
    await audio_handler.initialize_stream(TEST_CONVERSATION_ID, TEST_MEDIA_FORMAT)
    audio_handler._closed = True
    
    # Try to send audio
    data = {"audioChunk": TEST_AUDIO_CHUNK_B64}
    await audio_handler.handle_incoming_audio(data)
    
    # Verify no audio was sent
    audio_handler.realtime_websocket.send.assert_not_called()
    assert audio_handler.audio_chunks_sent == 0

@pytest.mark.asyncio
async def test_handle_outgoing_audio_closed_connection(audio_handler):
    """Test handling outgoing audio with closed connection."""
    await audio_handler.initialize_stream(TEST_CONVERSATION_ID, TEST_MEDIA_FORMAT)
    audio_handler._closed = True
    
    # Try to send audio
    response_dict = {
        "type": "response.audio.delta",
        "response_id": TEST_RESPONSE_ID,
        "item_id": TEST_ITEM_ID,
        "output_index": TEST_OUTPUT_INDEX,
        "content_index": TEST_CONTENT_INDEX,
        "delta": TEST_AUDIO_DELTA
    }
    await audio_handler.handle_outgoing_audio(response_dict)
    
    # Verify no audio was sent
    audio_handler.telephony_websocket.send_json.assert_not_called()
    assert audio_handler.active_stream_id is None

@pytest.mark.asyncio
async def test_get_audio_stats(audio_handler):
    """Test getting audio statistics."""
    await audio_handler.initialize_stream(TEST_CONVERSATION_ID, TEST_MEDIA_FORMAT)
    
    # Send some audio
    data = {"audioChunk": TEST_AUDIO_CHUNK_B64}
    await audio_handler.handle_incoming_audio(data)
    
    # Get stats
    stats = audio_handler.get_audio_stats()
    
    # Verify stats
    assert stats["audio_chunks_sent"] == 1
    assert stats["total_audio_bytes_sent"] == 3200
    assert stats["total_duration_ms"] == 100.0  # 3200 bytes = 100ms at 16kHz 16-bit

@pytest.mark.asyncio
async def test_websocket_closed_detection(audio_handler):
    """Test WebSocket closed state detection."""
    # Test with disconnected state
    audio_handler.telephony_websocket.client_state = WebSocketState.DISCONNECTED
    assert audio_handler._is_websocket_closed()
    
    # Test with None websocket
    audio_handler.telephony_websocket = None
    assert audio_handler._is_websocket_closed()
    
    # Test with connected state
    audio_handler.telephony_websocket = AsyncMock()
    audio_handler.telephony_websocket.client_state = WebSocketState.CONNECTED
    assert not audio_handler._is_websocket_closed() 