#!/usr/bin/env python3
"""
Hang-Up Functionality Demo

This script demonstrates the enhanced hang-up functionality for both
the caller agent and voice agent (AudioCodes bridge). It shows how:

1. The voice agent can infer when to hang up based on function calls
2. The caller agent can detect hang-up signals from agent responses
3. Both agents properly end sessions with appropriate reasons

Usage:
    python hang_up_demo.py
"""

import asyncio
import logging
from typing import Dict, Any

from opusagent.config.logging_config import configure_logging
from caller_agent import (
    create_perfect_card_replacement_caller,
    create_difficult_card_replacement_caller,
    CallerAgent,
    PersonalityType,
    ScenarioType,
    CallerPersonality,
    CallerGoal,
    CallerScenario
)

logger = configure_logging("hang_up_demo")


async def demo_voice_agent_hang_up():
    """
    Demo showing how the voice agent hangs up when functions indicate completion.
    
    This simulates the voice agent executing a wrap_up function that triggers
    the hang-up functionality.
    """
    logger.info("\n" + "="*60)
    logger.info("DEMO 1: Voice Agent Hang-Up (Function Triggered)")
    logger.info("="*60)
    
    # Simulate function handler with hang-up callback
    hang_up_called = False
    hang_up_reason = None
    
    async def mock_hang_up_callback(reason: str):
        nonlocal hang_up_called, hang_up_reason
        hang_up_called = True
        hang_up_reason = reason
        logger.info(f"🔚 HANG-UP TRIGGERED: {reason}")
    
    # Import and create a mock function handler
    from opusagent.function_handler import FunctionHandler
    
    # Mock websocket
    class MockWebSocket:
        async def send(self, data):
            logger.info(f"📤 Would send to OpenAI: {data}")
    
    mock_ws = MockWebSocket()
    
    # Create function handler with hang-up callback
    function_handler = FunctionHandler(
        realtime_websocket=mock_ws,
        hang_up_callback=mock_hang_up_callback
    )
    
    # Simulate wrap_up function execution
    logger.info("Executing wrap_up function...")
    
    wrap_up_args = {"organization_name": "Bank of Peril"}
    result = function_handler._func_wrap_up(wrap_up_args)
    
    logger.info(f"Function result: {result}")
    
    # Check if function indicates hang-up
    should_hang_up = function_handler._should_trigger_hang_up("wrap_up", result)
    logger.info(f"Should trigger hang-up: {should_hang_up}")
    
    if should_hang_up:
        # Simulate the hang-up scheduling (without the delay)
        reason = function_handler._get_hang_up_reason(result)
        await mock_hang_up_callback(reason)
    
    # Verify hang-up was triggered
    assert hang_up_called, "Hang-up should have been triggered"
    logger.info(f"✅ Voice agent hang-up demo completed successfully")
    logger.info(f"   Reason: {hang_up_reason}")


