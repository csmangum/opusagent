"""
Data models and enums for the AudioCodes mock client.

This module defines all the data structures, enumerations, and configuration
models used throughout the AudioCodes mock client. These models provide
type safety, validation, and clear interfaces for the various components
of the mock client system.

The models are organized into several categories:
- Session Management: Session states, configuration, and lifecycle tracking
- Stream Management: Audio stream states and control
- Message Handling: WebSocket message types and event structures
- Audio Processing: Audio chunk data and metadata
- Conversation Management: Multi-turn conversation state and results

All models use Pydantic for automatic validation, serialization, and
documentation generation. The models follow a hierarchical structure where
configuration models define parameters, state models track current conditions,
and event models represent communication data.

Model Relationships:
- SessionConfig → SessionState: Configuration drives initial state
- SessionState + StreamState: Combined session and stream tracking
- MessageEvent: Represents all incoming WebSocket messages
- AudioChunk: Fundamental unit for audio streaming
- ConversationState → ConversationResult: State tracking to final results

Validation and Constraints:
- All enums provide type safety for status and message types
- Pydantic validators ensure data integrity and format compliance
- Field descriptions provide clear documentation for each attribute
- Default values ensure sensible behavior when not specified
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class SessionStatus(str, Enum):
    """
    Session status enumeration for tracking AudioCodes session lifecycle.
    
    The session status represents the current state of the connection
    between the mock client and the bridge server. Status transitions
    follow a specific flow from disconnected to active to ended.
    
    Status Flow:
    DISCONNECTED → CONNECTING → CONNECTED → INITIATING → ACTIVE → ENDED
                                    ↓
                                RESUMING → ACTIVE → ENDED
                                    ↓
                                ERROR → ENDED
    
    Status Descriptions:
    - DISCONNECTED: No connection established, initial state
    - CONNECTING: WebSocket connection attempt in progress
    - CONNECTED: WebSocket connected but session not yet initiated
    - INITIATING: Session initiation request sent, waiting for acceptance
    - ACTIVE: Session fully established and ready for communication
    - RESUMING: Session resumption attempt in progress
    - ERROR: Session encountered an error and cannot continue
    - ENDED: Session terminated (normal completion or error)
    
    Usage:
        status = SessionStatus.ACTIVE
        if status == SessionStatus.ACTIVE:
            # Session is ready for audio communication
            pass
    """

    DISCONNECTED = "disconnected"  # No connection established
    CONNECTING = "connecting"      # Attempting to establish connection
    CONNECTED = "connected"        # WebSocket connected, session not initiated
    INITIATING = "initiating"      # Session initiation in progress
    ACTIVE = "active"              # Session active and ready for communication
    RESUMING = "resuming"          # Session resumption in progress
    ERROR = "error"                # Session error occurred
    ENDED = "ended"                # Session ended (normal or error)


class StreamStatus(str, Enum):
    """
    Stream status enumeration for tracking audio stream states.
    
    Audio streams (user input and play output) have their own lifecycle
    that is independent of the session status. Streams can be started,
    stopped, and restarted multiple times during a session.
    
    Stream Flow:
    INACTIVE → STARTING → ACTIVE → STOPPING → STOPPED → INACTIVE
    
    Status Descriptions:
    - INACTIVE: Stream not created or fully cleaned up
    - STARTING: Stream start request sent, waiting for confirmation
    - ACTIVE: Stream active and processing audio data
    - STOPPING: Stream stop request sent, waiting for confirmation
    - STOPPED: Stream stopped but not yet cleaned up
    
    Stream Types:
    - User Stream: Audio input from user (microphone/simulated)
    - Play Stream: Audio output to user (AI responses)
    
    Usage:
        user_status = StreamStatus.ACTIVE
        play_status = StreamStatus.INACTIVE
        if user_status == StreamStatus.ACTIVE:
            # User audio stream is ready for input
            pass
    """

    INACTIVE = "inactive"  # Stream not created or fully stopped
    STARTING = "starting"  # Stream start request sent
    ACTIVE = "active"      # Stream active and processing audio
    STOPPING = "stopping"  # Stream stop request sent
    STOPPED = "stopped"    # Stream stopped but not yet cleaned up


class MessageType(str, Enum):
    """
    WebSocket message types for AudioCodes bridge communication.
    
    This enumeration defines all the message types that can be sent
    or received during AudioCodes session communication. Messages
    are categorized by their purpose and direction.
    
    Message Categories:
    - Session: Session lifecycle management and control
    - Connection: Connection validation and health checks
    - Stream: Audio stream control and data transmission
    - Speech: Voice activity detection and transcription events
    - Play: Audio playback control and data
    - Activity: Custom events and activities
    
    Message Direction:
    - Client → Server: Session initiation, audio streaming, events
    - Server → Client: Session responses, audio playback, speech events
    
    Usage:
        msg_type = MessageType.SESSION_ACCEPTED
        if msg_type.value.startswith("session."):
            # Handle session-related message
            pass
    """

    # Session messages - Session lifecycle management
    SESSION_INITIATE = "session.initiate"      # Request new session
    SESSION_RESUME = "session.resume"          # Resume existing session
    SESSION_ACCEPTED = "session.accepted"      # Session accepted by bridge
    SESSION_RESUMED = "session.resumed"        # Session resumed successfully
    SESSION_ERROR = "session.error"            # Session error occurred
    SESSION_END = "session.end"                # End session request

    # Connection messages - Connection validation
    CONNECTION_VALIDATE = "connection.validate"    # Validate connection
    CONNECTION_VALIDATED = "connection.validated"  # Connection validated

    # Stream messages - Audio stream control
    USER_STREAM_START = "userStream.start"     # Start user audio stream
    USER_STREAM_STOP = "userStream.stop"       # Stop user audio stream
    USER_STREAM_CHUNK = "userStream.chunk"     # User audio data chunk
    USER_STREAM_STARTED = "userStream.started" # User stream started
    USER_STREAM_STOPPED = "userStream.stopped" # User stream stopped

    # Speech/VAD messages - Voice activity detection
    USER_STREAM_SPEECH_STARTED = "userStream.speech.started"     # Speech detected
    USER_STREAM_SPEECH_STOPPED = "userStream.speech.stopped"     # Speech ended
    USER_STREAM_SPEECH_COMMITTED = "userStream.speech.committed" # Final transcription
    USER_STREAM_SPEECH_HYPOTHESIS = "userStream.speech.hypothesis" # Interim transcription

    # Play stream messages - Audio playback
    PLAY_STREAM_START = "playStream.start"     # Start audio playback
    PLAY_STREAM_CHUNK = "playStream.chunk"     # Audio playback chunk
    PLAY_STREAM_STOP = "playStream.stop"       # Stop audio playback

    # Activity messages - Custom events
    ACTIVITIES = "activities"                  # Custom activities/events


class SessionConfig(BaseModel):
    """
    Configuration for AudioCodes session parameters.
    
    This model defines all configurable parameters for establishing
    and managing AudioCodes sessions. It includes connection settings,
    audio format preferences, and VAD configuration options.
    
    The configuration is validated on creation to ensure all parameters
    are within acceptable ranges and formats. Configuration changes
    can be made at runtime to adjust session behavior.
    
    Configuration Categories:
    - Connection: Bridge URL and connection settings
    - Bot: Bot identification and caller information
    - Media: Audio format and streaming preferences
    - VAD: Voice activity detection parameters
    - Features: Optional feature enablement
    
    Usage Examples:
        # Basic configuration
        config = SessionConfig(
            bridge_url="ws://localhost:8080",
            bot_name="CustomerServiceBot",
            caller="+15551234567"
        )
        
        # Advanced configuration with VAD
        config = SessionConfig(
            bridge_url="wss://bridge.example.com",
            bot_name="SalesBot",
            caller="+15559876543",
            enable_vad=True,
            vad_threshold=0.6,
            vad_min_speech_duration_ms=300
        )
    """

    bridge_url: str = Field(
        description="WebSocket URL for bridge server connection",
        examples=["ws://localhost:8080", "wss://bridge.example.com"]
    )
    bot_name: str = Field(
        default="TestBot",
        description="Name identifier for the bot/agent"
    )
    caller: str = Field(
        default="+15551234567",
        description="Caller phone number for session identification"
    )
    media_format: str = Field(
        default="raw/lpcm16",
        description="Audio media format for streaming"
    )
    supported_media_formats: List[str] = Field(
        default_factory=lambda: ["raw/lpcm16"],
        description="List of supported audio media formats"
    )
    expect_audio_messages: bool = Field(
        default=True,
        description="Whether to expect and process audio messages"
    )
    
    # VAD (Voice Activity Detection) configuration
    enable_vad: bool = Field(
        default=True,
        description="Enable Voice Activity Detection processing"
    )
    vad_threshold: float = Field(
        default=0.5,
        description="VAD speech detection threshold (0.0 to 1.0)"
    )
    vad_silence_threshold: float = Field(
        default=0.3,
        description="VAD silence detection threshold (0.0 to 1.0)"
    )
    vad_min_speech_duration_ms: int = Field(
        default=500,
        description="Minimum speech duration in milliseconds"
    )
    vad_min_silence_duration_ms: int = Field(
        default=300,
        description="Minimum silence duration in milliseconds"
    )
    enable_speech_hypothesis: bool = Field(
        default=False,
        description="Enable speech hypothesis simulation"
    )

    @field_validator("bridge_url")
    def validate_bridge_url(cls, v):
        """Validate bridge URL format."""
        if not v.startswith(("ws://", "wss://")):
            raise ValueError("Bridge URL must start with ws:// or wss://")
        return v

    @field_validator("vad_threshold", "vad_silence_threshold")
    def validate_vad_thresholds(cls, v):
        """Validate VAD threshold values."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("VAD threshold must be between 0.0 and 1.0")
        return v


