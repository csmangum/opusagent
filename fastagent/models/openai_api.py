"""
Pydantic models for OpenAI Realtime API message structures.

This module provides type-safe models for the messages exchanged with the OpenAI Realtime API,
including both incoming and outgoing message formats.

The OpenAI Realtime API enables real-time audio and text communication via WebSockets.
It supports various features including:
- Streaming text and audio responses
- Voice input and output with speech-to-text and text-to-speech
- Server-side Voice Activity Detection (VAD)
- Function/tool calling capabilities
- Audio transcription

Messages are exchanged as events with specific types, parameters, and structures defined
in this module as Pydantic models.
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
    """Configuration for a Realtime API Session.

    This object defines the configuration for a new or updated session, including
    modalities, model selection, audio formats, VAD settings, and tools.
    """

    modalities: List[str] = Field(default=["text"])  # e.g. ["text", "audio"]
    model: Optional[str] = None
    instructions: Optional[str] = None
    voice: Optional[str] = None
    input_audio_format: Optional[str] = None  # "pcm16" or "g711"
    output_audio_format: Optional[str] = None  # "pcm16" or "g711"
    turn_detection: Optional[Dict[str, Any]] = None  # {"type": "server_vad"}
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Literal["auto", "none"]] = None
    temperature: Optional[float] = None
    max_response_output_tokens: Optional[Union[int, str]] = None
    input_audio_transcription: Optional[Dict[str, Any]] = None
    input_audio_noise_reduction: Optional[Dict[str, Any]] = None


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
    content: List[ConversationItemContentParam] = Field(
        default_factory=list
    )  # Make content required and default to empty list
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
    TRANSCRIPTION_SESSION_UPDATE = "transcription_session.update"


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
    CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED = (
        "conversation.item.input_audio_transcription.completed"
    )
    CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_DELTA = (
        "conversation.item.input_audio_transcription.delta"
    )
    CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_FAILED = (
        "conversation.item.input_audio_transcription.failed"
    )
    TRANSCRIPTION_SESSION_UPDATED = "transcription_session.updated"


class ClientEvent(BaseModel):
    """Base model for events sent to the server."""

    type: str
    event_id: Optional[str] = None


class ServerEvent(BaseModel):
    """Base model for events received from the server."""

    type: str
    event_id: Optional[str] = None


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
    """Event to update session configuration.

    Used to update the session's default configuration. The client may send this event
    at any time to update any field, except for voice. Once a session has been initialized
    with a particular model, it can't be changed to another model using session.update.

    The server will respond with a session.updated event.
    """

    type: str = "session.update"
    session: SessionConfig


class InputAudioBufferAppendEvent(ClientEvent):
    """Event to append audio to the input buffer.

    Used to send audio bytes to the input audio buffer. The audio buffer is temporary
    storage that can be committed later. In Server VAD mode, the buffer is used to detect
    speech and the server will decide when to commit.

    The server does not send a confirmation response to this event.
    """

    type: str = "input_audio_buffer.append"
    audio: str  # Base64 encoded audio


class InputAudioBufferCommitEvent(ClientEvent):
    """Event to commit the audio buffer to the conversation.

    Used to commit the user input audio buffer, creating a new user message item
    in the conversation. This event will produce an error if the buffer is empty.
    In Server VAD mode, the client doesn't need to send this as the server commits
    automatically.

    The server will respond with an input_audio_buffer.committed event.
    """

    type: str = "input_audio_buffer.commit"


class InputAudioBufferClearEvent(ClientEvent):
    """Event to clear the audio buffer.

    Used to clear all audio bytes in the buffer.

    The server will respond with an input_audio_buffer.cleared event.
    """

    type: str = "input_audio_buffer.clear"


class ConversationItemCreateEvent(ClientEvent):
    """Event to create a conversation item.

    Used to add a new Item to the Conversation's context, including messages,
    function calls, and function call responses.

    The server will respond with a conversation.item.created event if successful.
    """

    type: str = "conversation.item.create"
    item: ConversationItemParam
    previous_item_id: Optional[str] = None


class ConversationItemRetrieveEvent(ClientEvent):
    """Event to retrieve a conversation item.

    Used to get the server's representation of a specific item in the conversation history.
    Useful for inspecting user audio after noise cancellation and VAD.

    The server will respond with a conversation.item.retrieved event.
    """

    type: str = "conversation.item.retrieve"
    item_id: str


class ConversationItemTruncateEvent(ClientEvent):
    """Event to truncate a conversation item's content.

    Used to truncate a previous assistant message's audio. Useful when the user
    interrupts to truncate audio that has been sent but not yet played.

    The server will respond with a conversation.item.truncated event.
    """

    type: str = "conversation.item.truncate"
    item_id: str
    content_index: int
    audio_end_ms: int


class ConversationItemDeleteEvent(ClientEvent):
    """Event to delete a conversation item.

    Used to remove any item from the conversation history.

    The server will respond with a conversation.item.deleted event.
    """

    type: str = "conversation.item.delete"
    item_id: str


class ResponseCreateOptions(BaseModel):
    """Options for creating a response

    Configures various aspects of model inference, including modalities,
    voice settings, tools, and generation parameters.
    """

    modalities: List[Literal["audio", "text"]] = Field(default_factory=lambda: ["text"])
    voice: Optional[str] = None
    instructions: Optional[str] = None
    output_audio_format: Optional[Literal["pcm16"]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Literal["auto", "none"]] = "auto"
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class ResponseCreateEvent(ClientEvent):
    """Event to create a model response.

    Instructs the server to create a Response by triggering model inference.
    When in Server VAD mode, the server creates Responses automatically.

    The server will respond with a response.created event, followed by various
    delta events, and finally a response.done event.
    """

    type: str = "response.create"
    response: ResponseCreateOptions


class ResponseCancelEvent(ClientEvent):
    """Event to cancel an active model response.

    Used to stop an in-progress response.

    The server will respond with a response.cancelled event.
    """

    type: str = "response.cancel"
    response_id: Optional[str] = None


class TranscriptionSessionUpdateEvent(ClientEvent):
    """Event to update a transcription session.

    Used to update settings for the transcription session.

    The server will respond with a transcription_session.updated event.
    """

    type: str = "transcription_session.update"
    session: Dict[str, Any]


# Specific server event implementations


class ErrorEvent(ServerEvent):
    """Error message from OpenAI Realtime API.

    Returned when an error occurs, which could be client or server related.
    Most errors are recoverable and the session will stay open.
    """

    type: str = "error"
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class SessionCreatedEvent(ServerEvent):
    """Event indicating a session was created.

    Emitted automatically when a new connection is established as the first server event.
    Contains the default Session configuration.
    """

    type: str = "session.created"
    session: Dict[str, Any]


class SessionUpdatedEvent(ServerEvent):
    """Event indicating session configuration was updated.

    Returned when a session is updated with a session.update event.
    """

    type: str = "session.updated"
    session: Dict[str, Any]


class ConversationCreatedEvent(ServerEvent):
    """Event indicating a conversation was created.

    Emitted right after session creation.
    """

    type: str = "conversation.created"
    conversation: Dict[str, Any]


class ConversationItemCreatedEvent(ServerEvent):
    """Event indicating a conversation item was created.

    Returned when a new item is added to the conversation, either from
    a response, input audio buffer commit, or conversation.item.create event.
    """

    type: str = "conversation.item.created"
    item: Dict[str, Any]
    previous_item_id: Optional[str] = None


class ConversationItemRetrievedEvent(ServerEvent):
    """Event containing a retrieved conversation item.

    Returned in response to a conversation.item.retrieve event.
    """

    type: str = "conversation.item.retrieved"
    item: Dict[str, Any]


class ConversationItemTruncatedEvent(ServerEvent):
    """Event indicating a conversation item was truncated.

    Returned when an assistant audio message is truncated by the client.
    """

    type: str = "conversation.item.truncated"
    item_id: str
    content_index: int
    audio_end_ms: int


class ConversationItemDeletedEvent(ServerEvent):
    """Event indicating a conversation item was deleted.

    Returned in response to a conversation.item.delete event.
    """

    type: str = "conversation.item.deleted"
    item_id: str


class InputAudioBufferCommittedEvent(ServerEvent):
    """Event indicating the input audio buffer was committed.

    Returned when an input audio buffer is committed, either by the client
    or automatically in server VAD mode.
    """

    type: str = "input_audio_buffer.committed"
    item_id: str
    previous_item_id: Optional[str] = None


class InputAudioBufferClearedEvent(ServerEvent):
    """Event indicating the input audio buffer was cleared.

    Returned in response to an input_audio_buffer.clear event.
    """

    type: str = "input_audio_buffer.cleared"


class InputAudioBufferSpeechStartedEvent(ServerEvent):
    """Event indicating speech was detected in the audio buffer.

    Sent in server_vad mode to indicate that speech has been detected.
    """

    type: str = "input_audio_buffer.speech_started"
    audio_start_ms: int
    item_id: str


class InputAudioBufferSpeechStoppedEvent(ServerEvent):
    """Event indicating speech has stopped in the audio buffer.

    Returned in server_vad mode when the server detects the end of speech.
    """

    type: str = "input_audio_buffer.speech_stopped"
    audio_end_ms: int
    item_id: str


class ResponseCreatedEvent(ServerEvent):
    """Event indicating a response was created.

    The first event of response creation, where the response is in an initial state.
    """

    type: str = "response.created"
    response: Dict[str, Any]


class ResponseDoneEvent(ServerEvent):
    """Event indicating the model response is complete.

    Always emitted when a Response is done streaming, regardless of final state.
    """

    type: str = "response.done"
    response: Dict[str, Any]


class ResponseCancelledEvent(ServerEvent):
    """Event indicating a response was cancelled.

    Returned in response to a response.cancel event.
    """

    type: str = "response.cancelled"
    response_id: str


class ResponseTextDeltaEvent(ServerEvent):
    """Event containing a text delta from the model."""

    type: str = "response.text.delta"
    response_id: str
    item_id: str
    output_index: int
    content_index: int
    delta: str


class ResponseTextDoneEvent(ServerEvent):
    """Event indicating text generation is complete.

    Returned when text generation for a content part is finished.
    """

    type: str = "response.text.done"
    response_id: str
    item_id: str
    output_index: int
    content_index: int
    text: str


class ResponseAudioDeltaEvent(ServerEvent):
    """Event containing an audio delta from the model."""

    type: str = "response.audio.delta"
    response_id: str
    item_id: str
    output_index: int
    content_index: int
    delta: str  # Base64 encoded audio chunk


class ResponseAudioDoneEvent(ServerEvent):
    """Event indicating audio generation is complete.

    Returned when audio generation for a content part is finished.
    """

    type: str = "response.audio.done"
    response_id: str
    item_id: str
    output_index: int
    content_index: int


class ResponseAudioTranscriptDeltaEvent(ServerEvent):
    """Event containing a transcript delta for generated audio."""

    type: str = "response.audio_transcript.delta"
    response_id: str
    item_id: str
    output_index: int
    content_index: int
    delta: str


class ResponseAudioTranscriptDoneEvent(ServerEvent):
    """Event indicating audio transcript generation is complete."""

    type: str = "response.audio_transcript.done"
    response_id: str
    item_id: str
    output_index: int
    content_index: int
    transcript: str


class ResponseFunctionCallArgumentsDeltaEvent(ServerEvent):
    """Event containing a function call arguments delta."""

    type: str = "response.function_call_arguments.delta"
    response_id: str
    item_id: str
    output_index: int
    call_id: str
    delta: str


class ResponseFunctionCallArgumentsDoneEvent(ServerEvent):
    """Event indicating function call arguments generation is complete."""

    type: str = "response.function_call_arguments.done"
    response_id: str
    item_id: str
    output_index: int
    call_id: str
    arguments: str


class RateLimitsUpdatedEvent(ServerEvent):
    """Event indicating rate limits have been updated.

    Emitted at the beginning of a Response to indicate the updated rate limits.
    """

    type: Literal["rate_limits.updated"] = "rate_limits.updated"
    rate_limits: List[Dict[str, Any]] = Field(
        ..., description="List of rate limit updates"
    )


class ResponseOutputItemAddedEvent(ServerEvent):
    """Event indicating a new output item has been added to the response.

    Returned when a new Item is created during Response generation.
    """

    type: str = "response.output_item.added"
    response_id: str
    output_index: int
    item: Dict[str, Any]


class ResponseOutputItemDoneEvent(ServerEvent):
    """Event indicating an output item is complete.

    Returned when an Item is done streaming.
    """

    type: str = "response.output_item.done"
    response_id: str
    output_index: int
    item: Dict[str, Any]


class ResponseContentPartDoneEvent(ServerEvent):
    """Event sent when a response content part is completed

    Returned when a content part is done streaming.
    """

    type: str = "response.content_part.done"
    response_id: str
    item_id: str
    output_index: int
    content_index: int
    part_id: Optional[str] = None
    status: Optional[str] = None
    part: Dict[str, Any]  # The completed content part


class ResponseContentPartAddedEvent(ServerEvent):
    """Event sent when a new content part is added to a response

    Returned when a new content part is added to an assistant message item.
    """

    type: str = "response.content_part.added"
    response_id: str
    item_id: str
    output_index: int
    content_index: int
    part: Dict[str, Any]  # The added content part


class ConversationItemInputAudioTranscriptionCompletedEvent(ServerEvent):
    """Event indicating input audio transcription is complete.

    This is the output of audio transcription for user audio, which runs
    asynchronously with Response creation.
    """

    type: str = "conversation.item.input_audio_transcription.completed"
    item_id: str
    content_index: int
    transcript: str
    logprobs: Optional[List[Dict[str, Any]]] = None


class ConversationItemInputAudioTranscriptionDeltaEvent(ServerEvent):
    """Event containing a delta update for input audio transcription."""

    type: str = "conversation.item.input_audio_transcription.delta"
    item_id: str
    content_index: int
    delta: str
    logprobs: Optional[List[Dict[str, Any]]] = None


class ConversationItemInputAudioTranscriptionFailedEvent(ServerEvent):
    """Event indicating input audio transcription failed."""

    type: str = "conversation.item.input_audio_transcription.failed"
    item_id: str
    content_index: int
    error: Dict[str, Any]


class TranscriptionSessionUpdatedEvent(ServerEvent):
    """Event indicating a transcription session was updated."""

    type: str = "transcription_session.updated"
    session: Dict[str, Any]


# Union type for all possible incoming messages (client-to-server)
IncomingMessage = Union[
    SessionUpdateEvent,
    InputAudioBufferAppendEvent,
    InputAudioBufferCommitEvent,
    InputAudioBufferClearEvent,
    ConversationItemCreateEvent,
    ConversationItemRetrieveEvent,
    ConversationItemTruncateEvent,
    ConversationItemDeleteEvent,
    ResponseCreateEvent,
    ResponseCancelEvent,
    TranscriptionSessionUpdateEvent,
]

# Union type for all possible outgoing messages (server-to-client)
OutgoingMessage = Union[
    ErrorEvent,
    SessionCreatedEvent,
    SessionUpdatedEvent,
    ConversationCreatedEvent,
    ConversationItemCreatedEvent,
    ConversationItemRetrievedEvent,
    ConversationItemTruncatedEvent,
    ConversationItemDeletedEvent,
    InputAudioBufferCommittedEvent,
    InputAudioBufferClearedEvent,
    InputAudioBufferSpeechStartedEvent,
    InputAudioBufferSpeechStoppedEvent,
    ResponseCreatedEvent,
    ResponseDoneEvent,
    ResponseCancelledEvent,
    ResponseTextDeltaEvent,
    ResponseTextDoneEvent,
    ResponseAudioDeltaEvent,
    ResponseAudioDoneEvent,
    ResponseAudioTranscriptDeltaEvent,
    ResponseAudioTranscriptDoneEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    RateLimitsUpdatedEvent,
    ResponseOutputItemAddedEvent,
    ResponseOutputItemDoneEvent,
    ResponseContentPartDoneEvent,
    ResponseContentPartAddedEvent,
    ConversationItemInputAudioTranscriptionCompletedEvent,
    ConversationItemInputAudioTranscriptionDeltaEvent,
    ConversationItemInputAudioTranscriptionFailedEvent,
    TranscriptionSessionUpdatedEvent,
]
