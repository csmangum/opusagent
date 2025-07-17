"""
Transcription Module for OpusAgent

A modular, extensible system for audio transcription with support for multiple backends.
Provides high-quality, real-time transcription capabilities for audio processing applications.

Quick Start:
    from opusagent.mock.transcription import TranscriptionFactory, load_transcription_config
    
    # Load configuration
    config = load_transcription_config()
    
    # Create transcriber
    transcriber = TranscriptionFactory.create_transcriber(config)
    
    # Initialize and use
    await transcriber.initialize()
    result = await transcriber.transcribe_chunk(audio_data)
    await transcriber.cleanup()

Supported Backends:
    - PocketSphinx: Fast, lightweight, offline transcription
    - Whisper: High-accuracy transcription with multiple model sizes

Features:
    - Real-time streaming transcription
    - Multiple backend support
    - Configurable audio preprocessing
    - Confidence scoring
    - Error handling and recovery
    - Session management
    - Audio format conversion and resampling

For detailed documentation, see DESIGN.md in this directory.
"""

from .models import TranscriptionResult, TranscriptionConfig
from .factory import TranscriptionFactory
from .config import load_transcription_config
from .base import BaseTranscriber

__all__ = [
    "TranscriptionResult",
    "TranscriptionConfig",
    "TranscriptionFactory",
    "load_transcription_config",
    "BaseTranscriber",
] 