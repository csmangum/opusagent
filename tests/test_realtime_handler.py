"""Unit tests for the RealtimeHandler class."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import websockets
from websockets.exceptions import ConnectionClosed
from opusagent.audio_stream_handler import AudioStreamHandler
from opusagent.call_recorder import CallRecorder
from opusagent.event_router import EventRouter
from opusagent.function_handler import FunctionHandler
from opusagent.models.openai_api import (
    ResponseDoneEvent,
    ServerEventType,
)
from opusagent.realtime_handler import RealtimeHandler
from opusagent.session_manager import SessionManager
from opusagent.transcript_manager import TranscriptManager


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket client."""
    return AsyncMock()


@pytest.fixture
def mock_audio_handler():
    """Create a mock AudioStreamHandler."""
    return AsyncMock(spec=AudioStreamHandler)


@pytest.fixture
def mock_function_handler():
    """Create a mock FunctionHandler."""
    handler = MagicMock(spec=FunctionHandler)
    handler.active_function_calls = {}
    return handler


@pytest.fixture
def mock_session_manager():
    """Create a mock SessionManager."""
    return AsyncMock(spec=SessionManager)


@pytest.fixture
def mock_event_router():
    """Create a mock EventRouter."""
    return MagicMock(spec=EventRouter)


@pytest.fixture
def mock_transcript_manager():
    """Create a mock TranscriptManager."""
    return AsyncMock(spec=TranscriptManager)


@pytest.fixture
def realtime_handler(
    mock_websocket,
    mock_audio_handler,
    mock_function_handler,
    mock_session_manager,
    mock_event_router,
    mock_transcript_manager,
):
    """Create a RealtimeHandler instance with mocked dependencies."""
    return RealtimeHandler(
        realtime_websocket=mock_websocket,
        audio_handler=mock_audio_handler,
        function_handler=mock_function_handler,
        session_manager=mock_session_manager,
        event_router=mock_event_router,
        transcript_manager=mock_transcript_manager,
    )


@pytest.mark.asyncio
async def test_handle_session_update(realtime_handler):
    """Test handling of session update events."""
    # Test SESSION_UPDATED
    await realtime_handler.handle_session_update(
        {"type": ServerEventType.SESSION_UPDATED}
    )

    # Test SESSION_CREATED
    await realtime_handler.handle_session_update(
        {"type": ServerEventType.SESSION_CREATED}
    )


@pytest.mark.asyncio
async def test_handle_speech_detection(realtime_handler):
    """Test handling of speech detection events."""
    # Test speech started
    await realtime_handler.handle_speech_detection(
        {"type": ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED}
    )

    # Test speech stopped
    await realtime_handler.handle_speech_detection(
        {"type": ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED}
    )

    # Test audio buffer committed
    await realtime_handler.handle_speech_detection(
        {"type": ServerEventType.INPUT_AUDIO_BUFFER_COMMITTED}
    )


@pytest.mark.asyncio
async def test_handle_audio_response_delta(realtime_handler):
    """Test handling of audio response delta events."""
    response_dict = {"type": ServerEventType.RESPONSE_AUDIO_DELTA, "delta": "test_audio"}
    await realtime_handler.handle_audio_response_delta(response_dict)
    realtime_handler.audio_handler.handle_outgoing_audio.assert_called_once_with(
        response_dict
    )


@pytest.mark.asyncio
async def test_handle_audio_response_completion(realtime_handler):
    """Test handling of audio response completion events."""
    await realtime_handler.handle_audio_response_completion({})
    realtime_handler.audio_handler.stop_stream.assert_called_once()


@pytest.mark.asyncio
async def test_handle_text_and_transcript(realtime_handler):
    """Test handling of text and transcript events."""
    # Test text delta
    await realtime_handler.handle_text_and_transcript(
        {"type": ServerEventType.RESPONSE_TEXT_DELTA, "delta": "test_text"}
    )

    # Test audio transcript delta
    await realtime_handler.handle_text_and_transcript(
        {"type": ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA, "delta": "test_transcript"}
    )


@pytest.mark.asyncio
async def test_handle_response_created(realtime_handler):
    """Test handling of response created events."""
    response_dict = {
        "response": {"id": "test_response_id"},
    }
    await realtime_handler.handle_response_created(response_dict)
    assert realtime_handler.response_active is True
    assert realtime_handler.response_id_tracker == "test_response_id"


