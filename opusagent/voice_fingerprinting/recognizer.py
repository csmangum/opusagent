import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
from scipy.spatial.distance import cosine
from .storage import JSONStorage
from .config import VoiceFingerprintConfig
from .models import Voiceprint

class OpusAgentVoiceRecognizer:
    def __init__(self, storage_backend=None):
        self.encoder = VoiceEncoder()
        self.storage = storage_backend or JSONStorage()
        self.config = VoiceFingerprintConfig()
    
    def get_embedding(self, audio_buffer):
        """Generate voice embedding from audio buffer."""
        wav = preprocess_wav(audio_buffer)
        embedding = self.encoder.embed_utterance(wav)
        return np.array(embedding, dtype=np.float32)
    
    def match_caller(self, audio_buffer):
        """Match incoming voice to stored voiceprints."""
        new_embedding = self.get_embedding(audio_buffer)
        
        matches = []
        for voiceprint in self.storage.get_all():
            similarity = 1 - cosine(new_embedding, voiceprint.embedding)
            if similarity > self.config.similarity_threshold:
                matches.append((voiceprint.caller_id, similarity, voiceprint.metadata))
        
        if matches:
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[0]  # (caller_id, similarity, metadata)
        return None
    
    def enroll_caller(self, caller_id, audio_buffer, metadata=None):
        """Enroll a new caller by storing their voiceprint."""
        embedding = self.get_embedding(audio_buffer)
        voiceprint = Voiceprint(
            caller_id=caller_id,
            embedding=embedding,
            metadata=metadata or {}
        )
        self.storage.save(voiceprint)
        return voiceprint 