"""
Mock WebSocket connection for LocalRealtimeClient.

This module provides a WebSocket-compatible wrapper around LocalRealtimeClient
that allows it to be used as a drop-in replacement for real WebSocket connections.
The mock connection implements the same interface as websockets.WebSocketClientProtocol
and routes messages through the LocalRealtimeClient.

Key Features:
- WebSocket-compatible interface (send, receive, close, iteration)
- Internal message routing through LocalRealtimeClient
- Proper connection lifecycle management
- Async iteration support for receiving messages
- Error handling and connection state management

Usage:
    # Create mock connection
    mock_ws = await create_mock_websocket_connection(session_config, local_realtime_config)
    
    # Use like a real WebSocket
    await mock_ws.send(json.dumps({"type": "session.update", "session": {...}}))
    
    async for message in mock_ws:
        data = json.loads(message)
        # Process message
        
    await mock_ws.close()
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Optional

from .client import LocalRealtimeClient
from .models import LocalResponseConfig, ResponseSelectionCriteria
from opusagent.models.openai_api import SessionConfig

logger = logging.getLogger(__name__)


class MockWebSocketConnection:
    """
    Mock WebSocket connection that wraps LocalRealtimeClient.
    
    This class provides a WebSocket-compatible interface around LocalRealtimeClient,
    allowing it to be used as a drop-in replacement for real WebSocket connections
    in bridges and other components.
    
    The mock connection handles:
    - Message routing between external code and LocalRealtimeClient
    - WebSocket interface compatibility (send, receive, close, iteration)
    - Connection lifecycle management
    - Async iteration for message receiving
    - Error handling and connection state
    """
    
    def __init__(
        self,
        client: LocalRealtimeClient,
        connection_id: Optional[str] = None
    ):
        """
        Initialize the mock WebSocket connection.
        
        Args:
            client: Configured LocalRealtimeClient instance
            connection_id: Optional connection identifier for logging
        """
        self.client = client
        self.connection_id = connection_id or str(uuid.uuid4())
        self.closed = False
        self.close_code = None
        self._message_queue = asyncio.Queue()
        self._client_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Set up message routing from client to queue
        self._setup_message_routing()
        
        logger.info(f"[MOCK WS] Created mock WebSocket connection: {self.connection_id}")
    
    def _setup_message_routing(self):
        """Set up message routing from LocalRealtimeClient to external consumers."""
        # We'll set up a custom WebSocket-like interface for the client
        # The client will route messages through our queue
        original_send_event = self.client._event_handler._send_event
        
        async def mock_send_event(event: Dict[str, Any]):
            """Route events from client to our message queue."""
            try:
                message = json.dumps(event)
                await self._message_queue.put(message)
                logger.debug(f"[MOCK WS] Queued message: {event.get('type', 'unknown')}")
            except Exception as e:
                logger.error(f"[MOCK WS] Error routing message: {e}")
        
        # Replace the client's send method with our routing
        self.client._event_handler._send_event = mock_send_event
        if hasattr(self.client, '_response_generator'):
            self.client._response_generator._send_event = mock_send_event
    
    async def send(self, message: str) -> None:
        """
        Send a message to the LocalRealtimeClient.
        
        Args:
            message: JSON string message to send
            
        Raises:
            ConnectionClosed: If the connection is closed
        """
        if self.closed:
            from websockets.exceptions import ConnectionClosed
            raise ConnectionClosed(None, None)
        
        try:
            # Route message to the LocalRealtimeClient
            await self.client._event_handler.handle_message(message)
            logger.debug(f"[MOCK WS] Sent message to client: {json.loads(message).get('type', 'unknown')}")
        except Exception as e:
            logger.error(f"[MOCK WS] Error sending message: {e}")
            raise
    
    async def recv(self) -> str:
        """
        Receive a message from the LocalRealtimeClient.
        
        Returns:
            JSON string message from the client
            
        Raises:
            ConnectionClosed: If the connection is closed
        """
        if self.closed:
            from websockets.exceptions import ConnectionClosed
            raise ConnectionClosed(None, None)
        
        try:
            # Get message from queue with timeout
            message = await asyncio.wait_for(self._message_queue.get(), timeout=30.0)
            logger.debug(f"[MOCK WS] Received message: {json.loads(message).get('type', 'unknown')}")
            return message
        except asyncio.TimeoutError:
            logger.warning("[MOCK WS] Receive timeout")
            raise
        except Exception as e:
            logger.error(f"[MOCK WS] Error receiving message: {e}")
            raise
    
    async def close(self, code: int = 1000, reason: str = "Normal closure") -> None:
        """
        Close the mock WebSocket connection.
        
        Args:
            code: Close code (default: 1000 for normal closure)
            reason: Close reason description
        """
        if self.closed:
            return
        
        logger.info(f"[MOCK WS] Closing connection {self.connection_id}: {reason}")
        
        self.closed = True
        self.close_code = code
        
        # Stop the client task if running
        if self._client_task and not self._client_task.done():
            self._client_task.cancel()
            try:
                if self._client_task:
                    await self._client_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect the client
        if self.client.connected:
            await self.client.disconnect()
        
        # Signal end of messages
        await self._message_queue.put(None)
        
        logger.info(f"[MOCK WS] Connection closed: {self.connection_id}")
    
    def __aiter__(self):
        """Make the connection async iterable."""
        return self
    
    async def __anext__(self):
        """Async iteration to receive messages."""
        try:
            message = await self.recv()
            if message is None:
                raise StopAsyncIteration
            return message
        except Exception:
            raise StopAsyncIteration
    
    @property
    def open(self) -> bool:
        """Check if the connection is open."""
        return not self.closed
    
    def __repr__(self):
        """String representation of the mock connection."""
        status = "open" if self.open else "closed"
        return f"MockWebSocketConnection(id={self.connection_id}, status={status})"


async def create_mock_websocket_connection(
    session_config: Optional[SessionConfig] = None,
    local_realtime_config: Optional[Dict[str, Any]] = None,
    response_configs: Optional[Dict[str, LocalResponseConfig]] = None,
    setup_smart_responses: bool = True,
    enable_vad: bool = True,
    enable_transcription: bool = False,
    connection_id: Optional[str] = None
) -> MockWebSocketConnection:
    """
    Create a mock WebSocket connection with LocalRealtimeClient.
    
    This function creates and configures a LocalRealtimeClient, then wraps it
    in a MockWebSocketConnection that provides a WebSocket-compatible interface.
    
    Args:
        session_config: OpenAI session configuration
        local_realtime_config: Local realtime client configuration
        response_configs: Pre-configured response configurations
        setup_smart_responses: Whether to set up smart response examples
        enable_vad: Whether to enable Voice Activity Detection
        enable_transcription: Whether to enable local transcription
        connection_id: Optional connection identifier
    
    Returns:
        MockWebSocketConnection: Ready-to-use mock connection
        
    Example:
        ```python
        # Create mock connection with default configuration
        mock_ws = await create_mock_websocket_connection()
        
        # Use like a real WebSocket
        await mock_ws.send(json.dumps({"type": "session.update", "session": {...}}))
        
        async for message in mock_ws:
            data = json.loads(message)
            print(f"Received: {data['type']}")
        
        await mock_ws.close()
        ```
    """
    # Set up default configuration
    if session_config is None:
        session_config = SessionConfig(
            model="gpt-4o-realtime-preview-2025-06-03",
            modalities=["text", "audio"],
            voice="alloy",
            turn_detection={"type": "server_vad"} if enable_vad else None
        )
    
    # Extract configuration from local_realtime_config
    config = local_realtime_config or {}
    vad_config = config.get("vad_config", {})
    transcription_config = config.get("transcription_config", {})
    
    # Create LocalRealtimeClient
    client = LocalRealtimeClient(
        session_config=session_config,
        response_configs=response_configs,
        enable_vad=enable_vad,
        vad_config=vad_config,
        enable_transcription=enable_transcription,
        transcription_config=transcription_config
    )
    
    # Set up smart responses if requested
    if setup_smart_responses:
        client.setup_smart_response_examples()
    
    # Create mock WebSocket connection
    mock_ws = MockWebSocketConnection(client, connection_id)
    
    logger.info(f"[MOCK WS] Created mock connection with client: {client}")
    
    return mock_ws


class MockWebSocketConnectionManager:
    """
    Manager for mock WebSocket connections.
    
    This class provides a context manager interface similar to the real
    WebSocketManager, allowing drop-in replacement in existing code.
    """
    
    def __init__(self, **default_config):
        """
        Initialize the mock connection manager.
        
        Args:
            **default_config: Default configuration for all connections
        """
        self.default_config = default_config
        self.connections = {}
        
    def connection_context(self, connection_id: Optional[str] = None):
        """
        Context manager for mock WebSocket connections.
        
        Args:
            connection_id: Optional connection identifier
            
        Returns:
            Context manager yielding MockWebSocketConnection
        """
        return MockConnectionContext(self, connection_id)
    
    async def create_connection(self, connection_id: Optional[str] = None):
        """
        Create a new mock WebSocket connection.
        
        Args:
            connection_id: Optional connection identifier
            
        Returns:
            MockWebSocketConnection: New mock connection
        """
        connection_id = connection_id or str(uuid.uuid4())
        
        mock_ws = await create_mock_websocket_connection(
            connection_id=connection_id,
            **self.default_config
        )
        
        self.connections[connection_id] = mock_ws
        return mock_ws
    
    async def close_connection(self, connection_id: str):
        """
        Close a specific mock connection.
        
        Args:
            connection_id: Connection identifier to close
        """
        if connection_id in self.connections:
            await self.connections[connection_id].close()
            del self.connections[connection_id]
    
    async def close_all(self):
        """Close all mock connections."""
        for connection_id in list(self.connections.keys()):
            await self.close_connection(connection_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about mock connections.
        
        Returns:
            Dictionary with connection statistics
        """
        total_connections = len(self.connections)
        healthy_connections = sum(1 for conn in self.connections.values() if conn.open)
        
        return {
            "total_connections": total_connections,
            "healthy_connections": healthy_connections,
            "max_connections": 100,  # Mock limit
            "connection_ids": list(self.connections.keys())
        }


class MockConnectionContext:
    """Context manager for mock WebSocket connections."""
    
    def __init__(self, manager: MockWebSocketConnectionManager, connection_id: Optional[str] = None):
        self.manager = manager
        self.connection_id = connection_id
        self.connection = None
    
    async def __aenter__(self):
        """Enter the context manager."""
        self.connection = await self.manager.create_connection(self.connection_id)
        return self.connection
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        if self.connection:
            await self.connection.close()
            if self.connection.connection_id in self.manager.connections:
                del self.manager.connections[self.connection.connection_id] 