@pytest.mark.asyncio
async def test_handle_response_completion(realtime_handler):
    """Test handling of response completion events."""
    # Set up initial state
    realtime_handler.response_active = True
    realtime_handler.pending_user_input = {"audio_committed": True}

    # Test response completion
    response_dict = {
        "response": {"id": "test_response_id"},
    }
    await realtime_handler.handle_response_completion(response_dict)

    assert realtime_handler.response_active is False
    assert realtime_handler.pending_user_input is None
    realtime_handler.audio_handler.stop_stream.assert_called_once()
    realtime_handler.session_manager.create_response.assert_called_once()


@pytest.mark.asyncio
async def test_handle_output_item_added(realtime_handler):
    """Test handling of output item added events."""
    # Test regular output item
    await realtime_handler.handle_output_item_added({"item": {"type": "text"}})

    # Test function call item
    function_call = {
        "item": {
            "type": "function_call",
            "call_id": "test_call_id",
            "name": "test_function",
            "id": "test_item_id",
        },
        "output_index": 0,
        "response_id": "test_response_id",
    }
    await realtime_handler.handle_output_item_added(function_call)

    assert "test_call_id" in realtime_handler.function_handler.active_function_calls
    assert (
        realtime_handler.function_handler.active_function_calls["test_call_id"][
            "function_name"
        ]
        == "test_function"
    )


@pytest.mark.asyncio
async def test_handle_audio_transcript_delta(realtime_handler):
    """Test handling of audio transcript delta events."""
    response_dict = {"delta": "test_transcript"}
    await realtime_handler.handle_audio_transcript_delta(response_dict)
    realtime_handler.transcript_manager.handle_output_transcript_delta.assert_called_once_with(
        "test_transcript"
    )


@pytest.mark.asyncio
async def test_handle_audio_transcript_done(realtime_handler):
    """Test handling of audio transcript completion events."""
    await realtime_handler.handle_audio_transcript_done({})
    realtime_handler.transcript_manager.handle_output_transcript_completed.assert_called_once()


@pytest.mark.asyncio
async def test_handle_input_audio_transcription_delta(realtime_handler):
    """Test handling of input audio transcription delta events."""
    response_dict = {"delta": "test_transcript"}
    await realtime_handler.handle_input_audio_transcription_delta(response_dict)
    realtime_handler.transcript_manager.handle_input_transcript_delta.assert_called_once_with(
        "test_transcript"
    )


@pytest.mark.asyncio
async def test_handle_input_audio_transcription_completed(realtime_handler):
    """Test handling of input audio transcription completion events."""
    await realtime_handler.handle_input_audio_transcription_completed({})
    realtime_handler.transcript_manager.handle_input_transcript_completed.assert_called_once()


@pytest.mark.asyncio
async def test_close(realtime_handler):
    """Test closing the realtime handler."""
    await realtime_handler.close()
    assert realtime_handler._closed is True
    realtime_handler.audio_handler.close.assert_called_once()


@pytest.mark.asyncio
async def test_receive_from_realtime(realtime_handler):
    """Test receiving and processing events from the realtime API."""
    # Mock WebSocket messages
    messages = [
        json.dumps({"type": ServerEventType.SESSION_UPDATED}),
        json.dumps({"type": ServerEventType.RESPONSE_CREATED}),
    ]
    realtime_handler.realtime_websocket.__aiter__.return_value = messages

    # Test normal operation
    await realtime_handler.receive_from_realtime()
    assert realtime_handler.event_router.handle_realtime_event.call_count == 2

    # Test WebSocket closed
    realtime_handler.realtime_websocket.__aiter__.side_effect = ConnectionClosed(
        rcvd=None,
        sent=None,
        rcvd_then_sent=None
    )
    await realtime_handler.receive_from_realtime()
    assert realtime_handler._closed is True

    # Test TypeError
    realtime_handler._closed = False
    realtime_handler.realtime_websocket.__aiter__.side_effect = TypeError()
    await realtime_handler.receive_from_realtime()
    assert realtime_handler._closed is True

    # Test general exception
    realtime_handler._closed = False
    realtime_handler.realtime_websocket.__aiter__.side_effect = Exception("test")
    await realtime_handler.receive_from_realtime()
    assert realtime_handler._closed is True 