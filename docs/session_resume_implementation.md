# Session Resume Implementation

## Overview

The session resume functionality enables persistent conversation state across session interruptions, allowing users to seamlessly continue conversations after network disconnections, system restarts, or other interruptions. This implementation provides a robust, scalable solution for maintaining conversation context, function call history, and audio state.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Session Resume System                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Session Storage │  │ Session Manager │  │ Bridge Layer │ │
│  │   Interface     │  │    Service      │  │ Integration  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│           │                     │                    │       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Memory Storage  │  │ Session State   │  │ AudioCodes   │ │
│  │   (Dev/Test)    │  │    Models       │  │   Bridge     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│           │                     │                    │       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Redis Storage   │  │ Transcript      │  │ Function     │ │
│  │  (Production)   │  │   Manager       │  │  Handler     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Session Creation**: When a conversation starts, session state is created and stored
2. **State Persistence**: Conversation context, function calls, and metadata are continuously updated
3. **Session Resume**: When a resume request is received, the system:
   - Retrieves session state from storage
   - Validates session can be resumed
   - Restores conversation context to components
   - Increments resume count
4. **Fallback**: If resume fails, creates a new session

## Components

### 1. Session Storage Interface

**File**: `opusagent/session_storage.py`

Abstract interface defining the contract for session state storage:

```python
class SessionStorage(ABC):
    @abstractmethod
    async def store_session(self, conversation_id: str, session_data: Dict[str, Any]) -> bool
    
    @abstractmethod
    async def retrieve_session(self, conversation_id: str) -> Optional[Dict[str, Any]]
    
    @abstractmethod
    async def delete_session(self, conversation_id: str) -> bool
    
    @abstractmethod
    async def list_active_sessions(self) -> List[str]
    
    @abstractmethod
    async def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> int
```

### 2. Memory Storage Implementation

**File**: `opusagent/session_storage/memory_storage.py`

In-memory storage for development and testing:

**Features**:
- In-memory storage with automatic cleanup
- Configurable session limits and cleanup intervals
- Thread-safe operations
- Background cleanup task

**Usage**:
```python
from opusagent.session_storage.memory_storage import MemorySessionStorage

storage = MemorySessionStorage(
    max_sessions=1000,
    cleanup_interval=300  # 5 minutes
)
```

### 3. Redis Storage Implementation

**File**: `opusagent/session_storage/redis_storage.py`

Production-ready Redis storage with high availability:

**Features**:
- Connection pooling and automatic reconnection
- Configurable TTL and session expiration
- Background cleanup tasks
- Error handling and graceful degradation

**Usage**:
```python
from opusagent.session_storage.redis_storage import RedisSessionStorage

storage = RedisSessionStorage(
    redis_url="redis://localhost:6379",
    session_prefix="opusagent:session:",
    default_ttl=3600,  # 1 hour
    max_connections=10
)
```

### 4. Session State Model

**File**: `opusagent/models/session_state.py`

Comprehensive session state model:

```python
@dataclass
class SessionState:
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
    function_calls: List[Dict[str, Any]] = field(default_factory=list)
    
    # Audio state
    audio_buffer: List[bytes] = field(default_factory=list)
    
    # OpenAI Realtime API state
    openai_session_id: Optional[str] = None
    active_response_id: Optional[str] = None
```

### 5. Session Manager Service

**File**: `opusagent/services/session_manager_service.py`

Centralized session management service:

**Key Methods**:
- `create_session()`: Create new session
- `resume_session()`: Resume existing session
- `update_session()`: Update session state
- `end_session()`: End session gracefully
- `validate_session()`: Validate session for resume

**Usage**:
```python
from opusagent.services.session_manager_service import SessionManagerService

service = SessionManagerService(storage)

# Create session
session = await service.create_session("conversation-123")

# Resume session
resumed_session = await service.resume_session("conversation-123")
```

### 6. Bridge Integration

**File**: `opusagent/bridges/base_bridge.py`

Updated base bridge with session management integration:

**Key Changes**:
- Session manager service initialization
- Session state restoration in `initialize_conversation()`
- Automatic session state updates

