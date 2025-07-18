# AudioCodes Mock Client Module

This module provides a comprehensive mock implementation of the AudioCodes VAIC client that connects to the bridge server. It simulates the behavior of a real AudioCodes device for testing and development purposes.

## Overview

The AudioCodes mock client is designed to test bridge server functionality by simulating how a real AudioCodes VAIC would connect and interact with the bridge. It supports all the major features including:

- Session management (initiate, resume, validate, end)
- Audio streaming (user and play streams)
- Multi-turn conversations
- DTMF events and activities
- Speech/VAD events with real-time processing
- Audio file handling and caching
- **Live microphone input** for realistic testing
- **Real-time VAD** with configurable thresholds
- **Audio device management** and selection

## Module Structure

```
opusagent/mock/audiocodes/
├── __init__.py              # Main module exports
├── README.md               # This file
├── models.py               # Data models and enums
├── client.py               # Main MockAudioCodesClient class
├── session_manager.py      # Session state and lifecycle management
├── message_handler.py      # WebSocket message processing
├── audio_manager.py        # Audio file handling and caching
├── live_audio_manager.py   # Live microphone input and VAD
└── conversation_manager.py # Multi-turn conversation handling
```

## Components

### 1. Models (`models.py`)

Defines the data structures used throughout the module:

- **SessionStatus**: Enum for session states (disconnected, connecting, active, etc.)
- **StreamStatus**: Enum for stream states (inactive, starting, active, etc.)
- **MessageType**: Enum for WebSocket message types
- **SessionConfig**: Configuration for AudioCodes sessions
- **SessionState**: Current session state tracking
- **StreamState**: Stream state information
- **AudioChunk**: Audio chunk data structure
- **MessageEvent**: WebSocket message event
- **ConversationState**: Conversation state and history
- **ConversationResult**: Results of multi-turn conversations

### 2. Session Manager (`session_manager.py`)

Handles session lifecycle and state management:

- Session creation, initiation, and resumption
- Connection validation
- Session state tracking
- Event message preparation (DTMF, hangup, custom activities)
- Session status reporting

### 3. Message Handler (`message_handler.py`)

Processes incoming WebSocket messages from the bridge:

- Message parsing and validation
- Event handler registration and execution
- State updates based on received messages
- Message history tracking
- Speech/VAD event handling

### 4. Audio Manager (`audio_manager.py`)

Manages audio file operations:

- Audio file loading and chunking
- Format conversion and resampling
- Audio caching for performance
- Audio chunk saving and retrieval
- Silence generation for fallback scenarios

### 5. Conversation Manager (`conversation_manager.py`)

Handles multi-turn conversations:

- Conversation state tracking
- Audio collection (greeting and response)
- Multi-turn conversation orchestration
- Conversation result analysis
- Audio saving and analysis

### 6. Live Audio Manager (`live_audio_manager.py`)

Handles real-time microphone input and VAD:

- Live audio capture from microphone
- Real-time Voice Activity Detection (VAD)
- Audio device enumeration and selection
- Configurable VAD thresholds and parameters
- Audio level monitoring and visualization
- Thread-safe audio processing

### 7. Main Client (`client.py`)

Integrates all components into a cohesive client:

- WebSocket connection management
- Component coordination
- High-level API for testing
- Conversation testing utilities
- **Live audio capture integration**
- **Real-time VAD event handling**

## Usage

### Basic Usage

```python
from opusagent.mock.audiocodes import MockAudioCodesClient

async def test_basic_conversation():
    async with MockAudioCodesClient("ws://localhost:8080") as client:
        # Initiate session
        success = await client.initiate_session()
        if not success:
            print("Failed to initiate session")
            return
        
        # Send user audio
        await client.send_user_audio("audio/user_input.wav")
        
        # Wait for AI response
        response = await client.wait_for_llm_response()
        print(f"Received {len(response)} audio chunks")
        
        # End session
        await client.end_session("Test completed")
```

### Multi-turn Conversation Testing

```python
async def test_multi_turn_conversation():
    audio_files = [
        "audio/turn1.wav",
        "audio/turn2.wav", 
        "audio/turn3.wav"
    ]
    
    async with MockAudioCodesClient("ws://localhost:8080") as client:
        # Run multi-turn conversation
        result = await client.multi_turn_conversation(audio_files)
        
        # Print results
        print(f"Completed {result.completed_turns}/{result.total_turns} turns")
        print(f"Success rate: {result.success_rate:.1f}%")
        print(f"Duration: {result.duration:.2f}s")
        
        # Save collected audio
        client.save_collected_audio("output/")
```

### Session Management

```python
async def test_session_features():
    async with MockAudioCodesClient("ws://localhost:8080") as client:
        # Initiate session
        await client.initiate_session()
        
        # Validate connection
        validated = await client.validate_connection()
        print(f"Connection validated: {validated}")
        
        # Send DTMF event
        await client.send_dtmf_event("1")
        
        # Send custom activity
        await client.send_custom_activity({
            "type": "event",
            "name": "custom_event",
            "value": "test_value"
        })
        
        # Get session status
        status = client.get_session_status()
        print(f"Session status: {status}")
```

### Live Audio Testing

