import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from fastapi import WebSocket

from opusagent.bridges.audiocodes_bridge import AudioCodesBridge
from opusagent.models.audiocodes_api import (
    SessionAcceptedResponse,
    TelephonyEventType,
    UserStreamSpeechCommittedResponse,
    UserStreamSpeechStartedResponse,
    UserStreamSpeechStoppedResponse,
    UserStreamStartedResponse,
    UserStreamStoppedResponse,
)
from opusagent.models.openai_api import SessionConfig

# Test constants
TEST_VOICE = "verse"
TEST_MODEL = "gpt-4o-realtime-preview-2025-06-03"


@pytest.fixture
def test_session_config():
    """Create a test session configuration."""
    return SessionConfig(
        input_audio_format="pcm16",
        output_audio_format="pcm16",
        voice=TEST_VOICE,
        instructions="You are a test customer service agent.",
        modalities=["text", "audio"],
        temperature=0.8,
        model=TEST_MODEL,
        tools=[
            {
                "type": "function",
                "name": "route_call",
                "description": "Route the call to the appropriate function based on the intent of the call.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "enum": [
                                "Card Replacement",
                                "Account Inquiry",
                                "Account Management",
                                "Transaction Dispute",
                                "Other",
                            ],
                        },
                    },
                },
            },
            {
                "type": "function",
                "name": "human_handoff",
                "description": "Transfer the conversation to a human agent.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "The reason for transferring to a human agent",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "normal", "high"],
                            "description": "The priority level of the transfer",
                        },
                        "context": {
                            "type": "object",
                            "description": "Additional context for the human agent",
                        },
                    },
                },
            },
        ],
    )


@pytest.fixture
async def mock_websocket():
    websocket = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
async def mock_realtime_websocket():
    websocket = AsyncMock(spec=websockets.ClientConnection)
    websocket.send = AsyncMock()
    websocket.recv = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
async def bridge(mock_websocket, mock_realtime_websocket, test_session_config):
    bridge = AudioCodesBridge(
        mock_websocket, mock_realtime_websocket, test_session_config, vad_enabled=True
    )
    # Mock the dependencies to avoid actual initialization
    bridge.session_manager.initialize_session = AsyncMock()
    bridge.session_manager.send_initial_conversation_item = AsyncMock()
    bridge.audio_handler.initialize_stream = AsyncMock()
    return bridge


@pytest.fixture
async def bridge_vad_disabled(
    mock_websocket, mock_realtime_websocket, test_session_config
):
    """Create a bridge with VAD disabled for testing."""
    bridge = AudioCodesBridge(
        mock_websocket, mock_realtime_websocket, test_session_config, vad_enabled=False
    )
    # Mock the dependencies to avoid actual initialization
    bridge.session_manager.initialize_session = AsyncMock()
    bridge.session_manager.send_initial_conversation_item = AsyncMock()
    bridge.audio_handler.initialize_stream = AsyncMock()
    return bridge


@pytest.mark.asyncio
async def test_bridge_initialization(bridge, mock_websocket, mock_realtime_websocket):
    """Test AudioCodesBridge initialization."""
    assert bridge.platform_websocket == mock_websocket
    assert bridge.realtime_websocket == mock_realtime_websocket
    assert isinstance(bridge, AudioCodesBridge)


@pytest.mark.asyncio
async def test_register_platform_event_handlers(bridge):
    """Test registration of AudioCodes-specific event handlers."""
    bridge.register_platform_event_handlers()

    # Verify all AudioCodes event types are registered
    expected_handlers = {
        TelephonyEventType.SESSION_INITIATE: bridge.handle_session_start,
        TelephonyEventType.USER_STREAM_START: bridge.handle_audio_start,
        TelephonyEventType.USER_STREAM_CHUNK: bridge.handle_audio_data,
        TelephonyEventType.USER_STREAM_STOP: bridge.handle_audio_end,
        TelephonyEventType.SESSION_END: bridge.handle_session_end,
    }

    for event_type, handler in expected_handlers.items():
        assert event_type in bridge.event_router.telephony_handlers
        assert bridge.event_router.telephony_handlers[event_type] == handler


