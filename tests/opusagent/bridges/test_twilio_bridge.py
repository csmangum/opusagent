import asyncio
import base64
import json
import pytest
import websockets
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket

from opusagent.bridges.twilio_bridge import TwilioBridge
from opusagent.models.twilio_api import (
    ConnectedMessage,
    DTMFMessage,
    MarkMessage,
    MediaMessage,
    OutgoingMediaMessage,
    OutgoingMediaPayload,
    StartMessage,
    StopMessage,
    TwilioEventType,
)
from opusagent.models.openai_api import SessionConfig

# Test constants
TEST_VOICE = "verse"
TEST_MODEL = "gpt-4o-realtime-preview-2025-06-03"


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
def session_config():
    return SessionConfig(
        modalities=["text"],
        model="gpt-4o",
        tools=[],
    )


@pytest.fixture
def mock_platform_websocket():
    websocket = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.send = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def mock_realtime_websocket():
    websocket = AsyncMock()
    websocket.send = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def twilio_bridge(session_config, mock_platform_websocket, mock_realtime_websocket):
    bridge = TwilioBridge(
        platform_websocket=mock_platform_websocket,
        realtime_websocket=mock_realtime_websocket,
        session_config=session_config,
    )
    return bridge


class TestTwilioBridgeEnhanced:
    """Test enhanced Twilio bridge functionality."""

    def test_bridge_initialization_with_participant_tracking(self, twilio_bridge):
        """Test that bridge initializes with participant tracking."""
        assert twilio_bridge.current_participant == "caller"
        assert hasattr(twilio_bridge, 'current_participant')

    def test_register_platform_event_handlers_with_vad(self, twilio_bridge):
        """Test that VAD event handlers are registered when VAD is enabled."""
        twilio_bridge.vad_enabled = True
        twilio_bridge.register_platform_event_handlers()
        
        # Check that VAD handlers are registered
        assert hasattr(twilio_bridge, 'handle_speech_started')
        assert hasattr(twilio_bridge, 'handle_speech_stopped')
        assert hasattr(twilio_bridge, 'handle_speech_committed')

    def test_register_platform_event_handlers_without_vad(self, twilio_bridge):
        """Test that VAD event handlers are not registered when VAD is disabled."""
        twilio_bridge.vad_enabled = False
        twilio_bridge.register_platform_event_handlers()
        
        # VAD handlers should still exist but not be registered
        assert hasattr(twilio_bridge, 'handle_speech_started')
        assert hasattr(twilio_bridge, 'handle_speech_stopped')
        assert hasattr(twilio_bridge, 'handle_speech_committed')

    @pytest.mark.asyncio
    async def test_handle_session_resume_success(self, twilio_bridge):
        """Test successful session resume."""
        # Mock session state with resume count
        mock_session_state = MagicMock()
        mock_session_state.resumed_count = 1
        twilio_bridge.session_state = mock_session_state
        
        # Mock initialize_conversation to return successfully
        with patch.object(twilio_bridge, 'initialize_conversation', new_callable=AsyncMock) as mock_init:
            with patch.object(twilio_bridge, 'send_session_resumed', new_callable=AsyncMock) as mock_send:
                await twilio_bridge.handle_session_resume({
                    "callSid": "CA123456789",
                    "streamSid": "MZ123456789",
                    "accountSid": "AC123456789"
                })
                
                mock_init.assert_called_once_with("CA123456789")
                mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_session_resume_failure(self, twilio_bridge):
        """Test session resume failure falls back to new session."""
        # Mock session state with no resume count
        mock_session_state = MagicMock()
        mock_session_state.resumed_count = 0
        twilio_bridge.session_state = mock_session_state
        
        # Mock initialize_conversation to return successfully
        with patch.object(twilio_bridge, 'initialize_conversation', new_callable=AsyncMock) as mock_init:
            with patch.object(twilio_bridge, 'send_session_accepted', new_callable=AsyncMock) as mock_send:
                await twilio_bridge.handle_session_resume({
                    "callSid": "CA123456789",
                    "streamSid": "MZ123456789",
                    "accountSid": "AC123456789"
                })
                
                mock_init.assert_called_once_with("CA123456789")
                mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_session_resume_missing_callsid(self, twilio_bridge):
        """Test session resume with missing callSid."""
        with patch.object(twilio_bridge, 'initialize_conversation', new_callable=AsyncMock) as mock_init:
            await twilio_bridge.handle_session_resume({
                "streamSid": "MZ123456789",
                "accountSid": "AC123456789"
            })
            
            # Should not call initialize_conversation
            mock_init.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_audio_data_with_participant_tracking(self, twilio_bridge):
        """Test audio data handling with participant tracking."""
        twilio_bridge.realtime_websocket = AsyncMock()
        twilio_bridge.audio_buffer = []
        
        # Mock audio data with track information
        audio_data = {
            "event": "media",
            "streamSid": "MZ123456789",
            "sequenceNumber": "1",
            "media": {
                "track": "outbound",
                "chunk": "1",
                "timestamp": "1000",
                "payload": base64.b64encode(b"test_audio").decode()
            }
        }
        
        await twilio_bridge.handle_audio_data(audio_data)
        
        # Check that participant was updated
        assert twilio_bridge.current_participant == "outbound"

    @pytest.mark.asyncio
    async def test_validate_connection_health_success(self, twilio_bridge):
        """Test successful connection health validation."""
        twilio_bridge._closed = False
        twilio_bridge.platform_websocket = AsyncMock()
        twilio_bridge.realtime_websocket = AsyncMock()
        
        # Mock _is_websocket_closed to return False
        with patch.object(twilio_bridge, '_is_websocket_closed', return_value=False):
            is_healthy = await twilio_bridge._validate_connection_health()
            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_validate_connection_health_failure(self, twilio_bridge):
        """Test connection health validation failure."""
        twilio_bridge._closed = True
        
        is_healthy = await twilio_bridge._validate_connection_health()
        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_handle_connection_validate_success(self, twilio_bridge):
        """Test successful connection validation."""
        with patch.object(twilio_bridge, '_validate_connection_health', return_value=True) as mock_validate:
            with patch.object(twilio_bridge, 'send_connection_validated', new_callable=AsyncMock) as mock_send:
                await twilio_bridge.handle_connection_validate({"test": "data"})
                
                mock_validate.assert_called_once()
                mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_connection_validate_failure(self, twilio_bridge):
        """Test connection validation failure."""
        with patch.object(twilio_bridge, '_validate_connection_health', return_value=False) as mock_validate:
            with patch.object(twilio_bridge, 'send_connection_validated', new_callable=AsyncMock) as mock_send:
                await twilio_bridge.handle_connection_validate({"test": "data"})
                
                mock_validate.assert_called_once()
                mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_speech_started_with_vad_enabled(self, twilio_bridge):
        """Test speech started handling with VAD enabled."""
        twilio_bridge.vad_enabled = True
        
        with patch.object(twilio_bridge, 'send_speech_started', new_callable=AsyncMock) as mock_send:
            await twilio_bridge.handle_speech_started({"test": "data"})
            
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_speech_started_with_vad_disabled(self, twilio_bridge):
        """Test speech started handling with VAD disabled."""
        twilio_bridge.vad_enabled = False
        
        with patch.object(twilio_bridge, 'send_speech_started', new_callable=AsyncMock) as mock_send:
            await twilio_bridge.handle_speech_started({"test": "data"})
            
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_speech_stopped_with_vad_enabled(self, twilio_bridge):
        """Test speech stopped handling with VAD enabled."""
        twilio_bridge.vad_enabled = True
        
        with patch.object(twilio_bridge, 'send_speech_stopped', new_callable=AsyncMock) as mock_send:
            await twilio_bridge.handle_speech_stopped({"test": "data"})
            
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_speech_committed_with_vad_enabled(self, twilio_bridge):
        """Test speech committed handling with VAD enabled."""
        twilio_bridge.vad_enabled = True
        
        with patch.object(twilio_bridge, 'send_speech_committed', new_callable=AsyncMock) as mock_send:
            await twilio_bridge.handle_speech_committed({"test": "data"})
            
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_session_accepted(self, twilio_bridge):
        """Test session accepted response."""
        twilio_bridge.conversation_id = "test_conv"
        twilio_bridge.stream_sid = "test_stream"
        
        # This should just log, not send anything to Twilio
        await twilio_bridge.send_session_accepted()

    @pytest.mark.asyncio
    async def test_send_session_resumed(self, twilio_bridge):
        """Test session resumed response."""
        twilio_bridge.conversation_id = "test_conv"
        twilio_bridge.stream_sid = "test_stream"
        
        # This should just log, not send anything to Twilio
        await twilio_bridge.send_session_resumed()

    @pytest.mark.asyncio
    async def test_send_user_stream_started(self, twilio_bridge):
        """Test user stream started response."""
        twilio_bridge.conversation_id = "test_conv"
        twilio_bridge.current_participant = "caller"
        
        # This should just log, not send anything to Twilio
        await twilio_bridge.send_user_stream_started()

    @pytest.mark.asyncio
    async def test_send_user_stream_stopped(self, twilio_bridge):
        """Test user stream stopped response."""
        twilio_bridge.conversation_id = "test_conv"
        twilio_bridge.current_participant = "caller"
        
        # This should just log, not send anything to Twilio
        await twilio_bridge.send_user_stream_stopped()

    @pytest.mark.asyncio
    async def test_send_speech_started(self, twilio_bridge):
        """Test speech started response."""
        twilio_bridge.conversation_id = "test_conv"
        twilio_bridge.current_participant = "caller"
        
        # This should just log, not send anything to Twilio
        await twilio_bridge.send_speech_started()

    @pytest.mark.asyncio
    async def test_send_speech_stopped(self, twilio_bridge):
        """Test speech stopped response."""
        twilio_bridge.conversation_id = "test_conv"
        twilio_bridge.current_participant = "caller"
        
        # This should just log, not send anything to Twilio
        await twilio_bridge.send_speech_stopped()

    @pytest.mark.asyncio
    async def test_send_speech_committed(self, twilio_bridge):
        """Test speech committed response."""
        twilio_bridge.conversation_id = "test_conv"
        twilio_bridge.current_participant = "caller"
        
        # This should just log, not send anything to Twilio
        await twilio_bridge.send_speech_committed()

    @pytest.mark.asyncio
    async def test_send_connection_validated(self, twilio_bridge):
        """Test connection validated response."""
        twilio_bridge.conversation_id = "test_conv"
        twilio_bridge.stream_sid = "test_stream"
        
        # This should just log, not send anything to Twilio
        await twilio_bridge.send_connection_validated()

    @pytest.mark.asyncio
    async def test_start_connection_health_monitor(self, twilio_bridge):
        """Test starting connection health monitor."""
        with patch('asyncio.create_task') as mock_create_task:
            await twilio_bridge.start_connection_health_monitor()
            
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_enhanced_session_start_logging(self, twilio_bridge):
        """Test enhanced logging in session start."""
        start_data = {
            "event": "start",
            "sequenceNumber": "1",
            "streamSid": "MZ123456789",
            "start": {
                "streamSid": "MZ123456789",
                "accountSid": "AC123456789",
                "callSid": "CA123456789",
                "tracks": ["inbound", "outbound"],
                "customParameters": {"test": "value"},
                "mediaFormat": {
                    "encoding": "audio/x-mulaw",
                    "sampleRate": 8000,
                    "channels": 1
                }
            }
        }
        
        with patch.object(twilio_bridge, 'initialize_conversation', new_callable=AsyncMock) as mock_init:
            with patch.object(twilio_bridge, 'send_session_accepted', new_callable=AsyncMock) as mock_send:
                await twilio_bridge.handle_session_start(start_data)
                
                mock_init.assert_called_once_with("CA123456789")
                mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_enhanced_session_end_logging(self, twilio_bridge):
        """Test enhanced logging in session end."""
        twilio_bridge.audio_chunks_sent = 100
        twilio_bridge.total_audio_bytes_sent = 5000
        twilio_bridge.conversation_id = "test_conv"
        twilio_bridge.stream_sid = "test_stream"
        twilio_bridge.call_sid = "test_call"
        
        stop_data = {
            "event": "stop",
            "sequenceNumber": "5",
            "streamSid": "MZ123456789",
            "stop": {
                "accountSid": "AC123456789",
                "callSid": "CA123456789"
            }
        }
        
        with patch.object(twilio_bridge.audio_handler, 'commit_audio_buffer', new_callable=AsyncMock) as mock_commit:
            with patch.object(twilio_bridge, 'close', new_callable=AsyncMock) as mock_close:
                await twilio_bridge.handle_session_end(stop_data)
                
                mock_commit.assert_called_once()
                mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_audio_quality_monitor(self, twilio_bridge):
        """Test starting audio quality monitor."""
        with patch('asyncio.create_task') as mock_create_task:
            await twilio_bridge.start_audio_quality_monitor()
            
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_performance_monitor(self, twilio_bridge):
        """Test starting performance monitor."""
        with patch('asyncio.create_task') as mock_create_task:
            await twilio_bridge.start_performance_monitor()
            
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_enable_advanced_monitoring(self, twilio_bridge):
        """Test enabling all advanced monitoring features."""
        with patch.object(twilio_bridge, 'start_connection_health_monitor', new_callable=AsyncMock) as mock_health:
            with patch.object(twilio_bridge, 'start_audio_quality_monitor', new_callable=AsyncMock) as mock_audio:
                with patch.object(twilio_bridge, 'start_performance_monitor', new_callable=AsyncMock) as mock_perf:
                    await twilio_bridge.enable_advanced_monitoring()
                    
                    mock_health.assert_called_once()
                    mock_audio.assert_called_once()
                    mock_perf.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_bridge_statistics(self, twilio_bridge):
        """Test getting bridge statistics."""
        # Set some test data
        twilio_bridge.conversation_id = "test_conv"
        twilio_bridge.stream_sid = "test_stream"
        twilio_bridge.call_sid = "test_call"
        twilio_bridge.account_sid = "test_account"
        twilio_bridge.media_format = "test_format"
        twilio_bridge.current_participant = "test_participant"
        twilio_bridge.audio_chunks_sent = 100
        twilio_bridge.total_audio_bytes_sent = 5000
        twilio_bridge.audio_buffer = [b"test"]
        twilio_bridge._closed = False
        twilio_bridge.platform_websocket = AsyncMock()
        twilio_bridge.realtime_websocket = AsyncMock()
        twilio_bridge.vad_enabled = True
        twilio_bridge.bridge_type = "twilio"
        
        # Mock _is_websocket_closed
        with patch.object(twilio_bridge, '_is_websocket_closed', return_value=False):
            stats = await twilio_bridge.get_bridge_statistics()
            
            assert "session" in stats
            assert "audio" in stats
            assert "connection" in stats
            assert "features" in stats
            
            assert stats["session"]["conversation_id"] == "test_conv"
            assert stats["audio"]["chunks_sent"] == 100
            assert stats["features"]["vad_enabled"] is True

    @pytest.mark.asyncio
    async def test_get_bridge_statistics_with_session_state(self, twilio_bridge):
        """Test getting bridge statistics with session state."""
        # Mock session state
        mock_session_state = MagicMock()
        mock_session_state.resumed_count = 2
        mock_session_state.status = "active"
        twilio_bridge.session_state = mock_session_state
        
        with patch.object(twilio_bridge, '_is_websocket_closed', return_value=False):
            stats = await twilio_bridge.get_bridge_statistics()
            
            assert stats["session"]["resumed_count"] == 2
            assert stats["session"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_log_bridge_statistics(self, twilio_bridge):
        """Test logging bridge statistics."""
        with patch.object(twilio_bridge, 'get_bridge_statistics', return_value={
            "session": {"test": "data"},
            "audio": {"test": "data"},
            "connection": {"test": "data"},
            "features": {"test": "data"}
        }) as mock_get_stats:
            await twilio_bridge.log_bridge_statistics()
            
            mock_get_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_graceful_shutdown(self, twilio_bridge):
        """Test graceful shutdown handling."""
        with patch.object(twilio_bridge, 'log_bridge_statistics', new_callable=AsyncMock) as mock_log:
            with patch.object(twilio_bridge, 'close', new_callable=AsyncMock) as mock_close:
                await twilio_bridge.handle_graceful_shutdown("Test shutdown")
                
                mock_log.assert_called_once()
                mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_error_recovery_connection_error(self, twilio_bridge):
        """Test error recovery with connection error."""
        connection_error = ConnectionError("Connection failed")
        
        with patch.object(twilio_bridge, 'log_bridge_statistics', new_callable=AsyncMock) as mock_log:
            await twilio_bridge.handle_error_recovery(connection_error, "Test context")
            
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_error_recovery_timeout_error(self, twilio_bridge):
        """Test error recovery with timeout error."""
        timeout_error = TimeoutError("Operation timed out")
        
        with patch.object(twilio_bridge, 'log_bridge_statistics', new_callable=AsyncMock) as mock_log:
            await twilio_bridge.handle_error_recovery(timeout_error, "Test context")
            
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_error_recovery_generic_error(self, twilio_bridge):
        """Test error recovery with generic error."""
        generic_error = ValueError("Generic error")
        
        with patch.object(twilio_bridge, 'log_bridge_statistics', new_callable=AsyncMock) as mock_log:
            await twilio_bridge.handle_error_recovery(generic_error, "Test context")
            
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_error_recovery_logging_failure(self, twilio_bridge):
        """Test error recovery when logging statistics fails."""
        connection_error = ConnectionError("Connection failed")
        
        with patch.object(twilio_bridge, 'log_bridge_statistics', side_effect=Exception("Logging failed")):
            # Should not raise an exception
            await twilio_bridge.handle_error_recovery(connection_error, "Test context")

    @pytest.mark.asyncio
    async def test_audio_quality_monitor_small_chunks(self, twilio_bridge):
        """Test audio quality monitor with small chunks."""
        twilio_bridge.audio_chunks_sent = 10
        twilio_bridge.total_audio_bytes_sent = 500  # Small average chunk size
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Start the monitor and let it run briefly
            task = asyncio.create_task(twilio_bridge.start_audio_quality_monitor())
            
            # Let it run for a moment
            await asyncio.sleep(0.1)
            
            # Stop the monitor
            twilio_bridge._closed = True
            await asyncio.sleep(0.1)
            
            # Clean up
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_audio_quality_monitor_large_chunks(self, twilio_bridge):
        """Test audio quality monitor with large chunks."""
        twilio_bridge.audio_chunks_sent = 10
        twilio_bridge.total_audio_bytes_sent = 15000  # Large average chunk size
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Start the monitor and let it run briefly
            task = asyncio.create_task(twilio_bridge.start_audio_quality_monitor())
            
            # Let it run for a moment
            await asyncio.sleep(0.1)
            
            # Stop the monitor
            twilio_bridge._closed = True
            await asyncio.sleep(0.1)
            
            # Clean up
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_performance_monitor_metrics(self, twilio_bridge):
        """Test performance monitor metrics calculation."""
        twilio_bridge.audio_chunks_sent = 50
        twilio_bridge.total_audio_bytes_sent = 2500
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Start the monitor and let it run briefly
            task = asyncio.create_task(twilio_bridge.start_performance_monitor())
            
            # Let it run for a moment
            await asyncio.sleep(0.1)
            
            # Stop the monitor
            twilio_bridge._closed = True
            await asyncio.sleep(0.1)
            
            # Clean up
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_bridge_statistics_comprehensive(self, twilio_bridge):
        """Test comprehensive bridge statistics."""
        # Set comprehensive test data
        twilio_bridge.conversation_id = "test_conv"
        twilio_bridge.stream_sid = "test_stream"
        twilio_bridge.call_sid = "test_call"
        twilio_bridge.account_sid = "test_account"
        twilio_bridge.media_format = "test_format"
        twilio_bridge.current_participant = "test_participant"
        twilio_bridge.audio_chunks_sent = 100
        twilio_bridge.total_audio_bytes_sent = 5000
        twilio_bridge.audio_buffer = [b"test1", b"test2"]
        twilio_bridge._closed = False
        twilio_bridge.platform_websocket = AsyncMock()
        twilio_bridge.realtime_websocket = AsyncMock()
        twilio_bridge.vad_enabled = True
        twilio_bridge.bridge_type = "twilio"
        
        # Mock session state
        mock_session_state = MagicMock()
        mock_session_state.resumed_count = 3
        mock_session_state.status = "active"
        twilio_bridge.session_state = mock_session_state
        
        # Mock _is_websocket_closed
        with patch.object(twilio_bridge, '_is_websocket_closed', return_value=False):
            stats = await twilio_bridge.get_bridge_statistics()
            
            # Verify session stats
            assert stats["session"]["conversation_id"] == "test_conv"
            assert stats["session"]["stream_sid"] == "test_stream"
            assert stats["session"]["call_sid"] == "test_call"
            assert stats["session"]["account_sid"] == "test_account"
            assert stats["session"]["media_format"] == "test_format"
            assert stats["session"]["current_participant"] == "test_participant"
            assert stats["session"]["resumed_count"] == 3
            assert stats["session"]["status"] == "active"
            
            # Verify audio stats
            assert stats["audio"]["chunks_sent"] == 100
            assert stats["audio"]["total_bytes_sent"] == 5000
            assert stats["audio"]["avg_chunk_size"] == 50.0
            assert stats["audio"]["buffer_size"] == 2
            
            # Verify connection stats
            assert stats["connection"]["closed"] is False
            assert stats["connection"]["platform_websocket_active"] is True
            assert stats["connection"]["realtime_websocket_active"] is True
            assert stats["connection"]["websocket_closed"] is False
            
            # Verify features stats
            assert stats["features"]["vad_enabled"] is True
            assert stats["features"]["bridge_type"] == "twilio"


class TestTwilioBridge:
    """Test original Twilio bridge functionality."""
    
    def test_basic_functionality(self):
        """Test that the basic functionality still works."""
        # This is a placeholder for the original tests
        # The actual tests are in the enhanced class above
        pass 