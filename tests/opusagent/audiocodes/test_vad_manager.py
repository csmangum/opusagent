"""
Unit tests for AudioCodes mock client VAD manager.

This module tests the VAD integration functionality for the AudioCodes mock client,
including speech detection, event emission, and state management.
"""

import pytest
import base64
import numpy as np
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from opusagent.local.audiocodes.vad_manager import VADManager
from opusagent.local.audiocodes.models import StreamState


class TestVADManager:
    """Test VADManager class."""

    @pytest.fixture
    def stream_state(self):
        """Create a test stream state."""
        return StreamState()

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock()

    @pytest.fixture
    def mock_event_callback(self):
        """Create a mock event callback."""
        return Mock()

    @pytest.fixture
    def vad_manager(self, stream_state, mock_logger, mock_event_callback):
        """Create a test VAD manager."""
        return VADManager(stream_state, mock_logger, mock_event_callback)

    @pytest.fixture
    def sample_audio_chunk(self):
        """Create a sample audio chunk for testing."""
        # Create 1 second of silence at 16kHz, 16-bit, mono
        audio_data = np.zeros(16000, dtype=np.int16)
        audio_bytes = audio_data.tobytes()
        return base64.b64encode(audio_bytes).decode('utf-8')

    @pytest.fixture
    def speech_audio_chunk(self):
        """Create a sample audio chunk with speech-like content."""
        # Create audio with some variation (simulating speech)
        audio_data = np.random.randint(-1000, 1000, 16000, dtype=np.int16)
        audio_bytes = audio_data.tobytes()
        return base64.b64encode(audio_bytes).decode('utf-8')

    def test_vad_manager_initialization(self, vad_manager, stream_state, mock_logger):
        """Test VADManager initialization."""
        assert vad_manager.logger == mock_logger
        assert vad_manager.stream_state == stream_state
        assert vad_manager.event_callback is not None
        assert vad_manager.vad is None
        assert vad_manager.enabled is False
        assert vad_manager.config == {}
        assert vad_manager._speech_start_time is None
        assert vad_manager._last_vad_result is None
        assert vad_manager._consecutive_speech_chunks == 0
        assert vad_manager._consecutive_silence_chunks == 0

    def test_vad_manager_initialization_without_callback(self, stream_state, mock_logger):
        """Test VADManager initialization without event callback."""
        vad_manager = VADManager(stream_state, mock_logger)
        assert vad_manager.event_callback is None

    def test_vad_manager_initialization_without_logger(self, stream_state, mock_event_callback):
        """Test VADManager initialization without logger."""
        vad_manager = VADManager(stream_state, event_callback=mock_event_callback)
        assert vad_manager.logger is not None

    @patch('opusagent.local.audiocodes.vad_manager.VADFactory')
    @patch('opusagent.local.audiocodes.vad_manager.load_vad_config')
    def test_initialize_success(self, mock_load_config, mock_vad_factory, vad_manager):
        """Test successful VAD initialization."""
        # Mock VAD configuration
        mock_config = {
            'backend': 'silero',
            'sample_rate': 16000,
            'threshold': 0.5,
            'silence_threshold': 0.3,
            'min_speech_duration_ms': 500,
            'min_silence_duration_ms': 300,
            'speech_start_threshold': 2,
            'speech_stop_threshold': 3,
            'device': 'cpu',
            'chunk_size': 512,
            'confidence_history_size': 5,
            'force_stop_timeout_ms': 2000,
        }
        mock_load_config.return_value = mock_config

        # Mock VAD instance
        mock_vad = Mock()
        mock_vad_factory.create_vad.return_value = mock_vad

        # Test initialization
        result = vad_manager.initialize()

        assert result is True
        assert vad_manager.enabled is True
        assert vad_manager.vad == mock_vad
        assert vad_manager.config == mock_config
        mock_vad.initialize.assert_called_once_with(mock_config)
        vad_manager.logger.info.assert_called()

    @patch('opusagent.local.audiocodes.vad_manager.VADFactory')
    @patch('opusagent.local.audiocodes.vad_manager.load_vad_config')
    def test_initialize_with_custom_config(self, mock_load_config, mock_vad_factory, vad_manager):
        """Test VAD initialization with custom configuration."""
        # Mock base configuration
        base_config = {'backend': 'silero', 'sample_rate': 16000}
        mock_load_config.return_value = base_config

        # Custom configuration
        custom_config = {'threshold': 0.7, 'silence_threshold': 0.2}

        # Mock VAD instance
        mock_vad = Mock()
        mock_vad_factory.create_vad.return_value = mock_vad

        # Test initialization with custom config
        result = vad_manager.initialize(custom_config)

        assert result is True
        # Verify custom config was merged
        expected_config = base_config.copy()
        expected_config.update(custom_config)
        mock_vad.initialize.assert_called_once_with(expected_config)

    @patch('opusagent.local.audiocodes.vad_manager.VADFactory')
    def test_initialize_vad_creation_failure(self, mock_vad_factory, vad_manager):
        """Test VAD initialization when VAD creation fails."""
        mock_vad_factory.create_vad.return_value = None

        result = vad_manager.initialize()

        assert result is False
        assert vad_manager.enabled is False
        vad_manager.logger.error.assert_called()

    @patch('opusagent.local.audiocodes.vad_manager.VADFactory')
    def test_initialize_vad_initialization_failure(self, mock_vad_factory, vad_manager):
        """Test VAD initialization when VAD initialization fails."""
        mock_vad = Mock()
        mock_vad.initialize.side_effect = Exception("VAD init failed")
        mock_vad_factory.create_vad.return_value = mock_vad

        result = vad_manager.initialize()

        assert result is False
        assert vad_manager.enabled is False
        vad_manager.logger.error.assert_called()

    def test_process_audio_chunk_disabled(self, vad_manager, sample_audio_chunk):
        """Test processing audio chunk when VAD is disabled."""
        result = vad_manager.process_audio_chunk(sample_audio_chunk)
        assert result is None

    def test_process_audio_chunk_no_vad(self, vad_manager, sample_audio_chunk):
        """Test processing audio chunk when VAD instance is None."""
        vad_manager.enabled = True
        vad_manager.vad = None

        result = vad_manager.process_audio_chunk(sample_audio_chunk)
        assert result is None

    @patch('opusagent.local.audiocodes.vad_manager.to_float32_mono')
    def test_process_audio_chunk_success(self, mock_to_float32, vad_manager, sample_audio_chunk):
        """Test successful audio chunk processing."""
        # Setup VAD
        vad_manager.enabled = True
        mock_vad = Mock()
        vad_result = {
            'speech_prob': 0.8,
            'is_speech': True,
            'speech_state': 'active'
        }
        mock_vad.process_audio.return_value = vad_result
        vad_manager.vad = mock_vad

        # Mock audio conversion
        mock_to_float32.return_value = np.zeros(16000, dtype=np.float32)

        # Test processing
        result = vad_manager.process_audio_chunk(sample_audio_chunk)

        assert result == vad_result
        mock_vad.process_audio.assert_called_once()
        mock_to_float32.assert_called_once()

    @patch('opusagent.local.audiocodes.vad_manager.to_float32_mono')
    def test_process_audio_chunk_processing_error(self, mock_to_float32, vad_manager, sample_audio_chunk):
        """Test audio chunk processing with error."""
        # Setup VAD
        vad_manager.enabled = True
        mock_vad = Mock()
        mock_vad.process_audio.side_effect = Exception("Processing error")
        vad_manager.vad = mock_vad

        # Mock audio conversion
        mock_to_float32.return_value = np.zeros(16000, dtype=np.float32)

        # Test processing
        result = vad_manager.process_audio_chunk(sample_audio_chunk)

        assert result is None
        vad_manager.logger.error.assert_called()

    def test_update_speech_state_speech_start(self, vad_manager, mock_event_callback):
        """Test speech state update when speech starts."""
        # Initialize VAD manager with test configuration
        test_config = {
            'speech_start_threshold': 2,
            'speech_stop_threshold': 3,
            'threshold': 0.5,
            'silence_threshold': 0.3
        }
        vad_manager._vad_config.update(test_config)
        
        # Setup initial state
        vad_manager.stream_state.speech_active = False
        vad_manager._consecutive_speech_chunks = 0  # Start at 0, will increment to 1 on first call

        # VAD result indicating speech
        vad_result = {
            'speech_prob': 0.8,
            'is_speech': True,
            'speech_state': 'started'
        }

        # Update speech state
        vad_manager._update_speech_state(vad_result)

        # Should not trigger speech start yet (need more consecutive chunks)
        assert vad_manager.stream_state.speech_active is False
        assert vad_manager._consecutive_speech_chunks == 1

        # Update again to reach threshold
        vad_manager._update_speech_state(vad_result)

        # Should trigger speech start
        assert vad_manager.stream_state.speech_active is True
        assert vad_manager._speech_start_time is not None
        assert vad_manager._consecutive_speech_chunks == 2
        mock_event_callback.assert_called()

    def test_update_speech_state_speech_stop(self, vad_manager, mock_event_callback):
        """Test speech state update when speech stops."""
        # Initialize VAD manager with test configuration
        test_config = {
            'speech_start_threshold': 2,
            'speech_stop_threshold': 3,
            'threshold': 0.5,
            'silence_threshold': 0.3
        }
        vad_manager._vad_config.update(test_config)
        
        # Setup speech active state
        vad_manager.stream_state.speech_active = True
        vad_manager._speech_start_time = 1000.0  # Mock start time
        vad_manager._consecutive_silence_chunks = 1  # Start at 1, will increment to 2 on first call

        # VAD result indicating silence
        vad_result = {
            'speech_prob': 0.2,
            'is_speech': False,
            'speech_state': 'stopped'
        }

        # Update speech state
        vad_manager._update_speech_state(vad_result)

        # Should not trigger speech stop yet (need more consecutive chunks)
        assert vad_manager.stream_state.speech_active is True
        assert vad_manager._consecutive_silence_chunks == 2

        # Update again to reach threshold
        vad_manager._update_speech_state(vad_result)

        # Should trigger speech stop
        assert vad_manager.stream_state.speech_active is False
        assert vad_manager._speech_start_time is None
        assert vad_manager._consecutive_silence_chunks == 3
        mock_event_callback.assert_called()

    def test_emit_speech_event(self, vad_manager, mock_event_callback):
        """Test speech event emission."""
        event_type = "userStream.speech.started"
        event_data = {
            "timestamp": 1234.5,
            "speech_prob": 0.8
        }

        vad_manager._emit_speech_event(event_type, event_data)

        mock_event_callback.assert_called_once()
        call_args = mock_event_callback.call_args[0][0]
        assert call_args["type"] == event_type
        assert call_args["data"] == event_data

    def test_emit_speech_event_no_callback(self, vad_manager):
        """Test speech event emission when no callback is set."""
        vad_manager.event_callback = None
        event_type = "userStream.speech.started"
        event_data = {"timestamp": 1234.5}

        # Should not raise exception
        vad_manager._emit_speech_event(event_type, event_data)

    def test_emit_speech_event_callback_error(self, vad_manager, mock_event_callback):
        """Test speech event emission when callback raises error."""
        mock_event_callback.side_effect = Exception("Callback error")
        event_type = "userStream.speech.started"
        event_data = {"timestamp": 1234.5}

        # Should handle error gracefully
        vad_manager._emit_speech_event(event_type, event_data)
        vad_manager.logger.error.assert_called()

    def test_simulate_speech_hypothesis(self, vad_manager, mock_event_callback):
        """Test speech hypothesis simulation."""
        vad_manager.enabled = True
        text = "Hello, how can I help you?"
        confidence = 0.9

        vad_manager.simulate_speech_hypothesis(text, confidence)

        mock_event_callback.assert_called_once()
        call_args = mock_event_callback.call_args[0][0]
        assert call_args["type"] == "userStream.speech.hypothesis"
        assert call_args["data"]["alternatives"][0]["text"] == text
        assert call_args["data"]["alternatives"][0]["confidence"] == confidence

    def test_simulate_speech_hypothesis_disabled(self, vad_manager, mock_event_callback):
        """Test speech hypothesis simulation when VAD is disabled."""
        vad_manager.enabled = False
        text = "Hello, how can I help you?"
        confidence = 0.9

        vad_manager.simulate_speech_hypothesis(text, confidence)

        mock_event_callback.assert_not_called()

    def test_simulate_speech_committed(self, vad_manager, mock_event_callback):
        """Test speech committed simulation."""
        vad_manager.enabled = True
        text = "I need help with my account"

        vad_manager.simulate_speech_committed(text)

        mock_event_callback.assert_called_once()
        call_args = mock_event_callback.call_args[0][0]
        assert call_args["type"] == "userStream.speech.committed"
        assert call_args["data"]["text"] == text
        assert vad_manager.stream_state.speech_committed is True

    def test_simulate_speech_committed_disabled(self, vad_manager, mock_event_callback):
        """Test speech committed simulation when VAD is disabled."""
        vad_manager.enabled = False
        text = "I need help with my account"

        vad_manager.simulate_speech_committed(text)

        mock_event_callback.assert_not_called()

    def test_reset(self, vad_manager):
        """Test VAD state reset."""
        # Setup some state
        vad_manager.stream_state.speech_active = True
        vad_manager.stream_state.speech_committed = True
        vad_manager.stream_state.current_hypothesis = [{"text": "test"}]
        vad_manager._speech_start_time = 1000.0
        vad_manager._last_vad_result = {"test": "data"}
        vad_manager._consecutive_speech_chunks = 5
        vad_manager._consecutive_silence_chunks = 3

        # Mock VAD instance
        mock_vad = Mock()
        vad_manager.vad = mock_vad

        # Reset
        vad_manager.reset()

        # Check state is reset
        assert vad_manager.stream_state.speech_active is False
        assert vad_manager.stream_state.speech_committed is False
        assert vad_manager.stream_state.current_hypothesis is None
        assert vad_manager._speech_start_time is None
        assert vad_manager._last_vad_result is None
        assert vad_manager._consecutive_speech_chunks == 0
        assert vad_manager._consecutive_silence_chunks == 0
        mock_vad.reset.assert_called_once()

    def test_reset_no_vad(self, vad_manager):
        """Test VAD state reset when no VAD instance exists."""
        # Setup some state
        vad_manager.stream_state.speech_active = True
        vad_manager.vad = None

        # Reset should not raise exception
        vad_manager.reset()

        assert vad_manager.stream_state.speech_active is False

    def test_cleanup(self, vad_manager):
        """Test VAD cleanup."""
        # Setup VAD instance
        mock_vad = Mock()
        vad_manager.vad = mock_vad
        vad_manager.enabled = True

        # Cleanup
        vad_manager.cleanup()

        # Check cleanup
        assert vad_manager.vad is None
        assert vad_manager.enabled is False
        mock_vad.cleanup.assert_called_once()

    def test_cleanup_no_vad(self, vad_manager):
        """Test VAD cleanup when no VAD instance exists."""
        vad_manager.vad = None
        vad_manager.enabled = True

        # Cleanup should not raise exception
        vad_manager.cleanup()

        assert vad_manager.enabled is False

    def test_get_status(self, vad_manager):
        """Test getting VAD status."""
        # Setup some state
        vad_manager.enabled = True
        vad_manager.stream_state.speech_active = True
        vad_manager.stream_state.speech_committed = False
        vad_manager._consecutive_speech_chunks = 3
        vad_manager._consecutive_silence_chunks = 1
        vad_manager._last_vad_result = {"speech_prob": 0.8}

        status = vad_manager.get_status()

        assert status["enabled"] is True
        assert status["speech_active"] is True
        assert status["speech_committed"] is False
        assert status["consecutive_speech_chunks"] == 3
        assert status["consecutive_silence_chunks"] == 1
        assert status["last_vad_result"] == {"speech_prob": 0.8}
        assert "config" in status

    def test_enable(self, vad_manager):
        """Test enabling VAD."""
        vad_manager.enabled = False
        mock_vad = Mock()
        vad_manager.vad = mock_vad

        vad_manager.enable()

        assert vad_manager.enabled is True
        vad_manager.logger.info.assert_called()

    def test_enable_no_vad(self, vad_manager):
        """Test enabling VAD when no VAD instance exists."""
        vad_manager.enabled = False
        vad_manager.vad = None

        vad_manager.enable()

        assert vad_manager.enabled is False

    def test_disable(self, vad_manager):
        """Test disabling VAD."""
        vad_manager.enabled = True

        vad_manager.disable()

        assert vad_manager.enabled is False
        vad_manager.logger.info.assert_called()

    @patch('opusagent.local.audiocodes.vad_manager.VADFactory')
    @patch('opusagent.local.audiocodes.vad_manager.load_vad_config')
    def test_integration_speech_detection_cycle(self, mock_load_config, mock_vad_factory, vad_manager, mock_event_callback):
        """Test complete speech detection cycle."""
        # Setup VAD with proper configuration
        mock_config = {
            'backend': 'silero', 
            'sample_rate': 16000,
            'speech_start_threshold': 2,
            'speech_stop_threshold': 3,
            'threshold': 0.5,
            'silence_threshold': 0.3
        }
        mock_load_config.return_value = mock_config
        mock_vad = Mock()
        mock_vad_factory.create_vad.return_value = mock_vad
        vad_manager.initialize()

        # Simulate speech start
        speech_result = {'speech_prob': 0.9, 'is_speech': True, 'speech_state': 'started'}
        mock_vad.process_audio.return_value = speech_result

        # Create valid base64-encoded audio data (1 second of silence at 16kHz, 16-bit, mono)
        import base64
        import numpy as np
        audio_data = np.zeros(16000, dtype=np.int16)  # 1 second of silence
        audio_bytes = audio_data.tobytes()
        valid_audio_chunk = base64.b64encode(audio_bytes).decode('utf-8')
        
        # Process multiple chunks to trigger speech start
        for _ in range(3):
            vad_manager.process_audio_chunk(valid_audio_chunk)

        # Check speech started
        assert vad_manager.stream_state.speech_active is True
        assert mock_event_callback.call_count >= 1

        # Simulate speech stop
        silence_result = {'speech_prob': 0.1, 'is_speech': False, 'speech_state': 'stopped'}
        mock_vad.process_audio.return_value = silence_result

        # Process multiple chunks to trigger speech stop
        for _ in range(4):
            vad_manager.process_audio_chunk(valid_audio_chunk)

        # Check speech stopped
        assert vad_manager.stream_state.speech_active is False
        assert mock_event_callback.call_count >= 2 