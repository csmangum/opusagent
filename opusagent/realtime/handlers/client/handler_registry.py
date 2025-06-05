"""
Handler registry for client-side event handlers.

This module provides a centralized registry of all available handlers
for the OpenAI Realtime API client. It implements a dictionary-like interface
for accessing handlers by their event types.
"""

from typing import Dict, Type, Any
from .session_update_handler import SessionUpdateHandler
from .session_get_config_handler import SessionGetConfigHandler
from .input_audio_buffer_handler import InputAudioBufferHandler
from .conversation_item_handler import ConversationItemHandler
from .response_handler import ResponseHandler
from .transcription_session_handler import TranscriptionSessionHandler

class HandlerRegistry:
    """Registry of all available client-side event handlers."""
    
    def __init__(self):
        self._handlers: Dict[str, Type[Any]] = {
            'session_update': SessionUpdateHandler,
            'session_get_config': SessionGetConfigHandler,
            'input_audio_buffer': InputAudioBufferHandler,
            'conversation_item': ConversationItemHandler,
            'response': ResponseHandler,
            'transcription_session': TranscriptionSessionHandler
        }
    
    def __getitem__(self, key: str) -> Type[Any]:
        """Get a handler by its event type."""
        if key not in self._handlers:
            raise KeyError(f"No handler found for event type: {key}")
        return self._handlers[key]
    
    def __contains__(self, key: str) -> bool:
        """Check if a handler exists for the given event type."""
        return key in self._handlers
    
    def get(self, key: str, default: Type[Any] = None) -> Type[Any]:
        """Get a handler by its event type with a default value if not found."""
        return self._handlers.get(key, default)
    
    def keys(self):
        """Get all available event types."""
        return self._handlers.keys()
    
    def values(self):
        """Get all available handler classes."""
        return self._handlers.values()
    
    def items(self):
        """Get all event type and handler class pairs."""
        return self._handlers.items()

# Create a singleton instance
registry = HandlerRegistry() 