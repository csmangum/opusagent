#!/usr/bin/env python3
"""
Test script for the Agent Abstraction Layer.

This script demonstrates the new agent-centric architecture including:
- Agent registration and discovery
- Agent factory functionality
- Agent bridge interface
- Conversation flow management
"""

import asyncio
import json
from typing import Dict, Any

from opusagent.agents import (
    BaseAgent,
    AgentContext,
    AgentResponse,
    agent_registry,
    default_factory,
    AgentBridgeInterface,
    CardReplacementAgent,
    bootstrap_agent_system,
    validate_agent_system,
    get_agent_system_info
)


async def test_agent_registration():
    """Test agent registration system."""
    print("🔧 Testing Agent Registration System")
    print("=" * 50)
    
    # Bootstrap the system
    result = bootstrap_agent_system()
    print(f"Bootstrap result: {result['success']}")
    print(f"Message: {result['message']}")
    print(f"Stats: {result['stats']}")
    print()
    
    # List available agents
    agents = agent_registry.list_agents()
    print(f"Available agents: {len(agents)}")
    for agent in agents:
        print(f"  - {agent['agent_id']}: {agent['name']}")
        print(f"    Keywords: {agent['keywords']}")
        print(f"    Priority: {agent['priority']}")
    print()
    
    # Test intent matching
    test_intents = [
        ["card", "replacement"],
        ["lost", "card"],
        ["account", "balance"],
        ["loan", "application"]
    ]
    
    for intent in test_intents:
        best_agent = agent_registry.get_best_agent(intent)
        matching_agents = agent_registry.find_agents_by_intent(intent)
        print(f"Intent {intent}:")
        print(f"  Best agent: {best_agent}")
        print(f"  All matches: {matching_agents}")
    print()


async def test_agent_factory():
    """Test agent factory functionality."""
    print("🏭 Testing Agent Factory")
    print("=" * 50)
    
    # Create a test context
    context = AgentContext(
        conversation_id="test-conv-001",
        session_id="test-session-001"
    )
    
    # Test creating agent by ID
    agent = await default_factory.create_agent("card_replacement", context)
    if agent:
        print(f"✅ Created agent by ID: {agent.agent_id} ({agent.name})")
        print(f"   Status: {agent.status}")
        print(f"   Functions: {len(agent.get_available_functions())}")
        print(f"   System instruction length: {len(agent.get_system_instruction())}")
        await agent.cleanup()
    else:
        print("❌ Failed to create agent by ID")
    print()
    
    # Test creating agent by intent
    agent = await default_factory.create_agent_by_intent(
        ["card", "replacement"], context
    )
    if agent:
        print(f"✅ Created agent by intent: {agent.agent_id} ({agent.name})")
        await agent.cleanup()
    else:
        print("❌ Failed to create agent by intent")
    print()
    
    # Factory stats
    stats = default_factory.get_factory_stats()
    print(f"Factory stats: {json.dumps(stats, indent=2)}")
    print()


async def test_agent_bridge_interface():
    """Test agent bridge interface."""
    print("🌉 Testing Agent Bridge Interface")
    print("=" * 50)
    
    # Create interface
    interface = AgentBridgeInterface(
        conversation_id="test-conv-002",
        session_id="test-session-002"
    )
    
    # Initialize agent
    success = await interface.initialize_agent(agent_id="card_replacement")
    print(f"Agent initialization: {'✅ Success' if success else '❌ Failed'}")
    
    if success:
        print(f"Agent ready: {interface.is_agent_ready()}")
        print(f"Available functions: {len(interface.get_available_functions())}")
        
        # Test processing user input
        response = await interface.process_user_input("I need to replace my lost card")
        print(f"User input processed:")
        print(f"  Response type: {response.response_type}")
        print(f"  Message: {response.message}")
        print(f"  Function calls: {len(response.function_calls)}")
        
        # Test agent info
        agent_info = interface.get_agent_info()
        print(f"Agent info: {json.dumps(agent_info, indent=2, default=str)}")
        
        # Interface stats
        interface_stats = interface.get_interface_stats()
        print(f"Interface stats: {json.dumps(interface_stats, indent=2, default=str)}")
    
    # Cleanup
    await interface.cleanup()
    print()


