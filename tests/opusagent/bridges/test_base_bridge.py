import json
import pytest
import websockets
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from opusagent.bridges.base_bridge import BaseRealtimeBridge
from opusagent.handlers.event_router import EventRouter
from opusagent.handlers.audio_stream_handler import AudioStreamHandler
from opusagent.handlers.function_handler import FunctionHandler
from opusagent.handlers.session_manager import SessionManager
from opusagent.handlers.transcript_manager import TranscriptManager
from opusagent.handlers.realtime_handler import RealtimeHandler
from opusagent.models.audiocodes_api import TelephonyEventType
from opusagent.models.openai_api import SessionConfig

# Mock implementation of BaseRealtimeBridge for testing
class MockBridge(BaseRealtimeBridge):
    def register_platform_event_handlers(self):
        self.event_router.register_platform_handler(TelephonyEventType.SESSION_INITIATE, self.handle_test_event)
    
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
    websocket = AsyncMock(spec=websockets.ClientConnection)
    websocket.send = AsyncMock()
    websocket.recv = AsyncMock()
    websocket.close = AsyncMock()
    return websocket

@pytest.fixture
def test_session_config():
    return SessionConfig(
        input_audio_format="pcm16",
        output_audio_format="pcm16",
        voice="verse",
        instructions="Test instructions",
        tools=[],
    )

@pytest.fixture
async def bridge(mock_websocket, mock_realtime_websocket, test_session_config):
    bridge = MockBridge(mock_websocket, mock_realtime_websocket, test_session_config)
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
    bridge.register_platform_event_handlers()
    assert TelephonyEventType.SESSION_INITIATE in bridge.event_router.telephony_handlers
    assert bridge.event_router.telephony_handlers[TelephonyEventType.SESSION_INITIATE] == bridge.handle_test_event

@pytest.mark.asyncio
async def test_send_platform_json(bridge, mock_websocket):
    """Test sending JSON to platform websocket."""
    test_payload = {"type": "session.initiate", "data": "test_data"}
    await bridge.send_platform_json(test_payload)
    mock_websocket.send_json.assert_called_once_with(test_payload)

@pytest.mark.asyncio
async def test_close(bridge, mock_websocket, mock_realtime_websocket):
    """Test bridge closure."""
    # Verify initial state
    assert bridge._closed is False
    
    # Mock dependencies
    bridge.realtime_handler.close = AsyncMock()
    
    # Close the bridge
    await bridge.close()
    
    # Verify the bridge is marked as closed
    assert bridge._closed is True
    
    # Verify realtime handler close was called
    bridge.realtime_handler.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_with_call_recorder(bridge, mock_websocket, mock_realtime_websocket):
    """Test bridge closure with call recorder."""
    # Set up call recorder mock
    mock_call_recorder = AsyncMock()
    mock_call_recorder.stop_recording = AsyncMock(return_value=True)  # Success case
    mock_call_recorder.get_recording_summary = MagicMock(return_value="Test summary")
    bridge.call_recorder = mock_call_recorder
    
    # Mock dependencies
    bridge.realtime_handler.close = AsyncMock()
    
    # Close the bridge
    await bridge.close()
    
    # Verify the bridge is marked as closed
    assert bridge._closed is True
    
    # Verify call recorder was stopped
    mock_call_recorder.stop_recording.assert_called_once()
    mock_call_recorder.get_recording_summary.assert_called_once()
    
    # Verify realtime handler close was called
    bridge.realtime_handler.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_with_call_recorder_partial_failure(bridge, mock_websocket, mock_realtime_websocket):
    """Test bridge closure with call recorder that returns False (partial failure)."""
    # Set up call recorder mock that returns False (partial failure)
    mock_call_recorder = AsyncMock()
    mock_call_recorder.stop_recording = AsyncMock(return_value=False)
    mock_call_recorder.get_recording_summary = MagicMock(return_value="Test summary with errors")
    bridge.call_recorder = mock_call_recorder
    
    # Mock dependencies
    bridge.realtime_handler.close = AsyncMock()
    
    # Close the bridge
    await bridge.close()
    
    # Verify the bridge is marked as closed
    assert bridge._closed is True
    
    # Verify call recorder was stopped
    mock_call_recorder.stop_recording.assert_called_once()
    mock_call_recorder.get_recording_summary.assert_called_once()
    
    # Verify realtime handler close was called
    bridge.realtime_handler.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_with_call_recorder_summary_error(bridge, mock_websocket, mock_realtime_websocket):
    """Test bridge closure when call recorder summary throws an error."""
    # Set up call recorder mock that throws an error on get_recording_summary
    mock_call_recorder = AsyncMock()
    mock_call_recorder.stop_recording = AsyncMock(return_value=True)
    mock_call_recorder.get_recording_summary = MagicMock(side_effect=Exception("Summary error"))
    bridge.call_recorder = mock_call_recorder
    
    # Mock dependencies
    bridge.realtime_handler.close = AsyncMock()
    
    # Close the bridge - should not raise an exception
    await bridge.close()
    
    # Verify the bridge is still marked as closed despite the error
    assert bridge._closed is True
    
    # Verify call recorder stop was attempted
    mock_call_recorder.stop_recording.assert_called_once()
    mock_call_recorder.get_recording_summary.assert_called_once()
    
    # Verify realtime handler close was still called
    bridge.realtime_handler.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_with_call_recorder_emergency_cleanup(bridge, mock_websocket, mock_realtime_websocket):
    """Test bridge closure with call recorder that needs emergency cleanup."""
    # Set up call recorder mock that throws an error on stop_recording
    mock_call_recorder = AsyncMock()
    mock_call_recorder.stop_recording = AsyncMock(side_effect=Exception("Critical recording error"))
    mock_call_recorder.emergency_cleanup = AsyncMock()
    bridge.call_recorder = mock_call_recorder
    
    # Mock dependencies
    bridge.realtime_handler.close = AsyncMock()
    
    # Close the bridge - should not raise an exception
    await bridge.close()
    
    # Verify the bridge is still marked as closed despite the error
    assert bridge._closed is True
    
    # Verify call recorder stop was attempted
    mock_call_recorder.stop_recording.assert_called_once()
    
    # Verify emergency cleanup was called
    mock_call_recorder.emergency_cleanup.assert_called_once()
    
    # Verify realtime handler close was still called
    bridge.realtime_handler.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_with_call_recorder_emergency_cleanup_error(bridge, mock_websocket, mock_realtime_websocket):
    """Test bridge closure when both call recorder stop and emergency cleanup fail."""
    # Set up call recorder mock that throws errors on both stop_recording and emergency_cleanup
    mock_call_recorder = AsyncMock()
    mock_call_recorder.stop_recording = AsyncMock(side_effect=Exception("Critical recording error"))
    mock_call_recorder.emergency_cleanup = AsyncMock(side_effect=Exception("Emergency cleanup error"))
    bridge.call_recorder = mock_call_recorder
    
    # Mock dependencies
    bridge.realtime_handler.close = AsyncMock()
    
    # Close the bridge - should not raise an exception
    await bridge.close()
    
    # Verify the bridge is still marked as closed despite the errors
    assert bridge._closed is True
    
    # Verify call recorder stop was attempted
    mock_call_recorder.stop_recording.assert_called_once()
    
    # Verify emergency cleanup was attempted
    mock_call_recorder.emergency_cleanup.assert_called_once()
    
    # Verify realtime handler close was still called
    bridge.realtime_handler.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_idempotent(bridge, mock_websocket, mock_realtime_websocket):
    """Test that calling close multiple times is safe."""
    # Mock dependencies
    bridge.realtime_handler.close = AsyncMock()
    
    # Close the bridge twice
    await bridge.close()
    await bridge.close()
    
    # Verify the bridge is marked as closed
    assert bridge._closed is True
    
    # Verify realtime handler close was called only once
    bridge.realtime_handler.close.assert_called_once()


