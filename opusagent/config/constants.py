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
DEFAULT_SAMPLE_RATE = 16000  # 16kHz
DEFAULT_CHANNELS = 1  # Mono
DEFAULT_BITS_PER_SAMPLE = 16  # 16-bit PCM
DEFAULT_AUDIO_CHUNK_SIZE = 3200  # 200ms at 16kHz 16-bit
DEFAULT_AUDIO_CHUNK_SIZE_LARGE = 32000  # 2 seconds at 16kHz 16-bit (used in TUI)
DEFAULT_VAD_CHUNK_SIZE = 512  # VAD processing chunk size

# Transcription constants
DEFAULT_TRANSCRIPTION_BACKEND = "pocketsphinx"  # Default transcription backend
DEFAULT_TRANSCRIPTION_LANGUAGE = "en"  # Default language
DEFAULT_WHISPER_MODEL_SIZE = "base"  # Default Whisper model size
DEFAULT_TRANSCRIPTION_CONFIDENCE_THRESHOLD = 0.5  # Default confidence threshold
DEFAULT_TRANSCRIPTION_CHUNK_DURATION = 1.0  # Default chunk duration in seconds