async def test_card_replacement_flow():
    """Test the complete card replacement agent flow."""
    print("💳 Testing Card Replacement Flow")
    print("=" * 50)
    
    # Create interface
    interface = AgentBridgeInterface(
        conversation_id="test-conv-003",
        session_id="test-session-003"
    )
    
    # Initialize card replacement agent
    success = await interface.initialize_agent(agent_id="card_replacement")
    if not success:
        print("❌ Failed to initialize card replacement agent")
        return
    
    # Simulate conversation flow
    conversation_steps = [
        "Hi, I need to replace my card",
        "Yes, I want to replace my debit card",
        "My account number is 12345678 and SSN is 123-45-6789",
        "I lost my card yesterday",
        "Yes, that address is correct",
        "Thank you"
    ]
    
    for i, user_input in enumerate(conversation_steps, 1):
        print(f"\nStep {i}: User says: '{user_input}'")
        
        response = await interface.process_user_input(user_input)
        print(f"  Agent response type: {response.response_type}")
        if response.message:
            print(f"  Agent message: {response.message}")
        
        if response.function_calls:
            print(f"  Function calls to make: {len(response.function_calls)}")
            for func_call in response.function_calls:
                print(f"    - {func_call['name']}")
                
                # Simulate function execution with mock results
                mock_result = await simulate_function_call(func_call['name'])
                func_response = await interface.handle_function_result(
                    func_call['name'], mock_result
                )
                print(f"    - Function result handled: {func_response.response_type}")
                if func_response.message:
                    print(f"    - Agent says: {func_response.message}")
        
        if response.is_terminal():
            print(f"  🏁 Conversation ended: {response.response_type}")
            break
    
    # Cleanup
    await interface.cleanup()
    print()


async def simulate_function_call(function_name: str) -> Dict[str, Any]:
    """Simulate function call results for testing."""
    mock_results = {
        "call_intent": {
            "intent_confirmed": True,
            "message": "I understand you need a card replacement."
        },
        "member_account_confirmation": {
            "verified": True,
            "message": "Account verified successfully.",
            "account_details": {"account_type": "checking", "last_four": "1234"}
        },
        "replacement_reason": {
            "reason_collected": True,
            "reason": "lost",
            "message": "I see your card was lost."
        },
        "confirm_address": {
            "address_confirmed": True,
            "message": "Address confirmed.",
            "address": {"street": "123 Main St", "city": "Anytown", "state": "ST", "zip": "12345"}
        },
        "start_card_replacement": {
            "replacement_started": True,
            "replacement_details": {"order_id": "CR123456", "delivery_days": "7-10"}
        },
        "finish_card_replacement": {
            "replacement_completed": True,
            "message": "Your new card will arrive in 7-10 business days."
        },
        "wrap_up": {
            "call_completed": True,
            "message": "Thank you for calling. Your replacement card is on the way!"
        }
    }
    
    return mock_results.get(function_name, {"status": "completed"})


async def test_system_validation():
    """Test system validation."""
    print("✅ Testing System Validation")
    print("=" * 50)
    
    validation = validate_agent_system()
    print(f"System valid: {validation['valid']}")
    
    if validation['issues']:
        print("Issues found:")
        for issue in validation['issues']:
            print(f"  ❌ {issue}")
    
    if validation['warnings']:
        print("Warnings:")
        for warning in validation['warnings']:
            print(f"  ⚠️  {warning}")
    
    print(f"Summary: {json.dumps(validation['summary'], indent=2)}")
    print()
    
    # Full system info
    system_info = get_agent_system_info()
    print("📊 System Information:")
    print(json.dumps(system_info, indent=2, default=str))
    print()


async def main():
    """Run all tests."""
    print("🚀 Agent Abstraction Layer Test Suite")
    print("=" * 60)
    print()
    
    try:
        await test_agent_registration()
        await test_agent_factory()
        await test_agent_bridge_interface()
        await test_card_replacement_flow()
        await test_system_validation()
        
        print("🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 