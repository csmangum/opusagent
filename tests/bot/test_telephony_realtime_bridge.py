import asyncio
import json
import types
import uuid
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from fastapi.websockets import WebSocketDisconnect

from opusagent.models.openai_api import ServerEventType
from opusagent.telephony_realtime_bridge import TelephonyRealtimeBridge


@pytest.fixture
def mock_websocket():
    mock = AsyncMock()
    mock.send_json = AsyncMock()
    mock.iter_text = AsyncMock()
    mock.client_state = types.SimpleNamespace(DISCONNECTED=False)
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
@patch("opusagent.telephony_realtime_bridge.initialize_session")
@patch("opusagent.telephony_realtime_bridge.SessionAcceptedResponse")
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
    # Verify waiting_for_session_creation flag is False after session is accepted
    assert bridge.waiting_for_session_creation is False

    # Create a real handler for the session update event
    original_handler = bridge.handle_session_update

    # Define a function that will call the original handler with our test data
    async def mock_session_update_handler():
        # Create a session.created event
        session_created_event = {"type": "session.created", "session": {"config": {}}}
        await original_handler(session_created_event)

    # Call our handler directly to simulate processing the event
    await mock_session_update_handler()

    # Now verify session response was sent
    bridge.telephony_websocket.send_json.assert_called_once_with(
        mock_response.model_dump()
    )


@pytest.mark.asyncio
@patch("opusagent.telephony_realtime_bridge.InputAudioBufferAppendEvent")
async def test_receive_from_telephony_user_stream_chunk(mock_audio_event, bridge):
    # Setup
    bridge.conversation_id = "test-conversation-id"
    bridge.session_initialized = True
    bridge.realtime_websocket.close_code = None
    bridge._closed = False

    # Setup mock data
    audio_chunk = {
        "type": "userStream.chunk",
        "audioChunk": "AAAA",
    }  # valid base64 for two null bytes

    # Set up the mock to return the message
    async def mock_iter():
        yield json.dumps(audio_chunk)
        return

    bridge.telephony_websocket.iter_text = mock_iter

    # Mock the audio event model
    mock_event = MagicMock()
    mock_event.model_dump_json.return_value = (
        '{"type": "input_audio_buffer.append", "audio": "AAAA"}'
    )
    mock_audio_event.return_value = mock_event

    # Run the method
    await bridge.receive_from_telephony()

    # Verify audio was sent to OpenAI
    bridge.realtime_websocket.send.assert_called_once_with(
        mock_event.model_dump_json.return_value
    )


