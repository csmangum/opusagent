# Client Handlers Module

This module provides client-side event handlers for processing events from the OpenAI Realtime API WebSocket connection. Each handler implements specific logic for processing different types of events and managing the appropriate responses.

## Overview

The client handlers module is responsible for processing various event types received from the OpenAI Realtime API WebSocket connection. It consists of the following components:

### `response_handler.py`

Handles response events from the OpenAI Realtime API, including:
- Creating new model responses
- Canceling active responses
- Managing different response types (text, audio, function calls)
- Handling response states (in progress, completed, cancelled)

### `input_audio_buffer_handler.py`

Manages the processing of audio input data, including:
- Buffering incoming audio data
- Handling audio format conversion
- Managing audio stream state

### `conversation_item_handler.py`

Processes conversation-related events, including:
- Handling user messages
- Managing conversation state
- Processing conversation metadata

### `session_update_handler.py`

Manages session-related updates, including:
- Processing session state changes
- Handling session configuration updates
- Managing session lifecycle events

### `session_get_config_handler.py`

Handles session configuration requests, including:
- Retrieving current session settings
- Managing configuration state
- Processing configuration updates

## Usage Example

```python
from fastagent.realtime.handlers.cllient import (
    ResponseHandler,
    InputAudioBufferHandler,
    ConversationItemHandler,
    SessionUpdateHandler,
    SessionGetConfigHandler
)

# Initialize handlers with a callback for sending events
async def send_event(event: dict) -> None:
    # Implementation for sending events back to the server
    pass

# Create handler instances
response_handler = ResponseHandler(send_event)
audio_handler = InputAudioBufferHandler(send_event)
conversation_handler = ConversationItemHandler(send_event)
session_update_handler = SessionUpdateHandler(send_event)
config_handler = SessionGetConfigHandler(send_event)

# Handle incoming events
async def handle_event(event: dict) -> None:
    event_type = event.get("type")
    if event_type == "response.create":
        await response_handler.handle_create(event)
    elif event_type == "input_audio_buffer":
        await audio_handler.handle(event)
    # ... handle other event types
``` 