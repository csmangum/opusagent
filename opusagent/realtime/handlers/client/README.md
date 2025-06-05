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

### `transcription_session_handler.py`

Manages transcription-specific session settings, including:
- Input audio format configuration (pcm16, g711_ulaw, g711_alaw)
- Transcription model settings (model, prompt, language)
- Turn detection configuration (server_vad, semantic_vad)
- Noise reduction settings
- Additional field inclusion settings

### `handler_registry.py`

Provides a centralized registry for all client-side event handlers, including:
- Dictionary-like interface for accessing handlers by event type
- Singleton pattern for global access
- Type-safe handler registration and retrieval
- Support for all handler types (response, audio, conversation, session, transcription)

## Usage Example

```python
from opusagent.realtime.handlers.client import (
    ResponseHandler,
    InputAudioBufferHandler,
    ConversationItemHandler,
    SessionUpdateHandler,
    SessionGetConfigHandler,
    TranscriptionSessionHandler,
    registry  # Import the handler registry
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
transcription_handler = TranscriptionSessionHandler(send_event)

# Using the handler registry
async def handle_event(event: dict) -> None:
    event_type = event.get("type")
    if event_type in registry:
        handler_class = registry[event_type]
        handler = handler_class(send_event)
        await handler.handle(event)
    else:
        print(f"No handler found for event type: {event_type}")

# Example transcription session update
transcription_config = {
    "input_audio_format": "pcm16",
    "input_audio_transcription": {
        "model": "gpt-4o-transcribe",
        "prompt": "Transcribe the following audio:",
        "language": "en"
    },
    "turn_detection": {
        "type": "server_vad",
        "threshold": 0.5,
        "prefix_padding_ms": 300,
        "silence_duration_ms": 500,
        "create_response": True
    },
    "input_audio_noise_reduction": {
        "type": "near_field"
    },
    "include": [
        "item.input_audio_transcription.logprobs"
    ]
}

await transcription_handler.handle({
    "type": "transcription_session.update",
    "event_id": "event_123",
    "session": transcription_config
})
``` 