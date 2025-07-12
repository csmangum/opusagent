# Transcription Integration with LocalRealtimeClient

This document explains how transcription is integrated with the LocalRealtimeClient, providing a complete simulation of the OpenAI Realtime API with local audio transcription capabilities.

## Overview

The LocalRealtimeClient includes full transcription integration that allows it to:
- Process real-time audio streams
- Convert speech to text using local transcription backends
- Generate transcription events that match the OpenAI Realtime API
- Use transcription results for intelligent response generation
- Manage transcription sessions across multiple audio files

## Architecture

### Core Components

1. **LocalRealtimeClient**: Main client that orchestrates transcription
2. **TranscriptionFactory**: Creates and manages transcription backends
3. **BaseTranscriber**: Abstract base class for transcription implementations
4. **PocketSphinxTranscriber**: Lightweight, offline transcription
5. **WhisperTranscriber**: High-accuracy transcription using OpenAI Whisper
6. **EventHandlerManager**: Processes transcription events and WebSocket communication

### Integration Flow

```
Audio Input → VAD Processing → Audio Buffer → Transcription → Events → Response Generation
     ↓              ↓              ↓              ↓           ↓           ↓
  Real-time    Speech Detection  Chunking    Text Output  WebSocket   Context-Aware
  Streaming                                                      Events    Responses
```

## Configuration

### Session Configuration

Enable transcription in the session configuration:

```python
from opusagent.models.openai_api import SessionConfig

session_config = SessionConfig(
    model="gpt-4o-realtime-preview-2025-06-03",
    modalities=["text", "audio"],
    voice="alloy",
    input_audio_transcription={
        "model": "whisper",  # or "pocketsphinx"
        "language": "en"
    },
    turn_detection={"type": "server_vad"}
)
```

### Transcription Configuration

Configure transcription backends:

```python
from opusagent.mock.realtime import TranscriptionConfig

transcription_config = TranscriptionConfig(
    backend="whisper",  # "whisper" or "pocketsphinx"
    language="en",
    model_size="base",  # For Whisper: tiny, base, small, medium, large
    chunk_duration=1.0,
    confidence_threshold=0.5,
    sample_rate=16000,
    enable_vad=True,
    device="cpu"  # "cpu" or "cuda" for Whisper
)
```

### Client Initialization

Create a client with transcription enabled:

```python
from opusagent.mock.realtime import LocalRealtimeClient

client = LocalRealtimeClient(
    session_config=session_config,
    enable_transcription=True,
    transcription_config=transcription_config.__dict__
)
```

## Usage Examples

### Basic Transcription Setup

```python
import asyncio
from opusagent.mock.realtime import LocalRealtimeClient
from opusagent.models.openai_api import SessionConfig

async def basic_transcription_example():
    # Configure session with transcription
    session_config = SessionConfig(
        model="gpt-4o-realtime-preview-2025-06-03",
        modalities=["text", "audio"],
        input_audio_transcription={"model": "whisper", "language": "en"}
    )
    
    # Create client
    client = LocalRealtimeClient(
        session_config=session_config,
        enable_transcription=True
    )
    
    # Connect to WebSocket server
    await client.connect("ws://localhost:8080")
    
    # Process audio (this would normally come from WebSocket events)
    audio_data = b"..."  # Your audio data
    await client.handle_audio_append({
        "type": "input_audio_buffer.append",
        "audio": base64.b64encode(audio_data).decode("utf-8")
    })
    
    # Commit audio for transcription
    await client.handle_audio_commit({"type": "input_audio_buffer.commit"})
    
    # Disconnect
    await client.disconnect()

# Run the example
asyncio.run(basic_transcription_example())
```

### Direct Transcription Testing

