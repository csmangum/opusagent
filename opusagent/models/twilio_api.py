"""
Pydantic models for Twilio Media Streams WebSocket message structures.

This module defines structured data models for all incoming and outgoing messages
in the Twilio Media Streams WebSocket protocol, providing type validation and documentation.

Twilio Media Streams allows real-time access to audio from phone calls. The WebSocket
connection enables bidirectional communication where:
1. Twilio sends audio from the call to your server
2. Your server can send audio back to be played on the call
3. Various control and metadata messages are exchanged

The communication flow involves:
1. Twilio establishes a WebSocket connection to your server
2. Messages are exchanged as JSON (with audio encoded in base64)
3. The connection remains active for the entire call duration
4. Authentication is handled via the Stream configuration in TwiML

Note: Media Streams support both unidirectional (receive only) and bidirectional
(send and receive) audio streaming.

Reference: https://www.twilio.com/docs/voice/media-streams/websocket-messages
"""

import base64
import enum
import re
from typing import Dict, List, Literal, Optional, Pattern, Union

from pydantic import BaseModel, Field, field_validator


class TwilioEventType(str, enum.Enum):
    """Enumeration of all supported Twilio Media Streams message types.

    This enum provides type-safe access to all event type strings used in
    the Twilio Media Streams WebSocket protocol.
    """

    # Messages from Twilio to WebSocket server
    CONNECTED = "connected"
    START = "start"
    MEDIA = "media"
    STOP = "stop"
    DTMF = "dtmf"
    MARK = "mark"

    # Messages from WebSocket server to Twilio (bidirectional streams only)
    # Note: MEDIA, MARK also used for outgoing messages
    CLEAR = "clear"


# Regular expression patterns for validation
SID_PATTERN: Pattern = re.compile(r"^[A-Z]{2}[a-f0-9]{32}$")
DTMF_PATTERN: Pattern = re.compile(r"^[0-9*#ABCD]$")

# Supported audio formats
SUPPORTED_ENCODINGS = ["audio/x-mulaw"]
SUPPORTED_SAMPLE_RATES = [8000]
SUPPORTED_CHANNELS = [1]


# Base Models
class BaseTwilioMessage(BaseModel):
    """Base model for all Twilio Media Streams WebSocket messages.

    All messages exchanged in the Twilio Media Streams protocol include
    at least the 'event' field to identify the message type.
    """

    event: str = Field(..., description="Message event type identifier")


class TwilioMessageWithSequence(BaseTwilioMessage):
    """Base model for Twilio messages that include sequence numbers.

    Many Twilio messages include a sequence number for tracking message order.
    """

    sequenceNumber: str = Field(
        ..., description="Number used to keep track of message sending order"
    )


class TwilioMessageWithStreamSid(BaseTwilioMessage):
    """Base model for Twilio messages that include a stream SID.

    Most messages after the initial connection include the stream SID.
    """

    streamSid: str = Field(..., description="The unique identifier of the Stream")

    @field_validator("streamSid")
    def validate_stream_sid(cls, v):
        """Validate that stream SID follows Twilio's format."""
        if not SID_PATTERN.match(v):
            # Log warning but don't fail - Twilio might use different formats
            import logging

            from opusagent.config.constants import LOGGER_NAME

            logger = logging.getLogger(LOGGER_NAME)
            logger.warning(f"Stream SID does not match expected pattern: {v}")
        return v


# Messages from Twilio to WebSocket server


class ConnectedMessage(BaseTwilioMessage):
    """Model for 'connected' message from Twilio.

    This is the first message sent by Twilio once a WebSocket connection is established.
    It describes the protocol to expect in subsequent messages.

    Example:
    {
      "event": "connected",
      "protocol": "Call",
      "version": "1.0.0"
    }
    """

    event: Literal[TwilioEventType.CONNECTED]
    protocol: str = Field(..., description="Protocol for the WebSocket connection")
    version: str = Field(..., description="Semantic version of the protocol")

    @field_validator("protocol")
    def validate_protocol(cls, v):
        """Validate that protocol is expected value."""
        if v != "Call":
            import logging

            from opusagent.config.constants import LOGGER_NAME

            logger = logging.getLogger(LOGGER_NAME)
            logger.warning(f"Unexpected protocol value: {v}")
        return v


