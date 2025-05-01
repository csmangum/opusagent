"""
Unit tests for the AudioCodes Realtime Bridge.

These tests verify the functionality of the TelephonyRealtimeBridge class,
which connects AudioCodes WebSocket protocol with OpenAI Realtime API.
"""

import asyncio
import base64
import json
import os
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from fastapi import WebSocket

import fastagent.bot.telephony_realtime_bridge as bridge_module
from fastagent.bot.realtime_client import RealtimeClient
from fastagent.bot.telephony_realtime_bridge import TelephonyRealtimeBridge


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing."""
    mock = AsyncMock(spec=WebSocket)
    return mock


@pytest.fixture
def mock_client():
    """Create a mock RealtimeClient for testing."""
    mock = AsyncMock(spec=RealtimeClient)
    mock.connect.return_value = True
    return mock


@pytest.fixture
def bridge():
    """Create an TelephonyRealtimeBridge instance for testing."""
    return TelephonyRealtimeBridge()


@pytest.mark.asyncio
@patch.object(RealtimeClient, "__init__", return_value=None)
@patch.object(RealtimeClient, "connect")
@patch("asyncio.create_task")
async def test_create_client(
    mock_create_task, mock_connect, mock_init, bridge, mock_websocket
):
    """Test creating a new client."""
    conversation_id = "test-conv-123"

    # Set environment variable for test
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"}):
        with patch.object(bridge_module, "OPENAI_API_KEY", "test-api-key"):
            # Create a mock client with logger attribute
            mock_client = AsyncMock(spec=RealtimeClient)
            mock_client.logger = MagicMock()
            mock_client.connect.return_value = True

            # Patch RealtimeClient to return our mock
            with patch(
                "fastagent.bot.telephony_realtime_bridge.RealtimeClient",
                return_value=mock_client,
            ):
                await bridge.create_client(conversation_id, mock_websocket)

    # Verify client was stored in bridge
    assert conversation_id in bridge.clients
    assert bridge.websockets[conversation_id] == mock_websocket
    assert bridge.stream_ids[conversation_id] == 1

    # Verify response handling task was created
    mock_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_create_client_no_api_key(bridge, mock_websocket):
    """Test creating a client without API key set."""
    conversation_id = "test-conv-123"

    # Directly patch the module-level OPENAI_API_KEY variable
    with patch.object(bridge_module, "OPENAI_API_KEY", None):
        with pytest.raises(
            ValueError, match="OPENAI_API_KEY environment variable not set"
        ):
            await bridge.create_client(conversation_id, mock_websocket)


@pytest.mark.asyncio
async def test_send_audio_chunk(bridge, mock_client):
    """Test sending an audio chunk to OpenAI."""
    conversation_id = "test-conv-123"
    audio_chunk = base64.b64encode(b"test audio data").decode("utf-8")

    # Mock client in the bridge
    bridge.clients[conversation_id] = mock_client

    await bridge.send_audio_chunk(conversation_id, audio_chunk)

    # Verify audio was sent to the client
    mock_client.send_audio_chunk.assert_called_once_with(b"test audio data")


@pytest.mark.asyncio
async def test_send_audio_chunk_no_client(bridge):
    """Test sending audio with no client for the conversation."""
    conversation_id = "nonexistent"
    audio_chunk = base64.b64encode(b"test audio data").decode("utf-8")

    # This should not raise an exception
    await bridge.send_audio_chunk(conversation_id, audio_chunk)


class MockWebSocket:
    """A simple websocket mock that records sent messages."""

    def __init__(self, *args, **kwargs):
        self.sent_messages = []

    async def send_text(self, text):
        """Record the sent message."""
        self.sent_messages.append(text)
        return None


@pytest.mark.asyncio
async def test_handle_openai_responses(bridge, mock_client):
    """Test handling audio responses from OpenAI."""
    conversation_id = "test-conv-123"
    stream_id = 1

    # Create a proper mock WebSocket
    mock_websocket = MockWebSocket()

    # Setup the test
    bridge.clients[conversation_id] = mock_client
    bridge.websockets[conversation_id] = mock_websocket
    bridge.stream_ids[conversation_id] = stream_id

    # Mock client receiving audio chunks - we'll use a list that allows us to control the flow
    chunks = [b"audio chunk 1", b"audio chunk 2"]

    # Create a custom receive_audio_chunk method that returns our chunks then raises CancelledError
    async def mock_receive_audio_chunk():
        if chunks:
            return chunks.pop(0)
        raise asyncio.CancelledError()

    mock_client.receive_audio_chunk = mock_receive_audio_chunk

    # Run the response handler
    await bridge._handle_openai_responses(conversation_id)

    # Verify messages were sent
    assert len(mock_websocket.sent_messages) >= 3  # start, 2 chunks, stop

    # Verify playStream.start message was sent
    start_message = json.dumps(
        {
            "type": "playStream.start",
            "streamId": str(stream_id),
            "mediaFormat": "raw/lpcm16",
        }
    )
    assert start_message in mock_websocket.sent_messages

    # Verify audio chunks were sent
    chunk1_message = json.dumps(
        {
            "type": "playStream.chunk",
            "streamId": str(stream_id),
            "audioChunk": base64.b64encode(b"audio chunk 1").decode("utf-8"),
        }
    )
    assert chunk1_message in mock_websocket.sent_messages

    chunk2_message = json.dumps(
        {
            "type": "playStream.chunk",
            "streamId": str(stream_id),
            "audioChunk": base64.b64encode(b"audio chunk 2").decode("utf-8"),
        }
    )
    assert chunk2_message in mock_websocket.sent_messages

    # Verify playStream.stop was sent at the end
    stop_message = json.dumps({"type": "playStream.stop", "streamId": str(stream_id)})
    assert stop_message in mock_websocket.sent_messages


@pytest.mark.asyncio
async def test_handle_openai_responses_missing_components(bridge):
    """Test handling responses with missing client or websocket."""
    conversation_id = "missing"

    # This should not raise an exception but return early
    await bridge._handle_openai_responses(conversation_id)


@pytest.mark.asyncio
async def test_stop_stream(bridge):
    """Test stopping an audio stream."""
    conversation_id = "test-conv-123"
    stream_id = 2

    # Create a proper mock WebSocket
    mock_websocket = MockWebSocket()

    # Setup test
    bridge.websockets[conversation_id] = mock_websocket
    bridge.stream_ids[conversation_id] = stream_id

    await bridge.stop_stream(conversation_id)

    # Verify stop message was sent
    expected_message = json.dumps(
        {"type": "playStream.stop", "streamId": str(stream_id)}
    )
    assert expected_message in mock_websocket.sent_messages
    assert len(mock_websocket.sent_messages) == 1  # Only one message sent


@pytest.mark.asyncio
async def test_stop_stream_no_websocket(bridge):
    """Test stopping a stream with no websocket."""
    conversation_id = "nonexistent"

    # This should not raise an exception
    await bridge.stop_stream(conversation_id)


@pytest.mark.asyncio
async def test_close_client(bridge, mock_client):
    """Test closing a client."""
    conversation_id = "test-conv-123"

    # Setup test
    bridge.clients[conversation_id] = mock_client
    bridge.websockets[conversation_id] = MagicMock()
    bridge.stream_ids[conversation_id] = 1

    await bridge.close_client(conversation_id)

    # Verify client was closed
    mock_client.close.assert_called_once()

    # Verify client was removed from dictionaries
    assert conversation_id not in bridge.clients
    assert conversation_id not in bridge.websockets
    assert conversation_id not in bridge.stream_ids


@pytest.mark.asyncio
async def test_close_client_nonexistent(bridge):
    """Test closing a nonexistent client."""
    conversation_id = "nonexistent"

    # This should not raise an exception
    await bridge.close_client(conversation_id)


@pytest.mark.asyncio
async def test_handle_connection_lost(bridge, mock_client):
    """Test handling connection loss."""
    conversation_id = "test-conv-123"
    bridge.clients[conversation_id] = mock_client

    await bridge._handle_connection_lost(conversation_id)
    # Verify appropriate logging and state handling
    # TODO: Add assertions once reconnection logic is implemented


@pytest.mark.asyncio
async def test_handle_connection_restored(bridge, mock_client):
    """Test handling connection restoration."""
    conversation_id = "test-conv-123"
    bridge.clients[conversation_id] = mock_client

    await bridge._handle_connection_restored(conversation_id)
    # Verify appropriate logging and state handling


@pytest.mark.asyncio
async def test_cleanup_failed_client(bridge):
    """Test cleanup after client creation failure."""
    conversation_id = "test-conv-123"

    # Setup partial state
    bridge.clients[conversation_id] = MagicMock()
    bridge.websockets[conversation_id] = MagicMock()
    bridge.stream_ids[conversation_id] = 1
    bridge.response_tasks[conversation_id] = MagicMock()
    bridge.audio_latencies[conversation_id] = 0.0

    await bridge._cleanup_failed_client(conversation_id)

    # Verify all state was cleaned up
    assert conversation_id not in bridge.clients
    assert conversation_id not in bridge.websockets
    assert conversation_id not in bridge.stream_ids
    assert conversation_id not in bridge.response_tasks
    assert conversation_id not in bridge.audio_latencies


@pytest.mark.asyncio
async def test_send_audio_chunk_invalid_data(bridge, mock_client):
    """Test handling invalid audio data."""
    conversation_id = "test-conv-123"
    bridge.clients[conversation_id] = mock_client

    # Test with invalid base64 data
    invalid_chunk = "not-a-valid-base64-string"
    await bridge.send_audio_chunk(conversation_id, invalid_chunk)

    # Verify error was logged and handled gracefully
    # TODO: Add assertions for error logging


@pytest.mark.asyncio
async def test_handle_openai_responses_error_handling(bridge, mock_client):
    """Test error handling in response processing."""
    conversation_id = "test-conv-123"
    stream_id = 1

    # Setup test
    bridge.clients[conversation_id] = mock_client
    bridge.websockets[conversation_id] = MockWebSocket()
    bridge.stream_ids[conversation_id] = stream_id

    # Mock client to raise an exception
    async def mock_receive_audio_chunk():
        raise Exception("Test error")

    mock_client.receive_audio_chunk = mock_receive_audio_chunk

    # This should not raise an exception
    await bridge._handle_openai_responses(conversation_id)

    # Verify cleanup was performed
    # TODO: Add assertions for cleanup


@pytest.mark.asyncio
async def test_close_client_error_handling(bridge, mock_client, caplog):
    """Test error handling during client closure."""
    conversation_id = "test-conv-123"

    # Setup test
    bridge.clients[conversation_id] = mock_client
    bridge.websockets[conversation_id] = MagicMock()
    bridge.stream_ids[conversation_id] = 1

    # Mock client to raise an exception during close
    mock_client.close.side_effect = Exception("Test error")

    # This should not raise an exception
    await bridge.close_client(conversation_id)

    # Verify state was cleaned up despite error
    assert conversation_id not in bridge.clients
    assert conversation_id not in bridge.websockets
    assert conversation_id not in bridge.stream_ids

    # Verify error was logged
    assert any(
        f"Error closing client for conversation {conversation_id}" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_audio_latency_tracking(bridge, mock_client):
    """Test audio latency tracking functionality."""
    conversation_id = "test-conv-123"
    bridge.clients[conversation_id] = mock_client

    # Send multiple audio chunks
    for _ in range(3):
        audio_chunk = base64.b64encode(b"test audio data").decode("utf-8")
        await bridge.send_audio_chunk(conversation_id, audio_chunk)

    # Verify latency was tracked
    assert conversation_id in bridge.audio_latencies
    assert isinstance(bridge.audio_latencies[conversation_id], float)
