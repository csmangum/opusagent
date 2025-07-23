from pydantic import BaseModel
from typing import Dict, Any, Optional
import numpy as np

class Voiceprint(BaseModel):
    caller_id: str
    embedding: np.ndarray
    metadata: Dict[str, Any] = {}
    created_at: Optional[str] = None
    last_seen: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True

class VoiceFingerprintConfig(BaseModel):
    similarity_threshold: float = 0.75
    enrollment_duration: float = 5.0  # seconds
    min_audio_quality: float = 0.6
    max_voiceprints_per_caller: int = 3 