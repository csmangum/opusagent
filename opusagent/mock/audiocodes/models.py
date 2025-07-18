"""
Data models for the AudioCodes mock client.

This module defines the data structures used throughout the AudioCodes mock client
system, providing type safety and validation for session state, conversation data,
and message events.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, ValidationError


class SessionStatus(str, Enum):
    """Session status enumeration."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    INITIATING = "initiating"
    ACTIVE = "active"
    RESUMING = "resuming"
    ERROR = "error"
    ENDED = "ended"


class StreamStatus(str, Enum):
    """Stream status enumeration."""

    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    STOPPED = "stopped"


class MessageType(str, Enum):
    """WebSocket message types."""

    # Session messages
    SESSION_INITIATE = "session.initiate"
    SESSION_RESUME = "session.resume"
    SESSION_ACCEPTED = "session.accepted"
    SESSION_RESUMED = "session.resumed"
    SESSION_ERROR = "session.error"
    SESSION_END = "session.end"

    # Connection messages
    CONNECTION_VALIDATE = "connection.validate"
    CONNECTION_VALIDATED = "connection.validated"

    # Stream messages
    USER_STREAM_START = "userStream.start"
    USER_STREAM_STOP = "userStream.stop"
    USER_STREAM_CHUNK = "userStream.chunk"
    USER_STREAM_STARTED = "userStream.started"
    USER_STREAM_STOPPED = "userStream.stopped"

    # Speech/VAD messages
    USER_STREAM_SPEECH_STARTED = "userStream.speech.started"
    USER_STREAM_SPEECH_STOPPED = "userStream.speech.stopped"
    USER_STREAM_SPEECH_COMMITTED = "userStream.speech.committed"
    USER_STREAM_SPEECH_HYPOTHESIS = "userStream.speech.hypothesis"

    # Play stream messages
    PLAY_STREAM_START = "playStream.start"
    PLAY_STREAM_CHUNK = "playStream.chunk"
    PLAY_STREAM_STOP = "playStream.stop"

    # Activity messages
    ACTIVITIES = "activities"


class SessionConfig(BaseModel):
    """Configuration for AudioCodes session."""

    bridge_url: str = Field(description="WebSocket URL for bridge server")
    bot_name: str = Field(default="TestBot", description="Name of the bot")
    caller: str = Field(default="+15551234567", description="Caller phone number")
    media_format: str = Field(default="raw/lpcm16", description="Audio media format")
    supported_media_formats: List[str] = Field(
        default_factory=lambda: ["raw/lpcm16"],
        description="List of supported media formats",
    )
    expect_audio_messages: bool = Field(
        default=True, description="Expect audio messages"
    )
    
    # VAD configuration
    enable_vad: bool = Field(default=True, description="Enable VAD processing")
    vad_threshold: float = Field(default=0.5, description="VAD speech detection threshold")
    vad_silence_threshold: float = Field(default=0.3, description="VAD silence detection threshold")
    vad_min_speech_duration_ms: int = Field(default=500, description="Minimum speech duration")
    vad_min_silence_duration_ms: int = Field(default=300, description="Minimum silence duration")
    enable_speech_hypothesis: bool = Field(default=False, description="Enable speech hypothesis simulation")

    @field_validator("bridge_url")
    def validate_bridge_url(cls, v):
        if not v.startswith(("ws://", "wss://")):
            raise ValueError("Bridge URL must start with ws:// or wss://")
        return v
    
    @field_validator("vad_threshold", "vad_silence_threshold")
    def validate_vad_thresholds(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("VAD thresholds must be between 0.0 and 1.0")
        return v


class SessionState(BaseModel):
    """Current session state."""

    conversation_id: Optional[str] = Field(
        default=None, description="Current conversation ID"
    )
    status: SessionStatus = Field(
        default=SessionStatus.DISCONNECTED, description="Session status"
    )
    accepted: bool = Field(default=False, description="Session accepted flag")
    resumed: bool = Field(default=False, description="Session resumed flag")
    error: bool = Field(default=False, description="Session error flag")
    error_reason: Optional[str] = Field(default=None, description="Error reason if any")
    media_format: str = Field(default="raw/lpcm16", description="Current media format")
    connection_validated: bool = Field(
        default=False, description="Connection validated flag"
    )
    validation_pending: bool = Field(
        default=False, description="Validation pending flag"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.now, description="Session creation time"
    )
    last_activity: Optional[datetime] = Field(
        default=None, description="Last activity time"
    )

    class Config:
        validate_assignment = False


class StreamState(BaseModel):
    """Stream state information."""

    user_stream: StreamStatus = Field(
        default=StreamStatus.INACTIVE, description="User stream status"
    )
    play_stream: StreamStatus = Field(
        default=StreamStatus.INACTIVE, description="Play stream status"
    )
    current_stream_id: Optional[str] = Field(
        default=None, description="Current stream ID"
    )

    # Speech/VAD state
    speech_active: bool = Field(default=False, description="Speech active flag")
    speech_committed: bool = Field(default=False, description="Speech committed flag")
    current_hypothesis: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Current speech hypothesis"
    )


