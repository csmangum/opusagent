#!/usr/bin/env python3
"""
Example Usage of Caller Agent System

This script demonstrates how to use the intelligent caller agent system
to test your telephony bridge with different scenarios.
"""

import asyncio
import logging
from datetime import datetime

from caller_agent import (
    CallerAgent, PersonalityType, ScenarioType, CallerPersonality,
    CallerGoal, CallerScenario,
    create_difficult_card_replacement_caller,
    create_confused_elderly_caller,
    create_angry_complaint_caller
)
from caller_utils import PerformanceMonitor, TestDataGenerator, ConfigManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_1_basic_usage():
    """Example 1: Basic usage with predefined scenarios."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Usage with Predefined Scenarios")
    print("="*60)
    
    bridge_url = "ws://localhost:8000/ws/telephony"
    
    # Test different predefined callers
    callers = [
        # ("Difficult Card Replacement", create_difficult_card_replacement_caller),
        ("Confused Elderly Customer", create_confused_elderly_caller),
        # ("Angry Complaint Customer", create_angry_complaint_caller),
    ]
    
    for name, caller_factory in callers:
        print(f"\nTesting: {name}")
        print("-" * 40)
        
        try:
            async with caller_factory(bridge_url) as caller:
                success = await caller.start_call(timeout=30.0)
                
                print(f"  Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
                print(f"  Turns: {caller.conversation_turns}")
                print(f"  Goals: {len(caller.goals_achieved)}")
                
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            
        # Brief pause between tests
        await asyncio.sleep(2.0)


async def example_2_custom_caller():
    """Example 2: Creating a custom caller with specific personality and scenario."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Custom Caller Creation")
    print("="*60)
    
    # Create a custom personality: Impatient business customer
    personality = CallerPersonality(
        type=PersonalityType.IMPATIENT,
        traits=["rushed", "business-focused", "direct", "time-sensitive"],
        communication_style="Quick and to the point, expects fast service",
        patience_level=2,  # Very impatient
        tech_comfort=8,    # High tech comfort
        tendency_to_interrupt=0.8,  # Likely to interrupt
        provides_clear_info=0.9     # Provides clear information
    )
    
    # Create a custom goal
    goal = CallerGoal(
        primary_goal="Get business loan information and apply quickly",
        secondary_goals=[
            "Understand interest rates",
            "Learn about documentation requirements",
            "Set up application appointment"
        ],
        success_criteria=[
            "loan information provided",
            "application process explained",
            "next steps scheduled"
        ],
        failure_conditions=[
            "transferred to human without resolution",
            "call takes too long",
            "information not provided"
        ],
        max_conversation_turns=12  # Shorter due to impatience
    )
    
    # Create a custom scenario
    scenario = CallerScenario(
        scenario_type=ScenarioType.LOAN_APPLICATION,
        goal=goal,
        context={
            "business_type": "restaurant",
            "loan_amount": "$250,000",
            "urgency": "high",
            "has_previous_loans": True
        }
    )
    
    # Create the caller
    bridge_url = "ws://localhost:8000/ws/telephony"
    caller = CallerAgent(
        bridge_url=bridge_url,
        personality=personality,
        scenario=scenario,
        caller_name="BusinessBob",
        caller_phone="+15559876543"
    )
    
    print("Custom Caller Configuration:")
    print(f"  Name: {caller.caller_name}")
    print(f"  Personality: {personality.type.value}")
    print(f"  Scenario: {scenario.type.value}")
    print(f"  Primary Goal: {goal.primary_goal}")
    print(f"  Max Turns: {goal.max_conversation_turns}")
    
    try:
        async with caller:
            print("\nStarting custom caller test...")
            success = await caller.start_call(timeout=45.0)
            
            print(f"\nResults:")
            print(f"  Success: {'✅ YES' if success else '❌ NO'}")
            print(f"  Conversation Turns: {caller.conversation_turns}")
            print(f"  Goals Achieved: {caller.goals_achieved}")
            print(f"  Goal Achievement Rate: {len(caller.goals_achieved)}/{len(goal.success_criteria)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


async def example_3_performance_monitoring():
    """Example 3: Using performance monitoring during tests."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Performance Monitoring")
    print("="*60)
    
    monitor = PerformanceMonitor()
    monitor.start_monitoring()
    
    bridge_url = "ws://localhost:8000/ws/telephony"
    
    # Test multiple scenarios with monitoring
    scenarios = [
        create_difficult_card_replacement_caller,
        create_confused_elderly_caller,
    ]
    
    for i, caller_factory in enumerate(scenarios):
        caller_name = f"TestCaller{i+1}"
        monitor.record_call_start(caller_name)
        
        start_time = datetime.now()
        
        try:
            async with caller_factory(bridge_url) as caller:
                success = await caller.start_call(timeout=30.0)
                
                duration = (datetime.now() - start_time).total_seconds()
                
                if success:
                    monitor.record_call_success(duration, caller.conversation_turns)
                    print(f"✅ {caller_name}: {duration:.1f}s, {caller.conversation_turns} turns")
                else:
                    monitor.record_call_failure(duration)
                    print(f"❌ {caller_name}: Failed after {duration:.1f}s")
                    
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            monitor.record_call_failure(duration)
            print(f"❌ {caller_name}: Error after {duration:.1f}s - {e}")
            
        await asyncio.sleep(1.0)
    
    # Generate performance report
    report = monitor.get_performance_report()
    print(f"\nPerformance Report:")
    print(f"  Total Calls: {report['total_calls']}")
    print(f"  Success Rate: {report['success_rate']:.1%}")
    print(f"  Average Duration: {report['average_call_duration']:.1f}s")
    print(f"  Average Turns: {report['average_conversation_turns']:.1f}")
    print(f"  Calls per Minute: {report['calls_per_minute']:.1f}")


async def example_4_batch_testing():
    """Example 4: Batch testing with configuration file."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Batch Testing with Configuration")
    print("="*60)
    
    # Generate test scenarios programmatically
    generator = TestDataGenerator()
    
    personalities = ["normal", "difficult", "confused"]
    scenarios = ["card_replacement", "account_inquiry"]
    
    test_scenarios = generator.generate_test_scenarios(personalities, scenarios)
    
    print(f"Generated {len(test_scenarios)} test scenarios:")
    for i, scenario in enumerate(test_scenarios[:3]):  # Show first 3
        print(f"  {i+1}. {scenario['name']}")
        print(f"     Goal: {scenario['goal']}")
        print(f"     Personality: {scenario['personality']}")
    
    # Create a configuration structure
    config = {
        "scenarios": test_scenarios,
        "test_configurations": {
            "quick_test": {
                "scenarios": [0, 1, 2],  # First 3 scenarios
                "parallel": False
            }
        }
    }
    
    # Save configuration (in a real scenario)
    config_manager = ConfigManager()
    print(f"\nConfiguration structure created with {len(config['scenarios'])} scenarios")
    print("Ready for batch testing with caller_cli.py or batch_caller_test.py")


