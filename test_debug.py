import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock
from opusagent.websocket_manager import RealtimeConnection, WebSocketManager

async def test_close_debug():
    """Debug test to understand why close() is not being called."""
    
    # Mock the config
    with patch("opusagent.websocket_manager.WebSocketConfig") as mock_config:
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
        
        # Create manager
        manager = WebSocketManager()
        
        # Mock websockets.connect
        with patch("opusagent.websocket_manager.websockets.connect") as mock_connect:
            mock_websocket = AsyncMock()
            mock_websocket.open = True
            mock_websocket.closed = False
            
            # Make the mock return an awaitable coroutine
            future = asyncio.Future()
            future.set_result(mock_websocket)
            mock_connect.return_value = future
            
            # Get a connection
            connection = await manager.get_connection()
            connection_id = connection.connection_id
            
            print(f"Connection created: {connection_id}")
            print(f"WebSocket object: {connection.websocket}")
            print(f"WebSocket close method: {connection.websocket.close}")
            print(f"WebSocket close called before: {connection.websocket.close.called}")
            
            # Remove the connection
            await manager._remove_connection(connection_id)
            
            print(f"WebSocket close called after: {connection.websocket.close.called}")
            print(f"WebSocket close call count: {connection.websocket.close.call_count}")
            
            # Check if the connection was removed
            print(f"Connection in manager: {connection_id in manager._connections}")

if __name__ == "__main__":
    asyncio.run(test_close_debug()) 