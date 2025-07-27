"""
Voiceprint Models Module

This module defines the core data models for voiceprint functionality in the OpusAgent system.
It provides classes for representing voiceprint data and configuration settings used in
voice recognition and caller identification.

Classes:
    Voiceprint: Represents a single voiceprint with caller identification and embedding data
    VoiceFingerprintConfig: Configuration settings for voiceprint recognition parameters

Dependencies:
    - pydantic: For data validation and serialization
    - numpy: For numerical array operations
    - typing: For type hints
"""

from typing import Any, Dict, List, Optional, Union

import numpy as np
from pydantic import BaseModel, ConfigDict, field_validator


class Voiceprint(BaseModel):
    """
    Represents a voiceprint for caller identification.

    A voiceprint contains the unique audio characteristics of a caller's voice,
    stored as an embedding vector along with metadata for identification and tracking.

    Attributes:
        caller_id (str): Unique identifier for the caller
        embedding (np.ndarray): Numerical representation of voice characteristics
        metadata (Dict[str, Any]): Additional caller information and context
        created_at (Optional[str]): Timestamp when voiceprint was created
        last_seen (Optional[str]): Timestamp of last voiceprint usage

    Example:
        >>> voiceprint = Voiceprint(
        ...     caller_id="user_123",
        ...     embedding=np.array([0.1, 0.2, 0.3]),
        ...     metadata={"age": 30, "gender": "male"}
        ... )
    """

    caller_id: str
    embedding: np.ndarray
    metadata: Dict[str, Any] = {}
    created_at: Optional[str] = None
    last_seen: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("embedding", mode="before")
    @classmethod
    def validate_embedding(cls, v: Union[List[float], np.ndarray]) -> np.ndarray:
        """
        Validate and convert embedding input to numpy array.

        Ensures the embedding is in the correct format (numpy array) for processing.
        Converts lists to numpy arrays and validates the input type.

        Args:
            v: Input embedding as list or numpy array

        Returns:
            np.ndarray: Validated numpy array representation of the embedding

        Raises:
            ValueError: If input is neither a list nor numpy array

        Example:
            >>> Voiceprint.validate_embedding([0.1, 0.2, 0.3])
            array([0.1, 0.2, 0.3], dtype=float32)
        """
        if isinstance(v, list):
            return np.array(v, dtype=np.float32)
        if isinstance(v, np.ndarray):
            return v
        raise ValueError(f"Embedding must be a list or numpy array, got {type(v)}")


class VoiceFingerprintConfig(BaseModel):
    """
    Configuration settings for voiceprint recognition and processing.

    Defines the parameters used for voiceprint enrollment, matching, and quality
    control in the voice recognition system.

    Attributes:
        similarity_threshold (float): Minimum similarity score for voiceprint matching
        enrollment_duration (float): Required audio duration for voiceprint enrollment
        min_audio_quality (float): Minimum audio quality score for processing
        max_voiceprints_per_caller (int): Maximum voiceprints allowed per caller

    Example:
        >>> config = VoiceFingerprintConfig(
        ...     similarity_threshold=0.8,
        ...     enrollment_duration=10.0,
        ...     min_audio_quality=0.7
        ... )
    """

    similarity_threshold: float = 0.75
    enrollment_duration: float = 5.0  # seconds
    min_audio_quality: float = 0.6
    max_voiceprints_per_caller: int = 3
