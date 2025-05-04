import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.websockets import WebSocketDisconnect

from fastagent.telephony_realtime_bridge import TelephonyRealtimeBridge
from fastagent.models.audiocodes_api import (
    PlayStreamChunkMessage,
    PlayStreamStartMessage,
    PlayStreamStopMessage,
    SessionAcceptedResponse,
    UserStreamStartedResponse,
    UserStreamStoppedResponse,
)
from fastagent.models.openai_api import (
    ConversationItemContentParam,
    ConversationItemCreateEvent,
    ConversationItemParam,
    InputAudioBufferAppendEvent,
    InputAudioBufferCommitEvent,
    LogEventType,
    MessageRole,
    ResponseAudioDeltaEvent,
    ResponseCreateEvent,
    ResponseCreateOptions,
    ResponseDoneEvent,
    ResponseTextDeltaEvent,
    ServerEventType,
    SessionConfig,
    SessionUpdateEvent,
)


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
    return TelephonyRealtimeBridge(
        telephony_websocket=mock_websocket, realtime_websocket=mock_openai_ws
    )


@pytest.mark.asyncio
async def test_close_method(bridge):
    # Test closing when connections are active
    await bridge.close()

    # Verify both connections were closed
    bridge.realtime_websocket.close.assert_called_once()
    bridge.telephony_websocket.close.assert_called_once()
    assert bridge._closed is True


@pytest.mark.asyncio
async def test_close_method_with_errors(mock_websocket, mock_openai_ws):
    # Setup the mocks to raise exceptions when close is called
    mock_openai_ws.close.side_effect = Exception("OpenAI close error")
    mock_websocket.close.side_effect = Exception("WebSocket close error")

    bridge = TelephonyRealtimeBridge(
        telephony_websocket=mock_websocket, realtime_websocket=mock_openai_ws
    )

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
    bridge.realtime_websocket.close.assert_not_called()
    bridge.telephony_websocket.close.assert_not_called()


@pytest.mark.asyncio
@patch("fastagent.telephony_realtime_bridge.initialize_session")
@patch("fastagent.telephony_realtime_bridge.SessionAcceptedResponse")
@patch("uuid.uuid4")
async def test_receive_from_telephony_session_initiate(
    mock_uuid, mock_session_response, mock_init_session, bridge
):
    # Setup mock data
    session_initiate = {
        "type": "session.initiate",
        "conversationId": "test-conversation-id",
        "supportedMediaFormats": ["raw/lpcm16"],
    }

    # Set up the mock to return the message
    async def mock_iter():
        yield json.dumps(session_initiate)

    bridge.telephony_websocket.iter_text = mock_iter
    mock_init_session.return_value = None
    mock_uuid.return_value = "test-uuid"

    # Mock the session response
    mock_response = MagicMock()
    mock_response.model_dump.return_value = {
        "type": "session.accepted",
        "conversationId": "test-conversation-id",
        "mediaFormat": "raw/lpcm16",
    }
    mock_session_response.return_value = mock_response

    # Run the method
    await bridge.receive_from_telephony()

    # Verify conversation_id and media_format were set
    assert bridge.conversation_id == "test-conversation-id"
    assert bridge.media_format == "raw/lpcm16"
    # Verify session was initialized
    assert bridge.session_initialized is True
    # Verify initialize_session was called
    mock_init_session.assert_called_once_with(bridge.realtime_websocket)
    # Verify session response was sent
    bridge.telephony_websocket.send_json.assert_called_once_with(
        mock_response.model_dump()
    )


@pytest.mark.asyncio
@patch("fastagent.telephony_realtime_bridge.InputAudioBufferAppendEvent")
async def test_receive_from_telephony_user_stream_chunk(mock_audio_event, bridge):
    # Setup
    bridge.conversation_id = "test-conversation-id"
    bridge.session_initialized = True
    bridge.realtime_websocket.close_code = None
    bridge._closed = False

    # Setup mock data
    audio_chunk = {"type": "userStream.chunk", "audioChunk": "base64audio"}

    # Set up the mock to return the message
    async def mock_iter():
        yield json.dumps(audio_chunk)
        return

    bridge.telephony_websocket.iter_text = mock_iter

    # Mock the audio event model
    mock_event = MagicMock()
    mock_event.model_dump_json.return_value = (
        '{"type": "input_audio_buffer.append", "audio": "base64audio"}'
    )
    mock_audio_event.return_value = mock_event

    # Run the method
    await bridge.receive_from_telephony()

    # Verify audio was sent to OpenAI
    bridge.realtime_websocket.send.assert_called_once_with(
        mock_event.model_dump_json.return_value
    )


@pytest.mark.asyncio
@patch("fastagent.telephony_realtime_bridge.InputAudioBufferCommitEvent")
async def test_receive_from_telephony_user_stream_stop(mock_commit_event, bridge):
    # Setup
    bridge.conversation_id = "test-conversation-id"
    bridge.session_initialized = True
    bridge.realtime_websocket.close_code = None
    bridge._closed = False

    # Setup mock data
    stream_stop = {"type": "userStream.stop"}

    # Set up the mock to return the message
    async def mock_iter():
        yield json.dumps(stream_stop)
        return

    bridge.telephony_websocket.iter_text = mock_iter

    # Mock the commit event model
    mock_event = MagicMock()
    mock_event.model_dump_json.return_value = '{"type": "input_audio_buffer.commit"}'
    mock_commit_event.return_value = mock_event

    # Run the method
    await bridge.receive_from_telephony()

    # Verify commit event was sent to OpenAI
    bridge.realtime_websocket.send.assert_called_once_with(
        mock_event.model_dump_json.return_value
    )


