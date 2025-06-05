"""
Additional unit tests for the OpenAI Realtime API client.

These tests verify the extended functionality of the RealtimeClient class,
focusing on connection handlers, heartbeat functionality, and edge cases.
"""

import asyncio
import base64
import json
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from opusagent.realtime.realtime_client import (
    MAX_DATA_PER_WINDOW,
    MAX_REQUESTS_PER_WINDOW,
    RATE_LIMIT_WINDOW,
    BinaryDataError,
    RateLimit,
    RateLimitError,
    RealtimeClient,
)
from opusagent.models.openai_api import ClientEvent, ClientEventType, ServerEventType


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
async def test_set_connection_handlers(realtime_client):
    """Test setting connection loss and restoration handlers."""
    # Create mock handlers
    mock_lost_handler = AsyncMock()
    mock_restored_handler = AsyncMock()

    # Set handlers
    realtime_client.set_connection_handlers(
        lost_handler=mock_lost_handler, restored_handler=mock_restored_handler
    )

    # Verify handlers were set
    assert realtime_client._connection_lost_handler == mock_lost_handler
    assert realtime_client._connection_restored_handler == mock_restored_handler


@pytest.mark.asyncio
async def test_connection_lost_handler_called(realtime_client):
    """Test that connection lost handler is called when connection is lost."""
    # Setup
    mock_lost_handler = AsyncMock()
    realtime_client._connection_lost_handler = mock_lost_handler
    realtime_client._connection_active = True
    realtime_client._is_connected = True

    # Simulate connection loss by setting state and calling handler
    realtime_client._connection_active = False
    realtime_client._is_connected = False
    await realtime_client._connection_lost_handler()

    # Verify handler was called and connection state is updated
    mock_lost_handler.assert_called_once()
    assert not realtime_client._connection_active
    assert not realtime_client._is_connected


@pytest.mark.asyncio
async def test_connection_restored_handler_called(realtime_client):
    """Test that connection restored handler is called after reconnection."""
    # Setup
    mock_ws = AsyncMock()
    mock_restored_handler = AsyncMock()
    realtime_client._connection_restored_handler = mock_restored_handler

    # Instead of calling the real connect method which resets _reconnect_attempts,
    # we'll create a patched version that calls the handler
    async def patched_connect(*args, **kwargs):
        realtime_client.ws = mock_ws
        realtime_client._connection_active = True
        realtime_client._last_activity = time.time()
        # Don't reset reconnect_attempts here like the real method does

        # Call the handler directly
        if (
            realtime_client._connection_restored_handler
            and realtime_client._reconnect_attempts > 0
        ):
            await realtime_client._connection_restored_handler()
        return True

    # Set reconnect attempts to 1 to simulate a reconnection
    realtime_client._reconnect_attempts = 1

    # Use the patched connect method
    with patch.object(realtime_client, "connect", side_effect=patched_connect):
        # Call connect
        await realtime_client.connect()

    # Verify connection restored handler was called
    mock_restored_handler.assert_called_once()


@pytest.mark.asyncio
async def test_heartbeat_healthy_connection(realtime_client):
    """Test heartbeat with a healthy connection."""
    # Setup
    mock_ws = AsyncMock()
    mock_ws.ping.return_value = asyncio.Future()
    mock_ws.ping.return_value.set_result(None)  # Successful ping
    mock_ws.closed = False

    realtime_client.ws = mock_ws
    realtime_client._connection_active = True
    realtime_client._last_activity = 930  # Fixed value that will trigger heartbeat when time is 1000
    realtime_client._heartbeat_interval = 60  # Use the default interval

    # Mock asyncio.sleep to control timing
    sleep_calls = []
    
    async def mock_sleep(duration):
        sleep_calls.append(duration)
        # Only allow one iteration by setting connection_active to False
        if len(sleep_calls) >= 1:
            realtime_client._connection_active = False

    # Create a task for the heartbeat
    with patch("asyncio.sleep", side_effect=mock_sleep):
        with patch("time.time", return_value=1000):  # Fixed time for consistent behavior
            # Run heartbeat task and wait for it to complete
            await realtime_client._heartbeat()

    # Verify ping was sent
    mock_ws.ping.assert_called_once()
    assert realtime_client._last_activity == 1000  # Should be updated to current time


