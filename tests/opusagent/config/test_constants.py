"""
Unit tests for the constants module.

This module tests the constants defined in opusagent.config.constants to ensure
they have the expected values and are properly documented.
"""

import pytest
from opusagent.config.constants import (
    LOGGER_NAME,
    VOICE,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_CHANNELS,
    DEFAULT_BITS_PER_SAMPLE,
    DEFAULT_AUDIO_CHUNK_SIZE,
    DEFAULT_AUDIO_CHUNK_SIZE_LARGE,
    DEFAULT_VAD_CHUNK_SIZE,
    DEFAULT_VAD_SAMPLE_RATE,
    DEFAULT_VAD_CHUNK_SIZE_16KHZ,
    DEFAULT_INTERNAL_SAMPLE_RATE,
    DEFAULT_MIN_AUDIO_BYTES,
    DEFAULT_OPENAI_SAMPLE_RATE,
    DEFAULT_TRANSCRIPTION_BACKEND,
    DEFAULT_TRANSCRIPTION_LANGUAGE,
    DEFAULT_WHISPER_MODEL_SIZE,
    DEFAULT_TRANSCRIPTION_CONFIDENCE_THRESHOLD,
    DEFAULT_TRANSCRIPTION_CHUNK_DURATION,
    SPEECH_START_THRESHOLD,
    SPEECH_STOP_THRESHOLD,
    NO_NEW_CHUNKS_THRESHOLD,
)


class TestLoggerConstants:
    """Test logger-related constants."""

    def test_logger_name(self):
        """Test that LOGGER_NAME has the expected value."""
        assert LOGGER_NAME == "opusagent"
        assert isinstance(LOGGER_NAME, str)
        assert len(LOGGER_NAME) > 0

    def test_voice_constant(self):
        """Test that VOICE has the expected value."""
        assert VOICE == "verse"
        assert isinstance(VOICE, str)
        assert len(VOICE) > 0


class TestAudioConstants:
    """Test audio-related constants."""

    def test_default_sample_rate(self):
        """Test that DEFAULT_SAMPLE_RATE has the expected value."""
        assert DEFAULT_SAMPLE_RATE == 24000
        assert isinstance(DEFAULT_SAMPLE_RATE, int)
        assert DEFAULT_SAMPLE_RATE > 0

    def test_default_channels(self):
        """Test that DEFAULT_CHANNELS has the expected value."""
        assert DEFAULT_CHANNELS == 1
        assert isinstance(DEFAULT_CHANNELS, int)
        assert DEFAULT_CHANNELS > 0

    def test_default_bits_per_sample(self):
        """Test that DEFAULT_BITS_PER_SAMPLE has the expected value."""
        assert DEFAULT_BITS_PER_SAMPLE == 16
        assert isinstance(DEFAULT_BITS_PER_SAMPLE, int)
        assert DEFAULT_BITS_PER_SAMPLE > 0

    def test_default_audio_chunk_size(self):
        """Test that DEFAULT_AUDIO_CHUNK_SIZE has the expected value."""
        assert DEFAULT_AUDIO_CHUNK_SIZE == 4800
        assert isinstance(DEFAULT_AUDIO_CHUNK_SIZE, int)
        assert DEFAULT_AUDIO_CHUNK_SIZE > 0

    def test_default_audio_chunk_size_large(self):
        """Test that DEFAULT_AUDIO_CHUNK_SIZE_LARGE has the expected value."""
        assert DEFAULT_AUDIO_CHUNK_SIZE_LARGE == 48000
        assert isinstance(DEFAULT_AUDIO_CHUNK_SIZE_LARGE, int)
        assert DEFAULT_AUDIO_CHUNK_SIZE_LARGE > 0

    def test_audio_chunk_size_relationship(self):
        """Test that audio chunk sizes have logical relationships."""
        # Large chunk size should be larger than regular chunk size
        assert DEFAULT_AUDIO_CHUNK_SIZE_LARGE > DEFAULT_AUDIO_CHUNK_SIZE
        
        # Chunk sizes should be consistent with sample rate and bit depth
        # The constants are in samples, not bytes
        expected_regular_chunk = (DEFAULT_SAMPLE_RATE * DEFAULT_CHANNELS) // 5  # 200ms
        assert abs(DEFAULT_AUDIO_CHUNK_SIZE - expected_regular_chunk) <= 1
        
        expected_large_chunk = (DEFAULT_SAMPLE_RATE * DEFAULT_CHANNELS) * 2  # 2 seconds
        assert abs(DEFAULT_AUDIO_CHUNK_SIZE_LARGE - expected_large_chunk) <= 1


