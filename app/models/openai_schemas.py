"""
Pydantic models for OpenAI Realtime API message structures.

This module provides type-safe models for the messages exchanged with the OpenAI Realtime API,
including both incoming and outgoing message formats.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Role of a participant in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class OpenAIMessage(BaseModel):
    """Base model for OpenAI messages."""
    role: MessageRole
    content: str


# Session-related models

class SessionConfig(BaseModel):
    """Configuration for a Realtime API Session."""
    modalities: List[str] = Field(default=["text"])  # e.g. ["text", "audio"]
    model: Optional[str] = None
    instructions: Optional[str] = None
    voice: Optional[str] = None
    input_audio_format: Optional[str] = None  # "pcm16" or "g711"
    output_audio_format: Optional[str] = None  # "pcm16" or "g711"
    turn_detection: Optional[Dict[str, Any]] = None  # {"type": "server_vad"}
    tools: Optional[List[Dict[str, Any]]] = None


class RealtimeSessionResponse(BaseModel):
    """Response from session creation endpoint."""
    client_secret: Dict[str, str]
    expires_at: int
    id: str


# Conversation-related models

class ConversationItemType(str, Enum):
    """Type of conversation item."""
    MESSAGE = "message"
    FUNCTION_CALL = "function_call" 
    FUNCTION_CALL_OUTPUT = "function_call_output"


class ConversationItemStatus(str, Enum):
    """Status of a conversation item."""
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    INTERRUPTED = "interrupted"


class ConversationItemContentParam(BaseModel):
    """Parameter for creating content in a conversation item."""
    type: str  # "input_text", "input_audio", etc.
    text: Optional[str] = None
    audio: Optional[str] = None  # Base64 encoded audio


class ConversationItemParam(BaseModel):
    """Parameter for creating a conversation item."""
    type: str  # "message", "function_call", "function_call_output"
    role: Optional[MessageRole] = None
    content: Optional[List[ConversationItemContentParam]] = None
    function_call: Optional[Dict[str, str]] = None  # For function_call type


class ConversationItem(BaseModel):
    """An item in the conversation."""
    id: str
    object: str = "realtime.item"
    type: ConversationItemType
    status: ConversationItemStatus
    role: MessageRole
    content: List[Dict[str, Any]]
    created_at: int


# Event models for client-server communication

class ClientEventType(str, Enum):
    """Types of events that can be sent to the server."""
    SESSION_UPDATE = "session.update"
    INPUT_AUDIO_BUFFER_APPEND = "input_audio_buffer.append"
    INPUT_AUDIO_BUFFER_COMMIT = "input_audio_buffer.commit"
    INPUT_AUDIO_BUFFER_CLEAR = "input_audio_buffer.clear"
    CONVERSATION_ITEM_CREATE = "conversation.item.create"
    CONVERSATION_ITEM_TRUNCATE = "conversation.item.truncate"
    CONVERSATION_ITEM_DELETE = "conversation.item.delete"
    RESPONSE_CREATE = "response.create"
    RESPONSE_CANCEL = "response.cancel"


class ServerEventType(str, Enum):
    """Types of events received from the server."""
    ERROR = "error"
    SESSION_CREATED = "session.created"
    SESSION_UPDATED = "session.updated"
    CONVERSATION_CREATED = "conversation.created"
    CONVERSATION_ITEM_CREATED = "conversation.item.created"
    CONVERSATION_ITEM_TRUNCATED = "conversation.item.truncated"
    CONVERSATION_ITEM_DELETED = "conversation.item.deleted"
    INPUT_AUDIO_BUFFER_COMMITTED = "input_audio_buffer.committed"
    INPUT_AUDIO_BUFFER_CLEARED = "input_audio_buffer.cleared"
    INPUT_AUDIO_BUFFER_SPEECH_STARTED = "input_audio_buffer.speech_started"
    INPUT_AUDIO_BUFFER_SPEECH_STOPPED = "input_audio_buffer.speech_stopped"
    RESPONSE_CREATED = "response.created"
    RESPONSE_DONE = "response.done"
    RESPONSE_CANCELLED = "response.cancelled"
    RESPONSE_TEXT_DELTA = "response.text.delta"
    RESPONSE_TEXT_DONE = "response.text.done"
    RESPONSE_AUDIO_DELTA = "response.audio.delta"
    RESPONSE_AUDIO_DONE = "response.audio.done"
    RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA = "response.function_call_arguments.delta"
    RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE = "response.function_call_arguments.done"


class ClientEvent(BaseModel):
    """Base model for events sent to the server."""
    type: str


class ServerEvent(BaseModel):
    """Base model for events received from the server."""
    type: str


# Function/Tool calling models

class RealtimeFunctionCall(BaseModel):
    """Function call structure in OpenAI Realtime API."""
    name: str
    arguments: str


class RealtimeFunctionCallOutput(BaseModel):
    """Output from a function call."""
    name: str
    output: str


# Specific client event implementations

class SessionUpdateEvent(ClientEvent):
    """Event to update session configuration."""
    type: str = "session.update"
    session: SessionConfig


class InputAudioBufferAppendEvent(ClientEvent):
    """Event to append audio to the input buffer."""
    type: str = "input_audio_buffer.append"
    audio: str  # Base64 encoded audio


class InputAudioBufferCommitEvent(ClientEvent):
    """Event to commit the audio buffer to the conversation."""
    type: str = "input_audio_buffer.commit"


class ConversationItemCreateEvent(ClientEvent):
    """Event to create a conversation item."""
    type: str = "conversation.item.create"
    item: ConversationItemParam


class ResponseCreateEvent(ClientEvent):
    """Event to create a model response."""
    type: str = "response.create"
    response: Optional[Dict[str, Any]] = None  # Optional response parameters


# Specific server event implementations

class ErrorEvent(ServerEvent):
    """Error message from OpenAI Realtime API."""
    type: str = "error"
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class SessionCreatedEvent(ServerEvent):
    """Event indicating a session was created."""
    type: str = "session.created"
    session: Dict[str, Any]


class ConversationItemCreatedEvent(ServerEvent):
    """Event indicating a conversation item was created."""
    type: str = "conversation.item.created"
    item: Dict[str, Any]


class ResponseTextDeltaEvent(ServerEvent):
    """Event containing a text delta from the model."""
    type: str = "response.text.delta"
    delta: str


class ResponseAudioDeltaEvent(ServerEvent):
    """Event containing an audio delta from the model."""
    type: str = "response.audio.delta"
    audio: str  # Base64 encoded audio chunk


class ResponseFunctionCallArgumentsDeltaEvent(ServerEvent):
    """Event containing a function call arguments delta."""
    type: str = "response.function_call_arguments.delta"
    delta: str


class ResponseDoneEvent(ServerEvent):
    """Event indicating the model response is complete."""
    type: str = "response.done"


# Legacy/compatibility models

class RealtimeBaseMessage(BaseModel):
    """Base model for Realtime API messages (legacy)."""
    type: str


class RealtimeTranscriptMessage(RealtimeBaseMessage):
    """Transcription message from OpenAI Realtime API (legacy)."""
    type: str = "transcript"
    text: str
    is_final: bool = Field(default=True)
    confidence: Optional[float] = None


class RealtimeTurnMessage(RealtimeBaseMessage):
    """Turn detection message from OpenAI Realtime API (legacy)."""
    type: str = "turn"
    trigger: str  # 'vad', 'timeout', etc.


class RealtimeErrorMessage(RealtimeBaseMessage):
    """Error message from OpenAI Realtime API (legacy)."""
    type: str = "error"
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class RealtimeMessageContent(BaseModel):
    """Content part of a message within a conversation (legacy)."""
    type: str = "text"
    text: str


class RealtimeMessage(BaseModel):
    """Message within a conversation (legacy)."""
    role: MessageRole
    content: Union[str, List[RealtimeMessageContent]]
    name: Optional[str] = None


class RealtimeStreamMessage(RealtimeBaseMessage):
    """Stream message for chat responses from OpenAI Realtime API (legacy)."""
    type: str = "message"
    message: RealtimeMessage


class RealtimeFunctionMessage(RealtimeBaseMessage):
    """Function call message from OpenAI Realtime API (legacy)."""
    type: str = "function_call"
    function_call: RealtimeFunctionCall


class WebSocketErrorResponse(BaseModel):
    """Error response from OpenAI WebSocket connection."""
    error: Dict[str, Any] 