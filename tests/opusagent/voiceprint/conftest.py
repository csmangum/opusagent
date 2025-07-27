import pytest
import numpy as np
import tempfile
import os
from unittest.mock import Mock, patch
from opusagent.voiceprint.models import Voiceprint, VoiceFingerprintConfig
from opusagent.voiceprint.storage import JSONStorage, SQLiteStorage
from opusagent.voiceprint.recognizer import OpusAgentVoiceRecognizer


@pytest.fixture
def sample_audio_buffer():
    """Generate a sample audio buffer for testing."""
    return np.random.rand(16000).astype(np.float32)  # 1 second at 16kHz


@pytest.fixture
def sample_embedding():
    """Generate a sample voice embedding."""
    return np.random.rand(256).astype(np.float32)


@pytest.fixture
def sample_voiceprint(sample_embedding):
    """Create a sample voiceprint."""
    return Voiceprint(
        caller_id="test_caller_123",
        embedding=sample_embedding,
        metadata={"age": 30, "gender": "male"},
        created_at="2024-01-01T00:00:00Z",
        last_seen="2024-01-01T00:00:00Z"
    )


@pytest.fixture
def sample_voiceprint_config():
    """Create a sample voice fingerprint config."""
    return VoiceFingerprintConfig(
        similarity_threshold=0.75,
        enrollment_duration=5.0,
        min_audio_quality=0.6,
        max_voiceprints_per_caller=3
    )


@pytest.fixture
def temp_json_storage():
    """Create a temporary JSON storage for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
    
    storage = JSONStorage(temp_file)
    yield storage
    
    # Cleanup
    try:
        os.unlink(temp_file)
    except FileNotFoundError:
        pass


@pytest.fixture
def temp_sqlite_storage():
    """Create a temporary SQLite storage for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db = f.name
    
    storage = SQLiteStorage(temp_db)
    yield storage
    
    # Cleanup
    try:
        os.unlink(temp_db)
    except FileNotFoundError:
        pass


@pytest.fixture
def mock_voice_encoder():
    """Mock voice encoder for testing."""
    mock_encoder = Mock()
    mock_encoder.embed_utterance.return_value = np.random.rand(256).astype(np.float32)
    return mock_encoder


@pytest.fixture
def mock_recognizer(mock_voice_encoder, temp_json_storage):
    """Create a mock voice recognizer."""
    with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
        mock_encoder_class.return_value = mock_voice_encoder
        
        recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
        return recognizer


@pytest.fixture
def multiple_voiceprints(sample_embedding):
    """Create multiple voiceprints for testing."""
    embeddings = [
        sample_embedding,
        sample_embedding + 0.1,  # Slightly different
        sample_embedding + 0.5,  # More different
    ]
    
    return [
        Voiceprint(
            caller_id=f"caller_{i}",
            embedding=emb,
            metadata={"test_id": i}
        )
        for i, emb in enumerate(embeddings)
    ]


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_redis = Mock()
    mock_redis.keys.return_value = [b"voiceprint:caller_1", b"voiceprint:caller_2"]
    mock_redis.get.return_value = '{"caller_id": "test", "embedding": [0.1, 0.2]}'
    return mock_redis 