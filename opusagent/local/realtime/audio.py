"""
Audio management for the LocalRealtime module.

This module provides a high-performance audio caching and management system for the
LocalRealtimeClient, which simulates the OpenAI Realtime API. It wraps the existing
AudioUtils with intelligent caching to improve response times and reduce I/O overhead.

Key Features:
- Audio File Caching: Intelligent caching of loaded audio files with metadata
- Format Support: Leverages AudioUtils for multi-format audio processing
- Fallback Handling: Graceful degradation with silence generation when files are unavailable
- Performance Optimization: Reduces repeated file I/O operations through caching
- Memory Management: Cache size monitoring and manual cache control

Core Components:
- AudioManager: Main class providing audio loading, caching, and management
- Cache Management: Automatic and manual cache control with statistics
- Error Handling: Robust error handling with fallback to silence generation
- Metadata Tracking: Sample rate and channel information caching

Supported Operations:
- load_audio_file(): Load and cache audio files with resampling
- clear_cache(): Remove all cached audio data
- get_cache_info(): Retrieve cache statistics and memory usage
- is_cached(): Check if a file is currently cached
- remove_from_cache(): Remove specific files from cache

The module is designed to work seamlessly with the LocalRealtimeClient, providing
fast audio responses for mock conversations while maintaining compatibility with
the existing AudioUtils infrastructure.

Usage:
    audio_manager = AudioManager(logger)
    audio_data = await audio_manager.load_audio_file("audio/greeting.wav", 16000)
    cache_info = audio_manager.get_cache_info()
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

# Import the existing audio utilities
try:
    from opusagent.utils.audio_utils import AudioUtils

    AUDIO_UTILS_AVAILABLE = True
except ImportError:
    AUDIO_UTILS_AVAILABLE = False
    AudioUtils = None


class AudioManager:
    """
    Caching wrapper around AudioUtils for mock responses.

    This class provides efficient audio file handling with caching for
    improved performance, using the existing AudioUtils for actual processing.

    Attributes:
        logger (logging.Logger): Logger instance for debugging
        _audio_cache (Dict[str, bytes]): Cache for loaded audio files
        _metadata_cache (Dict[str, Tuple[int, int]]): Cache for audio metadata
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
        self._metadata_cache: Dict[str, Tuple[int, int]] = {}  # (sample_rate, channels)

        if not AUDIO_UTILS_AVAILABLE:
            self.logger.warning(
                "[MOCK REALTIME] AudioUtils not available - using fallback mode"
            )

    async def load_audio_file(
        self, file_path: str, target_sample_rate: int = 16000
    ) -> bytes:
        """
        Load an audio file and cache it for future use.

        This method uses AudioUtils for loading and processing, with caching
        for improved performance. If the file doesn't exist or can't be loaded,
        it falls back to generating silence.

        Args:
            file_path (str): Path to the audio file to load.
            target_sample_rate (int): Target sample rate for conversion.

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
            - Uses AudioUtils for format support and resampling
            - Falls back to silence if file not found or loading fails
            - Logs warnings and errors for debugging
        """
        cache_key = f"{file_path}:{target_sample_rate}"

        if cache_key in self._audio_cache:
            self.logger.debug(f"[MOCK REALTIME] Using cached audio file: {file_path}")
            return self._audio_cache[cache_key]

        try:
            path = Path(file_path)
            if not path.exists():
                self.logger.warning(
                    f"[MOCK REALTIME] Audio file not found: {file_path}"
                )
                return self._generate_silence()

            if AUDIO_UTILS_AVAILABLE and AudioUtils:
                # Use AudioUtils for loading and processing
                audio_data, sample_rate, channels = AudioUtils.load_audio_file(
                    file_path, target_sample_rate=target_sample_rate
                )

                if not audio_data:
                    self.logger.warning(
                        f"[MOCK REALTIME] AudioUtils failed to load: {file_path}"
                    )
                    return self._generate_silence()

                # Cache the result
                self._audio_cache[cache_key] = audio_data
                self._metadata_cache[cache_key] = (sample_rate, channels)

                self.logger.info(
                    f"[MOCK REALTIME] Loaded audio file: {file_path} ({len(audio_data)} bytes, {sample_rate}Hz, {channels}ch)"
                )
                return audio_data
            else:
                # Fallback to basic file loading
                with open(path, "rb") as f:
                    audio_data = f.read()
                    self._audio_cache[cache_key] = audio_data
                    self._metadata_cache[cache_key] = (target_sample_rate, 1)
                    self.logger.info(
                        f"[MOCK REALTIME] Loaded audio file (fallback): {file_path} ({len(audio_data)} bytes)"
                    )
                    return audio_data

        except Exception as e:
            self.logger.error(
                f"[MOCK REALTIME] Error loading audio file {file_path}: {e}"
            )
            return self._generate_silence()

    def _generate_silence(
        self, duration: float = 2.0, sample_rate: int = 16000
    ) -> bytes:
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
        self._metadata_cache.clear()
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
            "average_bytes_per_file": (
                total_size // len(self._audio_cache) if self._audio_cache else 0
            ),
        }

    def is_cached(self, file_path: str, target_sample_rate: int = 16000) -> bool:
        """
        Check if a file is currently cached.

        Args:
            file_path (str): Path to the audio file to check.
            target_sample_rate (int): Target sample rate to check.

        Returns:
            bool: True if the file is cached, False otherwise.
        """
        cache_key = f"{file_path}:{target_sample_rate}"
        return cache_key in self._audio_cache

    def remove_from_cache(
        self, file_path: str, target_sample_rate: int = 16000
    ) -> bool:
        """
        Remove a specific file from the cache.

        Args:
            file_path (str): Path to the audio file to remove.
            target_sample_rate (int): Target sample rate to remove.

        Returns:
            bool: True if the file was removed, False if it wasn't cached.
        """
        cache_key = f"{file_path}:{target_sample_rate}"
        if cache_key in self._audio_cache:
            del self._audio_cache[cache_key]
            if cache_key in self._metadata_cache:
                del self._metadata_cache[cache_key]
            self.logger.debug(f"[MOCK REALTIME] Removed {file_path} from audio cache")
            return True
        return False
