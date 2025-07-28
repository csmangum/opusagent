import pytest
import websockets
from unittest.mock import AsyncMock, MagicMock
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from opusagent.bridges.call_agent_bridge import CallAgentBridge
from opusagent.bridges.audiocodes_bridge import AudioCodesBridge
from opusagent.models.audiocodes_api import TelephonyEventType
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
                        "intent": {"type": "string", "enum": ["Card Replacement", "Account Inquiry", "Account Management", "Transaction Dispute", "Other"]},
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
                        "reason": {"type": "string", "description": "The reason for transferring to a human agent"},
                        "priority": {"type": "string", "enum": ["low", "normal", "high"], "description": "The priority level of the transfer"},
                        "context": {"type": "object", "description": "Additional context for the human agent"},
                    },
                },
            },
        ],
    )

@pytest.fixture
async def mock_websocket():
    websocket = MagicMock()
    websocket.send_json = AsyncMock()
    websocket.receive_text = AsyncMock()
    websocket.close = AsyncMock()
    websocket.client_state = WebSocketState.CONNECTED
    websocket.close_code = None  # Ensure is_websocket_closed returns False
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
    bridge = CallAgentBridge(mock_websocket, mock_realtime_websocket, test_session_config)
    # Mock the dependencies to avoid actual initialization
    bridge.session_manager.initialize_session = AsyncMock()
    bridge.session_manager.send_initial_conversation_item = AsyncMock()
    bridge.audio_handler.initialize_stream = AsyncMock()
    # Ensure the bridge is not closed
    bridge._closed = False
    return bridge


@pytest.mark.asyncio
async def test_bridge_initialization(bridge, mock_websocket, mock_realtime_websocket):
    """Test CallAgentBridge initialization and inheritance."""
    assert bridge.platform_websocket == mock_websocket
    assert bridge.realtime_websocket == mock_realtime_websocket
    assert isinstance(bridge, CallAgentBridge)
    assert isinstance(bridge, AudioCodesBridge)


@pytest.mark.asyncio
async def test_inheritance_from_audiocodes_bridge(bridge):
    """Test that CallAgentBridge properly inherits AudioCodesBridge functionality."""
    # Verify that it has all the methods from AudioCodesBridge
    audiocodes_methods = [
        'register_platform_event_handlers',
        'send_platform_json',
        'handle_session_start',
        'handle_audio_start',
        'handle_audio_data',
        'handle_audio_end',
        'handle_session_end',
        'send_session_accepted',
        'send_user_stream_started',
        'send_user_stream_stopped',
        'send_session_end'
    ]
    
    for method_name in audiocodes_methods:
        assert hasattr(bridge, method_name)
        assert callable(getattr(bridge, method_name))


@pytest.mark.asyncio
async def test_register_platform_event_handlers_inheritance(bridge):
    """Test that CallAgentBridge inherits AudioCodes event handler registration."""
    bridge.register_platform_event_handlers()
    
    # Verify all AudioCodes event types are registered (inherited functionality)
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
async def test_send_platform_json_inheritance(bridge, mock_websocket):
    """Test that CallAgentBridge inherits send_platform_json functionality."""
    test_payload = {"type": "session.accepted", "conversationId": "test-123"}
    await bridge.send_platform_json(test_payload)
    mock_websocket.send_json.assert_called_once_with(test_payload)


@pytest.mark.asyncio
async def test_session_start_handling_inheritance(bridge):
    """Test that CallAgentBridge inherits session start handling."""
    test_data = {
        "type": "session.initiate",
        "conversationId": "test-conv-123",
        "supportedMediaFormats": ["raw/lpcm16"]
    }
    
    # Mock the dependencies
    bridge.initialize_conversation = AsyncMock()
    bridge.send_session_accepted = AsyncMock()
    
    await bridge.handle_session_start(test_data)
    
    # Verify inherited functionality works
    bridge.initialize_conversation.assert_called_once_with("test-conv-123")
    bridge.send_session_accepted.assert_called_once()
    assert bridge.media_format == "raw/lpcm16"