```python
import asyncio
from pathlib import Path
from opusagent.mock.realtime import LocalRealtimeClient

async def direct_transcription_test():
    client = LocalRealtimeClient(enable_transcription=True)
    
    # Load audio file
    audio_file = Path("audio/sample.wav")
    with open(audio_file, 'rb') as f:
        audio_data = f.read()
    
    # Skip WAV header if present
    if len(audio_data) > 44 and audio_data[:4] == b'RIFF':
        audio_data = audio_data[44:]
    
    # Test transcription directly
    if client._transcriber:
        await client._transcriber.initialize()
        client._transcriber.start_session()
        
        # Process in chunks
        chunk_size = 3200  # 200ms at 16kHz 16-bit
        chunks = [audio_data[i:i + chunk_size] for i in range(0, len(audio_data), chunk_size)]
        
        for chunk in chunks:
            result = await client._transcriber.transcribe_chunk(chunk)
            if result.text:
                print(f"Delta: {result.text}")
        
        # Finalize
        final_result = await client._transcriber.finalize()
        print(f"Final: {final_result.text}")
        
        client._transcriber.end_session()

asyncio.run(direct_transcription_test())
```

### Response Generation with Transcription

```python
from opusagent.mock.realtime import LocalResponseConfig, ResponseSelectionCriteria

# Add response configurations that use transcription
client.add_response_config(
    "greeting_response",
    LocalResponseConfig(
        text="Hello! I heard you say: {transcription}. How can I help you today?",
        selection_criteria=ResponseSelectionCriteria(
            required_keywords=["hello", "hi", "greeting"],
            priority=10
        )
    )
)

client.add_response_config(
    "help_response",
    LocalResponseConfig(
        text="I understand you need help. You said: '{transcription}'. Let me assist you with that.",
        selection_criteria=ResponseSelectionCriteria(
            required_keywords=["help", "assist", "support"],
            priority=15
        )
    )
)

# Update conversation context with transcription
transcription_text = "Hello, I need help with my account"
client.update_conversation_context(transcription_text)

# The response generation will now use the transcription text
```

## Event Handling

### Transcription Events

The client generates transcription events that match the OpenAI Realtime API:

1. **Transcription Delta Events**: Real-time transcription updates
   ```json
   {
     "type": "conversation_item_input_audio_transcription_delta",
     "item_id": "item_123",
     "content_index": 0,
     "delta": "Hello, how can"
   }
   ```

2. **Transcription Completed Events**: Final transcription results
   ```json
   {
     "type": "conversation_item_input_audio_transcription_completed",
     "item_id": "item_123",
     "content_index": 0,
     "transcript": "Hello, how can I help you today?"
   }
   ```

3. **Transcription Failed Events**: Error handling
   ```json
   {
     "type": "conversation_item_input_audio_transcription_failed",
     "item_id": "item_123",
     "content_index": 0,
     "error": {
       "code": "transcription_failed",
       "message": "Failed to process audio"
     }
   }
   ```

### Custom Event Handlers

Register custom handlers for transcription events:

```python
async def transcription_handler(data):
    event_type = data.get("type")
    if "transcription" in event_type.lower():
        if "delta" in data:
            print(f"Transcription delta: {data['delta']}")
        elif "transcript" in data:
            print(f"Final transcript: {data['transcript']}")

client.register_event_handler(
    "conversation_item_input_audio_transcription_delta",
    transcription_handler
)
client.register_event_handler(
    "conversation_item_input_audio_transcription_completed",
    transcription_handler
)
```

## Session Management

### Session State

The client maintains session state including transcription information:

```python
session_state = client.get_session_state()
print(f"Session ID: {session_state['session_id']}")
print(f"Transcription enabled: {session_state['transcription_enabled']}")
print(f"Current item ID: {session_state['current_item_id']}")

# Conversation context includes transcription results
conversation_context = session_state.get("conversation_context")
if conversation_context:
    print(f"Last user input: {conversation_context.last_user_input}")
    print(f"Detected intents: {conversation_context.detected_intents}")
```

### Session Reset

Reset transcription sessions for multiple audio files:

```python
# Reset session without destroying transcriber
if client._transcriber:
    client._transcriber.reset_session()
    print("Session reset for next audio file")
```

## State Management

### Transcription State

Check transcription status and configuration:

```python
transcription_state = client.get_transcription_state()
print(f"Enabled: {transcription_state['enabled']}")
print(f"Backend: {transcription_state['backend']}")
print(f"Initialized: {transcription_state['initialized']}")
print(f"Configuration: {transcription_state['configuration']}")
```

### VAD State

Monitor Voice Activity Detection state:

```python
vad_state = client.get_vad_state()
print(f"VAD enabled: {vad_state['enabled']}")
print(f"Speech active: {vad_state['speech_active']}")
print(f"Confidence: {vad_state.get('confidence', 'N/A')}")
```

