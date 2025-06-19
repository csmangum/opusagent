"""
Pydantic models for AudioCodes VoiceAI Connect Enterprise message schemas.

This module defines structured data models for all incoming and outgoing messages
in the AudioCodes Bot API WebSocket protocol, providing type validation and documentation.

The AudioCodes Bot API in WebSocket mode allows a voice bot to communicate with the
AudioCodes VoiceAI Connect Enterprise platform. A typical use case is implementing
LLM AI agents for voice interactions.

The communication flow involves:
1. VoiceAI Connect initiates a WebSocket connection to the bot
2. Messages are exchanged as JSON (with media encoded in base64)
3. The connection remains active for the entire conversation session
4. Authentication is handled via HTTP Authorization header with a shared token

Note: WebSocket mode is supported only by VoiceAI Connect Enterprise v3.24 or later.
"""

import base64
import enum
import re
from typing import Dict, List, Literal, Optional, Pattern, Union

from pydantic import BaseModel, Field, field_validator


class TelephonyEventType(str, enum.Enum):
    """Enumeration of all supported Telephony (AudioCodes) message types.

    This enum provides type-safe access to all event type strings used in
    the AudioCodes VoiceAI Connect Enterprise WebSocket protocol.
    """

    # Session events
    SESSION_INITIATE = "session.initiate"
    SESSION_RESUME = "session.resume"
    SESSION_END = "session.end"
    SESSION_ACCEPTED = "session.accepted"
    SESSION_ERROR = "session.error"

    # User stream events
    USER_STREAM_START = "userStream.start"
    USER_STREAM_CHUNK = "userStream.chunk"
    USER_STREAM_STOP = "userStream.stop"
    USER_STREAM_STARTED = "userStream.started"
    USER_STREAM_STOPPED = "userStream.stopped"
    USER_STREAM_SPEECH_HYPOTHESIS = "userStream.speech.hypothesis"
    USER_STREAM_SPEECH_RECOGNITION = "userStream.speech.recognition"

    # Play stream events
    PLAY_STREAM_START = "playStream.start"
    PLAY_STREAM_CHUNK = "playStream.chunk"
    PLAY_STREAM_STOP = "playStream.stop"

    # Activity and connection events
    ACTIVITIES = "activities"
    CONNECTION_VALIDATE = "connection.validate"
    CONNECTION_VALIDATED = "connection.validated"


# Regular expression patterns for validation
PHONE_PATTERN: Pattern = re.compile(r"^\+?[0-9\- ]{6,15}$")
UUID_PATTERN: Pattern = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
SUPPORTED_MEDIA_FORMATS = ["raw/lpcm16", "audio/wav", "audio/mp3", "audio/alaw"]


# Base Models
class BaseMessage(BaseModel):
    """Base model for all WebSocket messages.

    All messages exchanged between VoiceAI Connect Enterprise and the bot
    must include at least the 'type' field, and messages from VoiceAI Connect
    to the bot include a 'conversationId' field.
    """

    type: str = Field(..., description="Message type identifier")
    conversationId: Optional[str] = Field(
        None, description="Unique conversation identifier"
    )

    @field_validator("conversationId")
    def validate_conversation_id(cls, v):
        """Validate that conversation ID is a UUID if provided."""
        if v is not None and not UUID_PATTERN.match(v):
            # Not enforcing UUID format as the service might use different formats
            # Just log a warning
            import logging

            from opusagent.config.constants import LOGGER_NAME

            logger = logging.getLogger(LOGGER_NAME)
            logger.warning(f"Conversation ID does not match UUID pattern: {v}")
        return v


