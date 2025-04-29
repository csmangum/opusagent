# Bot Module

## Overview

The Bot module integrates OpenAI's Realtime API with AudioCodes VoiceAI Connect platform, enabling real-time speech-to-speech conversations. It serves as the core of the voice agent system, allowing seamless voice interactions between users and OpenAI's models through AudioCodes telephony infrastructure.

## Components

### RealtimeClient

A robust WebSocket client for OpenAI's Realtime API that handles:

- Bidirectional audio streaming
- Session management with configurable parameters
- Auto-reconnection and heartbeats for reliable connections
- Structured event handling via Pydantic models
- Voice Activity Detection (VAD) support
- Function calling capabilities

### AudiocodesRealtimeBridge

A bidirectional bridge that:

- Converts between AudioCodes and OpenAI protocols
- Manages audio format conversion
- Handles stream lifecycle
- Processes audio in both directions with low latency
- Provides error handling and connection management

## Usage

### Basic Usage with the Bridge Singleton

The recommended approach is to use the singleton bridge instance:

```python
from app.bot import bridge
import asyncio

async def handle_new_conversation(conversation_id, websocket):
    # Create a new client for this conversation
    await bridge.create_client(conversation_id, websocket)
    
    # Send audio to OpenAI
    await bridge.send_audio_chunk(conversation_id, base64_audio_data)
    
    # Clean up when conversation ends
    await bridge.close_client(conversation_id)
```

### Direct RealtimeClient Usage

For more customized implementations:

```python
from app.bot import RealtimeClient
import os

async def custom_client_usage():
    # Create and connect client
    api_key = os.getenv("OPENAI_API_KEY")
    model = "gpt-4o-realtime-preview-2024-12-17"
    client = RealtimeClient(api_key, model)
    await client.connect()
    
    # Send and receive audio
    await client.send_audio_chunk(audio_bytes)
    response_chunk = await client.receive_audio_chunk()
    
    # Close when done
    await client.close()
```

## Configuration

The module uses the following environment variables:

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_REALTIME_MODEL`: The model to use (defaults to "gpt-4o-realtime-preview-2024-12-17")

## Requirements

- Python 3.7+
- `websockets` library
- `asyncio` support
- Valid OpenAI API key with access to Realtime API models

## Error Handling

The module includes comprehensive error handling for common scenarios:
- Connection failures
- Reconnection logic
- Audio processing errors
- Protocol conversion issues

## Performance Considerations

The implementation is optimized for low-latency audio processing with:
- TCP_NODELAY socket options
- Efficient base64 encoding/decoding
- Queue size limitations to prevent buffering
- Latency tracking for performance monitoring 