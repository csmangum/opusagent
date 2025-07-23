# OpusAgent

OpusAgent is an open-source Python framework for building real-time voice agents. It provides a FastAPI-based server that bridges telephony platforms like AudioCodes VoiceAI Connect and Twilio with AI backends such as OpenAI's Realtime API. The package enables developers to create intelligent, conversational AI systems for voice interactions, with support for audio streaming, voice activity detection, transcription, and function calling.

Key components include bridges for different platforms, models for API schemas, utilities for audio and WebSocket handling, and tools for testing and simulation.

## Features

- **[Real-Time Audio Streaming](docs/realtime_audio_streaming.md)**: Bidirectional audio between telephony platforms and AI.
- **[Voice Activity Detection (VAD)](docs/vad_implementation.md)**: Local VAD using Silero or other backends.
- **[Transcription](docs/transcription_implementation.md)**: Local transcription with PocketSphinx and Whisper.
- **[Function Calling](docs/function_calling_implementation.md)**: Integration with OpenAI's function tools for structured interactions.
- **[Mock Clients](docs/mock_clients_implementation.md)**: For testing without real telephony, including live microphone input.
- **[Dual Agent Simulation](docs/dual_agent_simulation_implementation.md)**: Test conversations between AI caller and customer service agents.
- **[Session Management](docs/session_management_implementation.md)**: Stateful sessions with resume capabilities.
- **[Audio Playback](docs/audio_playback_implementation.md)**: Local playback of AI responses.
- **[Extensible Architecture](docs/extensible_architecture_implementation.md)**: Modular design for adding new bridges and features.

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

- [**main.py**](./opusagent/main.py): FastAPI server with WebSocket endpoints for bridges.
- [**bridges/**](./opusagent/bridges/): Platform-specific bridges (e.g., audiocodes_bridge.py, twilio_bridge.py).
- [**models/**](./opusagent/models/): Pydantic models for API schemas.
- [**local/**](./opusagent/local/): Mock clients and local realtime simulation.
- [**vad/**](./opusagent/vad/): Voice Activity Detection module.
- [**transcription/**](./opusagent/local/transcription/): Local transcription backends.
- [**utils/**](./opusagent/utils/): Audio and WebSocket utilities.

For detailed design, see docs/DESIGN.md and subpackage READMEs.

## Roadmap / Future Features

Planned enhancements:
- [Voice fingerprinting for user identification](docs/voice_fingerprinting_implementation.md)
- [Cross-session user memory for persistent context](docs/cross_session_user_memory_implementation.md)
- [Web-based monitoring dashboard](docs/web_based_monitoring_dashboard_implementation.md)
- [Multimodal support (e.g., video calls)](docs/multimodal_support_implementation.md)
- [Enhanced security features (audio encryption, compliance tools)](docs/enhanced_security_features_implementation.md)
- [Call review interface](docs/call_review_interface_implementation.md)
- Multi-language support with automatic detection
- Integration with additional AI models
- And more based on community feedback

Contributions to these features are welcome! 

## Contributing

We welcome contributions! Here's how to get started:

1. **Create an Issue**: Before making changes, please create an issue to discuss the feature, bug fix, or improvement you'd like to contribute.

2. **Fork the Repository**: Fork the repository to your GitHub account.

3. **Create a Feature Branch**: Create a new branch from `main` for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make Your Changes**: Implement your changes with appropriate tests and documentation.

5. **Submit a Pull Request**: Push your branch and create a pull request against the main repository.

### Guidelines

- Follow the existing code style and conventions
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass before submitting
- Provide clear commit messages and PR descriptions

### Getting Help

- Check existing issues and discussions
- Join our community discussions
- Reach out if you need help getting started

For more information, see the [LICENSE](LICENSE) file.

## License

MIT License 