"""
Tests for WebSocket manager module.
"""

import asyncio
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import pytest

from opusagent.websocket_manager import RealtimeConnection, WebSocketManager, websocket_manager


class TestRealtimeConnection:
    """Test cases for RealtimeConnection class."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        websocket = AsyncMock()
        websocket.open = True
        websocket.closed = False
        return websocket

    @pytest.fixture
    def connection(self, mock_websocket):
        """Create a RealtimeConnection instance."""
        connection_id = "test_connection_123"
        return RealtimeConnection(mock_websocket, connection_id)

    def test_initialization(self, connection, mock_websocket):
        """Test RealtimeConnection initialization."""
        assert connection.websocket == mock_websocket
        assert connection.connection_id == "test_connection_123"
        assert connection.is_healthy is True
        assert connection.session_count == 0
        assert connection.max_sessions == 10  # Default from config
        assert isinstance(connection.created_at, float)
        assert isinstance(connection.last_used, float)

    def test_age_seconds(self, connection):
        """Test age calculation."""
        # Mock time to control age calculation
        with patch('time.time', return_value=connection.created_at + 100):
            assert connection.age_seconds == 100

    def test_idle_seconds(self, connection):
        """Test idle time calculation."""
        # Mock time to control idle calculation
        connection.last_used = time.time() - 50
        with patch('time.time', return_value=connection.last_used + 50):
            assert connection.idle_seconds == 50

    def test_mark_used(self, connection):
        """Test marking connection as used."""
        original_session_count = connection.session_count
        original_last_used = connection.last_used
        
        # Wait a small amount to ensure time changes
        time.sleep(0.01)
        connection.mark_used()
        
        assert connection.session_count == original_session_count + 1
        assert connection.last_used > original_last_used

    def test_can_accept_session_healthy(self, connection):
        """Test can_accept_session when connection is healthy."""
        assert connection.can_accept_session is True

    def test_can_accept_session_unhealthy(self, connection):
        """Test can_accept_session when connection is unhealthy."""
        connection.is_healthy = False
        assert connection.can_accept_session is False

    def test_can_accept_session_max_sessions_reached(self, connection):
        """Test can_accept_session when max sessions reached."""
        connection.session_count = connection.max_sessions
        assert connection.can_accept_session is False

    def test_can_accept_session_websocket_closed(self, connection, mock_websocket):
        """Test can_accept_session when WebSocket is closed."""
        mock_websocket.open = False
        assert connection.can_accept_session is False

    @pytest.mark.asyncio
    async def test_close_success(self, connection, mock_websocket):
        """Test successful connection close."""
        await connection.close()
        
        mock_websocket.close.assert_called_once()
        assert connection.is_healthy is False

    @pytest.mark.asyncio
    async def test_close_already_closed(self, connection, mock_websocket):
        """Test closing an already closed connection."""
        mock_websocket.closed = True
        
        await connection.close()
        
        mock_websocket.close.assert_not_called()
        assert connection.is_healthy is False

    @pytest.mark.asyncio
    async def test_close_with_exception(self, connection, mock_websocket):
        """Test closing connection when close() raises exception."""
        mock_websocket.close.side_effect = Exception("Close failed")
        
        # Should not raise exception, but should mark as unhealthy
        await connection.close()
        
        mock_websocket.close.assert_called_once()
        assert connection.is_healthy is False


class TestWebSocketManager:
    """Test cases for WebSocketManager class."""

    @pytest.fixture
    def mock_websockets_connect(self):
        """Mock websockets.connect function."""
        with patch('opusagent.websocket_manager.websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_websocket.open = True
            mock_websocket.closed = False
            mock_connect.return_value = mock_websocket
            yield mock_connect

    @pytest.fixture
    def mock_config(self):
        """Mock WebSocketConfig for testing."""
        with patch('opusagent.websocket_manager.WebSocketConfig') as mock_config:
            mock_config.validate.return_value = None
            mock_config.MAX_CONNECTIONS = 5
            mock_config.MAX_CONNECTION_AGE = 3600
            mock_config.MAX_IDLE_TIME = 300
            mock_config.HEALTH_CHECK_INTERVAL = 10
            mock_config.MAX_SESSIONS_PER_CONNECTION = 10
            mock_config.PING_INTERVAL = 20
            mock_config.PING_TIMEOUT = 30
            mock_config.CLOSE_TIMEOUT = 10
            mock_config.get_websocket_url.return_value = "wss://test.url"
            mock_config.get_headers.return_value = {"Authorization": "Bearer test"}
            yield mock_config

    @pytest.fixture
    def manager(self, mock_config):
        """Create a WebSocketManager instance."""
        return WebSocketManager()

    def test_initialization(self, manager, mock_config):
        """Test WebSocketManager initialization."""
        mock_config.validate.assert_called_once()
        assert manager.max_connections == 5
        assert manager.max_connection_age == 3600
        assert manager.max_idle_time == 300
        assert manager.health_check_interval == 10
        assert len(manager._connections) == 0
        assert len(manager._active_sessions) == 0
        assert manager._shutdown is False

    @pytest.mark.asyncio
    async def test_create_connection_success(self, manager, mock_websockets_connect):
        """Test successful connection creation."""
        connection = await manager._create_connection()
        
        assert isinstance(connection, RealtimeConnection)
        assert connection.connection_id.startswith("openai_")
        assert connection.connection_id in manager._connections
        mock_websockets_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_connection_failure(self, manager, mock_websockets_connect):
        """Test connection creation failure."""
        mock_websockets_connect.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await manager._create_connection()

    @pytest.mark.asyncio
    async def test_get_connection_new(self, manager, mock_websockets_connect):
        """Test getting a new connection when none exist."""
        connection = await manager.get_connection()
        
        assert isinstance(connection, RealtimeConnection)
        assert connection.session_count == 1  # Should be marked as used
        assert len(manager._connections) == 1

    @pytest.mark.asyncio
    async def test_get_connection_reuse_existing(self, manager, mock_websockets_connect):
        """Test reusing an existing healthy connection."""
        # Create first connection
        connection1 = await manager.get_connection()
        
        # Get second connection (should reuse)
        connection2 = await manager.get_connection()
        
        assert connection1 is connection2
        assert connection1.session_count == 2
        assert len(manager._connections) == 1

    @pytest.mark.asyncio
    async def test_get_connection_at_max_connections(self, manager, mock_websockets_connect):
        """Test getting connection when at max connections limit."""
        # Fill up to max connections
        connections = []
        for _ in range(manager.max_connections):
            conn = await manager.get_connection()
            conn.session_count = conn.max_sessions  # Mark as full
            connections.append(conn)
        
        # Request another connection - should replace oldest
        new_connection = await manager.get_connection()
        
        assert isinstance(new_connection, RealtimeConnection)
        assert len(manager._connections) == manager.max_connections

    @pytest.mark.asyncio
    async def test_connection_context_manager(self, manager, mock_websockets_connect):
        """Test connection context manager."""
        async with manager.connection_context() as connection:
            assert isinstance(connection, RealtimeConnection)
            assert connection.session_count == 1

    @pytest.mark.asyncio
    async def test_connection_context_manager_with_exception(self, manager, mock_websockets_connect):
        """Test connection context manager when exception occurs."""
        with pytest.raises(ValueError, match="Test error"):
            async with manager.connection_context() as connection:
                assert connection.is_healthy is True
                raise ValueError("Test error")
        
        # Connection should be marked as unhealthy
        connection_id = list(manager._connections.keys())[0]
        connection = manager._connections[connection_id]
        assert connection.is_healthy is False

    @pytest.mark.asyncio
    async def test_cleanup_unhealthy_connections(self, manager, mock_websockets_connect):
        """Test cleanup of unhealthy connections."""
        # Create a connection and mark it as unhealthy
        connection = await manager.get_connection()
        connection.is_healthy = False
        
        await manager._cleanup_unhealthy_connections()
        
        assert len(manager._connections) == 0

    @pytest.mark.asyncio
    async def test_cleanup_old_connections(self, manager, mock_websockets_connect):
        """Test cleanup of old connections."""
        # Create a connection and make it old
        connection = await manager.get_connection()
        connection.created_at = time.time() - manager.max_connection_age - 1
        
        await manager._cleanup_unhealthy_connections()
        
        assert len(manager._connections) == 0

    @pytest.mark.asyncio
    async def test_cleanup_idle_connections(self, manager, mock_websockets_connect):
        """Test cleanup of idle connections."""
        # Create a connection and make it idle
        connection = await manager.get_connection()
        connection.last_used = time.time() - manager.max_idle_time - 1
        
        await manager._cleanup_unhealthy_connections()
        
        assert len(manager._connections) == 0

    @pytest.mark.asyncio
    async def test_cleanup_closed_connections(self, manager, mock_websockets_connect):
        """Test cleanup of closed WebSocket connections."""
        # Create a connection and close its WebSocket
        connection = await manager.get_connection()
        connection.websocket.closed = True
        
        await manager._cleanup_unhealthy_connections()
        
        assert len(manager._connections) == 0

    @pytest.mark.asyncio
    async def test_remove_connection(self, manager, mock_websockets_connect):
        """Test removing a specific connection."""
        connection = await manager.get_connection()
        connection_id = connection.connection_id
        
        await manager._remove_connection(connection_id)
        
        assert connection_id not in manager._connections
        connection.websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_all_connections(self, manager, mock_websockets_connect):
        """Test closing all connections."""
        # Create multiple connections
        connections = []
        for _ in range(3):
            conn = await manager.get_connection()
            connections.append(conn)
        
        await manager.close_all_connections()
        
        assert len(manager._connections) == 0
        assert len(manager._active_sessions) == 0
        for conn in connections:
            conn.websocket.close.assert_called()

    @pytest.mark.asyncio
    async def test_shutdown(self, manager, mock_websockets_connect):
        """Test manager shutdown."""
        # Create a connection
        await manager.get_connection()
        
        # Start health monitoring task
        manager._start_health_monitoring()
        
        await manager.shutdown()
        
        assert manager._shutdown is True
        assert len(manager._connections) == 0
        assert manager._health_check_task.cancelled()

    def test_get_stats(self, manager):
        """Test getting connection statistics."""
        stats = manager.get_stats()
        
        expected_keys = [
            "total_connections",
            "healthy_connections", 
            "active_sessions",
            "total_sessions_handled",
            "max_connections"
        ]
        
        for key in expected_keys:
            assert key in stats
        
        assert stats["total_connections"] == 0
        assert stats["healthy_connections"] == 0
        assert stats["max_connections"] == manager.max_connections

    @pytest.mark.asyncio
    async def test_get_stats_with_connections(self, manager, mock_websockets_connect):
        """Test getting statistics with active connections."""
        # Create connections with different states
        healthy_conn = await manager.get_connection()
        unhealthy_conn = await manager.get_connection()
        unhealthy_conn.is_healthy = False
        
        stats = manager.get_stats()
        
        assert stats["total_connections"] == 2
        assert stats["healthy_connections"] == 1
        assert stats["total_sessions_handled"] == 2  # Both connections were used once

    @pytest.mark.asyncio
    async def test_health_monitor_loop(self, manager, mock_websockets_connect):
        """Test health monitoring background task."""
        # Create an unhealthy connection
        connection = await manager.get_connection()
        connection.is_healthy = False
        
        # Start health monitoring
        manager._start_health_monitoring()
        
        # Wait for health check to run
        await asyncio.sleep(0.1)
        
        # Cancel the task to stop it
        manager._health_check_task.cancel()
        
        try:
            await manager._health_check_task
        except asyncio.CancelledError:
            pass
        
        # Connection should be removed
        assert len(manager._connections) == 0 