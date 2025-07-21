# Local Realtime Bridge Integration

This document explains how to use the Local Realtime Client with the bridges instead of connecting to the OpenAI Realtime API. This feature enables testing, development, and scenarios where you want to avoid API costs or network dependencies.

## Overview

The Local Realtime Bridge integration allows you to:

- **Test without API costs**: Use local responses instead of OpenAI API calls
- **Develop offline**: Work without internet connectivity
- **Simulate scenarios**: Create custom response patterns for testing
- **Reduce latency**: Local responses are faster than API calls
- **Customize behavior**: Configure VAD, transcription, and response selection

> **Note**: The Local Realtime module is located at `opusagent/local/realtime/` and provides imports from `opusagent.local.realtime`.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Platform      │    │   Bridge         │    │  Local/OpenAI   │
│   (AudioCodes/  │◄──►│   (BaseBridge)   │◄──►│  Realtime API   │
│   Twilio/etc.)  │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

The bridge can connect to either:
- **OpenAI Realtime API**: Real AI responses (requires API key)
- **Local Realtime Client**: Mock responses (no API key needed)

### Module Structure

The Local Realtime module is located at `opusagent/local/realtime/` with the following structure:

```
opusagent/local/realtime/
├── __init__.py              # Public API exports
├── README.md                # Usage and feature overview
├── DESIGN.md                # Design documentation
├── models.py                # Data models and configuration classes
├── client.py                # Main LocalRealtimeClient implementation
├── handlers.py              # Event handler manager and event logic
├── audio.py                 # Audio file management and caching
├── generators.py            # Response generation logic
├── utils.py                 # Utility functions and constants
└── websocket_mock.py        # Mock WebSocket interface
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_LOCAL_REALTIME` | `false` | Enable local realtime client |
| `LOCAL_REALTIME_ENABLE_TRANSCRIPTION` | `false` | Enable local transcription |
| `LOCAL_REALTIME_SETUP_SMART_RESPONSES` | `true` | Use smart response examples |
| `LOCAL_REALTIME_VAD_BACKEND` | `silero` | VAD backend (silero/pocketsphinx) |
| `LOCAL_REALTIME_VAD_THRESHOLD` | `0.5` | VAD threshold (0.0-1.0) |
| `LOCAL_REALTIME_VAD_SAMPLE_RATE` | `16000` | VAD sample rate |
| `LOCAL_REALTIME_TRANSCRIPTION_BACKEND` | `pocketsphinx` | Transcription backend |
| `LOCAL_REALTIME_TRANSCRIPTION_LANGUAGE` | `en` | Transcription language |
| `LOCAL_REALTIME_TRANSCRIPTION_MODEL_SIZE` | `base` | Whisper model size |

### Example Configuration

```bash
# Enable local realtime with transcription
export USE_LOCAL_REALTIME=true
export LOCAL_REALTIME_ENABLE_TRANSCRIPTION=true
export LOCAL_REALTIME_VAD_THRESHOLD=0.3
export LOCAL_REALTIME_SETUP_SMART_RESPONSES=true

# Start the server
python opusagent/main.py
```

**Import Example:**
```python
from opusagent.local.realtime import LocalRealtimeClient, LocalResponseConfig, ResponseSelectionCriteria
```

## Usage

### Importing the Module

```python
# Main client and models
from opusagent.local.realtime import (
    LocalRealtimeClient,
    LocalResponseConfig,
    ResponseSelectionCriteria,
    ConversationContext
)

# Mock WebSocket interface
from opusagent.local.realtime import (
    MockWebSocketConnection,
    MockWebSocketConnectionManager,
    create_mock_websocket_connection
)
```

### Starting the Server

```bash
# Basic local realtime
USE_LOCAL_REALTIME=true python opusagent/main.py

# With custom configuration
USE_LOCAL_REALTIME=true \
LOCAL_REALTIME_ENABLE_TRANSCRIPTION=true \
LOCAL_REALTIME_VAD_THRESHOLD=0.3 \
python opusagent/main.py
```

### Testing with Clients

```bash
# Test with local VAD client
python scripts/test_local_vad.py

# Test with mock telephony client
python scripts/validate_telephony_mock.py

# Run the demo
USE_LOCAL_REALTIME=true python scripts/demo_local_realtime_bridge.py
```

### Supported Endpoints

All WebSocket endpoints support local realtime:

- `/ws/telephony` - AudioCodes bridge
- `/caller-agent` - Caller agent bridge  
- `/twilio-agent` - Twilio bridge

## Features

### Smart Response Selection

The local realtime client includes intelligent response selection based on:

- **Keywords**: Match user input keywords
- **Intents**: Detect conversation intents (greeting, help, complaint, etc.)
- **Turn count**: Different responses based on conversation position
- **Modalities**: Text vs audio responses
- **Function calls**: Simulate function call responses

### Voice Activity Detection (VAD)

Local VAD support with configurable:

- **Backend**: Silero (default) or PocketSphinx
- **Threshold**: Adjust sensitivity (0.0-1.0)
- **Sample rate**: Audio processing rate
- **Real-time processing**: Live speech detection

### Local Transcription

Optional local transcription using:

- **PocketSphinx**: Lightweight, offline
- **Whisper**: High accuracy (requires more resources)
- **Configurable**: Language, model size, confidence thresholds

### Performance Metrics

Track response performance:

