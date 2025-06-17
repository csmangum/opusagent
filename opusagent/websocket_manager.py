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
from typing import Dict, List, Optional, Set

import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

from opusagent.websocket_config import WebSocketConfig

logger = logging.getLogger(__name__)


class RealtimeConnection:
    """Wrapper for a WebSocket connection to OpenAI Realtime API."""

    def __init__(
        self, websocket: websockets.WebSocketClientProtocol, connection_id: str
    ):
        self.websocket = websocket
        self.connection_id = connection_id
        self.created_at = time.time()
        self.last_used = time.time()
        self.is_healthy = True
        self.session_count = 0
        self.max_sessions = WebSocketConfig.MAX_SESSIONS_PER_CONNECTION

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
        return (
            self.is_healthy
            and self.session_count < self.max_sessions
            and self.websocket.open
        )

    async def close(self):
        """Close the WebSocket connection."""
        try:
            if not self.websocket.closed:
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
    """

    def __init__(self):
        # Validate configuration first
        WebSocketConfig.validate()

        self.max_connections = WebSocketConfig.MAX_CONNECTIONS
        self.max_connection_age = WebSocketConfig.MAX_CONNECTION_AGE
        self.max_idle_time = WebSocketConfig.MAX_IDLE_TIME
        self.health_check_interval = WebSocketConfig.HEALTH_CHECK_INTERVAL

        self._connections: Dict[str, RealtimeConnection] = {}
        self._active_sessions: Set[str] = set()
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown = False

        # Connection parameters from config
        self._url = WebSocketConfig.get_websocket_url()
        self._headers = WebSocketConfig.get_headers()

        logger.info(
            f"WebSocket manager initialized with config: {WebSocketConfig.to_dict()}"
        )

        # Start health monitoring
        self._start_health_monitoring()

    def _start_health_monitoring(self):
        """Start the background health monitoring task."""
        if not self._health_check_task:
            try:
                # Only start health monitoring if there's a running event loop
                asyncio.get_running_loop()
                self._health_check_task = asyncio.create_task(self._health_monitor_loop())
                logger.debug("Health monitoring task started")
            except RuntimeError:
                # No event loop running (e.g., during tests or module import)
                logger.debug("No event loop running, health monitoring will start when first used")
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
            should_remove = (
                not conn.is_healthy
                or conn.websocket.closed
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
        """Create a new WebSocket connection to OpenAI."""
        connection_id = f"openai_{uuid.uuid4().hex[:8]}"

        try:
            websocket = await websockets.connect(
                self._url,
                subprotocols=["realtime"],
                additional_headers=self._headers,
                ping_interval=WebSocketConfig.PING_INTERVAL,
                ping_timeout=WebSocketConfig.PING_TIMEOUT,
                close_timeout=WebSocketConfig.CLOSE_TIMEOUT,
            )

            connection = RealtimeConnection(websocket, connection_id)
            self._connections[connection_id] = connection

            logger.info(f"Created new OpenAI connection: {connection_id}")
            return connection

        except Exception as e:
            logger.error(f"Failed to create OpenAI connection: {e}")
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
            async with websocket_manager.connection_context() as connection:
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
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
