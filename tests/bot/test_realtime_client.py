"""
Unit tests for the OpenAI Realtime API client.

These tests verify the functionality of the RealtimeClient class,
which is responsible for connecting to the OpenAI Realtime API and
streaming audio data.
"""

import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from websockets.exceptions import ConnectionClosedError

from fastagent.models.openai_api import InputAudioBufferAppendEvent
from fastagent.realtime.realtime_client import RealtimeClient


@pytest.fixture
def mock_api_key():
    """Provide a mock API key for testing."""
    return "test-api-key"


@pytest.fixture
def mock_model():
    """Provide a mock model name for testing."""
    return "gpt-4o-realtime-preview-test"


@pytest.fixture
def realtime_client(mock_api_key, mock_model):
    """Create a RealtimeClient instance for testing."""
    return RealtimeClient(mock_api_key, mock_model)


@pytest.mark.asyncio
async def test_connect_success(realtime_client):
    """Test successful connection to the OpenAI Realtime API."""
    mock_ws = AsyncMock()
    mock_ws.closed = False
    mock_ws.ping = AsyncMock()
    mock_ws.pong = AsyncMock()
    mock_ws.recv = AsyncMock(return_value="{}")
    mock_ws.send = AsyncMock()
    mock_ws.sock = MagicMock()

    # Set up the client's URL and headers
    realtime_client._api_base = "wss://api.openai.com/v1/realtime"
    realtime_client._model = "gpt-4o-realtime-preview"
    realtime_client._headers = {
        "Authorization": f"Bearer {realtime_client._api_key}",
        "OpenAI-Beta": "realtime=v1"
    }
    realtime_client._logger = MagicMock()

    with patch("websockets.connect", return_value=mock_ws):
        with patch("asyncio.wait_for", return_value=mock_ws) as mock_wait_for:
            with patch("asyncio.create_task") as mock_create_task:
                # Patch _initialize_session to return True
                with patch.object(
                    realtime_client, "_initialize_session", return_value=True
                ):
                    result = await realtime_client.connect()

                    assert result is True
                    assert realtime_client._ws == mock_ws
                    assert realtime_client._connection_active is True
                    assert mock_create_task.call_count == 2  # _recv_loop and _heartbeat


@pytest.mark.asyncio
async def test_connect_failure(realtime_client):
    """Test connection failure to the OpenAI Realtime API."""
    with patch("websockets.connect", side_effect=Exception("Connection error")):
        result = await realtime_client.connect()

        assert result is False
        assert realtime_client._connection_active is False


@pytest.mark.asyncio
async def test_send_audio_chunk_success(realtime_client):
    """Test sending an audio chunk successfully."""
    realtime_client._ws = AsyncMock()
    realtime_client._connection_active = True
    realtime_client._ws.closed = False
    realtime_client._rate_limit = MagicMock()
    realtime_client._rate_limit.is_allowed.return_value = True
    realtime_client._audio_queue = asyncio.Queue(maxsize=32)
    realtime_client._audio_queue_size = 32
    realtime_client._is_closing = False
    realtime_client._logger = MagicMock()

    # Mock the send_event method
    with patch.object(realtime_client, "send_event", return_value="test-event-id"):
        mock_chunk = b"test audio data"
        result = await realtime_client.send_audio_chunk(mock_chunk)

        assert result is True
        # Check that send_event was called with the correct event
        realtime_client.send_event.assert_called_once()
        call_args = realtime_client.send_event.call_args[0][0]
        assert isinstance(call_args, InputAudioBufferAppendEvent)
        assert call_args.audio_data == "dGVzdCBhdWRpbyBkYXRh"  # base64 encoded "test audio data"


