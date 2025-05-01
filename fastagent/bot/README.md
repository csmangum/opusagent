# Bot Module

The Bot module provides real-time speech-to-speech conversation capabilities by integrating OpenAI's Realtime API with telephony platforms. It serves as the core component for voice agent systems, enabling seamless voice interactions through telephony infrastructure.

## Key Components

### RealtimeClient
A robust WebSocket client for OpenAI's Realtime API that handles:
- Real-time audio streaming in both directions
- Session management and configuration
- Voice Activity Detection (VAD)
- Function calling capabilities
- Auto-reconnection and heartbeat mechanisms
- Rate limiting and security features

### TelephonyRealtimeBridge
A bidirectional bridge that:
- Connects telephony platforms (AudioCodes, Twilio, etc.) with OpenAI's Realtime API
- Handles protocol conversion between different systems
- Manages audio format conversion
- Provides stream management capabilities

## Features

- **Real-time Audio Processing**
  - Low-latency WebSocket communication
  - Efficient audio buffer management
  - Optimized TCP settings for real-time audio

- **Security**
  - TLS encryption for WebSocket connections
  - Secure API key handling
  - Input validation
  - Rate limiting
  - Resource leak prevention

- **Reliability**
  - Auto-reconnection capabilities
  - Heartbeat monitoring
  - Connection state management
  - Error handling and recovery

## Usage

### Basic Usage with Bridge (Recommended)

```python
from fastagent.bot import bridge
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

```python
from fastagent.bot import RealtimeClient
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

## Error Handling

The module provides several custom exceptions:
- `RealtimeClientError`: Base exception class
- `ConnectionError`: Connection-related issues
- `AuthenticationError`: API key or authentication problems
- `RateLimitError`: Rate limiting violations
- `SessionError`: Session management issues
- `MemoryError`: Memory-related problems
- `AudioError`: Audio processing issues
- `BinaryDataError`: Binary data handling problems

## Performance Considerations

- Connection pooling for reuse
- Memory-efficient queue management
- Optimized TCP settings
- Efficient audio buffer handling
- Low-latency WebSocket configuration

## Dependencies

- Python 3.8+
- OpenAI API access
- WebSocket support
- Telephony platform integration (AudioCodes, Twilio, etc.)

## Security Notes

- API keys should be stored securely and never logged
- All WebSocket connections use TLS encryption
- Input validation is performed on all messages
- Rate limiting is implemented to prevent abuse
- Connection state is carefully managed to prevent resource leaks 