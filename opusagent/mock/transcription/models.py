"""
This module provides Pydantic models for transcription configuration and results,
ensuring type safety and validation for the transcription system.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, ValidationInfo


class TranscriptionResult(BaseModel):
    """
    Pydantic model for the result of a transcription operation.
    """
    text: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    is_final: bool = False
    segments: Optional[List[Dict[str, Any]]] = None
    processing_time: float = 0.0
    error: Optional[str] = None


class TranscriptionConfig(BaseModel):
    """
    Configuration for transcription backends.
    """
    backend: str = Field(default="pocketsphinx")
    language: str = "en"
    model_size: str = "base"  # For Whisper: tiny, base, small, medium, large
    chunk_duration: float = Field(default=1.0, gt=0.0)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    sample_rate: int = Field(default=16000, gt=0)
    enable_vad: bool = True
    device: str = Field(default="cpu", pattern=r"^(cpu|cuda)$")

    # PocketSphinx specific
    pocketsphinx_hmm: Optional[str] = None
    pocketsphinx_lm: Optional[str] = None
    pocketsphinx_dict: Optional[str] = None
    
    # PocketSphinx optimization settings (based on analysis results)
    pocketsphinx_audio_preprocessing: str = Field(
        default="normalize", 
        pattern=r"^(none|normalize|amplify|noise_reduction|silence_trim)$"
    )
    pocketsphinx_vad_settings: str = Field(
        default="conservative", 
        pattern=r"^(default|aggressive|conservative)$"
    )
    pocketsphinx_auto_resample: bool = True
    pocketsphinx_input_sample_rate: int = Field(default=24000, gt=0)

    # Whisper specific
    whisper_model_dir: Optional[str] = None
    whisper_temperature: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("backend")
    def validate_backend(cls, v: str, info: ValidationInfo) -> str:
        v_lower = v.lower()
        if v_lower not in ["pocketsphinx", "whisper"]:
            raise ValueError(f"Unsupported transcription backend: {v}")
        return v_lower

    @field_validator("pocketsphinx_audio_preprocessing")
    def validate_preprocessing(cls, v):
        """
        Validate audio preprocessing type.
        """
        valid_types = ["none", "normalize", "amplify", "noise_reduction", "silence_trim"]
        if v not in valid_types:
            raise ValueError(f"Invalid preprocessing type: {v}")
        return v

    @field_validator("pocketsphinx_vad_settings")
    def validate_vad_settings(cls, v):
        """
        Validate VAD settings.
        """
        valid_settings = ["default", "aggressive", "conservative"]
        if v not in valid_settings:
            raise ValueError(f"Invalid VAD settings: {v}")
        return v 