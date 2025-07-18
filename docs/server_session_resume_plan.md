# Server-Side Session Resume Support Enhancement Plan

## Overview

This plan outlines the implementation of robust server-side session resume support for the FastAgent system. Currently, the system has basic session resume functionality but lacks proper session state persistence, restoration, and comprehensive error handling.

## Current State Analysis

### ✅ What's Already Working
- Basic `session.resume` message handling in `AudioCodesBridge`
- Client-side session resume support in `MockAudioCodesClient`
- Session resume message models and routing
- Basic session state tracking in bridges

### ❌ What's Missing
- **Session State Persistence**: No persistent storage of session state
- **State Restoration**: Cannot restore conversation context, audio buffers, or function state
- **Session Validation**: No validation of resume requests against stored sessions
- **Error Handling**: Limited error scenarios for invalid resume attempts
- **Session Cleanup**: No automatic cleanup of expired sessions
- **Multi-Bridge Support**: Session resume not consistently implemented across all bridges

## Implementation Plan

### Phase 1: Session State Persistence (Week 1)

#### 1.1 Create Session Storage Interface
```python
# opusagent/session_storage.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

class SessionStorage(ABC):
    """Abstract interface for session state storage."""
    
    @abstractmethod
    async def store_session(self, conversation_id: str, session_data: Dict[str, Any]) -> bool:
        """Store session state."""
        pass
    
    @abstractmethod
    async def retrieve_session(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session state."""
        pass
    
    @abstractmethod
    async def delete_session(self, conversation_id: str) -> bool:
        """Delete session state."""
        pass
    
    @abstractmethod
    async def list_active_sessions(self) -> List[str]:
        """List all active session IDs."""
        pass
    
    @abstractmethod
    async def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> int:
        """Clean up expired sessions."""
        pass
```

#### 1.2 Implement Memory-Based Storage
```python
# opusagent/session_storage/memory_storage.py
import asyncio
import time
from typing import Dict, Any, Optional, List
from opusagent.session_storage import SessionStorage

class MemorySessionStorage(SessionStorage):
    """In-memory session storage implementation."""
    
    def __init__(self, max_sessions: int = 1000, cleanup_interval: int = 300):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._session_timestamps: Dict[str, float] = {}
        self._max_sessions = max_sessions
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start_cleanup_task(self):
        """Start background cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Background cleanup loop."""
        while True:
            await asyncio.sleep(self._cleanup_interval)
            await self.cleanup_expired_sessions()
```

#### 1.3 Implement Redis-Based Storage (Optional)
```python
# opusagent/session_storage/redis_storage.py
import json
import asyncio
from typing import Dict, Any, Optional, List
from opusagent.session_storage import SessionStorage

class RedisSessionStorage(SessionStorage):
    """Redis-based session storage implementation."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._redis = None
        
    async def _get_redis(self):
        """Get Redis connection."""
        if self._redis is None:
            import aioredis
            self._redis = await aioredis.from_url(self.redis_url)
        return self._redis
```

### Phase 2: Enhanced Session State Management (Week 1-2)

#### 2.1 Create Comprehensive Session State Model
```python
# opusagent/models/session_state.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

class SessionStatus(Enum):
    INITIATED = "initiated"
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    ERROR = "error"

@dataclass
class SessionState:
    """Comprehensive session state model."""
    
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
```

