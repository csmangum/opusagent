#!/usr/bin/env python3
"""
Test script for agent conversation endpoint with different caller types.

This script demonstrates how to connect to the agent conversation endpoint
and test different caller personalities.
"""

import asyncio
import json
from typing import Optional

import websockets


async def test_agent_conversation(caller_type: str = "typical", duration: int = 30):
    """
    Test agent conversation with a specific caller type.

    Args:
        caller_type: Type of caller to test (typical, frustrated, elderly, hurried)
        duration: Duration to run the conversation in seconds
    """
    uri = f"ws://localhost:8000/agent-conversation?caller_type={caller_type}"

    print(f"Connecting to agent conversation with {caller_type} caller...")
    print(f"URI: {uri}")
    print(f"Duration: {duration} seconds")
    print("-" * 50)

    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected! Testing {caller_type} caller for {duration} seconds...")

            # Keep the connection alive for the specified duration
            await asyncio.sleep(duration)

            print(f"Test completed for {caller_type} caller")

    except websockets.exceptions.ConnectionClosed:
        print("Connection closed by server")
    except Exception as e:
        print(f"Error during test: {e}")


async def get_available_caller_types():
    """Get available caller types from the server."""
    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/caller-types") as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    print(f"Error getting caller types: {response.status}")
                    return None
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return None


async def main():
    """Main function to run the test."""
    print("Agent Conversation Test")
    print("=" * 50)

    # Get available caller types
    caller_types_data = await get_available_caller_types()
    if caller_types_data:
        print("Available caller types:")
        for caller_type, description in caller_types_data[
            "available_caller_types"
        ].items():
            print(f"  - {caller_type}: {description}")
        print()

    # Test each caller type
    # caller_types = ["typical", "frustrated", "elderly", "hurried"]
    caller_types = ["typical"]

    for caller_type in caller_types:
        print(f"\nTesting {caller_type.upper()} caller...")
        await test_agent_conversation(caller_type, duration=15)
        print(f"Completed {caller_type} caller test")
        print("-" * 30)

    print("\nAll tests completed!")


if __name__ == "__main__":
    print("Make sure the server is running on localhost:8000")
    print("Run: python opusagent/main.py")
    print()

    # Run the test
    asyncio.run(main())
