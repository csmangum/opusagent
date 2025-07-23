from resemblyzer import preprocess_wav
import numpy as np

def preprocess_audio(audio_buffer):
    return preprocess_wav(audio_buffer)

def normalize_embedding(embedding):
    norm = np.linalg.norm(embedding)
    if norm == 0:
        raise ValueError("Cannot normalize zero vector")
    if norm < 1e-10:  # Check for very small norms that could cause numerical issues
        raise ValueError("Cannot normalize vector with very small norm (numerical instability)")
    if np.isinf(norm):  # Handle infinite norm by using a more robust approach
        # For overflow cases, try to normalize by scaling down first
        max_val = np.max(np.abs(embedding))
        if max_val == 0:
            raise ValueError("Cannot normalize zero vector")
        # Scale down to avoid overflow
        scaled_embedding = embedding / max_val
        scaled_norm = np.linalg.norm(scaled_embedding)
        if scaled_norm < 1e-10:
            raise ValueError("Cannot normalize vector with very small norm (numerical instability)")
        return scaled_embedding / scaled_norm
    return embedding / norm 