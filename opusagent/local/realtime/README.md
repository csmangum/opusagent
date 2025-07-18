# LocalRealtime Module - OpenAI Realtime API Simulator

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](https://example.com) [![License](https://img.shields.io/badge/license-MIT-green.svg)](https://example.com/license)

## Overview

The LocalRealtime module provides a comprehensive mock implementation of the OpenAI Realtime API WebSocket connection. It is designed for testing and development purposes, allowing you to simulate real-time interactions without requiring an actual OpenAI API connection. This module enables developers to build and test applications that integrate with the OpenAI Realtime API in a controlled, local environment.

Key benefits include:
- **Cost-Effective Testing**: Develop and test without incurring API costs or hitting rate limits.
- **Customizable Responses**: Configure mock responses with text, audio, and function calls.
- **Intelligent Response Selection**: Context-aware response choosing based on conversation history, intents, and keywords.
- **Audio Handling**: Support for audio file streaming, caching, and silence generation.
- **Event Simulation**: Complete simulation of WebSocket events matching the OpenAI API.

This module is part of the larger `opusagent` project and is located in `opusagent/mock/realtime`.

## Installation

To use the LocalRealtime module, ensure you have the `opusagent` package installed. If not, install it via pip:

```bash
pip install opusagent
```

For development or if you need to work with the source code:

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/opusagent.git
   cd opusagent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Install additional dependencies for advanced features:
   - For audio processing: `pip install pydub`
   - For VAD: Ensure Silero VAD is configured (see VAD documentation)
   - For transcription: `pip install pocketsphinx` or `pip install openai-whisper`

## Quick Start

Here's a basic example to get you started:

```python
from opusagent.mock.realtime import LocalRealtimeClient, LocalResponseConfig, ResponseSelectionCriteria

# Create the mock client
client = LocalRealtimeClient()

# Add a custom response configuration
client.add_response_config(
    "greeting",
    LocalResponseConfig(
        text="Hello! How can I help you today?",
        audio_file="path/to/greeting.wav",
        delay_seconds=0.03,
        selection_criteria=ResponseSelectionCriteria(
            required_keywords=["hello", "hi"],
            max_turn_count=1,
            priority=10
        )
    )
)

# Connect to a mock WebSocket server (you'll need to run a WebSocket server locally)
await client.connect("ws://localhost:8080")

# Update conversation context
client.update_conversation_context("Hello there!")

# The client will now select and generate responses based on the context
```

## Key Features

### Smart Response Selection
The client uses intelligent response selection based on:
- User input keywords and content
- Conversation turn count and history
- Detected intents (e.g., greeting, help, complaint)
- Requested modalities (text, audio)
- Function call requirements
- Priority scoring

### Audio Management
- Caching of audio files for performance
- Support for multiple formats via `AudioUtils`
- Fallback to silence generation
- Chunked streaming with configurable delays

### Event Handling
- Complete simulation of OpenAI Realtime API events
- Custom event handler registration
- Session management and updates

### VAD and Transcription
- Voice Activity Detection (VAD) integration
- Local audio transcription using PocketSphinx or Whisper
- Configurable backends and parameters

## Configuration

### Response Configurations
Use `LocalResponseConfig` to define mock responses:

```python
config = LocalResponseConfig(
    text="Response text",
    audio_file="path/to/audio.wav",  # Optional
    delay_seconds=0.05,             # Text streaming delay
    audio_chunk_delay=0.2,          # Audio streaming delay
    function_call={                 # Optional function call
        "name": "function_name",
        "arguments": {"param": "value"}
    },
    selection_criteria=ResponseSelectionCriteria(
        required_keywords=["help"],
        required_intents=["help_request"],
        priority=15
    )
)
client.add_response_config("help", config)
```

### Session Configuration
Configure the mock session using OpenAI's `SessionConfig`:

```python
from opusagent.models.openai_api import SessionConfig

session_config = SessionConfig(
    model="gpt-4o-realtime-preview",
    modalities=["text", "audio"],
    voice="alloy",
    turn_detection={"type": "server_vad"}
)
client = LocalRealtimeClient(session_config=session_config)
```

### VAD and Transcription
Enable and configure VAD/transcription:

```python
vad_config = {
    "backend": "silero",
    "threshold": 0.5
}
transcription_config = {
    "backend": "whisper",
    "model_size": "base"
}
client = LocalRealtimeClient(
    enable_vad=True,
    vad_config=vad_config,
    enable_transcription=True,
    transcription_config=transcription_config
)
```

## Advanced Usage

### Custom Event Handlers
Register custom handlers for specific events:

```python
async def custom_handler(data):
    print(f"Custom handling: {data}")

client.register_event_handler("response.create", custom_handler)
```

### Performance Monitoring
Access response timings:

```python
timings = client.get_response_timings()
for t in timings:
    print(f"Response {t['response_key']}: {t['duration']:.3f}s")
```

### State Management
Inspect and modify session state:

```python
state = client.get_session_state()
print(f"Session ID: {state['session_id']}")

# Modify audio buffer
client.set_audio_buffer([b'audio_chunk'])
```

## Testing and Development

Run unit tests:

```bash
pytest tests/opusagent/mock/realtime
```

For integration testing, set up a mock WebSocket server and connect the client.

## Contributing

Contributions are welcome! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 