"""Comprehensive tests for session resume functionality.

This module tests the complete session resume system including:
- Session storage (memory and Redis)
- Session state models
- Session manager service
- Bridge integration
- Conversation context restoration
- Function call restoration
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import time

from opusagent.session_storage.memory_storage import MemorySessionStorage
from opusagent.models.session_state import SessionState, SessionStatus
from opusagent.services.session_manager_service import SessionManagerService
from opusagent.handlers.transcript_manager import TranscriptManager
from opusagent.handlers.function_handler import FunctionHandler


class TestSessionState:
    """Test session state model functionality."""
    
    def test_session_state_creation(self):
        """Test creating a new session state."""
        session = SessionState(
            conversation_id="test-123",
            status=SessionStatus.ACTIVE,
            media_format="pcm16"
        )
        
        assert session.conversation_id == "test-123"
        assert session.status == SessionStatus.ACTIVE
        assert session.media_format == "pcm16"
        assert session.resumed_count == 0
        assert session.created_at is not None
    
    def test_session_state_serialization(self):
        """Test session state serialization and deserialization."""
        session = SessionState(
            conversation_id="test-123",
            status=SessionStatus.ACTIVE,
            media_format="pcm16"
        )
        
        # Add some test data
        session.conversation_history = [
            {"type": "input", "text": "Hello"},
            {"type": "output", "text": "Hi there!"}
        ]
        session.function_calls = [
            {"call_id": "func-1", "function_name": "test_func"}
        ]
        
        # Serialize
        session_dict = session.to_dict()
        
        # Deserialize
        restored_session = SessionState.from_dict(session_dict)
        
        assert restored_session.conversation_id == session.conversation_id
        assert restored_session.status == session.status
        assert restored_session.media_format == session.media_format
        assert len(restored_session.conversation_history) == 2
        assert len(restored_session.function_calls) == 1
    
    def test_session_state_activity_tracking(self):
        """Test session activity tracking."""
        session = SessionState(conversation_id="test-123")
        
        original_activity = session.last_activity
        import time
        time.sleep(0.001)  # Small delay to ensure timestamp difference
        session.update_activity()
        
        assert session.last_activity > original_activity
    
    def test_session_state_resume_counting(self):
        """Test session resume counting."""
        session = SessionState(conversation_id="test-123")
        
        assert session.resumed_count == 0
        session.increment_resume_count()
        assert session.resumed_count == 1
        session.increment_resume_count()
        assert session.resumed_count == 2
    
    def test_session_state_expiration(self):
        """Test session expiration logic."""
        session = SessionState(conversation_id="test-123")
        
        # Should not be expired initially
        assert not session.is_expired()
        
        # Make it old
        session.created_at = datetime.now() - timedelta(hours=2)
        session.last_activity = datetime.now() - timedelta(hours=1)
        
        # Should be expired with 30 minute max age
        assert session.is_expired(max_age_seconds=1800)
    
    def test_session_state_resume_validation(self):
        """Test session resume validation."""
        session = SessionState(conversation_id="test-123")
        
        # Active session should be resumable
        session.status = SessionStatus.ACTIVE
        assert session.can_resume()
        
        # Ended session should not be resumable
        session.status = SessionStatus.ENDED
        assert not session.can_resume()
        
        # Expired session should not be resumable
        session.status = SessionStatus.ACTIVE
        session.created_at = datetime.now() - timedelta(hours=2)
        session.last_activity = datetime.now() - timedelta(hours=1)
        assert not session.can_resume(max_age_seconds=1800)


class TestMemorySessionStorage:
    """Test memory-based session storage."""
    
    @pytest.fixture
    def storage(self):
        """Create a memory storage instance."""
        return MemorySessionStorage()
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_session(self, storage):
        """Test storing and retrieving a session."""
        conversation_id = "test-123"
        session_data = {
            "conversation_id": conversation_id,
            "status": "active",
            "media_format": "pcm16"
        }
        
        # Store session
        success = await storage.store_session(conversation_id, session_data)
        assert success
        
        # Retrieve session
        retrieved = await storage.retrieve_session(conversation_id)
        assert retrieved is not None
        assert retrieved["conversation_id"] == conversation_id
        assert retrieved["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_delete_session(self, storage):
        """Test deleting a session."""
        conversation_id = "test-123"
        session_data = {"conversation_id": conversation_id}
        
        # Store session
        await storage.store_session(conversation_id, session_data)
        
        # Verify it exists
        retrieved = await storage.retrieve_session(conversation_id)
        assert retrieved is not None
        
        # Delete session
        success = await storage.delete_session(conversation_id)
        assert success
        
        # Verify it's gone
        retrieved = await storage.retrieve_session(conversation_id)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_list_active_sessions(self, storage):
        """Test listing active sessions."""
        # Store multiple sessions
        await storage.store_session("test-1", {"conversation_id": "test-1"})
        await storage.store_session("test-2", {"conversation_id": "test-2"})
        await storage.store_session("test-3", {"conversation_id": "test-3"})
        
        # List active sessions
        active_sessions = await storage.list_active_sessions()
        assert len(active_sessions) == 3
        assert "test-1" in active_sessions
        assert "test-2" in active_sessions
        assert "test-3" in active_sessions
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, storage):
        """Test cleaning up expired sessions."""
        # Store sessions with different ages
        await storage.store_session("recent", {"conversation_id": "recent"})
        await storage.store_session("old", {"conversation_id": "old"})
        
        # Manually age the old session by updating its timestamp
        storage._session_timestamps["old"] = time.time() - 7200  # 2 hours ago
        
        # Clean up expired sessions (1 hour max age)
        cleaned = await storage.cleanup_expired_sessions(max_age_seconds=3600)
        assert cleaned == 1
        
        # Verify old session is gone
        active_sessions = await storage.list_active_sessions()
        assert "old" not in active_sessions
        assert "recent" in active_sessions
    
    @pytest.mark.asyncio
    async def test_update_session_activity(self, storage):
        """Test updating session activity."""
        conversation_id = "test-123"
        session_data = {"conversation_id": conversation_id}
        
        # Store session
        await storage.store_session(conversation_id, session_data)
        
        # Get original activity time
        original_activity = storage._sessions[conversation_id]["last_activity"]
        
        # Update activity
        await asyncio.sleep(0.1)  # Small delay to ensure time difference
        success = await storage.update_session_activity(conversation_id)
        assert success
        
        # Verify activity was updated
        updated_activity = storage._sessions[conversation_id]["last_activity"]
        assert updated_activity > original_activity


class TestSessionManagerService:
    """Test session manager service."""
    
    @pytest.fixture
    def storage(self):
        """Create a memory storage instance."""
        return MemorySessionStorage()
    
    @pytest.fixture
    def service(self, storage):
        """Create a session manager service instance."""
        return SessionManagerService(storage)
    
    @pytest.mark.asyncio
    async def test_create_session(self, service):
        """Test creating a new session."""
        conversation_id = "test-123"
        
        session = await service.create_session(
            conversation_id,
            status=SessionStatus.ACTIVE,
            media_format="pcm16"
        )
        
        assert session.conversation_id == conversation_id
        assert session.status == SessionStatus.ACTIVE
        assert session.media_format == "pcm16"
    
    @pytest.mark.asyncio
    async def test_get_session(self, service):
        """Test retrieving a session."""
        conversation_id = "test-123"
        
        # Create session
        created_session = await service.create_session(conversation_id)
        
        # Retrieve session
        retrieved_session = await service.get_session(conversation_id)
        
        assert retrieved_session is not None
        assert retrieved_session.conversation_id == conversation_id
        assert retrieved_session.resumed_count == created_session.resumed_count
    
    @pytest.mark.asyncio
    async def test_resume_session(self, service):
        """Test resuming a session."""
        conversation_id = "test-123"
        
        # Create session
        await service.create_session(conversation_id, status=SessionStatus.ACTIVE)
        
        # Resume session
        resumed_session = await service.resume_session(conversation_id)
        
        assert resumed_session is not None
        assert resumed_session.resumed_count == 1
        assert resumed_session.status == SessionStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_resume_nonexistent_session(self, service):
        """Test resuming a session that doesn't exist."""
        conversation_id = "nonexistent"
        
        resumed_session = await service.resume_session(conversation_id)
        
        assert resumed_session is None
    
    @pytest.mark.asyncio
    async def test_resume_ended_session(self, service):
        """Test resuming an ended session."""
        conversation_id = "test-123"
        
        # Create and end session
        await service.create_session(conversation_id, status=SessionStatus.ACTIVE)
        await service.end_session(conversation_id, "Test end")
        
        # Try to resume
        resumed_session = await service.resume_session(conversation_id)
        
        assert resumed_session is None
    
    @pytest.mark.asyncio
    async def test_update_session(self, service):
        """Test updating session state."""
        conversation_id = "test-123"
        
        # Create session
        await service.create_session(conversation_id)
        
        # Update session
        success = await service.update_session(
            conversation_id,
            media_format="opus",
            status=SessionStatus.PAUSED
        )
        
        assert success
        
        # Verify updates
        session = await service.get_session(conversation_id)
        assert session.media_format == "opus"
        assert session.status == SessionStatus.PAUSED
    
    @pytest.mark.asyncio
    async def test_end_session(self, service):
        """Test ending a session."""
        conversation_id = "test-123"
        
        # Create session
        await service.create_session(conversation_id)
        
        # End session
        success = await service.end_session(conversation_id, "Test completion")
        
        assert success
        
        # Verify session is ended
        session = await service.get_session(conversation_id)
        assert session.status == SessionStatus.ENDED
        assert session.metadata["end_reason"] == "Test completion"
    
    @pytest.mark.asyncio
    async def test_delete_session(self, service):
        """Test deleting a session."""
        conversation_id = "test-123"
        
        # Create session
        await service.create_session(conversation_id)
        
        # Verify it exists
        session = await service.get_session(conversation_id)
        assert session is not None
        
        # Delete session
        success = await service.delete_session(conversation_id)
        assert success
        
        # Verify it's gone
        session = await service.get_session(conversation_id)
        assert session is None
    
    @pytest.mark.asyncio
    async def test_list_active_sessions(self, service):
        """Test listing active sessions."""
        # Create multiple sessions
        await service.create_session("test-1")
        await service.create_session("test-2")
        await service.create_session("test-3")
        
        # End one session
        await service.end_session("test-2", "Test end")
        
        # List active sessions
        active_sessions = await service.list_active_sessions()
        
        assert len(active_sessions) == 2
        assert "test-1" in active_sessions
        assert "test-3" in active_sessions
        assert "test-2" not in active_sessions
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, service):
        """Test cleaning up expired sessions."""
        # Create sessions
        await service.create_session("recent")
        await service.create_session("old")
        
        # Manually age the old session by updating its timestamp in storage
        old_session = await service.get_session("old")
        old_session.created_at = datetime.now() - timedelta(hours=2)
        old_session.last_activity = datetime.now() - timedelta(hours=1)
        await service.storage.store_session("old", old_session.to_dict())
        
        # Update the storage timestamp directly
        service.storage._session_timestamps["old"] = time.time() - 7200  # 2 hours ago
        
        # Clean up expired sessions
        cleaned = await service.cleanup_expired_sessions(max_age_seconds=1800)
        assert cleaned == 1
        
        # Verify old session is gone
        active_sessions = await service.list_active_sessions()
        assert "old" not in active_sessions
        assert "recent" in active_sessions


