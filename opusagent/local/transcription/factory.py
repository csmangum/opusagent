"""
TranscriptionFactory for creating transcription backend instances.

This module provides:
- TranscriptionFactory: A factory class for instantiating transcription backends (PocketSphinx, Whisper) based on configuration.
- Centralized logic for backend selection, validation, and runtime availability checks.

Usage:
    from opusagent.mock.transcription.factory import TranscriptionFactory
    transcriber = TranscriptionFactory.create_transcriber(config)
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