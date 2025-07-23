"""
Shared fixtures and configuration for transcription tests.
"""
import pytest
import numpy as np
from unittest.mock import MagicMock

from opusagent.local.transcription.models import TranscriptionConfig


@pytest.fixture
def sample_config():
    """Provide a sample TranscriptionConfig for testing."""
    return TranscriptionConfig(
        backend="pocketsphinx",
        chunk_duration=1.0,
        sample_rate=16000,
        confidence_threshold=0.5
    )


@pytest.fixture
def whisper_config():
    """Provide a Whisper-specific TranscriptionConfig for testing."""
    return TranscriptionConfig(
        backend="whisper",
        model_size="base",
        chunk_duration=2.0,
        device="cpu",
        whisper_temperature=0.0
    )


@pytest.fixture
def sample_audio_data():
    """Provide sample 16-bit PCM audio data for testing."""
    # Generate 1 second of test audio at 16kHz
    duration = 1.0
    sample_rate = 16000
    samples = int(duration * sample_rate)
    
    # Create a simple sine wave
    t = np.linspace(0, duration, samples, False)
    frequency = 440.0  # A4 note
    audio_float = np.sin(2 * np.pi * frequency * t) * 0.3  # 30% amplitude
    
    # Convert to 16-bit PCM
    audio_int16 = (audio_float * 32767).astype(np.int16)
    return audio_int16.tobytes()


@pytest.fixture
def mock_pocketsphinx():
    """Provide a mock PocketSphinx module for testing."""
    mock_pocketsphinx = MagicMock()
    mock_decoder = MagicMock()
    mock_config = MagicMock()
    mock_hyp = MagicMock()
    
    # Set up the mock hierarchy
    mock_pocketsphinx.Decoder.default_config.return_value = mock_config
    mock_pocketsphinx.Decoder.return_value = mock_decoder
    mock_hyp.hypstr = "test transcription"
    mock_hyp.prob = 0.85
    mock_decoder.hyp.return_value = mock_hyp
    
    return mock_pocketsphinx


@pytest.fixture
def mock_whisper():
    """Provide a mock Whisper module for testing."""
    mock_whisper = MagicMock()
    mock_model = MagicMock()
    
    # Set up transcription result
    mock_result = {
        "text": "test transcription",
        "segments": [
            {
                "start": 0.0,
                "end": 2.0,
                "text": "test transcription",
                "avg_logprob": -0.1
            }
        ]
    }
    
    mock_whisper.load_model.return_value = mock_model
    mock_model.transcribe.return_value = mock_result
    
    return mock_whisper


@pytest.fixture
def empty_env(monkeypatch):
    """Provide an empty environment for configuration testing."""
    # Remove all environment variables that might affect transcription config
    env_vars_to_clear = [
        "TRANSCRIPTION_BACKEND",
        "TRANSCRIPTION_LANGUAGE",
        "WHISPER_MODEL_SIZE",
        "TRANSCRIPTION_CHUNK_DURATION",
        "TRANSCRIPTION_CONFIDENCE_THRESHOLD",
        "TRANSCRIPTION_SAMPLE_RATE",
        "TRANSCRIPTION_ENABLE_VAD",
        "WHISPER_DEVICE",
        "POCKETSPHINX_HMM",
        "POCKETSPHINX_LM",
        "POCKETSPHINX_DICT",
        "POCKETSPHINX_AUDIO_PREPROCESSING",
        "POCKETSPHINX_VAD_SETTINGS",
        "POCKETSPHINX_AUTO_RESAMPLE",
        "POCKETSPHINX_INPUT_SAMPLE_RATE",
        "WHISPER_MODEL_DIR",
        "WHISPER_TEMPERATURE",
    ]
    
    for var in env_vars_to_clear:
        monkeypatch.delenv(var, raising=False)


# Test configuration for pytest
def pytest_configure(config):
    """Configure pytest for transcription tests."""
    # Add custom markers if needed
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    ) 