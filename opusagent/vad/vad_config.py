import os
from opusagent.config.constants import DEFAULT_SAMPLE_RATE, DEFAULT_VAD_CHUNK_SIZE

def load_vad_config():
    """Load VAD configuration from environment variables or use defaults."""
    return {
        'backend': os.getenv('VAD_BACKEND', 'silero'),
        'sample_rate': int(os.getenv('VAD_SAMPLE_RATE', DEFAULT_SAMPLE_RATE)),
        'threshold': float(os.getenv('VAD_CONFIDENCE_THRESHOLD', 0.5)),
        'device': os.getenv('VAD_DEVICE', 'cpu'),
        'chunk_size': int(os.getenv('VAD_CHUNK_SIZE', DEFAULT_VAD_CHUNK_SIZE)),
    } 