@pytest.mark.asyncio
async def test_receive_from_telephony_session_end(bridge):
    # Setup mock data
    session_end = {"type": "session.end", "reason": "Test end"}

    # Set up the mock to return the message
    async def mock_iter():
        yield json.dumps(session_end)

    bridge.telephony_websocket.iter_text = mock_iter

    # Run the method
    await bridge.receive_from_telephony()

    # Verify bridge was closed
    assert bridge._closed is True
    bridge.realtime_websocket.close.assert_called_once()
    bridge.telephony_websocket.close.assert_called_once()


@pytest.mark.asyncio
async def test_receive_from_telephony_disconnect(bridge):
    # Simulate WebSocket disconnect
    bridge.telephony_websocket.iter_text.side_effect = WebSocketDisconnect()

    # Run the method
    await bridge.receive_from_telephony()

    # Verify bridge was closed
    assert bridge._closed is True
    bridge.realtime_websocket.close.assert_called_once()
    bridge.telephony_websocket.close.assert_called_once()


@pytest.mark.asyncio
async def test_receive_from_telephony_exception(bridge):
    # Simulate a generic exception
    bridge.telephony_websocket.iter_text.side_effect = Exception("Test error")

    # Run the method
    await bridge.receive_from_telephony()

    # Verify bridge was closed
    assert bridge._closed is True
    bridge.realtime_websocket.close.assert_called_once()
    bridge.telephony_websocket.close.assert_called_once()


@pytest.mark.asyncio
@patch("fastagent.telephony_realtime_bridge.ResponseAudioDeltaEvent")
@patch("fastagent.telephony_realtime_bridge.PlayStreamStartMessage")
@patch("fastagent.telephony_realtime_bridge.PlayStreamChunkMessage")
async def test_receive_from_realtime_audio_delta(
    mock_chunk_msg, mock_start_msg, mock_audio_event, bridge
):
    # Setup
    bridge.conversation_id = "test-conversation-id"
    bridge.media_format = "raw/lpcm16"
    bridge._closed = False

    # Create mock response from OpenAI
    audio_delta = {"type": "response.audio.delta", "delta": "base64audio"}

    # Set up the mock to return the message
    mock_iter = MagicMock()
    mock_iter.__aiter__.return_value = [json.dumps(audio_delta)]
    bridge.realtime_websocket = mock_iter

    # Mock the audio event model
    mock_event = MagicMock()
    mock_event.delta = "base64audio"
    mock_audio_event.return_value = mock_event

    # Mock the stream messages
    mock_start = MagicMock()
    mock_start.model_dump.return_value = {
        "type": "playStream.start",
        "conversationId": "test-conversation-id",
        "streamId": "test-stream-id",
        "mediaFormat": "raw/lpcm16",
    }
    mock_start_msg.return_value = mock_start

    mock_chunk = MagicMock()
    mock_chunk.model_dump.return_value = {
        "type": "playStream.chunk",
        "conversationId": "test-conversation-id",
        "streamId": "test-stream-id",
        "audioChunk": "base64audio",
    }
    mock_chunk_msg.return_value = mock_chunk

    # Run the method
    await bridge.receive_from_realtime()

    # Verify audio was sent to telephony
    assert bridge.telephony_websocket.send_json.call_count == 2  # One for start, one for chunk


@pytest.mark.asyncio
@patch("fastagent.telephony_realtime_bridge.PlayStreamStopMessage")
async def test_receive_from_realtime_audio_done(mock_stop_msg, bridge):
    # Setup
    bridge.conversation_id = "test-conversation-id"
    bridge.active_stream_id = "test-stream-id"
    bridge._closed = False

    # Create mock response from OpenAI
    audio_done = {"type": "response.audio.done"}

    # Set up the mock to return the message
    mock_iter = MagicMock()
    mock_iter.__aiter__.return_value = [json.dumps(audio_done)]
    bridge.realtime_websocket = mock_iter

    # Mock the stop message
    mock_stop = MagicMock()
    mock_stop.model_dump.return_value = {
        "type": "playStream.stop",
        "conversationId": "test-conversation-id",
        "streamId": "test-stream-id",
    }
    mock_stop_msg.return_value = mock_stop

    # Run the method
    await bridge.receive_from_realtime()

    # Verify stream was stopped
    bridge.telephony_websocket.send_json.assert_called_once_with(mock_stop.model_dump())
    assert bridge.active_stream_id is None


@pytest.mark.asyncio
async def test_receive_from_realtime_log_events(bridge):
    # Create mock log event from OpenAI
    log_event = {"type": "session.updated", "data": {"some": "data"}}

    # Configure the mock
    bridge.realtime_websocket.__aiter__.return_value = [json.dumps(log_event)]

    # Run the method
    await bridge.receive_from_realtime()

    # Verify no audio was sent to telephony for log events
    bridge.telephony_websocket.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_receive_from_realtime_exception(bridge):
    # Configure the mock to raise an exception
    bridge.realtime_websocket.__aiter__.side_effect = Exception("Test error")

    # Run the method
    await bridge.receive_from_realtime()

    # Verify bridge was closed
    assert bridge._closed is True
    bridge.realtime_websocket.close.assert_called_once()
    bridge.telephony_websocket.close.assert_called_once()