# Session Messages
class SessionInitiateMessage(BaseMessage):
    """Model for session.initiate message from AudioCodes.

    Sent upon establishment of the session. The bot should respond to this
    message with a session.accepted message or a session.error message if
    declining the conversation.

    Example:
    {
      "conversationId": "4a5b4b9d-dab7-42d0-a977-6740c9349588",
      "type": "session.initiate",
      "botName": "my_bot_name",
      "caller": "+1234567890",
      "expectAudioMessages": true,
      "supportedMediaFormats": [
        "raw/lpcm16"
      ]
    }
    """

    type: Literal[TelephonyEventType.SESSION_INITIATE]
    expectAudioMessages: bool = Field(
        ...,
        description="Whether the bot should send audio (set according to directTTS bot parameter)",
    )
    botName: str = Field(..., description="Configured name of the bot")
    caller: str = Field(..., description="Phone number of the caller")
    supportedMediaFormats: List[str] = Field(
        ..., description="Supported audio formats (in order of preference)"
    )

    @field_validator("botName")
    def validate_bot_name(cls, v):
        """Validate that bot name is not empty."""
        if not v.strip():
            raise ValueError("Bot name cannot be empty")
        return v

    @field_validator("caller")
    def validate_caller(cls, v):
        """Validate that caller is a phone number if it looks like one."""
        if v.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            if not PHONE_PATTERN.match(v):
                import logging

                from opusagent.config.constants import LOGGER_NAME

                logger = logging.getLogger(LOGGER_NAME)
                logger.warning(f"Caller doesn't match expected phone pattern: {v}")
        return v

    @field_validator("supportedMediaFormats")
    def validate_media_formats(cls, v):
        """Validate that at least one supported media format is included."""
        if not v or not any(fmt in SUPPORTED_MEDIA_FORMATS for fmt in v):
            raise ValueError(
                f"At least one supported media format required: {SUPPORTED_MEDIA_FORMATS}"
            )
        return v


class SessionResumeMessage(BaseMessage):
    """Model for session.resume message from AudioCodes.

    Sent when the WebSocket connection is lost and VoiceAI Connect attempts to reconnect.
    The bot should respond with a session.accepted message, or session.error to decline.

    Example:
    {
      "conversationId": "4a5b4b9d-dab7-42d0-a977-6740c9349588",
      "type": "session.resume"
    }
    """

    type: Literal[TelephonyEventType.SESSION_RESUME]


class SessionEndMessage(BaseMessage):
    """Model for session.end message from AudioCodes.

    Sent by VoiceAI Connect to indicate the end of the conversation.
    This is the final message in a conversation session.

    Example:
    {
      "conversationId": "4a5b4b9d-dab7-42d0-a977-6740c9349588",
      "type": "session.end",
      "reasonCode": "client-disconnected",
      "reason": "Client Side"
    }
    """

    type: Literal[TelephonyEventType.SESSION_END]
    reasonCode: str = Field(..., description="Code indicating reason for session end")
    reason: str = Field(..., description="Description of why session ended")


class SessionAcceptedResponse(BaseMessage):
    """Model for session.accepted response to AudioCodes.

    Sent in response to either session.initiate or session.resume messages
    to accept the conversation.

    Example:
    {
      "type": "session.accepted",
      "mediaFormat": "raw/lpcm16"
    }
    """

    type: Literal[TelephonyEventType.SESSION_ACCEPTED]
    mediaFormat: str = Field(
        ...,
        description="Selected audio format for the session (must be one of the formats specified in session.initiate)",
    )

    @field_validator("mediaFormat")
    def validate_media_format(cls, v):
        """Validate that media format is supported."""
        if v not in SUPPORTED_MEDIA_FORMATS:
            raise ValueError(f"Unsupported media format: {v}")
        return v


class SessionErrorResponse(BaseMessage):
    """Model for session.error response to AudioCodes.

    Sent by the bot to report a fatal error or decline a conversation.
    Upon receiving this message, VoiceAI Connect disconnects the call and
    closes the WebSocket connection.

    Example:
    {
      "type": "session.error",
      "reason": "Internal Server Error"
    }
    """

    type: Literal[TelephonyEventType.SESSION_ERROR]
    reason: str = Field(..., description="Reason for rejecting the session")


# Stream Messages
class UserStreamStartMessage(BaseMessage):
    """Model for userStream.start message from AudioCodes.

    Sent by VoiceAI Connect to indicate a request to start audio streaming to the bot.
    The bot should respond with a userStream.started message, after which
    VoiceAI Connect starts sending audio chunks.

    Example:
    {
      "conversationId": "4a5b4b9d-dab7-42d0-a977-6740c9349588",
      "type": "userStream.start"
    }
    """

    type: Literal[TelephonyEventType.USER_STREAM_START]