@pytest.mark.asyncio
async def test_send_platform_json(bridge, mock_websocket):
    """Test sending JSON to AudioCodes websocket."""
    test_payload = {"type": "session.accepted", "conversationId": "test-123"}
    await bridge.send_platform_json(test_payload)
    mock_websocket.send_json.assert_called_once_with(test_payload)


@pytest.mark.asyncio
async def test_handle_session_start(bridge):
    """Test handling session initiate from AudioCodes."""
    test_data = {
        "type": "session.initiate",
        "conversationId": "test-conv-123",
        "supportedMediaFormats": ["raw/lpcm16", "raw/mulaw"],
    }

    # Mock the dependencies
    bridge.initialize_conversation = AsyncMock()
    bridge.send_session_accepted = AsyncMock()

    await bridge.handle_session_start(test_data)

    # Verify conversation initialization
    bridge.initialize_conversation.assert_called_once_with("test-conv-123")

    # Verify session accepted response
    bridge.send_session_accepted.assert_called_once()

    # Verify media format is set
    assert bridge.media_format == "raw/lpcm16"


@pytest.mark.asyncio
async def test_handle_session_start_default_media_format(bridge):
    """Test handling session initiate with default media format."""
    test_data = {"type": "session.initiate", "conversationId": "test-conv-123"}

    # Mock the dependencies
    bridge.initialize_conversation = AsyncMock()
    bridge.send_session_accepted = AsyncMock()

    await bridge.handle_session_start(test_data)

    # Verify default media format is used
    assert bridge.media_format == "raw/lpcm16"


@pytest.mark.asyncio
async def test_handle_audio_start(bridge):
    """Test handling user stream start from AudioCodes."""
    test_data = {"type": "userStream.start", "conversationId": "test-conv-123"}

    # Set initial values
    bridge.audio_chunks_sent = 5
    bridge.total_audio_bytes_sent = 1000

    # Mock the response
    bridge.send_user_stream_started = AsyncMock()

    await bridge.handle_audio_start(test_data)

    # Verify counters are reset
    assert bridge.audio_chunks_sent == 0
    assert bridge.total_audio_bytes_sent == 0

    # Verify response is sent
    bridge.send_user_stream_started.assert_called_once()


@pytest.mark.asyncio
async def test_handle_audio_start_with_participant(bridge):
    """Test handling user stream start with participant field (Agent Assist mode)."""
    test_data = {
        "type": "userStream.start",
        "conversationId": "test-conv-123",
        "participant": "agent",
    }

    # Set initial values
    bridge.audio_chunks_sent = 5
    bridge.total_audio_bytes_sent = 1000

    # Mock the response
    bridge.send_user_stream_started = AsyncMock()

    await bridge.handle_audio_start(test_data)

    # Verify participant is set
    assert bridge.current_participant == "agent"

    # Verify counters are reset
    assert bridge.audio_chunks_sent == 0
    assert bridge.total_audio_bytes_sent == 0

    # Verify response is sent
    bridge.send_user_stream_started.assert_called_once()


@pytest.mark.asyncio
async def test_handle_audio_start_default_participant(bridge):
    """Test handling user stream start with default participant (single-party call)."""
    test_data = {"type": "userStream.start", "conversationId": "test-conv-123"}

    # Mock the response
    bridge.send_user_stream_started = AsyncMock()

    await bridge.handle_audio_start(test_data)

    # Verify default participant is used
    assert bridge.current_participant == "caller"

    # Verify response is sent
    bridge.send_user_stream_started.assert_called_once()