@pytest.mark.asyncio 
async def test_close_with_call_recorder_error(bridge, mock_websocket, mock_realtime_websocket):
    """Test bridge closure when call recorder throws an error."""
    # Set up call recorder mock that throws an error
    mock_call_recorder = AsyncMock()
    mock_call_recorder.stop_recording = AsyncMock(side_effect=Exception("Recording error"))
    mock_call_recorder.emergency_cleanup = AsyncMock()  # Add emergency cleanup mock
    bridge.call_recorder = mock_call_recorder
    
    # Mock dependencies
    bridge.realtime_handler.close = AsyncMock()
    
    # Close the bridge - should not raise an exception
    await bridge.close()
    
    # Verify the bridge is still marked as closed despite the error
    assert bridge._closed is True
    
    # Verify call recorder stop was attempted
    mock_call_recorder.stop_recording.assert_called_once()
    
    # Verify emergency cleanup was called
    mock_call_recorder.emergency_cleanup.assert_called_once()
    
    # Verify realtime handler close was still called
    bridge.realtime_handler.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_websocket_when_disconnected(bridge, mock_websocket, mock_realtime_websocket):
    """Test bridge closure when websocket is already disconnected."""
    from starlette.websockets import WebSocketState
    
    # Mock dependencies
    bridge.realtime_handler.close = AsyncMock()
    mock_websocket.close = AsyncMock()
    mock_websocket.client_state = WebSocketState.DISCONNECTED
    
    # Close the bridge
    await bridge.close()
    
    # Verify the bridge is marked as closed
    assert bridge._closed is True
    
    # Verify realtime handler close was called
    bridge.realtime_handler.close.assert_called_once()
    
    # Verify platform websocket close was NOT called (since websocket is DISCONNECTED)
    mock_websocket.close.assert_not_called()

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
    test_message = {"type": "session.initiate", "data": "test_data"}
    mock_websocket.iter_text.return_value = AsyncIterator([json.dumps(test_message)])
    
    # Mock the event router to prevent actual event handling
    bridge.event_router.handle_platform_event = AsyncMock()
    
    await bridge.receive_from_platform()
    bridge.event_router.handle_platform_event.assert_called_once_with(test_message)

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

@pytest.mark.asyncio
async def test_close_with_websocket_error_handling(bridge, mock_websocket, mock_realtime_websocket):
    """Test bridge closure with proper error handling even if websocket operations fail."""
    # Mock dependencies
    bridge.realtime_handler.close = AsyncMock()
    
    # Close the bridge - should not raise any exceptions
    await bridge.close()
    
    # Verify the bridge is marked as closed
    assert bridge._closed is True
    
    # Verify realtime handler close was called
    bridge.realtime_handler.close.assert_called_once() 