class TestTranscriptManagerRestoration:
    """Test transcript manager conversation context restoration."""
    
    @pytest.fixture
    def transcript_manager(self):
        """Create a transcript manager instance."""
        return TranscriptManager()
    
    def test_restore_conversation_context(self, transcript_manager):
        """Test restoring conversation context."""
        conversation_history = [
            {"type": "input", "text": "Hello, I need help"},
            {"type": "output", "text": "Hi there! How can I assist you today?"},
            {"type": "input", "text": "I lost my card"},
            {"type": "output", "text": "I'm sorry to hear that. Let me help you with card replacement."}
        ]
        
        # Restore context
        transcript_manager.restore_conversation_context(conversation_history)
        
        # Verify input buffer
        assert len(transcript_manager.input_transcript_buffer) == 2
        assert "Hello, I need help" in transcript_manager.input_transcript_buffer
        assert "I lost my card" in transcript_manager.input_transcript_buffer
        
        # Verify output buffer
        assert len(transcript_manager.output_transcript_buffer) == 2
        assert "Hi there! How can I assist you today?" in transcript_manager.output_transcript_buffer
        assert "I'm sorry to hear that. Let me help you with card replacement." in transcript_manager.output_transcript_buffer
    
    def test_get_conversation_context(self, transcript_manager):
        """Test getting conversation context."""
        # Add some content to buffers
        transcript_manager.input_transcript_buffer = ["User input 1", "User input 2"]
        transcript_manager.output_transcript_buffer = ["Bot output 1", "Bot output 2"]
        
        # Get context
        context = transcript_manager.get_conversation_context()
        
        assert len(context) == 4
        assert context[0]["type"] == "input"
        assert context[0]["text"] == "User input 1"
        assert context[2]["type"] == "output"
        assert context[2]["text"] == "Bot output 1"
    
    def test_clear_conversation_context(self, transcript_manager):
        """Test clearing conversation context."""
        # Add some content
        transcript_manager.input_transcript_buffer = ["test input"]
        transcript_manager.output_transcript_buffer = ["test output"]
        
        # Clear context
        transcript_manager.clear_conversation_context()
        
        assert len(transcript_manager.input_transcript_buffer) == 0
        assert len(transcript_manager.output_transcript_buffer) == 0
    
    def test_restore_empty_context(self, transcript_manager):
        """Test restoring empty conversation context."""
        # Should not cause errors
        transcript_manager.restore_conversation_context([])
        
        assert len(transcript_manager.input_transcript_buffer) == 0
        assert len(transcript_manager.output_transcript_buffer) == 0
    
    def test_restore_invalid_context(self, transcript_manager):
        """Test restoring invalid conversation context."""
        invalid_history = [
            {"type": "invalid", "text": "test"},
            {"type": "input"},  # Missing text
            {"text": "no type"}  # Missing type
        ]
        
        # Should handle gracefully
        transcript_manager.restore_conversation_context(invalid_history)
        
        # Should not add invalid items
        assert len(transcript_manager.input_transcript_buffer) == 0
        assert len(transcript_manager.output_transcript_buffer) == 0


