"""
Tests for the transcription module.

This module contains tests for the local audio transcription functionality
in the LocalRealtimeClient mock system.
"""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from opusagent.mock.realtime.transcription import (
    BaseTranscriber,
    PocketSphinxTranscriber,
    TranscriptionConfig,
    TranscriptionFactory,
    TranscriptionResult,
    WhisperTranscriber,
    load_transcription_config,
)


class TestTranscriptionConfig:
    """Test TranscriptionConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TranscriptionConfig()
        assert config.backend == "pocketsphinx"
        assert config.language == "en"
        assert config.model_size == "base"
        assert config.chunk_duration == 1.0
        assert config.confidence_threshold == 0.5
        assert config.sample_rate == 16000
        assert config.enable_vad == True
        assert config.device == "cpu"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = TranscriptionConfig(
            backend="whisper",
            language="es",
            model_size="large",
            chunk_duration=2.0,
            confidence_threshold=0.8,
            sample_rate=24000,
            enable_vad=False,
            device="cuda"
        )
        assert config.backend == "whisper"
        assert config.language == "es"
        assert config.model_size == "large"
        assert config.chunk_duration == 2.0
        assert config.confidence_threshold == 0.8
        assert config.sample_rate == 24000
        assert config.enable_vad == False
        assert config.device == "cuda"


class TestTranscriptionResult:
    """Test TranscriptionResult class."""

    def test_default_result(self):
        """Test default result values."""
        result = TranscriptionResult(text="hello world")
        assert result.text == "hello world"
        assert result.confidence == 0.0
        assert result.is_final == False
        assert result.segments is None
        assert result.processing_time == 0.0
        assert result.error is None

    def test_custom_result(self):
        """Test custom result values."""
        segments = [{"word": "hello", "start": 0.0, "end": 0.5}]
        result = TranscriptionResult(
            text="hello world",
            confidence=0.85,
            is_final=True,
            segments=segments,
            processing_time=0.123,
            error="test error"
        )
        assert result.text == "hello world"
        assert result.confidence == 0.85
        assert result.is_final == True
        assert result.segments == segments
        assert result.processing_time == 0.123
        assert result.error == "test error"


class TestTranscriptionFactory:
    """Test TranscriptionFactory class."""

    def test_create_pocketsphinx_transcriber(self):
        """Test creating PocketSphinx transcriber."""
        config = TranscriptionConfig(backend="pocketsphinx")
        transcriber = TranscriptionFactory.create_transcriber(config)
        assert isinstance(transcriber, PocketSphinxTranscriber)

    def test_create_whisper_transcriber(self):
        """Test creating Whisper transcriber."""
        config = TranscriptionConfig(backend="whisper")
        transcriber = TranscriptionFactory.create_transcriber(config)
        assert isinstance(transcriber, WhisperTranscriber)

    def test_create_transcriber_with_dict_config(self):
        """Test creating transcriber with dictionary configuration."""
        config_dict = {"backend": "pocketsphinx", "language": "en"}
        transcriber = TranscriptionFactory.create_transcriber(config_dict)
        assert isinstance(transcriber, PocketSphinxTranscriber)

    def test_unsupported_backend(self):
        """Test creating transcriber with unsupported backend."""
        config = TranscriptionConfig(backend="unsupported")
        with pytest.raises(ValueError, match="Unsupported transcription backend"):
            TranscriptionFactory.create_transcriber(config)

    def test_get_available_backends(self):
        """Test getting available backends."""
        backends = TranscriptionFactory.get_available_backends()
        assert isinstance(backends, list)
        # The actual available backends depend on installed dependencies


class TestLoadTranscriptionConfig:
    """Test load_transcription_config function."""

    def test_load_default_config(self):
        """Test loading default configuration."""
        config = load_transcription_config()
        assert isinstance(config, TranscriptionConfig)
        assert config.backend == "pocketsphinx"  # Default from constants

    @patch.dict(os.environ, {
        "TRANSCRIPTION_BACKEND": "whisper",
        "TRANSCRIPTION_LANGUAGE": "es",
        "WHISPER_MODEL_SIZE": "large",
        "TRANSCRIPTION_CHUNK_DURATION": "2.0",
        "TRANSCRIPTION_CONFIDENCE_THRESHOLD": "0.8",
        "TRANSCRIPTION_SAMPLE_RATE": "24000",
        "TRANSCRIPTION_ENABLE_VAD": "false",
        "WHISPER_DEVICE": "cuda"
    })
    def test_load_config_from_env(self):
        """Test loading configuration from environment variables."""
        config = load_transcription_config()
        assert config.backend == "whisper"
        assert config.language == "es"
        assert config.model_size == "large"
        assert config.chunk_duration == 2.0
        assert config.confidence_threshold == 0.8
        assert config.sample_rate == 24000
        assert config.enable_vad == False
        assert config.device == "cuda"


class MockTranscriber(BaseTranscriber):
    """Mock transcriber for testing base functionality."""

    def __init__(self, config: TranscriptionConfig):
        super().__init__(config)
        self.initialized = False
        self.transcribe_calls = []
        self.finalize_calls = []
        self.cleanup_calls = []

    async def initialize(self) -> bool:
        self.initialized = True
        self._initialized = True
        return True

    async def transcribe_chunk(self, audio_data: bytes) -> TranscriptionResult:
        self.transcribe_calls.append(audio_data)
        return TranscriptionResult(text="mock transcription", confidence=0.9)

    async def finalize(self) -> TranscriptionResult:
        self.finalize_calls.append(True)
        return TranscriptionResult(text="final mock transcription", confidence=0.95, is_final=True)

    async def cleanup(self) -> None:
        self.cleanup_calls.append(True)
        self._initialized = False


class TestBaseTranscriber:
    """Test BaseTranscriber functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return TranscriptionConfig()

    @pytest.fixture
    def transcriber(self, config):
        """Create mock transcriber."""
        return MockTranscriber(config)

    def test_initialization(self, transcriber):
        """Test transcriber initialization."""
        assert not transcriber._initialized
        assert not transcriber._session_active
        assert len(transcriber._audio_buffer) == 0

    @pytest.mark.asyncio
    async def test_initialize(self, transcriber):
        """Test transcriber initialize method."""
        result = await transcriber.initialize()
        assert result == True
        assert transcriber.initialized == True
        assert transcriber._initialized == True

    def test_start_session(self, transcriber):
        """Test starting transcription session."""
        transcriber._audio_buffer = [b"test"]
        transcriber.start_session()
        assert transcriber._session_active == True
        assert len(transcriber._audio_buffer) == 0

    def test_end_session(self, transcriber):
        """Test ending transcription session."""
        transcriber._session_active = True
        transcriber.end_session()
        assert transcriber._session_active == False

    @pytest.mark.asyncio
    async def test_transcribe_chunk(self, transcriber):
        """Test transcribing audio chunk."""
        audio_data = b"test audio data"
        result = await transcriber.transcribe_chunk(audio_data)
        assert result.text == "mock transcription"
        assert result.confidence == 0.9
        assert len(transcriber.transcribe_calls) == 1
        assert transcriber.transcribe_calls[0] == audio_data

    @pytest.mark.asyncio
    async def test_finalize(self, transcriber):
        """Test finalizing transcription."""
        result = await transcriber.finalize()
        assert result.text == "final mock transcription"
        assert result.confidence == 0.95
        assert result.is_final == True
        assert len(transcriber.finalize_calls) == 1

    @pytest.mark.asyncio
    async def test_cleanup(self, transcriber):
        """Test cleaning up transcriber."""
        transcriber._initialized = True
        await transcriber.cleanup()
        assert len(transcriber.cleanup_calls) == 1
        assert transcriber._initialized == False

    def test_convert_audio_for_processing(self, transcriber):
        """Test audio conversion for processing."""
        # Test with valid 16-bit PCM data
        import numpy as np
        audio_int16 = np.array([1000, -1000, 2000, -2000], dtype=np.int16)
        audio_bytes = audio_int16.tobytes()
        
        result = transcriber._convert_audio_for_processing(audio_bytes)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert len(result) == 4
        
        # Test with empty data
        empty_result = transcriber._convert_audio_for_processing(b"")
        assert len(empty_result) == 0


