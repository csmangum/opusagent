"""
Silero Voice Activity Detection (VAD) implementation.

This module provides a wrapper around the Silero VAD model for real-time
voice activity detection in audio streams. Silero VAD is a lightweight,
on-device voice activity detection model that can run efficiently on CPU.

The model supports both 8kHz and 16kHz sample rates and automatically
handles audio chunking for variable-length inputs.
"""

from typing import Any, Dict, Optional

import numpy as np
import torch

from .base_vad import BaseVAD


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
        device: Device to run inference on ('cpu' or 'cuda')
        chunk_size: Size of audio chunks for processing (256 for 8kHz, 512 for 16kHz)

    Example:
        >>> vad = SileroVAD()
        >>> config = {'sample_rate': 16000, 'threshold': 0.5}
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
        self.sample_rate: int = 16000
        self.threshold: float = 0.5
        self.device: str = "cpu"
        self.chunk_size: int = 512  # Default chunk size for 16kHz

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the Silero VAD model with the provided configuration.

        Args:
            config: Configuration dictionary containing:
                - sample_rate: Audio sample rate in Hz (8000 or 16000)
                - threshold: Speech detection threshold (0.0 to 1.0)
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
        self.sample_rate = config.get("sample_rate", 16000)
        self.threshold = config.get("threshold", 0.5)
        self.device = config.get("device", "cpu")
        self.chunk_size = config.get("chunk_size", 512)

        # Validate configuration parameters
        if self.sample_rate not in [8000, 16000]:
            raise ValueError(
                f"Unsupported sample rate: {self.sample_rate}. Must be 8000 or 16000 Hz"
            )

        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError(
                f"Threshold must be between 0.0 and 1.0, got: {self.threshold}"
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
        Process audio data to detect speech activity.

        This method takes audio data and returns speech detection results.
        The audio is automatically chunked if it doesn't match the expected
        chunk size, and results are aggregated across chunks.

        Args:
            audio_data: Input audio as numpy array (float32, -1.0 to 1.0, mono)
                       Can be any length; will be automatically chunked

        Returns:
            Dictionary containing:
                - speech_prob: Maximum speech probability across all chunks (0.0 to 1.0)
                - is_speech: Boolean indicating if speech was detected

        Raises:
            RuntimeError: If model is not initialized

        Note:
            For variable-length audio, the method splits the audio into chunks
            and uses the maximum speech probability across all chunks as the
            final result. Short audio is padded with zeros if necessary.
        """
        if self.model is None:
            raise RuntimeError(
                "Silero VAD model not initialized. Call initialize() first."
            )

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
            is_speech = max_speech_prob > self.threshold

            return {"speech_prob": max_speech_prob, "is_speech": is_speech}
        else:
            # Audio is already the correct size - process directly
            audio_tensor = torch.from_numpy(audio_data).float()
            speech_prob = self.model(audio_tensor, self.sample_rate).item()
            is_speech = speech_prob > self.threshold
            return {"speech_prob": speech_prob, "is_speech": is_speech}

    def reset(self) -> None:
        """
        Reset the VAD state.

        Silero VAD is stateless, so this method does nothing.
        Included for compatibility with the BaseVAD interface.
        """
        pass  # No state to reset for Silero VAD

    def cleanup(self) -> None:
        """
        Clean up resources used by the VAD model.

        This method releases the model from memory. Call this when
        you're done using the VAD to free up memory.
        """
        self.model = None
