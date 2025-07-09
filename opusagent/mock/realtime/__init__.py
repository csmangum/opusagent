"""
MockRealtime Module - Enhanced OpenAI Realtime API Simulator

This module provides a comprehensive mock implementation of the OpenAI Realtime API
WebSocket connection, designed for testing and development without requiring an
actual OpenAI API connection.

The module is organized into separate concerns:
- models: Data models and configuration classes
- client: Main MockRealtimeClient implementation
- handlers: Event handlers for WebSocket messages
- audio: Audio file management and processing
- generators: Response generation logic
- utils: Utility functions and constants

Example Usage:
    ```python
    from opusagent.mock.mock_realtime import MockRealtimeClient, MockResponseConfig
    
    # Create a mock client with saved audio phrases
    mock_client = MockRealtimeClient()
    
    # Add response configuration
    mock_client.add_response_config(
        "greeting",
        MockResponseConfig(
            text="Hello! How can I help you?",
            audio_file="demo/audio/greeting.wav"
        )
    )
    ```
"""

from .models import MockResponseConfig
from .client import MockRealtimeClient

__all__ = [
    "MockRealtimeClient",
    "MockResponseConfig",
]

__version__ = "2.0.0" 