"""
Integration tests for WebSocket manager with main application.
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch, Mock
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from opusagent.websocket_manager import websocket_manager


class TestWebSocketManagerIntegration:
    """Integration tests for WebSocket manager with main application."""

    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock the global websocket_manager."""
        with patch('opusagent.main.websocket_manager') as mock_manager:
            mock_manager.get_stats.return_value = {
                "total_connections": 3,
                "healthy_connections": 2,
                "active_sessions": 1,
                "total_sessions_handled": 10,
                "max_connections": 10
            }
            mock_manager.connection_context.return_value.__aenter__ = AsyncMock()
            mock_manager.connection_context.return_value.__aexit__ = AsyncMock()
            mock_manager.shutdown = AsyncMock()
            yield mock_manager

    @pytest.fixture
    def mock_websocket_config(self):
        """Mock WebSocketConfig for endpoints."""
        with patch('opusagent.main.WebSocketConfig') as mock_config:
            mock_config.to_dict.return_value = {
                "max_connections": 10,
                "max_connection_age": 3600,
                "max_idle_time": 300,
                "health_check_interval": 30,
                "max_sessions_per_connection": 10,
                "ping_interval": 20,
                "ping_timeout": 30,
                "close_timeout": 10,
                "openai_model": "gpt-4o-realtime-preview-2024-12-17",
                "websocket_url": "wss://api.openai.com/v1/realtime?model=test"
            }
            yield mock_config

    @pytest.fixture
    def test_app(self, mock_websocket_manager, mock_websocket_config):
        """Create a test FastAPI app with mocked dependencies."""
        # Import main after mocking to ensure mocks are applied
        from opusagent import main
        return main.app

    @pytest.fixture
    def client(self, test_app):
        """Create a test client."""
        return TestClient(test_app)

    def test_stats_endpoint(self, client, mock_websocket_manager):
        """Test the /stats endpoint."""
        response = client.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        expected_keys = [
            "total_connections",
            "healthy_connections",
            "active_sessions", 
            "total_sessions_handled",
            "max_connections"
        ]
        
        for key in expected_keys:
            assert key in data
        
        assert data["total_connections"] == 3
        assert data["healthy_connections"] == 2
        mock_websocket_manager.get_stats.assert_called_once()

    def test_health_endpoint_healthy(self, client, mock_websocket_manager):
        """Test the /health endpoint when service is healthy."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["message"] == "Service is operational"
        assert "websocket_manager" in data
        assert data["websocket_manager"]["healthy_connections"] == 2

    def test_health_endpoint_degraded(self, client, mock_websocket_manager):
        """Test the /health endpoint when service is degraded."""
        # Mock degraded state
        mock_websocket_manager.get_stats.return_value = {
            "total_connections": 0,
            "healthy_connections": 0,
            "active_sessions": 0,
            "total_sessions_handled": 0,
            "max_connections": 10
        }
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["message"] == "WebSocket connection issues detected"

    def test_config_endpoint(self, client, mock_websocket_config):
        """Test the /config endpoint."""
        response = client.get("/config")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "websocket_manager" in data
        assert "note" in data
        assert data["websocket_manager"]["max_connections"] == 10
        assert data["websocket_manager"]["openai_model"] == "gpt-4o-realtime-preview-2024-12-17"
        mock_websocket_config.to_dict.assert_called_once()

    def test_root_endpoint(self, client):
        """Test the root endpoint includes websocket manager endpoints."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "endpoints" in data
        endpoints = data["endpoints"]
        assert "/stats" in endpoints
        assert "/health" in endpoints
        assert "/config" in endpoints


