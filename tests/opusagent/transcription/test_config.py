"""
Unit tests for transcription configuration loading.
"""
import os
import pytest
from unittest.mock import patch

from opusagent.local.transcription.config import load_transcription_config
from opusagent.local.transcription.models import TranscriptionConfig


class TestTranscriptionConfig:
    """Test transcription configuration loading."""

    def test_load_default_config(self):
        """Test loading configuration with all defaults."""
        env_vars = {"OPUSAGENT_USE_MOCK": "true"}
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_transcription_config()
        
        assert isinstance(config, TranscriptionConfig)
        assert config.backend == "pocketsphinx"  # Default from constants
        assert config.language == "en"
        assert config.model_size == "base"
        assert config.chunk_duration == 1.0
        assert config.confidence_threshold == 0.5
        assert config.sample_rate == 16000
        assert config.enable_vad == True
        assert config.device == "cpu"

    def test_load_config_from_environment(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            "OPUSAGENT_USE_MOCK": "true",
            "TRANSCRIPTION_BACKEND": "whisper",
            "TRANSCRIPTION_LANGUAGE": "es",
            "WHISPER_MODEL_SIZE": "large",
            "TRANSCRIPTION_CHUNK_DURATION": "2.5",
            "TRANSCRIPTION_CONFIDENCE_THRESHOLD": "0.8",
            "TRANSCRIPTION_SAMPLE_RATE": "48000",
            "TRANSCRIPTION_ENABLE_VAD": "false",
            "WHISPER_DEVICE": "cuda",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_transcription_config()
        
        assert config.backend == "whisper"
        assert config.language == "es"
        assert config.model_size == "large"
        assert config.chunk_duration == 2.5
        assert config.confidence_threshold == 0.8
        assert config.sample_rate == 48000
        assert config.enable_vad == False
        assert config.device == "cuda"

    def test_load_pocketsphinx_config(self):
        """Test loading PocketSphinx specific configuration."""
        env_vars = {
            "OPUSAGENT_USE_MOCK": "true",
            "TRANSCRIPTION_BACKEND": "pocketsphinx",
            "POCKETSPHINX_HMM": "/custom/hmm",
            "POCKETSPHINX_LM": "/custom/lm", 
            "POCKETSPHINX_DICT": "/custom/dict",
            "POCKETSPHINX_AUDIO_PREPROCESSING": "amplify",
            "POCKETSPHINX_VAD_SETTINGS": "aggressive",
            "POCKETSPHINX_AUTO_RESAMPLE": "false",
            "POCKETSPHINX_INPUT_SAMPLE_RATE": "48000",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_transcription_config()
        
        assert config.backend == "pocketsphinx"
        assert config.pocketsphinx_hmm == "/custom/hmm"
        assert config.pocketsphinx_lm == "/custom/lm"
        assert config.pocketsphinx_dict == "/custom/dict"
        assert config.pocketsphinx_audio_preprocessing == "amplify"
        assert config.pocketsphinx_vad_settings == "aggressive"
        assert config.pocketsphinx_auto_resample == False
        assert config.pocketsphinx_input_sample_rate == 48000

    def test_load_whisper_config(self):
        """Test loading Whisper specific configuration."""
        env_vars = {
            "OPUSAGENT_USE_MOCK": "true",
            "TRANSCRIPTION_BACKEND": "whisper",
            "WHISPER_MODEL_DIR": "/custom/models",
            "WHISPER_TEMPERATURE": "0.3",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_transcription_config()
        
        assert config.backend == "whisper"
        assert config.whisper_model_dir == "/custom/models"
        assert config.whisper_temperature == 0.3

    def test_load_config_partial_environment(self):
        """Test loading configuration with partial environment variables."""
        env_vars = {
            "OPUSAGENT_USE_MOCK": "true",
            "TRANSCRIPTION_BACKEND": "whisper",
            "TRANSCRIPTION_CHUNK_DURATION": "3.0",
            # Other values should use defaults
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_transcription_config()
        
        assert config.backend == "whisper"
        assert config.chunk_duration == 3.0
        # Check that defaults are still used for unspecified values
        assert config.language == "en"
        assert config.confidence_threshold == 0.5
        assert config.sample_rate == 16000

    def test_load_config_boolean_parsing(self):
        """Test boolean environment variable parsing."""
        env_vars = {
            "OPUSAGENT_USE_MOCK": "true",
            "TRANSCRIPTION_ENABLE_VAD": "false",
            "POCKETSPHINX_AUTO_RESAMPLE": "true",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_transcription_config()
        
        assert config.enable_vad == False
        assert config.pocketsphinx_auto_resample == True

    def test_load_config_numeric_parsing(self):
        """Test numeric environment variable parsing."""
        env_vars = {
            "OPUSAGENT_USE_MOCK": "true",
            "TRANSCRIPTION_CHUNK_DURATION": "2.5",
            "TRANSCRIPTION_CONFIDENCE_THRESHOLD": "0.75",
            "TRANSCRIPTION_SAMPLE_RATE": "48000",
            "POCKETSPHINX_INPUT_SAMPLE_RATE": "24000",
            "WHISPER_TEMPERATURE": "0.2",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_transcription_config()
        
        assert config.chunk_duration == 2.5
        assert config.confidence_threshold == 0.75
        assert config.sample_rate == 48000
        assert config.pocketsphinx_input_sample_rate == 24000
        assert config.whisper_temperature == 0.2

    def test_load_config_with_none_values(self):
        """Test loading configuration with None values."""
        env_vars = {
            "OPUSAGENT_USE_MOCK": "true",
            "POCKETSPHINX_HMM": "",
            "POCKETSPHINX_LM": "",
            "POCKETSPHINX_DICT": "",
            "WHISPER_MODEL_DIR": "",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_transcription_config()
        
        # Empty strings should result in None values
        assert config.pocketsphinx_hmm is None
        assert config.pocketsphinx_lm is None
        assert config.pocketsphinx_dict is None
        assert config.whisper_model_dir is None

    def test_config_validation_still_applies(self):
        """Test that configuration validation still applies."""
        env_vars = {
            "OPUSAGENT_USE_MOCK": "true",
            "TRANSCRIPTION_CONFIDENCE_THRESHOLD": "1.5",  # Invalid: > 1.0
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="confidence threshold"):
                load_transcription_config()

    def test_config_defaults_from_constants(self):
        """Test that configuration defaults come from constants."""
        env_vars = {"OPUSAGENT_USE_MOCK": "true"}
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_transcription_config()
        
        # These should match the defaults in TranscriptionConfig
        assert config.backend == "pocketsphinx"
        assert config.language == "en"
        assert config.model_size == "base"
        assert config.chunk_duration == 1.0
        assert config.confidence_threshold == 0.5
        assert config.sample_rate == 16000
        assert config.enable_vad == True
        assert config.device == "cpu"

    def test_load_config_returns_valid_instance(self):
        """Test that load_config returns a valid TranscriptionConfig instance."""
        env_vars = {"OPUSAGENT_USE_MOCK": "true"}
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_transcription_config()
        
        assert isinstance(config, TranscriptionConfig)
        # Test that the config can be used (no validation errors)
        assert config.backend in ["pocketsphinx", "whisper"]
        assert 0 <= config.confidence_threshold <= 1
        assert config.sample_rate > 0 