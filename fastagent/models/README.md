# Models Module

This module provides structured data models and state management for the FastAgent application, defining the schemas and interfaces for both AudioCodes VoiceAI Connect and OpenAI Realtime API integration.

## Overview

The models module serves as the foundation for type safety and data validation across the application, ensuring robust communication with external services. It consists of the following components:

### `audiocodes_api.py`

Pydantic models for AudioCodes VoiceAI Connect Enterprise message schemas. This includes:

- Base message structures for the WebSocket protocol
- Session management messages (initiate, resume, end)
- Audio streaming messages for voice data
- Activity event messages (DTMF, hangup)
- Connection validation messages

### `openai_api.py`

Type-safe models for the OpenAI Realtime API message structures, including:

- Session configuration and management
- Conversation item models for different message types
- Event models for client-server WebSocket communication
- Function/tool calling structures
- Audio streaming message formats

### `conversation.py`

State management for active voice conversations, including:

- Tracking WebSocket connections for each conversation
- Managing media format preferences
- Providing conversation lifecycle management (add, retrieve, remove)

## Usage Example

```python
# Create and use conversation management
from app.models.conversation import ConversationManager

# Initialize conversation tracking
conversation_manager = ConversationManager()

# Register a new conversation
conversation_manager.add_conversation(
    conversation_id="1234-5678-90ab-cdef",
    websocket=websocket_connection,
    media_format="raw/lpcm16"
)

# Using OpenAI Realtime API models
from app.models.openai_api import SessionConfig, ResponseCreateEvent

# Configure a new OpenAI Realtime session
session_config = SessionConfig(
    modalities=["text", "audio"],
    model="gpt-4",
    voice="alloy",
    input_audio_format="pcm16"
) 