# LocalRealtime Module Design Document

## Overview

The `LocalRealtime` module provides a comprehensive, modular simulation of the OpenAI Realtime API for local development and testing. It enables developers to build, test, and validate real-time conversational AI systems without requiring access to the actual OpenAI API, supporting text, audio, function calls, and advanced event handling.

## Architecture

### Core Design Principles

1. **Separation of Concerns**: Each submodule (client, models, handlers, audio, etc.) has a clear, focused responsibility.
2. **Extensibility**: New response types, event handlers, and audio/transcription backends can be added with minimal changes.
3. **Testability**: The system is designed for easy unit and integration testing, with mockable interfaces and clear state management.
4. **Configurability**: Behavior is controlled via configuration objects and environment variables, supporting a wide range of scenarios.
5. **Realism**: Simulates the OpenAI Realtime API as closely as possible, including event sequencing, streaming, and error handling.

### Module Structure

```
opusagent/mock/realtime/
├── __init__.py              # Public API exports
├── README.md                # Usage and feature overview
├── DESIGN.md                # (This file)
├── models.py                # Data models and configuration classes
├── client.py                # Main LocalRealtimeClient implementation
├── handlers.py              # Event handler manager and event logic
├── audio.py                 # Audio file management and caching
├── generators.py            # Response generation logic (text, audio, function calls)
├── utils.py                 # Utility functions and constants
├── websocket_mock.py        # Mock WebSocket interface for drop-in testing
└── ... (other helpers)
```

## Components

### 1. Models (`models.py`)
- **Purpose**: Define Pydantic models for session state, response configuration, selection criteria, and conversation context.
- **Key Models**:
  - `ConversationContext`: Tracks conversation history, user input, intents, and modalities.
  - `ResponseSelectionCriteria`: Defines rules for selecting responses (keywords, intents, turn count, etc.).
  - `LocalResponseConfig`: Configures mock responses (text, audio, function call, delays, selection criteria).
  - `MockSessionState`: Tracks session, audio buffer, and active response state.

### 2. Main Client (`client.py`)
- **Purpose**: Implements the `LocalRealtimeClient`, the core orchestrator for the mock API.
- **Responsibilities**:
  - Manages session state, event routing, and response generation.
  - Integrates audio management, VAD, and transcription modules.
  - Provides a public API for connecting, sending/receiving events, and managing context.
  - Handles configuration, extensibility, and performance tracking.
- **Key Methods**:
  - `connect()`, `disconnect()`: Manage WebSocket lifecycle.
  - `add_response_config()`, `get_response_config()`: Manage response scenarios.
  - `update_conversation_context()`: Track and analyze user input.
  - `setup_smart_response_examples()`: Preload example response configs.
  - `get_session_state()`, `get_audio_buffer()`: Inspect internal state.

### 3. Event Handlers (`handlers.py`)
- **Purpose**: Centralized event handler registration and management.
- **Responsibilities**:
  - Register and dispatch event handlers for all supported API events.
  - Manage session updates, audio buffer operations, and response lifecycle.
  - Integrate VAD and transcription for realistic speech detection and input transcription.
  - Provide extensibility for custom event handlers.

### 4. Audio Management (`audio.py`)
- **Purpose**: Efficiently load, cache, and manage audio files for mock responses.
- **Features**:
  - Intelligent caching for performance.
  - Support for multiple audio formats and resampling.
  - Fallback to silence generation if files are missing.
  - Metadata tracking (sample rate, channels).

### 5. Response Generation (`generators.py`)
- **Purpose**: Simulate streaming of text, audio, and function call responses.
- **Features**:
  - Character-by-character text streaming with delays.
  - Chunked audio streaming with configurable chunk size and delay.
  - Function call simulation with argument streaming.
  - Transcript event generation for both input and output audio.
  - Error event generation for edge case testing.

### 6. Utilities (`utils.py`)
- **Purpose**: Provide shared constants, validation, event creation, and re-exports of common utilities.
- **Features**:
  - Audio and event constants.
  - Helper functions for event formatting and validation.
  - Re-exports of audio and websocket utilities.

### 7. Mock WebSocket (`websocket_mock.py`)
- **Purpose**: Provide a drop-in, WebSocket-compatible interface for the mock client.
- **Features**:
  - Implements `send`, `recv`, `close`, and async iteration.
  - Routes messages through the `LocalRealtimeClient`.
  - Supports context manager and connection pooling for integration tests.

## Design Patterns

- **Factory Pattern**: Used for VAD and transcription backend instantiation.
- **Strategy Pattern**: Different response selection and generation strategies.
- **Observer Pattern**: Event handler registration and dispatch.
- **State Pattern**: Session and conversation context management.
- **Adapter Pattern**: Mock WebSocket interface adapts the client to WebSocket API.

## Extensibility

- **Add New Response Types**: Implement new response generators and register them in the client.
- **Custom Event Handlers**: Register additional handlers for new or custom events.
- **Audio/Transcription Backends**: Plug in new audio or transcription modules via the factory pattern.
- **Configuration**: Extend models and config loading to support new features.

## Usage Example

```python
from opusagent.mock.realtime import LocalRealtimeClient, LocalResponseConfig, ResponseSelectionCriteria

client = LocalRealtimeClient()
client.add_response_config(
    "greeting",
    LocalResponseConfig(
        text="Hello! How can I help you?",
        audio_file="audio/greeting.wav",
        selection_criteria=ResponseSelectionCriteria(
            required_keywords=["hello", "hi"],
            max_turn_count=1,
            priority=10
        )
    )
)
await client.connect("ws://localhost:8080")
client.update_conversation_context("Hello there!")
```

## Testing Strategy

- **Unit Tests**: For models, event handlers, and response generators.
- **Integration Tests**: End-to-end tests using the mock WebSocket interface.
- **Performance Tests**: Measure response timing and resource usage.
- **Error Handling Tests**: Simulate and verify error event generation.

## Migration Guide

- **From Monolithic to Modular**: All major features are preserved; imports and configuration are backward compatible.
- **API Changes**: Most public APIs are unchanged; new features are additive.
- **Configuration**: Environment variables and config objects remain the primary control mechanism.

## Future Enhancements

- **Additional Event Types**: Support for more OpenAI API events.
- **Advanced Audio Processing**: Real-time effects, noise simulation.
- **Customizable Streaming**: User-defined streaming patterns and delays.
- **Metrics and Analytics**: Built-in performance and usage tracking.
- **Plugin System**: For user-contributed response and event logic.

## Conclusion

The `LocalRealtime` module provides a robust, extensible, and realistic simulation of the OpenAI Realtime API. Its modular design, clear separation of concerns, and comprehensive feature set make it ideal for local development, testing, and research in conversational AI systems. 