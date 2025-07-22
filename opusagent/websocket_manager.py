"""
WebSocket Manager for OpenAI Realtime API connections.

This module provides centralized management of WebSocket connections to the OpenAI Realtime API,
including connection pooling, health monitoring, reconnection logic, and graceful cleanup.
"""

import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Set

import websockets
from websockets.exceptions import ConnectionClosed
from websockets.typing import Subprotocol

from opusagent.config import get_config, websocket_config, mock_config, openai_config

logger = logging.getLogger(__name__)

# Get centralized configuration
config = get_config()


class MockWebSocketWrapper:
    """Wrapper to make LocalRealtimeClient compatible with websockets interface."""

    def __init__(self, mock_client):
        self.mock_client = mock_client
        self.closed = False
        self.open = True

    async def send(self, message):
        """Send a message through the mock client."""
        if hasattr(self.mock_client, "_ws") and self.mock_client._ws:
            await self.mock_client._ws.send(message)
        else:
            # If no mock server is running, just log the message
            logger.debug(f"[MOCK] Would send: {message}")

    async def recv(self):
        """Receive a message through the mock client."""
        if hasattr(self.mock_client, "_ws") and self.mock_client._ws:
            return await self.mock_client._ws.recv()
        else:
            # Simulate a delay and return a mock message
            await asyncio.sleep(0.1)
            return '{"type": "session.created", "session": {"id": "mock_session"}}'

    async def close(self):
        """Close the mock connection."""
        self.closed = True
        self.open = False
        if hasattr(self.mock_client, "disconnect"):
            await self.mock_client.disconnect()

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            message = await self.recv()
            return message
        except Exception:
            raise StopAsyncIteration


class RealtimeConnection:
    """Wrapper for a WebSocket connection to OpenAI Realtime API."""

    def __init__(self, websocket: Any, connection_id: str):
        self.websocket = websocket
        self.connection_id = connection_id
        self.created_at = time.time()
        self.last_used = time.time()
        self.is_healthy = True
        self.session_count = 0
        self.max_sessions = config.websocket.max_sessions_per_connection

    @property
    def age_seconds(self) -> float:
        """Get the age of this connection in seconds."""
        return time.time() - self.created_at

    @property
    def idle_seconds(self) -> float:
        """Get how long this connection has been idle."""
        return time.time() - self.last_used

    def mark_used(self):
        """Mark this connection as recently used."""
        self.last_used = time.time()
        self.session_count += 1

    @property
    def can_accept_session(self) -> bool:
        """Check if this connection can accept another session."""
        try:
            # Check if websocket is still open
            websocket_open = getattr(self.websocket, 'closed', None) is False and getattr(self.websocket, 'close_code', None) is None
        except:
            websocket_open = False
            
        return (
            self.is_healthy
            and self.session_count < self.max_sessions
            and websocket_open
        )

    async def close(self):
        """Close the WebSocket connection."""
        try:
            # Safely check if websocket is already closed
            try:
                websocket_closed = getattr(self.websocket, 'closed', False) or getattr(self.websocket, 'close_code', None) is not None
            except:
                websocket_closed = True
                
            if not websocket_closed:
                await self.websocket.close()
        except Exception as e:
            logger.warning(f"Error closing connection {self.connection_id}: {e}")
        finally:
            self.is_healthy = False


