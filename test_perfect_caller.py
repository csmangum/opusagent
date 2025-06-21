#!/usr/bin/env python3
"""
Test script for the perfect caller agent.

This script demonstrates a caller who provides all necessary information
in the first message: "Hi I need to replace my lost gold card, can you send it to the address on file?"
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from opusagent.caller_agent import create_perfect_card_replacement_caller

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_perfect_caller():
    """Test the perfect caller agent."""

    logger.info("🧪 Testing Perfect Caller Agent")
    logger.info("=" * 50)

    # Create the perfect caller
    caller = create_perfect_card_replacement_caller()

    try:
        async with caller:
            logger.info("✅ Perfect caller created successfully")
            logger.info(f"   Name: {caller.caller_name}")
            logger.info(f"   Phone: {caller.caller_phone}")
            logger.info(f"   Personality: {caller.personality.type.value}")
            logger.info(f"   Goal: {caller.scenario.goal.primary_goal}")
            logger.info(
                f"   Expected first message: 'Hi I need to replace my lost gold card, can you send it to the address on file?'"
            )

            # Start the call
            logger.info("\n📞 Starting call...")
            success = await caller.start_call(timeout=30.0)

            if success:
                logger.info("✅ Call completed successfully")

                # Get results
                results = caller.get_call_results()
                logger.info(f"   Success: {results['success']}")
                logger.info(f"   Success rate: {results['success_rate']:.1%}")
                logger.info(f"   Goals achieved: {results['goals_achieved']}")
                logger.info(f"   Conversation turns: {results['conversation_turns']}")
                logger.info(f"   Max turns reached: {results['max_turns_reached']}")

                if results["success"]:
                    logger.info("🎉 Perfect caller achieved all goals!")
                else:
                    logger.warning("⚠️  Perfect caller did not achieve all goals")

            else:
                logger.error("❌ Call failed to start or complete")

    except Exception as e:
        logger.error(f"❌ Error during perfect caller test: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Main function to run the perfect caller test."""
    logger.info("🚀 Starting Perfect Caller Agent Test")

    try:
        await test_perfect_caller()
    except KeyboardInterrupt:
        logger.info("⏹️  Test interrupted by user")
    except Exception as e:
        logger.error(f"💥 Test failed with error: {e}")
        sys.exit(1)

    logger.info("🏁 Perfect Caller Agent Test completed")


if __name__ == "__main__":
    asyncio.run(main())