- **Response timing**: Generation duration
- **Response selection**: Which responses were chosen
- **VAD metrics**: Speech detection accuracy
- **Transcription metrics**: Accuracy and timing

## Customization

### Custom Response Configurations

```python
from opusagent.local.realtime import LocalResponseConfig, ResponseSelectionCriteria

# Create custom responses
custom_responses = {
    "greeting": LocalResponseConfig(
        text="Hello! Welcome to our service.",
        delay_seconds=0.02,
        selection_criteria=ResponseSelectionCriteria(
            required_keywords=["hello", "hi"],
            priority=20
        )
    ),
    "help": LocalResponseConfig(
        text="I'm here to help! What do you need?",
        delay_seconds=0.03,
        selection_criteria=ResponseSelectionCriteria(
            required_keywords=["help", "assist"],
            priority=15
        )
    )
}

# Use in bridge configuration
local_config = {
    "response_configs": custom_responses,
    "setup_smart_responses": False  # Don't use defaults
}
```

### VAD Configuration

```python
vad_config = {
    "backend": "silero",
    "threshold": 0.3,  # More sensitive
    "sample_rate": 16000,
    "chunk_size": 512
}
```

### Transcription Configuration

```python
transcription_config = {
    "backend": "whisper",
    "model_size": "base",
    "language": "en",
    "confidence_threshold": 0.6,
    "chunk_duration": 2.0
}
```

## Integration with Bridges

### BaseRealtimeBridge Changes

The base bridge now supports:

```python
class BaseRealtimeBridge:
    def __init__(
        self,
        platform_websocket,
        realtime_websocket,
        session_config,
        use_local_realtime=False,
        local_realtime_config=None,
        **kwargs
    ):
        # Initialize local realtime client if requested
        if use_local_realtime:
            self._initialize_local_realtime_client()
```

### Bridge-Specific Support

All bridge implementations support local realtime:

- **AudioCodesBridge**: Full AudioCodes VAIC support
- **TwilioBridge**: Complete Twilio Media Streams support
- **CallAgentBridge**: Caller agent functionality

### Transparent Operation

The bridges work identically regardless of backend:

- Same event handling
- Same audio processing
- Same function calls
- Same session management

## Testing

### Demo Script

Run the comprehensive demo:

```bash
USE_LOCAL_REALTIME=true python scripts/demo_local_realtime_bridge.py
```

### Validation Scripts

```bash
# Test local VAD integration
python scripts/validate_vad_integration.py

# Test transcription integration
python scripts/validate_transcription_capability.py

# Test bridge integration
python scripts/validate_telephony_mock.py
```

### Unit Tests

```bash
# Run bridge tests
pytest tests/opusagent/bridges/ -v

# Run local realtime tests
pytest tests/opusagent/realtime/ -v
```

**Available Test Files:**
- `tests/opusagent/realtime/test_client.py` - Main client tests
- `tests/opusagent/realtime/test_models.py` - Data model tests
- `tests/opusagent/realtime/test_handlers.py` - Event handler tests
- `tests/opusagent/realtime/test_generators.py` - Response generation tests
- `tests/opusagent/realtime/test_audio.py` - Audio management tests
- `tests/opusagent/realtime/test_transcription.py` - Transcription tests

## Troubleshooting

### Common Issues

1. **Import Error**: Ensure `opusagent.local.realtime` is available
2. **VAD Initialization**: Check VAD dependencies (torch, silero)
3. **Transcription**: Verify transcription backend installation
4. **Response Selection**: Check response configuration syntax

### Debugging

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
USE_LOCAL_REALTIME=true python opusagent/main.py
```

Check bridge state:

```python
# Get local realtime client
client = bridge.get_local_realtime_client()

# Check VAD state
vad_state = client.get_vad_state()

# Check transcription state
transcription_state = client.get_transcription_state()

# Get performance metrics
timings = client.get_response_timings()
```

## Performance Considerations

### Local vs OpenAI

| Aspect | Local Realtime | OpenAI API |
|--------|----------------|------------|
| **Latency** | ~10-50ms | ~200-1000ms |
| **Cost** | Free | Per API call |
| **Accuracy** | Configurable | High |
| **Offline** | Yes | No |
| **Customization** | Full | Limited |

### Resource Usage

- **Memory**: ~100-500MB (depending on models)
- **CPU**: Moderate (VAD + transcription)
- **GPU**: Optional (for Whisper/advanced VAD)

### Optimization Tips

1. **Use PocketSphinx** for lightweight transcription
2. **Adjust VAD threshold** for your environment
3. **Cache audio files** for faster responses
4. **Limit response configurations** to essential ones

## Future Enhancements

### Planned Features

- **Response templates**: Dynamic response generation
- **Conversation flows**: Multi-turn response patterns
- **Audio synthesis**: Local TTS integration
- **Advanced VAD**: Multi-speaker detection
- **Performance profiling**: Detailed metrics dashboard

### Integration Opportunities

- **Custom LLMs**: Local model integration
- **Audio processing**: Advanced audio effects
- **Multi-language**: Internationalization support
- **Analytics**: Conversation analytics and insights

## Conclusion

The Local Realtime Bridge integration provides a powerful alternative to the OpenAI Realtime API for testing, development, and cost-sensitive deployments. It maintains full compatibility with existing bridge functionality while offering extensive customization options.

For more information, see:
- [Local Realtime Client Documentation](../opusagent/local/realtime/README.md)
- [Bridge Architecture](base_bridge.md)
- [Testing Guide](testing_guide.md) 