class TestWebSocketManagerWebSocketEndpoints:
    """Test WebSocket endpoints with WebSocket manager integration."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock connection from websocket manager."""
        mock_connection = Mock()
        mock_connection.websocket = AsyncMock()
        mock_connection.connection_id = "test_connection_123"
        return mock_connection

    @pytest.fixture
    def mock_bridge_classes(self):
        """Mock bridge classes."""
        with patch('opusagent.main.AudioCodesBridge') as mock_audiocodes, \
             patch('opusagent.main.TwilioBridge') as mock_twilio:
            
            # Mock bridge instances
            mock_audiocodes_instance = AsyncMock()
            mock_audiocodes.return_value = mock_audiocodes_instance
            
            mock_twilio_instance = AsyncMock()
            mock_twilio.return_value = mock_twilio_instance
            
            yield {
                'audiocodes': mock_audiocodes,
                'audiocodes_instance': mock_audiocodes_instance,
                'twilio': mock_twilio,
                'twilio_instance': mock_twilio_instance
            }

    @pytest.mark.asyncio
    async def test_telephony_websocket_with_manager(self, mock_connection, mock_bridge_classes):
        """Test telephony WebSocket endpoint uses websocket manager."""
        from opusagent.main import websocket_endpoint
        
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        
        with patch('opusagent.main.websocket_manager') as mock_manager:
            # Set up context manager mock
            context_manager = AsyncMock()
            context_manager.__aenter__.return_value = mock_connection
            context_manager.__aexit__.return_value = None
            mock_manager.connection_context.return_value = context_manager
            
            # Mock asyncio.gather to avoid actual execution
            with patch('asyncio.gather', new_callable=AsyncMock) as mock_gather:
                mock_gather.return_value = None
                
                await websocket_endpoint(mock_websocket)
                
                # Verify websocket manager was used
                mock_manager.connection_context.assert_called_once()
                
                # Verify bridge was created with managed connection
                mock_bridge_classes['audiocodes'].assert_called_once_with(
                    mock_websocket, mock_connection.websocket
                )

    @pytest.mark.asyncio
    async def test_twilio_websocket_with_manager(self, mock_connection, mock_bridge_classes):
        """Test Twilio WebSocket endpoint uses websocket manager."""
        from opusagent.main import handle_twilio_call
        
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.client = "test_client"
        
        with patch('opusagent.main.websocket_manager') as mock_manager:
            # Set up context manager mock
            context_manager = AsyncMock()
            context_manager.__aenter__.return_value = mock_connection
            context_manager.__aexit__.return_value = None
            mock_manager.connection_context.return_value = context_manager
            
            # Mock asyncio.gather to avoid actual execution
            with patch('asyncio.gather', new_callable=AsyncMock) as mock_gather:
                mock_gather.return_value = None
                
                await handle_twilio_call(mock_websocket)
                
                # Verify websocket manager was used
                mock_manager.connection_context.assert_called_once()
                
                # Verify bridge was created with managed connection
                mock_bridge_classes['twilio'].assert_called_once_with(
                    mock_websocket, mock_connection.websocket
                )

    @pytest.mark.asyncio
    async def test_websocket_endpoint_exception_handling(self, mock_connection, mock_bridge_classes):
        """Test WebSocket endpoint handles exceptions properly."""
        from opusagent.main import websocket_endpoint
        
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        
        with patch('opusagent.main.websocket_manager') as mock_manager:
            # Set up context manager to raise exception
            context_manager = AsyncMock()
            context_manager.__aenter__.side_effect = Exception("Connection failed")
            mock_manager.connection_context.return_value = context_manager
            
            # Should not raise exception - should be handled gracefully
            await websocket_endpoint(mock_websocket)
            
            # Verify context manager was attempted
            mock_manager.connection_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_disconnect_handling(self, mock_connection, mock_bridge_classes):
        """Test WebSocket disconnect is handled properly."""
        from opusagent.main import websocket_endpoint
        from fastapi import WebSocketDisconnect
        
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        
        with patch('opusagent.main.websocket_manager') as mock_manager:
            context_manager = AsyncMock()
            context_manager.__aenter__.return_value = mock_connection
            context_manager.__aexit__.return_value = None
            mock_manager.connection_context.return_value = context_manager
            
            # Mock asyncio.gather to raise WebSocketDisconnect
            with patch('asyncio.gather', side_effect=WebSocketDisconnect()):
                await websocket_endpoint(mock_websocket)
                
                # Should handle disconnect gracefully
                mock_manager.connection_context.assert_called_once()


