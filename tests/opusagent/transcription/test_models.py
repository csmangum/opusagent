"""
Unit tests for transcription models.
"""
import pytest
from pydantic import ValidationError

from opusagent.local.transcription.models import TranscriptionResult, TranscriptionConfig


class TestTranscriptionResult:
    """Test TranscriptionResult model."""

    def test_basic_creation(self):
        """Test basic TranscriptionResult creation."""
        result = TranscriptionResult(text="Hello world")
        assert result.text == "Hello world"
        assert result.confidence == 0.0
        assert result.is_final == False
        assert result.segments is None
        assert result.processing_time == 0.0
        assert result.error is None

    def test_full_creation(self):
        """Test TranscriptionResult with all fields."""
        segments = [{"start": 0.0, "end": 1.0, "text": "Hello"}]
        result = TranscriptionResult(
            text="Hello world",
            confidence=0.85,
            is_final=True,
            segments=segments,
            processing_time=1.5,
            error=None
        )
        assert result.text == "Hello world"
        assert result.confidence == 0.85
        assert result.is_final == True
        assert result.segments == segments
        assert result.processing_time == 1.5
        assert result.error is None

    def test_confidence_validation(self):
        """Test confidence field validation."""
        # Valid confidence values
        TranscriptionResult(text="test", confidence=0.0)
        TranscriptionResult(text="test", confidence=0.5)
        TranscriptionResult(text="test", confidence=1.0)
        
        # Invalid confidence values
        with pytest.raises(ValidationError):
            TranscriptionResult(text="test", confidence=-0.1)
        
        with pytest.raises(ValidationError):
            TranscriptionResult(text="test", confidence=1.1)

    def test_with_error(self):
        """Test TranscriptionResult with error."""
        result = TranscriptionResult(
            text="",
            error="Transcription failed"
        )
        assert result.text == ""
        assert result.error == "Transcription failed"
        assert result.confidence == 0.0


