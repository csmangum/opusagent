from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, RootModel


class InputAudioTranscription(BaseModel):
    model: str = "whisper-1"


class TurnDetection(BaseModel):
    type: Literal["server_vad", "none"] = "server_vad"
    threshold: float = 0.5
    prefix_padding_ms: int = 300
    silence_duration_ms: int = 200
    create_response: bool = True


class SessionConfig(BaseModel):
    """Configuration for the OpenAI Realtime API session"""
    modalities: List[Literal["audio", "text"]] = ["audio", "text"]
    instructions: str = ""
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = "alloy"
    input_audio_format: Literal["pcm16"] = "pcm16"
    output_audio_format: Literal["pcm16"] = "pcm16"
    input_audio_transcription: Optional[InputAudioTranscription] = None
    turn_detection: Optional[TurnDetection] = None
    tools: List[Dict[str, Any]] = Field(default_factory=list)


class SessionUpdateEvent(BaseModel):
    """Event to update the session configuration"""
    type: Literal["session.update"] = "session.update"
    session: SessionConfig


class AudioBufferAppendEvent(BaseModel):
    """Event to append audio data to the input buffer"""
    type: Literal["input_audio_buffer.append"] = "input_audio_buffer.append"
    audio: str  # Base64 encoded audio data


class AudioBufferCommitEvent(BaseModel):
    """Event to commit the audio buffer to the conversation"""
    type: Literal["input_audio_buffer.commit"] = "input_audio_buffer.commit"


class AudioBufferClearEvent(BaseModel):
    """Event to clear the audio buffer"""
    type: Literal["input_audio_buffer.clear"] = "input_audio_buffer.clear"


class InputTextContent(BaseModel):
    """Text content for a message"""
    type: Literal["input_text"] = "input_text"
    text: str


class InputAudioContent(BaseModel):
    """Audio content for a message"""
    type: Literal["input_audio"] = "input_audio"
    audio: str  # Base64 encoded audio data


# In Pydantic v2, we use RootModel instead of __root__
class ConversationItemContent(RootModel):
    """Content for a conversation item"""
    root: Union[InputTextContent, InputAudioContent]


class ConversationItem(BaseModel):
    """A message in the conversation"""
    type: Literal["message"] = "message"
    role: Literal["user", "assistant"] = "user"
    content: List[Union[InputTextContent, InputAudioContent]]


class ConversationItemCreateEvent(BaseModel):
    """Event to create a new conversation item"""
    type: Literal["conversation.item.create"] = "conversation.item.create"
    item: ConversationItem


class ConversationItemTruncateEvent(BaseModel):
    """Event to truncate a conversation item"""
    type: Literal["conversation.item.truncate"] = "conversation.item.truncate"
    id: str


class ConversationItemDeleteEvent(BaseModel):
    """Event to delete a conversation item"""
    type: Literal["conversation.item.delete"] = "conversation.item.delete"
    id: str


class ResponseCreateOptions(BaseModel):
    """Options for creating a response"""
    modalities: List[Literal["audio", "text"]] = ["text"]
    voice: Optional[str] = None
    instructions: Optional[str] = None
    output_audio_format: Optional[Literal["pcm16"]] = None
    commit: bool = True
    cancel_previous: bool = True
    conversation: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ResponseCreateEvent(BaseModel):
    """Event to create a new response"""
    type: Literal["response.create"] = "response.create"
    response: ResponseCreateOptions


class ResponseCancelEvent(BaseModel):
    """Event to cancel an in-progress response"""
    type: Literal["response.cancel"] = "response.cancel"
    id: Optional[str] = None


# Server events

class SessionCreatedEvent(BaseModel):
    """Event sent when a session is created"""
    type: Literal["session.created"] = "session.created"
    event_id: str
    session: Dict[str, Any]  # Full session details


class SessionUpdatedEvent(BaseModel):
    """Event sent when a session is updated"""
    type: Literal["session.updated"] = "session.updated"
    event_id: str
    session: Dict[str, Any]  # Updated session details


