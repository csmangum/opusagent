#!/usr/bin/env python3
"""
Test script for MockTwilioClient - demonstrates how to test Twilio bridge functionality.
"""

import asyncio
import logging
from pathlib import Path
import pytest

from opusagent.local.mock_twilio_client import MockTwilioClient

# Bridge server URL (adjust based on your setup)
BRIDGE_URL = "ws://localhost:8000/twilio-agent"


@pytest.mark.asyncio
async def test_single_turn():
    """Test a single turn conversation with the bridge."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Test audio file (create or use existing)
    test_audio = "demo/user_audio/hello.wav"
    
    logger.info("Starting single turn Twilio mock test...")
    
    try:
        async with MockTwilioClient(BRIDGE_URL, logger=logger) as client:
            # Initiate the call flow
            success = await client.initiate_call_flow()
            if not success:
                logger.error("Failed to initiate call flow")
                return False
            
            # Wait for initial greeting
            greeting = await client.wait_for_ai_greeting(timeout=20.0)
            if greeting:
                logger.info(f"Received greeting: {len(greeting)} audio chunks")
            
            # Send user audio
            if Path(test_audio).exists():
                await client.send_user_audio(test_audio)
                
                # Wait for AI response
                response = await client.wait_for_ai_response(timeout=30.0)
                if response:
                    logger.info(f"Received response: {len(response)} audio chunks")
                else:
                    logger.error("No response received")
            else:
                logger.warning(f"Test audio file not found: {test_audio}")
            
            # End the call
            await client.send_stop()
            
            # Save collected audio
            client.save_collected_audio()
            
            logger.info("Single turn test completed")
            return True
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False


@pytest.mark.asyncio
async def test_multi_turn():
    """Test a multi-turn conversation with the bridge."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Test audio files for multiple turns
    audio_files = [
        "demo/user_audio/hello.wav",
        "demo/user_audio/question1.wav",
        "demo/user_audio/question2.wav",
    ]
    
    # Filter to only existing files
    existing_files = [f for f in audio_files if Path(f).exists()]
    if not existing_files:
        logger.error("No test audio files found")
        return False
    
    logger.info(f"Starting multi-turn Twilio mock test with {len(existing_files)} files...")
    
    try:
        async with MockTwilioClient(BRIDGE_URL, logger=logger) as client:
            # Run multi-turn conversation
            success = await client.simple_conversation_test(
                existing_files, 
                session_name="TwilioMockTest"
            )
            
            if success:
                logger.info("Multi-turn test completed successfully")
            else:
                logger.error("Multi-turn test failed")
            
            return success
            
    except Exception as e:
        logger.error(f"Multi-turn test failed: {e}")
        return False


@pytest.mark.asyncio
async def test_dtmf_and_marks():
    """Test DTMF and mark functionality."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    logger.info("Starting DTMF and marks test...")
    
    try:
        async with MockTwilioClient(BRIDGE_URL, logger=logger) as client:
            # Initiate call
            await client.initiate_call_flow()
            
            # Wait for greeting
            await client.wait_for_ai_greeting(timeout=10.0)
            
            # Send some DTMF digits
            await client.send_dtmf("1")
            await asyncio.sleep(1)
            await client.send_dtmf("2")
            await asyncio.sleep(1)
            await client.send_dtmf("#")
            
            # Wait a bit to see if bridge responds to DTMF
            await asyncio.sleep(5)
            
            # End call
            await client.send_stop()
            
            # Check received marks
            logger.info(f"Received {len(client.received_marks)} marks: {client.received_marks}")
            
            return True
            
    except Exception as e:
        logger.error(f"DTMF test failed: {e}")
        return False


@pytest.mark.asyncio
async def test_protocol_compliance():
    """Test that we're sending properly formatted Twilio messages."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    logger.info("Starting protocol compliance test...")
    
    try:
        async with MockTwilioClient(BRIDGE_URL, logger=logger) as client:
            logger.info(f"Stream SID: {client.stream_sid}")
            logger.info(f"Account SID: {client.account_sid}")
            logger.info(f"Call SID: {client.call_sid}")
            
            # Test the full protocol sequence
            await client.send_connected()
            await asyncio.sleep(0.5)
            
            await client.send_start()
            await asyncio.sleep(0.5)
            
            # Send a few media chunks (if we have test audio)
            test_audio = "demo/user_audio/hello.wav"
            if Path(test_audio).exists():
                chunks = client._load_audio_as_mulaw_chunks(test_audio)
                if chunks:
                    logger.info(f"Sending {min(5, len(chunks))} test chunks...")
                    for i in range(min(5, len(chunks))):
                        await client.send_media_chunk(chunks[i])
                        await asyncio.sleep(0.02)  # 20ms delay
            
            await asyncio.sleep(2)  # Wait for any response
            
            await client.send_stop()
            
            logger.info(f"Protocol test completed. Received {len(client.received_messages)} messages from bridge")
            
            return True
            
    except Exception as e:
        logger.error(f"Protocol test failed: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    async def main():
        """Run the specified test or all tests."""
        if len(sys.argv) > 1:
            test_name = sys.argv[1]
            
            if test_name == "single":
                success = await test_single_turn()
            elif test_name == "multi":
                success = await test_multi_turn()
            elif test_name == "dtmf":
                success = await test_dtmf_and_marks()
            elif test_name == "protocol":
                success = await test_protocol_compliance()
            else:
                print(f"Unknown test: {test_name}")
                print("Available tests: single, multi, dtmf, protocol")
                return
                
            if success:
                print(f"✅ Test '{test_name}' passed")
            else:
                print(f"❌ Test '{test_name}' failed")
        else:
            # Run all tests
            print("Running all Twilio mock tests...")
            
            tests = [
                ("Protocol Compliance", test_protocol_compliance),
                ("Single Turn", test_single_turn),
                ("DTMF & Marks", test_dtmf_and_marks),
                ("Multi Turn", test_multi_turn),
            ]
            
            results = {}
            for test_name, test_func in tests:
                print(f"\n--- Running {test_name} Test ---")
                try:
                    success = await test_func()
                    results[test_name] = success
                    status = "✅ PASS" if success else "❌ FAIL"
                    print(f"{test_name}: {status}")
                except Exception as e:
                    print(f"{test_name}: ❌ ERROR - {e}")
                    results[test_name] = False
                
                # Wait between tests
                await asyncio.sleep(2)
            
            print("\n--- Test Summary ---")
            for test_name, success in results.items():
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"{test_name}: {status}")
            
            passed = sum(results.values())
            total = len(results)
            print(f"\nOverall: {passed}/{total} tests passed")

    # Run the main function
    asyncio.run(main()) 