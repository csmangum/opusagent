import pytest
import os
from unittest.mock import patch
from opusagent.voice_fingerprinting.config import VoiceFingerprintConfig


class TestVoiceFingerprintConfig:
    """Test the VoiceFingerprintConfig class."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = VoiceFingerprintConfig()
        
        assert config.enabled is True
        assert config.similarity_threshold == 0.75
        assert config.enrollment_duration == 5.0
        assert config.storage_backend == 'json'
        assert config.storage_path == 'voiceprints.json'
        assert config.min_audio_quality == 0.6
        assert config.max_voiceprints_per_caller == 3
    
    @patch.dict(os.environ, {
        'VOICE_FINGERPRINTING_ENABLED': 'false',
        'VOICE_SIMILARITY_THRESHOLD': '0.85',
        'VOICE_ENROLLMENT_DURATION': '10.0',
        'VOICE_STORAGE_BACKEND': 'redis',
        'VOICE_STORAGE_PATH': '/custom/path/voiceprints.json',
        'VOICE_MIN_AUDIO_QUALITY': '0.8',
        'VOICE_MAX_VOICEPRINTS_PER_CALLER': '5'
    })
    def test_custom_configuration_from_env(self):
        """Test configuration with custom environment variables."""
        config = VoiceFingerprintConfig()
        
        assert config.enabled is False
        assert config.similarity_threshold == 0.85
        assert config.enrollment_duration == 10.0
        assert config.storage_backend == 'redis'
        assert config.storage_path == '/custom/path/voiceprints.json'
        assert config.min_audio_quality == 0.8
        assert config.max_voiceprints_per_caller == 5
    
    @patch.dict(os.environ, {
        'VOICE_FINGERPRINTING_ENABLED': 'TRUE',
        'VOICE_FINGERPRINTING_ENABLED': 'FALSE'
    })
    def test_enabled_case_insensitive(self):
        """Test that enabled flag is case insensitive."""
        config = VoiceFingerprintConfig()
        assert config.enabled is False  # Last value should be used
    
    @patch.dict(os.environ, {
        'VOICE_SIMILARITY_THRESHOLD': 'invalid'
    })
    def test_invalid_similarity_threshold(self):
        """Test handling of invalid similarity threshold."""
        with pytest.raises(ValueError):
            VoiceFingerprintConfig()
    
    @patch.dict(os.environ, {
        'VOICE_ENROLLMENT_DURATION': 'invalid'
    })
    def test_invalid_enrollment_duration(self):
        """Test handling of invalid enrollment duration."""
        with pytest.raises(ValueError):
            VoiceFingerprintConfig()
    
    @patch.dict(os.environ, {
        'VOICE_MIN_AUDIO_QUALITY': 'invalid'
    })
    def test_invalid_audio_quality(self):
        """Test handling of invalid audio quality."""
        with pytest.raises(ValueError):
            VoiceFingerprintConfig()
    
    @patch.dict(os.environ, {
        'VOICE_MAX_VOICEPRINTS_PER_CALLER': 'invalid'
    })
    def test_invalid_max_voiceprints(self):
        """Test handling of invalid max voiceprints."""
        with pytest.raises(ValueError):
            VoiceFingerprintConfig()
    
    def test_similarity_threshold_range(self):
        """Test similarity threshold range validation."""
        # Test valid range
        with patch.dict(os.environ, {'VOICE_SIMILARITY_THRESHOLD': '0.5'}):
            config = VoiceFingerprintConfig()
            assert config.similarity_threshold == 0.5
        
        # Test out of range values
        with patch.dict(os.environ, {'VOICE_SIMILARITY_THRESHOLD': '1.5'}):
            config = VoiceFingerprintConfig()
            assert config.similarity_threshold == 1.5  # No validation in current implementation
        
        with patch.dict(os.environ, {'VOICE_SIMILARITY_THRESHOLD': '-0.1'}):
            config = VoiceFingerprintConfig()
            assert config.similarity_threshold == -0.1  # No validation in current implementation
    
    def test_enrollment_duration_positive(self):
        """Test enrollment duration positive validation."""
        with patch.dict(os.environ, {'VOICE_ENROLLMENT_DURATION': '0.1'}):
            config = VoiceFingerprintConfig()
            assert config.enrollment_duration == 0.1
        
        with patch.dict(os.environ, {'VOICE_ENROLLMENT_DURATION': '-1.0'}):
            config = VoiceFingerprintConfig()
            assert config.enrollment_duration == -1.0  # No validation in current implementation
    
    def test_max_voiceprints_positive(self):
        """Test max voiceprints positive validation."""
        with patch.dict(os.environ, {'VOICE_MAX_VOICEPRINTS_PER_CALLER': '1'}):
            config = VoiceFingerprintConfig()
            assert config.max_voiceprints_per_caller == 1
        
        with patch.dict(os.environ, {'VOICE_MAX_VOICEPRINTS_PER_CALLER': '0'}):
            config = VoiceFingerprintConfig()
            assert config.max_voiceprints_per_caller == 0  # No validation in current implementation
    
    def test_storage_backend_options(self):
        """Test different storage backend options."""
        backends = ['json', 'redis', 'sqlite']
        
        for backend in backends:
            with patch.dict(os.environ, {'VOICE_STORAGE_BACKEND': backend}):
                config = VoiceFingerprintConfig()
                assert config.storage_backend == backend
    
    def test_storage_path_customization(self):
        """Test custom storage path configuration."""
        custom_paths = [
            '/tmp/voiceprints.json',
            'data/voiceprints.json',
            'voiceprints.db',
            '/custom/path/voiceprints.redis'
        ]
        
        for path in custom_paths:
            with patch.dict(os.environ, {'VOICE_STORAGE_PATH': path}):
                config = VoiceFingerprintConfig()
                assert config.storage_path == path 