async def demo_caller_agent_hang_up_detection():
    """
    Demo showing how the caller agent detects hang-up signals.
    
    This tests the caller agent's ability to recognize when the voice agent
    is indicating the call should end.
    """
    logger.info("\n" + "="*60)
    logger.info("DEMO 2: Caller Agent Hang-Up Detection")
    logger.info("="*60)
    
    # Create a test caller agent
    personality = CallerPersonality(
        type=PersonalityType.NORMAL,
        traits=["polite", "efficient"],
        communication_style="Professional",
        patience_level=7,
        tech_comfort=8,
        tendency_to_interrupt=0.1,
        provides_clear_info=0.9,
    )

    goal = CallerGoal(
        primary_goal="Test hang-up detection",
        secondary_goals=[],
        success_criteria=["call completed"],
        failure_conditions=["call failed"],
        max_conversation_turns=5,
    )

    scenario = CallerScenario(
        scenario_type=ScenarioType.CARD_REPLACEMENT,
        goal=goal,
        context={"card_type": "test card", "reason": "test"}
    )

    # Create caller agent (but don't connect)
    caller = CallerAgent(
        bridge_url="ws://localhost:8000/test",  # Won't actually connect
        personality=personality,
        scenario=scenario,
        caller_name="TestCaller",
        caller_phone="+15551234567",
    )
    
    # Test various hang-up detection scenarios
    test_cases = [
        {
            "agent_text": "Thank you for calling Bank of Peril. Have a great day!",
            "should_hang_up": True,
            "description": "Direct farewell"
        },
        {
            "agent_text": "Your replacement card will be sent within 5-7 business days.",
            "should_hang_up": True,
            "description": "Card replacement completion"
        },
        {
            "agent_text": "We're all set! Is there anything else I can help you with today?",
            "should_hang_up": True,
            "description": "Wrap-up question"
        },
        {
            "agent_text": "I'm transferring you now to a human agent. Please hold.",
            "should_hang_up": True,
            "description": "Human transfer"
        },
        {
            "agent_text": "Let me look up your account information.",
            "should_hang_up": False,
            "description": "Normal conversation"
        },
        {
            "agent_text": "Can you please provide your account number?",
            "should_hang_up": False,
            "description": "Information request"
        }
    ]
    
    logger.info(f"Testing {len(test_cases)} hang-up detection scenarios...")
    
    for i, test_case in enumerate(test_cases, 1):
        agent_text = test_case["agent_text"]
        expected = test_case["should_hang_up"]
        description = test_case["description"]
        
        result = caller._should_hang_up(agent_text)
        
        status = "✅" if result == expected else "❌"
        logger.info(f"{status} Test {i}: {description}")
        logger.info(f"   Agent text: '{agent_text}'")
        logger.info(f"   Expected: {expected}, Got: {result}")
        
        if result != expected:
            logger.error(f"   FAILED: Hang-up detection mismatch!")
        
        logger.info("")
    
    logger.info("✅ Caller agent hang-up detection demo completed")


async def demo_perfect_caller_scenario():
    """
    Demo showing a perfect caller scenario with hang-up.
    
    This demonstrates how a perfect caller would handle a complete interaction
    that ends with the voice agent triggering a hang-up.
    """
    logger.info("\n" + "="*60)
    logger.info("DEMO 3: Perfect Caller with Hang-Up Scenario")
    logger.info("="*60)
    
    # Create perfect caller
    perfect_caller = create_perfect_card_replacement_caller(
        bridge_url="ws://localhost:8000/test"  # Won't actually connect in demo
    )
    
    logger.info("Created perfect caller with:")
    logger.info(f"  Personality: {perfect_caller.personality.type.value}")
    logger.info(f"  Goal: {perfect_caller.scenario.goal.primary_goal}")
    logger.info(f"  Max turns: {perfect_caller.scenario.goal.max_conversation_turns}")
    logger.info(f"  Success criteria: {perfect_caller.scenario.goal.success_criteria}")
    
    # Simulate conversation flow
    simulated_conversation = [
        {
            "speaker": "Agent",
            "text": "Hello! How can I help you today?",
            "caller_should_hang_up": False
        },
        {
            "speaker": "Caller", 
            "text": "Hi, I need to replace my lost gold card. Can you send it to the address on file?",
            "caller_should_hang_up": False
        },
        {
            "speaker": "Agent",
            "text": "I can help you with that. Let me process the replacement for your gold card.",
            "caller_should_hang_up": False
        },
        {
            "speaker": "Agent",
            "text": "Your replacement gold card has been ordered and will arrive within 5-7 business days. Thank you for calling!",
            "caller_should_hang_up": True
        }
    ]
    
    logger.info("\nSimulating conversation flow:")
    
    for turn, exchange in enumerate(simulated_conversation, 1):
        speaker = exchange["speaker"]
        text = exchange["text"]
        
        logger.info(f"\nTurn {turn} - {speaker}: {text}")
        
        if speaker == "Agent":
            should_hang_up = perfect_caller._should_hang_up(text)
            expected = exchange["caller_should_hang_up"]
            
            status = "✅" if should_hang_up == expected else "❌"
            logger.info(f"  {status} Caller hang-up detection: {should_hang_up} (expected: {expected})")
            
            if should_hang_up:
                logger.info("  🔚 Caller would end call here")
                break
    
    logger.info("\n✅ Perfect caller scenario demo completed")