#### 2.2 Create Session Manager Service
```python
# opusagent/services/session_manager_service.py
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from opusagent.session_storage import SessionStorage
from opusagent.models.session_state import SessionState, SessionStatus
from opusagent.config.logging_config import configure_logging

logger = configure_logging("session_manager_service")

class SessionManagerService:
    """Centralized session management service."""
    
    def __init__(self, storage: SessionStorage):
        self.storage = storage
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the session manager service."""
        if hasattr(self.storage, 'start_cleanup_task'):
            await self.storage.start_cleanup_task()
        logger.info("Session manager service started")
    
    async def stop(self):
        """Stop the session manager service."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("Session manager service stopped")
    
    async def create_session(self, conversation_id: str, **kwargs) -> SessionState:
        """Create a new session."""
        session_state = SessionState(conversation_id=conversation_id, **kwargs)
        await self.storage.store_session(conversation_id, session_state.to_dict())
        logger.info(f"Created session: {conversation_id}")
        return session_state
    
    async def get_session(self, conversation_id: str) -> Optional[SessionState]:
        """Retrieve a session by conversation ID."""
        session_data = await self.storage.retrieve_session(conversation_id)
        if session_data:
            session_state = SessionState.from_dict(session_data)
            # Update last activity
            session_state.last_activity = datetime.now()
            await self.storage.store_session(conversation_id, session_state.to_dict())
            return session_state
        return None
    
    async def update_session(self, conversation_id: str, **updates) -> bool:
        """Update session state."""
        session_state = await self.get_session(conversation_id)
        if not session_state:
            return False
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(session_state, key):
                setattr(session_state, key, value)
        
        session_state.last_activity = datetime.now()
        await self.storage.store_session(conversation_id, session_state.to_dict())
        return True
    
    async def resume_session(self, conversation_id: str) -> Optional[SessionState]:
        """Resume an existing session."""
        session_state = await self.get_session(conversation_id)
        if not session_state:
            return None
        
        # Validate session can be resumed
        if session_state.status == SessionStatus.ENDED:
            logger.warning(f"Cannot resume ended session: {conversation_id}")
            return None
        
        # Update resume count and status
        session_state.resumed_count += 1
        session_state.status = SessionStatus.ACTIVE
        session_state.last_activity = datetime.now()
        
        await self.storage.store_session(conversation_id, session_state.to_dict())
        logger.info(f"Resumed session: {conversation_id} (resume #{session_state.resumed_count})")
        return session_state
    
    async def end_session(self, conversation_id: str, reason: str = "normal") -> bool:
        """End a session."""
        session_state = await self.get_session(conversation_id)
        if not session_state:
            return False
        
        session_state.status = SessionStatus.ENDED
        session_state.last_activity = datetime.now()
        session_state.metadata["end_reason"] = reason
        
        await self.storage.store_session(conversation_id, session_state.to_dict())
        logger.info(f"Ended session: {conversation_id} - {reason}")
        return True
    
    async def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up expired sessions."""
        max_age = timedelta(hours=max_age_hours)
        cutoff_time = datetime.now() - max_age
        
        active_sessions = await self.storage.list_active_sessions()
        cleaned_count = 0
        
        for conversation_id in active_sessions:
            session_state = await self.get_session(conversation_id)
            if session_state and session_state.last_activity < cutoff_time:
                await self.storage.delete_session(conversation_id)
                cleaned_count += 1
                logger.info(f"Cleaned up expired session: {conversation_id}")
        
        return cleaned_count
```

### Phase 3: Enhanced Bridge Integration (Week 2)

#### 3.1 Update BaseRealtimeBridge
```python
# opusagent/bridges/base_bridge.py
# Add to BaseRealtimeBridge class

def __init__(self, ...):
    # ... existing initialization ...
    
    # Add session manager service
    self.session_manager_service = get_session_manager_service()
    self.session_state: Optional[SessionState] = None

async def initialize_conversation(self, conversation_id: str):
    """Initialize conversation with session state management."""
    # Try to resume existing session
    self.session_state = await self.session_manager_service.resume_session(conversation_id)
    
    if self.session_state:
        # Resume existing session
        await self._restore_session_state()
        logger.info(f"Resumed session: {conversation_id}")
    else:
        # Create new session
        self.session_state = await self.session_manager_service.create_session(
            conversation_id=conversation_id,
            bridge_type=self.bridge_type,
            bot_name=getattr(self, 'bot_name', 'voice-bot'),
            caller=getattr(self, 'caller', 'unknown'),
            media_format=self.media_format or "raw/lpcm16"
        )
        logger.info(f"Created new session: {conversation_id}")

async def _restore_session_state(self):
    """Restore session state from storage."""
    if not self.session_state:
        return
    
    # Restore conversation ID
    self.conversation_id = self.session_state.conversation_id
    
    # Restore media format
    if self.session_state.media_format:
        self.media_format = self.session_state.media_format
    
    # Restore OpenAI session state if available
    if self.session_state.openai_session_id:
        # Reconnect to OpenAI with existing session
        await self._restore_openai_session()
    
    # Restore conversation context
    if self.session_state.conversation_history:
        await self._restore_conversation_context()
    
    # Restore function calls state
    if self.session_state.function_calls:
        await self._restore_function_state()

async def _restore_openai_session(self):
    """Restore OpenAI Realtime API session."""
    if not self.session_state or not self.session_state.openai_session_id:
        return
    
    try:
        # Attempt to restore OpenAI session
        # This would require OpenAI API support for session restoration
        logger.info(f"Restoring OpenAI session: {self.session_state.openai_session_id}")
        # Implementation depends on OpenAI API capabilities
    except Exception as e:
        logger.warning(f"Failed to restore OpenAI session: {e}")
        # Fall back to new session
        await self.session_manager.initialize_session()

async def _restore_conversation_context(self):
    """Restore conversation context."""
    if not self.session_state or not self.session_state.conversation_history:
        return
    
    # Restore conversation history to transcript manager
    for item in self.session_state.conversation_history:
        await self.transcript_manager.add_conversation_item(item)

async def _restore_function_state(self):
    """Restore function call state."""
    if not self.session_state or not self.session_state.function_calls:
        return
    
    # Restore function call history
    for function_call in self.session_state.function_calls:
        await self.function_handler.restore_function_call(function_call)

async def _save_session_state(self):
    """Save current session state."""
    if not self.session_state:
        return
    
    # Update session state with current information
    self.session_state.conversation_history = await self.transcript_manager.get_conversation_history()
    self.session_state.function_calls = self.function_handler.get_function_calls()
    self.session_state.audio_buffer = self.audio_handler.get_audio_buffer()
    self.session_state.openai_session_id = getattr(self.session_manager, 'session_id', None)
    self.session_state.active_response_id = getattr(self.realtime_handler, 'response_id_tracker', None)
    
    # Save to storage
    await self.session_manager_service.update_session(
        self.session_state.conversation_id,
        **self.session_state.__dict__
    )

async def close(self):
    """Close bridge with session state preservation."""
    if self.session_state:
        # Save final state before closing
        await self._save_session_state()
        
        # Mark session as ended
        await self.session_manager_service.end_session(
            self.session_state.conversation_id,
            reason="bridge_closed"
        )
    
    await super().close()
```