async def example_5_error_handling():
    """Example 5: Proper error handling and cleanup."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Error Handling and Cleanup")
    print("="*60)
    
    bridge_url = "ws://invalid:9999/ws/telephony"  # Invalid URL to trigger error
    
    try:
        async with create_difficult_card_replacement_caller(bridge_url) as caller:
            print("Starting call with invalid bridge URL...")
            success = await caller.start_call(timeout=5.0)
            print(f"Call result: {success}")
            
    except Exception as e:
        print(f"✅ Expected error caught: {type(e).__name__}: {e}")
        print("Proper cleanup performed automatically by context manager")
    
    print("\nTesting timeout handling...")
    
    # Test with very short timeout
    try:
        async with create_confused_elderly_caller("ws://localhost:8000/ws/telephony") as caller:
            success = await caller.start_call(timeout=0.1)  # Very short timeout
            print(f"Call result: {success}")
            
    except Exception as e:
        print(f"✅ Timeout handled properly: {type(e).__name__}")


async def example_6_conversation_analysis():
    """Example 6: Analyzing conversation results."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Conversation Analysis")
    print("="*60)
    
    # Simulate conversation log data (in real usage, this comes from the caller)
    conversation_log = [
        {
            "speaker": "agent",
            "text": "Hello, thank you for calling. How can I help you today?",
            "timestamp": datetime.now(),
            "duration": 3.2
        },
        {
            "speaker": "caller", 
            "text": "Hi, I need to replace my lost credit card urgently",
            "timestamp": datetime.now(),
            "duration": 2.8,
            "sentiment": "urgent"
        },
        {
            "speaker": "agent",
            "text": "I can help you with that. Let me verify your identity first",
            "timestamp": datetime.now(),
            "duration": 3.5
        },
        {
            "speaker": "caller",
            "text": "Sure, my name is John Doe and my account number is 12345",
            "timestamp": datetime.now(),
            "duration": 2.1,
            "sentiment": "cooperative"
        }
    ]
    
    from caller_utils import ConversationAnalyzer
    
    # Analyze conversation flow
    analysis = ConversationAnalyzer.analyze_conversation_flow(conversation_log)
    
    print("Conversation Analysis:")
    print(f"  Total Turns: {analysis['total_turns']}")
    print(f"  Caller Turns: {analysis['caller_turns']}")
    print(f"  Agent Turns: {analysis['agent_turns']}")
    print(f"  Turn Ratio: {analysis['turn_ratio']:.2f}")
    print(f"  Average Turn Duration: {analysis['average_turn_duration']:.1f}s")
    print(f"  Total Conversation Time: {analysis['conversation_length_seconds']:.1f}s")
    
    # Extract key phrases
    key_phrases = ConversationAnalyzer.extract_key_phrases(conversation_log, "caller")
    print(f"  Key Phrases from Caller: {key_phrases}")
    
    # Calculate goal achievement
    goals = ["card replacement", "identity verification"]
    achievement_score = ConversationAnalyzer.calculate_goal_achievement_score(goals, conversation_log)
    print(f"  Goal Achievement Score: {achievement_score:.1%}")


async def main():
    """Run all examples."""
    print("🤖 Caller Agent System - Example Usage")
    print("="*60)
    print("This script demonstrates various ways to use the caller agent system.")
    print("Make sure your bridge server is running on ws://localhost:8000/ws/telephony")
    print("\nPress Ctrl+C to exit at any time.\n")
    
    try:
        # Run examples in sequence
        await example_1_basic_usage()
        await example_2_custom_caller()
        await example_3_performance_monitoring()
        await example_4_batch_testing()
        await example_5_error_handling()
        await example_6_conversation_analysis()
        
        print("\n" + "="*60)
        print("✅ All examples completed successfully!")
        print("\nNext Steps:")
        print("1. Try running: python caller_cli.py --interactive")
        print("2. Or run batch tests: python caller_cli.py --batch scenarios.json")
        print("3. Create your own custom scenarios using the CallerAgent class")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 