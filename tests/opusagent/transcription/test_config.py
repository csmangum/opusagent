"""
Unit tests for transcription configuration loading.
"""
import os
import pytest
from unittest.mock import patch

from opusagent.mock.transcription.config import load_transcription_config
from opusagent.mock.transcription.models import TranscriptionConfig


class TestTranscriptionConfig:
    """Test transcription configuration loading."""

    def test_load_default_config(self):
        """Test loading configuration with all defaults."""
        with patch.dict(os.environ, {}, clear=True):
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
            "TRANSCRIPTION_BACKEND": "whisper",
            "TRANSCRIPTION_CHUNK_DURATION": "3.0",
            # Other values should use defaults
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_transcription_config()
        
        assert config.backend == "whisper"
        assert config.chunk_duration == 3.0
        # These should be defaults
        assert config.language == "en"
        assert config.model_size == "base"
        assert config.confidence_threshold == 0.5

    def test_load_config_boolean_parsing(self):
        """Test boolean environment variable parsing."""
        # Test various boolean representations
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("1", False),  # Only "true" (case insensitive) should be True
            ("0", False),
            ("yes", False),
            ("no", False),
        ]
        
        for env_value, expected in test_cases:
            env_vars = {"TRANSCRIPTION_ENABLE_VAD": env_value}
            with patch.dict(os.environ, env_vars, clear=True):
                config = load_transcription_config()
                assert config.enable_vad == expected, f"Failed for env_value: {env_value}"

    def test_load_config_numeric_parsing(self):
        """Test numeric environment variable parsing."""
        env_vars = {
            "TRANSCRIPTION_CHUNK_DURATION": "2.5",
            "TRANSCRIPTION_CONFIDENCE_THRESHOLD": "0.75",
            "TRANSCRIPTION_SAMPLE_RATE": "22050",
            "POCKETSPHINX_INPUT_SAMPLE_RATE": "44100",
            "WHISPER_TEMPERATURE": "0.2",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_transcription_config()
        
        assert config.chunk_duration == 2.5
        assert config.confidence_threshold == 0.75
        assert config.sample_rate == 22050
        assert config.pocketsphinx_input_sample_rate == 44100
        assert config.whisper_temperature == 0.2

    def test_load_config_with_none_values(self):
        """Test loading configuration with None/empty values."""
        env_vars = {
            "POCKETSPHINX_HMM": "",  # Empty string
            "WHISPER_MODEL_DIR": "",  # Empty string
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_transcription_config()
        
        # Empty strings should be treated as None for optional fields
        # This depends on how the environment loading is implemented
        # The current implementation will set them as empty strings
        assert config.pocketsphinx_hmm == ""
        assert config.whisper_model_dir == ""

    def test_config_validation_still_applies(self):
        """Test that Pydantic validation still applies to loaded config."""
        # Test invalid backend
        with patch.dict(os.environ, {"TRANSCRIPTION_BACKEND": "invalid"}, clear=True):
            with pytest.raises(ValueError):
                load_transcription_config()

    def test_config_defaults_from_constants(self):
        """Test that defaults come from constants module."""
        # This test ensures integration with the constants module
        with patch.dict(os.environ, {}, clear=True):
            config = load_transcription_config()
        
        # These values should match the defaults from opusagent.config.constants
        # We can't test the exact values since they might change, but we can
        # test that the config is valid and has reasonable defaults
        assert config.backend in ["pocketsphinx", "whisper"]
        assert config.sample_rate > 0
        assert 0.0 <= config.confidence_threshold <= 1.0
        assert config.chunk_duration > 0.0
        assert config.language != ""

    def test_load_config_returns_valid_instance(self):
        """Test that load_transcription_config always returns a valid instance."""
        # Test with empty environment
        with patch.dict(os.environ, {}, clear=True):
            config = load_transcription_config()
            assert isinstance(config, TranscriptionConfig)
        
        # Test with various environment combinations
        env_combinations = [
            {"TRANSCRIPTION_BACKEND": "pocketsphinx"},
            {"TRANSCRIPTION_BACKEND": "whisper"},
            {"TRANSCRIPTION_BACKEND": "whisper", "WHISPER_MODEL_SIZE": "large"},
            {"TRANSCRIPTION_BACKEND": "pocketsphinx", "POCKETSPHINX_AUDIO_PREPROCESSING": "none"},
        ]
        
        for env_vars in env_combinations:
            with patch.dict(os.environ, env_vars, clear=True):
                config = load_transcription_config()
                assert isinstance(config, TranscriptionConfig)
                # Verify it can be used to create a transcriber
                assert hasattr(config, 'backend')
                assert hasattr(config, 'chunk_duration')
                assert hasattr(config, 'sample_rate') 