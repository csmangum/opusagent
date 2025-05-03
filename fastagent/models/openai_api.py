"""
Pydantic models for OpenAI Realtime API message structures.

This module provides type-safe models for the messages exchanged with the OpenAI Realtime API,
including both incoming and outgoing message formats.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

# Define constants for event types
SESSION_CONFIG = "session.config"


class LogEventType(str, Enum):
    """Event types that should be logged in the bridge implementation."""

    ERROR = "error"
    RESPONSE_CONTENT_DONE = "response.content.done"
    RATE_LIMITS_UPDATED = "rate_limits.updated"
    RESPONSE_DONE = "response.done"
    INPUT_AUDIO_BUFFER_COMMITTED = "input_audio_buffer.committed"
    INPUT_AUDIO_BUFFER_SPEECH_STOPPED = "input_audio_buffer.speech_stopped"
    INPUT_AUDIO_BUFFER_SPEECH_STARTED = "input_audio_buffer.speech_started"
    SESSION_CREATED = "session.created"


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
    GET_SESSION_CONFIG = "session.get_config"
    INPUT_AUDIO_BUFFER_APPEND = "input_audio_buffer.append"
    INPUT_AUDIO_BUFFER_COMMIT = "input_audio_buffer.commit"
    INPUT_AUDIO_BUFFER_CLEAR = "input_audio_buffer.clear"
    CONVERSATION_ITEM_CREATE = "conversation.item.create"
    CONVERSATION_ITEM_RETRIEVE = "conversation.item.retrieve"
    CONVERSATION_ITEM_TRUNCATE = "conversation.item.truncate"
    CONVERSATION_ITEM_DELETE = "conversation.item.delete"
    RESPONSE_CREATE = "response.create"
    RESPONSE_CANCEL = "response.cancel"


class ServerEventType(str, Enum):
    """Types of events received from the server."""

    ERROR = "error"
    SESSION_CREATED = "session.created"
    SESSION_UPDATED = "session.updated"
    SESSION_CONFIG = "session.config"
    CONVERSATION_CREATED = "conversation.created"
    CONVERSATION_ITEM_CREATED = "conversation.item.created"
    CONVERSATION_ITEM_RETRIEVED = "conversation.item.retrieved"
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
    RESPONSE_AUDIO_TRANSCRIPT_DELTA = "response.audio_transcript.delta"
    RESPONSE_AUDIO_TRANSCRIPT_DONE = "response.audio_transcript.done"
    RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA = "response.function_call_arguments.delta"
    RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE = "response.function_call_arguments.done"
    RATE_LIMITS_UPDATED = "rate_limits.updated"
    RESPONSE_OUTPUT_ITEM_ADDED = "response.output_item.added"
    RESPONSE_OUTPUT_ITEM_DONE = "response.output_item.done"
    RESPONSE_CONTENT_PART_DONE = "response.content_part.done"
    RESPONSE_CONTENT_PART_ADDED = "response.content_part.added"


class ClientEvent(BaseModel):
    """Base model for events sent to the server."""

    type: str


class ServerEvent(BaseModel):
    """Base model for events received from the server."""

    type: str


# Legacy OpenAI message models

class RealtimeBaseMessage(BaseModel):
    """Base model for Realtime API messages."""

    type: str


class RealtimeErrorMessage(RealtimeBaseMessage):
    """Error message from OpenAI Realtime API."""

    type: str = "error"
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class RealtimeTranscriptMessage(RealtimeBaseMessage):
    """Transcript message from OpenAI Realtime API."""

    type: str = "transcript"
    text: str
    final: bool = False
    created_at: Optional[int] = None


class RealtimeTurnMessage(RealtimeBaseMessage):
    """Turn message from OpenAI Realtime API."""

    type: str = "turn"
    action: str  # "start" or "end"
    created_at: Optional[int] = None


class RealtimeMessageContent(BaseModel):
    """Content of a message in OpenAI Realtime API."""

    type: str  # "text" or other content types
    text: Optional[str] = None


class RealtimeMessage(RealtimeBaseMessage):
    """Message model for OpenAI Realtime API."""

    type: str = "message"
    role: str
    content: Union[str, List[RealtimeMessageContent]]
    name: Optional[str] = None
    function_call: Optional[Dict[str, str]] = None
    created_at: Optional[int] = None


class RealtimeStreamMessage(RealtimeBaseMessage):
    """Stream message from OpenAI Realtime API."""

    type: str = "stream"
    content: str
    role: str = "assistant"
    end: bool = False
    created_at: Optional[int] = None


class RealtimeFunctionMessage(RealtimeBaseMessage):
    """Function message for OpenAI Realtime API."""

    type: str = "function"
    function: Dict[str, str]
    created_at: Optional[int] = None


class WebSocketErrorResponse(BaseModel):
    """Error response for WebSocket errors."""

    error: str
    message: str


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


class InputAudioBufferClearEvent(ClientEvent):
    """Event to clear the audio buffer."""

    type: str = "input_audio_buffer.clear"


class ConversationItemCreateEvent(ClientEvent):
    """Event to create a conversation item."""

    type: str = "conversation.item.create"
    item: ConversationItemParam


class ConversationItemRetrieveEvent(ClientEvent):
    """Event to retrieve a conversation item."""

    type: str = "conversation.item.retrieve"
    item_id: str


class ConversationItemTruncateEvent(ClientEvent):
    """Event to truncate a conversation item's content."""

    type: str = "conversation.item.truncate"
    item_id: str


class ConversationItemDeleteEvent(ClientEvent):
    """Event to delete a conversation item."""

    type: str = "conversation.item.delete"
    item_id: str


class ResponseCreateOptions(BaseModel):
    """Options for creating a response"""

    modalities: List[Literal["audio", "text"]] = ["text"]
    voice: Optional[str] = None
    instructions: Optional[str] = None
    output_audio_format: Optional[Literal["pcm16"]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Literal["auto", "none"]] = "auto"
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class ResponseCreateEvent(ClientEvent):
    """Event to create a model response."""

    type: str = "response.create"
    event_id: Optional[str] = None
    response: ResponseCreateOptions


class ResponseCancelEvent(ClientEvent):
    """Event to cancel an active model response."""

    type: str = "response.cancel"
    event_id: Optional[str] = None
    response_id: Optional[str] = None


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


class RateLimitsUpdatedEvent(ServerEvent):
    """Event indicating rate limits have been updated."""

    type: Literal["rate_limits.updated"] = "rate_limits.updated"
    event_id: str
    rate_limits: List[Dict[str, Any]] = Field(
        ..., description="List of rate limit updates"
    )


class ResponseOutputItemAddedEvent(ServerEvent):
    """Event indicating a new output item has been added to the response."""

    type: str = "response.output_item.added"
    item: Dict[str, Any]


class ResponseContentPartDoneEvent(ServerEvent):
    """Event sent when a response content part is completed"""

    type: str = "response.content_part.done"
    event_id: str
    response_id: str
    item_id: str
    output_index: int
    content_index: int
    part_id: Optional[str] = None
    status: Optional[str] = None
    part: Dict[str, Any]  # The completed content part


class ResponseContentPartAddedEvent(ServerEvent):
    """Event sent when a new content part is added to a response"""

    type: str = "response.content_part.added"
    response_id: str
    item_id: str
    output_index: int
    content_index: int
    part: Dict[str, Any]  # The added content part
