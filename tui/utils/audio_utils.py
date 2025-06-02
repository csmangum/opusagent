"""
Audio utilities for the Interactive TUI Validator.

This module provides audio file handling, processing, and conversion utilities
for working with audio data in the TUI application.
"""

import base64
import wave
import struct
import math
from pathlib import Path
from typing import List, Tuple, Optional, Union
import logging

try:
    import librosa
    import soundfile as sf
    import numpy as np
    ADVANCED_AUDIO_AVAILABLE = True
except ImportError:
    ADVANCED_AUDIO_AVAILABLE = False
    librosa = None
    sf = None
    np = None

logger = logging.getLogger(__name__)

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
        try:
            with wave.open(filepath, 'rb') as wav_file:
                frames = wav_file.readframes(-1)
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                
                logger.info(f"Loaded WAV: {filepath} - {sample_rate}Hz, {channels}ch, {sample_width*8}bit, {len(frames)} bytes")
                return frames, sample_rate, channels
                
        except Exception as e:
            logger.error(f"Error loading WAV file {filepath}: {e}")
            return b'', 16000, 1
    
    @staticmethod
    def load_audio_file(filepath: str, target_sample_rate: int = 16000) -> Tuple[bytes, int, int]:
        """
        Load any supported audio file format.
        
        Args:
            filepath: Path to the audio file
            target_sample_rate: Target sample rate for conversion
            
        Returns:
            Tuple of (audio_data, sample_rate, channels)
        """
        file_path = Path(filepath)
        
        if not file_path.exists():
            logger.error(f"Audio file not found: {filepath}")
            return b'', target_sample_rate, 1
        
        # Handle WAV files with built-in support
        if file_path.suffix.lower() == '.wav':
            audio_data, sample_rate, channels = AudioUtils.load_wav_file(filepath)
            
            # Resample if needed
            if sample_rate != target_sample_rate:
                audio_data = AudioUtils.resample_audio(audio_data, sample_rate, target_sample_rate)
                sample_rate = target_sample_rate
            
            return audio_data, sample_rate, channels
        
        # Use librosa for other formats if available
        if ADVANCED_AUDIO_AVAILABLE:
            try:
                # Load with librosa and convert to target sample rate
                audio_array, sample_rate = librosa.load(filepath, sr=target_sample_rate, mono=True)
                
                # Convert to 16-bit PCM bytes
                audio_int16 = (audio_array * 32767).astype(np.int16)
                audio_data = audio_int16.tobytes()
                
                logger.info(f"Loaded audio: {filepath} - {sample_rate}Hz, 1ch, {len(audio_data)} bytes")
                return audio_data, sample_rate, 1
                
            except Exception as e:
                logger.error(f"Error loading audio file {filepath} with librosa: {e}")
        else:
            logger.warning("Advanced audio loading not available. Install librosa for MP3/FLAC support.")
        
        return b'', target_sample_rate, 1
    
    @staticmethod  
    def chunk_audio_data(audio_data: bytes, chunk_size: int, overlap: int = 0) -> List[bytes]:
        """
        Split audio data into chunks of specified size with optional overlap.
        
        Args:
            audio_data: Raw audio data
            chunk_size: Size of each chunk in bytes
            overlap: Overlap between chunks in bytes
            
        Returns:
            List of audio chunks
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
                chunk += b'\x00' * padding
            
            chunks.append(chunk)
            
            # Break if we've reached the end
            if chunk_end >= len(audio_data):
                break
        
        return chunks
    
    @staticmethod
    def chunk_audio_by_duration(audio_data: bytes, sample_rate: int, duration_ms: int, 
                               channels: int = 1, sample_width: int = 2) -> List[bytes]:
        """
        Split audio data into chunks by duration.
        
        Args:
            audio_data: Raw audio data
            sample_rate: Sample rate in Hz
            duration_ms: Duration of each chunk in milliseconds
            channels: Number of audio channels
            sample_width: Sample width in bytes
            
        Returns:
            List of audio chunks
        """
        # Calculate chunk size in bytes
        frames_per_chunk = int((duration_ms / 1000.0) * sample_rate)
        bytes_per_frame = channels * sample_width
        chunk_size = frames_per_chunk * bytes_per_frame
        
        return AudioUtils.chunk_audio_data(audio_data, chunk_size)
    
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
        try:
            return base64.b64decode(base64_data)
        except Exception as e:
            logger.error(f"Error decoding base64 audio: {e}")
            return b''
    
    @staticmethod
    def resample_audio(audio_data: bytes, from_rate: int, to_rate: int, 
                      channels: int = 1, sample_width: int = 2) -> bytes:
        """
        Resample audio data to a different sample rate.
        
        Args:
            audio_data: Raw audio data
            from_rate: Source sample rate
            to_rate: Target sample rate
            channels: Number of channels
            sample_width: Sample width in bytes
            
        Returns:
            Resampled audio data
        """
        if from_rate == to_rate:
            return audio_data
        
        if not ADVANCED_AUDIO_AVAILABLE:
            logger.warning("Resampling requires librosa. Returning original data.")
            return audio_data
        
        try:
            # Convert bytes to numpy array
            if sample_width == 2:
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                logger.warning(f"Unsupported sample width: {sample_width}")
                return audio_data
            
            # Reshape for multiple channels
            if channels > 1:
                audio_array = audio_array.reshape(-1, channels)
                # Convert to mono for simplicity
                audio_array = np.mean(audio_array, axis=1)
            
            # Resample using librosa
            resampled = librosa.resample(audio_array, orig_sr=from_rate, target_sr=to_rate)
            
            # Convert back to int16 bytes
            resampled_int16 = (resampled * 32767).astype(np.int16)
            return resampled_int16.tobytes()
            
        except Exception as e:
            logger.error(f"Error resampling audio: {e}")
            return audio_data
    
    @staticmethod
    def visualize_audio_level(audio_data: bytes, max_bars: int = 13, sample_width: int = 2) -> str:
        """
        Create a simple ASCII visualization of audio levels.
        
        Args:
            audio_data: Raw audio data
            max_bars: Maximum number of bars in visualization
            sample_width: Sample width in bytes
            
        Returns:
            ASCII bar visualization string
        """
        if not audio_data:
            return "▁" * max_bars
        
        try:
            # Convert to samples based on sample width
            if sample_width == 2:
                samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
                max_val = 32768.0
            elif sample_width == 1:
                samples = struct.unpack(f'{len(audio_data)}B', audio_data)
                max_val = 128.0
            else:
                # Fallback for unsupported formats
                return "▁" * max_bars
            
            # Calculate RMS level
            if samples:
                rms = math.sqrt(sum(x*x for x in samples) / len(samples))
                level = min(rms / max_val, 1.0)  # Normalize to 0-1
            else:
                level = 0.0
                
        except Exception as e:
            logger.debug(f"Error calculating audio level: {e}")
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
    def create_waveform_visualization(audio_data: bytes, width: int = 50, height: int = 10,
                                    sample_width: int = 2) -> List[str]:
        """
        Create a waveform visualization of audio data.
        
        Args:
            audio_data: Raw audio data
            width: Width of visualization in characters
            height: Height of visualization in lines
            sample_width: Sample width in bytes
            
        Returns:
            List of strings representing the waveform
        """
        if not audio_data or not ADVANCED_AUDIO_AVAILABLE:
            # Return empty waveform
            return [" " * width for _ in range(height)]
        
        try:
            # Convert to numpy array
            if sample_width == 2:
                samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                return [" " * width for _ in range(height)]
            
            # Downsample to fit width
            if len(samples) > width:
                step = len(samples) // width
                downsampled = samples[::step][:width]
            else:
                downsampled = np.pad(samples, (0, width - len(samples)))
            
            # Create waveform lines
            lines = []
            center = height // 2
            
            for y in range(height):
                line = ""
                for x in range(width):
                    sample_val = downsampled[x] if x < len(downsampled) else 0.0
                    sample_height = int(sample_val * center)
                    
                    # Determine if this position should have a character
                    if abs(y - center) <= abs(sample_height):
                        line += "█"
                    else:
                        line += " "
                
                lines.append(line)
            
            return lines
            
        except Exception as e:
            logger.debug(f"Error creating waveform: {e}")
            return [" " * width for _ in range(height)]
    
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
        if not path.exists():
            return False
        
        supported_extensions = {'.wav'}
        
        if ADVANCED_AUDIO_AVAILABLE:
            supported_extensions.update({'.mp3', '.flac', '.ogg', '.m4a', '.aac'})
        
        return path.suffix.lower() in supported_extensions
    
    @staticmethod
    def convert_to_pcm16(audio_data: bytes, from_format: str) -> bytes:
        """
        Convert audio data to PCM16 format.
        
        Args:
            audio_data: Raw audio data
            from_format: Source format ("pcm16", "ulaw", "alaw")
            
        Returns:
            PCM16 audio data
        """
        if from_format.lower() == "pcm16" or from_format.lower() == "raw/lpcm16":
            return audio_data
        
        # G.711 μ-law decoding
        elif from_format.lower() in ["ulaw", "g711/ulaw"]:
            return AudioUtils._ulaw_to_pcm16(audio_data)
        
        # G.711 A-law decoding  
        elif from_format.lower() in ["alaw", "g711/alaw"]:
            return AudioUtils._alaw_to_pcm16(audio_data)
        
        else:
            logger.warning(f"Unsupported audio format: {from_format}")
            return audio_data
    
    @staticmethod
    def convert_from_pcm16(audio_data: bytes, to_format: str) -> bytes:
        """
        Convert PCM16 audio data to another format.
        
        Args:
            audio_data: PCM16 audio data
            to_format: Target format ("ulaw", "alaw")
            
        Returns:
            Converted audio data
        """
        if to_format.lower() == "pcm16" or to_format.lower() == "raw/lpcm16":
            return audio_data
        
        # G.711 μ-law encoding
        elif to_format.lower() in ["ulaw", "g711/ulaw"]:
            return AudioUtils._pcm16_to_ulaw(audio_data)
        
        # G.711 A-law encoding
        elif to_format.lower() in ["alaw", "g711/alaw"]:
            return AudioUtils._pcm16_to_alaw(audio_data)
        
        else:
            logger.warning(f"Unsupported audio format: {to_format}")
            return audio_data
    
    @staticmethod
    def _ulaw_to_pcm16(ulaw_data: bytes) -> bytes:
        """Convert μ-law to PCM16."""
        # μ-law decompression table
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
        
        pcm_samples = []
        for byte in ulaw_data:
            pcm_samples.append(ulaw_table[byte])
        
        return struct.pack(f'<{len(pcm_samples)}h', *pcm_samples)
    
    @staticmethod
    def _pcm16_to_ulaw(pcm_data: bytes) -> bytes:
        """Convert PCM16 to μ-law."""
        # Simplified μ-law compression
        samples = struct.unpack(f'<{len(pcm_data)//2}h', pcm_data)
        ulaw_bytes = []
        
        for sample in samples:
            # Bias and scale
            sample = max(-32768, min(32767, sample))
            if sample < 0:
                sample = -sample
                sign = 0x80
            else:
                sign = 0x00
            
            # Compress using μ-law algorithm (simplified)
            if sample < 31:
                ulaw_byte = sign | (sample >> 1)
            else:
                # Find the position of the highest set bit
                position = 0
                temp = sample >> 5
                while temp != 0:
                    temp >>= 1
                    position += 1
                
                position = min(position, 7)
                ulaw_byte = sign | (position << 4) | ((sample >> (position + 1)) & 0x0F)
            
            ulaw_bytes.append(ulaw_byte ^ 0xFF)  # Complement
        
        return bytes(ulaw_bytes)
    
    @staticmethod
    def _alaw_to_pcm16(alaw_data: bytes) -> bytes:
        """Convert A-law to PCM16 (simplified implementation)."""
        # This is a simplified A-law decoder
        pcm_samples = []
        for byte in alaw_data:
            # Basic A-law decompression (would need full implementation for production)
            pcm_samples.append(int((byte - 128) * 256))
        
        return struct.pack(f'<{len(pcm_samples)}h', *pcm_samples)
    
    @staticmethod  
    def _pcm16_to_alaw(pcm_data: bytes) -> bytes:
        """Convert PCM16 to A-law (simplified implementation)."""
        samples = struct.unpack(f'<{len(pcm_data)//2}h', pcm_data)
        alaw_bytes = []
        
        for sample in samples:
            # Basic A-law compression (would need full implementation for production)
            alaw_byte = max(0, min(255, (sample // 256) + 128))
            alaw_bytes.append(alaw_byte)
        
        return bytes(alaw_bytes) 