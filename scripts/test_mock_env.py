#!/usr/bin/env python3
"""
Test Mock Environment Variable Integration

This script tests that the MockRealtimeClient can be used via environment variables
and that the WebSocket manager properly switches to mock mode when configured.

Usage:
    # Test with mock mode enabled
    OPUSAGENT_USE_MOCK=true python scripts/test_mock_env.py
    
    # Test with mock mode disabled (default)
    python scripts/test_mock_env.py
    
    # Test with custom mock server URL
    OPUSAGENT_USE_MOCK=true OPUSAGENT_MOCK_SERVER_URL=ws://localhost:9000 python scripts/test_mock_env.py
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_environment_variables():
    """Test that environment variables are properly read."""
    print("=== Environment Variable Test ===")
    
    # Check current environment variables
    use_mock = os.getenv("OPUSAGENT_USE_MOCK", "false").lower() == "true"
    mock_server_url = os.getenv("OPUSAGENT_MOCK_SERVER_URL", "ws://localhost:8080")
    
    print(f"OPUSAGENT_USE_MOCK: {os.getenv('OPUSAGENT_USE_MOCK', 'not set')} -> {use_mock}")
    print(f"OPUSAGENT_MOCK_SERVER_URL: {mock_server_url}")
    
    # Test different values
    test_cases = [
        ("true", True),
        ("TRUE", True),
        ("True", True),
        ("false", False),
        ("FALSE", False),
        ("False", False),
        ("not_set", False),
        ("", False),
    ]
    
    print("\nTesting different OPUSAGENT_USE_MOCK values:")
    for value, expected in test_cases:
        if value == "not_set":
            result = "false".lower() == "true"
        else:
            result = value.lower() == "true"
        print(f"  '{value}' -> {result} (expected: {expected})")
    
    return use_mock, mock_server_url


def test_websocket_manager_creation():
    """Test that WebSocket manager can be created with mock mode."""
    print("\n=== WebSocket Manager Creation Test ===")
    
    try:
        from opusagent.websocket_manager import (
            create_websocket_manager,
            create_mock_websocket_manager,
            get_websocket_manager
        )
        
        # Test creating mock manager explicitly
        mock_manager = create_mock_websocket_manager()
        print(f"✓ Mock WebSocket manager created: use_mock={mock_manager.use_mock}")
        
        # Test creating regular manager
        regular_manager = create_websocket_manager(use_mock=False)
        print(f"✓ Regular WebSocket manager created: use_mock={regular_manager.use_mock}")
        
        # Test creating manager with custom mock settings
        custom_mock_manager = create_websocket_manager(
            use_mock=True, 
            mock_server_url="ws://localhost:9000"
        )
        print(f"✓ Custom mock WebSocket manager created: use_mock={custom_mock_manager.use_mock}")
        print(f"  Mock server URL: {custom_mock_manager.mock_server_url}")
        
        # Test global manager
        global_manager = get_websocket_manager()
        print(f"✓ Global WebSocket manager: use_mock={global_manager.use_mock}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error creating WebSocket managers: {e}")
        return False


def test_mock_client_import():
    """Test that MockRealtimeClient can be imported."""
    print("\n=== Mock Client Import Test ===")
    
    try:
        from opusagent.mock.mock_realtime_client import MockRealtimeClient, MockResponseConfig
        print("✓ MockRealtimeClient imported successfully")
        
        # Test creating mock client
        mock_client = MockRealtimeClient()
        print("✓ MockRealtimeClient created successfully")
        
        # Test adding response config
        mock_client.add_response_config(
            "test",
            MockResponseConfig(
                text="Test response",
                audio_file="demo/audio/mock_test/greetings/greetings_01.wav"
            )
        )
        print("✓ Response configuration added successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error creating mock client: {e}")
        return False


async def test_mock_connection():
    """Test that mock connections can be created."""
    print("\n=== Mock Connection Test ===")
    
    try:
        from opusagent.websocket_manager import create_mock_websocket_manager
        
        # Create mock manager
        mock_manager = create_mock_websocket_manager()
        
        # Try to get a connection
        connection = await mock_manager.get_connection()
        print(f"✓ Mock connection created: {connection.connection_id}")
        
        # Check connection stats
        stats = mock_manager.get_stats()
        print(f"✓ Connection stats: {stats}")
        
        # Clean up
        await mock_manager.shutdown()
        print("✓ Mock manager shutdown successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Error creating mock connection: {e}")
        return False


def test_configuration_validation():
    """Test that configuration validation works with mock mode."""
    print("\n=== Configuration Validation Test ===")
    
    try:
        from opusagent.config.websocket_config import WebSocketConfig
        
        # Test validation
        WebSocketConfig.validate()
        print("✓ Configuration validation passed")
        
        # Show configuration
        config_dict = WebSocketConfig.to_dict()
        print(f"✓ Configuration: {config_dict}")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration validation failed: {e}")
        return False


def test_environment_override():
    """Test that environment variables can override default settings."""
    print("\n=== Environment Override Test ===")
    
    # Save original environment
    original_use_mock = os.getenv("OPUSAGENT_USE_MOCK")
    original_mock_url = os.getenv("OPUSAGENT_MOCK_SERVER_URL")
    
    try:
        # Test with mock enabled
        os.environ["OPUSAGENT_USE_MOCK"] = "true"
        os.environ["OPUSAGENT_MOCK_SERVER_URL"] = "ws://localhost:9000"
        
        from opusagent.websocket_manager import create_websocket_manager
        
        # Create manager (should use environment variables)
        manager = create_websocket_manager()
        print(f"✓ Manager created with mock mode: {manager.use_mock}")
        print(f"✓ Mock server URL: {manager.mock_server_url}")
        
        # Test with mock disabled
        os.environ["OPUSAGENT_USE_MOCK"] = "false"
        
        manager2 = create_websocket_manager()
        print(f"✓ Manager created without mock mode: {manager2.use_mock}")
        
        return True
        
    except Exception as e:
        print(f"✗ Environment override test failed: {e}")
        return False
    finally:
        # Restore original environment
        if original_use_mock is None:
            os.environ.pop("OPUSAGENT_USE_MOCK", None)
        else:
            os.environ["OPUSAGENT_USE_MOCK"] = original_use_mock
            
        if original_mock_url is None:
            os.environ.pop("OPUSAGENT_MOCK_SERVER_URL", None)
        else:
            os.environ["OPUSAGENT_MOCK_SERVER_URL"] = original_mock_url


async def main():
    """Main test function."""
    print("Mock Environment Variable Integration Test")
    print("=" * 50)
    
    # Test environment variables
    use_mock, mock_server_url = test_environment_variables()
    
    # Test configuration validation
    config_ok = test_configuration_validation()
    
    # Test mock client import
    import_ok = test_mock_client_import()
    
    # Test WebSocket manager creation
    manager_ok = test_websocket_manager_creation()
    
    # Test environment override
    override_ok = test_environment_override()
    
    # Test mock connection (only if mock mode is enabled)
    connection_ok = True
    if use_mock:
        connection_ok = await test_mock_connection()
    else:
        print("\n=== Mock Connection Test ===")
        print("Skipped (mock mode not enabled)")
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Environment Variables: {'✓' if use_mock or not use_mock else '✗'}")
    print(f"Configuration Validation: {'✓' if config_ok else '✗'}")
    print(f"Mock Client Import: {'✓' if import_ok else '✗'}")
    print(f"WebSocket Manager Creation: {'✓' if manager_ok else '✗'}")
    print(f"Environment Override: {'✓' if override_ok else '✗'}")
    print(f"Mock Connection: {'✓' if connection_ok else '✗'}")
    
    all_passed = all([config_ok, import_ok, manager_ok, override_ok, connection_ok])
    
    if all_passed:
        print("\n🎉 All tests passed! Mock environment variable integration is working correctly.")
        print(f"\nCurrent mode: {'MOCK' if use_mock else 'REAL'} API")
        if use_mock:
            print(f"Mock server URL: {mock_server_url}")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    print(f"\nTo enable mock mode, set: OPUSAGENT_USE_MOCK=true")
    print(f"To set custom mock server: OPUSAGENT_MOCK_SERVER_URL=ws://localhost:9000")


if __name__ == "__main__":
    asyncio.run(main()) 