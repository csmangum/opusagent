"""
Tests for the transcription module.

This module contains tests for the local audio transcription functionality
"""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import numpy as np
import pydantic

from opusagent.local.transcription import (
    TranscriptionConfig,
    TranscriptionFactory,
    TranscriptionResult,
    load_transcription_config,
    BaseTranscriber,
)
from opusagent.local.transcription.backends import PocketSphinxTranscriber, WhisperTranscriber


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

    def test_pocketsphinx_specific_config(self):
        """Test PocketSphinx-specific configuration."""
        config = TranscriptionConfig(
            pocketsphinx_hmm="/path/to/hmm",
            pocketsphinx_lm="/path/to/lm",
            pocketsphinx_dict="/path/to/dict"
        )
        assert config.pocketsphinx_hmm == "/path/to/hmm"
        assert config.pocketsphinx_lm == "/path/to/lm"
        assert config.pocketsphinx_dict == "/path/to/dict"

    def test_whisper_specific_config(self):
        """Test Whisper-specific configuration."""
        config = TranscriptionConfig(
            whisper_model_dir="/path/to/models",
            whisper_temperature=0.3
        )
        assert config.whisper_model_dir == "/path/to/models"
        assert config.whisper_temperature == 0.3


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

    def test_result_with_error(self):
        """Test result with error."""
        result = TranscriptionResult(
            text="",
            error="Transcription failed",
            is_final=True
        )
        assert result.text == ""
        assert result.error == "Transcription failed"
        assert result.is_final == True


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

    def test_create_transcriber_case_insensitive(self):
        """Test creating transcriber with case-insensitive backend."""
        config = TranscriptionConfig(backend="POCKETSPHINX")
        transcriber = TranscriptionFactory.create_transcriber(config)
        assert isinstance(transcriber, PocketSphinxTranscriber)

    def test_unsupported_backend(self):
        """Test creating transcriber with unsupported backend."""
        with pytest.raises(pydantic.ValidationError, match="Unsupported transcription backend"):
            TranscriptionConfig(backend="unsupported")

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
        # Reload config to pick up environment variables
        from opusagent.config.settings import reload_config
        reload_config()
        
        config = load_transcription_config()
        assert config.backend == "whisper"
        assert config.language == "es"
        assert config.model_size == "large"
        assert config.chunk_duration == 2.0
        assert config.confidence_threshold == 0.8
        assert config.sample_rate == 24000
        assert config.enable_vad == False
        assert config.device == "cuda"

    @patch.dict(os.environ, {
        "POCKETSPHINX_HMM": "/custom/hmm",
        "POCKETSPHINX_LM": "/custom/lm",
        "POCKETSPHINX_DICT": "/custom/dict",
        "WHISPER_MODEL_DIR": "/custom/models",
        "WHISPER_TEMPERATURE": "0.3"
    })
    def test_load_custom_model_paths(self):
        """Test loading custom model paths from environment."""
        # Reload config to pick up environment variables
        from opusagent.config.settings import reload_config
        reload_config()
        
        config = load_transcription_config()
        assert config.pocketsphinx_hmm == "/custom/hmm"
        assert config.pocketsphinx_lm == "/custom/lm"
        assert config.pocketsphinx_dict == "/custom/dict"
        assert config.whisper_model_dir == "/custom/models"
        assert config.whisper_temperature == 0.3


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
        assert transcriber.config is not None

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

    def test_reset_session(self, transcriber):
        """Test resetting session state."""
        transcriber._audio_buffer = [b"test"]
        transcriber._session_active = True
        transcriber.reset_session()
        assert transcriber._session_active == False
        assert len(transcriber._audio_buffer) == 0

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
        audio_int16 = np.array([1000, -1000, 2000, -2000], dtype=np.int16)
        audio_bytes = audio_int16.tobytes()
        
        result = transcriber._convert_audio_for_processing(audio_bytes)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert len(result) == 4
        
        # Test with empty data
        empty_result = transcriber._convert_audio_for_processing(b"")
        assert len(empty_result) == 0

    def test_convert_audio_for_processing_error(self, transcriber):
        """Test audio conversion error handling."""
        # Test with invalid data
        result = transcriber._convert_audio_for_processing(b"invalid")
        assert len(result) == 0


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
    async def test_initialize_with_pocketsphinx(self, transcriber):
        """Test initialization with PocketSphinx available."""
        mock_decoder = MagicMock()
        mock_config = MagicMock()
        
        with patch('pocketsphinx.Decoder') as mock_decoder_class, \
             patch('pocketsphinx.Decoder.default_config') as mock_default_config:
            
            mock_default_config.return_value = mock_config
            mock_decoder_class.return_value = mock_decoder
            
            result = await transcriber.initialize()
            
            assert result == True
            assert transcriber._initialized == True
            assert transcriber._decoder == mock_decoder

    @pytest.mark.asyncio
    async def test_initialize_with_custom_models(self, transcriber):
        """Test initialization with custom PocketSphinx models."""
        transcriber.config.pocketsphinx_hmm = "/custom/hmm"
        transcriber.config.pocketsphinx_lm = "/custom/lm"
        transcriber.config.pocketsphinx_dict = "/custom/dict"
        
        mock_decoder = MagicMock()
        mock_config = MagicMock()
        
        with patch('pocketsphinx.Decoder') as mock_decoder_class, \
             patch('pocketsphinx.Decoder.default_config') as mock_default_config:
            
            mock_default_config.return_value = mock_config
            mock_decoder_class.return_value = mock_decoder
            
            result = await transcriber.initialize()
            
            assert result == True
            # Verify config was set with custom paths
            mock_config.set_string.assert_any_call("hmm", "/custom/hmm")
            mock_config.set_string.assert_any_call("lm", "/custom/lm")
            mock_config.set_string.assert_any_call("dict", "/custom/dict")

    @pytest.mark.asyncio
    async def test_transcribe_chunk_not_initialized(self, transcriber):
        """Test transcribing chunk when not initialized."""
        result = await transcriber.transcribe_chunk(b"test")
        assert result.text == ""
        assert result.error == "Transcriber not initialized"

    @pytest.mark.asyncio
    async def test_transcribe_chunk_initialized(self, transcriber):
        """Test transcribing chunk when initialized."""
        # Mock decoder and hypothesis
        mock_hypothesis = MagicMock()
        mock_hypothesis.hypstr = "test transcription"
        mock_hypothesis.prob = 0.85
        
        mock_decoder = MagicMock()
        mock_decoder.hyp.return_value = mock_hypothesis
        
        transcriber._decoder = mock_decoder
        transcriber._initialized = True
        transcriber._accumulated_text = ""  # Ensure it's empty
        
        # Create test audio data (enough for chunk processing)
        audio_data = np.zeros(16000, dtype=np.int16).tobytes()  # 1 second at 16kHz
        
        # First call fills the buffer, second call processes it
        await transcriber.transcribe_chunk(audio_data)
        result = await transcriber.transcribe_chunk(audio_data)
        
        assert result.text == "test transcription"
        assert result.confidence == 0.85
        assert result.is_final == False

    @pytest.mark.asyncio
    async def test_transcribe_chunk_insufficient_data(self, transcriber):
        """Test transcribing chunk with insufficient data."""
        mock_decoder = MagicMock()
        transcriber._decoder = mock_decoder
        transcriber._initialized = True
        
        # Small audio chunk (not enough for processing)
        audio_data = b"small"
        
        result = await transcriber.transcribe_chunk(audio_data)
        
        assert result.text == ""
        assert result.error == "Invalid audio data"
        # Decoder should not be called for insufficient data
        mock_decoder.process_raw.assert_not_called()

    @pytest.mark.asyncio
    async def test_finalize_not_initialized(self, transcriber):
        """Test finalizing when not initialized."""
        result = await transcriber.finalize()
        assert result.text == ""
        assert result.error == "Transcriber not initialized"

    @pytest.mark.asyncio
    async def test_finalize_initialized(self, transcriber):
        """Test finalizing when initialized."""
        mock_hypothesis = MagicMock()
        mock_hypothesis.hypstr = "final transcription"
        mock_hypothesis.prob = 0.9
        
        mock_decoder = MagicMock()
        mock_decoder.hyp.return_value = mock_hypothesis
        
        transcriber._decoder = mock_decoder
        transcriber._initialized = True
        transcriber._accumulated_text = "partial text"
        
        result = await transcriber.finalize()
        
        assert result.text == "final transcription"
        assert result.confidence == 0.9
        assert result.is_final == True

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

    def test_start_session_with_utterance(self, transcriber):
        """Test starting session with utterance management."""
        mock_decoder = MagicMock()
        transcriber._decoder = mock_decoder
        
        transcriber.start_session()
        
        mock_decoder.start_utt.assert_called_once()
        assert transcriber._session_active == True

    def test_end_session_with_utterance(self, transcriber):
        """Test ending session with utterance management."""
        mock_decoder = MagicMock()
        transcriber._decoder = mock_decoder
        transcriber._session_active = True
        
        transcriber.end_session()
        
        mock_decoder.end_utt.assert_called_once()
        assert transcriber._session_active == False

    def test_reset_session(self, transcriber):
        """Test resetting session state."""
        mock_decoder = MagicMock()
        transcriber._decoder = mock_decoder
        transcriber._audio_buffer = [b"test"]
        transcriber._accumulated_text = "test text"
        transcriber._session_active = True
        
        transcriber.reset_session()
        
        mock_decoder.end_utt.assert_called_once()
        assert len(transcriber._audio_buffer) == 0
        assert transcriber._accumulated_text == ""
        assert transcriber._session_active == False


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
    async def test_initialize_with_openai_whisper(self, transcriber):
        """Test initialization with openai-whisper."""
        mock_model = MagicMock()
        mock_whisper = MagicMock()
        mock_whisper.load_model.return_value = mock_model
        
        with patch.dict('sys.modules', {'openai_whisper': mock_whisper}), \
             patch('tempfile.mkdtemp') as mock_mkdtemp:
            
            mock_mkdtemp.return_value = "/tmp/test"
            
            result = await transcriber.initialize()
            
            assert result == True
            assert transcriber._initialized == True
            assert transcriber._model == mock_model
            assert transcriber._temp_dir == "/tmp/test"
            mock_whisper.load_model.assert_called_once_with("base", device="cpu")

    @pytest.mark.asyncio
    async def test_initialize_with_regular_whisper(self, transcriber):
        """Test initialization with regular whisper module."""
        mock_model = MagicMock()
        mock_whisper = MagicMock()
        mock_whisper.load_model.return_value = mock_model
        
        with patch.dict('sys.modules', {'openai_whisper': None, 'whisper': mock_whisper}), \
             patch('tempfile.mkdtemp') as mock_mkdtemp:
            
            mock_mkdtemp.return_value = "/tmp/test"
            
            result = await transcriber.initialize()
            
            assert result == True
            assert transcriber._initialized == True
            assert transcriber._model == mock_model
            mock_whisper.load_model.assert_called_once_with("base", device="cpu")

    @pytest.mark.asyncio
    async def test_initialize_with_custom_model_dir(self, transcriber):
        """Test initialization with custom model directory."""
        transcriber.config.whisper_model_dir = "/custom/models"
        transcriber.config.model_size = "large"
        
        mock_model = MagicMock()
        mock_whisper = MagicMock()
        mock_whisper.load_model.return_value = mock_model
        
        with patch.dict('sys.modules', {'openai_whisper': mock_whisper}), \
             patch('tempfile.mkdtemp') as mock_mkdtemp, \
             patch('pathlib.Path.exists', return_value=True):
            
            mock_mkdtemp.return_value = "/tmp/test"
            
            result = await transcriber.initialize()
            
            assert result == True
            # Should load from custom directory (path separator may vary by OS)
            mock_whisper.load_model.assert_called_once()
            call_args = mock_whisper.load_model.call_args
            # call_args is a tuple: (args, kwargs)
            assert call_args[0][0].endswith("large.pt")
            assert call_args[1]["device"] == "cpu"

    @pytest.mark.asyncio
    async def test_transcribe_chunk_not_initialized(self, transcriber):
        """Test transcribing chunk when not initialized."""
        result = await transcriber.transcribe_chunk(b"test")
        assert result.text == ""
        assert result.error == "Transcriber not initialized"

    @pytest.mark.asyncio
    async def test_transcribe_chunk_initialized(self, transcriber):
        """Test transcribing chunk when initialized."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "test transcription",
            "segments": [{"avg_logprob": -0.1}]
        }
        
        transcriber._model = mock_model
        transcriber._initialized = True
        
        # Create test audio data (enough for chunk processing)
        audio_data = np.zeros(32000, dtype=np.int16).tobytes()  # 2 seconds at 16kHz
        
        with patch('asyncio.get_event_loop') as mock_loop:
            # Mock the executor to return a proper result
            async def mock_executor(*args):
                return TranscriptionResult(
                    text="test transcription", confidence=0.8
                )
            mock_loop.return_value.run_in_executor = mock_executor
            
            result = await transcriber.transcribe_chunk(audio_data)
            
            # The result should come from the mocked executor
            assert result.text == "test transcription"
            assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_transcribe_chunk_insufficient_data(self, transcriber):
        """Test transcribing chunk with insufficient data."""
        mock_model = MagicMock()
        transcriber._model = mock_model
        transcriber._initialized = True
        
        # Small audio chunk (not enough for processing)
        audio_data = b"small"
        
        result = await transcriber.transcribe_chunk(audio_data)
        
        assert result.text == ""
        assert result.error == "Invalid audio data"
        # Model should not be called for insufficient data
        mock_model.transcribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_finalize_not_initialized(self, transcriber):
        """Test finalizing when not initialized."""
        result = await transcriber.finalize()
        assert result.text == ""
        assert result.error == "Transcriber not initialized"

    @pytest.mark.asyncio
    async def test_finalize_initialized(self, transcriber):
        """Test finalizing when initialized."""
        transcriber._model = MagicMock()
        transcriber._initialized = True
        transcriber._accumulated_text = "partial text"
        transcriber._audio_buffer = [0.1, 0.2, 0.3]  # Some audio data
        
        with patch('asyncio.get_event_loop') as mock_loop:
            # run_in_executor returns a Future that resolves to the result
            future = asyncio.Future()
            future.set_result(TranscriptionResult(
                text="final transcription", confidence=0.9
            ))
            mock_loop.return_value.run_in_executor.return_value = future
            
            result = await transcriber.finalize()
            
            # Should return accumulated text from chunks, combined with finalization result
            assert result.text == "partial text final transcription"
            assert result.is_final == True

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

    def test_reset_session(self, transcriber):
        """Test resetting session state."""
        transcriber._audio_buffer = [0.1, 0.2, 0.3]
        transcriber._accumulated_text = "test text"
        transcriber._session_active = True
        
        transcriber.reset_session()
        
        assert len(transcriber._audio_buffer) == 0
        assert transcriber._accumulated_text == ""
        assert transcriber._session_active == False

    def test_transcribe_with_whisper(self, transcriber):
        """Test the _transcribe_with_whisper method."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "hello world",
            "segments": [
                {"avg_logprob": -0.1},
                {"avg_logprob": -0.2}
            ]
        }
        
        transcriber._model = mock_model
        
        # Test audio data
        audio_data = np.random.randn(16000).astype(np.float32)
        
        result = transcriber._transcribe_with_whisper(audio_data)
        
        assert result.text == "hello world"
        assert result.confidence > 0.0
        assert result.is_final == False
        assert result.segments is not None

    def test_transcribe_with_whisper_error(self, transcriber):
        """Test _transcribe_with_whisper error handling."""
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = Exception("Whisper error")
        
        transcriber._model = mock_model
        
        audio_data = np.random.randn(16000).astype(np.float32)
        
        result = transcriber._transcribe_with_whisper(audio_data)
        
        assert result.text == ""
        assert result.error == "Whisper error"


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

    @pytest.mark.asyncio
    async def test_multiple_sessions(self):
        """Test multiple transcription sessions with the same transcriber."""
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
            # First session
            transcriber.start_session()
            test_audio = np.zeros(16000, dtype=np.int16)
            result1 = await transcriber.transcribe_chunk(test_audio.tobytes())
            final1 = await transcriber.finalize()
            transcriber.end_session()
            
            # Second session
            transcriber.start_session()
            result2 = await transcriber.transcribe_chunk(test_audio.tobytes())
            final2 = await transcriber.finalize()
            transcriber.end_session()
            
            # Both sessions should work
            assert isinstance(result1, TranscriptionResult)
            assert isinstance(result2, TranscriptionResult)
            assert isinstance(final1, TranscriptionResult)
            assert isinstance(final2, TranscriptionResult)
            
        finally:
            await transcriber.cleanup()


if __name__ == "__main__":
    pytest.main([__file__]) 