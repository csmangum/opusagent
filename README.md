# OpusAgent

## Overview

OpusAgent is an open-source Python framework for building real-time voice agents. It provides a FastAPI-based server that bridges telephony platforms like AudioCodes VoiceAI Connect and Twilio with AI backends such as OpenAI's Realtime API. The package enables developers to create intelligent, conversational AI systems for voice interactions, with support for audio streaming, voice activity detection, transcription, and function calling.

Key components include bridges for different platforms, models for API schemas, utilities for audio and WebSocket handling, and tools for testing and simulation.

## Features

- **Real-Time Audio Streaming**: Bidirectional audio between telephony platforms and AI.
- **Voice Activity Detection (VAD)**: Local VAD using Silero or other backends.
- **Transcription**: Local transcription with PocketSphinx and Whisper.
- **Function Calling**: Integration with OpenAI's function tools for structured interactions.
- **Mock Clients**: For testing without real telephony, including live microphone input.
- **Dual Agent Simulation**: Test conversations between AI caller and customer service agents.
- **Session Management**: Stateful sessions with resume capabilities.
- **Audio Playback**: Local playback of AI responses.
- **Extensible Architecture**: Modular design for adding new bridges and features.

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/your-org/fastagent.git
cd fastagent
pip install -r requirements.txt
```

## Quick Start

1. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

2. Start the server:
   ```bash
   python -m opusagent.main
   ```

3. Test with a mock client or connect via telephony platform.

For local testing:
- Use `python scripts/test_local_vad.py` for live microphone testing.
- Run agent-to-agent conversations: `python scripts/test_agent_conversation.py`.

## Configuration

Configure via environment variables:
- `OPENAI_API_KEY`: Required for OpenAI integration.
- `VAD_ENABLED`: Enable/disable VAD (default: true).
- `USE_LOCAL_REALTIME`: Use local mock instead of OpenAI (default: false).
- `LOCAL_REALTIME_ENABLE_TRANSCRIPTION`: Enable local transcription (default: true).
- And more (see docs for full list).

## Usage Examples

### Basic Server Start
```bash
python -m opusagent.main
```

### Agent Conversation
```bash
python scripts/test_agent_conversation.py
```

### Local Realtime Mode
```bash
USE_LOCAL_REALTIME=true python -m opusagent.main
```

For more examples, see the `scripts/` directory and subpackage READMEs.

## Architecture

- **main.py**: FastAPI server with WebSocket endpoints for bridges.
- **bridges/**: Platform-specific bridges (e.g., audiocodes_bridge.py, twilio_bridge.py).
- **models/**: Pydantic models for API schemas.
- **local/**: Mock clients and local realtime simulation.
- **vad/**: Voice Activity Detection module.
- **transcription/**: Local transcription backends.
- **utils/**: Audio and WebSocket utilities.

For detailed design, see docs/DESIGN.md and subpackage READMEs.

## Roadmap / Future Features

Planned enhancements:
- Voice fingerprinting for user identification
- Cross-session user memory for persistent context
- Multi-language support with automatic detection
- Integration with additional AI models (e.g., Grok, Claude)
- Advanced conversation analytics and reporting
- Web-based monitoring dashboard
- Multimodal support (e.g., video calls)
- Enhanced security features (audio encryption, compliance tools)
- And more based on community feedback

Contributions to these features are welcome! 

## Contributing

Contributions welcome! See LICENSE for details.

## License

MIT License 