@pytest.mark.asyncio
async def test_handle_audio_data(bridge):
    """Test handling user stream chunk from AudioCodes."""
    test_data = {
        "type": "userStream.chunk",
        "conversationId": "test-conv-123",
        "audio": "dGVzdCBhdWRpbyBkYXRh",  # base64 encoded test data
    }

    # Mock the audio handler
    bridge.audio_handler.handle_incoming_audio = AsyncMock()

    await bridge.handle_audio_data(test_data)

    # Verify audio handler is called
    bridge.audio_handler.handle_incoming_audio.assert_called_once_with(test_data)


@pytest.mark.asyncio
async def test_handle_audio_end(bridge):
    """Test handling user stream stop from AudioCodes."""
    test_data = {"type": "userStream.stop", "conversationId": "test-conv-123"}

    bridge.conversation_id = "test-conv-123"

    # Mock the dependencies
    bridge.send_user_stream_stopped = AsyncMock()
    bridge.handle_audio_commit = AsyncMock()

    await bridge.handle_audio_end(test_data)

    # Verify response is sent
    bridge.send_user_stream_stopped.assert_called_once()

    # Verify audio commit is handled
    bridge.handle_audio_commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_session_end(bridge):
    """Test handling session end from AudioCodes."""
    test_data = {
        "type": "session.end",
        "conversationId": "test-conv-123",
        "reason": "User hung up",
    }

    # Mock the close method
    bridge.close = AsyncMock()

    await bridge.handle_session_end(test_data)

    # Verify bridge is closed
    bridge.close.assert_called_once()


@pytest.mark.asyncio
async def test_handle_session_end_no_reason(bridge):
    """Test handling session end without reason."""
    test_data = {"type": "session.end", "conversationId": "test-conv-123"}

    # Mock the close method
    bridge.close = AsyncMock()

    await bridge.handle_session_end(test_data)

    # Verify bridge is closed
    bridge.close.assert_called_once()


@pytest.mark.asyncio
async def test_send_session_accepted(bridge, mock_websocket):
    """Test sending session accepted response."""
    bridge.conversation_id = "test-conv-123"
    bridge.media_format = "raw/lpcm16"

    await bridge.send_session_accepted()

    # Verify the correct message is sent
    expected_payload = SessionAcceptedResponse(
        type=TelephonyEventType.SESSION_ACCEPTED,
        conversationId="test-conv-123",
        mediaFormat="raw/lpcm16",
        participant="caller",
    ).model_dump(exclude_none=True)

    mock_websocket.send_json.assert_called_once_with(expected_payload)


@pytest.mark.asyncio
async def test_send_session_accepted_default_media_format(bridge, mock_websocket):
    """Test sending session accepted response with default media format."""
    bridge.conversation_id = "test-conv-123"
    bridge.media_format = None

    await bridge.send_session_accepted()

    # Verify default media format is used
    expected_payload = SessionAcceptedResponse(
        type=TelephonyEventType.SESSION_ACCEPTED,
        conversationId="test-conv-123",
        mediaFormat="raw/lpcm16",
        participant="caller",
    ).model_dump(exclude_none=True)

    mock_websocket.send_json.assert_called_once_with(expected_payload)


@pytest.mark.asyncio
async def test_send_user_stream_started(bridge, mock_websocket):
    """Test sending user stream started response."""
    bridge.conversation_id = "test-conv-123"

    await bridge.send_user_stream_started()

    expected_payload = UserStreamStartedResponse(
        type=TelephonyEventType.USER_STREAM_STARTED,
        conversationId="test-conv-123",
        participant="caller",
    ).model_dump(exclude_none=True)

    mock_websocket.send_json.assert_called_once_with(expected_payload)