**Session Resume Flow**:
```python
async def initialize_conversation(self, conversation_id: Optional[str] = None):
    self.conversation_id = conversation_id or str(uuid.uuid4())
    
    # Try to resume existing session
    if self.session_manager_service:
        self.session_state = await self.session_manager_service.resume_session(self.conversation_id)
        
        if self.session_state:
            # Resume existing session
            await self._restore_session_state()
            logger.info(f"Resumed session: {self.conversation_id}")
        else:
            # Create new session
            self.session_state = await self.session_manager_service.create_session(
                conversation_id=self.conversation_id,
                bridge_type=self.bridge_type
            )
```

### 7. Component Restoration

#### Transcript Manager Restoration

**File**: `opusagent/transcript_manager.py`

Added methods for conversation context restoration:

```python
def restore_conversation_context(self, conversation_history: List[Dict[str, Any]]) -> None:
    """Restore conversation context from session state."""
    
def get_conversation_context(self) -> List[Dict[str, Any]]:
    """Get current conversation context for session state storage."""
    
def clear_conversation_context(self) -> None:
    """Clear all conversation context buffers."""
```

#### Function Handler Restoration

**File**: `opusagent/function_handler.py`

Added methods for function call state restoration:

```python
def restore_function_calls(self, function_calls: List[Dict[str, Any]]) -> None:
    """Restore function call state from session state."""
    
def get_function_call_history(self) -> List[Dict[str, Any]]:
    """Get function call history for session state storage."""
    
def clear_function_call_history(self) -> None:
    """Clear all function call history."""
```

## Usage Examples

### Basic Session Resume

```python
import asyncio
from opusagent.session_storage.memory_storage import MemorySessionStorage
from opusagent.services.session_manager_service import SessionManagerService
from opusagent.models.session_state import SessionState, SessionStatus

async def basic_session_resume():
    # Initialize storage and service
    storage = MemorySessionStorage()
    service = SessionManagerService(storage)
    
    # Create session
    session = await service.create_session(
        "conversation-123",
        status=SessionStatus.ACTIVE,
        media_format="pcm16"
    )
    
    # Add conversation context
    session.conversation_history = [
        {"type": "input", "text": "Hello, I need help"},
        {"type": "output", "text": "Hi! How can I assist you?"}
    ]
    
    # Store session
    await storage.store_session("conversation-123", session.to_dict())
    
    # Resume session
    resumed_session = await service.resume_session("conversation-123")
    print(f"Resumed session with {len(resumed_session.conversation_history)} items")

asyncio.run(basic_session_resume())
```

### Production Redis Setup

```python
import asyncio
import os
from opusagent.session_storage.redis_storage import RedisSessionStorage
from opusagent.services.session_manager_service import SessionManagerService

async def production_session_resume():
    # Redis configuration
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Initialize Redis storage
    redis_storage = RedisSessionStorage(
        redis_url=redis_url,
        session_prefix="opusagent:session:",
        default_ttl=3600,  # 1 hour
        max_connections=10
    )
    
    # Initialize service
    service = SessionManagerService(redis_storage)
    await service.start()
    
    try:
        # Create and resume sessions
        session = await service.create_session("prod-test-123")
        resumed = await service.resume_session("prod-test-123")
        
        print(f"Session resumed: {resumed.resumed_count} times")
        
    finally:
        await service.stop()
        await redis_storage.close()

asyncio.run(production_session_resume())
```

### Bridge Integration Example

```python
from opusagent.bridges.audiocodes_bridge import AudioCodesBridge
from opusagent.session_storage.redis_storage import RedisSessionStorage

# Initialize bridge with Redis storage
redis_storage = RedisSessionStorage(redis_url="redis://localhost:6379")
bridge = AudioCodesBridge(
    platform_websocket=websocket,
    realtime_websocket=realtime_ws,
    session_config=config,
    session_storage=redis_storage  # Custom storage
)

# Session resume happens automatically in handle_session_resume
```

## Testing

### Comprehensive Test Suite

**File**: `tests/test_session_resume.py`

The test suite covers:

1. **Session State Tests**:
   - Creation and serialization
   - Activity tracking
   - Resume counting
   - Expiration logic
   - Resume validation

2. **Storage Tests**:
   - Store and retrieve operations
   - Session deletion
   - Active session listing
   - Expired session cleanup
   - Activity updates

3. **Service Tests**:
   - Session creation and retrieval
   - Resume operations
   - Session updates and ending
   - Validation and statistics

