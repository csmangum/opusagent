#!/usr/bin/env python3
"""
Example demonstrating how to use the mock WebSocket manager for testing.

This script shows different ways to use the mock functionality integrated
into the WebSocketManager.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opusagent.websocket_manager import (
    create_mock_websocket_manager,
    create_websocket_manager,
    get_websocket_manager,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_with_mock_manager():
    """Example using a mock WebSocket manager."""
    logger.info("=== Example 1: Using mock WebSocket manager ===")
    
    # Create a mock WebSocket manager
    mock_manager = create_mock_websocket_manager()
    
    try:
        # Get a mock connection
        async with mock_manager.connection_context() as connection:
            logger.info(f"Got mock connection: {connection.connection_id}")
            
            # Send a test message
            test_message = json.dumps({
                "type": "session.update",
                "session": {
                    "model": "gpt-4o-realtime-preview",
                    "instructions": "You are a helpful assistant."
                }
            })
            
            await connection.websocket.send(test_message)
            logger.info("Sent test message to mock connection")
            
            # Try to receive a response (this will be a mock response)
            try:
                response = await asyncio.wait_for(connection.websocket.recv(), timeout=2.0)
                logger.info(f"Received mock response: {response}")
            except asyncio.TimeoutError:
                logger.info("No response received (normal for mock without server)")
                
    except Exception as e:
        logger.error(f"Error in mock example: {e}")
    finally:
        await mock_manager.shutdown()


async def example_with_env_variables():
    """Example using environment variables to control mock mode."""
    logger.info("=== Example 2: Using environment variables ===")
    
    # Set environment variables for mock mode
    os.environ["OPUSAGENT_USE_MOCK"] = "true"
    os.environ["OPUSAGENT_MOCK_SERVER_URL"] = "ws://localhost:8080"
    
    # Import after setting env vars (in real usage, you'd set these before import)
    from opusagent.websocket_manager import websocket_manager
    
    # The global manager should now be in mock mode
    stats = websocket_manager.get_stats()
    logger.info(f"Global manager stats: {stats}")
    
    try:
        async with websocket_manager.connection_context() as connection:
            logger.info(f"Got connection from global manager: {connection.connection_id}")
            
            # Send a mock message
            await connection.websocket.send('{"type": "test"}')
            logger.info("Sent test message")
            
    except Exception as e:
        logger.error(f"Error with global manager: {e}")
    finally:
        await websocket_manager.shutdown()


async def example_factory_function():
    """Example using the factory function for different configurations."""
    logger.info("=== Example 3: Using factory function ===")
    
    # Create different managers for different test scenarios
    managers = [
        ("Mock Manager", create_websocket_manager(use_mock=True)),
        ("Real Manager (would connect to OpenAI)", create_websocket_manager(use_mock=False)),
    ]
    
    for name, manager in managers:
        logger.info(f"Testing {name}")
        stats = manager.get_stats()
        logger.info(f"  Stats: {stats}")
        
        if manager.use_mock:
            try:
                async with manager.connection_context() as connection:
                    logger.info(f"  Successfully got mock connection: {connection.connection_id}")
            except Exception as e:
                logger.error(f"  Error getting mock connection: {e}")
        else:
            logger.info("  Skipping real connection test (would require OpenAI API)")
        
        await manager.shutdown()


async def main():
    """Run all examples."""
    logger.info("Starting mock WebSocket manager examples")
    
    await example_with_mock_manager()
    await example_with_env_variables()
    await example_factory_function()
    
    logger.info("All examples completed")


if __name__ == "__main__":
    asyncio.run(main()) 