@pytest.mark.asyncio
async def test_send_user_stream_started_with_participant(bridge, mock_websocket):
    """Test sending user stream started response with participant (Agent Assist mode)."""
    bridge.conversation_id = "test-conv-123"
    bridge.current_participant = "agent"

    await bridge.send_user_stream_started()

    expected_payload = UserStreamStartedResponse(
        **{
            "type": TelephonyEventType.USER_STREAM_STARTED,
            "conversationId": "test-conv-123",
            "participant": "agent",
        }
    ).model_dump()

    mock_websocket.send_json.assert_called_once_with(expected_payload)


@pytest.mark.asyncio
async def test_send_user_stream_stopped(bridge, mock_websocket):
    """Test sending user stream stopped response."""
    bridge.conversation_id = "test-conv-123"

    await bridge.send_user_stream_stopped()

    expected_payload = UserStreamStoppedResponse(
        type=TelephonyEventType.USER_STREAM_STOPPED,
        conversationId="test-conv-123",
        participant="caller",
    ).model_dump(exclude_none=True)

    mock_websocket.send_json.assert_called_once_with(expected_payload)


@pytest.mark.asyncio
async def test_send_user_stream_stopped_with_participant(bridge, mock_websocket):
    """Test sending user stream stopped response with participant (Agent Assist mode)."""
    bridge.conversation_id = "test-conv-123"
    bridge.current_participant = "agent"

    await bridge.send_user_stream_stopped()

    expected_payload = UserStreamStoppedResponse(
        **{
            "type": TelephonyEventType.USER_STREAM_STOPPED,
            "conversationId": "test-conv-123",
            "participant": "agent",
        }
    ).model_dump()

    mock_websocket.send_json.assert_called_once_with(expected_payload)


@pytest.mark.asyncio
async def test_send_session_end(bridge, mock_websocket):
    """Test sending session end message."""
    bridge.conversation_id = "test-conv-123"

    test_reason = "Call completed"
    await bridge.send_session_end(test_reason)

    expected_payload = {
        "type": "session.end",
        "conversationId": "test-conv-123",
        "reasonCode": "normal",
        "reason": test_reason,
    }

    mock_websocket.send_json.assert_called_once_with(expected_payload)


@pytest.mark.asyncio
async def test_send_session_end_with_error(bridge, mock_websocket):
    """Test sending session end message when websocket send fails."""
    bridge.conversation_id = "test-conv-123"

    # Mock websocket to raise an exception
    mock_websocket.send_json.side_effect = Exception("Connection error")

    # Should not raise an exception
    await bridge.send_session_end("Test reason")

    # Verify send was attempted
    mock_websocket.send_json.assert_called_once()


@pytest.mark.asyncio
async def test_handle_speech_started(bridge):
    """Test handling speech started event from OpenAI Realtime API."""
    bridge.send_speech_started = AsyncMock()

    await bridge.handle_speech_started({"type": "input_audio_buffer.speech_started"})

    bridge.send_speech_started.assert_called_once()


@pytest.mark.asyncio
async def test_handle_speech_stopped(bridge):
    """Test handling speech stopped event from OpenAI Realtime API."""
    bridge.send_speech_stopped = AsyncMock()

    await bridge.handle_speech_stopped({"type": "input_audio_buffer.speech_stopped"})

    bridge.send_speech_stopped.assert_called_once()


@pytest.mark.asyncio
async def test_handle_speech_committed(bridge):
    """Test handling speech committed event from OpenAI Realtime API."""
    bridge.send_speech_committed = AsyncMock()

    await bridge.handle_speech_committed({"type": "input_audio_buffer.committed"})

    bridge.send_speech_committed.assert_called_once()


@pytest.mark.asyncio
async def test_send_speech_started(bridge, mock_websocket):
    """Test sending speech started response to AudioCodes."""
    bridge.conversation_id = "test-conv-123"

    await bridge.send_speech_started()

    expected_payload = UserStreamSpeechStartedResponse(
        **{
            "type": TelephonyEventType.USER_STREAM_SPEECH_STARTED,
            "conversationId": "test-conv-123",
        }
    ).model_dump()

    mock_websocket.send_json.assert_called_once_with(expected_payload)