class TestTranscriptionConfig:
    """Test TranscriptionConfig model."""

    def test_default_creation(self):
        """Test TranscriptionConfig with defaults."""
        config = TranscriptionConfig()
        assert config.backend == "pocketsphinx"
        assert config.language == "en"
        assert config.model_size == "base"
        assert config.chunk_duration == 1.0
        assert config.confidence_threshold == 0.5
        assert config.sample_rate == 16000
        assert config.enable_vad == True
        assert config.device == "cpu"

    def test_pocketsphinx_defaults(self):
        """Test PocketSphinx specific defaults."""
        config = TranscriptionConfig()
        assert config.pocketsphinx_hmm is None
        assert config.pocketsphinx_lm is None
        assert config.pocketsphinx_dict is None
        assert config.pocketsphinx_audio_preprocessing == "normalize"
        assert config.pocketsphinx_vad_settings == "conservative"
        assert config.pocketsphinx_auto_resample == True
        assert config.pocketsphinx_input_sample_rate == 24000

    def test_whisper_defaults(self):
        """Test Whisper specific defaults."""
        config = TranscriptionConfig()
        assert config.whisper_model_dir is None
        assert config.whisper_temperature == 0.0

    def test_backend_validation(self):
        """Test backend validation."""
        # Valid backends
        config1 = TranscriptionConfig(backend="pocketsphinx")
        assert config1.backend == "pocketsphinx"
        
        config2 = TranscriptionConfig(backend="whisper")
        assert config2.backend == "whisper"
        
        config3 = TranscriptionConfig(backend="WHISPER")  # Case insensitive
        assert config3.backend == "whisper"
        
        # Invalid backend
        with pytest.raises(ValidationError):
            TranscriptionConfig(backend="invalid")

    def test_confidence_threshold_validation(self):
        """Test confidence threshold validation."""
        # Valid values
        TranscriptionConfig(confidence_threshold=0.0)
        TranscriptionConfig(confidence_threshold=0.5)
        TranscriptionConfig(confidence_threshold=1.0)
        
        # Invalid values
        with pytest.raises(ValidationError):
            TranscriptionConfig(confidence_threshold=-0.1)
        
        with pytest.raises(ValidationError):
            TranscriptionConfig(confidence_threshold=1.1)

    def test_chunk_duration_validation(self):
        """Test chunk duration validation."""
        # Valid values
        TranscriptionConfig(chunk_duration=0.1)
        TranscriptionConfig(chunk_duration=5.0)
        
        # Invalid values
        with pytest.raises(ValidationError):
            TranscriptionConfig(chunk_duration=0.0)
        
        with pytest.raises(ValidationError):
            TranscriptionConfig(chunk_duration=-1.0)

    def test_sample_rate_validation(self):
        """Test sample rate validation."""
        # Valid values
        TranscriptionConfig(sample_rate=8000)
        TranscriptionConfig(sample_rate=16000)
        TranscriptionConfig(sample_rate=44100)
        
        # Invalid values
        with pytest.raises(ValidationError):
            TranscriptionConfig(sample_rate=0)
        
        with pytest.raises(ValidationError):
            TranscriptionConfig(sample_rate=-1000)

    def test_device_validation(self):
        """Test device validation."""
        # Valid devices
        TranscriptionConfig(device="cpu")
        TranscriptionConfig(device="cuda")
        
        # Invalid device
        with pytest.raises(ValidationError):
            TranscriptionConfig(device="gpu")

    def test_pocketsphinx_preprocessing_validation(self):
        """Test PocketSphinx preprocessing validation."""
        # Valid preprocessing types
        valid_types = ["none", "normalize", "amplify", "noise_reduction", "silence_trim"]
        for preprocessing_type in valid_types:
            TranscriptionConfig(pocketsphinx_audio_preprocessing=preprocessing_type)
        
        # Invalid preprocessing type
        with pytest.raises(ValidationError):
            TranscriptionConfig(pocketsphinx_audio_preprocessing="invalid")

    def test_pocketsphinx_vad_validation(self):
        """Test PocketSphinx VAD settings validation."""
        # Valid VAD settings
        valid_settings = ["default", "aggressive", "conservative"]
        for vad_setting in valid_settings:
            TranscriptionConfig(pocketsphinx_vad_settings=vad_setting)
        
        # Invalid VAD setting
        with pytest.raises(ValidationError):
            TranscriptionConfig(pocketsphinx_vad_settings="invalid")

    def test_whisper_temperature_validation(self):
        """Test Whisper temperature validation."""
        # Valid temperatures
        TranscriptionConfig(whisper_temperature=0.0)
        TranscriptionConfig(whisper_temperature=0.5)
        TranscriptionConfig(whisper_temperature=1.0)
        
        # Invalid temperatures
        with pytest.raises(ValidationError):
            TranscriptionConfig(whisper_temperature=-0.1)
        
        with pytest.raises(ValidationError):
            TranscriptionConfig(whisper_temperature=1.1)

    def test_pocketsphinx_input_sample_rate_validation(self):
        """Test PocketSphinx input sample rate validation."""
        # Valid sample rates
        TranscriptionConfig(pocketsphinx_input_sample_rate=16000)
        TranscriptionConfig(pocketsphinx_input_sample_rate=24000)
        TranscriptionConfig(pocketsphinx_input_sample_rate=48000)
        
        # Invalid sample rates
        with pytest.raises(ValidationError):
            TranscriptionConfig(pocketsphinx_input_sample_rate=0)
        
        with pytest.raises(ValidationError):
            TranscriptionConfig(pocketsphinx_input_sample_rate=-1000)

    def test_custom_configuration(self):
        """Test custom configuration."""
        config = TranscriptionConfig(
            backend="whisper",
            language="es",
            model_size="large",
            chunk_duration=2.0,
            confidence_threshold=0.8,
            sample_rate=48000,
            enable_vad=False,
            device="cuda",
            whisper_model_dir="/custom/models",
            whisper_temperature=0.2,
            pocketsphinx_audio_preprocessing="amplify",
            pocketsphinx_vad_settings="aggressive"
        )
        
        assert config.backend == "whisper"
        assert config.language == "es"
        assert config.model_size == "large"
        assert config.chunk_duration == 2.0
        assert config.confidence_threshold == 0.8
        assert config.sample_rate == 48000
        assert config.enable_vad == False
        assert config.device == "cuda"
        assert config.whisper_model_dir == "/custom/models"
        assert config.whisper_temperature == 0.2
        assert config.pocketsphinx_audio_preprocessing == "amplify"
        assert config.pocketsphinx_vad_settings == "aggressive" 