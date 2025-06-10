#!/usr/bin/env python3
"""
Multi-Turn Conversation Test Script

Simple script to test multi-turn conversations using the MockAudioCodesClient.
This demonstrates how to have extended conversations with the AI using multiple audio files.
"""

import asyncio
import sys
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opusagent.config.logging_config import configure_logging
from validate.mock_audiocodes_client import MockAudioCodesClient

# Load environment variables
load_dotenv()

# Configure logging
logger = configure_logging("multi_turn_test")

# Configuration
BRIDGE_URL = "ws://localhost:8000/ws/telephony"

# Example conversation flows - modify these lists for your own testing
REPLACEMENT_CARD_CONVERSATION = [
    "static/need_to_replace_card.wav",  # "Hi, I need to replace my card"
    "static/my_gold_card.wav",  # "My gold card"
    "static/i_lost_it.wav",  # "I lost it"
    "static/yes_that_address.wav",
    "static/thanks_thats_all.wav",
]


async def run_multi_turn_test(audio_files: List[str], test_name: str = "MultiTurnTest"):
    """Run a multi-turn conversation test with the given audio files."""
    logger.info(f"[TEST] Starting {test_name}")
    logger.info("=" * 50)
    
    # Filter to only existing files
    existing_files = []
    for audio_file in audio_files:
        if Path(audio_file).exists():
            existing_files.append(audio_file)
        else:
            logger.warning(f"[TEST] Audio file not found: {audio_file}")
    
    if not existing_files:
        logger.error(f"[TEST] No audio files found for {test_name}")
        logger.error("   Please ensure the audio files exist in the static/ directory")
        return False
    
    logger.info(f"[TEST] Using {len(existing_files)} audio files:")
    for i, file in enumerate(existing_files, 1):
        logger.info(f"   {i}. {Path(file).name}")
    
    try:
        async with MockAudioCodesClient(
            bridge_url=BRIDGE_URL,
            bot_name=f"{test_name}Bot",
            caller="+15551234567",
            logger=logger
        ) as mock_client:
            
            # Run the multi-turn conversation
            success = await mock_client.simple_conversation_test(
                audio_files=existing_files,
                session_name=test_name
            )
            
            if success:
                logger.info(f"\n[TEST] {test_name} completed successfully!")
            else:
                logger.error(f"\n[TEST] {test_name} failed!")
            
            return success
            
    except Exception as e:
        logger.error(f"[TEST] {test_name} error: {e}")
        return False


async def main():
    """Main function - choose which conversation to run."""
    logger.info("[MAIN] Multi-Turn Conversation Test Tool")
    logger.info("=" * 50)
    

    logger.info("[MAIN] Running replacement card conversation flow")
    success = await run_multi_turn_test(
        REPLACEMENT_CARD_CONVERSATION, 
        "ReplacementCardConversation"
    )
    logger.info(f"[MAIN] Replacement card conversation flow completed: {success}")
    



if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n[MAIN] Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"[MAIN] Unexpected error: {e}")
        sys.exit(1) 