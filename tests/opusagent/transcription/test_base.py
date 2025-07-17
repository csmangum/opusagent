"""
Unit tests for base transcriber functionality.
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from opusagent.mock.transcription.base import BaseTranscriber
from opusagent.mock.transcription.models import TranscriptionConfig, TranscriptionResult


class ConcreteTranscriber(BaseTranscriber):
    """Concrete implementation for testing BaseTranscriber."""
    
    async def initialize(self) -> bool:
        self._initialized = True
        return True
    
    async def transcribe_chunk(self, audio_data: bytes) -> TranscriptionResult:
        return TranscriptionResult(text="test")
    
    async def finalize(self) -> TranscriptionResult:
        return TranscriptionResult(text="final")
    
    async def cleanup(self) -> None:
        self._initialized = False


class TestBaseTranscriber:
    """Test BaseTranscriber functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = TranscriptionConfig()
        self.transcriber = ConcreteTranscriber(self.config)

    def test_initialization(self):
        """Test transcriber initialization."""
        assert self.transcriber.config == self.config
        assert hasattr(self.transcriber, 'logger')
        assert self.transcriber._initialized == False
        assert self.transcriber._audio_buffer == []
        assert self.transcriber._session_active == False

    def test_session_management(self):
        """Test session start and end."""
        assert self.transcriber._session_active == False
        
        self.transcriber.start_session()
        assert self.transcriber._session_active == True
        assert self.transcriber._audio_buffer == []
        
        # Add some data to buffer
        self.transcriber._audio_buffer = [1, 2, 3]
        
        self.transcriber.end_session()
        assert self.transcriber._session_active == False
        # Buffer should not be cleared by end_session
        assert self.transcriber._audio_buffer == [1, 2, 3]

    def test_reset_session(self):
        """Test session reset."""
        # Set up some state
        self.transcriber._session_active = True
        self.transcriber._audio_buffer = [1, 2, 3]
        
        self.transcriber.reset_session()
        
        assert self.transcriber._session_active == False
        assert self.transcriber._audio_buffer == []

    def test_convert_audio_for_processing_valid(self):
        """Test audio conversion with valid data."""
        # Create 16-bit PCM audio data
        audio_int16 = np.array([0, 16384, -16384, 32767, -32768], dtype=np.int16)
        audio_bytes = audio_int16.tobytes()
        
        result = self.transcriber._convert_audio_for_processing(audio_bytes)
        
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert len(result) == 5
        
        # Check normalization
        expected = audio_int16.astype(np.float32) / 32768.0
        np.testing.assert_array_almost_equal(result, expected, decimal=5)

    def test_convert_audio_for_processing_empty(self):
        """Test audio conversion with empty data."""
        result = self.transcriber._convert_audio_for_processing(b"")
        
        assert isinstance(result, np.ndarray)
        assert len(result) == 0
        assert result.dtype == np.float32

    def test_convert_audio_for_processing_invalid(self):
        """Test audio conversion with invalid data."""
        # Odd number of bytes (invalid for 16-bit)
        invalid_bytes = b"abc"
        
        result = self.transcriber._convert_audio_for_processing(invalid_bytes)
        
        # Should handle gracefully and return empty array
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32

    def test_resample_audio_same_rate(self):
        """Test audio resampling with same input and output rates."""
        # Create test audio data
        audio_int16 = np.array([0, 16384, -16384, 32767], dtype=np.int16)
        audio_bytes = audio_int16.tobytes()
        
        result = self.transcriber._resample_audio_for_pocketsphinx(
            audio_bytes, 16000, 16000
        )
        
        # Should return original data
        assert result == audio_bytes

    def test_resample_audio_downsample(self):
        """Test audio downsampling."""
        # Create test audio data at 48kHz
        duration = 0.1  # 100ms
        sample_rate = 48000
        samples = int(duration * sample_rate)
        audio_int16 = np.random.randint(-1000, 1000, samples, dtype=np.int16)
        audio_bytes = audio_int16.tobytes()
        
        result = self.transcriber._resample_audio_for_pocketsphinx(
            audio_bytes, 48000, 16000
        )
        
        # Check that result is different and properly sized
        assert result != audio_bytes
        result_array = np.frombuffer(result, dtype=np.int16)
        expected_length = int(len(audio_int16) * 16000 / 48000)
        assert len(result_array) == expected_length

    def test_resample_audio_upsample(self):
        """Test audio upsampling."""
        # Create test audio data at 8kHz
        audio_int16 = np.array([0, 16384, -16384, 32767], dtype=np.int16)
        audio_bytes = audio_int16.tobytes()
        
        result = self.transcriber._resample_audio_for_pocketsphinx(
            audio_bytes, 8000, 16000
        )
        
        # Check that result is upsampled
        result_array = np.frombuffer(result, dtype=np.int16)
        expected_length = len(audio_int16) * 2  # 2x upsampling
        assert len(result_array) == expected_length

    def test_resample_audio_error_handling(self):
        """Test audio resampling error handling."""
        # Test with invalid input
        with patch.object(self.transcriber.logger, 'error') as mock_logger:
            result = self.transcriber._resample_audio_for_pocketsphinx(b"invalid", 16000, 16000)
            # Should return original data on error
            assert result == b"invalid"
            mock_logger.assert_called_once()

    def test_apply_audio_preprocessing_none(self):
        """Test audio preprocessing with 'none' type."""
        audio_array = np.array([0.1, -0.5, 0.8, -0.2], dtype=np.float32)
        
        result = self.transcriber._apply_audio_preprocessing(audio_array, "none")
        
        np.testing.assert_array_equal(result, audio_array)

    def test_apply_audio_preprocessing_normalize(self):
        """Test audio preprocessing with 'normalize' type."""
        audio_array = np.array([0.1, -0.5, 0.8, -0.2], dtype=np.float32)
        
        result = self.transcriber._apply_audio_preprocessing(audio_array, "normalize")
        
        # Should normalize to max amplitude of 1.0
        max_val = np.max(np.abs(audio_array))
        expected = audio_array / max_val
        np.testing.assert_array_almost_equal(result, expected)

    def test_apply_audio_preprocessing_normalize_empty(self):
        """Test audio preprocessing normalize with empty array."""
        audio_array = np.array([], dtype=np.float32)
        
        result = self.transcriber._apply_audio_preprocessing(audio_array, "normalize")
        
        np.testing.assert_array_equal(result, audio_array)

    def test_apply_audio_preprocessing_normalize_zero(self):
        """Test audio preprocessing normalize with all zeros."""
        audio_array = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        
        result = self.transcriber._apply_audio_preprocessing(audio_array, "normalize")
        
        # Should return original array if max is 0
        np.testing.assert_array_equal(result, audio_array)

    def test_apply_audio_preprocessing_amplify(self):
        """Test audio preprocessing with 'amplify' type."""
        audio_array = np.array([0.1, -0.2, 0.3, -0.1], dtype=np.float32)
        
        result = self.transcriber._apply_audio_preprocessing(audio_array, "amplify")
        
        # Should amplify if max is below 0.5
        max_val = np.max(np.abs(audio_array))
        if max_val > 0 and max_val < 0.5:
            expected = audio_array * (0.5 / max_val)
            np.testing.assert_array_almost_equal(result, expected)
        else:
            np.testing.assert_array_equal(result, audio_array)

    def test_apply_audio_preprocessing_silence_trim(self):
        """Test audio preprocessing with 'silence_trim' type."""
        # Create audio with silence at beginning and end
        audio_array = np.array([0.001, 0.001, 0.5, -0.3, 0.2, 0.001, 0.001], dtype=np.float32)
        
        result = self.transcriber._apply_audio_preprocessing(audio_array, "silence_trim")
        
        # Should trim silence (below 0.01 threshold)
        expected = np.array([0.5, -0.3, 0.2], dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)

    def test_apply_audio_preprocessing_silence_trim_all_silent(self):
        """Test silence trimming with all silent audio."""
        audio_array = np.array([0.001, 0.005, 0.002], dtype=np.float32)
        
        result = self.transcriber._apply_audio_preprocessing(audio_array, "silence_trim")
        
        # Should return original if all is silent
        np.testing.assert_array_equal(result, audio_array)

    def test_apply_audio_preprocessing_silence_trim_empty(self):
        """Test silence trimming with empty array."""
        audio_array = np.array([], dtype=np.float32)
        
        result = self.transcriber._apply_audio_preprocessing(audio_array, "silence_trim")
        
        np.testing.assert_array_equal(result, audio_array)

    def test_apply_audio_preprocessing_noise_reduction(self):
        """Test audio preprocessing with 'noise_reduction' type."""
        audio_array = np.array([0.1, -0.5, 0.8, -0.2], dtype=np.float32)
        
        with patch.object(self.transcriber.logger, 'warning') as mock_logger:
            result = self.transcriber._apply_audio_preprocessing(audio_array, "noise_reduction")
            
            # Should warn about reduced accuracy
            mock_logger.assert_called_once()
            # Currently just returns original array
            np.testing.assert_array_equal(result, audio_array)

    def test_apply_audio_preprocessing_unknown(self):
        """Test audio preprocessing with unknown type."""
        audio_array = np.array([0.1, -0.5, 0.8, -0.2], dtype=np.float32)
        
        with patch.object(self.transcriber.logger, 'warning') as mock_logger:
            result = self.transcriber._apply_audio_preprocessing(audio_array, "unknown")
            
            # Should warn and return original
            mock_logger.assert_called_once()
            np.testing.assert_array_equal(result, audio_array)

    def test_apply_audio_preprocessing_error_handling(self):
        """Test audio preprocessing error handling."""
        audio_array = np.array([0.1, -0.5, 0.8, -0.2], dtype=np.float32)
        
        # Mock an error in processing
        with patch('numpy.max', side_effect=Exception("Test error")):
            with patch.object(self.transcriber.logger, 'error') as mock_logger:
                result = self.transcriber._apply_audio_preprocessing(audio_array, "normalize")
                
                # Should handle error and return original
                mock_logger.assert_called_once()
                np.testing.assert_array_equal(result, audio_array)

    def test_abstract_methods_implemented(self):
        """Test that concrete class implements abstract methods."""
        # These should not raise NotImplementedError
        assert hasattr(self.transcriber, 'initialize')
        assert hasattr(self.transcriber, 'transcribe_chunk')
        assert hasattr(self.transcriber, 'finalize')
        assert hasattr(self.transcriber, 'cleanup')

    def test_logger_configuration(self):
        """Test logger is properly configured."""
        assert hasattr(self.transcriber, 'logger')
        assert self.transcriber.logger.name.endswith('.ConcreteTranscriber')

    def test_config_storage(self):
        """Test that config is properly stored."""
        custom_config = TranscriptionConfig(
            backend="whisper",
            chunk_duration=2.0,
            sample_rate=48000
        )
        transcriber = ConcreteTranscriber(custom_config)
        
        assert transcriber.config == custom_config
        assert transcriber.config.backend == "whisper"
        assert transcriber.config.chunk_duration == 2.0
        assert transcriber.config.sample_rate == 48000 