"""
TranscriptionFactory for creating transcription backend instances.
"""
from typing import Any, Dict, List, Union
from .models import TranscriptionConfig
from .backends import PocketSphinxTranscriber, WhisperTranscriber

class TranscriptionFactory:
    """Factory for creating transcription backends."""

    @staticmethod
    def create_transcriber(
        config: Union[Dict[str, Any], TranscriptionConfig],
    ):
        if isinstance(config, dict):
            config = TranscriptionConfig(**config)
        backend = config.backend.lower()
        if backend == "pocketsphinx":
            return PocketSphinxTranscriber(config)
        elif backend == "whisper":
            return WhisperTranscriber(config)
        else:
            raise ValueError(f"Unsupported transcription backend: {backend}")

    @staticmethod
    def get_available_backends() -> List[str]:
        available = []
        try:
            import pocketsphinx
            available.append("pocketsphinx")
        except ImportError:
            pass
        # Whisper is always listed; actual import is checked at runtime
        available.append("whisper")
        return available 