from resemblyzer import preprocess_wav
import numpy as np

def preprocess_audio(audio_buffer):
    return preprocess_wav(audio_buffer)

def normalize_embedding(embedding):
    return embedding / np.linalg.norm(embedding) 