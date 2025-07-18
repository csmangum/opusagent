#!/usr/bin/env python3
"""
Demo: Using LocalRealtimeClient with Environment Variables

This script demonstrates how to use the LocalRealtimeClient via environment variables.
It shows both the default behavior and how to enable mock mode.

Usage:
    # Run with real API (default)
    python scripts/demo_mock_env.py
    
    # Run with mock API
    OPUSAGENT_USE_MOCK=true python scripts/demo_mock_env.py
    
    # Run with custom mock server
    OPUSAGENT_USE_MOCK=true OPUSAGENT_MOCK_SERVER_URL=ws://localhost:9000 python scripts/demo_mock_env.py
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def show_current_config():
    """Show the current configuration."""
    print("=== Current Configuration ===")
    
    use_mock = os.getenv("OPUSAGENT_USE_MOCK", "false").lower() == "true"
    mock_server_url = os.getenv("OPUSAGENT_MOCK_SERVER_URL", "ws://localhost:8080")
    
    print(f"OPUSAGENT_USE_MOCK: {os.getenv('OPUSAGENT_USE_MOCK', 'not set')}")
    print(f"OPUSAGENT_MOCK_SERVER_URL: {mock_server_url}")
    print(f"Mode: {'MOCK' if use_mock else 'REAL'} API")
    print()


async def demo_websocket_manager():
    """Demonstrate WebSocket manager behavior."""
    print("=== WebSocket Manager Demo ===")
    
    from opusagent.websocket_manager import get_websocket_manager
    
    # Get the global manager (uses environment variables)
    manager = get_websocket_manager()
    
    print(f"Manager type: {type(manager).__name__}")
    print(f"Use mock: {manager.use_mock}")
    print(f"Mock server URL: {manager.mock_server_url}")
    
    # Show stats
    stats = manager.get_stats()
    print(f"Stats: {stats}")
    print()


async def demo_mock_client():
    """Demonstrate LocalRealtimeClient functionality."""
    print("=== LocalRealtimeClient Demo ===")
    
    from opusagent.local.realtime.client import LocalRealtimeClient
    from opusagent.local.realtime.models import LocalResponseConfig
    
    # Create mock client
    mock_client = LocalRealtimeClient()
    
    # Add some response configurations
    mock_client.add_response_config(
        "greeting",
        LocalResponseConfig(
            text="Hello! Welcome to our service.",
            audio_file="demo/audio/mock_test/greetings/greetings_01.wav"
        )
    )
    
    mock_client.add_response_config(
        "help",
        LocalResponseConfig(
            text="How can I help you today?",
            audio_file="demo/audio/mock_test/greetings/greetings_02.wav"
        )
    )
    
    print(f"Available response configs: {list(mock_client.response_configs.keys())}")
    
    # Test getting a response config
    config = mock_client.get_response_config("greeting")
    print(f"Greeting config: {config.text}")
    
    if config.audio_file:
        print(f"Audio file: {config.audio_file}")
    else:
        print("No audio file configured")
    
    print()


async def demo_connection():
    """Demonstrate connection creation."""
    print("=== Connection Demo ===")
    
    from opusagent.websocket_manager import get_websocket_manager
    
    manager = get_websocket_manager()
    
    try:
        # Try to get a connection
        connection = await manager.get_connection()
        print(f"✓ Connection created: {connection.connection_id}")
        print(f"✓ Connection type: {type(connection.websocket).__name__}")
        
        # Show connection details
        print(f"✓ Connection age: {connection.age_seconds:.1f}s")
        print(f"✓ Sessions handled: {connection.session_count}")
        print(f"✓ Can accept session: {connection.can_accept_session}")
        
        # Clean up
        await manager.shutdown()
        print("✓ Manager shutdown successfully")
        
    except Exception as e:
        print(f"✗ Error creating connection: {e}")
    
    print()


def show_usage_examples():
    """Show usage examples."""
    print("=== Usage Examples ===")
    
    print("1. Enable mock mode:")
    print("   export OPUSAGENT_USE_MOCK=true")
    print("   python your_script.py")
    print()
    
    print("2. Set custom mock server:")
    print("   export OPUSAGENT_USE_MOCK=true")
    print("   export OPUSAGENT_MOCK_SERVER_URL=ws://localhost:9000")
    print("   python your_script.py")
    print()
    
    print("3. Use in Python code:")
    print("   import os")
    print("   os.environ['OPUSAGENT_USE_MOCK'] = 'true'")
    print("   from opusagent.websocket_manager import get_websocket_manager")
    print("   manager = get_websocket_manager()  # Will use mock mode")
    print()
    
    print("4. Create manager explicitly:")
    print("   from opusagent.websocket_manager import create_mock_websocket_manager")
    print("   manager = create_mock_websocket_manager()")
    print()


async def main():
    """Main demo function."""
    print("LocalRealtimeClient Environment Variable Demo")
    print("=" * 50)
    
    # Show current configuration
    show_current_config()
    
    # Demo WebSocket manager
    await demo_websocket_manager()
    
    # Demo mock client
    await demo_mock_client()
    
    # Demo connection (only if mock mode is enabled)
    use_mock = os.getenv("OPUSAGENT_USE_MOCK", "false").lower() == "true"
    if use_mock:
        await demo_connection()
    else:
        print("=== Connection Demo ===")
        print("Skipped (mock mode not enabled)")
        print("Set OPUSAGENT_USE_MOCK=true to enable mock mode")
        print()
    
    # Show usage examples
    show_usage_examples()
    
    print("=" * 50)
    print("Demo completed!")
    print()
    print("To enable mock mode, set: OPUSAGENT_USE_MOCK=true")
    print("To set custom mock server: OPUSAGENT_MOCK_SERVER_URL=ws://localhost:9000")


if __name__ == "__main__":
    asyncio.run(main()) 