class TestVADConstants:
    """Test VAD-related constants."""

    def test_default_vad_chunk_size(self):
        """Test that DEFAULT_VAD_CHUNK_SIZE has the expected value."""
        assert DEFAULT_VAD_CHUNK_SIZE == 768
        assert isinstance(DEFAULT_VAD_CHUNK_SIZE, int)
        assert DEFAULT_VAD_CHUNK_SIZE > 0

    def test_default_vad_sample_rate(self):
        """Test that DEFAULT_VAD_SAMPLE_RATE has the expected value."""
        assert DEFAULT_VAD_SAMPLE_RATE == 16000
        assert isinstance(DEFAULT_VAD_SAMPLE_RATE, int)
        assert DEFAULT_VAD_SAMPLE_RATE > 0

    def test_default_vad_chunk_size_16khz(self):
        """Test that DEFAULT_VAD_CHUNK_SIZE_16KHZ has the expected value."""
        assert DEFAULT_VAD_CHUNK_SIZE_16KHZ == 512
        assert isinstance(DEFAULT_VAD_CHUNK_SIZE_16KHZ, int)
        assert DEFAULT_VAD_CHUNK_SIZE_16KHZ > 0

    def test_vad_chunk_size_consistency(self):
        """Test that VAD chunk sizes are consistent with their sample rates."""
        # 32ms at 16kHz: 16000 * 0.032 = 512 samples
        expected_16khz_chunk = int(DEFAULT_VAD_SAMPLE_RATE * 0.032)
        assert DEFAULT_VAD_CHUNK_SIZE_16KHZ == expected_16khz_chunk
        
        # 32ms at 24kHz: 24000 * 0.032 = 768 samples
        expected_24khz_chunk = int(DEFAULT_SAMPLE_RATE * 0.032)
        assert DEFAULT_VAD_CHUNK_SIZE == expected_24khz_chunk