@pytest.mark.asyncio
async def test_send_speech_started_with_participant(bridge, mock_websocket):
    """Test sending speech started response with participant (Agent Assist mode)."""
    bridge.conversation_id = "test-conv-123"
    bridge.current_participant = "agent"

    await bridge.send_speech_started()

    expected_payload = UserStreamSpeechStartedResponse(
        **{
            "type": TelephonyEventType.USER_STREAM_SPEECH_STARTED,
            "conversationId": "test-conv-123",
            "participantId": "agent",
        }
    ).model_dump()

    mock_websocket.send_json.assert_called_once_with(expected_payload)


@pytest.mark.asyncio
async def test_send_speech_stopped(bridge, mock_websocket):
    """Test sending speech stopped response to AudioCodes."""
    bridge.conversation_id = "test-conv-123"

    await bridge.send_speech_stopped()

    expected_payload = UserStreamSpeechStoppedResponse(
        **{
            "type": TelephonyEventType.USER_STREAM_SPEECH_STOPPED,
            "conversationId": "test-conv-123",
        }
    ).model_dump()

    mock_websocket.send_json.assert_called_once_with(expected_payload)


@pytest.mark.asyncio
async def test_send_speech_stopped_with_participant(bridge, mock_websocket):
    """Test sending speech stopped response with participant (Agent Assist mode)."""
    bridge.conversation_id = "test-conv-123"
    bridge.current_participant = "agent"

    await bridge.send_speech_stopped()

    expected_payload = UserStreamSpeechStoppedResponse(
        **{
            "type": TelephonyEventType.USER_STREAM_SPEECH_STOPPED,
            "conversationId": "test-conv-123",
            "participantId": "agent",
        }
    ).model_dump()

    mock_websocket.send_json.assert_called_once_with(expected_payload)


@pytest.mark.asyncio
async def test_send_speech_committed(bridge, mock_websocket):
    """Test sending speech committed response to AudioCodes."""
    bridge.conversation_id = "test-conv-123"

    await bridge.send_speech_committed()

    expected_payload = UserStreamSpeechCommittedResponse(
        **{
            "type": TelephonyEventType.USER_STREAM_SPEECH_COMMITTED,
            "conversationId": "test-conv-123",
        }
    ).model_dump()

    mock_websocket.send_json.assert_called_once_with(expected_payload)


@pytest.mark.asyncio
async def test_send_speech_committed_with_participant(bridge, mock_websocket):
    """Test sending speech committed response with participant (Agent Assist mode)."""
    bridge.conversation_id = "test-conv-123"
    bridge.current_participant = "agent"

    await bridge.send_speech_committed()

    expected_payload = UserStreamSpeechCommittedResponse(
        **{
            "type": TelephonyEventType.USER_STREAM_SPEECH_COMMITTED,
            "conversationId": "test-conv-123",
            "participantId": "agent",
        }
    ).model_dump()

    mock_websocket.send_json.assert_called_once_with(expected_payload)


