"""Session state models for persistent session management.

This module defines the data models for session state persistence,
including session metadata, conversation context, and state tracking.
The SessionState class provides a comprehensive model for storing and
restoring conversation sessions across different storage backends.

The module includes:
- SessionStatus enumeration for tracking session lifecycle states
- SessionState dataclass for comprehensive session data storage
- Serialization/deserialization methods for storage persistence
- Session validation and state management utilities

Example:
    ```python
    # Create a new session state
    session = SessionState(
        conversation_id="call_123",
        bot_name="customer-service-bot",
        caller="+1234567890"
    )
    
    # Add conversation items
    session.add_conversation_item({
        "role": "user",
        "content": "Hello, I need help with my account"
    })
    
    # Check if session can be resumed
    if session.can_resume(max_age_seconds=3600):
        print("Session is resumable")
    
    # Serialize for storage
    session_dict = session.to_dict()
    
    # Deserialize from storage
    restored_session = SessionState.from_dict(session_dict)
    ```
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
import asyncio
import logging


class SessionStatus(Enum):
    """Session status enumeration for tracking session lifecycle.
    
    This enumeration defines the possible states a session can be in
    throughout its lifecycle, from creation to termination.
    
    Attributes:
        INITIATED: Session has been created but not yet active
        ACTIVE: Session is currently active and processing
        PAUSED: Session is temporarily paused but can be resumed
        ENDED: Session has been terminated and cannot be resumed
        ERROR: Session encountered an error and may need intervention
    """
    INITIATED = "initiated"
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    ERROR = "error"


@dataclass
class SessionState:
    """Comprehensive session state model for conversation persistence.
    
    This model tracks all the information needed to restore a session,
    including conversation context, audio state, and function calls.
    It provides methods for session lifecycle management, state validation,
    and serialization for storage persistence.
    
    The SessionState maintains conversation continuity across system
    restarts, network interruptions, and session resumptions. It stores
    both the conversation history and the current processing state to
    enable seamless session recovery.
    
    State Transition Callbacks:
    The SessionState supports registering callbacks that are triggered when
    the session status changes. This enables reactive programming patterns
    and allows components to respond to state changes without tight coupling.
    
    Attributes:
        conversation_id: Unique identifier for the conversation session
        session_id: Optional internal session identifier
        bridge_type: Type of telephony bridge being used (e.g., "audiocodes", "twilio")
        bot_name: Name or identifier of the bot handling the conversation
        caller: Identifier of the person making the call
        media_format: Audio format specification for the session
        status: Current session status from SessionStatus enumeration
        created_at: Timestamp when the session was created
        last_activity: Timestamp of the last activity in the session
        resumed_count: Number of times this session has been resumed
        conversation_history: List of conversation messages and interactions
        current_turn: Current turn number in the conversation
        function_calls: History of function calls made during the session
        audio_buffer: List of audio data chunks for the session
        audio_metadata: Additional metadata about audio processing
        openai_session_id: OpenAI session identifier for API continuity
        openai_conversation_id: OpenAI conversation identifier
        active_response_id: ID of the currently active response
        error_count: Number of errors encountered in this session
        last_error: Description of the last error encountered
        metadata: Custom metadata dictionary for extensibility
        _status_callbacks: Internal list of status change callbacks
    
    Example:
        ```python
        # Create a new session
        session = SessionState(
            conversation_id="call_123",
            bot_name="customer-service-bot",
            caller="+1234567890",
            bridge_type="audiocodes"
        )
        
        # Register status change callback
        def on_status_change(old_status, new_status, session):
            print(f"Session {session.conversation_id} changed from {old_status} to {new_status}")
        
        session.register_status_callback(on_status_change)
        
        # Add conversation history
        session.add_conversation_item({
            "role": "user",
            "content": "I need help with my account"
        })
        
        # Update session status (triggers callbacks)
        session.update_status(SessionStatus.ACTIVE)
        
        # Check session validity
        if session.can_resume():
            print("Session can be resumed")
        ```
    """
    
    # Core identifiers
    conversation_id: str
    session_id: Optional[str] = None
    bridge_type: str = "audiocodes"
    
    # Session metadata
    bot_name: str = "voice-bot"
    caller: str = "unknown"
    media_format: str = "raw/lpcm16"
    
    # State tracking
    status: SessionStatus = SessionStatus.INITIATED
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    resumed_count: int = 0
    
    # Conversation context
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    current_turn: int = 0
    function_calls: List[Dict[str, Any]] = field(default_factory=list)
    
    # Audio state
    audio_buffer: List[bytes] = field(default_factory=list)
    audio_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # OpenAI Realtime API state
    openai_session_id: Optional[str] = None
    openai_conversation_id: Optional[str] = None
    active_response_id: Optional[str] = None
    
    # Error tracking
    error_count: int = 0
    last_error: Optional[str] = None
    
    # Custom metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # State transition callbacks (not serialized)
    _status_callbacks: List[Callable] = field(default_factory=list, init=False, repr=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session state to dictionary for storage serialization.
        
        Serializes the SessionState object into a dictionary format suitable
        for storage in various backends (Redis, database, file system, etc.).
        Handles complex data types like datetime objects and binary audio data
        by converting them to storage-friendly formats.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the session state
                with all fields serialized for storage. Audio buffer chunks
                are converted to hexadecimal strings for JSON compatibility.
                
        Example:
            ```python
            session = SessionState(conversation_id="call_123")
            session_dict = session.to_dict()
            
            # Store in Redis
            redis_client.set(f"session:{session.conversation_id}", json.dumps(session_dict))
            ```
        """
        return {
            "conversation_id": self.conversation_id,
            "session_id": self.session_id,
            "bridge_type": self.bridge_type,
            "bot_name": self.bot_name,
            "caller": self.caller,
            "media_format": self.media_format,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "resumed_count": self.resumed_count,
            "conversation_history": self.conversation_history,
            "current_turn": self.current_turn,
            "function_calls": self.function_calls,
            "audio_buffer": [chunk.hex() for chunk in self.audio_buffer],
            "audio_metadata": self.audio_metadata,
            "openai_session_id": self.openai_session_id,
            "openai_conversation_id": self.openai_conversation_id,
            "active_response_id": self.active_response_id,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        """Create SessionState instance from dictionary data.
        
        Deserializes a dictionary back into a SessionState object, handling
        data type conversions and providing fallback values for missing fields.
        This method is robust against data corruption and provides logging
        for debugging serialization issues.
        
        Args:
            data: Dictionary containing session state data. Must contain at
                least a 'conversation_id' field. Other fields are optional
                and will use default values if missing.
                
        Returns:
            SessionState: New instance populated with the provided data
            
        Raises:
            ValueError: If conversation_id is missing or empty
            ValueError: If datetime parsing fails for created_at or last_activity
            
        Example:
            ```python
            # Load from storage
            session_data = {
                "conversation_id": "call_123",
                "bot_name": "customer-service-bot",
                "status": "active",
                "conversation_history": [
                    {"role": "user", "content": "Hello"}
                ]
            }
            
            session = SessionState.from_dict(session_data)
            print(f"Restored session: {session.conversation_id}")
            ```
        """
        # Validate required conversation_id
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            raise ValueError("conversation_id is required but missing from session data")
        
        # Safely handle status with fallback to initiated
        status_value = data.get("status", "initiated")
        try:
            status = SessionStatus(status_value)
        except ValueError:
            # Log warning and fallback to initiated status
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Invalid session status '{status_value}', falling back to 'initiated'")
            status = SessionStatus.INITIATED
        
        # Convert hex strings back to bytes for audio buffer
        audio_buffer = []
        try:
            audio_buffer = [bytes.fromhex(chunk) for chunk in data.get("audio_buffer", [])]
        except (ValueError, TypeError) as e:
            # Log warning and use empty buffer if hex conversion fails
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to convert audio buffer from hex: {e}, using empty buffer")
            audio_buffer = []
        
        return cls(
            conversation_id=conversation_id,
            session_id=data.get("session_id"),
            bridge_type=data.get("bridge_type", "audiocodes"),
            bot_name=data.get("bot_name", "voice-bot"),
            caller=data.get("caller", "unknown"),
            media_format=data.get("media_format", "raw/lpcm16"),
            status=status,
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            last_activity=datetime.fromisoformat(data.get("last_activity", datetime.now().isoformat())),
            resumed_count=data.get("resumed_count", 0),
            conversation_history=data.get("conversation_history", []),
            current_turn=data.get("current_turn", 0),
            function_calls=data.get("function_calls", []),
            audio_buffer=audio_buffer,
            audio_metadata=data.get("audio_metadata", {}),
            openai_session_id=data.get("openai_session_id"),
            openai_conversation_id=data.get("openai_conversation_id"),
            active_response_id=data.get("active_response_id"),
            error_count=data.get("error_count", 0),
            last_error=data.get("last_error"),
            metadata=data.get("metadata", {}),
        )
    
    def update_activity(self) -> None:
        """Update the last activity timestamp to current time.
        
        This method is called whenever the session has activity to ensure
        accurate tracking of session freshness for expiration checks and
        cleanup operations.
        
        Example:
            ```python
            # Update activity when user speaks
            session.update_activity()
            print(f"Last activity: {session.last_activity}")
            ```
        """
        self.last_activity = datetime.now()
    
    def increment_resume_count(self) -> None:
        """Increment resume count and update session status to active.
        
        Called when a session is successfully resumed. Updates the resume
        counter, sets the status to ACTIVE, and updates the activity timestamp.
        This method is typically called by the session manager service.
        
        Example:
            ```python
            # When resuming a session
            session.increment_resume_count()
            print(f"Session resumed {session.resumed_count} times")
            ```
        """
        self.resumed_count += 1
        self.update_status(SessionStatus.ACTIVE)
    
    def add_conversation_item(self, item: Dict[str, Any]) -> None:
        """Add a conversation item to the session history.
        
        Adds a new conversation item (message, response, etc.) to the
        conversation history and increments the turn counter. Also updates
        the activity timestamp to reflect the new conversation activity.
        
        Args:
            item: Dictionary containing conversation item data. Should include
                at least a 'role' and 'content' field. Common structure:
                {
                    "role": "user" | "assistant" | "system",
                    "content": "Message content",
                    "timestamp": "2023-01-01T12:00:00",
                    "metadata": {...}
                }
                
        Example:
            ```python
            # Add user message
            session.add_conversation_item({
                "role": "user",
                "content": "I need help with my account",
                "timestamp": "2023-01-01T12:00:00"
            })
            
            # Add bot response
            session.add_conversation_item({
                "role": "assistant",
                "content": "I'd be happy to help you with your account.",
                "timestamp": "2023-01-01T12:00:01"
            })
            
            print(f"Conversation turn: {session.current_turn}")
            ```
        """
        self.conversation_history.append(item)
        self.current_turn += 1
        self.update_activity()
    
    def add_function_call(self, function_call: Dict[str, Any]) -> None:
        """Add a function call to the session history.
        
        Records a function call made during the conversation for audit
        and debugging purposes. Function calls are stored separately from
        conversation items to maintain clear separation of concerns.
        
        Args:
            function_call: Dictionary containing function call data. Should
                include function name, arguments, and result. Common structure:
                {
                    "name": "function_name",
                    "arguments": {...},
                    "result": {...},
                    "timestamp": "2023-01-01T12:00:00"
                }
                
        Example:
            ```python
            # Add function call
            session.add_function_call({
                "name": "get_account_balance",
                "arguments": {"account_id": "12345"},
                "result": {"balance": 1000.00},
                "timestamp": "2023-01-01T12:00:00"
            })
            
            print(f"Function calls: {len(session.function_calls)}")
            ```
        """
        self.function_calls.append(function_call)
        self.update_activity()
    
    def set_error(self, error_message: str) -> None:
        """Set the session to error state and record error information.
        
        Updates the session status to ERROR, increments the error counter,
        and stores the error message for debugging and monitoring purposes.
        This method should be called when the session encounters an
        unrecoverable error.
        
        Args:
            error_message: Human-readable description of the error that
                occurred. Should be descriptive enough for debugging.
                
        Example:
            ```python
            try:
                # Some operation that might fail
                process_audio()
            except Exception as e:
                session.set_error(f"Audio processing failed: {str(e)}")
                print(f"Session error count: {session.error_count}")
            ```
        """
        self.last_error = error_message
        self.error_count += 1
        self.update_status(SessionStatus.ERROR)
    
    def is_expired(self, max_age_seconds: int = 3600) -> bool:
        """Check if the session has expired based on last activity.
        
        Determines if the session has exceeded the specified maximum age
        since the last activity. This is used for cleanup operations and
        to prevent resuming very old sessions.
        
        Args:
            max_age_seconds: Maximum age in seconds before session is
                considered expired. Defaults to 3600 (1 hour).
                
        Returns:
            bool: True if session has expired, False otherwise
            
        Example:
            ```python
            # Check if session expired after 30 minutes
            if session.is_expired(max_age_seconds=1800):
                print("Session has expired")
            
            # Check with default 1 hour expiration
            if session.is_expired():
                print("Session expired (1 hour)")
            ```
        """
        age = (datetime.now() - self.last_activity).total_seconds()
        return age > max_age_seconds
    
    def can_resume(self, max_age_seconds: Optional[int] = None) -> bool:
        """Check if the session can be resumed.
        
        Performs comprehensive validation to determine if the session
        is in a state that allows resumption. Checks both the session
        status and expiration (if max_age_seconds is provided).
        
        Args:
            max_age_seconds: Optional maximum age in seconds before session
                is considered expired. If None, only status is checked.
                If provided, both status and expiration are validated.
                
        Returns:
            bool: True if session can be resumed, False otherwise
            
        Example:
            ```python
            # Check if session can be resumed (status only)
            if session.can_resume():
                print("Session status allows resumption")
            
            # Check with expiration validation (30 minutes)
            if session.can_resume(max_age_seconds=1800):
                print("Session can be resumed (not expired)")
            else:
                print("Session cannot be resumed (expired or invalid status)")
            ```
        """
        # Check status
        if self.status in [SessionStatus.ENDED, SessionStatus.ERROR]:
            return False
            
        # Check expiration if max_age_seconds is provided
        if max_age_seconds is not None and self.is_expired(max_age_seconds):
            return False
            
        return True
    
    def register_status_callback(
        self, 
        callback: Callable[[SessionStatus, SessionStatus, 'SessionState'], Any],
        priority: int = 0
    ) -> None:
        """
        Register a callback to be called when session status changes.
        
        Args:
            callback: Function to call with (old_status, new_status, session) parameters
            priority: Callback priority (higher numbers execute first)
            
        Example:
            ```python
            def on_status_change(old_status, new_status, session):
                print(f"Session status changed from {old_status} to {new_status}")
            
            session.register_status_callback(on_status_change)
            ```
        """
        self._status_callbacks.append((priority, callback))
        self._status_callbacks.sort(key=lambda x: x[0], reverse=True)
    
    def unregister_status_callback(self, callback: Callable) -> bool:
        """
        Unregister a status change callback.
        
        Args:
            callback: The callback function to remove
            
        Returns:
            bool: True if callback was found and removed
        """
        for i, (priority, cb) in enumerate(self._status_callbacks):
            if cb == callback:
                self._status_callbacks.pop(i)
                return True
        return False
    
    def update_status(self, new_status: SessionStatus) -> None:
        """
        Update session status and trigger registered callbacks.
        
        Args:
            new_status: The new session status
            
        Example:
            ```python
            # This will trigger any registered status callbacks
            session.update_status(SessionStatus.ACTIVE)
            ```
        """
        if self.status != new_status:
            old_status = self.status
            self.status = new_status
            self.update_activity()
            
            # Execute status change callbacks
            self._execute_status_callbacks(old_status, new_status)
    
    def _execute_status_callbacks(self, old_status: SessionStatus, new_status: SessionStatus) -> None:
        """Execute status change callbacks with error isolation."""
        logger = logging.getLogger(__name__)
        
        for priority, callback in self._status_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    # For async callbacks, create a task if there's a running event loop
                    try:
                        asyncio.create_task(callback(old_status, new_status, self))
                    except RuntimeError:
                        # No event loop running, skip async callback
                        logger.warning(f"Skipping async status callback due to no event loop")
                else:
                    callback(old_status, new_status, self)
            except Exception as e:
                logger.error(f"Error in status callback: {e}", exc_info=True) 