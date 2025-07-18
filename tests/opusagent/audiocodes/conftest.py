"""
Pytest configuration for AudioCodes mock client tests.

This file contains fixtures and configuration specific to the AudioCodes
mock client test suite.
"""

import pytest
import logging
import tempfile
import os
from pathlib import Path


@pytest.fixture(scope="session")
def test_audio_files():
    """Create test audio files for the entire test session."""
    files = []
    try:
        for i in range(5):  # Create 5 test files
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                # Create a simple WAV file with 1 second of silence
                import wave
                with wave.open(temp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(16000)  # 16kHz
                    wav_file.writeframes(bytes([0] * 32000))  # 1 second of silence
                files.append(temp_file.name)
        yield files
    finally:
        # Cleanup
        for file in files:
            if os.path.exists(file):
                os.unlink(file)


@pytest.fixture(scope="session")
def test_audio_file_8khz():
    """Create a test audio file with 8kHz sample rate for resampling tests."""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        # Create a simple WAV file with 1 second of silence at 8kHz
        import wave
        with wave.open(temp_file.name, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(8000)  # 8kHz
            wav_file.writeframes(bytes([0] * 16000))  # 1 second of silence
        yield temp_file.name
        
        # Cleanup
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


@pytest.fixture(scope="session")
def test_output_dir():
    """Create a test output directory for saving audio files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture(autouse=True)
def setup_logging():
    """Set up logging for tests."""
    # Configure logging to be quiet during tests
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    yield


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    from unittest.mock import Mock
    return pytest.MonkeyPatch().setattr('logging.getLogger', lambda: Mock())


# Markers for different test types
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "audio: mark test as audio processing test"
    )
    config.addinivalue_line(
        "markers", "websocket: mark test as websocket communication test"
    ) 