# Models Module

This module provides structured data models and state management for the OpusAgent application, defining the schemas and interfaces for both AudioCodes VoiceAI Connect and OpenAI Realtime API integration.

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

### `twilio_api.py`

Pydantic models for Twilio Media Streams WebSocket protocol, including:

- Connection and session management messages
- Audio streaming messages for real-time media
- DTMF tone detection and handling
- Audio playback control and synchronization
- Bidirectional audio streaming support

### `conversation.py`

State management for active voice conversations, including:

- Tracking WebSocket connections for each conversation
- Managing media format preferences
- Providing conversation lifecycle management (add, retrieve, remove)

## Usage Example

```python
# Create and use conversation management
from opusagent.models.conversation import ConversationManager

# Initialize conversation tracking
conversation_manager = ConversationManager()

# Register a new conversation
conversation_manager.add_conversation(
    conversation_id="1234-5678-90ab-cdef",
    websocket=websocket_connection,
    media_format="raw/lpcm16"
)

# Using OpenAI Realtime API models
from opusagent.models.openai_api import SessionConfig, ResponseCreateEvent

# Configure a new OpenAI Realtime session
session_config = SessionConfig(
    modalities=["text", "audio"],
    model="gpt-4",
    voice="alloy",
    input_audio_format="pcm16"
)

# Using Twilio Media Streams models
from opusagent.models.twilio_api import StartMessage, OutgoingMediaMessage

# Parse an incoming start message from Twilio
start_data = {
    "event": "start",
    "sequenceNumber": "1",
    "start": {
        "streamSid": "MZXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "accountSid": "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "callSid": "CAXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "tracks": ["inbound", "outbound"],
        "customParameters": {},
        "mediaFormat": {
            "encoding": "audio/x-mulaw",
            "sampleRate": 8000,
            "channels": 1
        }
    },
    "streamSid": "MZXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
}
start_message = StartMessage(**start_data)

# Send audio back to Twilio  
outgoing_media = OutgoingMediaMessage(
    event="media",
    streamSid=start_message.streamSid,
    media={"payload": "base64_encoded_audio_data"}
) 