"""
Transcription backend exports for the transcription module.

This package exposes the available backend implementations:
- PocketSphinxTranscriber: Lightweight, offline transcription
- WhisperTranscriber: High-accuracy, multi-model transcription

Usage:
    from opusagent.mock.transcription.backends import PocketSphinxTranscriber, WhisperTranscriber
"""
from .pocketsphinx import PocketSphinxTranscriber
from .whisper import WhisperTranscriber

__all__ = [
    "PocketSphinxTranscriber",
    "WhisperTranscriber",
] 