class WebSocketManager:
    """
    Manages WebSocket connections to OpenAI Realtime API.

    Features:
    - Connection pooling and reuse
    - Health monitoring and automatic cleanup
    - Reconnection logic
    - Graceful shutdown
    - Usage tracking
    - Mock mode for testing
    """

    def __init__(self, use_mock: bool = False, mock_server_url: Optional[str] = None):
        # Use centralized configuration
        self.max_connections = config.websocket.max_connections
        self.max_connection_age = config.websocket.max_connection_age
        self.max_idle_time = config.websocket.max_idle_time
        self.health_check_interval = config.websocket.health_check_interval

        # Mock configuration from centralized config
        self.use_mock = use_mock if use_mock is not None else config.mock.enabled
        self.mock_server_url = mock_server_url or config.mock.server_url

        self._connections: Dict[str, RealtimeConnection] = {}
        self._active_sessions: Set[str] = set()
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown = False

        # Connection parameters from centralized config
        if not config.openai.api_key:
            raise ValueError("OpenAI API key is not set. Please configure 'config.openai.api_key' before initializing WebSocketManager.")
        self._url = config.openai.get_websocket_url()
        self._headers = config.openai.get_headers()

        logger.info(
            f"WebSocket manager initialized with centralized config - "
            f"max_connections={self.max_connections}, use_mock={self.use_mock}, "
            f"openai_model={config.openai.model}"
        )

        # Start health monitoring
        self._start_health_monitoring()

    def _start_health_monitoring(self):
        """Start the background health monitoring task."""
        if not self._health_check_task:
            try:
                # Only start health monitoring if there's a running event loop
                asyncio.get_running_loop()
                self._health_check_task = asyncio.create_task(
                    self._health_monitor_loop()
                )
                logger.debug("Health monitoring task started")
            except RuntimeError:
                # No event loop running (e.g., during tests or module import)
                logger.debug(
                    "No event loop running, health monitoring will start when first used"
                )
                pass

    async def _health_monitor_loop(self):
        """Background task for health monitoring and cleanup."""
        while not self._shutdown:
            try:
                await self._cleanup_unhealthy_connections()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                await asyncio.sleep(self.health_check_interval)

    async def _cleanup_unhealthy_connections(self):
        """Clean up unhealthy, old, or idle connections."""
        current_time = time.time()
        to_remove = []

        for conn_id, conn in self._connections.items():
            try:
                # Safely check if websocket is closed
                websocket_closed = getattr(conn.websocket, 'closed', False) or getattr(conn.websocket, 'close_code', None) is not None
            except:
                websocket_closed = True
                
            should_remove = (
                not conn.is_healthy
                or websocket_closed
                or conn.age_seconds > self.max_connection_age
                or conn.idle_seconds > self.max_idle_time
            )

            if should_remove:
                to_remove.append(conn_id)
                logger.info(
                    f"Removing connection {conn_id}: "
                    f"healthy={conn.is_healthy}, closed={conn.websocket.closed}, "
                    f"age={conn.age_seconds:.1f}s, idle={conn.idle_seconds:.1f}s"
                )

        for conn_id in to_remove:
            await self._remove_connection(conn_id)

    async def _remove_connection(self, connection_id: str):
        """Remove and close a connection."""
        if connection_id in self._connections:
            conn = self._connections.pop(connection_id)
            await conn.close()

    async def _create_connection(self) -> RealtimeConnection:
        """Create a new WebSocket connection to OpenAI or mock server."""
        connection_id = (
            f"{'mock' if self.use_mock else 'openai'}_{uuid.uuid4().hex[:8]}"
        )

        try:
            if self.use_mock:
                websocket = await self._create_mock_connection()
                logger.info(f"Created new mock connection: {connection_id}")
            else:
                websocket = await websockets.connect(
                    self._url,
                    subprotocols=[Subprotocol("realtime")],
                    additional_headers=self._headers,
                    ping_interval=config.websocket.ping_interval,
                    ping_timeout=config.websocket.ping_timeout,
                    close_timeout=config.websocket.close_timeout,
                )
                logger.info(f"Created new OpenAI connection: {connection_id}")

            connection = RealtimeConnection(websocket, connection_id)
            self._connections[connection_id] = connection
            return connection

        except Exception as e:
            logger.error(
                f"Failed to create {'mock' if self.use_mock else 'OpenAI'} connection: {e}"
            )
            raise

    async def _create_mock_connection(self):
        """Create a mock WebSocket connection for testing."""
        try:
            # Try to import the mock client
            from opusagent.local.realtime import LocalRealtimeClient

            # Create mock client
            mock_client = LocalRealtimeClient()

            try:
                # Try to connect to mock server if it's running
                await mock_client.connect(self.mock_server_url)
                logger.info(f"Connected to mock server at {self.mock_server_url}")
                return MockWebSocketWrapper(mock_client)
            except Exception as server_error:
                logger.warning(
                    f"Mock server not running at {self.mock_server_url}: {server_error}"
                )
                # Return a mock wrapper that doesn't require a server
                return MockWebSocketWrapper(mock_client)

        except ImportError:
            logger.error(
                "LocalRealtimeClient not available. Cannot create mock connection."
            )
            raise

    async def get_connection(self) -> RealtimeConnection:
        """
        Get an available WebSocket connection.

        Returns:
            RealtimeConnection: A healthy connection ready for use

        Raises:
            Exception: If unable to get or create a connection
        """
        # Ensure health monitoring is started if not already
        if not self._health_check_task:
            self._start_health_monitoring()

        # Try to find an existing healthy connection
        for conn in self._connections.values():
            if conn.can_accept_session:
                conn.mark_used()
                logger.debug(f"Reusing connection {conn.connection_id}")
                return conn

        # Create a new connection if we haven't hit the limit
        if len(self._connections) < self.max_connections:
            connection = await self._create_connection()
            connection.mark_used()
            return connection

        # If we're at the limit, find the least used connection
        # and close it to make room for a new one
        if self._connections:
            oldest_conn_id = min(
                self._connections.keys(), key=lambda k: self._connections[k].last_used
            )
            await self._remove_connection(oldest_conn_id)
            logger.info(f"Removed oldest connection to make room for new one")

        # Create a new connection
        connection = await self._create_connection()
        connection.mark_used()
        return connection

    @asynccontextmanager
    async def connection_context(self):
        """
        Context manager for getting and automatically managing a connection.

        Usage:
            async with manager.connection_context() as connection:
                # Use connection.websocket
                await connection.websocket.send(data)
        """
        connection = None
        try:
            connection = await self.get_connection()
            yield connection
        except Exception as e:
            logger.error(f"Error in connection context: {e}")
            if connection:
                connection.is_healthy = False
            raise
        finally:
            # Connection cleanup is handled by health monitoring
            pass

    async def close_all_connections(self):
        """Close all WebSocket connections."""
        logger.info(f"Closing {len(self._connections)} WebSocket connections")

        # Close all connections
        close_tasks = []
        for conn in self._connections.values():
            close_tasks.append(conn.close())

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        self._connections.clear()
        self._active_sessions.clear()

    async def shutdown(self):
        """Shutdown the WebSocket manager and clean up resources."""
        logger.info("Shutting down WebSocket manager")
        self._shutdown = True

        # Cancel health monitoring
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        await self.close_all_connections()

    def get_stats(self) -> Dict:
        """Get connection statistics."""
        healthy_connections = sum(
            1 for conn in self._connections.values() if conn.is_healthy
        )
        total_sessions = sum(conn.session_count for conn in self._connections.values())

        return {
            "total_connections": len(self._connections),
            "healthy_connections": healthy_connections,
            "active_sessions": len(self._active_sessions),
            "total_sessions_handled": total_sessions,
            "max_connections": self.max_connections,
            "use_mock": self.use_mock,
        }


