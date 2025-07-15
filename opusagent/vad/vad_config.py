import os
from opusagent.config.constants import DEFAULT_SAMPLE_RATE, DEFAULT_VAD_CHUNK_SIZE

def load_vad_config():
    """
    Load VAD configuration from environment variables or use defaults.
    
    Enhanced configuration includes:
    - silence_threshold: Minimum confidence threshold for silence detection
    - min_speech_duration_ms: Minimum duration for valid speech segments
    - speech_start_threshold: Number of consecutive speech detections to start
    - speech_stop_threshold: Number of consecutive silence detections to stop
    """
    return {
        'backend': os.getenv('VAD_BACKEND', 'silero'),
        'sample_rate': int(os.getenv('VAD_SAMPLE_RATE', DEFAULT_SAMPLE_RATE)),
        'threshold': float(os.getenv('VAD_CONFIDENCE_THRESHOLD', 0.5)),
        'silence_threshold': float(os.getenv('VAD_SILENCE_THRESHOLD', 0.6)),  # Increased from 0.4
        'min_speech_duration_ms': int(os.getenv('VAD_MIN_SPEECH_DURATION_MS', 500)),  # New parameter
        'speech_start_threshold': int(os.getenv('VAD_SPEECH_START_THRESHOLD', 2)),  # Hysteresis
        'speech_stop_threshold': int(os.getenv('VAD_SPEECH_STOP_THRESHOLD', 3)),   # Hysteresis
        'device': os.getenv('VAD_DEVICE', 'cpu'),
        'chunk_size': int(os.getenv('VAD_CHUNK_SIZE', DEFAULT_VAD_CHUNK_SIZE)),
        'confidence_history_size': int(os.getenv('VAD_CONFIDENCE_HISTORY_SIZE', 5)),
        'force_stop_timeout_ms': int(os.getenv('VAD_FORCE_STOP_TIMEOUT_MS', 2000)),  # Force stop after timeout
    } 