class MediaFormat(BaseModel):
    """Model for media format specification in Twilio messages."""

    encoding: str = Field(..., description="The encoding of the data in the payload")
    sampleRate: int = Field(
        ..., description="The sample rate in hertz of the audio data"
    )
    channels: int = Field(
        ..., description="The number of channels in the input audio data"
    )

    @field_validator("encoding")
    def validate_encoding(cls, v):
        """Validate that encoding is supported."""
        if v not in SUPPORTED_ENCODINGS:
            raise ValueError(f"Unsupported encoding: {v}")
        return v

    @field_validator("sampleRate")
    def validate_sample_rate(cls, v):
        """Validate that sample rate is supported."""
        if v not in SUPPORTED_SAMPLE_RATES:
            raise ValueError(f"Unsupported sample rate: {v}")
        return v

    @field_validator("channels")
    def validate_channels(cls, v):
        """Validate that channel count is supported."""
        if v not in SUPPORTED_CHANNELS:
            raise ValueError(f"Unsupported channel count: {v}")
        return v


class StartMetadata(BaseModel):
    """Model for start message metadata."""

    streamSid: str = Field(..., description="The unique identifier of the Stream")
    accountSid: str = Field(
        ..., description="The SID of the Account that created the Stream"
    )
    callSid: str = Field(..., description="The SID of the Call that started the Stream")
    tracks: List[str] = Field(
        ...,
        description="Array indicating which media flows are expected (inbound, outbound)",
    )
    customParameters: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom parameters set when defining the Stream",
    )
    mediaFormat: MediaFormat = Field(
        ..., description="Format of the payload in the media messages"
    )

    @field_validator("tracks")
    def validate_tracks(cls, v):
        """Validate that tracks contain expected values."""
        valid_tracks = {"inbound", "outbound"}
        for track in v:
            if track not in valid_tracks:
                raise ValueError(f"Invalid track: {track}")
        return v


class StartMessage(TwilioMessageWithSequence, TwilioMessageWithStreamSid):
    """Model for 'start' message from Twilio.

    Contains metadata about the Stream and is sent immediately after the 'connected' message.
    It is only sent once at the start of the Stream.

    Example:
    {
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
    """

    event: Literal[TwilioEventType.START]
    start: StartMetadata = Field(..., description="Stream metadata")


class MediaPayload(BaseModel):
    """Model for media payload in media messages."""

    track: str = Field(..., description="The track of the media (inbound or outbound)")
    chunk: str = Field(..., description="The chunk number of the media")
    timestamp: str = Field(..., description="The timestamp of the media")
    payload: str = Field(..., description="Base64-encoded audio data")

    @field_validator("track")
    def validate_track(cls, v):
        """Validate that track is expected value."""
        if v not in ["inbound", "outbound"]:
            raise ValueError(f"Invalid track: {v}")
        return v

    @field_validator("payload")
    def validate_payload(cls, v):
        """Validate that payload is valid base64."""
        try:
            if v:
                base64.b64decode(v)
            else:
                raise ValueError("Media payload cannot be empty")
        except Exception:
            raise ValueError("Invalid base64 encoded audio data")
        return v


class MediaMessage(TwilioMessageWithSequence, TwilioMessageWithStreamSid):
    """Model for 'media' message from Twilio.

    Contains audio data from the call. These messages are sent continuously
    during the call when audio is being transmitted.

    Example:
    {
      "event": "media",
      "sequenceNumber": "4",
      "media": {
        "track": "inbound",
        "chunk": "2",
        "timestamp": "5",
        "payload": "no+JhoaJjpzS..."
      },
      "streamSid": "MZXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    }
    """

    event: Literal[TwilioEventType.MEDIA]
    media: MediaPayload = Field(..., description="Media payload data")


class StopMetadata(BaseModel):
    """Model for stop message metadata."""

    accountSid: str = Field(
        ..., description="The Account identifier that created the Stream"
    )
    callSid: str = Field(..., description="The Call identifier that started the Stream")


class StopMessage(TwilioMessageWithSequence, TwilioMessageWithStreamSid):
    """Model for 'stop' message from Twilio.

    Sent when the Stream has stopped or the call has ended.

    Example:
    {
      "event": "stop",
      "sequenceNumber": "5",
      "stop": {
        "accountSid": "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "callSid": "CAXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
      },
      "streamSid": "MZXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    }
    """

    event: Literal[TwilioEventType.STOP]
    stop: StopMetadata = Field(..., description="Stop metadata")