# Global WebSocket manager instance
# Initialize with environment variable support for mock mode
_websocket_manager_instance = None


def _get_use_mock_from_config() -> bool:
    """Get the use_mock setting from centralized configuration."""
    return config.mock.enabled


def _get_mock_server_url_from_config() -> str:
    """Get the mock server URL from centralized configuration."""
    return config.mock.server_url


def _create_global_websocket_manager() -> WebSocketManager:
    """Create the global WebSocket manager instance using centralized config."""
    use_mock = _get_use_mock_from_config()
    mock_server_url = _get_mock_server_url_from_config()
    return WebSocketManager(use_mock=use_mock, mock_server_url=mock_server_url)


def create_websocket_manager(
    use_mock: bool = False, mock_server_url: Optional[str] = None
) -> WebSocketManager:
    """Factory function to create a WebSocket manager with specified configuration.

    Args:
        use_mock: Whether to use mock connections instead of real OpenAI API
        mock_server_url: URL for mock server (if use_mock is True)

    Returns:
        Configured WebSocketManager instance
    """
    return WebSocketManager(use_mock=use_mock, mock_server_url=mock_server_url)


def create_mock_websocket_manager(
    mock_server_url: str = "ws://localhost:8080",
) -> WebSocketManager:
    """Create a WebSocket manager configured for mock mode.

    Args:
        mock_server_url: URL for the mock server

    Returns:
        WebSocketManager configured for mock mode
    """
    return WebSocketManager(use_mock=True, mock_server_url=mock_server_url)


def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance.

    Returns:
        The global websocket_manager instance
    """
    global _websocket_manager_instance
    if _websocket_manager_instance is None:
        _websocket_manager_instance = _create_global_websocket_manager()
    return _websocket_manager_instance
