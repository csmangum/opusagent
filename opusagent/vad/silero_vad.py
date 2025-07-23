"""
Silero Voice Activity Detection (VAD) implementation.

This module provides a wrapper around the Silero VAD model for real-time
voice activity detection in audio streams. Silero VAD is a lightweight,
on-device voice activity detection model that can run efficiently on CPU.

The model supports both 8kHz and 16kHz sample rates and automatically
handles audio chunking for variable-length inputs.
"""

import time
from typing import Any, Dict, Optional

import numpy as np
import torch

from .base_vad import BaseVAD
from opusagent.config.constants import DEFAULT_SAMPLE_RATE, DEFAULT_VAD_CHUNK_SIZE


class SileroVAD(BaseVAD):
    """
    Silero Voice Activity Detection implementation.

    This class provides a wrapper around the Silero VAD model for detecting
    speech activity in audio streams. It supports real-time processing with
    configurable thresholds and automatic audio chunking.

    Attributes:
        model: The loaded Silero VAD model instance
        sample_rate: Audio sample rate in Hz (8000 or 16000)
        threshold: Speech detection threshold (0.0 to 1.0)
        silence_threshold: Silence detection threshold (0.0 to 1.0)
        min_speech_duration_ms: Minimum duration for valid speech segments
        device: Device to run inference on ('cpu' or 'cuda')
        chunk_size: Size of audio chunks for processing (256 for 8kHz, 512 for 16kHz)
        force_stop_timeout_ms: Timeout to force speech stop event

    Example:
        >>> vad = SileroVAD()
        >>> config = {'sample_rate': 16000, 'threshold': 0.5, 'silence_threshold': 0.6}
        >>> vad.initialize(config)
        >>> result = vad.process_audio(audio_data)
        >>> print(f"Speech detected: {result['is_speech']}")
    """

    def __init__(self) -> None:
        """
        Initialize SileroVAD with default configuration.

        The model is not loaded until initialize() is called with a config.
        """
        self.model: Optional[Any] = None
        self.sample_rate: int = DEFAULT_SAMPLE_RATE
        self.threshold: float = 0.5
        self.silence_threshold: float = 0.6
        self.min_speech_duration_ms: int = 500
        self.force_stop_timeout_ms: int = 2000
        self.device: str = "cpu"
        self.chunk_size: int = DEFAULT_VAD_CHUNK_SIZE  # Default chunk size for 16kHz
        
        # State tracking for enhanced detection
        self._speech_start_time: Optional[float] = None
        self._last_speech_time: Optional[float] = None
        self._consecutive_speech_count: int = 0
        self._consecutive_silence_count: int = 0

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the Silero VAD model with the provided configuration.

        Args:
            config: Configuration dictionary containing:
                - sample_rate: Audio sample rate in Hz (8000 or 16000)
                - threshold: Speech detection threshold (0.0 to 1.0)
                - silence_threshold: Silence detection threshold (0.0 to 1.0)
                - min_speech_duration_ms: Minimum duration for valid speech segments
                - force_stop_timeout_ms: Timeout to force speech stop event
                - device: Device to run inference on ('cpu' or 'cuda')
                - chunk_size: Size of audio chunks for processing

        Raises:
            RuntimeError: If silero-vad package is not installed
            ValueError: If invalid configuration parameters are provided

        Note:
            The chunk_size will be automatically adjusted based on sample_rate:
            - 8kHz: chunk_size = 256
            - 16kHz: chunk_size = 512
        """
        self.sample_rate = config.get("sample_rate", DEFAULT_SAMPLE_RATE)
        self.threshold = config.get("threshold", 0.5)
        self.silence_threshold = config.get("silence_threshold", 0.6)
        self.min_speech_duration_ms = config.get("min_speech_duration_ms", 500)
        self.force_stop_timeout_ms = config.get("force_stop_timeout_ms", 2000)
        self.device = config.get("device", "cpu")
        self.chunk_size = config.get("chunk_size", DEFAULT_VAD_CHUNK_SIZE)

        # Validate configuration parameters
        if self.sample_rate not in [8000, 16000]:
            raise ValueError(
                f"Unsupported sample rate: {self.sample_rate}. Must be 8000 or 16000 Hz"
            )

        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError(
                f"Threshold must be between 0.0 and 1.0, got: {self.threshold}"
            )

        if not 0.0 <= self.silence_threshold <= 1.0:
            raise ValueError(
                f"Silence threshold must be between 0.0 and 1.0, got: {self.silence_threshold}"
            )

        if self.min_speech_duration_ms < 0:
            raise ValueError(
                f"Minimum speech duration must be non-negative, got: {self.min_speech_duration_ms}"
            )

        # Automatically adjust chunk size based on sample rate
        if self.sample_rate == 16000 and self.chunk_size != 512:
            self.chunk_size = 512
        elif self.sample_rate == 8000 and self.chunk_size != 256:
            self.chunk_size = 256

        try:
            from silero_vad import load_silero_vad

            # Load the Silero VAD model (uses default device)
            self.model = load_silero_vad()
        except ImportError:
            raise RuntimeError(
                "silero-vad package not installed. Please install with: "
                "pip install silero-vad"
            )

    def process_audio(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        Process audio data to detect speech activity with enhanced state management.

        This method takes audio data and returns speech detection results with
        improved state tracking to ensure complete VAD event sequences.

        Args:
            audio_data: Input audio as numpy array (float32, -1.0 to 1.0, mono)
                       Can be any length; will be automatically chunked

        Returns:
            Dictionary containing:
                - speech_prob: Maximum speech probability across all chunks (0.0 to 1.0)
                - is_speech: Boolean indicating if speech was detected
                - speech_state: Current speech state ('started', 'active', 'stopped', 'idle')
                - force_stop: Boolean indicating if timeout-based stop should occur
                - speech_duration_ms: Duration of current speech segment (if active)

        Raises:
            RuntimeError: If model is not initialized
        """
        if self.model is None:
            raise RuntimeError(
                "Silero VAD model not initialized. Call initialize() first."
            )

        current_time = time.time()

        # Validate input audio format
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # Handle variable-length input by splitting into chunks
        if len(audio_data) != self.chunk_size:
            # Split audio into chunks of the correct size
            chunks = []
            for i in range(0, len(audio_data), self.chunk_size):
                chunk = audio_data[i : i + self.chunk_size]
                if len(chunk) == self.chunk_size:
                    chunks.append(chunk)

            if not chunks:
                # Audio is too short, pad with zeros
                padded_audio = np.zeros(self.chunk_size, dtype=np.float32)
                padded_audio[: len(audio_data)] = audio_data
                chunks = [padded_audio]

            # Process each chunk and aggregate results
            speech_probs = []
            for chunk in chunks:
                audio_tensor = torch.from_numpy(chunk).float()
                speech_prob = self.model(audio_tensor, self.sample_rate).item()
                speech_probs.append(speech_prob)

            # Use the maximum probability as the overall result
            max_speech_prob = max(speech_probs) if speech_probs else 0.0
        else:
            # Audio is already the correct size - process directly
            audio_tensor = torch.from_numpy(audio_data).float()
            max_speech_prob = self.model(audio_tensor, self.sample_rate).item()

        # Enhanced speech detection with improved state management
        is_speech = max_speech_prob > self.threshold
        is_silence = max_speech_prob < self.silence_threshold

        # Update consecutive counters
        if is_speech:
            self._consecutive_speech_count += 1
            self._consecutive_silence_count = 0
        elif is_silence:
            self._consecutive_silence_count += 1
            self._consecutive_speech_count = 0
        else:
            # In between thresholds - maintain current state
            pass

        # Determine speech state
        speech_state = "idle"
        force_stop = False
        speech_duration_ms = 0

        if self._speech_start_time is not None:
            # Currently in speech
            speech_duration_ms = (current_time - self._speech_start_time) * 1000
            speech_state = "active"
            
            # Check for forced stop due to timeout
            if speech_duration_ms > self.force_stop_timeout_ms:
                force_stop = True
                speech_state = "stopped"
                self._speech_start_time = None
            
            # Check for natural stop due to silence
            elif is_silence and self._consecutive_silence_count >= 3:
                # Only stop if we've had sufficient speech duration
                if speech_duration_ms >= self.min_speech_duration_ms:
                    speech_state = "stopped"
                    self._speech_start_time = None
                    self._last_speech_time = current_time
        else:
            # Not currently in speech
            if is_speech and self._consecutive_speech_count >= 2:
                # Start new speech segment
                self._speech_start_time = current_time
                speech_state = "started"

        return {
            "speech_prob": max_speech_prob,
            "is_speech": is_speech,
            "speech_state": speech_state,
            "force_stop": force_stop,
            "speech_duration_ms": speech_duration_ms,
            "consecutive_speech_count": self._consecutive_speech_count,
            "consecutive_silence_count": self._consecutive_silence_count,
        }

    def reset(self) -> None:
        """
        Reset the VAD state.

        Resets all internal state tracking variables to ensure clean state
        for new audio processing sessions.
        """
        self._speech_start_time = None
        self._last_speech_time = None
        self._consecutive_speech_count = 0
        self._consecutive_silence_count = 0

    def cleanup(self) -> None:
        """
        Clean up resources used by the VAD model.

        This method releases the model from memory and resets state.
        Call this when you're done using the VAD to free up memory.
        """
        self.model = None
        self.reset()