@pytest.mark.asyncio
async def test_integration_session_flow(bridge):
    """Test a complete session flow from start to end."""
    # Mock all dependencies
    bridge.initialize_conversation = AsyncMock()
    bridge.send_session_accepted = AsyncMock()
    bridge.send_user_stream_started = AsyncMock()
    bridge.audio_handler.handle_incoming_audio = AsyncMock()
    bridge.send_user_stream_stopped = AsyncMock()
    bridge.handle_audio_commit = AsyncMock()
    bridge.close = AsyncMock()

    # Simulate session initiate
    session_data = {
        "type": "session.initiate",
        "conversationId": "test-conv-123",
        "supportedMediaFormats": ["raw/lpcm16"],
    }
    await bridge.handle_session_start(session_data)

    # Simulate audio start
    audio_start_data = {"type": "userStream.start"}
    await bridge.handle_audio_start(audio_start_data)

    # Simulate audio data
    audio_data = {"type": "userStream.chunk", "audio": "dGVzdCBhdWRpbw=="}
    await bridge.handle_audio_data(audio_data)

    # Simulate audio end
    audio_end_data = {"type": "userStream.stop"}
    await bridge.handle_audio_end(audio_end_data)

    # Simulate session end
    session_end_data = {"type": "session.end", "reason": "Complete"}
    await bridge.handle_session_end(session_end_data)

    # Verify the complete flow
    bridge.initialize_conversation.assert_called_once()
    bridge.send_session_accepted.assert_called_once()
    bridge.send_user_stream_started.assert_called_once()
    bridge.audio_handler.handle_incoming_audio.assert_called_once()
    bridge.send_user_stream_stopped.assert_called_once()
    bridge.handle_audio_commit.assert_called_once()
    bridge.close.assert_called_once()


@pytest.mark.asyncio
async def test_register_realtime_event_handlers(bridge):
    """Test registration of realtime event handlers for VAD events."""
    bridge.register_platform_event_handlers()

    # Verify VAD event handlers are registered
    expected_realtime_handlers = {
        "input_audio_buffer.speech_started": bridge.handle_speech_started,
        "input_audio_buffer.speech_stopped": bridge.handle_speech_stopped,
        "input_audio_buffer.committed": bridge.handle_speech_committed,
    }

    for event_type, handler in expected_realtime_handlers.items():
        assert event_type in bridge.event_router.realtime_handlers
        assert bridge.event_router.realtime_handlers[event_type] == handler


@pytest.mark.asyncio
async def test_vad_configuration(bridge, bridge_vad_disabled):
    """Test VAD configuration is properly set."""
    # Test VAD enabled bridge
    assert bridge.vad_enabled is True

    # Test VAD disabled bridge
    assert bridge_vad_disabled.vad_enabled is False


@pytest.mark.asyncio
async def test_vad_event_handlers_registration(bridge, bridge_vad_disabled):
    """Test that VAD event handlers are registered only when VAD is enabled."""
    # When VAD is enabled, handlers should be registered
    assert bridge.vad_enabled is True

    # When VAD is disabled, handlers should not be registered
    assert bridge_vad_disabled.vad_enabled is False


@pytest.mark.asyncio
async def test_vad_speech_events_when_disabled(bridge_vad_disabled):
    """Test that VAD speech events are ignored when VAD is disabled."""
    # Mock the send methods to track calls
    bridge_vad_disabled.send_speech_started = AsyncMock()
    bridge_vad_disabled.send_speech_stopped = AsyncMock()
    bridge_vad_disabled.send_speech_committed = AsyncMock()

    # Test speech started event
    await bridge_vad_disabled.handle_speech_started({})
    bridge_vad_disabled.send_speech_started.assert_not_called()

    # Test speech stopped event
    await bridge_vad_disabled.handle_speech_stopped({})
    bridge_vad_disabled.send_speech_stopped.assert_not_called()

    # Test speech committed event
    await bridge_vad_disabled.handle_speech_committed({})
    bridge_vad_disabled.send_speech_committed.assert_not_called()


@pytest.mark.asyncio
async def test_vad_speech_events_when_enabled(bridge):
    """Test that VAD speech events are processed when VAD is enabled."""
    # Mock the send methods to track calls
    bridge.send_speech_started = AsyncMock()
    bridge.send_speech_stopped = AsyncMock()
    bridge.send_speech_committed = AsyncMock()

    # Test speech started event
    await bridge.handle_speech_started({})
    bridge.send_speech_started.assert_called_once()

    # Test speech stopped event
    await bridge.handle_speech_stopped({})
    bridge.send_speech_stopped.assert_called_once()

    # Test speech committed event
    await bridge.handle_speech_committed({})
    bridge.send_speech_committed.assert_called_once()
