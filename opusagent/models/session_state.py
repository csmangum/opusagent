"""Session state models for persistent session management.

This module defines the data models for session state persistence,
including session metadata, conversation context, and state tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum


class SessionStatus(Enum):
    """Session status enumeration."""
    INITIATED = "initiated"
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    ERROR = "error"


@dataclass
class SessionState:
    """Comprehensive session state model.
    
    This model tracks all the information needed to restore a session,
    including conversation context, audio state, and function calls.
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
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
        """Create from dictionary."""
        # Convert hex strings back to bytes for audio buffer
        audio_buffer = [bytes.fromhex(chunk) for chunk in data.get("audio_buffer", [])]
        
        return cls(
            conversation_id=data["conversation_id"],
            session_id=data.get("session_id"),
            bridge_type=data.get("bridge_type", "audiocodes"),
            bot_name=data.get("bot_name", "voice-bot"),
            caller=data.get("caller", "unknown"),
            media_format=data.get("media_format", "raw/lpcm16"),
            status=SessionStatus(data.get("status", "initiated")),
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
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def increment_resume_count(self):
        """Increment resume count and update status."""
        self.resumed_count += 1
        self.status = SessionStatus.ACTIVE
        self.update_activity()
    
    def add_conversation_item(self, item: Dict[str, Any]):
        """Add item to conversation history."""
        self.conversation_history.append(item)
        self.current_turn += 1
        self.update_activity()
    
    def add_function_call(self, function_call: Dict[str, Any]):
        """Add function call to history."""
        self.function_calls.append(function_call)
        self.update_activity()
    
    def set_error(self, error_message: str):
        """Set error state."""
        self.last_error = error_message
        self.error_count += 1
        self.status = SessionStatus.ERROR
        self.update_activity()
    
    def is_expired(self, max_age_seconds: int = 3600) -> bool:
        """Check if session is expired."""
        age = (datetime.now() - self.last_activity).total_seconds()
        return age > max_age_seconds
    
    def can_resume(self, max_age_seconds: Optional[int] = None) -> bool:
        """Check if session can be resumed.
        
        Args:
            max_age_seconds: Optional maximum age in seconds before session is considered expired
            
        Returns:
            True if session can be resumed, False otherwise
        """
        # Check status
        if self.status in [SessionStatus.ENDED, SessionStatus.ERROR]:
            return False
            
        # Check expiration if max_age_seconds is provided
        if max_age_seconds is not None and self.is_expired(max_age_seconds):
            return False
            
        return True 