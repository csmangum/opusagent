"""
Audio data validation and error handling utilities.

This module provides robust validation and decoding of audio data with
comprehensive error handling for malformed base64, corrupted audio,
and other common failure scenarios.
"""

import base64
import binascii
import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class AudioDataValidator:
    """Validates and decodes audio data with comprehensive error handling."""
    
    @staticmethod
    def validate_and_decode_audio(
        audio_chunk_b64: str, 
        expected_size_range: Optional[Tuple[int, int]] = None,
        fallback_silence_ms: int = 100,
        sample_rate: int = 16000
    ) -> bytes:
        """
        Validate and decode base64 audio data with comprehensive error handling.
        
        Args:
            audio_chunk_b64: Base64 encoded audio data
            expected_size_range: Optional (min_size, max_size) tuple for validation
            fallback_silence_ms: Duration of silence to return on failure (milliseconds)
            sample_rate: Sample rate for calculating fallback silence size
            
        Returns:
            Decoded audio bytes or fallback silence
            
        Raises:
            ValueError: For validation errors (logged but not re-raised)
        """
        try:
            # Validate input type and format
            if not audio_chunk_b64 or not isinstance(audio_chunk_b64, str):
                raise ValueError("Invalid audio chunk: must be non-empty string")
            
            # Check for valid base64 characters
            if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', audio_chunk_b64):
                raise ValueError("Invalid base64 format: contains invalid characters")
            
            # Validate padding
            padding_length = len(audio_chunk_b64) % 4
            if padding_length != 0:
                raise ValueError(f"Invalid base64 padding: length {len(audio_chunk_b64)} not divisible by 4")
            
            # Decode with error handling
            try:
                audio_bytes = base64.b64decode(audio_chunk_b64, validate=True)
            except binascii.Error as e:
                raise ValueError(f"Base64 decoding failed: {e}")
            
            # Validate decoded data
            if not audio_bytes:
                raise ValueError("Decoded audio data is empty")
            
            # Check size constraints if specified
            if expected_size_range:
                min_size, max_size = expected_size_range
                if len(audio_bytes) < min_size:
                    raise ValueError(f"Audio size {len(audio_bytes)} below minimum {min_size}")
                if len(audio_bytes) > max_size:
                    raise ValueError(f"Audio size {len(audio_bytes)} above maximum {max_size}")
            
            # Validate audio format (basic PCM16 check)
            if len(audio_bytes) % 2 != 0:
                raise ValueError(f"Audio data length {len(audio_bytes)} not even (PCM16 requires 2 bytes per sample)")
            
            logger.debug(f"Successfully validated and decoded audio: {len(audio_bytes)} bytes")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Audio validation failed: {e}")
            # Return silence as fallback
            silence_size = int(fallback_silence_ms * sample_rate * 2 / 1000)  # 2 bytes per sample
            fallback_silence = b"\x00" * silence_size
            logger.info(f"Returning {fallback_silence_ms}ms of silence as fallback ({silence_size} bytes)")
            return fallback_silence
    
    @staticmethod
    def validate_audio_quality(audio_bytes: bytes, sample_rate: int = 16000) -> dict:
        """
        Validate audio quality and detect potential issues.
        
        Args:
            audio_bytes: Raw audio data
            sample_rate: Sample rate for calculations
            
        Returns:
            Dictionary with quality metrics and issues
        """
        try:
            import numpy as np
            
            # Convert to numpy array
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # Calculate basic metrics
            max_amplitude = np.max(np.abs(audio_array))
            rms_level = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            zero_crossings = np.sum(np.diff(np.sign(audio_array)) != 0)
            
            # Detect issues
            issues = []
            if max_amplitude == 0:
                issues.append("silent_audio")
            elif max_amplitude > 32000:  # Near clipping
                issues.append("near_clipping")
            elif rms_level < 100:  # Very quiet
                issues.append("very_quiet")
            
            # Calculate duration
            duration_ms = len(audio_array) / sample_rate * 1000
            
            return {
                'valid': True,
                'duration_ms': duration_ms,
                'max_amplitude': int(max_amplitude),
                'rms_level': float(rms_level),
                'zero_crossings': int(zero_crossings),
                'issues': issues,
                'sample_count': len(audio_array)
            }
            
        except Exception as e:
            logger.warning(f"Audio quality validation failed: {e}")
            return {
                'valid': False,
                'error': str(e),
                'issues': ['quality_check_failed']
            }
    
    @staticmethod
    def sanitize_audio_data(audio_bytes: bytes, target_size: Optional[int] = None) -> bytes:
        """
        Sanitize audio data by removing invalid bytes and ensuring proper format.
        
        Args:
            audio_bytes: Raw audio data
            target_size: Optional target size (will pad or truncate)
            
        Returns:
            Sanitized audio bytes
        """
        try:
            # Ensure even length for PCM16
            if len(audio_bytes) % 2 != 0:
                audio_bytes = audio_bytes[:-1]  # Remove last byte
                logger.warning("Truncated audio to ensure even PCM16 format")
            
            # Handle target size
            if target_size:
                if len(audio_bytes) > target_size:
                    # Truncate
                    audio_bytes = audio_bytes[:target_size]
                    logger.info(f"Truncated audio to {target_size} bytes")
                elif len(audio_bytes) < target_size:
                    # Pad with silence
                    padding_needed = target_size - len(audio_bytes)
                    audio_bytes += b"\x00" * padding_needed
                    logger.info(f"Padded audio with {padding_needed} bytes of silence")
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Audio sanitization failed: {e}")
            # Return safe fallback
            return b"\x00" * 3200  # 100ms at 16kHz 