4. **Component Tests**:
   - Transcript manager restoration
   - Function handler restoration
   - Error handling

5. **Integration Tests**:
   - Complete session resume flow
   - Session updates with context
   - Error handling scenarios

### Running Tests

```bash
# Run all session resume tests
pytest tests/test_session_resume.py -v

# Run specific test class
pytest tests/test_session_resume.py::TestSessionState -v

# Run with coverage
pytest tests/test_session_resume.py --cov=opusagent.session_storage --cov=opusagent.services
```

## Deployment Considerations

### Development Environment

For development and testing, use memory storage:

```python
from opusagent.session_storage.memory_storage import MemorySessionStorage

storage = MemorySessionStorage(
    max_sessions=1000,
    cleanup_interval=300
)
```

### Production Environment

For production, use Redis storage with proper configuration:

```python
from opusagent.session_storage.redis_storage import RedisSessionStorage

storage = RedisSessionStorage(
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
    session_prefix="opusagent:session:",
    default_ttl=3600,  # 1 hour
    max_connections=20,
    retry_on_timeout=True,
    socket_keepalive=True
)
```

### Environment Variables

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_password
REDIS_DB=0

# Session Configuration
SESSION_TTL=3600
SESSION_PREFIX=opusagent:session:
MAX_SESSIONS=10000
```

### Monitoring and Observability

The implementation includes comprehensive logging and statistics:

```python
# Get session statistics
stats = await service.get_session_stats()
print(f"Active sessions: {stats['active_sessions_count']}")

# Get storage statistics
storage_stats = storage.get_stats()
print(f"Storage type: {storage_stats['storage_type']}")
```

### Performance Considerations

1. **Connection Pooling**: Redis storage uses connection pooling for efficient resource usage
2. **Background Cleanup**: Automatic cleanup of expired sessions reduces memory usage
3. **TTL Management**: Configurable TTL prevents session accumulation
4. **Error Handling**: Graceful degradation when storage is unavailable

### Security Considerations

1. **Session Validation**: Sessions are validated before resume operations
2. **Expiration**: Automatic session expiration prevents indefinite storage
3. **Access Control**: Redis authentication and network security
4. **Data Encryption**: Consider encrypting sensitive session data

## Troubleshooting

### Common Issues

1. **Session Not Found**:
   - Check if session was properly stored
   - Verify conversation ID consistency
   - Check storage backend connectivity

2. **Redis Connection Issues**:
   - Verify Redis server is running
   - Check connection URL and credentials
   - Monitor connection pool status

3. **Session Expiration**:
   - Adjust TTL settings
   - Check last activity timestamps
   - Review cleanup intervals

### Debug Logging

Enable debug logging for detailed troubleshooting:

```python
import logging
logging.getLogger("session_manager_service").setLevel(logging.DEBUG)
logging.getLogger("memory_session_storage").setLevel(logging.DEBUG)
logging.getLogger("redis_session_storage").setLevel(logging.DEBUG)
```

### Health Checks

Implement health checks for session storage:

```python
async def health_check():
    try:
        # Test storage operations
        test_id = "health-check"
        await storage.store_session(test_id, {"test": "data"})
        retrieved = await storage.retrieve_session(test_id)
        await storage.delete_session(test_id)
        
        return {"status": "healthy", "storage": "operational"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Future Enhancements

### Planned Features

1. **Database Storage**: PostgreSQL/MySQL backend for complex queries
2. **Session Analytics**: Detailed session metrics and reporting
3. **Multi-Region Support**: Distributed session storage
4. **Session Migration**: Tools for migrating between storage backends
5. **Advanced Caching**: Redis caching layer for frequently accessed sessions

### Performance Optimizations

1. **Compression**: Compress session data to reduce storage size
2. **Batch Operations**: Batch session updates for better performance
3. **Read Replicas**: Use Redis read replicas for high availability
4. **Sharding**: Distribute sessions across multiple storage instances

## Conclusion

The session resume implementation provides a robust, scalable solution for maintaining conversation state across session interruptions. With support for multiple storage backends, comprehensive testing, and production-ready features, it enables seamless user experiences in voice AI applications.

The modular design allows for easy customization and extension, while the comprehensive test suite ensures reliability and correctness. The implementation is ready for both development and production environments, with proper error handling, monitoring, and performance considerations. 