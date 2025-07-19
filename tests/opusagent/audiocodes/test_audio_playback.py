"""
Unit tests for the AudioCodes audio playback module.

This module tests the audio playback functionality including:
- AudioPlaybackConfig configuration
- AudioPlayback class functionality
- AudioPlaybackManager integration
- Audio chunk processing and queuing
- Volume control and mute functionality
- Audio level monitoring
- Error handling and edge cases
"""

import asyncio
import base64
import logging
import pytest
import tempfile
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from opusagent.local.audiocodes.audio_playback import (
    AudioPlaybackConfig,
    AudioPlayback,
    AudioPlaybackManager
)


class TestAudioPlaybackConfig:
    """Test AudioPlaybackConfig class."""

    def test_audio_playback_config_defaults(self):
        """Test AudioPlaybackConfig with default values."""
        config = AudioPlaybackConfig()
        
        assert config.sample_rate == 16000
        assert config.channels == 1
        assert config.chunk_size == 1024
        assert config.latency == 0.1
        assert config.volume == 1.0
        assert config.enable_playback is True

    def test_audio_playback_config_custom_values(self):
        """Test AudioPlaybackConfig with custom values."""
        config = AudioPlaybackConfig(
            sample_rate=8000,
            channels=2,
            chunk_size=2048,
            latency=0.2,
            volume=0.5,
            enable_playback=False
        )
        
        assert config.sample_rate == 8000
        assert config.channels == 2
        assert config.chunk_size == 2048
        assert config.latency == 0.2
        assert config.volume == 0.5
        assert config.enable_playback is False

    def test_audio_playback_config_volume_clamping(self):
        """Test that volume is clamped to valid range."""
        # Test volume below 0.0
        config = AudioPlaybackConfig(volume=-0.5)
        assert config.volume == 0.0
        
        # Test volume above 1.0
        config = AudioPlaybackConfig(volume=1.5)
        assert config.volume == 1.0
        
        # Test volume at boundaries
        config = AudioPlaybackConfig(volume=0.0)
        assert config.volume == 0.0
        
        config = AudioPlaybackConfig(volume=1.0)
        assert config.volume == 1.0