class SessionState(BaseModel):
    """
    Current session state and status tracking.
    
    This model tracks the real-time state of an AudioCodes session,
    including connection status, conversation information, and
    various flags that indicate the current session condition.
    
    The session state is updated by the MessageHandler as messages
    are received from the bridge server, providing a complete
    picture of the session's current condition. State changes
    are logged for debugging and monitoring purposes.
    
    State Components:
    - Status: Current session status (DISCONNECTED, ACTIVE, etc.)
    - Conversation: Conversation ID and metadata
    - Connection: Connection validation and health status
    - Media: Current audio format and capabilities
    - Timestamps: Creation and activity timing
    
    State Transitions:
    The session state transitions through various statuses as the
    session progresses, with each transition triggered by specific
    events or messages from the bridge server.
    
    Usage Examples:
        # Check session status
        if session_state.status == SessionStatus.ACTIVE:
            # Session is ready for communication
            pass
        
        # Get session information
        conv_id = session_state.conversation_id
        is_accepted = session_state.accepted
        last_activity = session_state.last_activity
    """

    conversation_id: Optional[str] = Field(
        default=None,
        description="Unique conversation identifier assigned by bridge"
    )
    status: SessionStatus = Field(
        default=SessionStatus.DISCONNECTED,
        description="Current session status"
    )
    accepted: bool = Field(
        default=False,
        description="Whether session has been accepted by bridge"
    )
    resumed: bool = Field(
        default=False,
        description="Whether session has been resumed successfully"
    )
    error: bool = Field(
        default=False,
        description="Whether session has encountered an error"
    )
    error_reason: Optional[str] = Field(
        default=None,
        description="Error reason if session is in error state"
    )
    media_format: str = Field(
        default="raw/lpcm16",
        description="Current audio media format"
    )
    connection_validated: bool = Field(
        default=False,
        description="Whether connection has been validated"
    )
    validation_pending: bool = Field(
        default=False,
        description="Whether connection validation is pending"
    )

    # Timestamps for tracking session lifecycle
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Session creation timestamp"
    )
    last_activity: Optional[datetime] = Field(
        default=None,
        description="Last activity timestamp"
    )

    class Config:
        """Pydantic configuration for SessionState."""
        validate_assignment = False  # Allow runtime state updates


