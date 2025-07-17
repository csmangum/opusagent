"""
Base transcriber class and shared utilities for the transcription module.

This module provides the abstract base class for transcription backends
and common utility functions used across different transcription implementations.
"""

import logging
import numpy as np
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .models import TranscriptionConfig, TranscriptionResult

class BaseTranscriber(ABC):
    """Abstract base class for audio transcription."""

    def __init__(self, config: TranscriptionConfig):
        """Initialize the transcriber with configuration.

        Args:
            config: Transcription configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._initialized = False
        self._audio_buffer = []
        self._session_active = False

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the transcription backend.

        Returns:
            True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    async def transcribe_chunk(self, audio_data: bytes) -> TranscriptionResult:
        """Transcribe a chunk of audio data.

        Args:
            audio_data: Raw audio data (16-bit PCM)

        Returns:
            TranscriptionResult with partial or complete text
        """
        pass

    @abstractmethod
    async def finalize(self) -> TranscriptionResult:
        """Finalize transcription and return complete result.

        Returns:
            TranscriptionResult with final transcription
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up transcription resources."""
        pass

    def start_session(self) -> None:
        """Start a new transcription session."""
        self._audio_buffer.clear()
        self._session_active = True
        self.logger.debug("Transcription session started")

    def end_session(self) -> None:
        """End the current transcription session."""
        self._session_active = False
        self.logger.debug("Transcription session ended")

    def reset_session(self) -> None:
        """Reset session state without destroying the transcriber.

        This method clears session-specific state (audio buffer, accumulated text)
        without destroying the underlying transcriber resources. Use this when
        you want to process multiple audio files with the same transcriber instance.
        """
        self._audio_buffer.clear()
        self._session_active = False
        self.logger.debug("Transcription session reset")

    def _convert_audio_for_processing(self, audio_data: bytes) -> np.ndarray:
        """Convert raw audio bytes to numpy array for processing.

        Args:
            audio_data: Raw audio bytes (16-bit PCM)

        Returns:
            Float32 numpy array normalized to [-1, 1]
        """
        try:
            # Convert bytes to int16 array
            audio_int16 = np.frombuffer(audio_data, dtype=np.int16)

            # Convert to float32 and normalize
            audio_float32 = audio_int16.astype(np.float32) / 32768.0

            return audio_float32
        except Exception as e:
            self.logger.error(f"Error converting audio data: {e}")
            return np.array([], dtype=np.float32)

    def _resample_audio_for_pocketsphinx(self, audio_data: bytes, 
                                       original_rate: int = 24000,
                                       target_rate: int = 16000) -> bytes:
        """Resample audio to 16kHz for optimal PocketSphinx performance.
        
        This is critical for PocketSphinx accuracy - it expects 16kHz audio.
        
        Args:
            audio_data: Raw audio bytes (16-bit PCM)
            original_rate: Original sample rate (default: 24000)
            target_rate: Target sample rate (default: 16000)
            
        Returns:
            Resampled audio bytes at target sample rate
        """
        try:
            # Convert bytes to numpy array
            audio_int16 = np.frombuffer(audio_data, dtype=np.int16)
            
            # Simple linear interpolation resampling
            # This is a basic implementation - for production, consider using scipy.signal.resample
            if original_rate == target_rate:
                return audio_data
                
            # Calculate resampling ratio
            ratio = target_rate / original_rate
            new_length = int(len(audio_int16) * ratio)
            
            # Simple linear interpolation
            resampled = np.zeros(new_length, dtype=np.int16)
            for i in range(new_length):
                old_index = i / ratio
                old_index_int = int(old_index)
                old_index_frac = old_index - old_index_int
                
                if old_index_int >= len(audio_int16) - 1:
                    resampled[i] = audio_int16[-1]
                else:
                    # Linear interpolation between samples
                    sample1 = audio_int16[old_index_int]
                    sample2 = audio_int16[old_index_int + 1]
                    resampled[i] = int(sample1 * (1 - old_index_frac) + sample2 * old_index_frac)
            
            return resampled.tobytes()
            
        except Exception as e:
            self.logger.error(f"Error resampling audio: {e}")
            # Return original data if resampling fails
            return audio_data

    def _apply_audio_preprocessing(self, audio_array: np.ndarray, 
                                 preprocessing_type: str) -> np.ndarray:
        """Apply audio preprocessing based on optimization analysis.
        
        Args:
            audio_array: Float32 audio array [-1, 1]
            preprocessing_type: Type of preprocessing to apply
            
        Returns:
            Preprocessed audio array
        """
        try:
            if preprocessing_type == "none":
                return audio_array
                
            elif preprocessing_type == "normalize":
                # Normalize audio levels (recommended for best performance)
                if len(audio_array) > 0:
                    max_val = np.max(np.abs(audio_array))
                    if max_val > 0:
                        return audio_array / max_val
                return audio_array
                
            elif preprocessing_type == "amplify":
                # Amplify audio (similar to normalize)
                if len(audio_array) > 0:
                    max_val = np.max(np.abs(audio_array))
                    if max_val > 0 and max_val < 0.5:
                        return audio_array * (0.5 / max_val)
                return audio_array
                
            elif preprocessing_type == "noise_reduction":
                # Simple noise reduction (avoid - reduces accuracy)
                # This is a placeholder - avoid using this preprocessing
                self.logger.warning("Noise reduction preprocessing reduces PocketSphinx accuracy")
                return audio_array
                
            elif preprocessing_type == "silence_trim":
                # Trim silence from beginning and end
                if len(audio_array) == 0:
                    return audio_array
                    
                # Find non-silent regions
                threshold = 0.01
                non_silent = np.abs(audio_array) > threshold
                
                if np.any(non_silent):
                    start = np.argmax(non_silent)
                    end = len(audio_array) - np.argmax(non_silent[::-1])
                    return audio_array[start:end]
                return audio_array
                
            else:
                self.logger.warning(f"Unknown preprocessing type: {preprocessing_type}")
                return audio_array
                
        except Exception as e:
            self.logger.error(f"Error in audio preprocessing: {e}")
            return audio_array 