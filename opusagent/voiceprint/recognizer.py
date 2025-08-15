"""
Voice Recognition Module for OpusAgent

This module provides voice recognition capabilities for identifying callers based on
voice fingerprints. It uses the Resemblyzer library to generate voice embeddings
and compare them against stored voiceprints to identify known callers.

The main component is the OpusAgentVoiceRecognizer class which handles:
- Voice embedding generation from audio buffers
- Caller enrollment with voiceprint storage
- Voice matching against stored voiceprints
- Similarity scoring and threshold-based identification

Key Features:
- Speaker identification through voice fingerprinting
- Configurable similarity thresholds
- Metadata storage for enrolled callers
- Support for multiple storage backends

Example Usage:
    >>> from opusagent.voiceprint.recognizer import OpusAgentVoiceRecognizer
    >>> recognizer = OpusAgentVoiceRecognizer()
    >>>
    >>> # Enroll a new caller
    >>> voiceprint = recognizer.enroll_caller("john_doe", audio_data)
    >>>
    >>> # Identify an incoming caller
    >>> result = recognizer.match_caller(incoming_audio)
    >>> if result:
    ...     caller_id, similarity, metadata = result
    ...     print(f"Caller identified: {caller_id}")

Dependencies:
    - resemblyzer: For voice embedding generation
    - numpy: For numerical operations
    - scipy: For similarity calculations
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
from scipy.spatial.distance import cosine

from .config import VoiceFingerprintConfig
from .models import Voiceprint
from .storage import JSONStorage


class OpusAgentVoiceRecognizer:
    """
    Voice recognition system for identifying callers based on voice fingerprints.

    This class provides functionality to enroll new callers by creating voice embeddings
    and match incoming audio against stored voiceprints to identify known callers.

    Attributes:
        encoder (VoiceEncoder): The voice encoder used to generate embeddings
        storage (JSONStorage): Backend storage for voiceprint data
        config (VoiceFingerprintConfig): Configuration settings for voice recognition
    """

    def __init__(self, storage_backend: Optional[Any] = None) -> None:
        """
        Initialize the voice recognizer.

        Args:
            storage_backend (Any, optional): Storage backend for voiceprints.
                Defaults to JSONStorage if not provided.
        """
        self.encoder: VoiceEncoder = VoiceEncoder()
        self.storage: Any = storage_backend or JSONStorage()
        self.config: VoiceFingerprintConfig = VoiceFingerprintConfig()

    def get_embedding(self, audio_buffer: np.ndarray) -> np.ndarray:
        """
        Generate voice embedding from audio buffer.

        This method processes the raw audio buffer and generates a numerical
        representation (embedding) that captures the unique characteristics
        of the speaker's voice.

        Args:
            audio_buffer (np.ndarray): Raw audio data as numpy array

        Returns:
            numpy.ndarray: Voice embedding as a float32 array

        Raises:
            ValueError: If audio_buffer is empty or invalid
        """
        wav = preprocess_wav(audio_buffer)
        embedding = self.encoder.embed_utterance(wav)
        return np.array(embedding, dtype=np.float32)

    def match_caller(
        self, audio_buffer: np.ndarray
    ) -> Optional[Tuple[str, float, Dict[str, Any]]]:
        """
        Match incoming voice to stored voiceprints.

        This method compares the voice embedding of the incoming audio against
        all stored voiceprints to identify if the caller is known. Returns
        the best match if similarity exceeds the configured threshold.

        Args:
            audio_buffer (np.ndarray): Raw audio data from the caller as numpy array

        Returns:
            tuple or None: If match found, returns (caller_id, similarity_score, metadata).
                Returns None if no match exceeds the similarity threshold.

        Example:
            >>> result = recognizer.match_caller(audio_data)
            >>> if result:
            ...     caller_id, similarity, metadata = result
            ...     print(f"Caller identified: {caller_id} (similarity: {similarity:.2f})")
        """
        new_embedding = self.get_embedding(audio_buffer)

        matches: List[Tuple[str, float, Dict[str, Any]]] = []
        for voiceprint in self.storage.get_all():
            similarity = float(1 - cosine(new_embedding, voiceprint.embedding))
            if similarity > self.config.similarity_threshold:
                matches.append((voiceprint.caller_id, similarity, voiceprint.metadata))

        if matches:
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[0]  # (caller_id, similarity, metadata)
        return None

    def enroll_caller(
        self,
        caller_id: str,
        audio_buffer: np.ndarray,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Voiceprint:
        """
        Enroll a new caller by storing their voiceprint.

        This method creates a voiceprint for a new caller by generating an
        embedding from their audio sample and storing it with associated metadata.

        Args:
            caller_id (str): Unique identifier for the caller
            audio_buffer (np.ndarray): Raw audio data from the caller as numpy array
            metadata (dict, optional): Additional metadata to store with the voiceprint.
                Defaults to empty dictionary.

        Returns:
            Voiceprint: The created voiceprint object

        Raises:
            ValueError: If caller_id is empty or audio_buffer is invalid
            StorageError: If voiceprint cannot be saved to storage

        Example:
            >>> voiceprint = recognizer.enroll_caller(
            ...     caller_id="john_doe",
            ...     audio_buffer=audio_data,
            ...     metadata={"name": "John Doe", "phone": "555-1234"}
            ... )
        """
        embedding = self.get_embedding(audio_buffer)
        voiceprint = Voiceprint(
            caller_id=caller_id, embedding=embedding, metadata=metadata or {}
        )
        self.storage.save(voiceprint)
        return voiceprint