class TestPocketSphinxTranscriber:
    """Test PocketSphinxTranscriber functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return TranscriptionConfig(backend="pocketsphinx")

    @pytest.fixture
    def transcriber(self, config):
        """Create PocketSphinx transcriber."""
        return PocketSphinxTranscriber(config)

    def test_initialization(self, transcriber):
        """Test PocketSphinx transcriber initialization."""
        assert transcriber._decoder is None
        assert transcriber._accumulated_text == ""

    @pytest.mark.asyncio
    async def test_initialize_without_pocketsphinx(self, transcriber):
        """Test initialization when PocketSphinx is not available."""
        with patch.dict('sys.modules', {'pocketsphinx': None}):
            result = await transcriber.initialize()
            assert result == False
            assert not transcriber._initialized

    @pytest.mark.asyncio
    async def test_transcribe_chunk_not_initialized(self, transcriber):
        """Test transcribing chunk when not initialized."""
        result = await transcriber.transcribe_chunk(b"test")
        assert result.text == ""
        assert result.error == "Transcriber not initialized"

    @pytest.mark.asyncio
    async def test_finalize_not_initialized(self, transcriber):
        """Test finalizing when not initialized."""
        result = await transcriber.finalize()
        assert result.text == ""
        assert result.error == "Transcriber not initialized"

    @pytest.mark.asyncio
    async def test_cleanup(self, transcriber):
        """Test cleaning up PocketSphinx transcriber."""
        # Mock decoder
        mock_decoder = MagicMock()
        transcriber._decoder = mock_decoder
        transcriber._initialized = True
        
        await transcriber.cleanup()
        
        mock_decoder.end_utt.assert_called_once()
        assert transcriber._decoder is None
        assert not transcriber._initialized


class TestWhisperTranscriber:
    """Test WhisperTranscriber functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return TranscriptionConfig(backend="whisper")

    @pytest.fixture
    def transcriber(self, config):
        """Create Whisper transcriber."""
        return WhisperTranscriber(config)

    def test_initialization(self, transcriber):
        """Test Whisper transcriber initialization."""
        assert transcriber._model is None
        assert transcriber._temp_dir is None
        assert transcriber._accumulated_text == ""

    @pytest.mark.asyncio
    async def test_initialize_without_whisper(self, transcriber):
        """Test initialization when Whisper is not available."""
        with patch('builtins.__import__', side_effect=ImportError("No module named 'whisper'")):
            result = await transcriber.initialize()
            assert result == False
            assert not transcriber._initialized

    @pytest.mark.asyncio
    async def test_transcribe_chunk_not_initialized(self, transcriber):
        """Test transcribing chunk when not initialized."""
        result = await transcriber.transcribe_chunk(b"test")
        assert result.text == ""
        assert result.error == "Transcriber not initialized"

    @pytest.mark.asyncio
    async def test_finalize_not_initialized(self, transcriber):
        """Test finalizing when not initialized."""
        result = await transcriber.finalize()
        assert result.text == ""
        assert result.error == "Transcriber not initialized"

    @pytest.mark.asyncio
    async def test_cleanup(self, transcriber):
        """Test cleaning up Whisper transcriber."""
        # Create temporary directory
        transcriber._temp_dir = tempfile.mkdtemp()
        transcriber._initialized = True
        
        await transcriber.cleanup()
        
        # Check that temp directory is cleaned up
        assert not os.path.exists(transcriber._temp_dir)
        assert transcriber._model is None
        assert not transcriber._initialized