class DTMFPayload(BaseModel):
    """Model for DTMF payload in DTMF messages."""

    track: str = Field(..., description="The track on which the DTMF key was pressed")
    digit: str = Field(..., description="The number-key tone detected")

    @field_validator("track")
    def validate_track(cls, v):
        """Validate that track is expected value."""
        if v != "inbound_track":
            import logging

            from opusagent.config.constants import LOGGER_NAME

            logger = logging.getLogger(LOGGER_NAME)
            logger.warning(f"Unexpected DTMF track: {v}")
        return v

    @field_validator("digit")
    def validate_digit(cls, v):
        """Validate that digit is a valid DTMF value."""
        if not DTMF_PATTERN.match(v):
            raise ValueError(f"Invalid DTMF digit: {v}")
        return v


class DTMFMessage(TwilioMessageWithSequence, TwilioMessageWithStreamSid):
    """Model for 'dtmf' message from Twilio.

    Sent when someone presses a touch-tone number key in the inbound stream.
    This message is currently only supported in bidirectional Streams.

    Example:
    {
      "event": "dtmf",
      "streamSid": "MZXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
      "sequenceNumber": "5",
      "dtmf": {
        "track": "inbound_track",
        "digit": "1"
      }
    }
    """

    event: Literal[TwilioEventType.DTMF]
    dtmf: DTMFPayload = Field(..., description="DTMF payload data")


class MarkPayload(BaseModel):
    """Model for mark payload in mark messages."""

    name: str = Field(..., description="A custom value for tracking audio playback")


class MarkMessage(TwilioMessageWithSequence, TwilioMessageWithStreamSid):
    """Model for 'mark' message from Twilio.

    Sent only during bidirectional Streams to indicate when audio playback is complete.
    Twilio sends this in response to mark messages sent by your server.

    Example:
    {
      "event": "mark",
      "sequenceNumber": "4",
      "streamSid": "MZXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
      "mark": {
        "name": "my label"
      }
    }
    """

    event: Literal[TwilioEventType.MARK]
    mark: MarkPayload = Field(..., description="Mark payload data")


# Messages from WebSocket server to Twilio (bidirectional streams only)


class OutgoingMediaPayload(BaseModel):
    """Model for media payload in outgoing media messages."""

    payload: str = Field(..., description="Raw mulaw/8000 audio encoded in base64")

    @field_validator("payload")
    def validate_payload(cls, v):
        """Validate that payload is valid base64."""
        try:
            if v:
                base64.b64decode(v)
            else:
                raise ValueError("Media payload cannot be empty")
        except Exception:
            raise ValueError("Invalid base64 encoded audio data")
        return v


class OutgoingMediaMessage(TwilioMessageWithStreamSid):
    """Model for 'media' message to Twilio.

    Sent by your server to stream audio back to the call participant.
    The audio must be encoded as mulaw/8000 and base64 encoded.

    Example:
    {
      "event": "media",
      "streamSid": "MZXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
      "media": {
        "payload": "a3242sa..."
      }
    }
    """

    event: Literal[TwilioEventType.MEDIA]
    media: OutgoingMediaPayload = Field(..., description="Media payload data")


class OutgoingMarkMessage(TwilioMessageWithStreamSid):
    """Model for 'mark' message to Twilio.

    Sent by your server after sending media to be notified when audio playback is complete.
    Twilio will send back a mark event with the same name when audio finishes playing.

    Example:
    {
      "event": "mark",
      "streamSid": "MZXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
      "mark": {
        "name": "my label"
      }
    }
    """

    event: Literal[TwilioEventType.MARK]
    mark: MarkPayload = Field(..., description="Mark payload data")


class ClearMessage(TwilioMessageWithStreamSid):
    """Model for 'clear' message to Twilio.

    Sent by your server to interrupt buffered audio and clear the audio queue.
    This will cause any pending mark messages to be sent back immediately.

    Example:
    {
      "event": "clear",
      "streamSid": "MZXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    }
    """

    event: Literal[TwilioEventType.CLEAR]


# Union types for message categorization

# Messages received from Twilio
IncomingMessage = Union[
    ConnectedMessage,
    StartMessage,
    MediaMessage,
    StopMessage,
    DTMFMessage,
    MarkMessage,
]

# Messages sent to Twilio (bidirectional streams only)
OutgoingMessage = Union[
    OutgoingMediaMessage,
    OutgoingMarkMessage,
    ClearMessage,
]

# All possible Twilio Media Streams messages
TwilioMessage = Union[IncomingMessage, OutgoingMessage]
