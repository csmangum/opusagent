#!/usr/bin/env python3
"""
Simple example of using the perfect caller agent.

This demonstrates how to create and use a caller that provides all necessary
information in the first message for efficient card replacement.
"""

import asyncio
from caller_agent import create_perfect_card_replacement_caller


async def main():
    """Run a simple example with the perfect caller."""
    
    print("🎯 Perfect Caller Agent Example")
    print("=" * 40)
    print("This caller will say: 'Hi I need to replace my lost gold card, can you send it to the address on file?'")
    print()
    
    # Create the perfect caller
    caller = create_perfect_card_replacement_caller()
    
    try:
        # Use async context manager for automatic cleanup
        async with caller:
            print("✅ Perfect caller created")
            print(f"   Name: {caller.caller_name}")
            print(f"   Goal: {caller.scenario.goal.primary_goal}")
            print()
            
            # Start the call
            print("📞 Starting call...")
            success = await caller.start_call()
            
            if success:
                print("✅ Call completed")
                
                # Show results
                results = caller.get_call_results()
                print(f"   Success: {results['success']}")
                print(f"   Turns: {results['conversation_turns']}")
                print(f"   Goals achieved: {len(results['goals_achieved'])}/{results['total_goals']}")
                
            else:
                print("❌ Call failed")
                
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 