#### 3.2 Update AudioCodesBridge
```python
# opusagent/bridges/audiocodes_bridge.py
# Update handle_session_resume method

async def handle_session_resume(self, data: dict):
    """Handle session resume from AudioCodes."""
    logger.info(f"Session resume received: {data}")
    conversation_id = data.get("conversationId")
    self.media_format = data.get("supportedMediaFormats", ["raw/lpcm16"])[0]

    # Initialize conversation (will attempt resume)
    await self.initialize_conversation(conversation_id)
    
    if self.session_state and self.session_state.resumed_count > 0:
        # Successfully resumed
        await self.send_session_resumed()
        logger.info(f"Session resumed successfully: {conversation_id}")
    else:
        # Failed to resume, treat as new session
        await self.send_session_accepted()
        logger.info(f"Session resume failed, created new session: {conversation_id}")

async def send_session_resumed(self):
    """Send AudioCodes-specific session resumed response."""
    kwargs = {
        "type": "session.resumed",  # Use correct message type
        "conversationId": self.conversation_id,
        "mediaFormat": self.media_format or "raw/lpcm16",
        "participant": self.current_participant,
    }
    await self.send_platform_json(kwargs)
    logger.info("✅ Session resumed response sent to AudioCodes")
```

### Phase 4: Error Handling and Validation (Week 2-3)

#### 4.1 Enhanced Error Handling
```python
# opusagent/bridges/audiocodes_bridge.py
# Add error handling methods

async def handle_session_resume_error(self, conversation_id: str, error_reason: str):
    """Handle session resume errors."""
    error_message = {
        "type": "session.error",
        "conversationId": conversation_id,
        "reason": error_reason,
        "errorCode": "RESUME_FAILED"
    }
    await self.send_platform_json(error_message)
    logger.error(f"Session resume error sent: {error_reason}")

async def validate_session_resume(self, conversation_id: str) -> tuple[bool, str]:
    """Validate session resume request."""
    # Check if session exists
    session_state = await self.session_manager_service.get_session(conversation_id)
    if not session_state:
        return False, "Session not found"
    
    # Check if session is ended
    if session_state.status == SessionStatus.ENDED:
        return False, "Session already ended"
    
    # Check if session is too old (configurable)
    max_resume_age = timedelta(hours=24)  # Configurable
    if datetime.now() - session_state.last_activity > max_resume_age:
        return False, "Session too old to resume"
    
    # Check resume count limit
    max_resumes = 10  # Configurable
    if session_state.resumed_count >= max_resumes:
        return False, "Maximum resume attempts exceeded"
    
    return True, "Valid resume request"
```

