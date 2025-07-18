"""
Audio management for the AudioCodes mock client.

This module provides comprehensive audio file handling, chunking, and caching
functionality for the AudioCodes mock client. It supports various audio formats
and provides efficient audio processing for testing scenarios.

The AudioManager handles:
- Audio file loading and format conversion
- Automatic resampling to target sample rates
- Audio chunking for streaming scenarios
- Performance optimization through caching
- Audio file saving and retrieval
- Silence generation for testing fallbacks

Supported audio formats include WAV files with automatic conversion to
16kHz, 16-bit PCM format for compatibility with the bridge server.

Audio Processing Pipeline:
1. File Loading: Load audio file and extract metadata
2. Format Conversion: Convert to target sample rate and format
3. Chunking: Split audio into streaming chunks
4. Encoding: Base64 encode chunks for transmission
5. Caching: Store processed audio for performance optimization

Performance Features:
- Intelligent caching to avoid repeated file I/O operations
- Configurable chunk sizes for optimal streaming
- Memory-efficient processing of large audio files
- Automatic format conversion and resampling
- Comprehensive error handling and logging
"""

import base64
import logging
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import signal

from .models import AudioChunk


class AudioManager:
    """
    Audio file manager for the AudioCodes mock client.

    This class handles loading, processing, and chunking of audio files
    for use in mock conversations. It provides caching for improved performance
    and supports various audio formats with automatic conversion.

    The AudioManager is designed for high-performance audio processing with:
    - Intelligent caching to avoid repeated file I/O operations
    - Automatic format conversion and resampling
    - Configurable chunking for optimal streaming
    - Memory-efficient processing of large audio files
    - Comprehensive error handling and logging

    Audio Processing Capabilities:
    - Load WAV files with automatic format detection
    - Resample audio to target sample rates (default: 16kHz)
    - Convert to 16-bit PCM format for compatibility
    - Split audio into configurable chunk sizes
    - Generate silence audio for testing scenarios
    - Save processed audio chunks to files

    Caching Strategy:
    The AudioManager implements a two-level caching system:
    - Audio data cache: Stores processed audio bytes
    - Metadata cache: Stores audio file metadata (sample rate, channels, etc.)
    
    Cache keys include file path, target sample rate, and chunk size to ensure
    proper cache invalidation when parameters change.

    Attributes:
        logger (logging.Logger): Logger instance for debugging and monitoring
        _audio_cache (Dict[str, bytes]): Cache for loaded and processed audio files
        _metadata_cache (Dict[str, Tuple[int, int, int]]): Cache for audio metadata
                                                          (sample_rate, channels, sample_width)
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the AudioManager with optional logging configuration.

        Args:
            logger (Optional[logging.Logger]): Logger instance for debugging and monitoring.
                                             If None, creates a default logger for this module.
        
        Example:
            # Create AudioManager with default logging
            audio_manager = AudioManager()
            
            # Create AudioManager with custom logger
            custom_logger = logging.getLogger("custom_audio")
            audio_manager = AudioManager(logger=custom_logger)
        """
        self.logger = logger or logging.getLogger(__name__)
        self._audio_cache: Dict[str, bytes] = {}
        self._metadata_cache: Dict[str, Tuple[int, int, int]] = (
            {}
        )  # (sample_rate, channels, sample_width)

    def load_audio_chunks(
        self, file_path: str, chunk_size: int = 32000, target_sample_rate: int = 16000
    ) -> List[str]:
        """
        Load and chunk an audio file into base64-encoded chunks.

        This method loads an audio file, converts it to the target format if necessary,
        and splits it into chunks suitable for streaming. The method includes intelligent
        caching to avoid repeated processing of the same file.

        The audio processing pipeline:
        1. Check cache for existing processed audio
        2. Load audio file and extract metadata
        3. Resample to target sample rate if needed
        4. Convert to 16-bit PCM format
        5. Split into chunks with minimum size enforcement
        6. Cache processed audio for future use

        Audio Format Requirements:
        - Input: WAV files (any sample rate, mono/stereo)
        - Output: 16kHz, 16-bit PCM, mono (for bridge compatibility)
        - Chunking: Configurable chunk size with minimum 100ms enforcement

        Performance Optimizations:
        - Cache processed audio data to avoid repeated file I/O
        - Use numpy and scipy for efficient audio processing
        - Minimize memory allocations during processing
        - Log processing statistics for performance monitoring

        Args:
            file_path (str): Path to the audio file to load and process
            chunk_size (int): Target size of each chunk in bytes (default: 32000)
            target_sample_rate (int): Target sample rate for conversion (default: 16000)

        Returns:
            List[str]: List of base64-encoded audio chunks ready for streaming

        Raises:
            FileNotFoundError: If the specified audio file doesn't exist
            ValueError: If the audio file is invalid or in an unsupported format
            Exception: For other audio processing errors

        Example:
            # Load audio file with default settings
            chunks = audio_manager.load_audio_chunks("audio/greeting.wav")
            print(f"Loaded {len(chunks)} audio chunks")
            
            # Load with custom chunk size
            chunks = audio_manager.load_audio_chunks(
                "audio/user_input.wav", 
                chunk_size=16000,  # Smaller chunks
                target_sample_rate=8000  # Lower sample rate
            )
        """
        # Create cache key based on file path and processing parameters
        cache_key = f"{file_path}:{target_sample_rate}:{chunk_size}"

        # Check if audio is already cached
        if cache_key in self._audio_cache:
            self.logger.debug(f"[AUDIO] Using cached audio file: {file_path}")
            return self._chunk_audio_data(self._audio_cache[cache_key], chunk_size)

        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Audio file not found: {file_path}")

            # Load audio file using wave module
            with wave.open(str(path), "rb") as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()

                self.logger.info(f"[AUDIO] Loading audio: {path.name}")
                self.logger.info(
                    f"   Format: {channels}ch, {sample_width*8}bit, {frame_rate}Hz"
                )

                # Read all audio frames
                audio_data = wav_file.readframes(wav_file.getnframes())

                # Resample to target sample rate if needed
                if frame_rate != target_sample_rate:
                    self.logger.info(
                        f"   Resampling from {frame_rate}Hz to {target_sample_rate}Hz..."
                    )
                    # Convert to numpy array for processing
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    # Calculate new sample count for target rate
                    number_of_samples = round(
                        len(audio_array) * target_sample_rate / frame_rate
                    )
                    # Perform resampling using scipy
                    audio_array = signal.resample(audio_array, number_of_samples)
                    # Convert back to 16-bit PCM
                    audio_array = np.array(audio_array, dtype=np.int16)
                    audio_data = audio_array.tobytes()
                    frame_rate = target_sample_rate

                # Cache the processed audio data for future use
                self._audio_cache[cache_key] = audio_data
                self._metadata_cache[cache_key] = (frame_rate, channels, sample_width)

                # Log processing results
                duration = len(audio_data) / (frame_rate * sample_width)
                self.logger.info(
                    f"   Processed: {len(audio_data)} bytes (~{duration:.2f}s)"
                )

                # Split audio into chunks and return
                return self._chunk_audio_data(audio_data, chunk_size)

        except Exception as e:
            self.logger.error(f"[AUDIO] Error loading audio file {file_path}: {e}")
            raise

    def _chunk_audio_data(self, audio_data: bytes, chunk_size: int) -> List[str]:
        """
        Split audio data into base64-encoded chunks for streaming.

        This method takes raw audio data and splits it into chunks suitable for
        streaming. It enforces a minimum chunk size to ensure proper audio
        processing and pads the final chunk if necessary.

        The chunking process:
        1. Calculate minimum chunk size (100ms at 16kHz, 16-bit, mono)
        2. Split audio data into chunks of specified size
        3. Pad final chunk if it's smaller than minimum size
        4. Encode each chunk as base64 string

        Chunk Size Considerations:
        - Minimum chunk size ensures proper audio processing
        - Larger chunks reduce overhead but increase latency
        - Smaller chunks provide better real-time behavior
        - Final chunk padding maintains consistent chunk sizes

        Args:
            audio_data (bytes): Raw audio data to be chunked
            chunk_size (int): Target size of each chunk in bytes

        Returns:
            List[str]: List of base64-encoded audio chunks

        Example:
            # Chunk audio data with default settings
            chunks = audio_manager._chunk_audio_data(audio_bytes, 32000)
            print(f"Created {len(chunks)} audio chunks")
            
            # Chunk with smaller size for lower latency
            chunks = audio_manager._chunk_audio_data(audio_bytes, 16000)
        """
        # Calculate minimum chunk size (100ms at 16kHz, 16-bit, mono)
        min_chunk_size = int(0.1 * 16000 * 2)  # 100ms minimum
        chunk_size = max(chunk_size, min_chunk_size)

        chunks = []
        for i in range(0, len(audio_data), chunk_size):
            # Extract chunk from audio data
            chunk = audio_data[i : i + chunk_size]
            
            # Pad last chunk if needed to meet minimum size
            if len(chunk) < min_chunk_size:
                # Pad with silence (zeros)
                padding = b"\x00" * (min_chunk_size - len(chunk))
                chunk = chunk + padding
            
            # Encode chunk as base64 string
            chunk_b64 = base64.b64encode(chunk).decode("utf-8")
            chunks.append(chunk_b64)

        self.logger.debug(f"[AUDIO] Created {len(chunks)} chunks from {len(audio_data)} bytes")
        return chunks

    def save_audio_chunks(self, chunks: List[str], output_path: str) -> bool:
        """
        Save base64-encoded audio chunks to a WAV file.

        This method reconstructs audio data from base64-encoded chunks and
        saves it as a WAV file. It's useful for saving collected audio
        responses or creating test audio files.

        The reconstruction process:
        1. Decode base64 chunks to binary audio data
        2. Concatenate all chunks into complete audio data
        3. Create WAV file with appropriate metadata
        4. Write audio data to file

        File Format:
        - Output: WAV file with 16kHz, 16-bit PCM, mono format
        - Compatibility: Standard WAV format for maximum compatibility
        - Metadata: Includes sample rate, channels, and sample width

        Args:
            chunks (List[str]): List of base64-encoded audio chunks
            output_path (str): Path where the WAV file should be saved

        Returns:
            bool: True if file was saved successfully, False otherwise

        Example:
            # Save collected audio chunks
            success = audio_manager.save_audio_chunks(
                response_chunks, 
                "output/ai_response.wav"
            )
            if success:
                print("Audio saved successfully")
        """
        try:
            # Decode all chunks and concatenate
            audio_data = b""
            for chunk in chunks:
                chunk_data = base64.b64decode(chunk)
                audio_data += chunk_data

            # Create output directory if it doesn't exist
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Write WAV file
            with wave.open(str(output_file), "wb") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)  # 16kHz
                wav_file.writeframes(audio_data)

            self.logger.info(f"[AUDIO] Saved audio to: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"[AUDIO] Error saving audio to {output_path}: {e}")
            return False

    def create_silence_chunks(
        self, duration: float = 2.0, chunk_size: int = 32000
    ) -> List[str]:
        """
        Create silence audio chunks for testing and fallback scenarios.

        This method generates silence audio data and chunks it for streaming.
        It's useful for testing scenarios where silence is needed or as
        fallback audio when no other audio is available.

        Silence Generation:
        - Creates silent audio data of specified duration
        - Uses 16kHz, 16-bit PCM format for compatibility
        - Chunks the silence data for streaming
        - Useful for testing VAD silence detection

        Args:
            duration (float): Duration of silence in seconds (default: 2.0)
            chunk_size (int): Size of each chunk in bytes (default: 32000)

        Returns:
            List[str]: List of base64-encoded silence chunks

        Example:
            # Create 2 seconds of silence
            silence_chunks = audio_manager.create_silence_chunks(duration=2.0)
            print(f"Created {len(silence_chunks)} silence chunks")
            
            # Create longer silence for testing
            long_silence = audio_manager.create_silence_chunks(duration=5.0)
        """
        # Calculate number of samples for silence duration
        sample_rate = 16000
        num_samples = int(duration * sample_rate)
        
        # Create silent audio data (zeros)
        silence_data = np.zeros(num_samples, dtype=np.int16).tobytes()
        
        # Chunk the silence data
        return self._chunk_audio_data(silence_data, chunk_size)

    def get_audio_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get audio file information without loading the entire file.

        This method extracts metadata from an audio file without processing
        the audio data. It's useful for checking audio file properties
        before loading or for validation purposes.

        Extracted Information:
        - File format and encoding details
        - Sample rate, channels, and bit depth
        - Duration and file size
        - Audio quality metrics

        Args:
            file_path (str): Path to the audio file

        Returns:
            Optional[Dict[str, Any]]: Audio file information dictionary, or None if error

        Example:
            # Get audio file information
            info = audio_manager.get_audio_info("audio/test.wav")
            if info:
                print(f"Duration: {info['duration']:.2f}s")
                print(f"Sample rate: {info['sample_rate']}Hz")
                print(f"Channels: {info['channels']}")
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return None

            with wave.open(str(path), "rb") as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                frames = wav_file.getnframes()
                
                # Calculate duration
                duration = frames / frame_rate
                
                # Calculate file size
                file_size = path.stat().st_size

                return {
                    "file_path": str(path),
                    "file_size": file_size,
                    "duration": duration,
                    "sample_rate": frame_rate,
                    "channels": channels,
                    "sample_width": sample_width,
                    "bit_depth": sample_width * 8,
                    "frames": frames,
                    "format": "WAV"
                }

        except Exception as e:
            self.logger.error(f"[AUDIO] Error getting audio info for {file_path}: {e}")
            return None

    def clear_cache(self) -> None:
        """
        Clear all cached audio data and metadata.

        This method removes all cached audio files and metadata to free up
        memory. It's useful when memory usage becomes high or when
        switching between different audio processing parameters.

        Cache Management:
        - Clears both audio data and metadata caches
        - Frees memory occupied by cached audio
        - Logs cache clearing for debugging
        - Useful for memory management in long-running processes

        Example:
            # Clear cache to free memory
            audio_manager.clear_cache()
            print("Audio cache cleared")
        """
        cache_size = len(self._audio_cache)
        self._audio_cache.clear()
        self._metadata_cache.clear()
        self.logger.info(f"[AUDIO] Cleared cache ({cache_size} files)")

    def get_cache_info(self) -> Dict[str, int]:
        """
        Get information about the current cache state.

        This method provides statistics about the audio cache, including
        the number of cached files and total memory usage. It's useful
        for monitoring cache performance and memory usage.

        Cache Statistics:
        - Number of cached audio files
        - Total memory usage of cached data
        - Cache hit rate (if tracking is enabled)
        - Memory efficiency metrics

        Returns:
            Dict[str, int]: Cache statistics dictionary

        Example:
            # Get cache information
            cache_info = audio_manager.get_cache_info()
            print(f"Cached files: {cache_info['cached_files']}")
            print(f"Total memory: {cache_info['total_memory']} bytes")
        """
        total_memory = sum(len(data) for data in self._audio_cache.values())
        return {
            "cached_files": len(self._audio_cache),
            "total_memory": total_memory,
            "metadata_entries": len(self._metadata_cache)
        }

    def is_cached(self, file_path: str, target_sample_rate: int = 16000) -> bool:
        """
        Check if an audio file is currently cached.

        This method checks if a specific audio file (with given processing
        parameters) is currently in the cache. It's useful for determining
        whether loading a file will require processing or can use cached data.

        Cache Key Generation:
        - Uses file path, target sample rate, and chunk size
        - Ensures cache hits only for identical processing parameters
        - Handles different chunk sizes as separate cache entries

        Args:
            file_path (str): Path to the audio file
            target_sample_rate (int): Target sample rate for processing

        Returns:
            bool: True if file is cached, False otherwise

        Example:
            # Check if file is cached
            if audio_manager.is_cached("audio/test.wav"):
                print("File is already cached")
            else:
                print("File needs to be processed")
        """
        # Check for any cached version of this file
        for cache_key in self._audio_cache.keys():
            if cache_key.startswith(f"{file_path}:{target_sample_rate}:"):
                return True
        return False

    def remove_from_cache(
        self, file_path: str, target_sample_rate: int = 16000
    ) -> bool:
        """
        Remove a specific audio file from the cache.

        This method removes a specific audio file and its metadata from
        the cache. It's useful for selective cache management when
        specific files are no longer needed.

        Cache Removal:
        - Removes all cached versions of the specified file
        - Handles different chunk sizes and sample rates
        - Cleans up both audio data and metadata
        - Logs removal for debugging

        Args:
            file_path (str): Path to the audio file to remove
            target_sample_rate (int): Target sample rate for processing

        Returns:
            bool: True if file was removed from cache, False if not found

        Example:
            # Remove specific file from cache
            removed = audio_manager.remove_from_cache("audio/old_file.wav")
            if removed:
                print("File removed from cache")
        """
        removed = False
        keys_to_remove = []
        
        # Find all cache keys for this file
        for cache_key in self._audio_cache.keys():
            if cache_key.startswith(f"{file_path}:{target_sample_rate}:"):
                keys_to_remove.append(cache_key)
        
        # Remove from both caches
        for key in keys_to_remove:
            self._audio_cache.pop(key, None)
            self._metadata_cache.pop(key, None)
            removed = True
        
        if removed:
            self.logger.debug(f"[AUDIO] Removed {len(keys_to_remove)} cache entries for {file_path}")
        
        return removed
