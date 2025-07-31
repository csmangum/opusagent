"""
Shared audio utilities for the OpusAgent project.

This module contains common audio processing functions that can be used
across different parts of the codebase to avoid duplication.
"""

import base64
import logging
import struct
from typing import List, Optional, Tuple

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

    @staticmethod
    def ulaw_to_pcm16(mulaw_bytes: bytes) -> bytes:
        """
        Convert μ-law encoded audio to PCM16.
        
        Args:
            mulaw_bytes (bytes): μ-law encoded audio data
        
        Returns:
            bytes: PCM16 audio data
        """
        try:
            import audioop
            return audioop.ulaw2lin(mulaw_bytes, 2)
        except ImportError:
            # Fallback implementation using lookup table
            return AudioUtils._ulaw_to_pcm16_fallback(mulaw_bytes)

    @staticmethod
    def pcm16_to_ulaw(pcm16_data: bytes) -> bytes:
        """
        Convert PCM16 audio to μ-law encoding.
        
        Args:
            pcm16_data (bytes): PCM16 audio data
        
        Returns:
            bytes: μ-law encoded audio data
        """
        try:
            import audioop
            return audioop.lin2ulaw(pcm16_data, 2)
        except ImportError:
            # Fallback implementation using lookup table
            return AudioUtils._pcm16_to_ulaw_fallback(pcm16_data)

    @staticmethod
    def _ulaw_to_pcm16_fallback(mulaw_bytes: bytes) -> bytes:
        """Fallback μ-law to PCM16 conversion using lookup table."""
        # μ-law to linear conversion table
        ulaw_table = [
            -32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
            -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
            -15996, -15484, -14972, -14460, -13948, -13436, -12924, -12412,
            -11900, -11388, -10876, -10364, -9852, -9340, -8828, -8316,
            -7932, -7676, -7420, -7164, -6908, -6652, -6396, -6140,
            -5884, -5628, -5372, -5116, -4860, -4604, -4348, -4092,
            -3900, -3772, -3644, -3516, -3388, -3260, -3132, -3004,
            -2876, -2748, -2620, -2492, -2364, -2236, -2108, -1980,
            -1884, -1820, -1756, -1692, -1628, -1564, -1500, -1436,
            -1372, -1308, -1244, -1180, -1116, -1052, -988, -924,
            -876, -844, -812, -780, -748, -716, -684, -652,
            -620, -588, -556, -524, -492, -460, -428, -396,
            -372, -356, -340, -324, -308, -292, -276, -260,
            -244, -228, -212, -196, -180, -164, -148, -132,
            -120, -112, -104, -96, -88, -80, -72, -64,
            -56, -48, -40, -32, -24, -16, -8, 0,
            32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
            23932, 22908, 21884, 20860, 19836, 18812, 17788, 16764,
            15996, 15484, 14972, 14460, 13948, 13436, 12924, 12412,
            11900, 11388, 10876, 10364, 9852, 9340, 8828, 8316,
            7932, 7676, 7420, 7164, 6908, 6652, 6396, 6140,
            5884, 5628, 5372, 5116, 4860, 4604, 4348, 4092,
            3900, 3772, 3644, 3516, 3388, 3260, 3132, 3004,
            2876, 2748, 2620, 2492, 2364, 2236, 2108, 1980,
            1884, 1820, 1756, 1692, 1628, 1564, 1500, 1436,
            1372, 1308, 1244, 1180, 1116, 1052, 988, 924,
            876, 844, 812, 780, 748, 716, 684, 652,
            620, 588, 556, 524, 492, 460, 428, 396,
            372, 356, 340, 324, 308, 292, 276, 260,
            244, 228, 212, 196, 180, 164, 148, 132,
            120, 112, 104, 96, 88, 80, 72, 64,
            56, 48, 40, 32, 24, 16, 8, 0
        ]
        
        pcm16_data = bytearray()
        for byte in mulaw_bytes:
            pcm16_data.extend(struct.pack('<h', ulaw_table[byte]))
        
        return bytes(pcm16_data)

    @staticmethod
    def _pcm16_to_ulaw_fallback(pcm16_data: bytes) -> bytes:
        """Fallback PCM16 to μ-law conversion using lookup table."""
        # Simplified PCM16 to μ-law conversion
        ulaw_data = bytearray()
        
        for i in range(0, len(pcm16_data), 2):
            if i + 1 < len(pcm16_data):
                # Convert 16-bit little-endian to signed integer
                sample = struct.unpack('<h', pcm16_data[i:i+2])[0]
                
                # Simple μ-law encoding (simplified version)
                if sample >= 0:
                    ulaw_byte = 0x80  # Sign bit
                else:
                    ulaw_byte = 0x00
                    sample = -sample
                
                # Quantize to 7-bit
                if sample > 0:
                    # Find the highest bit set
                    bit_pos = 0
                    temp = sample
                    while temp > 1:
                        temp >>= 1
                        bit_pos += 1
                    
                    # Encode segment and quantization
                    segment = max(0, min(7, bit_pos - 4))
                    quantization = (sample >> (bit_pos - 4)) & 0x0F
                    
                    ulaw_byte |= (segment << 4) | quantization
                
                ulaw_data.append(ulaw_byte)
        
        return bytes(ulaw_data)

    @staticmethod
    def visualize_audio_level(audio_data: bytes, max_bars: int = 10) -> str:
        """
        Create a simple audio level visualization.
        
        Args:
            audio_data (bytes): PCM16 audio data
            max_bars (int): Maximum number of bars to show
        
        Returns:
            str: ASCII visualization of audio level
        """
        if not audio_data or len(audio_data) < 2:
            return "▁" * max_bars
        
        # Calculate RMS level
        samples = []
        for i in range(0, len(audio_data), 2):
            if i + 1 < len(audio_data):
                sample = struct.unpack('<h', audio_data[i:i+2])[0]
                samples.append(abs(sample))
        
        if not samples:
            return "▁" * max_bars
        
        # Calculate RMS
        rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
        max_level = 32767  # 16-bit signed max
        level_ratio = min(1.0, rms / max_level)
        
        # Create visualization
        bars = int(level_ratio * max_bars)
        visualization = "█" * bars + "▁" * (max_bars - bars)
        
        return visualization

    @staticmethod
    def resample_audio(
        audio_bytes: bytes, 
        from_rate: int, 
        to_rate: int, 
        channels: int = 1, 
        sample_width: int = 2
    ) -> bytes:
        """
        Resample audio data using simple linear interpolation.
        
        Args:
            audio_bytes (bytes): Raw audio data
            from_rate (int): Source sample rate
            to_rate (int): Target sample rate
            channels (int): Number of channels
            sample_width (int): Sample width in bytes
        
        Returns:
            bytes: Resampled audio data
        """
        if from_rate == to_rate:
            return audio_bytes
        
        try:
            import librosa
            import numpy as np
            
            # Convert bytes to numpy array
            samples = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # Resample using librosa
            resampled_samples = librosa.resample(
                samples.astype(np.float32) / 32767.0,  # Normalize to [-1, 1]
                orig_sr=from_rate,
                target_sr=to_rate
            )
            
            # Convert back to int16 and bytes
            resampled_int16 = (resampled_samples * 32767.0).astype(np.int16)
            return resampled_int16.tobytes()
            
        except ImportError:
            # Fallback to simple linear interpolation
            return AudioUtils._simple_resample(audio_bytes, from_rate, to_rate, channels, sample_width)

    @staticmethod
    def _simple_resample(
        audio_bytes: bytes, 
        from_rate: int, 
        to_rate: int, 
        channels: int, 
        sample_width: int
    ) -> bytes:
        """Simple linear interpolation resampling."""
        if from_rate == to_rate:
            return audio_bytes
        
        # Convert to samples
        samples = []
        for i in range(0, len(audio_bytes), sample_width):
            if i + sample_width <= len(audio_bytes):
                sample = struct.unpack('<h', audio_bytes[i:i+sample_width])[0]
                samples.append(sample)
        
        if not samples:
            return audio_bytes
        
        # Calculate resampling ratio
        ratio = to_rate / from_rate
        new_length = int(len(samples) * ratio)
        
        # Simple linear interpolation
        resampled_samples = []
        for i in range(new_length):
            old_index = i / ratio
            index_low = int(old_index)
            index_high = min(index_low + 1, len(samples) - 1)
            
            if index_low == index_high:
                resampled_samples.append(samples[index_low])
            else:
                # Linear interpolation
                weight = old_index - index_low
                sample = samples[index_low] * (1 - weight) + samples[index_high] * weight
                resampled_samples.append(int(sample))
        
        # Convert back to bytes
        resampled_bytes = bytearray()
        for sample in resampled_samples:
            resampled_bytes.extend(struct.pack('<h', sample))
        
        return bytes(resampled_bytes) 

    @staticmethod
    def load_audio_file(file_path: str, target_sample_rate: int = 16000) -> Tuple[bytes, int, int]:
        """
        Load an audio file and return audio data with metadata.
        
        Args:
            file_path (str): Path to the audio file to load
            target_sample_rate (int): Target sample rate for conversion
            
        Returns:
            Tuple[bytes, int, int]: (audio_data, sample_rate, channels)
        """
        try:
            import wave
            
            with wave.open(file_path, 'rb') as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                audio_data = wav_file.readframes(wav_file.getnframes())
                
                # Resample if needed
                if frame_rate != target_sample_rate:
                    audio_data = AudioUtils.resample_audio(
                        audio_data, frame_rate, target_sample_rate, channels, sample_width
                    )
                    frame_rate = target_sample_rate
                
                return audio_data, frame_rate, channels
                
        except Exception as e:
            logger.error(f"Error loading audio file {file_path}: {e}")
            # Return silence as fallback
            silence_data = AudioUtils.create_simple_wav_data(2.0, target_sample_rate)
            return silence_data, target_sample_rate, 1 