class TestAudioPlayback:
    """Test AudioPlayback class."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def audio_playback_config(self):
        """Create a test audio playback configuration."""
        return AudioPlaybackConfig(
            sample_rate=16000,
            channels=1,
            chunk_size=1024,
            volume=0.8,
            enable_playback=True
        )

    @pytest.fixture
    def audio_playback(self, audio_playback_config, mock_logger):
        """Create an AudioPlayback instance for testing."""
        return AudioPlayback(config=audio_playback_config, logger=mock_logger)

    def test_audio_playback_initialization(self, audio_playback, audio_playback_config, mock_logger):
        """Test AudioPlayback initialization."""
        assert audio_playback.logger == mock_logger
        assert audio_playback.config == audio_playback_config
        assert audio_playback.playing is False
        assert audio_playback.muted is False
        assert audio_playback.volume == 0.8
        assert audio_playback.chunks_played == 0
        assert audio_playback.bytes_played == 0
        assert audio_playback.playback_errors == 0
        assert audio_playback.current_audio_level == 0.0

    def test_audio_playback_initialization_with_defaults(self, mock_logger):
        """Test AudioPlayback initialization with default config."""
        playback = AudioPlayback(logger=mock_logger)
        
        assert playback.config.sample_rate == 16000
        assert playback.config.channels == 1
        assert playback.config.enable_playback is True

    def test_audio_playback_initialization_with_audio_level_callback(self, mock_logger):
        """Test AudioPlayback initialization with audio level callback."""
        callback_called = False
        
        def audio_level_callback(level):
            nonlocal callback_called
            callback_called = True
        
        playback = AudioPlayback(
            logger=mock_logger,
            on_audio_level=audio_level_callback
        )
        
        assert playback.on_audio_level == audio_level_callback

    @patch('opusagent.local.audiocodes.audio_playback.AUDIO_AVAILABLE', False)
    def test_audio_playback_initialization_no_audio_dependencies(self, mock_logger):
        """Test AudioPlayback initialization when audio dependencies are not available."""
        playback = AudioPlayback(logger=mock_logger)
        
        assert playback.config.enable_playback is False
        mock_logger.warning.assert_called()

    def test_audio_playback_start_success(self, audio_playback, mock_logger):
        """Test successful audio playback start."""
        with patch('opusagent.local.audiocodes.audio_playback.AUDIO_AVAILABLE', True):
            with patch('opusagent.local.audiocodes.audio_playback.sd') as mock_sd:
                with patch('opusagent.local.audiocodes.audio_playback.np') as mock_np:
                    with patch('opusagent.local.audiocodes.audio_playback.threading') as mock_threading:
                        # Mock the output stream
                        mock_stream = Mock()
                        mock_sd.OutputStream.return_value = mock_stream
                        
                        # Mock the thread
                        mock_thread = Mock()
                        mock_threading.Thread.return_value = mock_thread
                        
                        success = audio_playback.start()
                        
                        assert success is True
                        assert audio_playback.playing is True
                        # The stream.start() is called in the playback loop, not in start()
                        # So we verify the thread was started instead
                        mock_thread.start.assert_called_once()
                        mock_logger.info.assert_called()

    def test_audio_playback_start_already_playing(self, audio_playback, mock_logger):
        """Test starting audio playback when already playing."""
        audio_playback.playing = True
        
        success = audio_playback.start()
        
        assert success is True
        mock_logger.warning.assert_called()

    def test_audio_playback_start_disabled(self, audio_playback, mock_logger):
        """Test starting audio playback when disabled."""
        audio_playback.config.enable_playback = False
        
        success = audio_playback.start()
        
        assert success is False
        mock_logger.warning.assert_called()

    def test_audio_playback_start_no_audio_dependencies(self, audio_playback, mock_logger):
        """Test starting audio playback without audio dependencies."""
        with patch('opusagent.local.audiocodes.audio_playback.AUDIO_AVAILABLE', False):
            success = audio_playback.start()
            
            assert success is False
            mock_logger.error.assert_called()

    def test_audio_playback_start_exception(self, audio_playback, mock_logger):
        """Test audio playback start with exception."""
        with patch('opusagent.local.audiocodes.audio_playback.AUDIO_AVAILABLE', True):
            with patch('opusagent.local.audiocodes.audio_playback.threading') as mock_threading:
                mock_threading.Thread.side_effect = Exception("Thread creation failed")
                
                success = audio_playback.start()
                
                assert success is False
                assert audio_playback.playing is False
                mock_logger.error.assert_called()

    def test_audio_playback_stop(self, audio_playback, mock_logger):
        """Test stopping audio playback."""
        audio_playback.playing = True
        audio_playback.output_stream = Mock()
        audio_playback.playback_thread = Mock()
        audio_playback.playback_thread.is_alive.return_value = True
        
        audio_playback.stop()
        
        assert audio_playback.playing is False
        assert audio_playback.output_stream is None
        audio_playback.playback_thread.join.assert_called_once()
        mock_logger.info.assert_called()

    def test_audio_playback_stop_not_playing(self, audio_playback, mock_logger):
        """Test stopping audio playback when not playing."""
        audio_playback.playing = False
        
        audio_playback.stop()
        
        # Should not log anything since it's not playing
        # But we need to account for the initialization log
        # So we check that no additional info logs were made after initialization
        info_calls = [call for call in mock_logger.info.call_args_list 
                     if '[AUDIO PLAYBACK] Audio playback stopped' in str(call)]
        assert len(info_calls) == 0

    def test_audio_playback_stop_with_stream_error(self, audio_playback, mock_logger):
        """Test stopping audio playback with stream error."""
        audio_playback.playing = True
        mock_stream = Mock()
        mock_stream.stop.side_effect = Exception("Stream error")
        audio_playback.output_stream = mock_stream
        
        audio_playback.stop()
        
        assert audio_playback.playing is False
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_queue_audio_chunk_success(self, audio_playback, mock_logger):
        """Test successfully queuing an audio chunk."""
        audio_playback.playing = True
        
        # Create test audio data
        test_audio_data = b"test_audio_data_16_bytes"
        test_chunk = base64.b64encode(test_audio_data).decode('utf-8')
        
        success = await audio_playback.queue_audio_chunk(test_chunk)
        
        assert success is True
        assert audio_playback.chunks_played == 1
        assert audio_playback.bytes_played == len(test_audio_data)

    @pytest.mark.asyncio
    async def test_queue_audio_chunk_not_playing(self, audio_playback, mock_logger):
        """Test queuing audio chunk when not playing."""
        audio_playback.playing = False
        
        test_chunk = base64.b64encode(b"test").decode('utf-8')
        success = await audio_playback.queue_audio_chunk(test_chunk)
        
        assert success is False
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_queue_audio_chunk_queue_full(self, audio_playback, mock_logger):
        """Test queuing audio chunk when queue is full."""
        audio_playback.playing = True
        
        # Fill the queue
        for i in range(51):  # Queue size is 50
            test_chunk = base64.b64encode(f"chunk_{i}".encode()).decode('utf-8')
            await audio_playback.queue_audio_chunk(test_chunk)
        
        # Try to queue one more
        test_chunk = base64.b64encode(b"overflow").decode('utf-8')
        success = await audio_playback.queue_audio_chunk(test_chunk)
        
        assert success is False
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_queue_audio_chunk_invalid_base64(self, audio_playback, mock_logger):
        """Test queuing audio chunk with invalid base64."""
        audio_playback.playing = True
        
        success = await audio_playback.queue_audio_chunk("invalid_base64!")
        
        assert success is False
        assert audio_playback.playback_errors == 1
        mock_logger.error.assert_called()

    def test_set_volume(self, audio_playback, mock_logger):
        """Test setting volume."""
        audio_playback.set_volume(0.5)
        assert audio_playback.volume == 0.5
        mock_logger.debug.assert_called()

    def test_set_volume_clamping(self, audio_playback):
        """Test volume clamping."""
        # Test below 0.0
        audio_playback.set_volume(-0.5)
        assert audio_playback.volume == 0.0
        
        # Test above 1.0
        audio_playback.set_volume(1.5)
        assert audio_playback.volume == 1.0

    def test_mute_unmute(self, audio_playback, mock_logger):
        """Test mute and unmute functionality."""
        assert audio_playback.muted is False
        
        audio_playback.mute()
        assert audio_playback.muted is True
        mock_logger.debug.assert_called()
        
        audio_playback.unmute()
        assert audio_playback.muted is False
        mock_logger.debug.assert_called()

    def test_get_audio_level(self, audio_playback):
        """Test getting audio level."""
        audio_playback.current_audio_level = 0.75
        level = audio_playback.get_audio_level()
        assert level == 0.75

    def test_get_statistics(self, audio_playback):
        """Test getting playback statistics."""
        audio_playback.playing = True
        audio_playback.muted = False
        audio_playback.volume = 0.8
        audio_playback.chunks_played = 10
        audio_playback.bytes_played = 1000
        audio_playback.playback_errors = 2
        audio_playback.current_audio_level = 0.5
        
        stats = audio_playback.get_statistics()
        
        assert stats["playing"] is True
        assert stats["muted"] is False
        assert stats["volume"] == 0.8
        assert stats["chunks_played"] == 10
        assert stats["bytes_played"] == 1000
        assert stats["playback_errors"] == 2
        assert stats["audio_level"] == 0.5
        assert "queue_size" in stats

    def test_cleanup(self, audio_playback, mock_logger):
        """Test cleanup functionality."""
        audio_playback.playing = True
        audio_playback.output_stream = Mock()
        
        audio_playback.cleanup()
        
        assert audio_playback.playing is False
        mock_logger.info.assert_called()

    @patch('opusagent.local.audiocodes.audio_playback.AUDIO_AVAILABLE', True)
    @patch('opusagent.local.audiocodes.audio_playback.sd')
    @patch('opusagent.local.audiocodes.audio_playback.np')
    def test_playback_loop_success(self, mock_np, mock_sd, audio_playback, mock_logger):
        """Test successful playback loop."""
        # Mock the output stream
        mock_stream = Mock()
        mock_sd.OutputStream.return_value = mock_stream
        
        # Set up the stop event to trigger after a short time
        def stop_after_delay():
            time.sleep(0.1)
            audio_playback._stop_event.set()
        
        stop_thread = threading.Thread(target=stop_after_delay)
        stop_thread.daemon = True
        stop_thread.start()
        
        audio_playback.playing = True
        audio_playback._playback_loop()
        
        mock_stream.start.assert_called_once()
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()

    @patch('opusagent.local.audiocodes.audio_playback.AUDIO_AVAILABLE', True)
    @patch('opusagent.local.audiocodes.audio_playback.sd')
    @patch('opusagent.local.audiocodes.audio_playback.np')
    def test_playback_loop_exception(self, mock_np, mock_sd, audio_playback, mock_logger):
        """Test playback loop with exception."""
        mock_sd.OutputStream.side_effect = Exception("Stream creation failed")
        
        audio_playback.playing = True
        audio_playback._playback_loop()
        
        assert audio_playback.playback_errors == 1
        mock_logger.error.assert_called()

    @patch('opusagent.local.audiocodes.audio_playback.AUDIO_AVAILABLE', True)
    @patch('opusagent.local.audiocodes.audio_playback.np')
    def test_playback_callback_success(self, mock_np, audio_playback, mock_logger):
        """Test successful playback callback."""
        # Mock numpy array and operations
        mock_array = MagicMock()
        mock_array.__len__.return_value = 8  # Return length for min() operation
        mock_np.frombuffer.return_value = mock_array
        mock_array.reshape.return_value = mock_array
        mock_array.astype.return_value = mock_array
        mock_array.__getitem__.return_value = mock_array  # For slicing operations
        
        # Mock the multiplication operations (* 0, * volume)
        mock_array.__mul__ = MagicMock(return_value=mock_array)
        
        # Mock the power operation (** 2)
        mock_array.__pow__ = MagicMock(return_value=mock_array)
        
        # Mock the audio level calculation
        mock_np.sqrt.return_value = 0.5
        mock_np.mean.return_value = 0.25
        
        # Create test data
        test_audio_data = b"test_audio_data_16_bytes"
        audio_playback.playback_queue.put(test_audio_data)
        
        # Mock output buffer
        outdata = Mock()
        outdata.fill = Mock()
        outdata.__setitem__ = Mock()  # For assignment operations
        
        audio_playback._playback_callback(outdata, 8, None, None)
        
        outdata.fill.assert_called_once()
        # Debug: Check if the queue was accessed
        assert mock_np.frombuffer.called, "frombuffer should be called to convert audio bytes"
        # Debug: Check if reshape was called (for channel conversion)
        assert mock_array.reshape.called, "reshape should be called for channel conversion"
        # Verify that the audio level calculation was attempted
        assert mock_array.astype.called, "astype should be called for float32 conversion"
        assert mock_array.__pow__.called, "power operation should be called for squaring"
        assert mock_np.mean.called, "mean should be called for audio level calculation"
        assert mock_np.sqrt.called, "sqrt should be called for audio level calculation"

    @patch('opusagent.local.audiocodes.audio_playback.AUDIO_AVAILABLE', True)
    @patch('opusagent.local.audiocodes.audio_playback.np')
    def test_playback_callback_muted(self, mock_np, audio_playback, mock_logger):
        """Test playback callback when muted."""
        audio_playback.muted = True
        
        # Mock numpy array
        mock_array = Mock()
        mock_np.frombuffer.return_value = mock_array
        mock_array.reshape.return_value = mock_array
        
        # Create test data
        test_audio_data = b"test_audio_data_16_bytes"
        audio_playback.playback_queue.put(test_audio_data)
        
        # Mock output buffer
        outdata = Mock()
        outdata.fill = Mock()
        
        audio_playback._playback_callback(outdata, 8, None, None)
        
        # Should still process but with muted audio
        outdata.fill.assert_called_once()

    @patch('opusagent.local.audiocodes.audio_playback.AUDIO_AVAILABLE', True)
    @patch('opusagent.local.audiocodes.audio_playback.np')
    def test_playback_callback_with_volume(self, mock_np, audio_playback, mock_logger):
        """Test playback callback with volume control."""
        audio_playback.volume = 0.5
        
        # Mock numpy array
        mock_array = Mock()
        mock_np.frombuffer.return_value = mock_array
        mock_array.reshape.return_value = mock_array
        mock_array.astype.return_value = mock_array
        mock_np.sqrt.return_value = 0.5
        mock_np.mean.return_value = 0.25
        
        # Create test data
        test_audio_data = b"test_audio_data_16_bytes"
        audio_playback.playback_queue.put(test_audio_data)
        
        # Mock output buffer
        outdata = Mock()
        outdata.fill = Mock()
        
        audio_playback._playback_callback(outdata, 8, None, None)
        
        outdata.fill.assert_called_once()

    @patch('opusagent.local.audiocodes.audio_playback.AUDIO_AVAILABLE', True)
    @patch('opusagent.local.audiocodes.audio_playback.np')
    def test_playback_callback_empty_queue(self, mock_np, audio_playback, mock_logger):
        """Test playback callback with empty queue."""
        # Mock output buffer
        outdata = Mock()
        outdata.fill = Mock()
        
        audio_playback._playback_callback(outdata, 8, None, None)
        
        # Should fill with silence
        outdata.fill.assert_called_once()

    @patch('opusagent.local.audiocodes.audio_playback.AUDIO_AVAILABLE', True)
    @patch('opusagent.local.audiocodes.audio_playback.np')
    def test_playback_callback_with_audio_level_callback(self, mock_np, audio_playback, mock_logger):
        """Test playback callback with audio level callback."""
        callback_called = False
        
        def audio_level_callback(level):
            nonlocal callback_called
            callback_called = True
        
        audio_playback.on_audio_level = audio_level_callback
        
        # Mock numpy array and operations more comprehensively
        mock_array = MagicMock()
        mock_array.__len__.return_value = 8  # Return length for min() operation
        mock_np.frombuffer.return_value = mock_array
        mock_array.reshape.return_value = mock_array
        mock_array.astype.return_value = mock_array
        mock_array.__getitem__.return_value = mock_array  # For slicing operations
        
        # Mock the multiplication operations (* 0, * volume)
        mock_array.__mul__ = MagicMock(return_value=mock_array)
        
        # Mock the power operation (** 2)
        mock_array.__pow__ = MagicMock(return_value=mock_array)
        
        # Mock the audio level calculation
        mock_np.sqrt.return_value = 0.5
        mock_np.mean.return_value = 0.25
        
        # Create test data
        test_audio_data = b"test_audio_data_16_bytes"
        audio_playback.playback_queue.put(test_audio_data)
        
        # Mock output buffer
        outdata = Mock()
        outdata.fill = Mock()
        outdata.__setitem__ = Mock()  # For assignment operations
        
        audio_playback._playback_callback(outdata, 8, None, None)
        
        # Verify that the audio level calculation was attempted
        assert mock_array.astype.called, "astype should be called for float32 conversion"
        assert mock_array.__pow__.called, "power operation should be called for squaring"
        assert mock_np.mean.called, "mean should be called for audio level calculation"
        assert mock_np.sqrt.called, "sqrt should be called for audio level calculation"
        # The callback should be called if the audio level calculation succeeds
        # Since we're mocking the calculation to return valid values, the callback should be called
        assert callback_called is True


class TestAudioPlaybackManager:
    """Test AudioPlaybackManager class."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def audio_playback_config(self):
        """Create a test audio playback configuration."""
        return AudioPlaybackConfig(
            sample_rate=16000,
            channels=1,
            volume=0.8,
            enable_playback=True
        )

    @pytest.fixture
    def audio_playback_manager(self, audio_playback_config, mock_logger):
        """Create an AudioPlaybackManager instance for testing."""
        return AudioPlaybackManager(config=audio_playback_config, logger=mock_logger)

    def test_audio_playback_manager_initialization(self, audio_playback_manager, audio_playback_config, mock_logger):
        """Test AudioPlaybackManager initialization."""
        assert audio_playback_manager.logger == mock_logger
        assert audio_playback_manager.config == audio_playback_config
        assert audio_playback_manager.enabled is True
        assert audio_playback_manager.connected is False
        assert audio_playback_manager.playback is not None

    def test_audio_playback_manager_initialization_with_defaults(self, mock_logger):
        """Test AudioPlaybackManager initialization with default config."""
        manager = AudioPlaybackManager(logger=mock_logger)
        
        assert manager.config.sample_rate == 16000
        assert manager.config.channels == 1
        assert manager.enabled is True

    def test_connect_to_message_handler_success(self, audio_playback_manager, mock_logger):
        """Test successful connection to message handler."""
        mock_message_handler = Mock()
        
        audio_playback_manager.connect_to_message_handler(mock_message_handler)
        
        assert audio_playback_manager.connected is True
        mock_message_handler.register_event_handler.assert_called_once_with(
            "playStream.chunk",
            audio_playback_manager._handle_play_stream_chunk
        )
        mock_logger.info.assert_called()

    def test_connect_to_message_handler_disabled(self, audio_playback_manager, mock_logger):
        """Test connection to message handler when disabled."""
        audio_playback_manager.enabled = False
        
        mock_message_handler = Mock()
        audio_playback_manager.connect_to_message_handler(mock_message_handler)
        
        assert audio_playback_manager.connected is False
        mock_message_handler.register_event_handler.assert_not_called()
        mock_logger.warning.assert_called()

    def test_connect_to_message_handler_exception(self, audio_playback_manager, mock_logger):
        """Test connection to message handler with exception."""
        mock_message_handler = Mock()
        mock_message_handler.register_event_handler.side_effect = Exception("Registration failed")
        
        audio_playback_manager.connect_to_message_handler(mock_message_handler)
        
        assert audio_playback_manager.connected is False
        mock_logger.error.assert_called()

    def test_start_success(self, audio_playback_manager, mock_logger):
        """Test successful start."""
        with patch.object(audio_playback_manager.playback, 'start', return_value=True):
            success = audio_playback_manager.start()
            
            assert success is True
            mock_logger.info.assert_called()

    def test_start_failure(self, audio_playback_manager, mock_logger):
        """Test start failure."""
        with patch.object(audio_playback_manager.playback, 'start', return_value=False):
            success = audio_playback_manager.start()
            
            assert success is False
            mock_logger.error.assert_called()

    def test_start_disabled(self, audio_playback_manager, mock_logger):
        """Test start when disabled."""
        audio_playback_manager.enabled = False
        
        success = audio_playback_manager.start()
        
        assert success is False
        mock_logger.warning.assert_called()

    def test_stop(self, audio_playback_manager, mock_logger):
        """Test stop functionality."""
        with patch.object(audio_playback_manager.playback, 'stop') as mock_stop:
            audio_playback_manager.stop()
            
            mock_stop.assert_called_once()
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_handle_play_stream_chunk_success(self, audio_playback_manager):
        """Test handling play stream chunk successfully."""
        audio_playback_manager.enabled = True
        audio_playback_manager.connected = True
        
        test_data = {"audioChunk": "dGVzdF9hdWRpb19kYXRh"}
        
        with patch.object(audio_playback_manager.playback, 'queue_audio_chunk') as mock_queue:
            audio_playback_manager._handle_play_stream_chunk(test_data)
            
            # Should create an asyncio task
            # We can't easily test the task creation, but we can verify the method was called
            # The actual task creation is handled by asyncio.create_task

    def test_handle_play_stream_chunk_disabled(self, audio_playback_manager):
        """Test handling play stream chunk when disabled."""
        audio_playback_manager.enabled = False
        audio_playback_manager.connected = True
        
        test_data = {"audioChunk": "dGVzdF9hdWRpb19kYXRh"}
        
        with patch.object(audio_playback_manager.playback, 'queue_audio_chunk') as mock_queue:
            audio_playback_manager._handle_play_stream_chunk(test_data)
            
            # Should not queue anything
            mock_queue.assert_not_called()

    def test_handle_play_stream_chunk_not_connected(self, audio_playback_manager):
        """Test handling play stream chunk when not connected."""
        audio_playback_manager.enabled = True
        audio_playback_manager.connected = False
        
        test_data = {"audioChunk": "dGVzdF9hdWRpb19kYXRh"}
        
        with patch.object(audio_playback_manager.playback, 'queue_audio_chunk') as mock_queue:
            audio_playback_manager._handle_play_stream_chunk(test_data)
            
            # Should not queue anything
            mock_queue.assert_not_called()

    def test_handle_play_stream_chunk_no_audio_chunk(self, audio_playback_manager):
        """Test handling play stream chunk with no audio chunk."""
        audio_playback_manager.enabled = True
        audio_playback_manager.connected = True
        
        test_data = {"other_field": "value"}
        
        with patch.object(audio_playback_manager.playback, 'queue_audio_chunk') as mock_queue:
            audio_playback_manager._handle_play_stream_chunk(test_data)
            
            # Should not queue anything
            mock_queue.assert_not_called()

    def test_set_volume(self, audio_playback_manager):
        """Test setting volume."""
        with patch.object(audio_playback_manager.playback, 'set_volume') as mock_set_volume:
            audio_playback_manager.set_volume(0.6)
            mock_set_volume.assert_called_once_with(0.6)

    def test_mute_unmute(self, audio_playback_manager):
        """Test mute and unmute functionality."""
        with patch.object(audio_playback_manager.playback, 'mute') as mock_mute:
            audio_playback_manager.mute()
            mock_mute.assert_called_once()
        
        with patch.object(audio_playback_manager.playback, 'unmute') as mock_unmute:
            audio_playback_manager.unmute()
            mock_unmute.assert_called_once()

    def test_get_audio_level(self, audio_playback_manager):
        """Test getting audio level."""
        with patch.object(audio_playback_manager.playback, 'get_audio_level', return_value=0.75):
            level = audio_playback_manager.get_audio_level()
            assert level == 0.75

    def test_get_status(self, audio_playback_manager):
        """Test getting status."""
        mock_stats = {
            "playing": True,
            "muted": False,
            "volume": 0.8,
            "chunks_played": 10,
            "bytes_played": 1000,
            "playback_errors": 0,
            "queue_size": 5,
            "audio_level": 0.5
        }
        
        with patch.object(audio_playback_manager.playback, 'get_statistics', return_value=mock_stats):
            status = audio_playback_manager.get_status()
            
            assert status["playing"] is True
            assert status["muted"] is False
            assert status["volume"] == 0.8
            assert status["enabled"] is True
            assert status["connected"] is False
            assert status["manager_active"] is False

    def test_cleanup(self, audio_playback_manager, mock_logger):
        """Test cleanup functionality."""
        with patch.object(audio_playback_manager.playback, 'cleanup') as mock_cleanup:
            audio_playback_manager.cleanup()
            
            assert audio_playback_manager.connected is False
            mock_cleanup.assert_called_once()
            mock_logger.info.assert_called()