## Configuration Management

### Update Transcription Configuration

Dynamically update transcription settings:

```python
# Update configuration
client.update_transcription_config({
    "confidence_threshold": 0.7,
    "chunk_duration": 0.5
})

# Reinitialize with new settings
client.enable_transcription(client.get_transcription_config())
```

### Enable/Disable Transcription

Control transcription at runtime:

```python
# Disable transcription
client.disable_transcription()

# Re-enable with custom config
client.enable_transcription({
    "backend": "pocketsphinx",
    "language": "en"
})
```

## Performance and Optimization

### Chunk Processing

Audio is processed in configurable chunks:

```python
# Default chunk size: 3200 bytes (200ms at 16kHz 16-bit)
chunk_size = 3200

# Customize chunk duration
transcription_config = TranscriptionConfig(
    chunk_duration=0.5,  # 500ms chunks
    # ... other settings
)
```

### Confidence Thresholds

Filter transcription results by confidence:

```python
transcription_config = TranscriptionConfig(
    confidence_threshold=0.8,  # Only high-confidence results
    # ... other settings
)
```

### Model Selection

Choose appropriate models for your use case:

```python
# Lightweight, offline processing
pocketsphinx_config = TranscriptionConfig(
    backend="pocketsphinx",
    language="en"
)

# High accuracy, requires more resources
whisper_config = TranscriptionConfig(
    backend="whisper",
    model_size="base",  # tiny, base, small, medium, large
    device="cpu"  # or "cuda" for GPU acceleration
)
```

## Error Handling

### Graceful Degradation

The system handles transcription failures gracefully:

```python
# If transcription fails, the client continues to function
# Error events are sent to the client
# Fallback responses can be configured

client.add_response_config(
    "transcription_fallback",
    LocalResponseConfig(
        text="I'm having trouble understanding your audio. Could you please repeat that?",
        selection_criteria=ResponseSelectionCriteria(
            priority=1  # Low priority fallback
        )
    )
)
```

### Error Monitoring

Monitor transcription errors:

```python
async def error_handler(data):
    if data.get("type") == "conversation_item_input_audio_transcription_failed":
        error = data.get("error", {})
        print(f"Transcription failed: {error.get('message', 'Unknown error')}")

client.register_event_handler(
    "conversation_item_input_audio_transcription_failed",
    error_handler
)
```

## Testing and Validation

### Running Integration Tests

Use the provided test scripts:

```bash
# Quick transcription demo
python scripts/quick_transcription_demo.py

# Comprehensive integration test
python scripts/demo_transcription_integration.py

# Direct transcription test
python scripts/direct_transcription_demo.py
```

### Validation Results

The integration provides:

- ✅ **Real-time audio streaming** with chunked processing
- ✅ **Transcription events** that match OpenAI Realtime API
- ✅ **Session state management** with transcription integration
- ✅ **Response generation** using transcription results
- ✅ **VAD integration** for speech detection
- ✅ **Multiple backend support** (Whisper, PocketSphinx)
- ✅ **Error handling** and graceful degradation
- ✅ **Configuration management** for runtime updates

## Best Practices

1. **Initialize transcription early** in the client lifecycle
2. **Use appropriate chunk sizes** for your audio format
3. **Monitor confidence scores** for quality control
4. **Handle transcription errors** gracefully
5. **Reset sessions** between audio files
6. **Configure fallback responses** for transcription failures
7. **Use VAD integration** for better speech detection
8. **Monitor performance** and adjust configuration as needed

## Troubleshooting

### Common Issues

1. **Transcription not working**: Check if backend is properly installed
2. **High latency**: Reduce chunk size or use faster models
3. **Low accuracy**: Increase model size or adjust confidence threshold
4. **Memory issues**: Use smaller models or reduce chunk duration
5. **WebSocket errors**: Ensure proper connection before sending events

### Debug Information

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Check transcription state
state = client.get_transcription_state()
print(f"Transcription state: {state}")

# Check session state
session = client.get_session_state()
print(f"Session state: {session}")
```

This integration provides a complete, production-ready transcription system that closely mimics the behavior of the OpenAI Realtime API while offering local processing capabilities and full control over the transcription pipeline. 