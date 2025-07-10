#!/usr/bin/env python3
"""
Test Live Conversation with MockTwilioClient

This script demonstrates how to use the MockTwilioClient to have a live conversation
with the AI using your microphone instead of pre-recorded audio files.

Usage:
    python scripts/test_live_conversation.py
    python scripts/test_live_conversation.py --verbose
    python scripts/test_live_conversation.py --bridge-url ws://localhost:8000/twilio-agent
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from opusagent.mock.mock_twilio_client import MockTwilioClient


def setup_logging(verbose: bool) -> logging.Logger:
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


async def test_live_conversation(bridge_url: str, logger: logging.Logger) -> bool:
    """Test live conversation with real-time microphone streaming."""
    logger.info("🎤 Starting Real-time Live Conversation Test")
    logger.info(f"Bridge URL: {bridge_url}")
    
    try:
        async with MockTwilioClient(bridge_url, logger=logger) as client:
            logger.info("✅ Connected to bridge server")
            
            # Test the real-time conversation
            success = await client.simple_realtime_conversation_test()
            
            if success:
                logger.info("✅ Real-time conversation test completed successfully!")
                return True
            else:
                logger.error("❌ Real-time conversation test failed")
                return False
                
    except Exception as e:
        logger.error(f"❌ Real-time conversation test failed: {e}")
        return False


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test Real-time Conversation with MockTwilioClient")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--bridge-url", default="ws://localhost:8000/twilio-agent", 
                       help="Bridge WebSocket URL (default: ws://localhost:8000/twilio-agent)")
    parser.add_argument("--voice-threshold", type=float, default=0.01,
                       help="Voice activation threshold (default: 0.01)")
    parser.add_argument("--silence-timeout", type=float, default=2.0,
                       help="Silence timeout in seconds (default: 2.0)")
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.verbose)
    
    # Print instructions
    logger.info("=" * 60)
    logger.info("🎙️  REAL-TIME CONVERSATION TEST")
    logger.info("=" * 60)
    logger.info("This test streams your microphone audio in real-time to the AI.")
    logger.info("")
    logger.info("REQUIREMENTS:")
    logger.info("1. Make sure your microphone is working and not muted")
    logger.info("2. The OpusAgent server should be running (python -m opusagent.main)")
    logger.info("3. You should have a valid OpenAI API key configured")
    logger.info("4. Ensure no other apps are using your microphone")
    logger.info("")
    logger.info("HOW IT WORKS:")
    logger.info("1. The AI will greet you first")
    logger.info("2. Your microphone goes LIVE immediately")
    logger.info("3. Speak naturally - audio streams in real-time")
    logger.info("4. The AI responds when you pause speaking")
    logger.info("5. Continue the natural conversation")
    logger.info("6. Press Ctrl+C to end the conversation")
    logger.info("")
    logger.info("AUDIO SETTINGS:")
    logger.info(f"• Voice threshold: {args.voice_threshold}")
    logger.info(f"• Silence timeout: {args.silence_timeout}s")
    logger.info("")
    logger.info("=" * 60)
    
    # Ask for confirmation
    response = input("Ready to start real-time conversation? (y/n): ").strip().lower()
    if response != 'y':
        logger.info("Test cancelled by user")
        return 0
    
    # Run the test
    success = await test_live_conversation(args.bridge_url, logger)
    
    if success:
        logger.info("🎉 Real-time conversation test completed successfully!")
        return 0
    else:
        logger.error("❌ Real-time conversation test failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 