# Legacy VAD config module - now uses centralized configuration
# This module is maintained for backward compatibility

from opusagent.config import vad_config

def load_vad_config():
    """
    Load VAD configuration using centralized configuration system.
    
    This function is maintained for backward compatibility.
    New code should use: from opusagent.config import vad_config
    """
    config = vad_config()
    return {
        'backend': config.backend,
        'sample_rate': config.sample_rate,
        'threshold': config.confidence_threshold,
        'silence_threshold': config.silence_threshold,
        'min_speech_duration_ms': config.min_speech_duration_ms,
        'speech_start_threshold': config.speech_start_threshold,
        'speech_stop_threshold': config.speech_stop_threshold,
        'device': config.device,
        'chunk_size': config.chunk_size,
        'confidence_history_size': config.confidence_history_size,
        'force_stop_timeout_ms': config.force_stop_timeout_ms,
    } 