#### 4.2 Session Resume Validation in Bridge
```python
# opusagent/bridges/audiocodes_bridge.py
# Update handle_session_resume with validation

async def handle_session_resume(self, data: dict):
    """Handle session resume from AudioCodes with validation."""
    logger.info(f"Session resume received: {data}")
    conversation_id = data.get("conversationId")
    self.media_format = data.get("supportedMediaFormats", ["raw/lpcm16"])[0]

    # Validate resume request
    is_valid, error_reason = await self.validate_session_resume(conversation_id)
    if not is_valid:
        await self.handle_session_resume_error(conversation_id, error_reason)
        return

    try:
        # Initialize conversation (will attempt resume)
        await self.initialize_conversation(conversation_id)
        
        if self.session_state and self.session_state.resumed_count > 0:
            # Successfully resumed
            await self.send_session_resumed()
            logger.info(f"Session resumed successfully: {conversation_id}")
        else:
            # Failed to resume, treat as new session
            await self.send_session_accepted()
            logger.info(f"Session resume failed, created new session: {conversation_id}")
            
    except Exception as e:
        logger.error(f"Error during session resume: {e}")
        await self.handle_session_resume_error(conversation_id, "Internal server error")
```

### Phase 5: Configuration and Monitoring (Week 3)

#### 5.1 Session Configuration
```python
# opusagent/config/session_config.py
from dataclasses import dataclass
from typing import Optional
from datetime import timedelta

@dataclass
class SessionConfig:
    """Session management configuration."""
    
    # Storage settings
    storage_type: str = "memory"  # "memory" or "redis"
    redis_url: Optional[str] = None
    
    # Session limits
    max_sessions: int = 1000
    max_session_age_hours: int = 24
    max_resume_attempts: int = 10
    max_resume_age_hours: int = 24
    
    # Cleanup settings
    cleanup_interval_seconds: int = 300  # 5 minutes
    cleanup_batch_size: int = 100
    
    # Memory storage settings
    memory_max_sessions: int = 1000
    
    # Monitoring
    enable_metrics: bool = True
    metrics_interval_seconds: int = 60
```

#### 5.2 Session Monitoring and Metrics
```python
# opusagent/services/session_monitor.py
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from opusagent.services.session_manager_service import SessionManagerService
from opusagent.config.logging_config import configure_logging

logger = configure_logging("session_monitor")

class SessionMonitor:
    """Monitor session activity and health."""
    
    def __init__(self, session_manager: SessionManagerService):
        self.session_manager = session_manager
        self._monitor_task: Optional[asyncio.Task] = None
        self._metrics: Dict[str, Any] = {}
    
    async def start_monitoring(self):
        """Start session monitoring."""
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Session monitoring started")
    
    async def _monitor_loop(self):
        """Monitoring loop."""
        while True:
            try:
                await self._collect_metrics()
                await self._log_metrics()
                await asyncio.sleep(60)  # Collect metrics every minute
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _collect_metrics(self):
        """Collect session metrics."""
        active_sessions = await self.session_manager.storage.list_active_sessions()
        
        self._metrics = {
            "timestamp": datetime.now().isoformat(),
            "active_sessions": len(active_sessions),
            "total_sessions": len(active_sessions),
            "resumed_sessions": 0,
            "failed_resumes": 0,
            "cleanup_count": 0,
        }
        
        # Collect detailed metrics
        for conversation_id in active_sessions:
            session_state = await self.session_manager.get_session(conversation_id)
            if session_state:
                if session_state.resumed_count > 0:
                    self._metrics["resumed_sessions"] += 1
    
    async def _log_metrics(self):
        """Log collected metrics."""
        logger.info(f"Session metrics: {self._metrics}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return self._metrics.copy()
```

### Phase 6: Testing and Validation (Week 3-4)

