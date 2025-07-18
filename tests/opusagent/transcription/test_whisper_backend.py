"""
Unit tests for Whisper transcription backend.
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch, Mock, AsyncMock
import asyncio
import tempfile
from pathlib import Path

from opusagent.local.transcription.backends.whisper import WhisperTranscriber
from opusagent.local.transcription.models import TranscriptionConfig, TranscriptionResult


class TestWhisperTranscriber:
    """Test WhisperTranscriber backend."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = TranscriptionConfig(
            backend="whisper",
            model_size="base",
            chunk_duration=2.0,
            sample_rate=16000,
            device="cpu",
            whisper_temperature=0.0
        )
        self.transcriber = WhisperTranscriber(self.config)

    def test_initialization(self):
        """Test transcriber initialization."""
        assert self.transcriber.config == self.config
        assert self.transcriber._model is None
        assert self.transcriber._temp_dir is None
        assert self.transcriber._accumulated_text == ""
        assert self.transcriber._last_segment_end == 0.0
        assert hasattr(self.transcriber, 'logger')

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful initialization."""
        mock_whisper = MagicMock()
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model
        
        with patch.dict('sys.modules', {'whisper': mock_whisper}):
            with patch('tempfile.mkdtemp', return_value='/tmp/whisper_test'):
                result = await self.transcriber.initialize()
        
        assert result == True
        assert self.transcriber._initialized == True
        assert self.transcriber._model == mock_model
        assert self.transcriber._temp_dir == '/tmp/whisper_test'
        
        # Verify model was loaded with correct parameters
        mock_whisper.load_model.assert_called_once_with("base", device="cpu")

    @pytest.mark.asyncio
    async def test_initialize_with_openai_whisper(self):
        """Test initialization with openai_whisper module."""
        mock_openai_whisper = MagicMock()
        mock_model = MagicMock()
        mock_openai_whisper.load_model.return_value = mock_model
        
        # Mock openai_whisper available, regular whisper not
        with patch.dict('sys.modules', {'openai_whisper': mock_openai_whisper, 'whisper': None}):
            with patch('tempfile.mkdtemp', return_value='/tmp/whisper_test'):
                result = await self.transcriber.initialize()
        
        assert result == True
        assert self.transcriber._model == mock_model
        mock_openai_whisper.load_model.assert_called_once_with("base", device="cpu")

    @pytest.mark.asyncio
    async def test_initialize_with_custom_model_dir(self):
        """Test initialization with custom model directory."""
        config = TranscriptionConfig(
            backend="whisper",
            model_size="large",
            whisper_model_dir="/custom/models"
        )
        transcriber = WhisperTranscriber(config)
        
        mock_whisper = MagicMock()
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model
        
        # Mock model file exists
        with patch.dict('sys.modules', {'whisper': mock_whisper}):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('tempfile.mkdtemp', return_value='/tmp/whisper_test'):
                    result = await transcriber.initialize()
        
        assert result == True
        # Should load from custom path
        expected_path = str(Path("/custom/models") / "large.pt")
        mock_whisper.load_model.assert_called_once_with(expected_path, device="cpu")

    @pytest.mark.asyncio
    async def test_initialize_custom_model_not_found(self):
        """Test initialization with custom model directory but file not found."""
        config = TranscriptionConfig(
            backend="whisper",
            whisper_model_dir="/custom/models"
        )
        transcriber = WhisperTranscriber(config)
        
        mock_whisper = MagicMock()
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model
        
        # Mock model file doesn't exist
        with patch.dict('sys.modules', {'whisper': mock_whisper}):
            with patch('pathlib.Path.exists', return_value=False):
                with patch('tempfile.mkdtemp', return_value='/tmp/whisper_test'):
                    with patch.object(transcriber.logger, 'warning') as mock_logger:
                        result = await transcriber.initialize()
        
        assert result == True
        # Should warn and fall back to default
        mock_logger.assert_called_once()
        mock_whisper.load_model.assert_called_with("base", device="cpu")

    @pytest.mark.asyncio
    async def test_initialize_import_error(self):
        """Test initialization failure due to import error."""
        with patch.dict('sys.modules', {}):
            with patch('builtins.__import__', side_effect=ImportError("No module")):
                result = await self.transcriber.initialize()
        
        assert result == False
        assert self.transcriber._initialized == False

    @pytest.mark.asyncio
    async def test_initialize_model_loading_error(self):
        """Test initialization failure due to model loading error."""
        mock_whisper = MagicMock()
        mock_whisper.load_model.side_effect = Exception("Model loading failed")
        
        with patch.dict('sys.modules', {'whisper': mock_whisper}):
            result = await self.transcriber.initialize()
        
        assert result == False
        assert self.transcriber._initialized == False

    @pytest.mark.asyncio
    async def test_transcribe_chunk_not_initialized(self):
        """Test transcription chunk when not initialized."""
        audio_data = b"test_audio"
        
        result = await self.transcriber.transcribe_chunk(audio_data)
        
        assert isinstance(result, TranscriptionResult)
        assert result.text == ""
        assert result.error == "Transcriber not initialized"

    @pytest.mark.asyncio
    async def test_transcribe_chunk_success(self):
        """Test successful chunk transcription."""
        mock_model = MagicMock()
        self.transcriber._model = mock_model
        self.transcriber._initialized = True
        
        # Mock transcription result
        mock_result = {
            "text": "hello world",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "hello", "avg_logprob": -0.2},
                {"start": 1.0, "end": 2.0, "text": " world", "avg_logprob": -0.3}
            ]
        }
        
        audio_data = b"test_audio"
        
        with patch.object(self.transcriber, '_convert_audio_for_processing') as mock_convert:
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_executor = AsyncMock()
                mock_executor.return_value = TranscriptionResult(
                    text="hello world",
                    confidence=0.75,
                    is_final=False,
                    segments=mock_result["segments"]
                )
                mock_loop.return_value.run_in_executor = mock_executor
                
                mock_convert.return_value = np.array([0.1, 0.2], dtype=np.float32)
                
                # Add enough samples to trigger processing
                samples_needed = int(self.config.sample_rate * self.config.chunk_duration * 2)
                self.transcriber._audio_buffer = [0.0] * samples_needed
                
                result = await self.transcriber.transcribe_chunk(audio_data)
        
        assert isinstance(result, TranscriptionResult)
        assert result.text == "hello world"
        assert result.confidence == 0.75
        assert result.is_final == False
        assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_transcribe_chunk_insufficient_data(self):
        """Test chunk transcription with insufficient audio data."""
        mock_model = MagicMock()
        self.transcriber._model = mock_model
        self.transcriber._initialized = True
        
        audio_data = b"small"
        
        with patch.object(self.transcriber, '_convert_audio_for_processing') as mock_convert:
            mock_convert.return_value = np.array([0.1, 0.2], dtype=np.float32)  # Small buffer
            
            result = await self.transcriber.transcribe_chunk(audio_data)
        
        assert isinstance(result, TranscriptionResult)
        assert result.text == ""
        assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_transcribe_chunk_error_handling(self):
        """Test error handling in chunk transcription."""
        self.transcriber._model = MagicMock()
        self.transcriber._initialized = True
        
        audio_data = b"test"
        
        # Mock an exception during processing
        with patch.object(self.transcriber, '_convert_audio_for_processing', side_effect=Exception("Test error")):
            result = await self.transcriber.transcribe_chunk(audio_data)
        
        assert isinstance(result, TranscriptionResult)
        assert result.text == ""
        assert result.error == "Test error"
        assert result.processing_time > 0

    def test_transcribe_with_whisper_success(self):
        """Test internal _transcribe_with_whisper method."""
        mock_model = MagicMock()
        mock_result = {
            "text": "transcribed text",
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "transcribed text", "avg_logprob": -0.1}
            ]
        }
        mock_model.transcribe.return_value = mock_result
        
        self.transcriber._model = mock_model
        
        audio_data = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        
        result = self.transcriber._transcribe_with_whisper(audio_data)
        
        assert isinstance(result, TranscriptionResult)
        assert result.text == "transcribed text"
        assert result.confidence > 0
        assert result.is_final == False
        assert result.segments == mock_result["segments"]

    def test_transcribe_with_whisper_audio_padding(self):
        """Test audio padding in _transcribe_with_whisper."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "test", "segments": []}
        
        self.transcriber._model = mock_model
        
        # Short audio that needs padding
        short_audio = np.array([0.1, 0.2], dtype=np.float32)
        
        result = self.transcriber._transcribe_with_whisper(short_audio)
        
        # Should have been called with padded audio
        call_args = mock_model.transcribe.call_args[0]
        padded_audio = call_args[0]
        expected_length = self.config.sample_rate * 30  # 30 seconds
        assert len(padded_audio) == expected_length

    def test_transcribe_with_whisper_audio_truncation(self):
        """Test audio truncation in _transcribe_with_whisper."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "test", "segments": []}
        
        self.transcriber._model = mock_model
        
        # Long audio that needs truncation
        long_audio = np.array([0.1] * (self.config.sample_rate * 35), dtype=np.float32)  # 35 seconds
        
        result = self.transcriber._transcribe_with_whisper(long_audio)
        
        # Should have been called with truncated audio
        call_args = mock_model.transcribe.call_args[0]
        truncated_audio = call_args[0]
        expected_length = self.config.sample_rate * 30  # 30 seconds
        assert len(truncated_audio) == expected_length

    def test_transcribe_with_whisper_delta_text(self):
        """Test delta text extraction in _transcribe_with_whisper."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "hello world", "segments": []}
        
        self.transcriber._model = mock_model
        self.transcriber._accumulated_text = "hello"
        
        audio_data = np.array([0.1], dtype=np.float32)
        
        result = self.transcriber._transcribe_with_whisper(audio_data)

        assert result.text == "world"  # Only the new part (stripped)
        assert self.transcriber._accumulated_text == "hello world"

    def test_transcribe_with_whisper_confidence_calculation(self):
        """Test confidence calculation from segments."""
        mock_model = MagicMock()
        mock_result = {
            "text": "test",
            "segments": [
                {"avg_logprob": -0.2},
                {"avg_logprob": -0.4},
                {"avg_logprob": -0.3}
            ]
        }
        mock_model.transcribe.return_value = mock_result
        
        self.transcriber._model = mock_model
        
        audio_data = np.array([0.1], dtype=np.float32)
        
        result = self.transcriber._transcribe_with_whisper(audio_data)
        
        # Confidence should be calculated from average log prob
        expected_avg_logprob = (-0.2 + -0.4 + -0.3) / 3
        expected_confidence = max(0.0, min(1.0, (expected_avg_logprob + 1.0) / 2.0))
        assert abs(result.confidence - expected_confidence) < 0.01

    def test_transcribe_with_whisper_error_handling(self):
        """Test error handling in _transcribe_with_whisper."""
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = Exception("Transcription error")
        
        self.transcriber._model = mock_model
        
        audio_data = np.array([0.1], dtype=np.float32)
        
        result = self.transcriber._transcribe_with_whisper(audio_data)
        
        assert isinstance(result, TranscriptionResult)
        assert result.text == ""
        assert result.error == "Transcription error"

    @pytest.mark.asyncio
    async def test_finalize_success(self):
        """Test successful finalization."""
        mock_model = MagicMock()
        self.transcriber._model = mock_model
        self.transcriber._initialized = True
        self.transcriber._accumulated_text = "final text"
        self.transcriber._audio_buffer = [0.1, 0.2, 0.3]
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_executor = AsyncMock()
            mock_executor.return_value = TranscriptionResult(
                text="additional text",
                confidence=0.9
            )
            mock_loop.return_value.run_in_executor = mock_executor
            
            result = await self.transcriber.finalize()
        
        assert isinstance(result, TranscriptionResult)
        assert result.text == "final text additional text"  # Combined accumulated + additional text
        assert result.confidence == 1.0
        assert result.is_final == True
        assert result.processing_time > 0
        assert self.transcriber._accumulated_text == ""
        assert len(self.transcriber._audio_buffer) == 0

    @pytest.mark.asyncio
    async def test_finalize_no_remaining_audio(self):
        """Test finalization with no remaining audio."""
        mock_model = MagicMock()
        self.transcriber._model = mock_model
        self.transcriber._initialized = True
        self.transcriber._accumulated_text = "final text"
        self.transcriber._audio_buffer = []  # No remaining audio
        
        result = await self.transcriber.finalize()
        
        assert isinstance(result, TranscriptionResult)
        assert result.text == "final text"
        assert result.confidence == 1.0
        assert result.is_final == True

    @pytest.mark.asyncio
    async def test_finalize_not_initialized(self):
        """Test finalization when not initialized."""
        result = await self.transcriber.finalize()
        
        assert isinstance(result, TranscriptionResult)
        assert result.text == ""
        assert result.error == "Transcriber not initialized"

    @pytest.mark.asyncio
    async def test_cleanup_success(self):
        """Test successful cleanup."""
        # Create a real temporary directory for testing
        temp_dir = tempfile.mkdtemp()
        
        self.transcriber._temp_dir = temp_dir
        self.transcriber._model = MagicMock()
        self.transcriber._initialized = True
        
        # Verify temp dir exists
        assert Path(temp_dir).exists()
        
        await self.transcriber.cleanup()
        
        # Verify cleanup
        assert self.transcriber._model is None
        assert self.transcriber._initialized == False
        # Temp dir should be cleaned up
        assert not Path(temp_dir).exists()

    @pytest.mark.asyncio
    async def test_cleanup_temp_dir_error(self):
        """Test cleanup with temp directory removal error."""
        self.transcriber._temp_dir = "/nonexistent/temp/dir"
        self.transcriber._model = MagicMock()
        self.transcriber._initialized = True
        
        with patch.object(self.transcriber.logger, 'warning') as mock_logger:
            await self.transcriber.cleanup()
        
        # Should handle error gracefully
        mock_logger.assert_called_once()
        assert self.transcriber._model is None
        assert self.transcriber._initialized == False

    def test_reset_session(self):
        """Test session reset."""
        self.transcriber._session_active = True
        self.transcriber._audio_buffer = [1, 2, 3]
        self.transcriber._accumulated_text = "some text"
        
        self.transcriber.reset_session()
        
        assert self.transcriber._session_active == False
        assert len(self.transcriber._audio_buffer) == 0
        assert self.transcriber._accumulated_text == ""

    def test_config_integration(self):
        """Test integration with configuration."""
        config = TranscriptionConfig(
            backend="whisper",
            model_size="large",
            chunk_duration=3.0,
            device="cuda",
            whisper_temperature=0.2,
            whisper_model_dir="/custom/models"
        )
        transcriber = WhisperTranscriber(config)
        
        assert transcriber.config.model_size == "large"
        assert transcriber.config.chunk_duration == 3.0
        assert transcriber.config.device == "cuda"
        assert transcriber.config.whisper_temperature == 0.2
        assert transcriber.config.whisper_model_dir == "/custom/models"

    def test_whisper_transcribe_parameters(self):
        """Test that Whisper is called with correct parameters."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "test", "segments": []}
        
        config = TranscriptionConfig(
            backend="whisper",
            language="es",
            whisper_temperature=0.5
        )
        transcriber = WhisperTranscriber(config)
        transcriber._model = mock_model
        
        audio_data = np.array([0.1], dtype=np.float32)
        
        transcriber._transcribe_with_whisper(audio_data)
        
        # Verify call parameters
        call_kwargs = mock_model.transcribe.call_args[1]
        assert call_kwargs["language"] == "es"
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["word_timestamps"] == True
        assert call_kwargs["verbose"] == False

    def test_whisper_transcribe_english_language_special_case(self):
        """Test that English language is handled specially."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "test", "segments": []}
        
        config = TranscriptionConfig(
            backend="whisper",
            language="en"  # English should be passed as None
        )
        transcriber = WhisperTranscriber(config)
        transcriber._model = mock_model
        
        audio_data = np.array([0.1], dtype=np.float32)
        
        transcriber._transcribe_with_whisper(audio_data)
        
        # English should be passed as None to Whisper
        call_kwargs = mock_model.transcribe.call_args[1]
        assert call_kwargs["language"] is None 