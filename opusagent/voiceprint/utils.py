from pathlib import Path
from typing import List, Tuple, Union

import numpy as np
from resemblyzer import preprocess_wav


def preprocess_audio(audio_buffer: Union[str, Path, np.ndarray]) -> np.ndarray:
    """
    Preprocess audio data for voiceprint analysis.

    This function takes raw audio data and applies preprocessing steps required
    by the resemblyzer library for voiceprint embedding generation.

    Args:
        audio_buffer: Audio data as file path (str/Path) or numpy array

    Returns:
        np.ndarray: Preprocessed audio data ready for embedding generation

    Raises:
        ValueError: If the audio buffer is empty or invalid
        TypeError: If the audio buffer format is not supported
    """
    return preprocess_wav(audio_buffer)


def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """
    Normalize a voiceprint embedding vector to unit length.

    This function performs L2 normalization on embedding vectors to ensure
    they have unit length (norm = 1.0). This is essential for accurate
    voiceprint comparison and similarity calculations.

    The function includes robust error handling for edge cases:
    - Zero vectors
    - Vectors with very small norms (numerical instability)
    - Vectors with infinite values (overflow handling)

    Args:
        embedding: A numpy array representing the voiceprint embedding vector

    Returns:
        np.ndarray: The normalized embedding vector with unit length

    Raises:
        ValueError: If the embedding is a zero vector or has very small norm
                   that would cause numerical instability
        TypeError: If the input is not a numpy array

    Example:
        >>> embedding = np.array([1.0, 2.0, 3.0])
        >>> normalized = normalize_embedding(embedding)
        >>> np.linalg.norm(normalized)  # Should be approximately 1.0
        1.0
    """
    norm = np.linalg.norm(embedding)
    if norm == 0:
        raise ValueError("Cannot normalize zero vector")
    if norm < 1e-10:  # Check for very small norms that could cause numerical issues
        raise ValueError(
            "Cannot normalize vector with very small norm (numerical instability)"
        )
    if np.isinf(norm):  # Handle infinite norm by using a more robust approach
        # For overflow cases, try to normalize by scaling down first
        max_val = np.max(np.abs(embedding))
        if max_val == 0:
            raise ValueError("Cannot normalize zero vector")
        # Scale down to avoid overflow
        scaled_embedding = embedding / max_val
        scaled_norm = np.linalg.norm(scaled_embedding)
        if scaled_norm < 1e-10:
            raise ValueError(
                "Cannot normalize vector with very small norm (numerical instability)"
            )
        return scaled_embedding / scaled_norm
    return embedding / norm