@pytest.mark.asyncio
async def test_send_audio_chunk_connection_closed(realtime_client):
    """Test sending an audio chunk when connection is closed."""
    realtime_client.ws = AsyncMock()
    realtime_client.ws.send.side_effect = ConnectionClosedError(None, None)
    realtime_client._connection_active = True

    with patch.object(realtime_client, "reconnect", return_value=False):
        mock_chunk = b"test audio data"
        result = await realtime_client.send_audio_chunk(mock_chunk)

        assert result is False


@pytest.mark.asyncio
async def test_receive_audio_chunk(realtime_client):
    """Test receiving an audio chunk."""
    mock_chunk = b"received audio data"

    # Put the mock chunk in the queue
    await realtime_client.audio_queue.put(mock_chunk)

    # Check that receive_audio_chunk returns the chunk
    result = await realtime_client.receive_audio_chunk()
    assert result == mock_chunk


@pytest.mark.asyncio
async def test_reconnect(realtime_client):
    """Test reconnection logic."""
    # Mock successful connection
    mock_ws = AsyncMock()
    mock_ws.closed = False
    mock_ws.close = AsyncMock()
    mock_ws.ping = AsyncMock()
    mock_ws.pong = AsyncMock()
    mock_ws.recv = AsyncMock(return_value="{}")
    mock_ws.send = AsyncMock()
    mock_ws.sock = MagicMock()

    # Set initial state
    realtime_client._reconnect_attempts = 0
    realtime_client._reconnecting = False
    realtime_client._ws = None  # Ensure WebSocket is None initially
    realtime_client._connection_active = True  # Set connection as active
    realtime_client._is_connected = False

    # Create an awaitable mock for websockets.connect
    async def mock_connect(*args, **kwargs):
        return mock_ws

    # Mock the task creation to prevent stalling
    mock_task = AsyncMock()
    mock_create_task = MagicMock(return_value=mock_task)

    # Mock websockets.connect to return our mock_ws
    with patch("websockets.connect", side_effect=mock_connect):
        # Mock _initialize_session to return True
        with patch.object(realtime_client, "_initialize_session", return_value=True):
            # Mock sleep to avoid delays
            with patch("asyncio.sleep"):
                # Mock create_task to prevent stalling
                with patch("asyncio.create_task", mock_create_task):
                    # Start reconnection
                    result = await realtime_client.reconnect()

                    # Check that reconnection was successful
                    assert result is True
                    # Check that reconnecting flag was reset
                    assert realtime_client._reconnecting is False
                    # Check that tasks were created
                    assert mock_create_task.call_count == 2  # _recv_loop and _heartbeat
                    # Check that connection was restored
                    assert realtime_client._is_connected is True

    # Reset reconnect attempts
    realtime_client._reconnect_attempts = 0
    realtime_client._reconnecting = False

    # Test max reconnect attempts
    realtime_client._reconnect_attempts = 5  # MAX_RECONNECT_ATTEMPTS
    result = await realtime_client.reconnect()

    assert result is False


@pytest.mark.asyncio
async def test_close(realtime_client):
    """Test closing the client."""
    mock_ws = AsyncMock()
    mock_ws.closed = False
    mock_ws.close = AsyncMock()
    realtime_client._ws = mock_ws
    
    # Create proper mock tasks
    mock_recv_task = AsyncMock()
    mock_recv_task.done.return_value = False
    mock_heartbeat_task = AsyncMock()
    mock_heartbeat_task.done.return_value = False
    realtime_client._recv_task = mock_recv_task
    realtime_client._heartbeat_task = mock_heartbeat_task
    
    realtime_client._connection_active = True
    realtime_client._is_closing = False
    realtime_client._is_connected = True
    realtime_client._audio_queue = asyncio.Queue(maxsize=32)
    realtime_client._logger = MagicMock()

    await realtime_client.close()

    assert realtime_client._is_closing is True
    assert realtime_client._connection_active is False
    mock_recv_task.cancel.assert_called_once()
    mock_heartbeat_task.cancel.assert_called_once()
    mock_ws.close.assert_called_once()  # Verify close was called on the mock