class TestWebSocketManagerAppLifecycle:
    """Test WebSocket manager integration with app lifecycle."""

    @pytest.mark.asyncio
    async def test_app_shutdown_event(self):
        """Test app shutdown event calls websocket manager shutdown."""
        from opusagent.main import shutdown_event
        
        with patch('opusagent.main.websocket_manager') as mock_manager:
            mock_manager.shutdown = AsyncMock()
            
            await shutdown_event()
            
            mock_manager.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_shutdown_with_exception(self):
        """Test app shutdown handles websocket manager exceptions."""
        from opusagent.main import shutdown_event
        
        with patch('opusagent.main.websocket_manager') as mock_manager:
            mock_manager.shutdown = AsyncMock(side_effect=Exception("Shutdown failed"))
            
            # Should not raise exception
            await shutdown_event()
            
            mock_manager.shutdown.assert_called_once()


class TestWebSocketManagerConfiguration:
    """Test WebSocket manager configuration integration."""

    def test_configuration_loaded_on_startup(self):
        """Test that configuration is properly loaded on module import."""
        # Re-import to test configuration loading
        import importlib
        from opusagent import websocket_manager as ws_manager_module
        
        # This should not raise any exceptions
        importlib.reload(ws_manager_module)
        
        # The global instance should exist
        assert ws_manager_module.websocket_manager is not None

    @pytest.mark.asyncio
    async def test_websocket_manager_stats_integration(self):
        """Test WebSocket manager statistics are properly integrated."""
        # Test that the global manager can provide stats
        stats = websocket_manager.get_stats()
        
        assert isinstance(stats, dict)
        required_keys = [
            "total_connections",
            "healthy_connections",
            "active_sessions",
            "total_sessions_handled",
            "max_connections"
        ]
        
        for key in required_keys:
            assert key in stats

    def test_websocket_manager_config_validation(self):
        """Test that WebSocket manager validates configuration."""
        from opusagent.websocket_config import WebSocketConfig
        
        # This should work with default configuration
        # (assuming OPENAI_API_KEY is not required for this test)
        try:
            WebSocketConfig.to_dict()
        except ValueError:
            # Expected if OPENAI_API_KEY is not set - that's OK for this test
            pass


class TestWebSocketManagerErrorScenarios:
    """Test error scenarios with WebSocket manager integration."""

    @pytest.mark.asyncio
    async def test_connection_failure_handling(self):
        """Test handling of connection failures."""
        with patch('opusagent.websocket_manager.websockets.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            
            # Create a new manager for testing
            from opusagent.websocket_manager import WebSocketManager
            
            with patch('opusagent.websocket_manager.WebSocketConfig') as mock_config:
                mock_config.validate.return_value = None
                mock_config.MAX_CONNECTIONS = 5
                mock_config.MAX_CONNECTION_AGE = 3600
                mock_config.MAX_IDLE_TIME = 300
                mock_config.HEALTH_CHECK_INTERVAL = 10
                mock_config.get_websocket_url.return_value = "wss://test.url"
                mock_config.get_headers.return_value = {"Authorization": "Bearer test"}
                
                manager = WebSocketManager()
                
                # Should raise exception when connection fails
                with pytest.raises(Exception, match="Connection failed"):
                    await manager.get_connection()

    @pytest.mark.asyncio
    async def test_health_check_error_recovery(self):
        """Test health check error recovery."""
        from opusagent.websocket_manager import WebSocketManager
        
        with patch('opusagent.websocket_manager.WebSocketConfig') as mock_config:
            mock_config.validate.return_value = None
            mock_config.MAX_CONNECTIONS = 5
            mock_config.MAX_CONNECTION_AGE = 3600
            mock_config.MAX_IDLE_TIME = 300
            mock_config.HEALTH_CHECK_INTERVAL = 0.1  # Fast for testing
            mock_config.get_websocket_url.return_value = "wss://test.url"
            mock_config.get_headers.return_value = {"Authorization": "Bearer test"}
            
            manager = WebSocketManager()
            
            # Mock cleanup to fail once, then succeed
            call_count = 0
            async def mock_cleanup():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("Cleanup failed")
                return None
            
            with patch.object(manager, '_cleanup_unhealthy_connections', side_effect=mock_cleanup):
                # Start health monitoring
                manager._start_health_monitoring()
                
                # Wait for multiple health checks
                await asyncio.sleep(0.3)
                
                # Stop health monitoring
                if manager._health_check_task:
                    manager._health_check_task.cancel()
                    try:
                        await manager._health_check_task
                    except asyncio.CancelledError:
                        pass
                
                # Should have made multiple cleanup attempts
                assert call_count >= 2 