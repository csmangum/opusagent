"""
Models module for data structures and state management in the real-time voice agent.

This module provides structured data models and state management classes for the application,
defining the schemas and interfaces for both AudioCodes VoiceAI Connect and OpenAI Realtime API.

Key components:
- audiocodes_api: Pydantic models for validating and serializing messages in the 
  AudioCodes Bot API WebSocket protocol, ensuring consistent communication.
- openai_api: Type-safe models for the OpenAI Realtime API message structures,
  supporting the real-time speech, chat functionality, and function calling capabilities.
  Includes models for session management, conversation items, client-server events,
  and audio streaming in the OpenAI Realtime API.
- conversation: State management for active voice conversations, tracking WebSocket
  connections and media formats throughout the call lifecycle.

The models module serves as the foundation for type safety and data validation
across the application, helping ensure robust communication with external services.

Usage examples:
```python
# Create and use conversation management
from fastagent.models.conversation import ConversationManager

# Initialize conversation tracking
conversation_manager = ConversationManager()

# Register a new conversation
conversation_manager.add_conversation(
    conversation_id="1234-5678-90ab-cdef",
    websocket=websocket_connection,
    media_format="raw/lpcm16"
)

# Validate and parse incoming messages
from fastagent.models.audiocodes_api import SessionInitiateMessage

# Parse and validate a message from AudioCodes
message_data = {
    "type": "session.initiate",
    "conversationId": "1234-5678-90ab-cdef",
    "botName": "VoiceAgent",
    "caller": "+12025550123",
    "expectAudioMessages": True,
    "supportedMediaFormats": ["raw/lpcm16", "audio/wav"]
}
session_message = SessionInitiateMessage(**message_data)

# Create response messages
from fastagent.models.audiocodes_api import SessionAcceptedResponse

response = SessionAcceptedResponse(
    type="session.accepted",
    conversationId=session_message.conversationId,
    mediaFormat="raw/lpcm16"
)
await websocket.send_text(response.json())

# Using OpenAI Realtime API models
from fastagent.models.openai_api import SessionConfig, ResponseCreateEvent

# Configure a new OpenAI Realtime session
session_config = SessionConfig(
    modalities=["text", "audio"],
    model="gpt-4",
    voice="alloy",
    input_audio_format="pcm16"
)

# Create a response event
response_event = ResponseCreateEvent()
```
"""

from fastagent.models.conversation import ConversationManager
from fastagent.models.audiocodes_api import (
    ActivitiesMessage,
    ActivityEvent,
    BaseMessage,
    ConnectionValidatedResponse,
    ConnectionValidateMessage,
    IncomingMessage,
    OutgoingMessage,
    PlayStreamChunkMessage,
    PlayStreamStartMessage,
    PlayStreamStopMessage,
    SessionAcceptedResponse,
    SessionEndMessage,
    SessionErrorResponse,
    SessionInitiateMessage,
    SessionResumeMessage,
    UserStreamChunkMessage,
    UserStreamHypothesisResponse,
    UserStreamStartedResponse,
    UserStreamStartMessage,
    UserStreamStopMessage,
    UserStreamStoppedResponse,
)

from fastagent.models.openai_api import (
    MessageRole,
    OpenAIMessage,
    SessionConfig,
    RealtimeSessionResponse,
    ConversationItemType,
    ConversationItemStatus,
    ConversationItemContentParam,
    ConversationItemParam,
    ConversationItem,
    ClientEventType,
    ServerEventType,
    ClientEvent,
    ServerEvent,
    RealtimeFunctionCall,
    RealtimeFunctionCallOutput,
    SessionUpdateEvent,
    InputAudioBufferAppendEvent,
    InputAudioBufferCommitEvent,
    ConversationItemCreateEvent,
    ResponseCreateEvent,
    ErrorEvent,
    SessionCreatedEvent,
    ConversationItemCreatedEvent,
    ResponseTextDeltaEvent,
    ResponseAudioDeltaEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
    ResponseDoneEvent,
    RealtimeBaseMessage,
    RealtimeTranscriptMessage,
    RealtimeTurnMessage,
    RealtimeErrorMessage,
    RealtimeMessageContent,
    RealtimeMessage,
    RealtimeStreamMessage,
    RealtimeFunctionMessage,
    WebSocketErrorResponse,
)