#### 6.1 Comprehensive Test Suite
```python
# tests/test_session_resume.py
import pytest
import asyncio
from datetime import datetime, timedelta

from opusagent.services.session_manager_service import SessionManagerService
from opusagent.session_storage.memory_storage import MemorySessionStorage
from opusagent.models.session_state import SessionState, SessionStatus

class TestSessionResume:
    """Test session resume functionality."""
    
    @pytest.fixture
    async def session_manager(self):
        """Create session manager for testing."""
        storage = MemorySessionStorage()
        manager = SessionManagerService(storage)
        await manager.start()
        yield manager
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_session_creation_and_resume(self, session_manager):
        """Test basic session creation and resume."""
        # Create session
        session = await session_manager.create_session("test-123")
        assert session.conversation_id == "test-123"
        assert session.status == SessionStatus.INITIATED
        
        # Resume session
        resumed_session = await session_manager.resume_session("test-123")
        assert resumed_session is not None
        assert resumed_session.resumed_count == 1
        assert resumed_session.status == SessionStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_session_validation(self, session_manager):
        """Test session resume validation."""
        # Create session
        await session_manager.create_session("test-123")
        
        # Test valid resume
        is_valid, reason = await session_manager.validate_session_resume("test-123")
        assert is_valid
        assert reason == "Valid resume request"
        
        # Test non-existent session
        is_valid, reason = await session_manager.validate_session_resume("non-existent")
        assert not is_valid
        assert "not found" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_session_cleanup(self, session_manager):
        """Test session cleanup."""
        # Create old session
        old_session = await session_manager.create_session("old-123")
        old_session.last_activity = datetime.now() - timedelta(hours=25)
        await session_manager.storage.store_session("old-123", old_session.to_dict())
        
        # Create recent session
        recent_session = await session_manager.create_session("recent-123")
        
        # Run cleanup
        cleaned_count = await session_manager.cleanup_expired_sessions(max_age_hours=24)
        assert cleaned_count == 1
        
        # Verify old session is gone
        old_session_retrieved = await session_manager.get_session("old-123")
        assert old_session_retrieved is None
        
        # Verify recent session still exists
        recent_session_retrieved = await session_manager.get_session("recent-123")
        assert recent_session_retrieved is not None
```

#### 6.2 Integration Tests
```python
# tests/integration/test_session_resume_integration.py
import pytest
import asyncio
from opusagent.mock.mock_audiocodes_client import MockAudioCodesClient

class TestSessionResumeIntegration:
    """Integration tests for session resume."""
    
    @pytest.mark.asyncio
    async def test_full_session_resume_flow(self):
        """Test complete session resume flow."""
        bridge_url = "ws://localhost:8000/caller-agent"
        
        # Create initial session
        async with MockAudioCodesClient(bridge_url) as client:
            # Initiate session
            success = await client.initiate_session()
            assert success
            
            conversation_id = client.conversation_id
            assert conversation_id is not None
            
            # End session
            await client.end_session("Testing resume")
        
        # Resume session
        async with MockAudioCodesClient(bridge_url) as client:
            # Resume session
            resume_success = await client.resume_session(conversation_id)
            assert resume_success
            
            # Verify session state
            status = client.get_session_status()
            assert status["session_resumed"] is True
            assert status["conversation_id"] == conversation_id
```

### Phase 7: Documentation and Deployment (Week 4)

#### 7.1 Update Documentation
- Update `docs/telephony_realtime_bridge.md` with session resume details
- Create `docs/session_resume_guide.md` for developers
- Update API documentation with new session resume endpoints

#### 7.2 Configuration Examples
```python
# Example configuration for session resume
SESSION_CONFIG = {
    "storage_type": "memory",  # or "redis"
    "redis_url": "redis://localhost:6379",  # if using Redis
    "max_sessions": 1000,
    "max_session_age_hours": 24,
    "max_resume_attempts": 10,
    "cleanup_interval_seconds": 300,
    "enable_metrics": True,
}
```

## Implementation Timeline

### Week 1: Foundation
- [ ] Create session storage interface and implementations
- [ ] Implement comprehensive session state model
- [ ] Create session manager service

### Week 2: Bridge Integration
- [ ] Update BaseRealtimeBridge with session management
- [ ] Enhance AudioCodesBridge session resume handling
- [ ] Implement session state restoration

### Week 3: Error Handling and Monitoring
- [ ] Add comprehensive error handling
- [ ] Implement session validation
- [ ] Create session monitoring and metrics

### Week 4: Testing and Documentation
- [ ] Write comprehensive test suite
- [ ] Create integration tests
- [ ] Update documentation
- [ ] Deploy and validate

## Success Metrics

1. **Functionality**: 100% session resume success rate for valid sessions
2. **Performance**: <100ms session resume time
3. **Reliability**: 99.9% uptime for session storage
4. **Scalability**: Support for 1000+ concurrent sessions
5. **Monitoring**: Real-time visibility into session health

## Risk Mitigation

1. **Backward Compatibility**: Maintain existing API while adding new features
2. **Graceful Degradation**: Fall back to new session creation if resume fails
3. **Data Loss Prevention**: Implement session state backup and recovery
4. **Performance Impact**: Monitor and optimize session storage operations
5. **Security**: Validate session ownership and implement access controls

## Future Enhancements

1. **Distributed Session Storage**: Support for Redis cluster or database storage
2. **Session Migration**: Move sessions between different bridge instances
3. **Advanced State Restoration**: Restore complex conversation context and function state
4. **Session Analytics**: Detailed analytics on session patterns and performance
5. **Multi-Tenant Support**: Session isolation for different customers or environments 