#!/usr/bin/env python3
"""
Test script for agent-to-agent conversations.

This script starts a conversation between the caller agent and customer service agent
by connecting to the dual agent bridge endpoint.
"""

import asyncio
import logging
import websockets
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("agent_conversation_test")


async def test_agent_conversation(server_url: str = "ws://localhost:8000"):
    """Test agent-to-agent conversation by connecting to the bridge endpoint.
    
    Args:
        server_url: Base URL of the server
    """
    endpoint_url = f"{server_url}/agent-conversation"
    
    logger.info(f"Starting agent conversation test...")
    logger.info(f"Connecting to: {endpoint_url}")
    
    try:
        # Connect to the agent conversation endpoint
        async with websockets.connect(endpoint_url) as websocket:
            logger.info("Connected to agent conversation endpoint")
            
            # The dual agent bridge will handle the conversation internally
            # We just need to keep the connection alive and monitor
            logger.info("Conversation started - monitoring for completion...")
            
            # Wait for the conversation to complete
            # The bridge will close the connection when done
            try:
                await websocket.wait_closed()
                logger.info("Conversation completed - connection closed")
            except websockets.exceptions.ConnectionClosed:
                logger.info("Connection closed by server")
                
    except ConnectionRefusedError:
        logger.error(f"Could not connect to {endpoint_url}")
        logger.error("Make sure the server is running with: python -m opusagent.main")
    except Exception as e:
        logger.error(f"Error during conversation: {e}")


async def main():
    """Main test function."""
    logger.info("=" * 60)
    logger.info("AGENT-TO-AGENT CONVERSATION TEST")
    logger.info("=" * 60)
    
    try:
        await test_agent_conversation()
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
    
    logger.info("Test completed")


if __name__ == "__main__":
    asyncio.run(main()) 