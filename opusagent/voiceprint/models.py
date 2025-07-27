from pydantic import BaseModel, ConfigDict, field_validator
from typing import Dict, Any, Optional, Union
import numpy as np

class Voiceprint(BaseModel):
    caller_id: str
    embedding: np.ndarray
    metadata: Dict[str, Any] = {}
    created_at: Optional[str] = None
    last_seen: Optional[str] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    @field_validator('embedding', mode='before')
    @classmethod
    def validate_embedding(cls, v):
        """Convert list to numpy array if needed."""
        if isinstance(v, list):
            return np.array(v, dtype=np.float32)
        elif isinstance(v, np.ndarray):
            return v
        else:
            raise ValueError(f"Embedding must be a list or numpy array, got {type(v)}")

class VoiceFingerprintConfig(BaseModel):
    similarity_threshold: float = 0.75
    enrollment_duration: float = 5.0  # seconds
    min_audio_quality: float = 0.6
    max_voiceprints_per_caller: int = 3 