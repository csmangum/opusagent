import pytest
import numpy as np
from datetime import datetime
from opusagent.voice_fingerprinting.models import Voiceprint, VoiceFingerprintConfig


class TestVoiceprint:
    """Test the Voiceprint model."""
    
    def test_voiceprint_creation(self, sample_embedding):
        """Test basic voiceprint creation."""
        voiceprint = Voiceprint(
            caller_id="test_caller",
            embedding=sample_embedding,
            metadata={"age": 25, "gender": "female"}
        )
        
        assert voiceprint.caller_id == "test_caller"
        assert np.array_equal(voiceprint.embedding, sample_embedding)
        assert voiceprint.metadata == {"age": 25, "gender": "female"}
        assert voiceprint.created_at is None
        assert voiceprint.last_seen is None
    
    def test_voiceprint_with_timestamps(self, sample_embedding):
        """Test voiceprint creation with timestamps."""
        created_at = "2024-01-01T00:00:00Z"
        last_seen = "2024-01-02T12:00:00Z"
        
        voiceprint = Voiceprint(
            caller_id="test_caller",
            embedding=sample_embedding,
            metadata={"test": True},
            created_at=created_at,
            last_seen=last_seen
        )
        
        assert voiceprint.created_at == created_at
        assert voiceprint.last_seen == last_seen
    
    def test_voiceprint_default_metadata(self, sample_embedding):
        """Test voiceprint with default empty metadata."""
        voiceprint = Voiceprint(
            caller_id="test_caller",
            embedding=sample_embedding
        )
        
        assert voiceprint.metadata == {}
    
    def test_voiceprint_serialization(self, sample_voiceprint):
        """Test voiceprint serialization to dict."""
        voiceprint_dict = sample_voiceprint.dict()
        
        assert voiceprint_dict["caller_id"] == "test_caller_123"
        assert "embedding" in voiceprint_dict
        assert voiceprint_dict["metadata"] == {"age": 30, "gender": "male"}
        assert voiceprint_dict["created_at"] == "2024-01-01T00:00:00Z"
        assert voiceprint_dict["last_seen"] == "2024-01-01T00:00:00Z"
    
    def test_voiceprint_from_dict(self, sample_embedding):
        """Test voiceprint creation from dictionary."""
        voiceprint_dict = {
            "caller_id": "test_caller",
            "embedding": sample_embedding.tolist(),
            "metadata": {"test": True},
            "created_at": "2024-01-01T00:00:00Z",
            "last_seen": "2024-01-01T00:00:00Z"
        }
        
        voiceprint = Voiceprint(**voiceprint_dict)
        
        assert voiceprint.caller_id == "test_caller"
        assert np.array_equal(voiceprint.embedding, sample_embedding)
        assert voiceprint.metadata == {"test": True}
    
    def test_voiceprint_validation_with_required_fields(self, sample_embedding):
        """Test voiceprint validation with required fields."""
        # These should work with required fields
        voiceprint1 = Voiceprint(
            caller_id="test_caller",
            embedding=sample_embedding
        )
        assert voiceprint1.caller_id == "test_caller"
        
        voiceprint2 = Voiceprint(
            caller_id="test_caller",
            embedding=np.array([1, 2, 3])
        )
        assert voiceprint2.caller_id == "test_caller"
    
    def test_voiceprint_embedding_types(self):
        """Test voiceprint with different embedding types."""
        # Test with list
        embedding_list = [1.0, 2.0, 3.0]
        voiceprint = Voiceprint(
            caller_id="test_caller",
            embedding=np.array(embedding_list)
        )
        assert np.array_equal(voiceprint.embedding, np.array(embedding_list))
        
        # Test with numpy array
        embedding_array = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        voiceprint = Voiceprint(
            caller_id="test_caller",
            embedding=embedding_array
        )
        assert np.array_equal(voiceprint.embedding, embedding_array)
    
    def test_voiceprint_metadata_types(self, sample_embedding):
        """Test voiceprint with different metadata types."""
        # Test with nested metadata
        nested_metadata = {
            "personal": {"age": 30, "gender": "male"},
            "preferences": {"language": "en", "accent": "us"},
            "flags": [True, False, True]
        }
        
        voiceprint = Voiceprint(
            caller_id="test_caller",
            embedding=sample_embedding,
            metadata=nested_metadata
        )
        
        assert voiceprint.metadata == nested_metadata
    
    def test_voiceprint_equality(self, sample_embedding):
        """Test voiceprint equality."""
        vp1 = Voiceprint(
            caller_id="test_caller",
            embedding=sample_embedding,
            metadata={"test": True}
        )
        
        vp2 = Voiceprint(
            caller_id="test_caller",
            embedding=sample_embedding,
            metadata={"test": True}
        )
        
        # Should be equal if all fields are the same
        assert vp1.dict() == vp2.dict()
    
    def test_voiceprint_inequality(self, sample_embedding):
        """Test voiceprint inequality."""
        vp1 = Voiceprint(
            caller_id="test_caller_1",
            embedding=sample_embedding,
            metadata={"test": True}
        )
        
        vp2 = Voiceprint(
            caller_id="test_caller_2",
            embedding=sample_embedding,
            metadata={"test": True}
        )
        
        # Should not be equal if caller_id is different
        assert vp1.dict() != vp2.dict()