class StreamState(BaseModel):
    """
    Audio stream state information and control.
    
    This model tracks the state of audio streams (user input and
    play output) during an AudioCodes session. It maintains
    separate status for each stream type and tracks speech
    activity state for VAD processing.
    
    Stream states are managed independently of session state,
    allowing for fine-grained control over audio processing.
    Streams can be started, stopped, and restarted multiple
    times during a session as needed.
    
    Stream Types:
    - User Stream: Audio input from user (microphone/simulated)
    - Play Stream: Audio output to user (AI responses)
    
    Speech State:
    The speech state tracks Voice Activity Detection results
    and manages speech event generation for realistic simulation.
    
    Usage Examples:
        # Check stream status
        if stream_state.user_stream == StreamStatus.ACTIVE:
            # User stream is ready for audio input
            pass
        
        # Check speech activity
        if stream_state.speech_active:
            # Speech is currently detected
            pass
        
        # Get current stream information
        current_id = stream_state.current_stream_id
        play_status = stream_state.play_stream
    """

    user_stream: StreamStatus = Field(
        default=StreamStatus.INACTIVE,
        description="User audio input stream status"
    )
    play_stream: StreamStatus = Field(
        default=StreamStatus.INACTIVE,
        description="Audio playback stream status"
    )
    current_stream_id: Optional[str] = Field(
        default=None,
        description="Current active stream identifier"
    )

    # Speech/VAD state tracking
    speech_active: bool = Field(
        default=False,
        description="Whether speech is currently detected"
    )
    speech_committed: bool = Field(
        default=False,
        description="Whether speech has been committed (finalized)"
    )
    current_hypothesis: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Current speech hypothesis (interim results)"
    )
    speech_start_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when current speech started"
    )

    class Config:
        """Pydantic configuration for StreamState."""
        validate_assignment = False  # Allow runtime state updates


