"""
Configuration loader for the transcription module.

This module provides:
- load_transcription_config: Loads transcription configuration using centralized config system.
- Maintained for backward compatibility.

Usage:
    from opusagent.local.transcription.config import load_transcription_config
    config = load_transcription_config()
    
    # New recommended usage:
    from opusagent.config import transcription_config
    config = transcription_config()
"""
from .models import TranscriptionConfig
from opusagent.config import transcription_config as get_transcription_config

def load_transcription_config() -> TranscriptionConfig:
    """Load transcription configuration using centralized configuration system.
    
    This function is maintained for backward compatibility.
    New code should use: from opusagent.config import transcription_config
    """
    config = get_transcription_config()
    
    return TranscriptionConfig(
        backend=config.backend,
        language=config.language,
        model_size=config.model_size,
        chunk_duration=config.chunk_duration,
        confidence_threshold=config.confidence_threshold,
        sample_rate=config.sample_rate,
        enable_vad=config.enable_vad,
        device=config.device,
        pocketsphinx_hmm=config.pocketsphinx_hmm,
        pocketsphinx_lm=config.pocketsphinx_lm,
        pocketsphinx_dict=config.pocketsphinx_dict,
        pocketsphinx_audio_preprocessing=config.pocketsphinx_audio_preprocessing,
        pocketsphinx_vad_settings=config.pocketsphinx_vad_settings,
        pocketsphinx_auto_resample=config.pocketsphinx_auto_resample,
        pocketsphinx_input_sample_rate=config.pocketsphinx_input_sample_rate,
        whisper_model_dir=config.whisper_model_dir,
        whisper_temperature=config.whisper_temperature,
    ) 