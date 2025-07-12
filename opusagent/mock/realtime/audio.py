"""
Audio management for the LocalRealtime module.

This module handles audio file loading, caching, and processing for the
LocalRealtimeClient. It provides utilities for working with various audio
formats and generating fallback audio data.
"""

import logging
from pathlib import Path
from typing import Dict, Optional


class AudioManager:
    """
    Manages audio file loading, caching, and processing for mock responses.
    
    This class provides efficient audio file handling with caching for
    improved performance and automatic fallback to silence for missing files.
    
    Attributes:
        logger (logging.Logger): Logger instance for debugging
        _audio_cache (Dict[str, bytes]): Cache for loaded audio files
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the AudioManager.
        
        Args:
            logger (Optional[logging.Logger]): Logger instance for debugging.
                                             If None, creates a default logger.
        """
        self.logger = logger or logging.getLogger(__name__)
        self._audio_cache: Dict[str, bytes] = {}
    
    async def load_audio_file(self, file_path: str) -> bytes:
        """
        Load an audio file and cache it for future use.
        
        This method loads audio files from disk and caches them in memory
        for improved performance. If the file doesn't exist or can't be loaded,
        it falls back to generating silence.
        
        Args:
            file_path (str): Path to the audio file to load.
        
        Returns:
            bytes: Audio data as bytes. If file loading fails, returns silence.
        
        Example:
            ```python
            audio_manager = AudioManager()
            audio_data = await audio_manager.load_audio_file("audio/greeting.wav")
            print(f"Loaded {len(audio_data)} bytes of audio data")
            ```
        
        Note:
            - Files are cached after first load for improved performance
            - Supports WAV, MP3, and other audio formats
            - Falls back to silence if file not found or loading fails
            - Logs warnings and errors for debugging
        """
        if file_path in self._audio_cache:
            self.logger.debug(f"Using cached audio file: {file_path}")
            return self._audio_cache[file_path]
        
        try:
            path = Path(file_path)
            if not path.exists():
                self.logger.warning(f"[MOCK REALTIME] Audio file not found: {file_path}")
                return self._generate_silence()
            
            with open(path, 'rb') as f:
                audio_data = f.read()
                self._audio_cache[file_path] = audio_data
                self.logger.info(f"[MOCK REALTIME] Loaded audio file: {file_path} ({len(audio_data)} bytes)")
                return audio_data
                
        except Exception as e:
            self.logger.error(f"[MOCK REALTIME] Error loading audio file {file_path}: {e}")
            return self._generate_silence()
    
    def _generate_silence(self, duration: float = 2.0, sample_rate: int = 16000) -> bytes:
        """
        Generate silence audio data for fallback scenarios.
        
        This method creates audio data consisting of silence, which is used
        as a fallback when audio files are not available or fail to load.
        
        Args:
            duration (float): Duration of silence in seconds. Default: 2.0s
            sample_rate (int): Audio sample rate in Hz. Default: 16000Hz
        
        Returns:
            bytes: Raw audio data representing silence.
        
        Note:
            - Generates 16-bit PCM audio data
            - Uses the specified sample rate and duration
            - All samples are set to 0 (silence)
        """
        num_samples = int(sample_rate * duration)
        return bytes([0] * num_samples * 2)  # 16-bit PCM
    
    def clear_cache(self) -> None:
        """
        Clear the audio file cache.
        
        This method removes all cached audio files from memory.
        Useful for freeing up memory or forcing reload of files.
        """
        self._audio_cache.clear()
        self.logger.info("[MOCK REALTIME] Audio cache cleared")
    
    def get_cache_size(self) -> int:
        """
        Get the number of cached audio files.
        
        Returns:
            int: Number of files currently cached.
        """
        return len(self._audio_cache)
    
    def get_cache_info(self) -> Dict[str, int]:
        """
        Get information about the audio cache.
        
        Returns:
            Dict[str, int]: Dictionary with cache statistics.
        """
        total_size = sum(len(data) for data in self._audio_cache.values())
        return {
            "cached_files": len(self._audio_cache),
            "total_bytes": total_size,
            "average_bytes_per_file": total_size // len(self._audio_cache) if self._audio_cache else 0
        }
    
    def is_cached(self, file_path: str) -> bool:
        """
        Check if a file is currently cached.
        
        Args:
            file_path (str): Path to the audio file to check.
        
        Returns:
            bool: True if the file is cached, False otherwise.
        """
        return file_path in self._audio_cache
    
    def remove_from_cache(self, file_path: str) -> bool:
        """
        Remove a specific file from the cache.
        
        Args:
            file_path (str): Path to the audio file to remove.
        
        Returns:
            bool: True if the file was removed, False if it wasn't cached.
        """
        if file_path in self._audio_cache:
            del self._audio_cache[file_path]
            self.logger.debug(f"Removed {file_path} from audio cache")
            return True
        return False 