class UserStreamChunkMessage(BaseMessage):
    """Model for userStream.chunk message from AudioCodes.

    Sent by VoiceAI Connect to stream audio data to the bot.
    These messages are sent continuously after a userStream.start
    until userStream.stop is sent.

    Example:
    {
      "conversationId": "4a5b4b9d-dab7-42d0-a977-6740c9349588",
      "type": "userStream.chunk",
      "audioChunk": "Base64EncodedAudioData"
    }
    """

    type: Literal[TelephonyEventType.USER_STREAM_CHUNK]
    audioChunk: str = Field(..., description="Base64-encoded audio data")

    @field_validator("audioChunk")
    def validate_audio_chunk(cls, v):
        """Validate that audio chunk is valid base64."""
        try:
            # Check if it's a valid base64 string
            if v:
                base64.b64decode(v)
            else:
                raise ValueError("Audio chunk cannot be empty")
        except Exception:
            raise ValueError("Invalid base64 encoded audio data")
        return v


class UserStreamStopMessage(BaseMessage):
    """Model for userStream.stop message from AudioCodes.

    Sent by VoiceAI Connect to indicate the end of audio streaming.
    The bot should respond with a userStream.stopped message.

    Example:
    {
      "conversationId": "4a5b4b9d-dab7-42d0-a977-6740c9349588",
      "type": "userStream.stop"
    }
    """

    type: Literal[TelephonyEventType.USER_STREAM_STOP]


class UserStreamStartedResponse(BaseMessage):
    """Model for userStream.started response to AudioCodes.

    Sent in response to the userStream.start message to indicate that
    the bot is ready to receive audio chunks.

    Example:
    {
      "type": "userStream.started"
    }
    """

    type: Literal[TelephonyEventType.USER_STREAM_STARTED]


class UserStreamStoppedResponse(BaseMessage):
    """Model for userStream.stopped response to AudioCodes.

    Sent in response to the userStream.stop message to indicate that
    the bot will not accept any more audio chunks.

    Example:
    {
      "type": "userStream.stopped"
    }
    """

    type: Literal[TelephonyEventType.USER_STREAM_STOPPED]


class UserStreamHypothesisResponse(BaseMessage):
    """Model for userStream.speech.hypothesis response to AudioCodes.

    Sent by the bot to provide partial recognition results.
    Using this message is recommended as VoiceAI Connect relies on it for barge-in.

    Example:
    {
      "type": "userStream.speech.hypothesis",
      "alternatives": [
        {
          "text": "How are"
        }
      ]
    }
    """

    type: Literal[TelephonyEventType.USER_STREAM_SPEECH_HYPOTHESIS]
    alternatives: List[Dict[str, str]] = Field(
        ..., description="List of recognition hypotheses, each with a 'text' field"
    )

    @field_validator("alternatives")
    def validate_alternatives(cls, v):
        """Validate that alternatives contain text."""
        if not v:
            raise ValueError("At least one hypothesis required")
        for alt in v:
            if "text" not in alt:
                raise ValueError("Each hypothesis must contain 'text' field")
        return v


# Play Stream Messages
class PlayStreamStartMessage(BaseMessage):
    """Model for playStream.start message to AudioCodes.

    Sent by the bot to initiate a Play Stream to stream audio to the user.
    After sending this message, the bot should stream audio data using playStream.chunk
    and then send playStream.stop to end the stream.

    Only one Play Stream can be active at a time. Before starting a new stream,
    the bot must stop the current one with playStream.stop.

    Example:
    {
      "type": "playStream.start",
      "streamId": "1",
      "mediaFormat": "raw/lpcm16"
    }
    """

    type: Literal[TelephonyEventType.PLAY_STREAM_START]
    streamId: str = Field(
        ..., description="Unique identifier for the stream within the conversation"
    )
    mediaFormat: str = Field(
        ...,
        description="Audio format of the stream (must be one of the formats specified in session.initiate)",
    )

    @field_validator("mediaFormat")
    def validate_media_format(cls, v):
        """Validate that media format is supported."""
        if v not in SUPPORTED_MEDIA_FORMATS:
            raise ValueError(f"Unsupported media format: {v}")
        return v


