import json
import pytest
import websockets
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from opusagent.bridges.base_bridge import BaseRealtimeBridge
from opusagent.event_router import EventRouter
from opusagent.audio_stream_handler import AudioStreamHandler
from opusagent.function_handler import FunctionHandler
from opusagent.session_manager import SessionManager
from opusagent.transcript_manager import TranscriptManager
from opusagent.realtime_handler import RealtimeHandler
from opusagent.models.audiocodes_api import TelephonyEventType

# Mock implementation of BaseRealtimeBridge for testing
class MockBridge(BaseRealtimeBridge):
    async def register_platform_event_handlers(self):
        self.event_router.register_telephony_handler("test_event", self.handle_test_event)
    
    async def send_platform_json(self, payload: dict):
        await self.platform_websocket.send_json(payload)
    
    async def handle_test_event(self, data: dict):
        pass
    
    async def handle_session_start(self, data: dict):
        pass
    
    async def handle_audio_start(self, data: dict):
        pass
    
    async def handle_audio_data(self, data: dict):
        pass
    
    async def handle_audio_end(self, data: dict):
        pass
    
    async def handle_session_end(self, data: dict):
        pass

class AsyncIterator:
    """Helper class to create async iterators for testing."""
    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item

@pytest.fixture
async def mock_websocket():
    websocket = AsyncMock(spec=WebSocket)
    websocket.send_json = AsyncMock()
    websocket.receive_text = AsyncMock()
    websocket.close = AsyncMock()
    return websocket

@pytest.fixture
async def mock_realtime_websocket():
    websocket = AsyncMock(spec=websockets.WebSocketClientProtocol)
    websocket.send = AsyncMock()
    websocket.recv = AsyncMock()
    websocket.close = AsyncMock()
    return websocket

@pytest.fixture
async def bridge(mock_websocket, mock_realtime_websocket):
    bridge = MockBridge(mock_websocket, mock_realtime_websocket)
    return bridge

@pytest.mark.asyncio
async def test_bridge_initialization(bridge, mock_websocket, mock_realtime_websocket):
    """Test bridge initialization and component setup."""
    assert bridge.platform_websocket == mock_websocket
    assert bridge.realtime_websocket == mock_realtime_websocket
    assert bridge.conversation_id is None
    assert bridge.media_format is None
    assert bridge.speech_detected is False
    assert bridge._closed is False
    assert isinstance(bridge.event_router, EventRouter)
    assert isinstance(bridge.audio_handler, AudioStreamHandler)
    assert isinstance(bridge.function_handler, FunctionHandler)
    assert isinstance(bridge.session_manager, SessionManager)
    assert isinstance(bridge.transcript_manager, TranscriptManager)
    assert isinstance(bridge.realtime_handler, RealtimeHandler)
    assert bridge.audio_chunks_sent == 0
    assert bridge.total_audio_bytes_sent == 0
    assert bridge.input_transcript_buffer == []
    assert bridge.output_transcript_buffer == []
    assert bridge.call_recorder is None

@pytest.mark.asyncio
async def test_register_platform_event_handlers(bridge):
    """Test registration of platform event handlers."""
    await bridge.register_platform_event_handlers()
    assert "test_event" in bridge.event_router.telephony_handlers
    assert bridge.event_router.telephony_handlers["test_event"] == bridge.handle_test_event

@pytest.mark.asyncio
async def test_send_platform_json(bridge, mock_websocket):
    """Test sending JSON to platform websocket."""
    test_payload = {"type": "test", "data": "test_data"}
    await bridge.send_platform_json(test_payload)
    mock_websocket.send_json.assert_called_once_with(test_payload)

@pytest.mark.asyncio
async def test_close(bridge, mock_websocket, mock_realtime_websocket):
    """Test bridge closure."""
    # Mock the realtime handler's close method
    bridge.realtime_handler.close = AsyncMock()

    # Mock _is_websocket_closed to return False so close() is called
    bridge._is_websocket_closed = MagicMock(return_value=False)

    # Mock the websocket's client_state to be CONNECTED
    mock_websocket.client_state = WebSocketState.CONNECTED

    # Ensure platform_websocket is set
    bridge.platform_websocket = mock_websocket

    # Mock the close method to be an async method
    mock_websocket.close = AsyncMock()

    await bridge.close()
    assert bridge._closed is True
    mock_websocket.close.assert_called_once()

@pytest.mark.asyncio
async def test_initialize_conversation(bridge):
    """Test conversation initialization."""
    test_conversation_id = "test-conv-123"
    await bridge.initialize_conversation(test_conversation_id)
    assert bridge.conversation_id == test_conversation_id
    assert bridge.call_recorder is not None
    assert bridge.call_recorder.conversation_id == test_conversation_id

@pytest.mark.asyncio
async def test_handle_audio_commit(bridge):
    """Test audio commit handling."""
    bridge.audio_handler.commit_audio_buffer = AsyncMock()
    bridge.session_manager.create_response = AsyncMock()
    bridge.realtime_handler.response_active = False
    
    await bridge.handle_audio_commit()
    bridge.audio_handler.commit_audio_buffer.assert_called_once()
    bridge.session_manager.create_response.assert_called_once()

@pytest.mark.asyncio
async def test_receive_from_platform(bridge, mock_websocket):
    """Test receiving messages from platform."""
    test_message = {"type": "test_event", "data": "test_data"}
    mock_websocket.iter_text.return_value = AsyncIterator([json.dumps(test_message)])
    
    # Mock the event router to prevent actual event handling
    bridge.event_router.handle_telephony_event = AsyncMock()
    
    await bridge.receive_from_platform()
    bridge.event_router.handle_telephony_event.assert_called_once_with(test_message)

@pytest.mark.asyncio
async def test_receive_from_realtime(bridge):
    """Test receiving messages from realtime API."""
    bridge.realtime_handler.receive_from_realtime = AsyncMock()
    await bridge.receive_from_realtime()
    bridge.realtime_handler.receive_from_realtime.assert_called_once()

@pytest.mark.asyncio
async def test_websocket_closed_check(bridge, mock_websocket):
    """Test websocket closed state check."""
    # Test when websocket is None
    bridge.platform_websocket = None
    assert bridge._is_websocket_closed() is True
    
    # Test when websocket is disconnected
    bridge.platform_websocket = mock_websocket
    mock_websocket.client_state = "DISCONNECTED"
    assert bridge._is_websocket_closed() is True 