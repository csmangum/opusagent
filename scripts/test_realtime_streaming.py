#!/usr/bin/env python3
"""
Test Real-time Audio Streaming with MockTwilioClient

This script demonstrates real-time audio streaming where microphone audio
is sent continuously in chunks to the bridge without any recording.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from opusagent.mock.mock_twilio_client import MockTwilioClient


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('realtime_test.log')
        ]
    )
    return logging.getLogger(__name__)


async def test_realtime_streaming(
    bridge_url: str, 
    logger: logging.Logger,
    voice_threshold: float = 0.01,
    silence_timeout: float = 2.0
) -> bool:
    """Test real-time audio streaming."""
    logger.info("🎤 Starting Real-time Audio Streaming Test")
    logger.info(f"Bridge URL: {bridge_url}")
    logger.info(f"Voice Threshold: {voice_threshold}")
    logger.info(f"Silence Timeout: {silence_timeout}s")
    
    try:
        async with MockTwilioClient(bridge_url, logger=logger) as client:
            logger.info("✅ Connected to bridge server")
            
            # Run real-time conversation with custom settings
            result = await client.live_realtime_conversation(
                wait_for_greeting=True,
                voice_activation_threshold=voice_threshold,
                silence_timeout=silence_timeout
            )
            
            # Save any collected audio
            client.save_collected_audio("realtime_test_output")
            
            if result["success"]:
                logger.info("✅ Real-time streaming test completed successfully!")
                logger.info(f"Duration: {result.get('total_duration', 0):.1f}s")
                logger.info(f"Chunks sent: {result.get('total_audio_chunks_sent', 0)}")
                return True
            else:
                logger.error("❌ Real-time streaming test failed")
                if result.get("error"):
                    logger.error(f"Error: {result['error']}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Real-time streaming test failed: {e}")
        return False


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test Real-time Audio Streaming with MockTwilioClient")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--bridge-url", default="ws://localhost:8000/twilio-agent", 
                       help="Bridge WebSocket URL (default: ws://localhost:8000/twilio-agent)")
    parser.add_argument("--voice-threshold", type=float, default=0.01,
                       help="Voice activation threshold (0.001-0.1, default: 0.01)")
    parser.add_argument("--silence-timeout", type=float, default=2.0,
                       help="Silence timeout in seconds (1.0-5.0, default: 2.0)")
    parser.add_argument("--no-instructions", action="store_true", help="Skip instructions and start immediately")
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.verbose)
    
    # Validate parameters
    if not (0.001 <= args.voice_threshold <= 0.1):
        logger.error("Voice threshold must be between 0.001 and 0.1")
        return 1
    
    if not (1.0 <= args.silence_timeout <= 5.0):
        logger.error("Silence timeout must be between 1.0 and 5.0 seconds")
        return 1
    
    # Show instructions unless skipped
    if not args.no_instructions:
        logger.info("=" * 70)
        logger.info("🎙️  REAL-TIME AUDIO STREAMING TEST")
        logger.info("=" * 70)
        logger.info("This test streams your microphone audio in real-time to the AI agent.")
        logger.info("")
        logger.info("REQUIREMENTS:")
        logger.info("1. ✅ OpusAgent server running (python -m opusagent.main)")
        logger.info("2. ✅ Working microphone (not muted)")
        logger.info("3. ✅ Valid OpenAI API key configured")
        logger.info("4. ✅ No other apps using microphone")
        logger.info("5. ✅ Quiet environment (for best voice detection)")
        logger.info("")
        logger.info("HOW IT WORKS:")
        logger.info("• The AI greets you first")
        logger.info("• Your microphone goes LIVE immediately")
        logger.info("• Speak naturally - audio streams in real-time")
        logger.info("• AI responds when you pause speaking")
        logger.info("• Continue natural conversation")
        logger.info("• Press Ctrl+C to end")
        logger.info("")
        logger.info("AUDIO SETTINGS:")
        logger.info(f"• Voice threshold: {args.voice_threshold} (lower = more sensitive)")
        logger.info(f"• Silence timeout: {args.silence_timeout}s")
        logger.info("")
        logger.info("TIPS:")
        logger.info("• Speak clearly and at normal volume")
        logger.info("• Pause briefly between sentences")
        logger.info("• If AI doesn't respond, try speaking louder")
        logger.info("• Use --voice-threshold 0.005 for quieter environments")
        logger.info("• Use --silence-timeout 1.5 for faster responses")
        logger.info("")
        logger.info("=" * 70)
        
        # Ask for confirmation
        response = input("Ready to start real-time conversation? (y/n): ").strip().lower()
        if response != 'y':
            logger.info("Test cancelled by user")
            return 0
        
        print("\n🎤 Starting in 3 seconds...")
        await asyncio.sleep(1)
        print("🎤 Starting in 2 seconds...")
        await asyncio.sleep(1)
        print("🎤 Starting in 1 second...")
        await asyncio.sleep(1)
        print("🎤 GO! Your microphone is now LIVE!")
        print("")
    
    # Run the test
    success = await test_realtime_streaming(
        args.bridge_url, 
        logger, 
        args.voice_threshold, 
        args.silence_timeout
    )
    
    if success:
        logger.info("🎉 Real-time streaming test completed successfully!")
        return 0
    else:
        logger.error("❌ Real-time streaming test failed")
        return 1


if __name__ == "__main__":
    asyncio.run(main()) 