class PlayStreamChunkMessage(BaseMessage):
    """Model for playStream.chunk message to AudioCodes.

    Sent by the bot to stream audio data to the user with a Play Stream.
    Audio chunks can only be sent when a Play Stream is active.
    To ensure smooth playback, audio data should be sent at a rate matching playback speed.

    Example:
    {
      "type": "playStream.chunk",
      "streamId": "1",
      "audioChunk": "Base64EncodedAudioData"
    }
    """

    type: Literal[TelephonyEventType.PLAY_STREAM_CHUNK]
    streamId: str = Field(
        ..., description="Stream identifier matching an active stream"
    )
    audioChunk: str = Field(..., description="Base64-encoded audio data")

    @field_validator("audioChunk")
    def validate_audio_chunk(cls, v):
        """Validate that audio chunk is valid base64."""
        try:
            # Check if it's a valid base64 string
            if v:
                base64.b64decode(v)
            else:
                raise ValueError("Audio chunk cannot be empty")
        except Exception:
            raise ValueError("Invalid base64 encoded audio data")
        return v


class PlayStreamStopMessage(BaseMessage):
    """Model for playStream.stop message to AudioCodes.

    Sent by the bot to stop a Play Stream.

    Example:
    {
      "type": "playStream.stop",
      "streamId": "1"
    }
    """

    type: Literal[TelephonyEventType.PLAY_STREAM_STOP]
    streamId: str = Field(..., description="Stream identifier to stop")


# Activity Messages
class ActivityEvent(BaseModel):
    """Model for activity event.

    Activities represent various events in the conversation, such as:
    - start: Call initiation
    - dtmf: User pressed DTMF digits
    - hangup: Request to disconnect the call

    According to AudioCodes documentation, activities may include additional fields
    like id, timestamp, language, and parameters for start events.
    """

    type: Literal["event"]
    name: str = Field(..., description="Event name (start, dtmf, hangup)")
    value: Optional[str] = Field(None, description="Event value, e.g., DTMF digit")
    # Additional fields from AudioCodes documentation
    id: Optional[str] = Field(None, description="Unique identifier for the activity")
    timestamp: Optional[str] = Field(None, description="ISO timestamp of the activity")
    language: Optional[str] = Field(None, description="Language code (e.g., 'en-US')")
    parameters: Optional[Dict[str, str]] = Field(
        None, description="Additional parameters (for start events)"
    )

    @field_validator("name")
    def validate_name(cls, v):
        """Validate that event name is a known type."""
        if v not in ["start", "dtmf", "hangup"]:
            import logging

            from opusagent.config.constants import LOGGER_NAME

            logger = logging.getLogger(LOGGER_NAME)
            logger.warning(f"Unknown event name: {v}")
        return v

    @field_validator("value")
    def validate_value(cls, v, values):
        """Validate that value is appropriate for the event type."""
        if values.data.get("name") == "dtmf" and v is not None:
            if not v in "0123456789*#ABCD":
                raise ValueError(f"Invalid DTMF value: {v}")
        return v

    @field_validator("timestamp")
    def validate_timestamp(cls, v):
        """Validate that timestamp is in ISO format if provided."""
        if v is not None:
            import re

            # Basic ISO timestamp validation
            iso_pattern = re.compile(
                r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z?$"
            )
            if not iso_pattern.match(v):
                import logging

                from opusagent.config.constants import LOGGER_NAME

                logger = logging.getLogger(LOGGER_NAME)
                logger.warning(f"Timestamp doesn't match ISO format: {v}")
        return v