@pytest.mark.asyncio
async def test_audio_handling_inheritance(bridge):
    """Test that CallAgentBridge inherits audio handling functionality."""
    # Test audio start
    bridge.send_user_stream_started = AsyncMock()
    await bridge.handle_audio_start({"type": "userStream.start"})
    bridge.send_user_stream_started.assert_called_once()
    
    # Test audio data
    bridge.audio_handler.handle_incoming_audio = AsyncMock()
    audio_data = {"type": "userStream.chunk", "audio": "dGVzdA=="}
    await bridge.handle_audio_data(audio_data)
    bridge.audio_handler.handle_incoming_audio.assert_called_once_with(audio_data)
    
    # Test audio end
    bridge.send_user_stream_stopped = AsyncMock()
    bridge.handle_audio_commit = AsyncMock()
    await bridge.handle_audio_end({"type": "userStream.stop"})
    bridge.send_user_stream_stopped.assert_called_once()
    bridge.handle_audio_commit.assert_called_once()


@pytest.mark.asyncio
async def test_session_end_handling_inheritance(bridge):
    """Test that CallAgentBridge inherits session end handling."""
    bridge.close = AsyncMock()
    
    await bridge.handle_session_end({"type": "session.end", "reason": "Test"})
    
    bridge.close.assert_called_once()


@pytest.mark.asyncio
async def test_caller_specific_logger_namespace():
    """Test that CallAgentBridge uses its own logger namespace."""
    # Import the logger to check its name
    from opusagent.bridges.call_agent_bridge import logger
    
    # Verify the logger name is specific to call_agent_bridge
    assert logger.name == "call_agent_bridge"


@pytest.mark.asyncio
async def test_semantic_clarity_separate_from_audiocodes(bridge):
    """Test that CallAgentBridge provides semantic clarity while maintaining functionality."""
    # This test ensures that CallAgentBridge can be differentiated from AudioCodesBridge
    # while maintaining the same functionality
    
    # Verify it's a distinct class
    assert type(bridge).__name__ == "CallAgentBridge"
    assert type(bridge).__module__ == "opusagent.bridges.call_agent_bridge"
    
    # Verify it maintains AudioCodes functionality
    assert isinstance(bridge, AudioCodesBridge)
    
    # Verify it can be used for caller-side operations
    # (This is mostly semantic at this point, but the structure is in place)
    bridge.register_platform_event_handlers()
    assert len(bridge.event_router.telephony_handlers) > 0


@pytest.mark.asyncio
async def test_complete_caller_session_flow(bridge):
    """Test a complete caller session flow using inherited AudioCodes functionality."""
    # Mock all dependencies
    bridge.initialize_conversation = AsyncMock()
    bridge.send_session_accepted = AsyncMock()
    bridge.send_user_stream_started = AsyncMock()
    bridge.audio_handler.handle_incoming_audio = AsyncMock()
    bridge.send_user_stream_stopped = AsyncMock()
    bridge.handle_audio_commit = AsyncMock()
    bridge.close = AsyncMock()
    
    # Simulate a complete caller session
    # 1. Session initiate (from caller side)
    await bridge.handle_session_start({
        "type": "session.initiate",
        "conversationId": "caller-123",
        "supportedMediaFormats": ["raw/lpcm16"]
    })
    
    # 2. Audio start (caller begins speaking)
    await bridge.handle_audio_start({"type": "userStream.start"})
    
    # 3. Audio data (caller's voice data)
    await bridge.handle_audio_data({
        "type": "userStream.chunk",
        "audio": "Y2FsbGVyIGF1ZGlv"  # "caller audio" base64
    })
    
    # 4. Audio end (caller stops speaking)
    await bridge.handle_audio_end({"type": "userStream.stop"})
    
    # 5. Session end (call completion)
    await bridge.handle_session_end({"type": "session.end", "reason": "Call complete"})
    
    # Verify the complete caller flow worked
    bridge.initialize_conversation.assert_called_once_with("caller-123")
    bridge.send_session_accepted.assert_called_once()
    bridge.send_user_stream_started.assert_called_once()
    bridge.audio_handler.handle_incoming_audio.assert_called_once()
    bridge.send_user_stream_stopped.assert_called_once()
    bridge.handle_audio_commit.assert_called_once()
    bridge.close.assert_called_once()
    
    # Verify media format was set correctly
    assert bridge.media_format == "raw/lpcm16" 