"""
Unit tests for AudioCodes mock client audio manager.

This module tests the audio file handling, chunking, and caching functionality
for the AudioCodes mock client.
"""

import pytest
import tempfile
import wave
import os
import base64
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from opusagent.mock.audiocodes.audio_manager import AudioManager


class TestAudioManager:
    """Test AudioManager class."""

    @pytest.fixture
    def audio_manager(self):
        """Create a test audio manager."""
        return AudioManager()

    @pytest.fixture
    def temp_wav_file(self):
        """Create a temporary WAV file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Create a simple WAV file with 1 second of silence
            sample_rate = 16000
            duration = 1.0
            num_samples = int(sample_rate * duration)
            
            with wave.open(temp_file.name, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                # Write silence (zeros)
                wav_file.writeframes(bytes([0] * num_samples * 2))
            
            yield temp_file.name
            
            # Cleanup
            os.unlink(temp_file.name)

    @pytest.fixture
    def temp_wav_file_8khz(self):
        """Create a temporary WAV file with 8kHz sample rate for testing resampling."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Create a simple WAV file with 1 second of silence at 8kHz
            sample_rate = 8000
            duration = 1.0
            num_samples = int(sample_rate * duration)
            
            with wave.open(temp_file.name, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                # Write silence (zeros)
                wav_file.writeframes(bytes([0] * num_samples * 2))
            
            yield temp_file.name
            
            # Cleanup
            os.unlink(temp_file.name)

    def test_audio_manager_initialization(self, audio_manager):
        """Test AudioManager initialization."""
        assert audio_manager.logger is not None
        assert audio_manager._audio_cache == {}
        assert audio_manager._metadata_cache == {}

    def test_audio_manager_with_custom_logger(self):
        """Test AudioManager initialization with custom logger."""
        custom_logger = Mock()
        audio_manager = AudioManager(custom_logger)
        
        assert audio_manager.logger == custom_logger

    def test_load_audio_chunks_success(self, audio_manager, temp_wav_file):
        """Test successful audio file loading and chunking."""
        chunks = audio_manager.load_audio_chunks(temp_wav_file)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(len(chunk) > 0 for chunk in chunks)
        
        # Verify chunks are base64 encoded
        for chunk in chunks:
            try:
                base64.b64decode(chunk)
            except Exception:
                pytest.fail(f"Chunk is not valid base64: {chunk}")

    def test_load_audio_chunks_with_custom_chunk_size(self, audio_manager, temp_wav_file):
        """Test audio loading with custom chunk size."""
        chunk_size = 16000  # 1 second at 16kHz, 16-bit, mono
        chunks = audio_manager.load_audio_chunks(temp_wav_file, chunk_size=chunk_size)
        
        assert len(chunks) > 0
        
        # Verify chunk sizes (except possibly the last one)
        for i, chunk in enumerate(chunks[:-1]):
            decoded_size = len(base64.b64decode(chunk))
            assert decoded_size >= chunk_size

    def test_load_audio_chunks_with_resampling(self, audio_manager, temp_wav_file_8khz):
        """Test audio loading with resampling from 8kHz to 16kHz."""
        chunks = audio_manager.load_audio_chunks(temp_wav_file_8khz, target_sample_rate=16000)
        
        assert len(chunks) > 0
        
        # Verify the file was processed (should be in cache)
        cache_key = f"{temp_wav_file_8khz}:16000:32000"
        assert cache_key in audio_manager._audio_cache

    def test_load_audio_chunks_file_not_found(self, audio_manager):
        """Test loading non-existent audio file."""
        with pytest.raises(FileNotFoundError):
            audio_manager.load_audio_chunks("nonexistent_file.wav")

    def test_load_audio_chunks_caching(self, audio_manager, temp_wav_file):
        """Test audio file caching functionality."""
        # Load file first time
        chunks1 = audio_manager.load_audio_chunks(temp_wav_file)
        
        # Load file second time (should use cache)
        chunks2 = audio_manager.load_audio_chunks(temp_wav_file)
        
        assert chunks1 == chunks2
        assert len(audio_manager._audio_cache) == 1

    def test_load_audio_chunks_different_parameters(self, audio_manager, temp_wav_file):
        """Test that different parameters create different cache entries."""
        # Load with default parameters
        chunks1 = audio_manager.load_audio_chunks(temp_wav_file)
        
        # Load with different chunk size
        chunks2 = audio_manager.load_audio_chunks(temp_wav_file, chunk_size=16000)
        
        # Should be different cache entries
        assert len(audio_manager._audio_cache) == 2
        assert chunks1 != chunks2

    def test_chunk_audio_data(self, audio_manager):
        """Test audio data chunking."""
        # Create test audio data (1 second of silence at 16kHz, 16-bit, mono)
        audio_data = bytes([0] * 32000)  # 1 second of silence
        
        chunks = audio_manager._chunk_audio_data(audio_data, chunk_size=16000)
        
        assert len(chunks) == 2  # Should be 2 chunks of 16KB each
        assert all(isinstance(chunk, str) for chunk in chunks)
        
        # Verify total data size
        total_decoded = b""
        for chunk in chunks:
            total_decoded += base64.b64decode(chunk)
        
        assert len(total_decoded) >= len(audio_data)

    def test_chunk_audio_data_minimum_chunk_size(self, audio_manager):
        """Test that minimum chunk size is enforced."""
        # Create small audio data
        audio_data = bytes([0] * 1000)  # Very small
        
        chunks = audio_manager._chunk_audio_data(audio_data, chunk_size=1000)
        
        # Should be padded to minimum size (100ms at 16kHz, 16-bit, mono = 3200 bytes)
        min_chunk_size = int(0.1 * 16000 * 2)
        
        for chunk in chunks:
            decoded_size = len(base64.b64decode(chunk))
            assert decoded_size >= min_chunk_size

    def test_save_audio_chunks_success(self, audio_manager):
        """Test saving audio chunks to WAV file."""
        # Create test chunks
        test_audio_data = bytes([0] * 32000)  # 1 second of silence
        chunks = [base64.b64encode(test_audio_data).decode('utf-8')]
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            success = audio_manager.save_audio_chunks(chunks, output_path)
            
            assert success is True
            assert os.path.exists(output_path)
            
            # Verify the saved file
            with wave.open(output_path, 'rb') as wav_file:
                assert wav_file.getnchannels() == 1  # Mono
                assert wav_file.getsampwidth() == 2  # 16-bit
                assert wav_file.getframerate() == 16000  # 16kHz
                
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_save_audio_chunks_empty_chunks(self, audio_manager):
        """Test saving empty chunks list."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            success = audio_manager.save_audio_chunks([], output_path)
            
            assert success is True
            assert os.path.exists(output_path)
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_save_audio_chunks_error_handling(self, audio_manager):
        """Test error handling when saving audio chunks."""
        chunks = ["invalid_base64_data"]
        
        # Try to save to a directory that doesn't exist
        success = audio_manager.save_audio_chunks(chunks, "/nonexistent/path/test.wav")
        
        assert success is False

    def test_create_silence_chunks(self, audio_manager):
        """Test creating silence audio chunks."""
        duration = 2.0
        chunks = audio_manager.create_silence_chunks(duration=duration)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        
        # Verify total duration
        total_decoded = b""
        for chunk in chunks:
            total_decoded += base64.b64decode(chunk)
        
        expected_size = int(duration * 16000 * 2)  # 2 seconds at 16kHz, 16-bit, mono
        assert len(total_decoded) >= expected_size

    def test_get_audio_info_success(self, audio_manager, temp_wav_file):
        """Test getting audio file information."""
        info = audio_manager.get_audio_info(temp_wav_file)
        
        assert info is not None
        assert info["channels"] == 1
        assert info["sample_width"] == 2
        assert info["frame_rate"] == 16000
        assert info["duration"] == 1.0
        assert info["file_size"] > 0

    def test_get_audio_info_file_not_found(self, audio_manager):
        """Test getting info for non-existent file."""
        info = audio_manager.get_audio_info("nonexistent_file.wav")
        
        assert info is None

    def test_clear_cache(self, audio_manager, temp_wav_file):
        """Test clearing the audio cache."""
        # Load a file to populate cache
        audio_manager.load_audio_chunks(temp_wav_file)
        
        assert len(audio_manager._audio_cache) > 0
        assert len(audio_manager._metadata_cache) > 0
        
        # Clear cache
        audio_manager.clear_cache()
        
        assert len(audio_manager._audio_cache) == 0
        assert len(audio_manager._metadata_cache) == 0

    def test_get_cache_info(self, audio_manager, temp_wav_file):
        """Test getting cache information."""
        # Initially empty
        cache_info = audio_manager.get_cache_info()
        assert cache_info["cached_files"] == 0
        assert cache_info["total_bytes"] == 0
        assert cache_info["average_bytes_per_file"] == 0
        
        # Load a file
        audio_manager.load_audio_chunks(temp_wav_file)
        
        cache_info = audio_manager.get_cache_info()
        assert cache_info["cached_files"] == 1
        assert cache_info["total_bytes"] > 0
        assert cache_info["average_bytes_per_file"] > 0

    def test_is_cached(self, audio_manager, temp_wav_file):
        """Test checking if file is cached."""
        # Initially not cached
        assert audio_manager.is_cached(temp_wav_file) is False
        
        # Load file
        audio_manager.load_audio_chunks(temp_wav_file)
        
        # Should be cached
        assert audio_manager.is_cached(temp_wav_file) is True

    def test_is_cached_different_sample_rate(self, audio_manager, temp_wav_file):
        """Test caching with different sample rates."""
        # Load with default sample rate
        audio_manager.load_audio_chunks(temp_wav_file, target_sample_rate=16000)
        
        # Should not be cached for different sample rate
        assert audio_manager.is_cached(temp_wav_file, target_sample_rate=8000) is False

    def test_remove_from_cache(self, audio_manager, temp_wav_file):
        """Test removing file from cache."""
        # Load file
        audio_manager.load_audio_chunks(temp_wav_file)
        
        # Should be cached
        assert audio_manager.is_cached(temp_wav_file) is True
        
        # Remove from cache
        removed = audio_manager.remove_from_cache(temp_wav_file)
        
        assert removed is True
        assert audio_manager.is_cached(temp_wav_file) is False

    def test_remove_from_cache_not_cached(self, audio_manager):
        """Test removing non-cached file."""
        removed = audio_manager.remove_from_cache("nonexistent_file.wav")
        
        assert removed is False

    @patch('opusagent.mock.audiocodes.audio_manager.wave.open')
    def test_load_audio_chunks_wave_error(self, mock_wave_open, audio_manager):
        """Test handling wave file errors."""
        mock_wave_open.side_effect = Exception("Wave file error")
        
        with pytest.raises(Exception):
            audio_manager.load_audio_chunks("test.wav")

    @patch('opusagent.mock.audiocodes.audio_manager.signal.resample')
    def test_load_audio_chunks_resampling_error(self, mock_resample, audio_manager, temp_wav_file_8khz):
        """Test handling resampling errors."""
        mock_resample.side_effect = Exception("Resampling error")
        
        with pytest.raises(Exception):
            audio_manager.load_audio_chunks(temp_wav_file_8khz, target_sample_rate=16000)

    def test_load_audio_chunks_with_metadata_cache(self, audio_manager, temp_wav_file):
        """Test that metadata is cached correctly."""
        # Load file
        audio_manager.load_audio_chunks(temp_wav_file)
        
        # Check metadata cache
        cache_key = f"{temp_wav_file}:16000:32000"
        assert cache_key in audio_manager._metadata_cache
        
        metadata = audio_manager._metadata_cache[cache_key]
        assert len(metadata) == 3  # (sample_rate, channels, sample_width)
        assert metadata[0] == 16000  # sample_rate
        assert metadata[1] == 1      # channels
        assert metadata[2] == 2      # sample_width 