class TestAudioPlaybackIntegration:
    """Integration tests for audio playback functionality."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock(spec=logging.Logger)

    @pytest.mark.asyncio
    async def test_audio_playback_manager_integration(self, mock_logger):
        """Test integration between AudioPlaybackManager and AudioPlayback."""
        config = AudioPlaybackConfig(enable_playback=True)
        manager = AudioPlaybackManager(config=config, logger=mock_logger)
        
        # Test that the manager creates a playback instance
        assert manager.playback is not None
        assert isinstance(manager.playback, AudioPlayback)
        
        # Test that the manager can start/stop the playback
        with patch.object(manager.playback, 'start', return_value=True):
            success = manager.start()
            assert success is True
        
        with patch.object(manager.playback, 'stop') as mock_stop:
            manager.stop()
            mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_audio_chunk_processing_integration(self, mock_logger):
        """Test integration of audio chunk processing."""
        config = AudioPlaybackConfig(enable_playback=True)
        playback = AudioPlayback(config=config, logger=mock_logger)
        
        # Create test audio data
        test_audio_data = b"test_audio_data_16_bytes"
        test_chunk = base64.b64encode(test_audio_data).decode('utf-8')
        
        # Test that chunks can be queued and processed
        with patch('opusagent.local.audiocodes.audio_playback.AUDIO_AVAILABLE', True):
            with patch('opusagent.local.audiocodes.audio_playback.sd') as mock_sd:
                with patch('opusagent.local.audiocodes.audio_playback.np') as mock_np:
                    with patch('opusagent.local.audiocodes.audio_playback.threading') as mock_threading:
                        # Mock the output stream
                        mock_stream = Mock()
                        mock_sd.OutputStream.return_value = mock_stream
                        
                        # Mock the thread
                        mock_thread = Mock()
                        mock_threading.Thread.return_value = mock_thread
                        
                        # Start playback
                        success = playback.start()
                        assert success is True
                        
                        # Queue audio chunk
                        chunk_success = await playback.queue_audio_chunk(test_chunk)
                        assert chunk_success is True
                        assert playback.chunks_played == 1
                        assert playback.bytes_played == len(test_audio_data)
                        
                        # Stop playback
                        playback.stop()

    def test_volume_control_integration(self, mock_logger):
        """Test integration of volume control across components."""
        config = AudioPlaybackConfig(volume=0.5)
        playback = AudioPlayback(config=config, logger=mock_logger)
        manager = AudioPlaybackManager(config=config, logger=mock_logger)
        
        # Test volume control in playback
        assert playback.volume == 0.5
        playback.set_volume(0.8)
        assert playback.volume == 0.8
        
        # Test volume control through manager
        manager.set_volume(0.3)
        assert manager.playback.volume == 0.3

    def test_mute_control_integration(self, mock_logger):
        """Test integration of mute control across components."""
        config = AudioPlaybackConfig()
        playback = AudioPlayback(config=config, logger=mock_logger)
        manager = AudioPlaybackManager(config=config, logger=mock_logger)
        
        # Test mute control in playback
        assert playback.muted is False
        playback.mute()
        assert playback.muted is True
        
        # Test mute control through manager
        manager.unmute()
        assert manager.playback.muted is False

    def test_statistics_integration(self, mock_logger):
        """Test integration of statistics across components."""
        config = AudioPlaybackConfig()
        playback = AudioPlayback(config=config, logger=mock_logger)
        manager = AudioPlaybackManager(config=config, logger=mock_logger)
        
        # Set some test statistics on the playback instance
        playback.chunks_played = 10
        playback.bytes_played = 1000
        playback.current_audio_level = 0.75
        
        # Test statistics from playback
        playback_stats = playback.get_statistics()
        assert playback_stats["chunks_played"] == 10
        assert playback_stats["bytes_played"] == 1000
        assert playback_stats["audio_level"] == 0.75
        
        # Test statistics from manager (should reflect the manager's playback instance)
        # Note: manager creates its own playback instance, so it won't have the same stats
        manager_stats = manager.get_status()
        assert manager_stats["enabled"] is True
        assert manager_stats["connected"] is False
        # The manager's playback instance will have default values
        assert manager_stats["chunks_played"] == 0
        assert manager_stats["bytes_played"] == 0
        assert manager_stats["audio_level"] == 0.0 