"""
Unit tests for LiveAudioManager.

This module tests the live audio capture functionality including
device management, VAD processing, and audio streaming.
"""

import pytest
import numpy as np
import tempfile
import os
import time
import pyaudio
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from opusagent.mock.audiocodes.live_audio_manager import LiveAudioManager


class TestLiveAudioManager:
    """Test cases for LiveAudioManager."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock()

    @pytest.fixture
    def mock_audio_callback(self):
        """Create a mock audio callback."""
        return Mock()

    @pytest.fixture
    def mock_vad_callback(self):
        """Create a mock VAD callback."""
        return Mock()

    @pytest.fixture
    def live_audio_manager(self, mock_logger, mock_audio_callback, mock_vad_callback):
        """Create a LiveAudioManager instance for testing."""
        return LiveAudioManager(
            audio_callback=mock_audio_callback,
            vad_callback=mock_vad_callback,
            logger=mock_logger
        )

    @pytest.fixture
    def sample_audio_data(self):
        """Create sample audio data for testing."""
        # Generate 1 second of test audio at 16kHz
        sample_rate = 16000
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        # Generate a 440Hz sine wave
        audio = np.sin(2 * np.pi * 440 * t) * 0.5
        # Convert to 16-bit PCM
        audio_int16 = (audio * 32767).astype(np.int16)
        return audio_int16

    def test_live_audio_manager_initialization(self, live_audio_manager, mock_logger):
        """Test LiveAudioManager initialization."""
        assert live_audio_manager.logger == mock_logger
        assert live_audio_manager.audio_callback is not None
        assert live_audio_manager.vad_callback is not None
        assert live_audio_manager._running is False
        assert live_audio_manager._audio_buffer == []
        assert live_audio_manager._pyaudio is None

    def test_live_audio_manager_initialization_without_callbacks(self, mock_logger):
        """Test LiveAudioManager initialization without callbacks."""
        manager = LiveAudioManager(logger=mock_logger)
        assert manager.audio_callback is None
        assert manager.vad_callback is None

    def test_live_audio_manager_initialization_with_custom_config(self, mock_logger):
        """Test LiveAudioManager initialization with custom configuration."""
        custom_config = {
            "sample_rate": 8000,
            "channels": 2,
            "vad_threshold": 0.7,
            "buffer_size": 16000
        }
        
        manager = LiveAudioManager(logger=mock_logger, config=custom_config)
        
        assert manager._config["sample_rate"] == 8000
        assert manager._config["channels"] == 2
        assert manager._config["vad_threshold"] == 0.7
        assert manager._config["buffer_size"] == 16000

    @patch('opusagent.mock.audiocodes.live_audio_manager.pyaudio.PyAudio')
    def test_start_capture_success(self, mock_pyaudio_class, live_audio_manager, mock_logger):
        """Test successful audio capture start."""
        # Mock PyAudio instance
        mock_pyaudio = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio
        
        # Mock device info
        mock_device_info = {
            "name": "Test Microphone",
            "index": 0,
            "channels": 1,
            "sample_rate": 16000
        }
        mock_pyaudio.get_default_input_device_info.return_value = mock_device_info
        
        # Mock audio stream
        mock_stream = Mock()
        mock_pyaudio.open.return_value = mock_stream
        
        # Start capture
        result = live_audio_manager.start_capture()
        
        assert result is True
        assert live_audio_manager._running is True
        assert live_audio_manager._pyaudio == mock_pyaudio
        assert live_audio_manager._audio_stream == mock_stream
        
        # Verify PyAudio was called correctly
        mock_pyaudio.open.assert_called_once()
        call_args = mock_pyaudio.open.call_args
        assert call_args[1]["format"] == live_audio_manager._config["format"]
        assert call_args[1]["channels"] == live_audio_manager._config["channels"]
        assert call_args[1]["rate"] == live_audio_manager._config["sample_rate"]
        assert call_args[1]["input"] is True

    @patch('opusagent.mock.audiocodes.live_audio_manager.pyaudio.PyAudio')
    def test_start_capture_already_running(self, mock_pyaudio_class, live_audio_manager, mock_logger):
        """Test starting capture when already running."""
        # Set running flag
        live_audio_manager._running = True
        
        result = live_audio_manager.start_capture()
        
        assert result is True
        mock_logger.warning.assert_called_with("[LIVE_AUDIO] Capture already running")

    @patch('opusagent.mock.audiocodes.live_audio_manager.pyaudio.PyAudio')
    def test_start_capture_failure(self, mock_pyaudio_class, live_audio_manager, mock_logger):
        """Test audio capture start failure."""
        # Mock PyAudio to raise exception
        mock_pyaudio_class.side_effect = Exception("PyAudio error")
        
        result = live_audio_manager.start_capture()
        
        assert result is False
        assert live_audio_manager._running is False
        mock_logger.error.assert_called_with("[LIVE_AUDIO] Error starting capture: PyAudio error")

    def test_stop_capture(self, live_audio_manager, mock_logger):
        """Test stopping audio capture."""
        # Set up running state
        live_audio_manager._running = True
        live_audio_manager._audio_stream = Mock()
        live_audio_manager._pyaudio = Mock()
        live_audio_manager._capture_thread = Mock()
        
        live_audio_manager.stop_capture()
        
        assert live_audio_manager._running is False
        mock_logger.info.assert_called_with("[LIVE_AUDIO] Live audio capture stopped")

    def test_cleanup(self, live_audio_manager, mock_logger):
        """Test audio resource cleanup."""
        # Set up resources
        mock_stream = Mock()
        mock_pyaudio = Mock()
        live_audio_manager._audio_stream = mock_stream
        live_audio_manager._pyaudio = mock_pyaudio
        
        live_audio_manager._cleanup()
        
        # Verify cleanup calls
        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()
        mock_pyaudio.terminate.assert_called_once()
        
        # Verify resources are cleared
        assert live_audio_manager._audio_stream is None
        assert live_audio_manager._pyaudio is None

    def test_cleanup_with_errors(self, live_audio_manager, mock_logger):
        """Test cleanup with error handling."""
        # Set up resources that will raise exceptions
        mock_stream = Mock()
        mock_stream.stop_stream.side_effect = Exception("Stream error")
        mock_pyaudio = Mock()
        mock_pyaudio.terminate.side_effect = Exception("PyAudio error")
        
        live_audio_manager._audio_stream = mock_stream
        live_audio_manager._pyaudio = mock_pyaudio
        
        live_audio_manager._cleanup()
        
        # Verify error logging
        mock_logger.error.assert_any_call("[LIVE_AUDIO] Error closing audio stream: Stream error")
        mock_logger.error.assert_any_call("[LIVE_AUDIO] Error terminating PyAudio: PyAudio error")

    @patch('opusagent.mock.audiocodes.live_audio_manager.pyaudio.PyAudio')
    def test_get_default_device_info(self, mock_pyaudio_class, live_audio_manager):
        """Test getting default device information."""
        mock_pyaudio = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio
        
        mock_device_info = {
            "name": "Test Microphone",
            "index": 0,
            "maxInputChannels": 1,
            "defaultSampleRate": 16000
        }
        mock_pyaudio.get_default_input_device_info.return_value = mock_device_info
        
        live_audio_manager._pyaudio = mock_pyaudio
        result = live_audio_manager._get_default_device_info()
        
        assert result["name"] == "Test Microphone"
        assert result["index"] == 0
        assert result["channels"] == 1
        assert result["sample_rate"] == 16000

    def test_get_default_device_info_no_pyaudio(self, live_audio_manager):
        """Test getting device info when PyAudio is not initialized."""
        result = live_audio_manager._get_default_device_info()
        assert result is None

    def test_audio_callback_internal(self, live_audio_manager, mock_logger):
        """Test internal audio callback processing."""
        # Set up running state
        live_audio_manager._running = True
        live_audio_manager._config["buffer_size"] = 1000
        
        # Create test audio data
        test_audio = np.array([100, 200, 300, 400, 500], dtype=np.int16)
        test_bytes = test_audio.tobytes()
        
        # Mock the process_audio_buffer method
        with patch.object(live_audio_manager, '_process_audio_buffer') as mock_process:
            result = live_audio_manager._audio_callback_internal(
                test_bytes, 5, {}, None
            )
            
            # Verify audio data was added to buffer
            assert len(live_audio_manager._audio_buffer) == 5
            assert live_audio_manager._audio_buffer == [100, 200, 300, 400, 500]
            
            # Verify return value
            assert result == (None, pyaudio.paContinue)

    def test_audio_callback_internal_with_status(self, live_audio_manager, mock_logger):
        """Test audio callback with status warning."""
        live_audio_manager._running = True
        
        result = live_audio_manager._audio_callback_internal(
            b"test", 1, {}, "status_warning"
        )
        
        mock_logger.warning.assert_called_with("[LIVE_AUDIO] Audio callback status: status_warning")

    def test_audio_callback_internal_not_running(self, live_audio_manager):
        """Test audio callback when not running."""
        live_audio_manager._running = False
        
        result = live_audio_manager._audio_callback_internal(
            b"test", 1, {}, None
        )
        
        # Should not process audio when not running
        assert len(live_audio_manager._audio_buffer) == 0

    def test_process_audio_buffer(self, live_audio_manager, mock_audio_callback):
        """Test audio buffer processing."""
        # Add test audio data to buffer
        test_audio = np.array([100, 200, 300, 400, 500], dtype=np.int16)
        live_audio_manager._audio_buffer = test_audio.tolist()
        
        # Mock VAD processing
        with patch.object(live_audio_manager, '_process_vad') as mock_vad:
            live_audio_manager._process_audio_buffer()
            
            # Verify VAD was called
            mock_vad.assert_called_once()
            
            # Verify audio callback was called
            mock_audio_callback.assert_called_once()
            
            # Verify buffer was cleared
            assert live_audio_manager._audio_buffer == []

    def test_process_audio_buffer_empty(self, live_audio_manager, mock_audio_callback):
        """Test processing empty audio buffer."""
        live_audio_manager._audio_buffer = []
        
        live_audio_manager._process_audio_buffer()
        
        # Should not call callbacks for empty buffer
        mock_audio_callback.assert_not_called()

    def test_process_audio_buffer_vad_disabled(self, live_audio_manager, mock_audio_callback):
        """Test audio buffer processing with VAD disabled."""
        live_audio_manager._config["vad_enabled"] = False
        test_audio = np.array([100, 200, 300], dtype=np.int16)
        live_audio_manager._audio_buffer = test_audio.tolist()
        
        with patch.object(live_audio_manager, '_process_vad') as mock_vad:
            live_audio_manager._process_audio_buffer()
            
            # VAD should not be called
            mock_vad.assert_not_called()
            
            # Audio callback should still be called
            mock_audio_callback.assert_called_once()

    def test_process_vad_speech_start(self, live_audio_manager, mock_vad_callback, mock_logger):
        """Test VAD processing for speech start."""
        live_audio_manager._speech_active = False
        live_audio_manager._config["vad_threshold"] = 0.3
        
        # Create audio with high energy (speech)
        high_energy_audio = np.array([10000, 12000, 15000, 13000, 14000], dtype=np.int16)
        
        with patch('time.time', return_value=123.456):
            live_audio_manager._process_vad(high_energy_audio)
            
            # Verify speech state was updated
            assert live_audio_manager._speech_active is True
            assert live_audio_manager._speech_start_time == 123.456
            
            # Verify VAD callback was called
            mock_vad_callback.assert_called_once()
            call_args = mock_vad_callback.call_args[0][0]
            assert call_args["type"] == "userStream.speech.started"
            assert "speech_prob" in call_args["data"]

    def test_process_vad_speech_stop(self, live_audio_manager, mock_vad_callback, mock_logger):
        """Test VAD processing for speech stop."""
        live_audio_manager._speech_active = True
        live_audio_manager._speech_start_time = 100.0
        live_audio_manager._last_vad_time = 102.0
        live_audio_manager._config["vad_silence_threshold"] = 0.1
        live_audio_manager._config["min_silence_duration_ms"] = 200
        
        # Create audio with low energy (silence)
        low_energy_audio = np.array([100, 50, 75, 25, 30], dtype=np.int16)
        
        with patch('time.time', return_value=104.0):  # 2 seconds after last VAD
            live_audio_manager._process_vad(low_energy_audio)
            
            # Verify speech state was updated
            assert live_audio_manager._speech_active is False
            
            # Verify VAD callback was called
            mock_vad_callback.assert_called_once()
            call_args = mock_vad_callback.call_args[0][0]
            assert call_args["type"] == "userStream.speech.stopped"
            assert "speech_duration_ms" in call_args["data"]

    def test_process_vad_silence_too_short(self, live_audio_manager, mock_vad_callback):
        """Test VAD processing with silence duration too short."""
        live_audio_manager._speech_active = True
        live_audio_manager._last_vad_time = 100.0
        live_audio_manager._config["min_silence_duration_ms"] = 1000  # 1 second
        
        low_energy_audio = np.array([100, 50, 75], dtype=np.int16)
        
        with patch('time.time', return_value=100.5):  # Only 0.5 seconds
            live_audio_manager._process_vad(low_energy_audio)
            
            # Speech should still be active
            assert live_audio_manager._speech_active is True
            
            # No VAD callback should be called
            mock_vad_callback.assert_not_called()

    def test_process_vad_error_handling(self, live_audio_manager, mock_logger):
        """Test VAD processing error handling."""
        # Create audio that will cause an error
        problematic_audio = np.array([], dtype=np.int16)
        
        live_audio_manager._process_vad(problematic_audio)
        
        # Empty arrays are now handled gracefully, so no error should be logged
        mock_logger.error.assert_not_called()

    @patch('opusagent.mock.audiocodes.live_audio_manager.pyaudio.PyAudio')
    def test_get_available_devices(self, mock_pyaudio_class, live_audio_manager):
        """Test getting available audio devices."""
        mock_pyaudio = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio
        mock_pyaudio.get_device_count.return_value = 3
        
        # Mock device info for each device
        device_infos = [
            {"name": "Device 0", "maxInputChannels": 1, "defaultSampleRate": 16000, "index": 0},
            {"name": "Device 1", "maxInputChannels": 2, "defaultSampleRate": 44100, "index": 1},
            {"name": "Device 2", "maxInputChannels": 0, "defaultSampleRate": 48000, "index": 2},  # No input
        ]
        
        mock_pyaudio.get_device_info_by_index.side_effect = device_infos
        mock_pyaudio.get_default_input_device_info.return_value = device_infos[0]
        
        live_audio_manager._pyaudio = mock_pyaudio
        devices = live_audio_manager.get_available_devices()
        
        # Should only return devices with input channels
        assert len(devices) == 2
        assert devices[0]["name"] == "Device 0"
        assert devices[0]["channels"] == 1
        assert devices[1]["name"] == "Device 1"
        assert devices[1]["channels"] == 2

    def test_set_device_success(self, live_audio_manager, mock_logger):
        """Test successfully setting audio device."""
        # Mock available devices
        with patch.object(live_audio_manager, 'get_available_devices') as mock_get_devices:
            mock_get_devices.return_value = [
                {"index": 0, "name": "Device 0"},
                {"index": 1, "name": "Device 1"}
            ]
            
            result = live_audio_manager.set_device(1)
            
            assert result is True
            assert live_audio_manager._config["device_index"] == 1
            mock_logger.info.assert_called_with("[LIVE_AUDIO] Set device to index 1")

    def test_set_device_invalid_index(self, live_audio_manager, mock_logger):
        """Test setting invalid device index."""
        with patch.object(live_audio_manager, 'get_available_devices') as mock_get_devices:
            mock_get_devices.return_value = [{"index": 0, "name": "Device 0"}]
            
            result = live_audio_manager.set_device(99)
            
            assert result is False
            mock_logger.error.assert_called_with("[LIVE_AUDIO] Invalid device index: 99")

    def test_set_device_while_running(self, live_audio_manager, mock_logger):
        """Test setting device while capture is running."""
        live_audio_manager._running = True
        
        result = live_audio_manager.set_device(0)
        
        assert result is False
        mock_logger.warning.assert_called_with("[LIVE_AUDIO] Cannot change device while capture is running")

    def test_update_config(self, live_audio_manager, mock_logger):
        """Test updating configuration."""
        new_config = {
            "sample_rate": 8000,
            "vad_threshold": 0.7
        }
        
        live_audio_manager.update_config(new_config)
        
        assert live_audio_manager._config["sample_rate"] == 8000
        assert live_audio_manager._config["vad_threshold"] == 0.7
        mock_logger.info.assert_called_with("[LIVE_AUDIO] Configuration updated: ['sample_rate', 'vad_threshold']")

    def test_update_config_while_running(self, live_audio_manager, mock_logger):
        """Test updating configuration while running."""
        live_audio_manager._running = True
        
        live_audio_manager.update_config({"sample_rate": 8000})
        
        mock_logger.warning.assert_called_with("[LIVE_AUDIO] Cannot update config while capture is running")

    def test_get_status(self, live_audio_manager):
        """Test getting status information."""
        live_audio_manager._running = True
        live_audio_manager._speech_active = True
        live_audio_manager._audio_buffer = [1, 2, 3]
        live_audio_manager._config["device_index"] = 1
        
        status = live_audio_manager.get_status()
        
        assert status["running"] is True
        assert status["speech_active"] is True
        assert status["buffer_size"] == 3
        assert status["device_index"] == 1
        assert status["vad_enabled"] is True
        assert "config" in status

    def test_is_capturing(self, live_audio_manager):
        """Test checking if capture is running."""
        assert live_audio_manager.is_capturing() is False
        
        live_audio_manager._running = True
        assert live_audio_manager.is_capturing() is True

    def test_get_audio_level(self, live_audio_manager):
        """Test getting current audio level."""
        # Test with empty buffer
        level = live_audio_manager.get_audio_level()
        assert level == 0.0
        
        # Test with audio data
        test_audio = np.array([1000, 2000, 3000], dtype=np.int16)
        live_audio_manager._audio_buffer = test_audio.tolist()
        
        level = live_audio_manager.get_audio_level()
        assert 0.0 < level < 1.0

    def test_get_audio_level_with_error(self, live_audio_manager):
        """Test getting audio level with error handling."""
        # Create problematic buffer
        live_audio_manager._audio_buffer = ["invalid", "data"]
        
        level = live_audio_manager.get_audio_level()
        assert level == 0.0

    @patch('threading.Thread')
    def test_capture_loop(self, mock_thread_class, live_audio_manager, mock_logger):
        """Test the capture loop functionality."""
        # Mock thread
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        # Set up running state
        live_audio_manager._running = True
        live_audio_manager._audio_buffer = [1, 2, 3]
        
        # Mock process_audio_buffer and time.sleep
        with patch.object(live_audio_manager, '_process_audio_buffer') as mock_process, \
             patch('time.sleep') as mock_sleep:
            
            # Make sleep raise an exception after first call to break the loop
            mock_sleep.side_effect = Exception("Test break")
            
            # Simulate loop running - it should break after first iteration due to exception
            live_audio_manager._capture_loop()
            
            # Verify process_audio_buffer was called
            mock_process.assert_called_once()
            
            # Verify sleep was called
            mock_sleep.assert_called_once_with(live_audio_manager._config["chunk_delay"])
            
            # Verify error was logged
            mock_logger.error.assert_called_with("[LIVE_AUDIO] Error in capture loop: Test break")

    @patch('threading.Thread')
    def test_capture_loop_with_exception(self, mock_thread_class, live_audio_manager, mock_logger):
        """Test capture loop error handling."""
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        live_audio_manager._running = True
        
        # Mock process_audio_buffer to raise exception
        with patch.object(live_audio_manager, '_process_audio_buffer', side_effect=Exception("Test error")), \
             patch('time.sleep') as mock_sleep:
            
            # Make sleep raise an exception after first call to break the loop
            mock_sleep.side_effect = Exception("Test break")
            
            # Simulate loop running - it should break after first iteration due to sleep exception
            # since there's no audio buffer to process
            live_audio_manager._capture_loop()
            
            # Verify error was logged for the sleep exception (which happens first)
            mock_logger.error.assert_called_with("[LIVE_AUDIO] Error in capture loop: Test break")

    def test_integration_audio_processing_cycle(self, live_audio_manager, mock_audio_callback, mock_vad_callback):
        """Test complete audio processing cycle."""
        # Set a lower VAD threshold to ensure the test audio triggers speech detection
        live_audio_manager._config["vad_threshold"] = 0.1
        
        # Simulate audio data being added to buffer with high energy
        test_audio = np.array([15000, 16000, 17000, 18000, 19000], dtype=np.int16)
        live_audio_manager._audio_buffer = test_audio.tolist()
        
        # Process the buffer
        live_audio_manager._process_audio_buffer()
        
        # Verify callbacks were called
        mock_audio_callback.assert_called_once()
        mock_vad_callback.assert_called()
        
        # Verify buffer was cleared
        assert live_audio_manager._audio_buffer == []

    def test_vad_threshold_configuration(self, live_audio_manager, mock_vad_callback):
        """Test VAD threshold configuration."""
        # Set high threshold
        live_audio_manager._config["vad_threshold"] = 0.8
        live_audio_manager._config["vad_silence_threshold"] = 0.1
        
        # Test with moderate energy audio
        moderate_audio = np.array([5000, 6000, 7000], dtype=np.int16)
        
        with patch('time.time', return_value=100.0):
            live_audio_manager._process_vad(moderate_audio)
            
            # Should not trigger speech start with high threshold
            assert live_audio_manager._speech_active is False
            mock_vad_callback.assert_not_called()

    def test_vad_duration_filtering(self, live_audio_manager, mock_vad_callback):
        """Test VAD duration filtering."""
        live_audio_manager._config["min_speech_duration_ms"] = 1000  # 1 second
        live_audio_manager._config["min_silence_duration_ms"] = 500   # 0.5 seconds
        live_audio_manager._config["vad_threshold"] = 0.3  # Lower threshold for test audio
        
        # Start speech
        high_energy_audio = np.array([10000, 12000, 15000], dtype=np.int16)
        with patch('time.time', return_value=100.0):
            live_audio_manager._process_vad(high_energy_audio)
        
        # Stop speech after short duration
        low_energy_audio = np.array([100, 200, 300], dtype=np.int16)
        with patch('time.time', return_value=100.3):  # Only 300ms
            live_audio_manager._process_vad(low_energy_audio)
            
            # Should still be speaking due to minimum duration
            assert live_audio_manager._speech_active is True 