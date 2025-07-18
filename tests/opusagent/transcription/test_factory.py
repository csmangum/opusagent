"""
Unit tests for transcription factory.
"""
import pytest
from unittest.mock import patch, MagicMock

from opusagent.local.transcription.factory import TranscriptionFactory
from opusagent.local.transcription.models import TranscriptionConfig
from opusagent.local.transcription.backends import PocketSphinxTranscriber, WhisperTranscriber


class TestTranscriptionFactory:
    """Test TranscriptionFactory."""

    def test_create_pocketsphinx_transcriber(self):
        """Test creating PocketSphinx transcriber."""
        config = TranscriptionConfig(backend="pocketsphinx")
        transcriber = TranscriptionFactory.create_transcriber(config)
        
        assert isinstance(transcriber, PocketSphinxTranscriber)
        assert transcriber.config == config

    def test_create_whisper_transcriber(self):
        """Test creating Whisper transcriber."""
        config = TranscriptionConfig(backend="whisper")
        transcriber = TranscriptionFactory.create_transcriber(config)
        
        assert isinstance(transcriber, WhisperTranscriber)
        assert transcriber.config == config

    def test_create_transcriber_case_insensitive(self):
        """Test creating transcriber with case insensitive backend."""
        config = TranscriptionConfig(backend="WHISPER")
        transcriber = TranscriptionFactory.create_transcriber(config)
        
        assert isinstance(transcriber, WhisperTranscriber)

    def test_create_transcriber_from_dict(self):
        """Test creating transcriber from dict config."""
        config_dict = {"backend": "pocketsphinx", "chunk_duration": 2.0}
        transcriber = TranscriptionFactory.create_transcriber(config_dict)
        
        assert isinstance(transcriber, PocketSphinxTranscriber)
        assert transcriber.config.backend == "pocketsphinx"
        assert transcriber.config.chunk_duration == 2.0

    def test_create_transcriber_invalid_backend(self):
        """Test creating transcriber with invalid backend."""
        with pytest.raises(ValueError, match="Unsupported transcription backend: invalid"):
            config = TranscriptionConfig(backend="invalid")
            # Override validation for testing
            config.backend = "invalid"
            TranscriptionFactory.create_transcriber(config)

    def test_create_transcriber_from_invalid_dict(self):
        """Test creating transcriber from dict with invalid config."""
        with pytest.raises(ValueError):
            config_dict = {"backend": "invalid_backend"}
            TranscriptionFactory.create_transcriber(config_dict)

    def test_get_available_backends_no_pocketsphinx(self):
        """Test getting available backends when PocketSphinx is not available."""
        # Mock the import to fail by patching the built-in __import__ function
        def mock_import(name, *args, **kwargs):
            if name == 'pocketsphinx':
                raise ImportError("No module named 'pocketsphinx'")
            return __import__(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            backends = TranscriptionFactory.get_available_backends()
        
        # Should still include whisper (import checked at runtime)
        assert "whisper" in backends
        # Should not include pocketsphinx when import fails
        assert "pocketsphinx" not in backends

    def test_get_available_backends_with_pocketsphinx(self):
        """Test getting available backends when PocketSphinx is available."""
        # Mock successful pocketsphinx import
        mock_pocketsphinx = MagicMock()
        with patch.dict('sys.modules', {'pocketsphinx': mock_pocketsphinx}):
            backends = TranscriptionFactory.get_available_backends()
        
        assert "pocketsphinx" in backends
        assert "whisper" in backends

    def test_get_available_backends_returns_list(self):
        """Test that get_available_backends returns a list."""
        backends = TranscriptionFactory.get_available_backends()
        assert isinstance(backends, list)
        # Whisper should always be in the list (import checked at runtime)
        assert "whisper" in backends

    def test_factory_with_custom_config(self):
        """Test factory with custom configuration."""
        config = TranscriptionConfig(
            backend="whisper",
            model_size="large",
            chunk_duration=3.0,
            confidence_threshold=0.9,
            device="cuda"
        )
        
        transcriber = TranscriptionFactory.create_transcriber(config)
        
        assert isinstance(transcriber, WhisperTranscriber)
        assert transcriber.config.model_size == "large"
        assert transcriber.config.chunk_duration == 3.0
        assert transcriber.config.confidence_threshold == 0.9
        assert transcriber.config.device == "cuda"

    def test_factory_preserves_all_config_fields(self):
        """Test that factory preserves all configuration fields."""
        config = TranscriptionConfig(
            backend="pocketsphinx",
            language="es",
            sample_rate=48000,
            pocketsphinx_audio_preprocessing="amplify",
            pocketsphinx_vad_settings="aggressive",
            pocketsphinx_auto_resample=False,
            pocketsphinx_input_sample_rate=48000,
            pocketsphinx_hmm="/custom/hmm",
            pocketsphinx_lm="/custom/lm",
            pocketsphinx_dict="/custom/dict"
        )
        
        transcriber = TranscriptionFactory.create_transcriber(config)
        
        assert transcriber.config.language == "es"
        assert transcriber.config.sample_rate == 48000
        assert transcriber.config.pocketsphinx_audio_preprocessing == "amplify"
        assert transcriber.config.pocketsphinx_vad_settings == "aggressive"
        assert transcriber.config.pocketsphinx_auto_resample == False
        assert transcriber.config.pocketsphinx_input_sample_rate == 48000
        assert transcriber.config.pocketsphinx_hmm == "/custom/hmm"
        assert transcriber.config.pocketsphinx_lm == "/custom/lm"
        assert transcriber.config.pocketsphinx_dict == "/custom/dict" 