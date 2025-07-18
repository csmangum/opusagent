"""
Unit tests for opusagent.local.realtime.audio module.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from typing import Optional

from opusagent.local.realtime.audio import AudioManager


class TestAudioManager:
    """Test AudioManager class."""

    def test_audio_manager_creation(self):
        """Test basic AudioManager creation."""
        logger = Mock()
        manager = AudioManager(logger)
        
        assert manager.logger == logger
        assert manager._audio_cache == {}
        assert manager._metadata_cache == {}

    def test_audio_manager_creation_without_logger(self):
        """Test AudioManager creation without logger."""
        manager = AudioManager()
        
        assert manager.logger is not None
        assert manager._audio_cache == {}
        assert manager._metadata_cache == {}

    @pytest.mark.asyncio
    async def test_load_audio_file_cached(self):
        """Test loading audio file that's already cached."""
        logger = Mock()
        manager = AudioManager(logger)
        
        # Pre-populate cache
        cache_key = "test_file.wav:16000"
        cached_data = b"cached_audio_data"
        manager._audio_cache[cache_key] = cached_data
        manager._metadata_cache[cache_key] = (16000, 1)
        
        # Load the file
        result = await manager.load_audio_file("test_file.wav", 16000)
        
        assert result == cached_data
        logger.debug.assert_called_with("[MOCK REALTIME] Using cached audio file: test_file.wav")

    @pytest.mark.asyncio
    @patch('opusagent.local.realtime.audio.AUDIO_UTILS_AVAILABLE', True)
    @patch('opusagent.local.realtime.audio.AudioUtils')
    async def test_load_audio_file_with_audio_utils(self, mock_audio_utils):
        """Test loading audio file with AudioUtils available."""
        logger = Mock()
        manager = AudioManager(logger)
        
        # Mock AudioUtils response
        mock_audio_utils.load_audio_file.return_value = (b"audio_data", 16000, 1)
        
        # Mock file exists
        with patch('pathlib.Path.exists', return_value=True):
            result = await manager.load_audio_file("test_file.wav", 16000)
        
        assert result == b"audio_data"
        mock_audio_utils.load_audio_file.assert_called_once_with("test_file.wav", target_sample_rate=16000)
        logger.info.assert_called_with("[MOCK REALTIME] Loaded audio file: test_file.wav (10 bytes, 16000Hz, 1ch)")

    @pytest.mark.asyncio
    @patch('opusagent.local.realtime.audio.AUDIO_UTILS_AVAILABLE', True)
    @patch('opusagent.local.realtime.audio.AudioUtils')
    async def test_load_audio_file_audio_utils_failure(self, mock_audio_utils):
        """Test loading audio file when AudioUtils fails."""
        logger = Mock()
        manager = AudioManager(logger)
        
        # Mock AudioUtils failure
        mock_audio_utils.load_audio_file.return_value = (None, 16000, 1)
        
        # Mock file exists
        with patch('pathlib.Path.exists', return_value=True):
            result = await manager.load_audio_file("test_file.wav", 16000)
        
        # Should return silence
        assert len(result) > 0
        assert all(b == 0 for b in result)
        logger.warning.assert_called_with("[MOCK REALTIME] AudioUtils failed to load: test_file.wav")

    @pytest.mark.asyncio
    @patch('opusagent.local.realtime.audio.AUDIO_UTILS_AVAILABLE', False)
    async def test_load_audio_file_fallback_mode(self):
        """Test loading audio file in fallback mode (no AudioUtils)."""
        logger = Mock()
        manager = AudioManager(logger)
        
        # Mock file exists
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = b"fallback_audio_data"
                
                result = await manager.load_audio_file("test_file.wav", 16000)
        
        assert result == b"fallback_audio_data"
        logger.info.assert_called_with("[MOCK REALTIME] Loaded audio file (fallback): test_file.wav (19 bytes)")

    @pytest.mark.asyncio
    async def test_load_audio_file_not_found(self):
        """Test loading audio file that doesn't exist."""
        logger = Mock()
        manager = AudioManager(logger)
        
        # Mock file doesn't exist
        with patch('pathlib.Path.exists', return_value=False):
            result = await manager.load_audio_file("nonexistent.wav", 16000)
        
        # Should return silence
        assert len(result) > 0
        assert all(b == 0 for b in result)
        logger.warning.assert_called_with("[MOCK REALTIME] Audio file not found: nonexistent.wav")

    @pytest.mark.asyncio
    async def test_load_audio_file_exception_handling(self):
        """Test loading audio file with exception handling."""
        logger = Mock()
        manager = AudioManager(logger)
        
        # Mock file exists but reading fails
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', side_effect=Exception("File read error")):
                result = await manager.load_audio_file("test_file.wav", 16000)
        
        # Should return silence
        assert len(result) > 0
        assert all(b == 0 for b in result)
        # The error is logged by AudioUtils, not AudioManager in this case
        # since we're in fallback mode and the exception occurs during file reading

    def test_generate_silence(self):
        """Test silence generation."""
        logger = Mock()
        manager = AudioManager(logger)
        
        # Test default silence
        silence = manager._generate_silence()
        assert len(silence) == 64000  # 2 seconds * 16000 Hz * 2 bytes
        
        # Test custom duration
        silence = manager._generate_silence(duration=1.0, sample_rate=8000)
        assert len(silence) == 16000  # 1 second * 8000 Hz * 2 bytes
        
        # Test that all bytes are zero
        assert all(b == 0 for b in silence)

    def test_clear_cache(self):
        """Test cache clearing."""
        logger = Mock()
        manager = AudioManager(logger)
        
        # Populate cache
        manager._audio_cache["key1"] = b"data1"
        manager._metadata_cache["key1"] = (16000, 1)
        
        # Clear cache
        manager.clear_cache()
        
        assert manager._audio_cache == {}
        assert manager._metadata_cache == {}
        logger.info.assert_called_with("[MOCK REALTIME] Audio cache cleared")

    def test_get_cache_size(self):
        """Test getting cache size."""
        logger = Mock()
        manager = AudioManager(logger)
        
        # Empty cache
        assert manager.get_cache_size() == 0
        
        # Populate cache
        manager._audio_cache["key1"] = b"data1"
        manager._audio_cache["key2"] = b"data2"
        
        assert manager.get_cache_size() == 2

    def test_get_cache_info(self):
        """Test getting cache information."""
        logger = Mock()
        manager = AudioManager(logger)
        
        # Empty cache
        info = manager.get_cache_info()
        assert info["cached_files"] == 0
        assert info["total_bytes"] == 0
        assert info["average_bytes_per_file"] == 0
        
        # Populate cache
        manager._audio_cache["key1"] = b"data1"  # 5 bytes
        manager._audio_cache["key2"] = b"data2"  # 5 bytes
        
        info = manager.get_cache_info()
        assert info["cached_files"] == 2
        assert info["total_bytes"] == 10
        assert info["average_bytes_per_file"] == 5

    def test_is_cached(self):
        """Test checking if file is cached."""
        logger = Mock()
        manager = AudioManager(logger)
        
        # Not cached
        assert not manager.is_cached("test_file.wav", 16000)
        
        # Add to cache
        cache_key = "test_file.wav:16000"
        manager._audio_cache[cache_key] = b"data"
        
        assert manager.is_cached("test_file.wav", 16000)
        assert not manager.is_cached("test_file.wav", 8000)  # Different sample rate

    def test_remove_from_cache(self):
        """Test removing file from cache."""
        logger = Mock()
        manager = AudioManager(logger)
        
        # Add to cache
        cache_key = "test_file.wav:16000"
        manager._audio_cache[cache_key] = b"data"
        manager._metadata_cache[cache_key] = (16000, 1)
        
        # Remove from cache
        result = manager.remove_from_cache("test_file.wav", 16000)
        assert result is True
        assert cache_key not in manager._audio_cache
        assert cache_key not in manager._metadata_cache
        logger.debug.assert_called_with("[MOCK REALTIME] Removed test_file.wav from audio cache")
        
        # Try to remove non-existent file
        result = manager.remove_from_cache("nonexistent.wav", 16000)
        assert result is False

    @pytest.mark.asyncio
    async def test_cache_integration(self):
        """Test cache integration with file loading."""
        logger = Mock()
        manager = AudioManager(logger)
        
        # Mock AudioUtils
        with patch('opusagent.local.realtime.audio.AUDIO_UTILS_AVAILABLE', True):
            with patch('opusagent.local.realtime.audio.AudioUtils') as mock_audio_utils:
                mock_audio_utils.load_audio_file.return_value = (b"audio_data", 16000, 1)
                
                # Mock file exists
                with patch('pathlib.Path.exists', return_value=True):
                    # Load file first time
                    result1 = await manager.load_audio_file("test_file.wav", 16000)
                    
                    # Load file second time (should use cache)
                    result2 = await manager.load_audio_file("test_file.wav", 16000)
                
                # Both should return same data
                assert result1 == result2 == b"audio_data"
                
                # AudioUtils should only be called once
                mock_audio_utils.load_audio_file.assert_called_once()
                
                # Check cache
                assert manager.is_cached("test_file.wav", 16000)
                assert manager.get_cache_size() == 1

    def test_different_sample_rates_caching(self):
        """Test that different sample rates are cached separately."""
        logger = Mock()
        manager = AudioManager(logger)
        
        # Add files with different sample rates
        manager._audio_cache["file.wav:16000"] = b"data_16k"
        manager._audio_cache["file.wav:8000"] = b"data_8k"
        
        assert manager.is_cached("file.wav", 16000)
        assert manager.is_cached("file.wav", 8000)
        assert not manager.is_cached("file.wav", 44100)
        assert manager.get_cache_size() == 2

    def test_audio_manager_warning_logging(self):
        """Test that warnings are logged when AudioUtils is not available."""
        with patch('opusagent.local.realtime.audio.AUDIO_UTILS_AVAILABLE', False):
            with patch('opusagent.local.realtime.audio.AudioUtils', None):
                logger = Mock()
                manager = AudioManager(logger)
                
                logger.warning.assert_called_with("[MOCK REALTIME] AudioUtils not available - using fallback mode")

    def test_silence_generation_edge_cases(self):
        """Test silence generation with edge cases."""
        logger = Mock()
        manager = AudioManager(logger)
        
        # Zero duration
        silence = manager._generate_silence(duration=0.0)
        assert len(silence) == 0
        
        # Very short duration
        silence = manager._generate_silence(duration=0.001, sample_rate=16000)
        assert len(silence) == 32  # 0.001 * 16000 * 2
        
        # High sample rate
        silence = manager._generate_silence(duration=1.0, sample_rate=48000)
        assert len(silence) == 96000  # 1 * 48000 * 2 