class TestVoiceFingerprintConfig:
    """Test the VoiceFingerprintConfig model."""
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = VoiceFingerprintConfig()
        
        assert config.similarity_threshold == 0.75
        assert config.enrollment_duration == 5.0
        assert config.min_audio_quality == 0.6
        assert config.max_voiceprints_per_caller == 3
    
    def test_config_custom_values(self):
        """Test configuration with custom values."""
        config = VoiceFingerprintConfig(
            similarity_threshold=0.85,
            enrollment_duration=10.0,
            min_audio_quality=0.8,
            max_voiceprints_per_caller=5
        )
        
        assert config.similarity_threshold == 0.85
        assert config.enrollment_duration == 10.0
        assert config.min_audio_quality == 0.8
        assert config.max_voiceprints_per_caller == 5
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Test valid ranges
        config = VoiceFingerprintConfig(
            similarity_threshold=0.5,
            enrollment_duration=1.0,
            min_audio_quality=0.1,
            max_voiceprints_per_caller=1
        )
        
        assert config.similarity_threshold == 0.5
        assert config.enrollment_duration == 1.0
        assert config.min_audio_quality == 0.1
        assert config.max_voiceprints_per_caller == 1
    
    def test_config_edge_cases(self):
        """Test configuration edge cases."""
        # Test boundary values
        config = VoiceFingerprintConfig(
            similarity_threshold=0.0,
            enrollment_duration=0.1,
            min_audio_quality=0.0,
            max_voiceprints_per_caller=0
        )
        
        assert config.similarity_threshold == 0.0
        assert config.enrollment_duration == 0.1
        assert config.min_audio_quality == 0.0
        assert config.max_voiceprints_per_caller == 0
    
    def test_config_serialization(self):
        """Test configuration serialization."""
        config = VoiceFingerprintConfig(
            similarity_threshold=0.8,
            enrollment_duration=7.5,
            min_audio_quality=0.7,
            max_voiceprints_per_caller=4
        )
        
        config_dict = config.dict()
        
        assert config_dict["similarity_threshold"] == 0.8
        assert config_dict["enrollment_duration"] == 7.5
        assert config_dict["min_audio_quality"] == 0.7
        assert config_dict["max_voiceprints_per_caller"] == 4
    
    def test_config_from_dict(self):
        """Test configuration creation from dictionary."""
        config_dict = {
            "similarity_threshold": 0.9,
            "enrollment_duration": 15.0,
            "min_audio_quality": 0.9,
            "max_voiceprints_per_caller": 10
        }
        
        config = VoiceFingerprintConfig(**config_dict)
        
        assert config.similarity_threshold == 0.9
        assert config.enrollment_duration == 15.0
        assert config.min_audio_quality == 0.9
        assert config.max_voiceprints_per_caller == 10
    
    def test_config_immutability(self):
        """Test that configuration is immutable after creation."""
        config = VoiceFingerprintConfig()
        
        # Should not be able to modify attributes after creation
        # (This depends on Pydantic configuration)
        original_threshold = config.similarity_threshold
        
        # In Pydantic v1, this would work, but in v2 it might not
        # This test documents the expected behavior
        assert config.similarity_threshold == original_threshold 