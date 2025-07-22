# Legacy VAD config module - now uses centralized configuration
# This module is maintained for backward compatibility

from opusagent.config import get_legacy_vad_config

def load_vad_config():
    """
    Load VAD configuration using centralized configuration system.
    
    This function is maintained for backward compatibility.
    New code should use: from opusagent.config import vad_config
    """
    return get_legacy_vad_config() 