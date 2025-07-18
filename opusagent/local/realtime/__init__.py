"""
LocalRealtime Module - OpenAI Realtime API Simulator

This module provides a comprehensive mock implementation of the OpenAI Realtime API
WebSocket connection, designed for testing and development without requiring an
actual OpenAI API connection.

The module is organized into separate concerns:
- models: Data models and configuration classes
- client: Main LocalRealtimeClient implementation
- handlers: Event handlers for WebSocket messages
- audio: Audio file management and processing
- generators: Response generation logic
- utils: Utility functions and constants

Key Features:
- Smart response selection based on conversation context
- Intent detection and keyword matching
- Configurable response criteria and priorities
- Audio file caching and management
- Complete WebSocket event handling
- Clean public API without backward compatibility

Example Usage:
    ```python
    from opusagent.local.realtime import LocalRealtimeClient, LocalResponseConfig, ResponseSelectionCriteria

    # Create a mock client with smart response selection
    mock_client = LocalRealtimeClient()

    # Add context-aware response configuration
    mock_client.add_response_config(
        "greeting",
        LocalResponseConfig(
            text="Hello! How can I help you?",
            audio_file="demo/audio/greeting.wav",
            selection_criteria=ResponseSelectionCriteria(
                required_keywords=["hello", "hi"],
                max_turn_count=1,
                priority=10
            )
        )
    )

    # Set up conversation context
    mock_client.update_conversation_context("Hello there!")

    # Access session state
    session_state = mock_client.get_session_state()
    audio_buffer = mock_client.get_audio_buffer()
    ```
"""

from .client import LocalRealtimeClient
from .models import ConversationContext, LocalResponseConfig, ResponseSelectionCriteria
from .websocket_mock import (
    MockWebSocketConnection,
    MockWebSocketConnectionManager,
    create_mock_websocket_connection,
)

__all__ = [
    "LocalRealtimeClient",
    "LocalResponseConfig",
    "ResponseSelectionCriteria",
    "ConversationContext",
    "MockWebSocketConnection",
    "MockWebSocketConnectionManager",
    "create_mock_websocket_connection",
]

__version__ = "3.0.0"