class ConversationCreatedEvent(BaseModel):
    """Event sent when a conversation is created"""
    type: Literal["conversation.created"] = "conversation.created"
    event_id: str
    conversation: Dict[str, Any]  # Conversation details


class InputAudioBufferCommittedEvent(BaseModel):
    """Event sent when the input audio buffer is committed"""
    type: Literal["input_audio_buffer.committed"] = "input_audio_buffer.committed"
    event_id: str


class InputAudioBufferClearedEvent(BaseModel):
    """Event sent when the input audio buffer is cleared"""
    type: Literal["input_audio_buffer.cleared"] = "input_audio_buffer.cleared"
    event_id: str


class InputAudioBufferSpeechStartedEvent(BaseModel):
    """Event sent when speech is detected in the input audio buffer"""
    type: Literal["input_audio_buffer.speech_started"] = "input_audio_buffer.speech_started"
    event_id: str


class InputAudioBufferSpeechStoppedEvent(BaseModel):
    """Event sent when speech stops in the input audio buffer"""
    type: Literal["input_audio_buffer.speech_stopped"] = "input_audio_buffer.speech_stopped"
    event_id: str


class ConversationItemCreatedEvent(BaseModel):
    """Event sent when a conversation item is created"""
    type: Literal["conversation.item.created"] = "conversation.item.created"
    event_id: str
    item: Dict[str, Any]  # Item details


class ConversationItemAudioTranscriptionCompletedEvent(BaseModel):
    """Event sent when audio transcription is completed"""
    type: Literal["conversation.item.audio_transcription.completed"] = "conversation.item.audio_transcription.completed"
    event_id: str
    id: str
    transcript: str


class ConversationItemAudioTranscriptionFailedEvent(BaseModel):
    """Event sent when audio transcription fails"""
    type: Literal["conversation.item.audio_transcription.failed"] = "conversation.item.audio_transcription.failed"
    event_id: str
    id: str
    error: Dict[str, Any]


class ResponseCreatedEvent(BaseModel):
    """Event sent when a response is created"""
    type: Literal["response.created"] = "response.created"
    event_id: str
    response: Dict[str, Any]  # Response details


class ResponseDoneEvent(BaseModel):
    """Event sent when a response is completed"""
    type: Literal["response.done"] = "response.done"
    event_id: str
    response: Dict[str, Any]  # Response details with usage


class ResponseTextDeltaEvent(BaseModel):
    """Event sent for each text delta in a response"""
    type: Literal["response.text.delta"] = "response.text.delta"
    event_id: str
    delta: str  # Text delta


class ResponseAudioTranscriptDeltaEvent(BaseModel):
    """Event sent for each audio transcript delta in a response"""
    type: Literal["response.audio_transcript.delta"] = "response.audio_transcript.delta"
    event_id: str
    delta: str  # Text delta


class ResponseAudioDeltaEvent(BaseModel):
    """Event sent for each audio delta in a response"""
    type: Literal["response.audio.delta"] = "response.audio.delta"
    event_id: str
    delta: str  # Base64 encoded audio data


# Union type for all client events
ClientEvent = Union[
    SessionUpdateEvent,
    AudioBufferAppendEvent,
    AudioBufferCommitEvent,
    AudioBufferClearEvent,
    ConversationItemCreateEvent,
    ConversationItemTruncateEvent,
    ConversationItemDeleteEvent,
    ResponseCreateEvent,
    ResponseCancelEvent
]

# Union type for all server events
ServerEvent = Union[
    SessionCreatedEvent,
    SessionUpdatedEvent,
    ConversationCreatedEvent,
    InputAudioBufferCommittedEvent,
    InputAudioBufferClearedEvent,
    InputAudioBufferSpeechStartedEvent,
    InputAudioBufferSpeechStoppedEvent,
    ConversationItemCreatedEvent,
    ConversationItemAudioTranscriptionCompletedEvent,
    ConversationItemAudioTranscriptionFailedEvent,
    ResponseCreatedEvent,
    ResponseDoneEvent,
    ResponseTextDeltaEvent,
    ResponseAudioTranscriptDeltaEvent,
    ResponseAudioDeltaEvent
] 