class ActivitiesMessage(BaseMessage):
    """Model for activities message from AudioCodes.

    Activities messages are used for various events like call initiation,
    DTMF digit presses, or call hangup requests.

    Example for call initiation:
    {
      "conversationId": "4a5b4b9d-dab7-42d0-a977-6740c9349588",
      "type": "activities",
      "activities": [
        {
          "type": "event",
          "name": "start",
          "id": "582bbc43-0ef7-47e9-97b4-1e6141625b01",
          "timestamp": "2022-07-20T07:15:48.239Z",
          "language": "en-US",
          "parameters": {
            "locale": "en-US",
            "caller": "caller-id",
            "callee": "my_bot_name"
          }
        }
      ]
    }

    Example for DTMF:
    {
      "conversationId": "4a5b4b9d-dab7-42d0-a977-6740c9349588",
      "type": "activities",
      "activities": [
        {
          "type": "event",
          "name": "dtmf",
          "id": "582bbc43-0ef7-47e9-97b4-1e6141625b01",
          "timestamp": "2022-07-20T07:15:48.239Z",
          "language": "en-US",
          "value": "123"
        }
      ]
    }
    """

    type: Literal[TelephonyEventType.ACTIVITIES]
    activities: List[ActivityEvent] = Field(..., description="List of activity events")

    @field_validator("activities")
    def validate_activities(cls, v):
        """Validate that there is at least one activity."""
        if not v:
            raise ValueError("At least one activity required")
        return v


# Connection Messages
class ConnectionValidateMessage(BaseMessage):
    """Model for connection.validate message from AudioCodes.

    Used to verify connectivity between the bot and AudioCodes Live Hub platform
    during initial integration. This message is NOT part of the regular call flow.

    Example:
    {
      "type": "connection.validate"
    }
    """

    type: Literal[TelephonyEventType.CONNECTION_VALIDATE]


class ConnectionValidatedResponse(BaseMessage):
    """Model for connection.validated response to AudioCodes.

    Sent in response to connection.validate during connectivity verification.
    This message is NOT part of the regular call flow.

    Example:
    {
      "type": "connection.validated",
      "success": true
    }
    """

    type: Literal[TelephonyEventType.CONNECTION_VALIDATED]
    success: bool = Field(..., description="Whether validation was successful")


# Model for userStream.speech.recognition response to AudioCodes
class UserStreamRecognitionResponse(BaseMessage):
    """Model for userStream.speech.recognition response to AudioCodes.

    Sent by the bot to provide final recognition results.
    Recommended mainly for logging purposes.

    Note: The AudioCodes documentation shows confidence as a string (e.g., "0.95"),
    but this implementation expects a float for better type safety and validation.

    Example:
    {
      "type": "userStream.speech.recognition",
      "alternatives": [
        {
          "text": "How are you.",
          "confidence": 0.83
        }
      ]
    }
    """

    type: Literal[TelephonyEventType.USER_STREAM_SPEECH_RECOGNITION]
    alternatives: List[Dict[str, Union[str, float]]] = Field(
        ...,
        description="List of recognition alternatives, each with 'text' and optional 'confidence' fields",
    )

    @field_validator("alternatives")
    def validate_alternatives(cls, v):
        """Validate that alternatives contain text."""
        if not v:
            raise ValueError("At least one recognition result required")
        for alt in v:
            if "text" not in alt:
                raise ValueError("Each recognition result must contain 'text' field")
            if "confidence" in alt and not (
                isinstance(alt["confidence"], float) and 0 <= alt["confidence"] <= 1
            ):
                raise ValueError("Confidence must be a float between 0 and 1")
        return v


# Union type for all possible incoming messages
IncomingMessage = Union[
    SessionInitiateMessage,
    SessionResumeMessage,
    SessionEndMessage,
    UserStreamStartMessage,
    UserStreamChunkMessage,
    UserStreamStopMessage,
    ActivitiesMessage,
    ConnectionValidateMessage,
]

# Union type for all possible outgoing messages
OutgoingMessage = Union[
    SessionAcceptedResponse,
    SessionErrorResponse,
    UserStreamStartedResponse,
    UserStreamStoppedResponse,
    UserStreamHypothesisResponse,
    UserStreamRecognitionResponse,
    PlayStreamStartMessage,
    PlayStreamChunkMessage,
    PlayStreamStopMessage,
    ActivitiesMessage,
    ConnectionValidatedResponse,
]