class AudioChunk(BaseModel):
    """
    Audio chunk data structure for streaming.
    
    This model represents a single chunk of audio data that can be
    streamed between the mock client and bridge server. Audio chunks
    are base64-encoded and include metadata for proper processing.
    
    Audio chunks are the fundamental unit of audio streaming,
    allowing for real-time audio processing and buffering. Each
    chunk contains a portion of audio data that can be processed
    independently while maintaining the overall audio stream.
    
    Chunk Properties:
    - Data: Base64-encoded audio data (typically 16-bit PCM)
    - Index: Sequential position in the audio stream
    - Timestamp: When the chunk was created or received
    - Size: Size of the audio data in bytes
    
    Processing Pipeline:
    1. Audio file loaded and converted to target format
    2. Audio data split into chunks of specified size
    3. Each chunk encoded as base64 string
    4. Chunks streamed with metadata for reconstruction
    
    Usage Examples:
        # Create audio chunk
        chunk = AudioChunk(
            data="UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT",
            chunk_index=1,
            size_bytes=32000
        )
        
        # Access chunk properties
        audio_data = base64.b64decode(chunk.data)
        chunk_position = chunk.chunk_index
        chunk_size = chunk.size_bytes
    """

    data: str = Field(
        description="Base64-encoded audio data"
    )
    chunk_index: int = Field(
        description="Sequential index of this chunk in the stream"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when chunk was created"
    )
    size_bytes: int = Field(
        description="Size of the audio data in bytes"
    )

    @field_validator("data")
    def validate_data(cls, v):
        """Validate base64 audio data format."""
        try:
            import base64
            base64.b64decode(v)
            return v
        except Exception:
            raise ValueError("Audio data must be valid base64-encoded")


class MessageEvent(BaseModel):
    """
    WebSocket message event representation.
    
    This model represents a parsed WebSocket message from the bridge
    server, including the message type, conversation context, and
    associated data. Message events are used throughout the system
    for event handling and state updates.
    
    Message events provide a structured way to handle the various
    types of messages that can be received during an AudioCodes session.
    Each event contains the message type, conversation context, and
    any associated data payload.
    
    Event Structure:
    - Type: Message type from MessageType enumeration
    - Conversation ID: Associated conversation identifier
    - Timestamp: When the message was received
    - Data: Message payload and additional information
    
    Event Processing:
    Message events are processed by the MessageHandler, which:
    1. Parses incoming WebSocket messages
    2. Creates MessageEvent objects
    3. Routes events to appropriate handlers
    4. Updates session and stream state
    
    Usage Examples:
        # Create message event
        event = MessageEvent(
            type=MessageType.SESSION_ACCEPTED,
            conversation_id="conv_12345",
            data={"sessionId": "sess_67890"}
        )
        
        # Process message event
        if event.type == MessageType.SESSION_ACCEPTED:
            conv_id = event.conversation_id
            session_data = event.data
            # Handle session acceptance
    """

    type: MessageType = Field(
        description="Type of message event"
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Associated conversation identifier"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Event timestamp"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Message payload and additional data"
    )

    @field_validator("type")
    def validate_type(cls, v):
        """Validate message type."""
        if not isinstance(v, MessageType):
            raise ValueError("Message type must be a valid MessageType")
        return v