class AudioChunk(BaseModel):
    """Audio chunk data."""

    data: str = Field(description="Base64 encoded audio data")
    chunk_index: int = Field(description="Chunk index in sequence")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Chunk timestamp"
    )
    size_bytes: int = Field(description="Size of audio data in bytes")

    @field_validator("data")
    def validate_data(cls, v):
        if not v:
            raise ValueError("Audio data cannot be empty")
        return v


class MessageEvent(BaseModel):
    """WebSocket message event."""

    type: MessageType = Field(description="Message type")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Event timestamp"
    )
    data: Dict[str, Any] = Field(default_factory=dict, description="Message data")

    @field_validator("type")
    def validate_type(cls, v):
        if not isinstance(v, MessageType):
            try:
                return MessageType(v)
            except ValueError:
                raise ValidationError(f"Invalid message type: {v}")
        return v


class ConversationState(BaseModel):
    """Conversation state and history."""

    conversation_id: str = Field(description="Conversation ID")
    turn_count: int = Field(default=0, description="Number of conversation turns")
    turns: List[Dict[str, Any]] = Field(
        default_factory=list, description="Conversation turns"
    )

    # Audio collection
    greeting_chunks: List[str] = Field(
        default_factory=list, description="Greeting audio chunks"
    )
    response_chunks: List[str] = Field(
        default_factory=list, description="Response audio chunks"
    )
    collecting_greeting: bool = Field(
        default=False, description="Currently collecting greeting"
    )
    collecting_response: bool = Field(
        default=False, description="Currently collecting response"
    )

    # Activities
    activities_received: List[Dict[str, Any]] = Field(
        default_factory=list, description="Received activities"
    )
    last_activity: Optional[Dict[str, Any]] = Field(
        default=None, description="Last received activity"
    )

    # Timestamps
    started_at: datetime = Field(
        default_factory=datetime.now, description="Conversation start time"
    )
    last_turn_at: Optional[datetime] = Field(default=None, description="Last turn time")


class ConversationResult(BaseModel):
    """Result of a multi-turn conversation."""

    total_turns: int = Field(description="Total number of turns")
    completed_turns: int = Field(default=0, description="Number of completed turns")
    greeting_received: bool = Field(
        default=False, description="Initial greeting received"
    )
    greeting_chunks: int = Field(default=0, description="Number of greeting chunks")
    success: bool = Field(default=False, description="Overall success flag")
    error: Optional[str] = Field(default=None, description="Error message if any")
    turns: List[Dict[str, Any]] = Field(
        default_factory=list, description="Turn results"
    )

    # Timing
    start_time: datetime = Field(
        default_factory=datetime.now, description="Conversation start time"
    )
    end_time: Optional[datetime] = Field(
        default=None, description="Conversation end time"
    )

    @property
    def duration(self) -> Optional[float]:
        """Get conversation duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_turns == 0:
            return 0.0
        return (self.completed_turns / self.total_turns) * 100.0
