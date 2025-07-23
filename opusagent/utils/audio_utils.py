"""
Shared audio utilities for the OpusAgent project.

This module contains common audio processing functions that can be used
across different parts of the codebase to avoid duplication.
"""

import base64
import logging
import struct
from typing import List, Optional

logger = logging.getLogger(__name__)


class AudioUtils:
    """Shared audio utility functions."""

    @staticmethod
    def create_simple_wav_data(duration: float = 2.0, sample_rate: int = 16000) -> bytes:
        """
        Create simple WAV audio data with silence.
        
        Args:
            duration (float): Duration in seconds. Default: 2.0s
            sample_rate (int): Sample rate in Hz. Default: 16000Hz
        
        Returns:
            bytes: Raw WAV audio data
        """
        # Calculate audio parameters
        num_samples = int(sample_rate * duration)
        data_size = num_samples * 2  # 16-bit samples
        
        # Create WAV file structure
        wav_data = bytearray()
        
        # RIFF header
        wav_data.extend(b'RIFF')
        wav_data.extend(struct.pack('<I', 36 + data_size))  # File size
        wav_data.extend(b'WAVE')
        
        # fmt chunk
        wav_data.extend(b'fmt ')
        wav_data.extend(struct.pack('<I', 16))  # Chunk size
        wav_data.extend(struct.pack('<H', 1))   # Audio format (PCM)
        wav_data.extend(struct.pack('<H', 1))   # Number of channels
        wav_data.extend(struct.pack('<I', sample_rate))  # Sample rate
        wav_data.extend(struct.pack('<I', sample_rate * 2))  # Byte rate
        wav_data.extend(struct.pack('<H', 2))   # Block align
        wav_data.extend(struct.pack('<H', 16))  # Bits per sample
        
        # data chunk
        wav_data.extend(b'data')
        wav_data.extend(struct.pack('<I', data_size))
        
        # Audio data (silence)
        wav_data.extend(b'\x00\x00' * num_samples)
        
        return bytes(wav_data)

    @staticmethod
    def chunk_audio_data(audio_data: bytes, chunk_size: int, overlap: int = 0) -> List[bytes]:
        """
        Split audio data into chunks of specified size with optional overlap.
        
        Args:
            audio_data (bytes): Raw audio data to chunk
            chunk_size (int): Size of each chunk in bytes
            overlap (int): Overlap between chunks in bytes
        
        Returns:
            List[bytes]: List of audio chunks
        """
        if not audio_data:
            return []
        
        chunks = []
        step_size = chunk_size - overlap
        
        for i in range(0, len(audio_data), step_size):
            chunk_end = min(i + chunk_size, len(audio_data))
            chunk = audio_data[i:chunk_end]
            
            # Pad last chunk if needed
            if len(chunk) < chunk_size and i + step_size >= len(audio_data):
                padding = chunk_size - len(chunk)
                chunk += b"\x00" * padding
            
            chunks.append(chunk)
            
            # Break if we've reached the end
            if chunk_end >= len(audio_data):
                break
        
        return chunks

    @staticmethod
    def chunk_audio_by_duration(
        audio_data: bytes,
        sample_rate: int,
        duration_ms: int,
        channels: int = 1,
        sample_width: int = 2,
    ) -> List[bytes]:
        """
        Split audio data into chunks by duration.
        
        Args:
            audio_data (bytes): Raw audio data
            sample_rate (int): Sample rate in Hz
            duration_ms (int): Duration of each chunk in milliseconds
            channels (int): Number of audio channels
            sample_width (int): Sample width in bytes
        
        Returns:
            List[bytes]: List of audio chunks
        """
        # Calculate chunk size in bytes
        frames_per_chunk = int((duration_ms / 1000.0) * sample_rate)
        bytes_per_frame = channels * sample_width
        chunk_size = frames_per_chunk * bytes_per_frame
        
        return AudioUtils.chunk_audio_data(audio_data, chunk_size)

    @staticmethod
    def calculate_audio_duration(
        audio_data: bytes, 
        sample_rate: int = 16000, 
        channels: int = 1, 
        bits_per_sample: int = 16
    ) -> float:
        """
        Calculate the duration of audio data.
        
        Args:
            audio_data (bytes): Raw audio data
            sample_rate (int): Sample rate in Hz
            channels (int): Number of channels
            bits_per_sample (int): Bits per sample
        
        Returns:
            float: Duration in seconds
        """
        if not audio_data:
            return 0.0
        
        bytes_per_sample = bits_per_sample // 8
        total_samples = len(audio_data) // (channels * bytes_per_sample)
        return total_samples / sample_rate

    @staticmethod
    def convert_to_base64(audio_data: bytes) -> str:
        """
        Convert audio data to base64 string.
        
        Args:
            audio_data (bytes): Raw audio data
        
        Returns:
            str: Base64 encoded string
        """
        return base64.b64encode(audio_data).decode("utf-8")

    @staticmethod
    def convert_from_base64(base64_data: str) -> bytes:
        """
        Convert base64 string back to audio data.
        
        Args:
            base64_data (str): Base64 encoded audio data
        
        Returns:
            bytes: Raw audio data
        """
        try:
            return base64.b64decode(base64_data)
        except Exception as e:
            logger.error(f"Error decoding base64 audio: {e}")
            return b"" 