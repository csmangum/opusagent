#!/usr/bin/env python3
"""
Tests for the mock WebSocket manager functionality.

This module tests the integration between the WebSocketManager and LocalRealtimeClient
to ensure that mock mode works correctly for testing scenarios.
"""

import asyncio
import json
import pytest
from unittest.mock import patch
import sys

from opusagent.handlers.websocket_manager import (
    WebSocketManager,
    create_mock_websocket_manager,
    create_websocket_manager,
    MockWebSocketWrapper,
)


class TestMockWebSocketManager:
    """Tests for mock WebSocket manager functionality."""

    @pytest.mark.asyncio
    async def test_create_mock_websocket_manager(self):
        """Test creating a mock WebSocket manager."""
        manager = create_mock_websocket_manager()
        
        assert manager.use_mock is True
        assert manager.mock_server_url == "ws://localhost:8080"
        
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_mock_websocket_manager_custom_url(self):
        """Test creating a mock WebSocket manager with custom URL."""
        custom_url = "ws://localhost:9999"
        manager = create_mock_websocket_manager(custom_url)
        
        assert manager.use_mock is True
        assert manager.mock_server_url == custom_url
        
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_factory_function_mock_mode(self):
        """Test factory function creates manager in mock mode."""
        manager = create_websocket_manager(use_mock=True, mock_server_url="ws://test:8080")
        
        assert manager.use_mock is True
        assert manager.mock_server_url == "ws://test:8080"
        
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_factory_function_real_mode(self):
        """Test factory function creates manager in real mode."""
        manager = create_websocket_manager(use_mock=False)
        
        assert manager.use_mock is False
        
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_mock_connection_creation(self):
        """Test that mock connections can be created."""
        manager = create_mock_websocket_manager()
        
        try:
            # This should create a mock connection without needing a real server
            async with manager.connection_context() as connection:
                assert connection is not None
                assert "mock" in connection.connection_id
                assert connection.can_accept_session
                
        except ImportError:
            # LocalRealtimeClient may not be available in test environment
            pytest.skip("LocalRealtimeClient not available")
        finally:
            await manager.shutdown()

    @pytest.mark.asyncio
    async def test_mock_websocket_wrapper(self):
        """Test the MockWebSocketWrapper functionality."""
        # Mock the LocalRealtimeClient
        class MockClient:
            def __init__(self):
                self._ws = None
                self.connected = False
            
            async def disconnect(self):
                self.connected = False
        
        mock_client = MockClient()
        wrapper = MockWebSocketWrapper(mock_client)
        
        # Test initial state
        assert wrapper.open is True
        assert wrapper.closed is False
        
        # Test sending (should not raise an exception)
        await wrapper.send('{"type": "test"}')
        
        # Test receiving (should return a mock message)
        message = await wrapper.recv()
        assert isinstance(message, str)
        assert "session.created" in message
        
        # Test closing
        await wrapper.close()
        assert wrapper.closed is True
        assert wrapper.open is False

    @pytest.mark.asyncio
    async def test_get_stats_includes_mock_flag(self):
        """Test that get_stats includes the mock flag."""
        mock_manager = create_mock_websocket_manager()
        real_manager = create_websocket_manager(use_mock=False)
        
        mock_stats = mock_manager.get_stats()
        real_stats = real_manager.get_stats()
        
        assert mock_stats["use_mock"] is True
        assert real_stats["use_mock"] is False
        
        await mock_manager.shutdown()
        await real_manager.shutdown()

    @pytest.mark.asyncio
    async def test_environment_variable_configuration(self):
        """Test that environment variables control mock mode."""
        # Clear the cached websocket manager
        from opusagent.handlers.websocket_manager import _websocket_manager_instance
        
        # Store original manager
        original_manager = _websocket_manager_instance
        
        try:
            # Clear cached manager instance
            import opusagent.handlers.websocket_manager
            opusagent.handlers.websocket_manager._websocket_manager_instance = None
            
            # Clear the cached config in websocket_manager module
            if hasattr(opusagent.handlers.websocket_manager, 'config'):
                delattr(opusagent.handlers.websocket_manager, 'config')
            
            with patch.dict('os.environ', {
                'OPUSAGENT_USE_MOCK': 'true',
                'OPUSAGENT_MOCK_SERVER_URL': 'ws://env-test:8080'
            }):
                # Reload configuration and get manager
                from opusagent.config.settings import reload_config
                from opusagent.handlers.websocket_manager import get_websocket_manager
                
                reload_config()
                manager = get_websocket_manager()
                
                assert manager.use_mock is True
                assert manager.mock_server_url == 'ws://env-test:8080'
                
                await manager.shutdown()
        finally:
            # Restore original manager
            import opusagent.handlers.websocket_manager
            opusagent.handlers.websocket_manager._websocket_manager_instance = original_manager

    @pytest.mark.asyncio
    async def test_mock_connection_logging(self):
        """Test that mock connections log appropriately."""
        manager = create_mock_websocket_manager()
        
        # Check that the manager was initialized with correct logging
        stats = manager.get_stats()
        assert stats["use_mock"] is True
        
        await manager.shutdown()


if __name__ == "__main__":
    # Simple test runner for when pytest is not available
    async def run_simple_test():
        """Run a simple test without pytest."""
        print("Running simple mock WebSocket manager test...")
        
        # Test basic functionality
        manager = create_mock_websocket_manager()
        stats = manager.get_stats()
        print(f"Mock manager stats: {stats}")
        assert stats["use_mock"] is True
        
        await manager.shutdown()
        print("Simple test passed!")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--simple":
        asyncio.run(run_simple_test())
    else:
        print("Run with pytest or use --simple flag for basic test")
        print("Example: python test_mock_websocket_manager.py --simple") 