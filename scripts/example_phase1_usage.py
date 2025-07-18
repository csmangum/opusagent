#!/usr/bin/env python3
"""
Simple example demonstrating Phase 1 enhancements to MockAudioCodesClient.

This script shows how to use the new Phase 1 features:
- Session resume
- Connection validation  
- DTMF events
- Session status monitoring
"""

import asyncio
import logging
from opusagent.mock.mock_audiocodes_client import MockAudioCodesClient


async def example_phase1_features():
    """Demonstrate key Phase 1 features."""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Bridge URL (adjust as needed)
    bridge_url = "ws://localhost:8000/caller-agent"
    
    print("=== Phase 1 Enhancement Example ===")
    
    async with MockAudioCodesClient(bridge_url) as client:
        try:
            # Step 1: Initiate session
            print("\n1. Initiating session...")
            success = await client.initiate_session()
            if not success:
                print("❌ Session initiation failed")
                return
            
            print("✅ Session initiated successfully")
            
            # Step 2: Validate connection (optional)
            print("\n2. Validating connection...")
            validation_success = await client.validate_connection()
            if validation_success:
                print("✅ Connection validated")
            else:
                print("⚠️  Connection validation failed (this is normal if bridge doesn't support it)")
            
            # Step 3: Send DTMF event
            print("\n3. Sending DTMF event...")
            dtmf_success = await client.send_dtmf_event("1")
            if dtmf_success:
                print("✅ DTMF event sent")
            else:
                print("❌ DTMF event failed")
            
            # Step 4: Check session status
            print("\n4. Checking session status...")
            status = client.get_session_status()
            print(f"   Conversation ID: {status['conversation_id']}")
            print(f"   Session Accepted: {status['session_accepted']}")
            print(f"   Connection Validated: {status['connection_validated']}")
            print(f"   Activities Count: {status['activities_count']}")
            
            # Step 5: Send custom activity
            print("\n5. Sending custom activity...")
            custom_activity = {
                "type": "event",
                "name": "example_event",
                "value": "example_value"
            }
            activity_success = await client.send_custom_activity(custom_activity)
            if activity_success:
                print("✅ Custom activity sent")
            else:
                print("❌ Custom activity failed")
            
            # Step 6: End session
            print("\n6. Ending session...")
            await client.end_session("Phase 1 example completed")
            print("✅ Session ended")
            
            print("\n🎉 Phase 1 example completed successfully!")
            
        except Exception as e:
            print(f"❌ Example failed: {e}")


async def example_session_resume():
    """Demonstrate session resume functionality."""
    
    bridge_url = "ws://localhost:8000/caller-agent"
    
    print("\n=== Session Resume Example ===")
    
    async with MockAudioCodesClient(bridge_url) as client:
        try:
            # Step 1: Create initial session
            print("\n1. Creating initial session...")
            success = await client.initiate_session()
            if not success:
                print("❌ Initial session failed")
                return
            
            conversation_id = client.conversation_id
            print(f"✅ Initial session created: {conversation_id}")
            
            # Step 2: End session
            print("\n2. Ending session...")
            await client.end_session("Testing resume")
            print("✅ Session ended")
            
            # Step 3: Reset state
            print("\n3. Resetting client state...")
            client.reset_session_state()
            print("✅ State reset")
            
            # Step 4: Resume session
            print("\n4. Resuming session...")
            if conversation_id:
                resume_success = await client.resume_session(conversation_id)
                if resume_success:
                    print("✅ Session resumed successfully")
                else:
                    print("❌ Session resume failed")
            else:
                print("❌ No conversation ID available")
            
        except Exception as e:
            print(f"❌ Session resume example failed: {e}")


async def example_multi_turn_conversation():
    """Demonstrate multi-turn conversation with available audio files."""
    
    from pathlib import Path
    
    bridge_url = "ws://localhost:8000/caller-agent"
    
    print("\n=== Multi-turn Conversation Example ===")
    
    # Use available audio files for testing
    audio_files = [
        "opusagent/mock/audio/greetings/greetings_01.wav",
        "opusagent/mock/audio/customer_service/customer_service_01.wav",
        "opusagent/mock/audio/default/default_01.wav"
    ]
    
    # Verify files exist
    missing_files = [f for f in audio_files if not Path(f).exists()]
    if missing_files:
        print(f"Missing audio files: {missing_files}")
        print("Skipping multi-turn conversation example")
        return
    
    print(f"Using {len(audio_files)} audio files for conversation:")
    for audio_file in audio_files:
        print(f"  - {Path(audio_file).name}")
    
    async with MockAudioCodesClient(bridge_url) as client:
        try:
            # Run multi-turn conversation
            result = await client.multi_turn_conversation(audio_files)
            
            print(f"\nConversation Results:")
            print(f"  Completed turns: {result['completed_turns']}/{result['total_turns']}")
            print(f"  Success: {result['success']}")
            print(f"  Greeting received: {result.get('greeting_received', False)}")
            
            if result.get('error'):
                print(f"  Error: {result['error']}")
            
            if result['success']:
                print("✅ Multi-turn conversation completed successfully!")
            else:
                print("❌ Multi-turn conversation failed")
                
        except Exception as e:
            print(f"❌ Multi-turn conversation example failed: {e}")


async def main():
    """Run the Phase 1 examples."""
    
    print("Phase 1 Enhancement Examples")
    print("=" * 40)
    
    # Run basic features example
    await example_phase1_features()
    
    # Run session resume example
    await example_session_resume()
    
    # Run multi-turn conversation example
    await example_multi_turn_conversation()
    
    print("\n" + "=" * 40)
    print("Examples completed!")


if __name__ == "__main__":
    asyncio.run(main()) 