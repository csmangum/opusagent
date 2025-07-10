#!/usr/bin/env python3
"""
Twilio Bridge Validation Script

This script uses MockTwilioClient to validate the Twilio bridge and endpoint.
It demonstrates how to test the complete Twilio Media Streams integration.

Usage:
    python scripts/validate_twilio_bridge.py
    python scripts/validate_twilio_bridge.py --verbose
    python scripts/validate_twilio_bridge.py --test single
    python scripts/validate_twilio_bridge.py --test multi
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from opusagent.mock.mock_twilio_client import MockTwilioClient


async def test_single_turn(bridge_url: str, logger: logging.Logger) -> bool:
    """Test a single turn conversation."""
    logger.info("Starting single turn test...")
    
    # Use existing mock audio if available
    test_audio_files = [
        "opusagent/mock/audio/greetings/greetings_01.wav",
        "opusagent/mock/audio/customer_service/customer_service_01.wav",
        "opusagent/mock/audio/default/default_01.wav"
    ]
    
    # Find first existing audio file
    test_audio = None
    for audio_file in test_audio_files:
        if Path(audio_file).exists():
            test_audio = audio_file
            break
    
    if not test_audio:
        logger.error("No test audio files found. Please ensure mock audio files exist.")
        return False
    
    try:
        async with MockTwilioClient(bridge_url, logger=logger) as client:
            # Initiate call flow
            success = await client.initiate_call_flow()
            if not success:
                logger.error("Failed to initiate call flow")
                return False
            
            # Wait for AI greeting
            greeting = await client.wait_for_ai_greeting(timeout=20.0)
            if greeting:
                logger.info(f"✅ Received AI greeting: {len(greeting)} chunks")
            else:
                logger.warning("⚠️ No AI greeting received")
            
            # Send user audio
            logger.info(f"Sending user audio: {test_audio}")
            await client.send_user_audio(test_audio)
            
            # Wait for AI response
            response = await client.wait_for_ai_response(timeout=30.0)
            if response:
                logger.info(f"✅ Received AI response: {len(response)} chunks")
            else:
                logger.error("❌ No AI response received")
                return False
            
            # End call
            await client.send_stop()
            
            # Save audio for analysis
            client.save_collected_audio("validation_output")
            
            logger.info("✅ Single turn test completed successfully")
            return True
            
    except Exception as e:
        logger.error(f"❌ Single turn test failed: {e}")
        return False


async def test_multi_turn(bridge_url: str, logger: logging.Logger) -> bool:
    """Test a multi-turn conversation."""
    logger.info("Starting multi-turn test...")
    
    # Use multiple audio files for conversation
    audio_files = [
        "opusagent/mock/audio/greetings/greetings_01.wav",
        "opusagent/mock/audio/customer_service/customer_service_01.wav",
        "opusagent/mock/audio/card_replacement/card_replacement_01.wav"
    ]
    
    # Filter to existing files
    existing_files = [f for f in audio_files if Path(f).exists()]
    if not existing_files:
        logger.error("No test audio files found for multi-turn test")
        return False
    
    logger.info(f"Using {len(existing_files)} audio files for multi-turn test")
    
    try:
        async with MockTwilioClient(bridge_url, logger=logger) as client:
            # Run multi-turn conversation
            result = await client.multi_turn_conversation(existing_files)
            
            if result["success"]:
                logger.info(f"✅ Multi-turn test completed: {result['completed_turns']}/{result['total_turns']} turns")
                return True
            else:
                logger.error(f"❌ Multi-turn test failed: {result.get('error', 'Unknown error')}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Multi-turn test failed: {e}")
        return False


async def test_protocol_compliance(bridge_url: str, logger: logging.Logger) -> bool:
    """Test protocol compliance and message flow."""
    logger.info("Starting protocol compliance test...")
    
    try:
        async with MockTwilioClient(bridge_url, logger=logger) as client:
            # Test each protocol step
            
            # 1. Connected
            success = await client.send_connected()
            if not success:
                logger.error("❌ Failed to send connected message")
                return False
            logger.info("✅ Connected message sent")
            
            # 2. Start
            success = await client.send_start()
            if not success:
                logger.error("❌ Failed to send start message")
                return False
            logger.info("✅ Start message sent")
            
            # 3. Wait for initial response
            await asyncio.sleep(2)
            
            # 4. Send DTMF
            await client.send_dtmf("1")
            logger.info("✅ DTMF sent")
            
            # 5. Wait for any marks or responses
            await asyncio.sleep(3)
            
            # 6. Stop
            await client.send_stop()
            logger.info("✅ Stop message sent")
            
            # Check received messages
            logger.info(f"Protocol test completed. Received {len(client.received_messages)} messages")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Protocol compliance test failed: {e}")
        return False


async def test_live_conversation(bridge_url: str, logger: logging.Logger) -> bool:
    """Test live conversation with microphone input (interactive recording)."""
    logger.info("Starting live conversation test...")
    logger.info("NOTE: This test requires microphone input and user interaction")
    
    try:
        async with MockTwilioClient(bridge_url, logger=logger) as client:
            # Run live conversation
            result = await client.simple_live_conversation_test()
            
            if result:
                logger.info("✅ Live conversation test completed successfully")
                return True
            else:
                logger.error("❌ Live conversation test failed")
                return False
                
    except Exception as e:
        logger.error(f"❌ Live conversation test failed: {e}")
        return False


async def test_realtime_conversation(bridge_url: str, logger: logging.Logger) -> bool:
    """Test real-time conversation with continuous audio streaming."""
    logger.info("Starting real-time conversation test...")
    logger.info("NOTE: This test streams microphone audio continuously in real-time")
    
    try:
        async with MockTwilioClient(bridge_url, logger=logger) as client:
            # Run real-time conversation
            result = await client.simple_realtime_conversation_test()
            
            if result:
                logger.info("✅ Real-time conversation test completed successfully")
                return True
            else:
                logger.error("❌ Real-time conversation test failed")
                return False
                
    except Exception as e:
        logger.error(f"❌ Real-time conversation test failed: {e}")
        return False


def setup_logging(verbose: bool) -> logging.Logger:
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


async def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description="Validate Twilio Bridge with MockTwilioClient")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--bridge-url", default="ws://localhost:8000/twilio-agent", help="Bridge WebSocket URL")
    parser.add_argument("--test", choices=["single", "multi", "protocol", "live", "realtime", "all"], default="all", help="Test to run")
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.verbose)
    
    logger.info("🚀 Starting Twilio Bridge Validation")
    logger.info(f"Bridge URL: {args.bridge_url}")
    logger.info(f"Test: {args.test}")
    
    # Ensure output directory exists
    Path("validation_output").mkdir(exist_ok=True)
    
    # Run tests
    results = {}
    
    if args.test == "all":
        tests = [
            ("Protocol Compliance", test_protocol_compliance),
            ("Single Turn", test_single_turn),
            ("Multi Turn", test_multi_turn),
            ("Live Conversation", test_live_conversation),
            ("Real-time Streaming", test_realtime_conversation),
        ]
    else:
        test_map = {
            "single": ("Single Turn", test_single_turn),
            "multi": ("Multi Turn", test_multi_turn),
            "protocol": ("Protocol Compliance", test_protocol_compliance),
            "live": ("Live Conversation", test_live_conversation),
            "realtime": ("Real-time Streaming", test_realtime_conversation),
        }
        tests = [test_map[args.test]]
    
    # Run selected tests
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            success = await test_func(args.bridge_url, logger)
            results[test_name] = success
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"{test_name}: {status}")
        except Exception as e:
            logger.error(f"{test_name}: ❌ ERROR - {e}")
            results[test_name] = False
        
        # Wait between tests
        if len(tests) > 1:
            await asyncio.sleep(2)
    
    # Print summary
    logger.info("\n" + "="*50)
    logger.info("VALIDATION SUMMARY")
    logger.info("="*50)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    passed = sum(results.values())
    total = len(results)
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Twilio bridge is ready for use.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 