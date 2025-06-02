"""
Audio utilities for the Interactive TUI Validator.

This module provides audio file handling, processing, and conversion utilities
for working with audio data in the TUI application.
"""

import base64
import wave
from pathlib import Path
from typing import List, Tuple, Optional


class AudioUtils:
    """Audio file handling and processing utilities."""
    
    @staticmethod
    def load_wav_file(filepath: str) -> Tuple[bytes, int, int]:
        """
        Load a WAV file and return audio data, sample rate, and channels.
        
        Args:
            filepath: Path to the WAV file
            
        Returns:
            Tuple of (audio_data, sample_rate, channels)
        """
        # TODO: Implement WAV file loading
        try:
            with wave.open(filepath, 'rb') as wav_file:
                frames = wav_file.readframes(-1)
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                return frames, sample_rate, channels
        except Exception as e:
            # Return empty data on error
            return b'', 16000, 1
    
    @staticmethod  
    def chunk_audio_data(audio_data: bytes, chunk_size: int) -> List[bytes]:
        """
        Split audio data into chunks of specified size.
        
        Args:
            audio_data: Raw audio data
            chunk_size: Size of each chunk in bytes
            
        Returns:
            List of audio chunks
        """
        chunks = []
        for i in range(0, len(audio_data), chunk_size):
            chunks.append(audio_data[i:i + chunk_size])
        return chunks
    
    @staticmethod
    def convert_to_base64(audio_data: bytes) -> str:
        """
        Convert audio data to base64 string.
        
        Args:
            audio_data: Raw audio data
            
        Returns:
            Base64 encoded string
        """
        return base64.b64encode(audio_data).decode('utf-8')
    
    @staticmethod
    def convert_from_base64(base64_data: str) -> bytes:
        """
        Convert base64 string back to audio data.
        
        Args:
            base64_data: Base64 encoded audio data
            
        Returns:
            Raw audio data
        """
        return base64.b64decode(base64_data)
    
    @staticmethod
    def visualize_audio_level(audio_data: bytes, max_bars: int = 13) -> str:
        """
        Create a simple ASCII visualization of audio levels.
        
        Args:
            audio_data: Raw audio data
            max_bars: Maximum number of bars in visualization
            
        Returns:
            ASCII bar visualization string
        """
        if not audio_data:
            return "▁" * max_bars
        
        # Simple level calculation (placeholder)
        # TODO: Implement proper audio level analysis
        import struct
        
        try:
            # Assume 16-bit PCM data
            samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
            
            # Calculate RMS level
            if samples:
                rms = (sum(x*x for x in samples) / len(samples)) ** 0.5
                level = min(rms / 32768.0, 1.0)  # Normalize to 0-1
            else:
                level = 0.0
        except:
            level = 0.0
        
        # Convert to bars
        num_bars = int(level * max_bars)
        bars = "▁▂▃▄▅▆▇█"
        
        result = ""
        for i in range(max_bars):
            if i < num_bars:
                bar_idx = min(i * len(bars) // max_bars, len(bars) - 1)
                result += bars[bar_idx]
            else:
                result += "▁"
        
        return result
    
    @staticmethod
    def get_audio_duration(audio_data: bytes, sample_rate: int, channels: int = 1, sample_width: int = 2) -> float:
        """
        Calculate audio duration in seconds.
        
        Args:
            audio_data: Raw audio data
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            sample_width: Sample width in bytes
            
        Returns:
            Duration in seconds
        """
        if not audio_data:
            return 0.0
        
        num_samples = len(audio_data) // (channels * sample_width)
        return num_samples / sample_rate
    
    @staticmethod
    def validate_audio_format(filepath: str) -> bool:
        """
        Validate if the file is a supported audio format.
        
        Args:
            filepath: Path to the audio file
            
        Returns:
            True if format is supported
        """
        path = Path(filepath)
        supported_extensions = {'.wav', '.mp3', '.flac', '.ogg'}
        return path.suffix.lower() in supported_extensions 