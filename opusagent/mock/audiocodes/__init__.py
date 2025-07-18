"""
AudioCodes Mock Client Module

This module provides a comprehensive mock implementation of the AudioCodes VAIC client
that connects to the bridge server. It simulates the behavior of a real AudioCodes
device for testing and development purposes.

Key Components:
- MockAudioCodesClient: Main client class for connecting to bridge server
- AudioManager: Audio file handling and caching
- SessionManager: Session state and lifecycle management
- MessageHandler: WebSocket message processing
- ConversationManager: Multi-turn conversation handling

Usage:
    from opusagent.mock.audiocodes import MockAudioCodesClient
    
    async with MockAudioCodesClient("ws://localhost:8080") as client:
        await client.initiate_session()
        await client.send_user_audio("audio/user_input.wav")
        response = await client.wait_for_llm_response()
"""

from .client import MockAudioCodesClient
from .audio_manager import AudioManager
from .session_manager import SessionManager
from .message_handler import MessageHandler
from .conversation_manager import ConversationManager
from .models import (
    SessionState,
    ConversationState,
    AudioChunk,
    MessageEvent,
    SessionConfig
)

__all__ = [
    "MockAudioCodesClient",
    "AudioManager", 
    "SessionManager",
    "MessageHandler",
    "ConversationManager",
    "SessionState",
    "ConversationState", 
    "AudioChunk",
    "MessageEvent",
    "SessionConfig"
]

__version__ = "1.0.0"
