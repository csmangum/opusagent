"""
Unit tests for the OpenAI Realtime API client.

These tests verify the functionality of the RealtimeClient class,
which is responsible for connecting to the OpenAI Realtime API and
streaming audio data.
"""

import asyncio
import base64
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from websockets.exceptions import ConnectionClosedError

from opusagent.models.openai_api import InputAudioBufferAppendEvent
from opusagent.realtime.realtime_client import RealtimeClient


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
        "OpenAI-Beta": "realtime=v1",
    }
    realtime_client._logger = MagicMock()

    async def mock_connect(*args, **kwargs):
        return mock_ws

    with patch("websockets.connect", side_effect=mock_connect):
        with patch("asyncio.wait_for", return_value=mock_ws) as mock_wait_for:
            with patch(
                "asyncio.create_task", new_callable=AsyncMock
            ) as mock_create_task:
                with patch.object(
                    realtime_client, "_initialize_session", return_value=True
                ):
                    result = await realtime_client.connect()

                    assert result is True
                    assert realtime_client.ws == mock_ws
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
    # Set up client state for successful operation
    realtime_client._connection_active = True
    realtime_client._is_closing = False
    realtime_client._audio_queue_size = 32
    
    # Mock the audio queue to report it's not full
    mock_audio_queue = MagicMock()
    mock_audio_queue.qsize.return_value = 10  # Queue has space
    realtime_client._audio_queue = mock_audio_queue
    
    # Mock the rate limit to allow the request
    mock_rate_limit = MagicMock()
    mock_rate_limit.is_allowed.return_value = True
    realtime_client._rate_limit = mock_rate_limit
    
    # Mock the send_event method to succeed
    realtime_client.send_event = AsyncMock()
    
    # Test audio data
    test_audio_data = b"test audio chunk data"
    expected_base64 = base64.b64encode(test_audio_data).decode("utf-8")
    
    # Call the method
    result = await realtime_client.send_audio_chunk(test_audio_data)
    
    # Verify success
    assert result is True
    
    # Verify rate limit was checked
    mock_rate_limit.is_allowed.assert_called_once()
    
    # Verify audio queue size was checked
    mock_audio_queue.qsize.assert_called_once()
    
    # Verify send_event was called with correct event
    realtime_client.send_event.assert_called_once()
    sent_event = realtime_client.send_event.call_args[0][0]
    
    # Verify the event is of correct type and contains expected data
    assert isinstance(sent_event, InputAudioBufferAppendEvent)
    assert sent_event.audio == expected_base64
    
    # Verify rate limit was updated with correct data size
    mock_rate_limit.add_request.assert_called_once_with(len(test_audio_data))


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
    realtime_client.ws = mock_ws

    # Create proper mock tasks using asyncio.Future and mock cancel
    mock_recv_task = asyncio.Future()
    mock_recv_task.cancel = MagicMock()
    mock_heartbeat_task = asyncio.Future()
    mock_heartbeat_task.cancel = MagicMock()

    # Mark the tasks as done after cancel is called
    def cancel_and_set_cancelled(fut):
        fut.set_exception(asyncio.CancelledError())

    mock_recv_task.cancel.side_effect = lambda: cancel_and_set_cancelled(mock_recv_task)
    mock_heartbeat_task.cancel.side_effect = lambda: cancel_and_set_cancelled(
        mock_heartbeat_task
    )

    realtime_client._recv_task = mock_recv_task
    realtime_client._heartbeat_task = mock_heartbeat_task

    realtime_client._connection_active = True
    realtime_client._is_closing = False
    realtime_client._is_connected = True
    realtime_client._audio_queue = asyncio.Queue(maxsize=32)
    realtime_client._audio_queue_size = realtime_client._audio_queue.maxsize
    realtime_client._logger = MagicMock()

    await realtime_client.close()

    assert realtime_client._is_closing is True
    assert realtime_client._connection_active is False
    mock_recv_task.cancel.assert_called_once()
    mock_heartbeat_task.cancel.assert_called_once()
    mock_ws.close.assert_called_once()  # Verify close was called on the mock
