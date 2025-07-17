"""
Configuration loader for the transcription module.

This module provides:
- load_transcription_config: Loads and validates transcription configuration from environment variables, with sensible defaults for all supported backends.
- Integrates with opusagent.config.constants for default values.

Usage:
    from opusagent.mock.transcription.config import load_transcription_config
    config = load_transcription_config()
"""
import os
from .models import TranscriptionConfig
from opusagent.config.constants import (
    DEFAULT_SAMPLE_RATE,
    DEFAULT_TRANSCRIPTION_BACKEND,
    DEFAULT_TRANSCRIPTION_CHUNK_DURATION,
    DEFAULT_TRANSCRIPTION_CONFIDENCE_THRESHOLD,
    DEFAULT_TRANSCRIPTION_LANGUAGE,
    DEFAULT_WHISPER_MODEL_SIZE,
)

def load_transcription_config() -> TranscriptionConfig:
    """Load transcription configuration from environment variables."""
    return TranscriptionConfig(
        backend=os.getenv("TRANSCRIPTION_BACKEND", DEFAULT_TRANSCRIPTION_BACKEND),
        language=os.getenv("TRANSCRIPTION_LANGUAGE", DEFAULT_TRANSCRIPTION_LANGUAGE),
        model_size=os.getenv("WHISPER_MODEL_SIZE", DEFAULT_WHISPER_MODEL_SIZE),
        chunk_duration=float(
            os.getenv(
                "TRANSCRIPTION_CHUNK_DURATION",
                str(DEFAULT_TRANSCRIPTION_CHUNK_DURATION),
            )
        ),
        confidence_threshold=float(
            os.getenv(
                "TRANSCRIPTION_CONFIDENCE_THRESHOLD",
                str(DEFAULT_TRANSCRIPTION_CONFIDENCE_THRESHOLD),
            )
        ),
        sample_rate=int(
            os.getenv("TRANSCRIPTION_SAMPLE_RATE", str(DEFAULT_SAMPLE_RATE))
        ),
        enable_vad=os.getenv("TRANSCRIPTION_ENABLE_VAD", "true").lower() == "true",
        device=os.getenv("WHISPER_DEVICE", "cpu"),
        pocketsphinx_hmm=os.getenv("POCKETSPHINX_HMM"),
        pocketsphinx_lm=os.getenv("POCKETSPHINX_LM"),
        pocketsphinx_dict=os.getenv("POCKETSPHINX_DICT"),
        pocketsphinx_audio_preprocessing=os.getenv("POCKETSPHINX_AUDIO_PREPROCESSING", "normalize"),
        pocketsphinx_vad_settings=os.getenv("POCKETSPHINX_VAD_SETTINGS", "conservative"),
        pocketsphinx_auto_resample=os.getenv("POCKETSPHINX_AUTO_RESAMPLE", "true").lower() == "true",
        pocketsphinx_input_sample_rate=int(os.getenv("POCKETSPHINX_INPUT_SAMPLE_RATE", "24000")),
        whisper_model_dir=os.getenv("WHISPER_MODEL_DIR"),
        whisper_temperature=float(os.getenv("WHISPER_TEMPERATURE", "0.0")),
    ) 