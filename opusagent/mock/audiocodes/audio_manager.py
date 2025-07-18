"""
Audio management for the AudioCodes mock client.

This module provides audio file handling, chunking, and caching functionality
for the AudioCodes mock client. It supports various audio formats and provides
efficient audio processing for testing scenarios.
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
    and supports various audio formats.

    Attributes:
        logger (logging.Logger): Logger instance for debugging
        _audio_cache (Dict[str, bytes]): Cache for loaded audio files
        _metadata_cache (Dict[str, Tuple[int, int, int]]): Cache for audio metadata
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
        self._metadata_cache: Dict[str, Tuple[int, int, int]] = (
            {}
        )  # (sample_rate, channels, sample_width)

    def load_audio_chunks(
        self, file_path: str, chunk_size: int = 32000, target_sample_rate: int = 16000
    ) -> List[str]:
        """
        Load and chunk an audio file into base64-encoded chunks.

        Args:
            file_path (str): Path to the audio file to load
            chunk_size (int): Size of each chunk in bytes
            target_sample_rate (int): Target sample rate for conversion

        Returns:
            List[str]: List of base64-encoded audio chunks

        Raises:
            FileNotFoundError: If the audio file doesn't exist
            ValueError: If the audio file is invalid or unsupported
        """
        cache_key = f"{file_path}:{target_sample_rate}:{chunk_size}"

        if cache_key in self._audio_cache:
            self.logger.debug(f"[AUDIO] Using cached audio file: {file_path}")
            return self._chunk_audio_data(self._audio_cache[cache_key], chunk_size)

        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Audio file not found: {file_path}")

            with wave.open(str(path), "rb") as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()

                self.logger.info(f"[AUDIO] Loading audio: {path.name}")
                self.logger.info(
                    f"   Format: {channels}ch, {sample_width*8}bit, {frame_rate}Hz"
                )

                audio_data = wav_file.readframes(wav_file.getnframes())

                # Resample to target sample rate if needed
                if frame_rate != target_sample_rate:
                    self.logger.info(
                        f"   Resampling from {frame_rate}Hz to {target_sample_rate}Hz..."
                    )
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    number_of_samples = round(
                        len(audio_array) * target_sample_rate / frame_rate
                    )
                    audio_array = signal.resample(audio_array, number_of_samples)
                    audio_array = np.array(audio_array, dtype=np.int16)
                    audio_data = audio_array.tobytes()
                    frame_rate = target_sample_rate

                # Cache the processed audio data
                self._audio_cache[cache_key] = audio_data
                self._metadata_cache[cache_key] = (frame_rate, channels, sample_width)

                duration = len(audio_data) / (frame_rate * sample_width)
                self.logger.info(
                    f"   Processed: {len(audio_data)} bytes (~{duration:.2f}s)"
                )

                return self._chunk_audio_data(audio_data, chunk_size)

        except Exception as e:
            self.logger.error(f"[AUDIO] Error loading audio file {file_path}: {e}")
            raise

    def _chunk_audio_data(self, audio_data: bytes, chunk_size: int) -> List[str]:
        """
        Chunk audio data into base64-encoded strings.

        Args:
            audio_data (bytes): Raw audio data
            chunk_size (int): Size of each chunk in bytes

        Returns:
            List[str]: List of base64-encoded chunks
        """
        # Calculate minimum chunk size (100ms at 16kHz, 16-bit, mono)
        min_chunk_size = int(0.1 * 16000 * 2)  # 100ms minimum
        chunk_size = max(chunk_size, min_chunk_size)

        chunks = []
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i : i + chunk_size]
            # Pad last chunk if needed
            if len(chunk) < min_chunk_size:
                chunk += b"\x00" * (min_chunk_size - len(chunk))
            encoded_chunk = base64.b64encode(chunk).decode("utf-8")
            chunks.append(encoded_chunk)

        self.logger.debug(f"[AUDIO] Split into {len(chunks)} chunks")
        return chunks

    def save_audio_chunks(self, chunks: List[str], output_path: str) -> bool:
        """
        Save base64-encoded audio chunks to a WAV file.

        Args:
            chunks (List[str]): List of base64-encoded audio chunks
            output_path (str): Path where to save the WAV file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Decode all chunks
            audio_data = b""
            for chunk in chunks:
                audio_data += base64.b64decode(chunk)

            # Save as WAV file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with wave.open(str(output_file), "wb") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)  # 16kHz
                wav_file.writeframes(audio_data)

            duration = len(audio_data) / (16000 * 2)
            self.logger.info(
                f"[AUDIO] Saved audio: {output_file.name} ({duration:.2f}s)"
            )
            return True

        except Exception as e:
            self.logger.error(f"[AUDIO] Error saving audio: {e}")
            return False

    def create_silence_chunks(
        self, duration: float = 2.0, chunk_size: int = 32000
    ) -> List[str]:
        """
        Create silence audio chunks for testing purposes.

        Args:
            duration (float): Duration of silence in seconds
            chunk_size (int): Size of each chunk in bytes

        Returns:
            List[str]: List of base64-encoded silence chunks
        """
        # Generate silence data (16-bit PCM, 16kHz, mono)
        sample_rate = 16000
        num_samples = int(sample_rate * duration)
        silence_data = bytes([0] * num_samples * 2)  # 16-bit = 2 bytes per sample

        return self._chunk_audio_data(silence_data, chunk_size)

    def get_audio_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an audio file without loading it.

        Args:
            file_path (str): Path to the audio file

        Returns:
            Optional[Dict[str, any]]: Audio file information or None if error
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return None

            with wave.open(str(path), "rb") as wav_file:
                return {
                    "channels": wav_file.getnchannels(),
                    "sample_width": wav_file.getsampwidth(),
                    "frame_rate": wav_file.getframerate(),
                    "frames": wav_file.getnframes(),
                    "duration": wav_file.getnframes() / wav_file.getframerate(),
                    "file_size": path.stat().st_size,
                }

        except Exception as e:
            self.logger.error(f"[AUDIO] Error getting audio info for {file_path}: {e}")
            return None

    def clear_cache(self) -> None:
        """Clear the audio file cache."""
        self._audio_cache.clear()
        self._metadata_cache.clear()
        self.logger.info("[AUDIO] Audio cache cleared")

    def get_cache_info(self) -> Dict[str, int]:
        """
        Get information about the audio cache.

        Returns:
            Dict[str, int]: Cache statistics
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
            file_path (str): Path to the audio file
            target_sample_rate (int): Target sample rate

        Returns:
            bool: True if the file is cached, False otherwise
        """
        cache_key = f"{file_path}:{target_sample_rate}:32000"  # Default chunk size
        return cache_key in self._audio_cache

    def remove_from_cache(
        self, file_path: str, target_sample_rate: int = 16000
    ) -> bool:
        """
        Remove a specific file from the cache.

        Args:
            file_path (str): Path to the audio file
            target_sample_rate (int): Target sample rate

        Returns:
            bool: True if the file was removed, False if it wasn't cached
        """
        cache_key = f"{file_path}:{target_sample_rate}:32000"  # Default chunk size
        if cache_key in self._audio_cache:
            del self._audio_cache[cache_key]
            if cache_key in self._metadata_cache:
                del self._metadata_cache[cache_key]
            self.logger.debug(f"[AUDIO] Removed {file_path} from audio cache")
            return True
        return False