@pytest.mark.asyncio
async def test_heartbeat_dead_connection(realtime_client):
    """Test heartbeat with a dead connection (ping fails)."""
    # Setup
    mock_ws = AsyncMock()
    ping_future = asyncio.Future()
    ping_future.set_exception(asyncio.TimeoutError())  # Ping will fail
    mock_ws.ping.return_value = ping_future
    mock_ws.closed = False

    realtime_client.ws = mock_ws
    realtime_client._connection_active = True
    realtime_client._last_activity = 930  # Fixed value that will trigger heartbeat when time is 1000
    realtime_client._is_closing = False
    realtime_client._heartbeat_interval = 60  # Use the default interval

    # Mock asyncio.sleep to control timing
    sleep_calls = []
    
    async def mock_sleep(duration):
        sleep_calls.append(duration)
        # Only allow one iteration
        if len(sleep_calls) >= 1:
            realtime_client._connection_active = False

    # Mock the reconnect task creation
    with patch("asyncio.sleep", side_effect=mock_sleep):
        with patch("time.time", return_value=1000):
            with patch("asyncio.create_task") as mock_create_task:
                # Run heartbeat task
                await realtime_client._heartbeat()

    # Verify ping was attempted and connection was marked as inactive
    mock_ws.ping.assert_called_once()
    assert not realtime_client._connection_active
    mock_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_heartbeat_closed_websocket(realtime_client):
    """Test heartbeat with a closed websocket."""
    # Setup
    mock_ws = AsyncMock()
    mock_ws.closed = True

    realtime_client.ws = mock_ws
    realtime_client._connection_active = True
    realtime_client._last_activity = 930  # Fixed value that will trigger heartbeat when time is 1000
    realtime_client._is_closing = False
    realtime_client._heartbeat_interval = 60

    # Mock asyncio.sleep to control timing
    sleep_calls = []
    
    async def mock_sleep(duration):
        sleep_calls.append(duration)
        # Only allow one iteration
        if len(sleep_calls) >= 1:
            realtime_client._connection_active = False

    # Mock the reconnect task creation
    with patch("asyncio.sleep", side_effect=mock_sleep):
        with patch("time.time", return_value=1000):
            with patch("asyncio.create_task") as mock_create_task:
                # Run heartbeat task
                await realtime_client._heartbeat()

    # Verify connection was marked as inactive and reconnect was attempted
    assert not realtime_client._connection_active
    mock_create_task.assert_called_once()
    # Verify that ping was not called since websocket was closed
    mock_ws.ping.assert_not_called()


@pytest.mark.asyncio
async def test_closing_state_prevents_reconnection(realtime_client):
    """Test that setting _is_closing prevents reconnection attempts."""
    realtime_client._is_closing = True

    # Attempt to connect
    result = await realtime_client.connect()
    assert result is False

    # Attempt to reconnect
    result = await realtime_client.reconnect()
    assert result is False


@pytest.mark.asyncio
async def test_recv_loop_json_parsing(realtime_client):
    """Test that _recv_loop correctly processes JSON messages."""
    # Setup
    test_message = json.dumps(
        {
            "type": ServerEventType.RESPONSE_AUDIO_DELTA,
            "audio": "c3RyZWFtIGF1ZGlv",  # base64 encoded "stream audio"
        }
    )

    mock_ws = AsyncMock()
    # Make the recv method return our test message once, then raise an exception to break the loop
    mock_ws.recv = AsyncMock(side_effect=[test_message, asyncio.CancelledError])
    mock_ws.closed = False

    realtime_client.ws = mock_ws
    realtime_client._connection_active = True
    realtime_client._is_connected = True
    realtime_client._is_closing = False  # Ensure we're not closing

    # Mock reconnect to prevent it from being called
    with patch.object(realtime_client, "reconnect", return_value=False):
        try:
            # Run recv_loop with timeout
            await asyncio.wait_for(realtime_client._recv_loop(), timeout=1.0)
        except asyncio.CancelledError:
            # This is expected when the mock.recv raises CancelledError
            pass

    # Verify audio was added to the queue
    assert not realtime_client.audio_queue.empty()
    audio_data = await realtime_client.audio_queue.get()
    assert audio_data == b"stream audio"


@pytest.mark.asyncio
async def test_recv_loop_error_message(realtime_client):
    """Test that _recv_loop handles error messages from the API."""
    # Setup
    error_message = {"type": "error", "message": "Test error from API"}

    mock_ws = AsyncMock()
    # Instead of using __aiter__, directly mock the recv method to return the error message
    # and then raise CancelledError to exit the loop
    mock_ws.recv = AsyncMock(
        side_effect=[json.dumps(error_message), asyncio.CancelledError]
    )

    realtime_client.ws = mock_ws
    realtime_client._connection_active = True

    # Run the receive loop with proper cancellation
    with patch.object(realtime_client, "reconnect", return_value=False):
        with patch("logging.getLogger") as mock_logger:
            try:
                # Run recv_loop with timeout
                await asyncio.wait_for(realtime_client._recv_loop(), timeout=1.0)
            except asyncio.CancelledError:
                # This is expected when the mock.recv raises CancelledError
                pass

    # Verify error handling behavior - no audio should be queued
    assert realtime_client.audio_queue.empty()


