import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.websockets import WebSocketDisconnect

from fastagent.telephony_realtime_bridge import TelephonyRealtimeBridge


@pytest.fixture
def mock_websocket():
    mock = AsyncMock()
    mock.send_json = AsyncMock()
    mock.iter_text = AsyncMock()
    return mock


@pytest.fixture
def mock_openai_ws():
    mock = AsyncMock()
    mock.close_code = None
    mock.send = AsyncMock()
    return mock


@pytest.fixture
def bridge(mock_websocket, mock_openai_ws):
    return TelephonyRealtimeBridge(websocket=mock_websocket, openai_ws=mock_openai_ws)


@pytest.mark.asyncio
async def test_close_method(bridge):
    # Test closing when connections are active
    await bridge.close()

    # Verify both connections were closed
    bridge.openai_ws.close.assert_called_once()
    bridge.websocket.close.assert_called_once()
    assert bridge._closed is True


@pytest.mark.asyncio
async def test_close_method_with_errors(mock_websocket, mock_openai_ws):
    # Setup the mocks to raise exceptions when close is called
    mock_openai_ws.close.side_effect = Exception("OpenAI close error")
    mock_websocket.close.side_effect = Exception("WebSocket close error")

    bridge = TelephonyRealtimeBridge(mock_websocket, mock_openai_ws)

    # Should handle exceptions gracefully
    await bridge.close()
    assert bridge._closed is True


@pytest.mark.asyncio
async def test_close_method_already_closed(bridge):
    # Mark as already closed
    bridge._closed = True

    # Call close
    await bridge.close()

    # Verify no additional close attempts
    bridge.openai_ws.close.assert_not_called()
    bridge.websocket.close.assert_not_called()


@pytest.mark.asyncio
async def test_receive_from_telephony_start_event(bridge):
    # Setup mock data
    start_message = json.dumps(
        {"event": "start", "start": {"streamSid": "test-stream-id"}}
    )

    # Configure the mock
    bridge.websocket.iter_text.return_value = [start_message]

    # Run the method
    await bridge.receive_from_telephony()

    # Verify stream_sid was set
    assert bridge.stream_sid == "test-stream-id"
    # No audio should be sent
    bridge.openai_ws.send.assert_not_called()


@pytest.mark.asyncio
async def test_receive_from_telephony_stop_event(bridge):
    # Setup mock data
    stop_message = json.dumps({"event": "stop"})

    # Configure the mock
    bridge.websocket.iter_text.return_value = [stop_message]

    # Run the method
    await bridge.receive_from_telephony()

    # Verify bridge was closed
    assert bridge._closed is True
    bridge.openai_ws.close.assert_called_once()
    bridge.websocket.close.assert_called_once()


@pytest.mark.asyncio
async def test_receive_from_telephony_disconnect(bridge):
    # Simulate WebSocket disconnect
    bridge.websocket.iter_text.side_effect = WebSocketDisconnect()

    # Run the method
    await bridge.receive_from_telephony()

    # Verify bridge was closed
    assert bridge._closed is True
    bridge.openai_ws.close.assert_called_once()
    bridge.websocket.close.assert_called_once()


@pytest.mark.asyncio
async def test_receive_from_telephony_exception(bridge):
    # Simulate a generic exception
    bridge.websocket.iter_text.side_effect = Exception("Test error")

    # Run the method
    await bridge.receive_from_telephony()

    # Verify bridge was closed
    assert bridge._closed is True
    bridge.openai_ws.close.assert_called_once()
    bridge.websocket.close.assert_called_once()


@pytest.mark.asyncio
async def test_send_to_telephony_audio_delta(bridge):
    # Setup
    bridge.stream_sid = "test-stream-id"

    # Create mock response from OpenAI
    audio_delta_message = json.dumps(
        {"type": "response.audio.delta", "delta": "base64audio"}
    )

    # Configure the mock
    bridge.openai_ws.__aiter__.return_value = [audio_delta_message]

    # Run the method
    await bridge.send_to_telephony()

    # Verify audio was sent to telephony
    expected_audio_delta = {
        "event": "media",
        "streamSid": "test-stream-id",
        "media": {"payload": "base64audio"},
    }
    bridge.websocket.send_json.assert_called_once_with(expected_audio_delta)


@pytest.mark.asyncio
async def test_send_to_telephony_log_events(bridge):
    # Create mock log event from OpenAI
    log_event_message = json.dumps(
        {"type": "session.updated", "data": {"some": "data"}}
    )

    # Configure the mock
    bridge.openai_ws.__aiter__.return_value = [log_event_message]

    # Run the method
    await bridge.send_to_telephony()

    # Verify no audio was sent to telephony for log events
    bridge.websocket.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_send_to_telephony_exception_processing_audio(bridge):
    # Setup
    bridge.stream_sid = "test-stream-id"

    # Create mock response from OpenAI
    audio_delta_message = json.dumps(
        {"type": "response.audio.delta", "delta": "base64audio"}
    )

    # Configure the mock to return the message
    bridge.openai_ws.__aiter__.return_value = [audio_delta_message]
    # But make send_json raise an exception
    bridge.websocket.send_json.side_effect = Exception("Error sending audio")

    # Run the method
    await bridge.send_to_telephony()

    # Verify bridge was closed on error
    assert bridge._closed is True
    bridge.openai_ws.close.assert_called_once()
    bridge.websocket.close.assert_called_once()


@pytest.mark.asyncio
async def test_send_to_telephony_general_exception(bridge):
    # Configure the mock to raise an exception
    bridge.openai_ws.__aiter__.side_effect = Exception("General error")

    # Run the method
    await bridge.send_to_telephony()

    # Verify bridge was closed on error
    assert bridge._closed is True
    bridge.openai_ws.close.assert_called_once()
    bridge.websocket.close.assert_called_once()
