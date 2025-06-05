#!/usr/bin/env python3
"""
Banking Conversation Test - Uses real banking audio files from /static

This script demonstrates a realistic banking customer service conversation
using the actual audio files in the static directory.
"""

import asyncio
import logging
from pathlib import Path

from mock_twilio_client import MockTwilioClient

# Configure logging at the module level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_banking_conversation_flow():
    """Test a realistic banking conversation using static audio files."""

    # Bridge server URL 
    bridge_url = "ws://localhost:6060/twilio-ws"
    
    # Define conversation flow using available audio files
    conversation_flow = [
        {
            "file": "static/tell_me_about_your_bank.wav",
            "description": "Customer asks about bank services",
            "expected_response": "AI should provide bank information"
        },
        {
            "file": "static/what_is_my_balance.wav", 
            "description": "Customer asks for account balance",
            "expected_response": "AI should ask for account verification"
        },
        {
            "file": "static/need_to_replace_card.wav",
            "description": "Customer needs card replacement",
            "expected_response": "AI should start card replacement process"
        },
        {
            "file": "static/my_gold_card.wav",
            "description": "Customer specifies gold card",
            "expected_response": "AI should confirm gold card replacement"
        },
        {
            "file": "static/i_lost_it.wav",
            "description": "Customer explains they lost the card",
            "expected_response": "AI should provide next steps for lost card"
        },
        {
            "file": "static/thanks_thats_all.wav",
            "description": "Customer thanks and ends conversation",
            "expected_response": "AI should provide polite closure"
        }
    ]
    
    # Filter to only existing files
    available_files = []
    for step in conversation_flow:
        if Path(step["file"]).exists():
            available_files.append(step)
            logger.info(f"✅ Found: {step['file']} - {step['description']}")
        else:
            logger.warning(f"❌ Missing: {step['file']}")
    
    if len(available_files) < 2:
        logger.error("Not enough audio files available for conversation test")
        return False
    
    logger.info(f"\n🎭 Starting banking conversation with {len(available_files)} turns...")
    
    try:
        async with MockTwilioClient(bridge_url, logger=logger) as client:
            # Initiate call flow
            logger.info("📞 Initiating call...")
            success = await client.initiate_call_flow()
            if not success:
                logger.error("Failed to initiate call flow")
                return False
            
            # Wait for AI greeting
            logger.info("👋 Waiting for AI greeting...")
            greeting = await client.wait_for_ai_greeting(timeout=20.0)
            if greeting:
                logger.info(f"✅ AI Greeting received: {len(greeting)} audio chunks")
            else:
                logger.warning("⚠️ No AI greeting received")
            
            # Process each conversation turn
            for i, step in enumerate(available_files, 1):
                logger.info(f"\n🗣️ Turn {i}: {step['description']}")
                logger.info(f"📁 Playing: {Path(step['file']).name}")
                
                # Send user audio
                await client.send_user_audio(step["file"])
                
                # Wait for AI response
                logger.info("🤖 Waiting for AI response...")
                response = await client.wait_for_ai_response(timeout=30.0)
                
                if response:
                    logger.info(f"✅ AI Response: {len(response)} audio chunks")
                    logger.info(f"💭 Expected: {step['expected_response']}")
                else:
                    logger.error(f"❌ No AI response for turn {i}")
                
                # Brief pause between turns
                await asyncio.sleep(1.5)
            
            # End call
            logger.info("\n📴 Ending call...")
            await client.send_stop()
            
            # Save collected audio
            client.save_collected_audio()
            
            logger.info("✅ Banking conversation test completed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Banking conversation test failed: {e}")
        return False


async def test_card_replacement_flow():
    """Test specific card replacement conversation."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    bridge_url = "ws://localhost:6060/twilio-ws"
    
    # Card replacement specific flow
    card_flow = [
        "static/need_to_replace_card.wav",
        "static/my_gold_card.wav", 
        "static/i_lost_it.wav",
        "static/yes_that_address.wav",
        "static/thanks_thats_all.wav"
    ]
    
    # Filter existing files
    existing_files = [f for f in card_flow if Path(f).exists()]
    
    if not existing_files:
        logger.error("No card replacement audio files available")
        return False
    
    logger.info(f"🔄 Testing card replacement flow with {len(existing_files)} files...")
    
    try:
        async with MockTwilioClient(bridge_url, logger=logger) as client:
            result = await client.multi_turn_conversation(
                existing_files,
                wait_for_greeting=True,
                turn_delay=2.0,
                chunk_delay=0.02
            )
            
            client.save_collected_audio()
            
            if result["success"]:
                logger.info("✅ Card replacement flow completed successfully")
                return True
            else:
                logger.error(f"❌ Card replacement flow failed: {result}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Card replacement test failed: {e}")
        return False


async def test_balance_inquiry_flow():
    """Test balance inquiry conversation."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    bridge_url = "ws://localhost:6060/twilio-ws"
    
    # Balance inquiry flow
    balance_flow = [
        "static/what_is_my_balance.wav",
        "static/when_last_payment.wav",
        "static/actually_i_moved.wav",
        "static/yes_that_address.wav",
        "static/thanks_thats_all.wav"
    ]
    
    existing_files = [f for f in balance_flow if Path(f).exists()]
    
    if not existing_files:
        logger.error("No balance inquiry audio files available")
        return False
    
    logger.info(f"💰 Testing balance inquiry flow with {len(existing_files)} files...")
    
    try:
        async with MockTwilioClient(bridge_url, logger=logger) as client:
            result = await client.simple_conversation_test(
                existing_files,
                session_name="BalanceInquiry"
            )
            
            return result
            
    except Exception as e:
        logger.error(f"❌ Balance inquiry test failed: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    async def main():
        """Run banking conversation tests."""
        if len(sys.argv) > 1:
            test_type = sys.argv[1]
            
            if test_type == "full":
                success = await test_banking_conversation_flow()
            elif test_type == "card":
                success = await test_card_replacement_flow() 
            elif test_type == "balance":
                success = await test_balance_inquiry_flow()
            else:
                print("Available tests: full, card, balance")
                return
            
            if success:
                print(f"✅ {test_type.title()} test passed")
            else:
                print(f"❌ {test_type.title()} test failed")
        else:
            print("🏦 Running all banking conversation tests...")
            
            tests = [
                ("Full Conversation", test_banking_conversation_flow),
                ("Card Replacement", test_card_replacement_flow),
                ("Balance Inquiry", test_balance_inquiry_flow),
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
                await asyncio.sleep(3)
            
            print("\n--- Banking Test Summary ---")
            for test_name, success in results.items():
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"{test_name}: {status}")
            
            passed = sum(results.values())
            total = len(results)
            print(f"\nOverall: {passed}/{total} banking tests passed")

    # Run the tests
    asyncio.run(main()) 