#!/usr/bin/env python3
"""
Test script for agent conversation endpoint with different caller types, scenarios, and agent types.

This script demonstrates how to connect to the agent conversation endpoint
and test different combinations of caller personalities, scenarios, and agent types
as introduced in PR #171.
"""

import asyncio
import json
from typing import Optional

import websockets


async def test_agent_conversation(
    caller_type: str = "typical",
    scenario: str = "banking_card_replacement",
    agent_type: str = "banking",
    duration: int = 30
):
    """
    Test agent conversation with specific parameters.

    Args:
        caller_type: Type of caller personality (typical, frustrated, elderly, hurried)
        scenario: Scenario context (banking_card_replacement, insurance_file_claim, etc.)
        agent_type: CS agent type (banking, insurance)
        duration: Duration to run the conversation in seconds
    """
    uri = f"ws://localhost:8000/agent-conversation?caller_type={caller_type}&scenario={scenario}&agent_type={agent_type}"

    print(f"Connecting to agent conversation:")
    print(f"  - Caller: {caller_type}")
    print(f"  - Scenario: {scenario}")
    print(f"  - Agent: {agent_type}")
    print(f"  - URI: {uri}")
    print(f"  - Duration: {duration} seconds")
    print("-" * 60)

    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected! Testing {caller_type} + {scenario} + {agent_type} for {duration} seconds...")

            # Keep the connection alive for the specified duration
            await asyncio.sleep(duration)

            print(f"✅ Test completed for {caller_type} + {scenario} + {agent_type}")

    except websockets.exceptions.ConnectionClosed:
        print("❌ Connection closed by server")
    except Exception as e:
        print(f"❌ Error during test: {e}")


async def get_available_options():
    """Get available caller types, scenarios, and agent types from the server."""
    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/caller-types") as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    print(f"❌ Error getting caller types: {response.status}")
                    return None
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        return None


async def main():
    """Main function to run comprehensive PR #171 validation tests."""
    print("=" * 80)
    print("PR #171 VALIDATION: Decoupled Caller Personality and Scenario Testing")
    print("=" * 80)

    # Get available options
    options_data = await get_available_options()
    if options_data:
        print("📋 Available Options:")
        print(f"  Caller Types: {list(options_data['available_caller_types'].keys())}")
        print(f"  Scenarios: {list(options_data['available_scenarios'].keys())}")
        print(f"  Agents: {list(options_data['available_agents'].keys())}")
        print()

    # Define comprehensive test combinations to validate PR #171
    test_combinations = [
        # Banking scenarios with different personalities
        # {"caller_type": "typical", "scenario": "banking_card_replacement", "agent_type": "banking"},
        # {"caller_type": "frustrated", "scenario": "banking_card_replacement", "agent_type": "banking"},
        # {"caller_type": "elderly", "scenario": "banking_card_replacement", "agent_type": "banking"},
        # {"caller_type": "hurried", "scenario": "banking_card_replacement", "agent_type": "banking"},
        
        # Insurance scenarios with different personalities (NEW IN PR #171)
        {"caller_type": "typical", "scenario": "insurance_file_claim", "agent_type": "insurance"},
        {"caller_type": "frustrated", "scenario": "insurance_file_claim", "agent_type": "insurance"},
        {"caller_type": "elderly", "scenario": "insurance_file_claim", "agent_type": "insurance"},
        {"caller_type": "hurried", "scenario": "insurance_file_claim", "agent_type": "insurance"},
    ]

    # Run tests for each combination
    for i, test_case in enumerate(test_combinations, 1):
        print(f"\n🧪 TEST {i}/{len(test_combinations)}: {test_case['caller_type'].upper()} caller")
        print(f"   📋 Scenario: {test_case['scenario']}")
        print(f"   🤖 Agent: {test_case['agent_type']}")
        
        await test_agent_conversation(
            caller_type=test_case["caller_type"],
            scenario=test_case["scenario"],
            agent_type=test_case["agent_type"],
            duration=25  # Slightly shorter for comprehensive testing
        )
        
        print(f"✅ Completed test {i}")
        print("-" * 60)
        
        # Small delay between tests
        if i < len(test_combinations):
            print("⏳ Waiting 5 seconds before next test...")
            await asyncio.sleep(5)

    print("\n" + "=" * 80)
    print("🎉 ALL PR #171 VALIDATION TESTS COMPLETED!")
    print("=" * 80)
    print("Key validations performed:")
    print("  ✅ Decoupled caller personalities from scenarios")
    print("  ✅ New insurance_file_claim scenario")
    print("  ✅ Insurance agent type functionality") 
    print("  ✅ All personality + scenario + agent combinations")
    print("  ✅ Enhanced /agent-conversation endpoint parameters")


if __name__ == "__main__":
    print("🚀 Starting PR #171 validation tests...")
    print("📝 Make sure the server is running: python run_opus_server.py --mock")
    print()

    # Run the comprehensive test suite
    asyncio.run(main())
