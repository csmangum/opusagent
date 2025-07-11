#!/usr/bin/env python3
"""
Pytest configuration for VAD tests.
"""

import pytest
import numpy as np
import os
from unittest.mock import Mock, patch


@pytest.fixture
def sample_audio_data():
    """Provide sample audio data for testing."""
    # Create 512 samples of test audio (32ms at 16kHz)
    return np.random.randn(512).astype(np.float32)


@pytest.fixture
def sample_audio_bytes():
    """Provide sample audio bytes for testing."""
    import struct
    # Create 512 samples of 16-bit PCM audio
    samples = [int(32767 * 0.5 * np.sin(2 * np.pi * 440 * i / 16000)) 
               for i in range(512)]
    return struct.pack('<512h', *samples)


@pytest.fixture
def vad_config():
    """Provide a standard VAD configuration for testing."""
    return {
        'backend': 'silero',
        'sample_rate': 16000,
        'threshold': 0.5,
        'device': 'cpu',
        'chunk_size': 512
    }


@pytest.fixture
def mock_silero_model():
    """Provide a mock Silero VAD model for testing."""
    mock_model = Mock()
    mock_model.return_value.item.return_value = 0.7
    return mock_model


@pytest.fixture
def mock_silero_load():
    """Provide a mock silero-vad loader."""
    with patch('opusagent.vad.silero_vad.load_silero_vad') as mock_load:
        mock_model = Mock()
        mock_model.return_value.item.return_value = 0.7
        mock_load.return_value = mock_model
        yield mock_load


@pytest.fixture
def clean_environment():
    """Provide a clean environment for testing."""
    # Store original environment
    original_env = os.environ.copy()
    
    # Clear VAD-related environment variables
    env_vars_to_clear = [
        'VAD_BACKEND',
        'VAD_SAMPLE_RATE', 
        'VAD_CONFIDENCE_THRESHOLD',
        'VAD_DEVICE',
        'VAD_CHUNK_SIZE'
    ]
    
    for var in env_vars_to_clear:
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def test_audio_formats():
    """Provide different audio formats for testing."""
    import struct
    
    formats = {
        'int16_mono_512': {
            'data': struct.pack('<512h', *[1000] * 512),
            'sample_width': 2,
            'channels': 1,
            'expected_samples': 512
        },
        'int16_mono_256': {
            'data': struct.pack('<256h', *[500] * 256),
            'sample_width': 2,
            'channels': 1,
            'expected_samples': 256
        },
        'float32_mono_128': {
            'data': struct.pack('<128f', *[0.5] * 128),
            'sample_width': 4,
            'channels': 1,
            'expected_samples': 128
        }
    }
    
    return formats


@pytest.fixture
def vad_test_scenarios():
    """Provide different VAD test scenarios."""
    scenarios = [
        {
            'name': 'high_speech_confidence',
            'audio_energy': 0.8,
            'expected_speech_prob': 0.8,
            'expected_is_speech': True
        },
        {
            'name': 'low_speech_confidence',
            'audio_energy': 0.2,
            'expected_speech_prob': 0.2,
            'expected_is_speech': False
        },
        {
            'name': 'medium_speech_confidence',
            'audio_energy': 0.5,
            'expected_speech_prob': 0.5,
            'expected_is_speech': True  # Assuming threshold is 0.5
        }
    ]
    
    return scenarios


@pytest.fixture
def performance_thresholds():
    """Provide performance thresholds for testing."""
    return {
        'audio_conversion_ms': 1.0,  # 1ms for audio conversion
        'vad_processing_ms': 10.0,   # 10ms for VAD processing (with mock)
        'memory_multiplier': 10,     # Memory shouldn't be more than 10x input
        'result_memory_bytes': 1000  # Result dict should be small
    }


# Pytest markers for different test types
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Skip tests that require silero-vad if not available
def pytest_collection_modifyitems(config, items):
    """Skip tests that require silero-vad if not available."""
    try:
        import silero_vad
        silero_available = True
    except ImportError:
        silero_available = False
    
    skip_silero = pytest.mark.skip(reason="silero-vad not available")
    
    for item in items:
        if not silero_available and "silero" in item.name.lower():
            item.add_marker(skip_silero) 