@pytest.mark.asyncio
@patch("opusagent.telephony_realtime_bridge.InputAudioBufferCommitEvent")
async def test_receive_from_telephony_user_stream_stop(mock_commit_event, bridge):
    # Setup
    bridge.conversation_id = "test-conversation-id"
    bridge.session_initialized = True
    bridge.realtime_websocket.close_code = None
    bridge._closed = False

    # Prepare a base64-encoded audio chunk of at least 3200 bytes
    import base64
    audio_bytes = b"\x00" * 3200
    audio_chunk_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    # Setup mock data: first a chunk, then a stop
    stream_chunk = {"type": "userStream.chunk", "audioChunk": audio_chunk_b64}
    stream_stop = {"type": "userStream.stop"}

    # Set up the mock to return the messages in sequence
    async def mock_iter():
        yield json.dumps(stream_chunk)
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
    bridge.realtime_websocket.send.assert_any_call(
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
    bridge.telephony_websocket.client_state.DISCONNECTED = (
        False  # Ensure initially connected
    )
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
    bridge.telephony_websocket.client_state.DISCONNECTED = (
        False  # Ensure initially connected
    )
    bridge.telephony_websocket.iter_text.side_effect = Exception("Test error")

    # Run the method
    await bridge.receive_from_telephony()

    # Verify bridge was closed
    assert bridge._closed is True
    bridge.realtime_websocket.close.assert_called_once()
    bridge.telephony_websocket.close.assert_called_once()


@pytest.mark.asyncio
@patch("opusagent.telephony_realtime_bridge.ResponseAudioDeltaEvent")
@patch("opusagent.telephony_realtime_bridge.PlayStreamStartMessage")
@patch("opusagent.telephony_realtime_bridge.PlayStreamChunkMessage")
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
    assert (
        bridge.telephony_websocket.send_json.call_count == 2
    )  # One for start, one for chunk


@pytest.mark.asyncio
@patch("opusagent.telephony_realtime_bridge.PlayStreamStopMessage")
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


@pytest.mark.asyncio
async def test_handle_user_stream_start(bridge):
    # Setup
    bridge.conversation_id = "test-conversation-id"

    # Call the handler
    await bridge.handle_user_stream_start({})

    # Verify userStream.started message was sent
    bridge.telephony_websocket.send_json.assert_called_once()
    sent_message = bridge.telephony_websocket.send_json.call_args[0][0]
    assert sent_message["type"] == "userStream.started"
    assert sent_message["conversationId"] == "test-conversation-id"


@pytest.mark.asyncio
async def test_handle_log_event_error(bridge):
    # Setup
    error_event = {
        "type": "error",
        "code": "test_error",
        "message": "Test error message",
        "details": {"additional": "info"},
    }

    # Call the handler
    with patch("opusagent.telephony_realtime_bridge.logger") as mock_logger:
        await bridge.handle_log_event(error_event)

        # Verify error was logged properly
        mock_logger.error.assert_any_call(
            "ERROR DETAILS: code=test_error, message='Test error message'"
        )
        mock_logger.error.assert_any_call(
            'ERROR ADDITIONAL DETAILS: {"additional": "info"}'
        )
        mock_logger.error.assert_any_call(
            f"FULL ERROR RESPONSE: {json.dumps(error_event)}"
        )


@pytest.mark.asyncio
async def test_handle_log_event_other(bridge):
    # Setup
    log_event = {"type": "other_log_type", "data": "some data"}

    # Call the handler - should not raise an exception
    await bridge.handle_log_event(log_event)


@pytest.mark.asyncio
@patch("opusagent.telephony_realtime_bridge.ResponseTextDeltaEvent")
async def test_handle_text_delta(mock_text_delta, bridge):
    # Setup
    text_event = {"type": "response.text.delta", "delta": "Hello, how can I help?"}

    # Mock the text delta event model
    mock_event = MagicMock()
    mock_event.delta = "Hello, how can I help?"
    mock_text_delta.return_value = mock_event

    # Call the handler
    with patch("opusagent.telephony_realtime_bridge.logger") as mock_logger:
        await bridge.handle_text_and_transcript(text_event)

        # Verify text delta was logged
        mock_logger.info.assert_called_with(f"Text delta received: {mock_event.delta}")


@pytest.mark.asyncio
async def test_handle_transcript_delta(bridge):
    # Setup
    transcript_event = {
        "type": ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA,
        "delta": "Hello, I heard you say",
    }

    # Call the handler
    with patch("opusagent.telephony_realtime_bridge.logger") as mock_logger:
        await bridge.handle_text_and_transcript(transcript_event)

        # Verify transcript delta was logged - use assert_called_with instead of assert_called_once_with
        # to check just the most recent call
        mock_logger.info.assert_called_with(
            f"Received audio transcript delta: {transcript_event.get('delta', '')}"
        )


@pytest.mark.asyncio
@patch("opusagent.telephony_realtime_bridge.ResponseDoneEvent")
@patch("opusagent.telephony_realtime_bridge.PlayStreamStopMessage")
async def test_handle_response_completion(mock_stop_msg, mock_response_done, bridge):
    # Setup
    bridge.conversation_id = "test-conversation-id"
    bridge.active_stream_id = "test-stream-id"

    response_done_event = {"type": ServerEventType.RESPONSE_DONE}

    # Mock the response done event model
    mock_event = MagicMock()
    mock_event.response = {"id": "test-response-123"}
    mock_response_done.return_value = mock_event

    # Mock the stop message
    mock_stop = MagicMock()
    mock_stop.model_dump.return_value = {
        "type": "playStream.stop",
        "conversationId": "test-conversation-id",
        "streamId": "test-stream-id",
    }
    mock_stop_msg.return_value = mock_stop

    # Call the handler
    with patch("opusagent.telephony_realtime_bridge.logger") as mock_logger:
        await bridge.handle_response_completion(response_done_event)

        # The method logs two messages, first about response completion and then about stopping the stream
        # Check that the first call was for response completion
        calls = mock_logger.info.call_args_list
        assert len(calls) >= 1  # Make sure there was at least one call
        assert calls[0] == call("Response generation completed: test-response-123")

        # Verify stream was stopped
        bridge.telephony_websocket.send_json.assert_called_once_with(
            mock_stop.model_dump()
        )
        assert bridge.active_stream_id is None


@pytest.mark.asyncio
async def test_handle_speech_detection_started(bridge):
    # Setup
    # Need to use the enum value from ServerEventType not the string literal
    speech_started_event = {"type": ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED}

    # Call the handler
    with patch("opusagent.telephony_realtime_bridge.logger") as mock_logger:
        await bridge.handle_speech_detection(speech_started_event)

        # Verify speech detection was logged
        mock_logger.info.assert_called_with("Speech started detected")
        assert bridge.speech_detected is True


@pytest.mark.asyncio
async def test_handle_speech_detection_stopped(bridge):
    # Setup
    # Need to use the enum value from ServerEventType not the string literal
    speech_stopped_event = {"type": ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED}

    # Call the handler
    with patch("opusagent.telephony_realtime_bridge.logger") as mock_logger:
        await bridge.handle_speech_detection(speech_stopped_event)

        # Verify speech detection was logged
        mock_logger.info.assert_called_with("Speech stopped detected")
        assert bridge.speech_detected is False


@pytest.mark.asyncio
async def test_handle_speech_detection_committed(bridge):
    # Setup
    buffer_committed_event = {"type": "input_audio_buffer.committed"}

    # Call the handler
    with patch("opusagent.telephony_realtime_bridge.logger") as mock_logger:
        await bridge.handle_speech_detection(buffer_committed_event)

        # Verify commitment was logged
        mock_logger.info.assert_called_with("Audio buffer committed")


@pytest.mark.asyncio
async def test_race_condition_prevention(bridge):
    """Test that race condition is prevented when user input arrives during active response."""
    # Setup
    bridge.conversation_id = "test-conversation-id"
    bridge.session_initialized = True
    bridge.realtime_websocket.close_code = None
    bridge._closed = False
    bridge.total_audio_bytes_sent = 3200  # Sufficient audio for commit
    
    # Simulate active response
    bridge.response_active = True
    bridge.response_id_tracker = "test-response-id"
    
    # Test data for user stream stop during active response
    stream_stop = {"type": "userStream.stop"}
    
    # Call handle_user_stream_stop during active response
    await bridge.handle_user_stream_stop(stream_stop)
    
    # Verify that no response.create was sent (since response is active)
    # The bridge should have queued the user input instead
    assert bridge.pending_user_input is not None
    assert bridge.pending_user_input["audio_committed"] is True
    assert "timestamp" in bridge.pending_user_input
    
    # Verify no response.create call was made
    sent_messages = [call[0][0] for call in bridge.realtime_websocket.send.call_args_list]
    response_create_messages = [msg for msg in sent_messages if '"type": "response.create"' in msg]
    assert len(response_create_messages) == 0, "No response.create should be sent during active response"


@pytest.mark.asyncio
async def test_response_state_tracking(bridge):
    """Test that response state is properly tracked through the lifecycle."""
    # Initial state
    assert bridge.response_active is False
    assert bridge.response_id_tracker is None
    assert bridge.pending_user_input is None
    
    # Simulate response created event
    response_created = {
        "type": "response.created",
        "response": {"id": "test-response-123"}
    }
    await bridge.handle_response_created(response_created)
    
    # Verify response is now active
    assert bridge.response_active is True
    assert bridge.response_id_tracker == "test-response-123"
    
    # Simulate response completion
    response_done = {
        "type": "response.done",
        "response": {"id": "test-response-123", "status": "completed"}
    }
    await bridge.handle_response_completion(response_done)
    
    # Verify response is no longer active
    assert bridge.response_active is False


@pytest.mark.asyncio
async def test_pending_input_processing(bridge):
    """Test that pending user input is processed after response completion."""
    # Setup
    bridge.conversation_id = "test-conversation-id"
    bridge.realtime_websocket.close_code = None
    bridge._closed = False
    
    # Set pending user input (as would happen during active response)
    bridge.pending_user_input = {
        "audio_committed": True,  
        "timestamp": 1234567890.0
    }
    
    # Simulate response completion
    response_done = {
        "type": "response.done", 
        "response": {"id": "test-response-123", "status": "completed"}
    }
    await bridge.handle_response_completion(response_done)
    
    # Verify pending input was processed (response.create should be called)
    sent_messages = [call[0][0] for call in bridge.realtime_websocket.send.call_args_list]
    response_create_messages = [msg for msg in sent_messages if '"type": "response.create"' in msg]
    assert len(response_create_messages) == 1, "response.create should be sent for queued input"
    
    # Verify pending input was cleared
    assert bridge.pending_user_input is None


@pytest.mark.asyncio
async def test_normal_flow_without_race_condition(bridge):
    """Test normal flow when no response is active."""
    # Setup
    bridge.conversation_id = "test-conversation-id"
    bridge.session_initialized = True
    bridge.realtime_websocket.close_code = None
    bridge._closed = False
    bridge.total_audio_bytes_sent = 3200  # Sufficient audio for commit
    bridge.response_active = False  # No active response
    
    # Test data
    stream_stop = {"type": "userStream.stop"}
    
    # Call handle_user_stream_stop when no response is active
    await bridge.handle_user_stream_stop(stream_stop)
    
    # Verify response.create was sent normally
    sent_messages = [call[0][0] for call in bridge.realtime_websocket.send.call_args_list]
    response_create_messages = [msg for msg in sent_messages if '"type": "response.create"' in msg]
    assert len(response_create_messages) == 1, "response.create should be sent when no active response"
    
    # Verify no pending input was created
    assert bridge.pending_user_input is None


@pytest.mark.asyncio
async def test_create_response_helper(bridge):
    """Test the _create_response helper method."""
    bridge.realtime_websocket.close_code = None
    bridge._closed = False
    
    # Call the helper method
    await bridge._create_response()
    
    # Verify response.create was sent with correct structure
    bridge.realtime_websocket.send.assert_called_once()
    sent_json = bridge.realtime_websocket.send.call_args[0][0]
    sent_data = json.loads(sent_json)
    
    assert sent_data["type"] == "response.create"
    assert sent_data["response"]["modalities"] == ["text", "audio"]
    assert sent_data["response"]["output_audio_format"] == "pcm16"
    assert sent_data["response"]["voice"] == "alloy"