# Integration tests would go here, but they require actual
# PocketSphinx or Whisper installations, so they're marked as skipif

@pytest.mark.skipif(
    not TranscriptionFactory.get_available_backends(),
    reason="No transcription backends available"
)
class TestIntegration:
    """Integration tests for transcription functionality."""

    @pytest.mark.asyncio
    async def test_end_to_end_transcription(self):
        """Test end-to-end transcription with available backend."""
        available_backends = TranscriptionFactory.get_available_backends()
        if not available_backends:
            pytest.skip("No transcription backends available")
        
        backend = available_backends[0]
        config = TranscriptionConfig(backend=backend)
        transcriber = TranscriptionFactory.create_transcriber(config)
        
        # Initialize transcriber
        initialized = await transcriber.initialize()
        if not initialized:
            pytest.skip(f"Failed to initialize {backend} transcriber")
        
        try:
            # Start session
            transcriber.start_session()
            
            # Generate some test audio (silence)
            import numpy as np
            test_audio = np.zeros(16000, dtype=np.int16)  # 1 second of silence
            audio_bytes = test_audio.tobytes()
            
            # Transcribe chunk
            result = await transcriber.transcribe_chunk(audio_bytes)
            assert isinstance(result, TranscriptionResult)
            
            # Finalize
            final_result = await transcriber.finalize()
            assert isinstance(final_result, TranscriptionResult)
            assert final_result.is_final == True
            
            # End session
            transcriber.end_session()
            
        finally:
            # Clean up
            await transcriber.cleanup()


if __name__ == "__main__":
    pytest.main([__file__]) 