class TestAudioStreamHandlerConstants:
    """Test Audio Stream Handler constants."""

    def test_default_internal_sample_rate(self):
        """Test that DEFAULT_INTERNAL_SAMPLE_RATE has the expected value."""
        assert DEFAULT_INTERNAL_SAMPLE_RATE == 24000
        assert isinstance(DEFAULT_INTERNAL_SAMPLE_RATE, int)
        assert DEFAULT_INTERNAL_SAMPLE_RATE > 0

    def test_default_min_audio_bytes(self):
        """Test that DEFAULT_MIN_AUDIO_BYTES has the expected value."""
        assert DEFAULT_MIN_AUDIO_BYTES == 4800
        assert isinstance(DEFAULT_MIN_AUDIO_BYTES, int)
        assert DEFAULT_MIN_AUDIO_BYTES > 0

    def test_default_openai_sample_rate(self):
        """Test that DEFAULT_OPENAI_SAMPLE_RATE has the expected value."""
        assert DEFAULT_OPENAI_SAMPLE_RATE == 24000
        assert isinstance(DEFAULT_OPENAI_SAMPLE_RATE, int)
        assert DEFAULT_OPENAI_SAMPLE_RATE > 0

    def test_audio_stream_handler_consistency(self):
        """Test that Audio Stream Handler constants are consistent."""
        # Internal and OpenAI sample rates should match
        assert DEFAULT_INTERNAL_SAMPLE_RATE == DEFAULT_OPENAI_SAMPLE_RATE
        
        # Min audio bytes should be consistent with sample rate
        expected_min_bytes = (DEFAULT_INTERNAL_SAMPLE_RATE * DEFAULT_CHANNELS * 
                             DEFAULT_BITS_PER_SAMPLE // 8) // 10  # 100ms
        assert abs(DEFAULT_MIN_AUDIO_BYTES - expected_min_bytes) <= 1


class TestTranscriptionConstants:
    """Test transcription-related constants."""

    def test_default_transcription_backend(self):
        """Test that DEFAULT_TRANSCRIPTION_BACKEND has the expected value."""
        assert DEFAULT_TRANSCRIPTION_BACKEND == "pocketsphinx"
        assert isinstance(DEFAULT_TRANSCRIPTION_BACKEND, str)
        assert len(DEFAULT_TRANSCRIPTION_BACKEND) > 0

    def test_default_transcription_language(self):
        """Test that DEFAULT_TRANSCRIPTION_LANGUAGE has the expected value."""
        assert DEFAULT_TRANSCRIPTION_LANGUAGE == "en"
        assert isinstance(DEFAULT_TRANSCRIPTION_LANGUAGE, str)
        assert len(DEFAULT_TRANSCRIPTION_LANGUAGE) > 0

    def test_default_whisper_model_size(self):
        """Test that DEFAULT_WHISPER_MODEL_SIZE has the expected value."""
        assert DEFAULT_WHISPER_MODEL_SIZE == "base"
        assert isinstance(DEFAULT_WHISPER_MODEL_SIZE, str)
        assert len(DEFAULT_WHISPER_MODEL_SIZE) > 0

    def test_default_transcription_confidence_threshold(self):
        """Test that DEFAULT_TRANSCRIPTION_CONFIDENCE_THRESHOLD has the expected value."""
        assert DEFAULT_TRANSCRIPTION_CONFIDENCE_THRESHOLD == 0.5
        assert isinstance(DEFAULT_TRANSCRIPTION_CONFIDENCE_THRESHOLD, float)
        assert 0.0 <= DEFAULT_TRANSCRIPTION_CONFIDENCE_THRESHOLD <= 1.0

    def test_default_transcription_chunk_duration(self):
        """Test that DEFAULT_TRANSCRIPTION_CHUNK_DURATION has the expected value."""
        assert DEFAULT_TRANSCRIPTION_CHUNK_DURATION == 1.0
        assert isinstance(DEFAULT_TRANSCRIPTION_CHUNK_DURATION, float)
        assert DEFAULT_TRANSCRIPTION_CHUNK_DURATION > 0.0


class TestSpeechDetectionConstants:
    """Test speech detection threshold constants."""

    def test_speech_start_threshold(self):
        """Test that SPEECH_START_THRESHOLD has the expected value."""
        assert SPEECH_START_THRESHOLD == 2
        assert isinstance(SPEECH_START_THRESHOLD, int)
        assert SPEECH_START_THRESHOLD > 0

    def test_speech_stop_threshold(self):
        """Test that SPEECH_STOP_THRESHOLD has the expected value."""
        assert SPEECH_STOP_THRESHOLD == 3
        assert isinstance(SPEECH_STOP_THRESHOLD, int)
        assert SPEECH_STOP_THRESHOLD > 0

    def test_speech_threshold_relationship(self):
        """Test that speech thresholds have logical relationships."""
        # Stop threshold should be greater than or equal to start threshold
        assert SPEECH_STOP_THRESHOLD >= SPEECH_START_THRESHOLD


class TestTimeoutConstants:
    """Test timeout-related constants."""

    def test_no_new_chunks_threshold(self):
        """Test that NO_NEW_CHUNKS_THRESHOLD has the expected value."""
        assert NO_NEW_CHUNKS_THRESHOLD == 20
        assert isinstance(NO_NEW_CHUNKS_THRESHOLD, int)
        assert NO_NEW_CHUNKS_THRESHOLD > 0

    def test_no_new_chunks_threshold_calculation(self):
        """Test that NO_NEW_CHUNKS_THRESHOLD is calculated correctly."""
        # Should be 2.0 seconds / 0.1 seconds = 20 iterations
        expected_threshold = int(2.0 / 0.1)
        assert NO_NEW_CHUNKS_THRESHOLD == expected_threshold


class TestConstantsIntegration:
    """Integration tests for constants."""

    def test_all_constants_are_defined(self):
        """Test that all expected constants are defined and accessible."""
        constants_to_check = [
            'LOGGER_NAME', 'VOICE', 'DEFAULT_SAMPLE_RATE', 'DEFAULT_CHANNELS',
            'DEFAULT_BITS_PER_SAMPLE', 'DEFAULT_AUDIO_CHUNK_SIZE',
            'DEFAULT_AUDIO_CHUNK_SIZE_LARGE', 'DEFAULT_VAD_CHUNK_SIZE',
            'DEFAULT_VAD_SAMPLE_RATE', 'DEFAULT_VAD_CHUNK_SIZE_16KHZ',
            'DEFAULT_INTERNAL_SAMPLE_RATE', 'DEFAULT_MIN_AUDIO_BYTES',
            'DEFAULT_OPENAI_SAMPLE_RATE', 'DEFAULT_TRANSCRIPTION_BACKEND',
            'DEFAULT_TRANSCRIPTION_LANGUAGE', 'DEFAULT_WHISPER_MODEL_SIZE',
            'DEFAULT_TRANSCRIPTION_CONFIDENCE_THRESHOLD',
            'DEFAULT_TRANSCRIPTION_CHUNK_DURATION', 'SPEECH_START_THRESHOLD',
            'SPEECH_STOP_THRESHOLD', 'NO_NEW_CHUNKS_THRESHOLD'
        ]
        
        for constant_name in constants_to_check:
            assert hasattr(__import__('opusagent.config.constants', fromlist=[constant_name]), constant_name)

    def test_audio_configuration_consistency(self):
        """Test that audio-related constants form a consistent configuration."""
        # Sample rates should be positive
        assert DEFAULT_SAMPLE_RATE > 0
        assert DEFAULT_VAD_SAMPLE_RATE > 0
        assert DEFAULT_INTERNAL_SAMPLE_RATE > 0
        assert DEFAULT_OPENAI_SAMPLE_RATE > 0
        
        # Channels should be positive
        assert DEFAULT_CHANNELS > 0
        
        # Bit depth should be positive and reasonable
        assert DEFAULT_BITS_PER_SAMPLE > 0
        assert DEFAULT_BITS_PER_SAMPLE <= 32  # Reasonable upper limit
        
        # All chunk sizes should be positive
        assert DEFAULT_AUDIO_CHUNK_SIZE > 0
        assert DEFAULT_AUDIO_CHUNK_SIZE_LARGE > 0
        assert DEFAULT_VAD_CHUNK_SIZE > 0
        assert DEFAULT_VAD_CHUNK_SIZE_16KHZ > 0
        assert DEFAULT_MIN_AUDIO_BYTES > 0

    def test_transcription_configuration_consistency(self):
        """Test that transcription-related constants form a consistent configuration."""
        # Backend should be a valid string
        assert isinstance(DEFAULT_TRANSCRIPTION_BACKEND, str)
        assert len(DEFAULT_TRANSCRIPTION_BACKEND) > 0
        
        # Language should be a valid string
        assert isinstance(DEFAULT_TRANSCRIPTION_LANGUAGE, str)
        assert len(DEFAULT_TRANSCRIPTION_LANGUAGE) > 0
        
        # Model size should be a valid string
        assert isinstance(DEFAULT_WHISPER_MODEL_SIZE, str)
        assert len(DEFAULT_WHISPER_MODEL_SIZE) > 0
        
        # Confidence threshold should be in valid range
        assert 0.0 <= DEFAULT_TRANSCRIPTION_CONFIDENCE_THRESHOLD <= 1.0
        
        # Chunk duration should be positive
        assert DEFAULT_TRANSCRIPTION_CHUNK_DURATION > 0.0

    def test_speech_detection_configuration_consistency(self):
        """Test that speech detection constants form a consistent configuration."""
        # Thresholds should be positive integers
        assert isinstance(SPEECH_START_THRESHOLD, int)
        assert isinstance(SPEECH_STOP_THRESHOLD, int)
        assert SPEECH_START_THRESHOLD > 0
        assert SPEECH_STOP_THRESHOLD > 0
        
        # Stop threshold should be >= start threshold
        assert SPEECH_STOP_THRESHOLD >= SPEECH_START_THRESHOLD

    def test_timeout_configuration_consistency(self):
        """Test that timeout constants form a consistent configuration."""
        # Threshold should be a positive integer
        assert isinstance(NO_NEW_CHUNKS_THRESHOLD, int)
        assert NO_NEW_CHUNKS_THRESHOLD > 0
        
        # Should represent a reasonable timeout (2 seconds)
        assert NO_NEW_CHUNKS_THRESHOLD == 20  # 2.0 / 0.1