class ConversationState(BaseModel):
    """
    Multi-turn conversation state and history tracking.
    
    This model maintains the complete state of a multi-turn conversation,
    including turn history, audio collection, and activity tracking.
    It provides the foundation for conversation analysis and testing.
    
    The conversation state is updated as the conversation progresses,
    building a complete record of the interaction for later analysis.
    It tracks both the conversation flow and the audio data exchanged
    during the conversation.
    
    State Components:
    - Conversation: Basic conversation information and metadata
    - Turns: Detailed turn-by-turn history and results
    - Audio: Collected audio chunks for greetings and responses
    - Activities: Custom events and activities received
    - Timing: Conversation timing and performance metrics
    
    Audio Collection:
    The conversation state tracks audio collection for both greetings
    (initial AI responses) and user responses. Audio chunks are
    collected and stored for later analysis or playback.
    
    Usage Examples:
        # Start new conversation
        conv_state = ConversationState(conversation_id="conv_12345")
        
        # Track conversation progress
        conv_state.turn_count += 1
        conv_state.turns.append({
            "turn_number": 1,
            "user_audio": "audio_file.wav",
            "ai_response": "response_chunks",
            "success": True
        })
        
        # Collect audio
        conv_state.greeting_chunks.extend(greeting_audio)
        conv_state.response_chunks.extend(response_audio)
    """

    conversation_id: str = Field(
        description="Unique conversation identifier"
    )
    turn_count: int = Field(
        default=0,
        description="Number of completed conversation turns"
    )
    turns: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detailed turn history and results"
    )

    # Audio collection for analysis
    greeting_chunks: List[str] = Field(
        default_factory=list,
        description="Collected greeting audio chunks"
    )
    response_chunks: List[str] = Field(
        default_factory=list,
        description="Collected response audio chunks"
    )
    collecting_greeting: bool = Field(
        default=False,
        description="Currently collecting greeting audio"
    )
    collecting_response: bool = Field(
        default=False,
        description="Currently collecting response audio"
    )

    # Activity tracking
    activities_received: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="All received activities and events"
    )
    last_activity: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Most recent activity received"
    )

    # Timestamps for conversation timing
    started_at: datetime = Field(
        default_factory=datetime.now,
        description="Conversation start timestamp"
    )
    last_turn_at: Optional[datetime] = Field(
        default=None,
        description="Last turn completion timestamp"
    )

    class Config:
        """Pydantic configuration for ConversationState."""
        validate_assignment = False  # Allow runtime state updates


class ConversationResult(BaseModel):
    """
    Results and analysis of a multi-turn conversation.
    
    This model provides comprehensive results and statistics for
    completed multi-turn conversations. It includes success metrics,
    timing information, and detailed turn-by-turn analysis.
    
    Conversation results are used for testing validation, performance
    analysis, and quality assessment of the conversation system.
    They provide both high-level metrics and detailed breakdowns
    of the conversation performance.
    
    Result Components:
    - Metrics: Success rates, completion counts, and performance indicators
    - Timing: Conversation duration and timing analysis
    - Audio: Audio collection statistics and quality metrics
    - Turns: Detailed turn-by-turn results and analysis
    - Errors: Error tracking and failure analysis
    
    Analysis Features:
    - Success rate calculation based on completed vs attempted turns
    - Duration tracking for performance analysis
    - Audio quality metrics and collection statistics
    - Turn-by-turn breakdown for detailed analysis
    - Error tracking for failure mode analysis
    
    Usage Examples:
        # Create conversation result
        result = ConversationResult(
            total_turns=5,
            completed_turns=4,
            success=True,
            duration=45.2,
            success_rate=80.0
        )
        
        # Analyze results
        if result.success_rate >= 80.0:
            print("Conversation passed quality threshold")
        
        # Get timing information
        duration = result.duration
        success_rate = result.success_rate
    """

    total_turns: int = Field(
        description="Total number of conversation turns attempted"
    )
    completed_turns: int = Field(
        default=0,
        description="Number of successfully completed turns"
    )
    greeting_received: bool = Field(
        default=False,
        description="Whether initial greeting was received"
    )
    greeting_chunks: int = Field(
        default=0,
        description="Number of greeting audio chunks collected"
    )
    success: bool = Field(
        default=False,
        description="Overall conversation success indicator"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if conversation failed"
    )
    turns: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detailed results for each conversation turn"
    )

    # Timing information
    start_time: datetime = Field(
        default_factory=datetime.now,
        description="Conversation start timestamp"
    )
    end_time: Optional[datetime] = Field(
        default=None,
        description="Conversation end timestamp"
    )

    @property
    def duration(self) -> Optional[float]:
        """
        Calculate conversation duration in seconds.
        
        Returns:
            Optional[float]: Duration in seconds, or None if not ended
        """
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """
        Calculate conversation success rate as percentage.
        
        Returns:
            float: Success rate as percentage (0.0 to 100.0)
        """
        if self.total_turns == 0:
            return 0.0
        return (self.completed_turns / self.total_turns) * 100.0