class TestFunctionHandlerRestoration:
    """Test function handler restoration."""
    
    @pytest.fixture
    def function_handler(self):
        """Create a function handler instance."""
        mock_websocket = AsyncMock()
        return FunctionHandler(mock_websocket)
    
    def test_restore_function_calls(self, function_handler):
        """Test restoring function calls."""
        function_calls = [
            {
                "call_id": "func-1",
                "function_name": "get_balance",
                "arguments": {"account_id": "12345"},
                "status": "completed",
                "result": {"balance": 1000.00},
                "timestamp": datetime.now().isoformat()
            },
            {
                "call_id": "func-2",
                "function_name": "transfer_funds",
                "arguments": {"from_account": "12345", "to_account": "67890", "amount": 100},
                "status": "in_progress",
                "result": {},
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        # Restore function calls
        function_handler.restore_function_calls(function_calls)
        
        # Verify restoration
        assert len(function_handler.active_function_calls) == 2
        assert "func-1" in function_handler.active_function_calls
        assert "func-2" in function_handler.active_function_calls
        
        # Check first function call
        func1 = function_handler.active_function_calls["func-1"]
        assert func1["function_name"] == "get_balance"
        assert func1["arguments"] == {"account_id": "12345"}
        assert func1["status"] == "completed"
        assert func1["result"] == {"balance": 1000.00}
    
    def test_get_function_call_history(self, function_handler):
        """Test getting function call history."""
        # Add some function calls
        function_handler.active_function_calls = {
            "func-1": {
                "function_name": "test_func",
                "arguments": {"param": "value"},
                "status": "completed",
                "result": {"success": True},
                "timestamp": "2024-01-01T12:00:00"
            }
        }
        
        # Get history
        history = function_handler.get_function_call_history()
        
        assert len(history) == 1
        assert history[0]["call_id"] == "func-1"
        assert history[0]["function_name"] == "test_func"
        assert history[0]["arguments"] == {"param": "value"}
    
    def test_clear_function_call_history(self, function_handler):
        """Test clearing function call history."""
        # Add some function calls
        function_handler.active_function_calls = {
            "func-1": {"function_name": "test_func"},
            "func-2": {"function_name": "test_func2"}
        }
        
        # Clear history
        function_handler.clear_function_call_history()
        
        assert len(function_handler.active_function_calls) == 0
    
    def test_restore_empty_function_calls(self, function_handler):
        """Test restoring empty function calls."""
        # Should not cause errors
        function_handler.restore_function_calls([])
        
        assert len(function_handler.active_function_calls) == 0
    
    def test_restore_invalid_function_calls(self, function_handler):
        """Test restoring invalid function calls."""
        invalid_calls = [
            {},  # Empty call
            {"call_id": "func-1"},  # Missing required fields
            {"call_id": None, "function_name": "test"}  # Invalid call_id
        ]
        
        # Should handle gracefully
        function_handler.restore_function_calls(invalid_calls)
        
        # Should not add invalid calls
        assert len(function_handler.active_function_calls) == 0


class TestRedisSessionStorage:
    """Test Redis-based session storage."""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_client.set.return_value = True
        mock_client.get.return_value = None
        mock_client.delete.return_value = 1
        mock_client.keys.return_value = []
        return mock_client
    
    @pytest.fixture
    def mock_redis_pool(self):
        """Create a mock Redis connection pool."""
        mock_pool = MagicMock()
        return mock_pool
    
    @pytest.mark.asyncio
    @patch('opusagent.session_storage.redis_storage.redis')
    async def test_redis_storage_initialization(self, mock_redis, mock_redis_pool):
        """Test Redis storage initialization."""
        from opusagent.session_storage.redis_storage import RedisSessionStorage
        
        mock_redis.ConnectionPool.from_url.return_value = mock_redis_pool
        mock_redis.Redis.return_value = AsyncMock()
        
        storage = RedisSessionStorage(
            redis_url="redis://localhost:6379",
            session_prefix="test:session:",
            default_ttl=3600,
            max_connections=10
        )
        
        assert storage.redis_url == "redis://localhost:6379"
        assert storage.session_prefix == "test:session:"
        assert storage.default_ttl == 3600
        assert storage.max_connections == 10
    
    @pytest.mark.asyncio
    @patch('opusagent.session_storage.redis_storage.redis')
    async def test_redis_store_and_retrieve_session(self, mock_redis, mock_redis_client):
        """Test storing and retrieving a session in Redis."""
        from opusagent.session_storage.redis_storage import RedisSessionStorage
        
        mock_redis.ConnectionPool.from_url.return_value = MagicMock()
        mock_redis.Redis.return_value = mock_redis_client
        
        storage = RedisSessionStorage()
        
        conversation_id = "test-123"
        session_data = {
            "conversation_id": conversation_id,
            "status": "active",
            "media_format": "pcm16"
        }
        
        # Mock successful storage
        mock_redis_client.set.return_value = True
        
        # Store session
        success = await storage.store_session(conversation_id, session_data)
        assert success
        
        # Mock successful retrieval
        mock_redis_client.get.return_value = json.dumps(session_data)
        
        # Retrieve session
        retrieved = await storage.retrieve_session(conversation_id)
        assert retrieved is not None
        assert retrieved["conversation_id"] == conversation_id
        assert retrieved["status"] == "active"
    
    @pytest.mark.asyncio
    @patch('opusagent.session_storage.redis_storage.redis')
    async def test_redis_connection_failure(self, mock_redis):
        """Test Redis storage with connection failure."""
        from opusagent.session_storage.redis_storage import RedisSessionStorage
        
        mock_redis.ConnectionPool.from_url.side_effect = Exception("Connection failed")
        
        storage = RedisSessionStorage()
        
        # Test that operations fail gracefully
        success = await storage.store_session("test-123", {"test": "data"})
        assert not success
        
        retrieved = await storage.retrieve_session("test-123")
        assert retrieved is None


class TestBridgeSessionManagerIntegration:
    """Test bridge integration with session manager service."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_realtime_websocket(self):
        """Create a mock realtime WebSocket."""
        return AsyncMock()
    
    @pytest.fixture
    def test_session_config(self):
        """Create a test session configuration."""
        from opusagent.models.openai_api import SessionConfig
        return SessionConfig(
            input_audio_format="pcm16",
            output_audio_format="pcm16",
            voice="verse",
            instructions="Test instructions",
            modalities=["text", "audio"],
            temperature=0.8,
            model="gpt-4o-realtime-preview-2024-12-17"
        )
    
    @pytest.mark.asyncio
    async def test_bridge_initialization_with_session_manager(self, mock_websocket, mock_realtime_websocket, test_session_config):
        """Test bridge initialization includes session manager service."""
        from opusagent.bridges.base_bridge import BaseRealtimeBridge
        from opusagent.session_storage.memory_storage import MemorySessionStorage
        
        # Create a mock bridge class that inherits from BaseRealtimeBridge
        class MockBridge(BaseRealtimeBridge):
            def register_platform_event_handlers(self):
                pass
            
            async def send_platform_json(self, payload: dict):
                pass
            
            async def handle_session_start(self, data: dict):
                pass
            
            async def handle_audio_start(self, data: dict):
                pass
            
            async def handle_audio_data(self, data: dict):
                pass
            
            async def handle_audio_end(self, data: dict):
                pass
            
            async def handle_session_end(self, data: dict):
                pass
        
        bridge = MockBridge(
            platform_websocket=mock_websocket,
            realtime_websocket=mock_realtime_websocket,
            session_config=test_session_config
        )
        
        # Verify session manager service is initialized
        assert bridge.session_manager_service is not None
        assert isinstance(bridge.session_manager_service.storage, MemorySessionStorage)
    
    @pytest.mark.asyncio
    async def test_bridge_initialize_conversation_with_resume(self, mock_websocket, mock_realtime_websocket, test_session_config):
        """Test bridge conversation initialization with session resume."""
        from opusagent.bridges.base_bridge import BaseRealtimeBridge
        from opusagent.session_storage.memory_storage import MemorySessionStorage
        
        class MockBridge(BaseRealtimeBridge):
            def register_platform_event_handlers(self):
                pass
            
            async def send_platform_json(self, payload: dict):
                pass
            
            async def handle_session_start(self, data: dict):
                pass
            
            async def handle_audio_start(self, data: dict):
                pass
            
            async def handle_audio_data(self, data: dict):
                pass
            
            async def handle_audio_end(self, data: dict):
                pass
            
            async def handle_session_end(self, data: dict):
                pass
        
        bridge = MockBridge(
            platform_websocket=mock_websocket,
            realtime_websocket=mock_realtime_websocket,
            session_config=test_session_config
        )
        
        # Mock session manager service methods
        if bridge.session_manager_service:
            bridge.session_manager_service.resume_session = AsyncMock(return_value=None)
            bridge.session_manager_service.create_session = AsyncMock()
        bridge._restore_session_state = AsyncMock()
        
        # Test conversation initialization
        await bridge.initialize_conversation("test-conv-123")
        
        # Verify resume was attempted
        if bridge.session_manager_service:
            bridge.session_manager_service.resume_session.assert_called_once_with("test-conv-123")
            # Verify new session was created since resume returned None
            bridge.session_manager_service.create_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bridge_initialize_conversation_with_existing_session(self, mock_websocket, mock_realtime_websocket, test_session_config):
        """Test bridge conversation initialization with existing session."""
        from opusagent.bridges.base_bridge import BaseRealtimeBridge
        
        class MockBridge(BaseRealtimeBridge):
            def register_platform_event_handlers(self):
                pass
            
            async def send_platform_json(self, payload: dict):
                pass
            
            async def handle_session_start(self, data: dict):
                pass
            
            async def handle_audio_start(self, data: dict):
                pass
            
            async def handle_audio_data(self, data: dict):
                pass
            
            async def handle_audio_end(self, data: dict):
                pass
            
            async def handle_session_end(self, data: dict):
                pass
        
        bridge = MockBridge(
            platform_websocket=mock_websocket,
            realtime_websocket=mock_realtime_websocket,
            session_config=test_session_config
        )
        
        # Create a mock existing session
        existing_session = SessionState(
            conversation_id="test-conv-123",
            status=SessionStatus.ACTIVE,
            conversation_history=[{"type": "input", "text": "Hello"}]
        )
        
        # Mock session manager service methods
        if bridge.session_manager_service:
            bridge.session_manager_service.resume_session = AsyncMock(return_value=existing_session)
            bridge.session_manager_service.create_session = AsyncMock()
        bridge._restore_session_state = AsyncMock()
        
        # Test conversation initialization
        await bridge.initialize_conversation("test-conv-123")
        
        # Verify resume was attempted
        if bridge.session_manager_service:
            bridge.session_manager_service.resume_session.assert_called_once_with("test-conv-123")
            # Verify new session was NOT created
            bridge.session_manager_service.create_session.assert_not_called()
        
        # Verify session state was restored
        bridge._restore_session_state.assert_called_once()


class TestComponentRestoration:
    """Test component restoration functionality."""
    
    @pytest.fixture
    def transcript_manager(self):
        """Create a transcript manager instance."""
        return TranscriptManager()
    
    @pytest.fixture
    def function_handler(self):
        """Create a function handler instance."""
        mock_websocket = AsyncMock()
        return FunctionHandler(mock_websocket)
    
    def test_transcript_manager_restore_conversation_context(self, transcript_manager):
        """Test transcript manager conversation context restoration."""
        conversation_history = [
            {"type": "input", "text": "Hello, I need help"},
            {"type": "output", "text": "Hi! How can I assist you?"},
            {"type": "input", "text": "I want to check my balance"}
        ]
        
        # Restore conversation context
        transcript_manager.restore_conversation_context(conversation_history)
        
        # Verify input transcripts
        assert len(transcript_manager.input_transcript_buffer) == 2
        assert transcript_manager.input_transcript_buffer[0] == "Hello, I need help"
        assert transcript_manager.input_transcript_buffer[1] == "I want to check my balance"
        
        # Verify output transcripts
        assert len(transcript_manager.output_transcript_buffer) == 1
        assert transcript_manager.output_transcript_buffer[0] == "Hi! How can I assist you?"
    
    def test_function_handler_restore_function_calls(self, function_handler):
        """Test function handler function call restoration."""
        function_calls = [
            {
                "call_id": "func-1",
                "function_name": "get_balance",
                "arguments": {"account_id": "12345"},
                "status": "completed",
                "result": {"balance": 1500.00}
            },
            {
                "call_id": "func-2",
                "function_name": "transfer_funds",
                "arguments": {"amount": 100, "to_account": "67890"},
                "status": "pending"
            }
        ]
        
        # Restore function calls
        function_handler.restore_function_calls(function_calls)
        
        # Verify function calls were restored
        assert len(function_handler.active_function_calls) == 2
        assert "func-1" in function_handler.active_function_calls
        assert "func-2" in function_handler.active_function_calls
        
        # Verify call details
        call_1 = function_handler.active_function_calls["func-1"]
        assert call_1["function_name"] == "get_balance"
        assert call_1["status"] == "completed"
        assert call_1["result"] == {"balance": 1500.00}
        
        call_2 = function_handler.active_function_calls["func-2"]
        assert call_2["function_name"] == "transfer_funds"
        assert call_2["status"] == "pending"


class TestSessionResumeIntegration:
    """Integration tests for session resume functionality."""
    
    @pytest.fixture
    def storage(self):
        """Create a memory storage instance."""
        return MemorySessionStorage()
    
    @pytest.fixture
    def service(self, storage):
        """Create a session manager service instance."""
        return SessionManagerService(storage)
    
    @pytest.fixture
    def transcript_manager(self):
        """Create a transcript manager instance."""
        return TranscriptManager()
    
    @pytest.fixture
    def function_handler(self):
        """Create a function handler instance."""
        mock_websocket = AsyncMock()
        return FunctionHandler(mock_websocket)
    
    @pytest.mark.asyncio
    async def test_complete_session_resume_flow(self, service, transcript_manager, function_handler):
        """Test complete session resume flow."""
        conversation_id = "test-resume-123"
        
        # 1. Create initial session with context
        session = await service.create_session(
            conversation_id,
            status=SessionStatus.ACTIVE,
            media_format="pcm16"
        )
        
        # Add conversation history
        session.conversation_history = [
            {"type": "input", "text": "Hello, I need help with my account"},
            {"type": "output", "text": "Hi! I'd be happy to help you with your account."},
            {"type": "input", "text": "I want to check my balance"}
        ]
        
        # Add function calls
        session.function_calls = [
            {
                "call_id": "func-1",
                "function_name": "get_balance",
                "arguments": {"account_id": "12345"},
                "status": "completed",
                "result": {"balance": 1500.00}
            }
        ]
        
        # Store session
        await service.storage.store_session(conversation_id, session.to_dict())
        
        # 2. Simulate session resume
        resumed_session = await service.resume_session(conversation_id)
        assert resumed_session is not None
        assert resumed_session.resumed_count == 1
        
        # 3. Restore conversation context
        transcript_manager.restore_conversation_context(resumed_session.conversation_history)
        assert len(transcript_manager.input_transcript_buffer) == 2
        assert len(transcript_manager.output_transcript_buffer) == 1
        
        # 4. Restore function calls
        function_handler.restore_function_calls(resumed_session.function_calls)
        assert len(function_handler.active_function_calls) == 1
        assert "func-1" in function_handler.active_function_calls
        
        # 5. Verify session state
        assert resumed_session.conversation_id == conversation_id
        assert resumed_session.status == SessionStatus.ACTIVE
        assert resumed_session.media_format == "pcm16"
    
    @pytest.mark.asyncio
    async def test_session_resume_with_updates(self, service, transcript_manager, function_handler):
        """Test session resume with subsequent updates."""
        conversation_id = "test-update-123"
        
        # Create initial session
        session = await service.create_session(conversation_id)
        
        # Resume session
        resumed_session = await service.resume_session(conversation_id)
        assert resumed_session.resumed_count == 1
        
        # Add new conversation context
        transcript_manager.input_transcript_buffer.append("New user input")
        transcript_manager.output_transcript_buffer.append("New bot response")
        
        # Add new function call
        function_handler.active_function_calls["func-2"] = {
            "function_name": "transfer_funds",
            "arguments": {"amount": 100},
            "status": "completed",
            "result": {"success": True}
        }
        
        # Update session with new context
        await service.update_session(
            conversation_id,
            conversation_history=transcript_manager.get_conversation_context(),
            function_calls=function_handler.get_function_call_history()
        )
        
        # Resume again
        second_resume = await service.resume_session(conversation_id)
        assert second_resume.resumed_count == 2
        
        # Verify updated context is preserved
        assert len(second_resume.conversation_history) == 2
        assert len(second_resume.function_calls) == 1
    
    @pytest.mark.asyncio
    async def test_session_resume_error_handling(self, service):
        """Test session resume error handling."""
        conversation_id = "test-error-123"
        
        # Try to resume non-existent session
        resumed_session = await service.resume_session(conversation_id)
        assert resumed_session is None
        
        # Create session but make it ended
        await service.create_session(conversation_id)
        await service.end_session(conversation_id, "Test end")
        
        # Try to resume ended session
        resumed_session = await service.resume_session(conversation_id)
        assert resumed_session is None
        
        # Create session but make it expired
        await service.create_session("expired-session")
        
        # Directly modify the session data in storage to make it expired
        expired_session_data = service.storage._sessions["expired-session"]
        expired_session_data["created_at"] = (datetime.now() - timedelta(hours=2)).isoformat()
        expired_session_data["last_activity"] = (datetime.now() - timedelta(hours=1)).isoformat()
        
        # Update the storage timestamp to make it actually expired
        service.storage._session_timestamps["expired-session"] = time.time() - 7200  # 2 hours ago
        
        # Try to resume expired session
        resumed_session = await service.resume_session("expired-session", max_age_seconds=1800)
        assert resumed_session is None


if __name__ == "__main__":
    pytest.main([__file__]) 