async def demo_function_hang_up_scenarios():
    """
    Demo different function-triggered hang-up scenarios.
    """
    logger.info("\n" + "="*60)
    logger.info("DEMO 4: Function-Triggered Hang-Up Scenarios")
    logger.info("="*60)
    
    # Mock websocket and callback
    class MockWebSocket:
        async def send(self, data):
            pass
    
    hang_up_calls = []
    
    async def mock_hang_up_callback(reason: str):
        hang_up_calls.append(reason)
        logger.info(f"🔚 HANG-UP: {reason}")
    
    # Create function handler
    from opusagent.function_handler import FunctionHandler
    
    function_handler = FunctionHandler(
        realtime_websocket=MockWebSocket(),
        hang_up_callback=mock_hang_up_callback
    )
    
    # Test different hang-up scenarios
    test_functions = [
        {
            "name": "wrap_up",
            "args": {"organization_name": "Bank of Peril"},
            "expected_hang_up": True
        },
        {
            "name": "transfer_to_human", 
            "args": {"reason": "complex issue", "priority": "high"},
            "expected_hang_up": True
        },
        {
            "name": "get_balance",
            "args": {},
            "expected_hang_up": False
        },
        {
            "name": "finish_card_replacement",
            "args": {"card_in_context": "gold card", "address_in_context": "123 Main St"},
            "expected_hang_up": False  # This doesn't directly hang up, but leads to wrap_up
        }
    ]
    
    for test in test_functions:
        func_name = test["name"]
        args = test["args"]
        expected_hang_up = test["expected_hang_up"]
        
        logger.info(f"\nTesting function: {func_name}")
        logger.info(f"Args: {args}")
        
        # Get the function and execute it
        func = function_handler.function_registry.get(func_name)
        if func:
            result = func(args)
            should_hang_up = function_handler._should_trigger_hang_up(func_name, result)
            
            status = "✅" if should_hang_up == expected_hang_up else "❌"
            logger.info(f"{status} Should hang up: {should_hang_up} (expected: {expected_hang_up})")
            
            if should_hang_up:
                reason = function_handler._get_hang_up_reason(result)
                await mock_hang_up_callback(reason)
        else:
            logger.error(f"❌ Function {func_name} not found!")
    
    logger.info(f"\n✅ Function hang-up scenarios completed")
    logger.info(f"   Total hang-ups triggered: {len(hang_up_calls)}")
    for reason in hang_up_calls:
        logger.info(f"   - {reason}")


async def main():
    """Run all hang-up functionality demos."""
    logger.info("🚀 Starting Hang-Up Functionality Demo")
    logger.info("This demo shows enhanced hang-up capabilities for both caller and voice agents")
    
    try:
        # Demo 1: Voice agent function-triggered hang-up
        await demo_voice_agent_hang_up()
        
        # Demo 2: Caller agent hang-up detection
        await demo_caller_agent_hang_up_detection()
        
        # Demo 3: Perfect caller scenario
        await demo_perfect_caller_scenario()
        
        # Demo 4: Function hang-up scenarios
        await demo_function_hang_up_scenarios()
        
        logger.info("\n" + "="*60)
        logger.info("🎉 ALL DEMOS COMPLETED SUCCESSFULLY!")
        logger.info("="*60)
        logger.info("\nHang-up functionality summary:")
        logger.info("✅ Voice agents can infer hang-up from function results")
        logger.info("✅ Caller agents can detect hang-up signals from responses")
        logger.info("✅ Both agents properly end sessions with reasons")
        logger.info("✅ Different hang-up scenarios are handled appropriately")
        
    except Exception as e:
        logger.error(f"❌ Demo failed with error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    asyncio.run(main())