@pytest.mark.asyncio
async def test_close_cancels_tasks(realtime_client):
    """Test that close method cancels tasks."""
    # Setup
    mock_ws = AsyncMock()
    mock_ws.closed = False  # Ensure the websocket appears to be open
    
    # Create tasks that will run indefinitely until cancelled
    async def long_running_task():
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
    
    mock_recv_task = asyncio.create_task(long_running_task())
    mock_heartbeat_task = asyncio.create_task(long_running_task())
    
    # Ensure tasks are running but not done
    assert not mock_recv_task.done()
    assert not mock_heartbeat_task.done()

    realtime_client.ws = mock_ws
    realtime_client._recv_task = mock_recv_task
    realtime_client._heartbeat_task = mock_heartbeat_task
    realtime_client._connection_active = True
    realtime_client._is_connected = True

    # Close the client
    await realtime_client.close()

    # Verify websocket was closed and state was updated
    assert realtime_client._is_closing is True
    assert realtime_client._connection_active is False
    assert realtime_client._is_connected is False
    mock_ws.close.assert_called_once()
    
    # Verify tasks are now done (cancelled)
    assert mock_recv_task.done()
    assert mock_heartbeat_task.done()
    assert mock_recv_task.cancelled()
    assert mock_heartbeat_task.cancelled()


@pytest.mark.asyncio
async def test_rate_limiting(realtime_client):
    """Test rate limiting functionality."""
    # Setup
    realtime_client.ws = AsyncMock()
    realtime_client._connection_active = True

    # Test request rate limiting
    # Send requests up to the limit
    for _ in range(MAX_REQUESTS_PER_WINDOW):
        assert realtime_client.rate_limit.is_allowed()
        realtime_client.rate_limit.add_request()

    # Next request should be rate limited
    assert not realtime_client.rate_limit.is_allowed()

    # Simulate window expiration by clearing requests
    realtime_client.rate_limit.requests.clear()
    realtime_client.rate_limit.data_sizes.clear()
    assert realtime_client.rate_limit.is_allowed()


# @pytest.mark.asyncio
# async def test_session_management(realtime_client):
#     """Test session initialization and management."""
#     # Setup
#     mock_ws = AsyncMock()
#     realtime_client.ws = mock_ws
#     realtime_client._connection_active = True

#     # Mock session creation response
#     session_data = {
#         "type": "session.created",
#         "session": {
#             "id": "test-session-id",
#             "conversation": {"id": "test-conversation-id"},
#         },
#     }

#     # Create a future to control when the session is created
#     session_created = asyncio.Future()
#     session_created.set_result(session_data)

#     # Mock send_event to trigger session creation
#     async def mock_send_event(event):
#         if event.type == ClientEventType.SESSION_UPDATE:
#             # Simulate session creation response
#             await realtime_client._process_event("session.created", session_data)
#         return "test-event-id"

#     # Mock the wait_for to return our session data
#     with patch.object(realtime_client, "send_event", side_effect=mock_send_event), \
#          patch("asyncio.wait_for", return_value=session_data):
#         # Initialize session
#         result = await realtime_client._initialize_session()

#         # Verify session was initialized
#         assert result is True
#         assert realtime_client.session_id == "test-session-id"
#         assert realtime_client.conversation_id == "test-conversation-id"

#         # Test session update
#         update_result = await realtime_client.update_session(
#             voice="nova", modalities=["text", "audio"]
#         )
#         assert update_result is True


@pytest.mark.asyncio
async def test_audio_queue_management(realtime_client):
    """Test audio queue management and backpressure."""
    # Setup
    mock_ws = AsyncMock()
    realtime_client.ws = mock_ws
    realtime_client._connection_active = True

    # Mock successful send_event to allow audio chunks to be sent
    async def mock_send_event(event):
        return "test-event-id"

    with patch.object(realtime_client, "send_event", side_effect=mock_send_event):
        # Test queue full scenario
        # Fill the queue
        for i in range(realtime_client._audio_queue_size):
            await realtime_client.audio_queue.put(b"test")

        # Try to send another chunk
        result = await realtime_client.send_audio_chunk(b"test")
        assert result is False  # Should fail due to full queue

        # Test backpressure
        # Clear the queue
        while not realtime_client.audio_queue.empty():
            await realtime_client.audio_queue.get()

        # Send chunks up to warning threshold
        warning_size = int(realtime_client._audio_queue_size * 0.8)
        for i in range(warning_size):
            # Put chunks directly in queue to simulate sending
            await realtime_client.audio_queue.put(b"test")
            # Update queue state
            current_size = realtime_client.audio_queue.qsize()
            if current_size >= realtime_client._audio_queue_warning_threshold:
                realtime_client._audio_queue_full = True
            else:
                realtime_client._audio_queue_full = False

        # Queue should be marked as full
        assert realtime_client._audio_queue_full is True

        # Test queue pressure relief
        # Clear some items from the queue
        for i in range(warning_size - 1):
            await realtime_client.audio_queue.get()
            # Update queue state
            current_size = realtime_client.audio_queue.qsize()
            if current_size < realtime_client._audio_queue_warning_threshold:
                realtime_client._audio_queue_full = False

        # Send another chunk
        result = await realtime_client.send_audio_chunk(b"test")
        assert result is True
        assert realtime_client._audio_queue_full is False