```python
async def test_live_audio():
    async with MockAudioCodesClient("ws://localhost:8080") as client:
        # Get available audio devices
        devices = client.get_available_audio_devices()
        print(f"Available devices: {len(devices)}")
        
        # Initiate session
        await client.initiate_session()
        
        # Start live audio capture with VAD
        live_config = {
            "vad_enabled": True,
            "vad_threshold": 0.3,
            "vad_silence_threshold": 0.1,
            "chunk_delay": 0.02,
        }
        
        success = client.start_live_audio_capture(config=live_config)
        if success:
            print("Live audio capture started - speak into your microphone!")
            
            # Monitor audio levels
            for _ in range(100):  # 10 seconds
                level = client.get_audio_level()
                print(f"Audio level: {level:.3f}")
                await asyncio.sleep(0.1)
            
            client.stop_live_audio_capture()
        
        await client.end_session("Live audio test completed")
```

### Enhanced Testing

```python
async def test_enhanced_features():
    async with MockAudioCodesClient("ws://localhost:8080") as client:
        # Simple conversation test with automatic setup/teardown
        success = await client.simple_conversation_test([
            "audio/greeting.wav",
            "audio/question.wav",
            "audio/followup.wav"
        ], session_name="EnhancedTest")
        
        print(f"Test completed: {'SUCCESS' if success else 'FAILED'}")
```

## Configuration

The client can be configured with various parameters:

```python
client = MockAudioCodesClient(
    bridge_url="ws://localhost:8080",
    bot_name="MyTestBot",
    caller="+15551234567"
)
```

## Audio File Support

The audio manager supports various audio formats and automatically handles:

- Format conversion to 16kHz, 16-bit PCM
- Audio chunking for streaming
- Caching for improved performance
- Resampling for different sample rates

## Testing Features

### Conversation Testing

- **Multi-turn conversations**: Test complex conversation flows
- **Audio collection**: Automatically collect and save AI responses
- **Turn-by-turn analysis**: Detailed results for each conversation turn
- **Success rate calculation**: Measure conversation effectiveness

### Session Testing

- **Session lifecycle**: Test session initiation, resumption, and ending
- **Connection validation**: Verify bridge connectivity
- **Event handling**: Test DTMF, hangup, and custom events
- **State tracking**: Monitor session and stream states

### Audio Testing

- **Audio streaming**: Test user and play audio streams
- **Format handling**: Test various audio formats and conversions
- **Chunking**: Test audio chunking and streaming
- **Caching**: Test audio file caching performance
- **Live audio capture**: Test real-time microphone input
- **VAD processing**: Test voice activity detection
- **Device management**: Test audio device selection

## Error Handling

The module provides comprehensive error handling:

- Connection failures
- Session errors
- Audio file errors
- Timeout handling
- Message processing errors

## Logging

All components use structured logging with prefixes:

- `[CLIENT]`: Main client operations
- `[SESSION]`: Session management
- `[MESSAGE]`: Message handling
- `[AUDIO]`: Audio operations
- `[LIVE_AUDIO]`: Live audio capture and VAD
- `[CONVERSATION]`: Conversation management

## Performance Features

- **Audio caching**: Reduces repeated file I/O
- **Efficient chunking**: Optimized audio chunk processing
- **Async operations**: Non-blocking WebSocket communication
- **Memory management**: Automatic cleanup and state reset

## Integration with Bridge Server

The mock client is designed to work seamlessly with the bridge server:

- Compatible WebSocket protocol
- Proper message formatting
- Session state synchronization
- Audio stream handling

## Live Audio Features

### Real-time Microphone Input

The live audio manager provides comprehensive real-time audio capture:

- **Device enumeration**: Automatically detect available audio input devices
- **Device selection**: Choose specific audio input devices
- **Real-time capture**: Stream audio directly from microphone
- **Configurable parameters**: Adjust sample rate, chunk size, and buffer settings
- **Thread-safe processing**: Non-blocking audio capture and processing

### Voice Activity Detection (VAD)

Built-in VAD with configurable parameters:

- **Energy-based detection**: Simple and efficient speech detection
- **Configurable thresholds**: Adjust speech and silence detection sensitivity
- **Duration filtering**: Minimum speech and silence duration settings
- **Real-time events**: Immediate VAD event generation
- **Bridge integration**: Automatic VAD event forwarding to bridge server

### Audio Level Monitoring

Real-time audio level monitoring for visualization:

- **Level calculation**: Current audio level (0.0 to 1.0)
- **Visualization support**: Ready for audio level meters
- **Performance optimized**: Efficient level calculation
- **Thread-safe access**: Safe concurrent access from multiple threads

## Future Enhancements

### Advanced Audio Features (Planned)

- **Advanced VAD algorithms**: More sophisticated speech detection
- **Transcription support**: Audio-to-text conversion
- **Advanced audio processing**: Enhanced audio format support
- **Performance monitoring**: Detailed metrics and analytics
- **Multi-channel support**: Stereo and multi-channel audio

## Examples

See the `example_usage.py` file in the parent directory for more detailed examples of how to use the AudioCodes mock client.

## Contributing

When adding new features to the AudioCodes mock client:

1. Follow the modular structure
2. Add appropriate data models
3. Include comprehensive logging
4. Add error handling
5. Update this README
6. Add tests for new functionality 