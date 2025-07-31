"""
Constants and configuration values used throughout the application.

This module defines constants that are used across different parts of the application,
providing a centralized location for configuration values and making it easier to
maintain consistent naming throughout the codebase.
"""

# Logger name used throughout the application
LOGGER_NAME = "opusagent"

# Default voice for CS agent (caller agent uses "alloy" for distinction)
VOICE = "verse"

# Audio constants used throughout the application
DEFAULT_SAMPLE_RATE = 24000  # 24kHz (updated for OpenAI Realtime API)
DEFAULT_CHANNELS = 1  # Mono
DEFAULT_BITS_PER_SAMPLE = 16  # 16-bit PCM
DEFAULT_AUDIO_CHUNK_SIZE = 4800  # 200ms at 24kHz 16-bit
DEFAULT_AUDIO_CHUNK_SIZE_LARGE = 48000  # 2 seconds at 24kHz 16-bit (used in TUI)
DEFAULT_VAD_CHUNK_SIZE = 768  # VAD processing chunk size (32ms at 24kHz)
DEFAULT_VAD_SAMPLE_RATE = 16000  # 16kHz (optimal for VAD processing)
DEFAULT_VAD_CHUNK_SIZE_16KHZ = 512  # VAD processing chunk size (32ms at 16kHz)

# Audio Stream Handler constants
DEFAULT_INTERNAL_SAMPLE_RATE = 24000  # Internal processing sample rate
DEFAULT_MIN_AUDIO_BYTES = 4800  # 100ms at 24kHz 16-bit mono
DEFAULT_OPENAI_SAMPLE_RATE = 24000  # OpenAI Realtime API sample rate

# Transcription constants
DEFAULT_TRANSCRIPTION_BACKEND = "pocketsphinx"  # Default transcription backend
DEFAULT_TRANSCRIPTION_LANGUAGE = "en"  # Default language
DEFAULT_WHISPER_MODEL_SIZE = "base"  # Default Whisper model size
DEFAULT_TRANSCRIPTION_CONFIDENCE_THRESHOLD = 0.5  # Default confidence threshold
DEFAULT_TRANSCRIPTION_CHUNK_DURATION = 1.0  # Default chunk duration in seconds

# VAD threshold constants for speech detection hysteresis
SPEECH_START_THRESHOLD = 2  # Number of consecutive speech detections to start speech
SPEECH_STOP_THRESHOLD = 3  # Number of consecutive silence detections to stop speech

# Audio collection timeout constants
# Polling interval is 0.1 seconds, so 20 iterations = 2 seconds
NO_NEW_CHUNKS_THRESHOLD = int(2.0 / 0.1)  # 20 iterations for 2-second timeout
