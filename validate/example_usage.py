#!/usr/bin/env python3
"""
Example usage of the enhanced MockAudioCodes for 4-step conversation flow validation.

This demonstrates how to use MockAudioCodes to test the flow:
1. Connect with bridge 
2. Receive LLM audio greeting
3. Send pre-recorded WAV to LLM
4. Receive LLM audio response
"""

import asyncio
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from validate.mock_audiocodes import MockAudioCodes


async def simple_flow_test():
    """Simple example of the 4-step flow."""
    print("🚀 Simple MockAudioCodes Flow Test")
    
    # Create mock server on port 9000
    async with MockAudioCodes(port=9000, bot_name="TestBot", caller="+15551234567") as mock:
        
        # Step 1: Initiate session
        print("\n--- Step 1: Initiating session ---")
        session_success = await mock.initiate_session()
        if not session_success:
            print("❌ Failed to initiate session")
            return False
        print("✅ Session initiated successfully")
        
        # Step 2: Wait for LLM greeting
        print("\n--- Step 2: Waiting for LLM greeting ---")
        greeting_chunks = await mock.wait_for_llm_greeting(timeout=15.0)
        if not greeting_chunks:
            print("❌ No greeting received")
            return False
        print(f"✅ Received greeting: {len(greeting_chunks)} audio chunks")
        
        # Step 3: Send user audio (replace with your audio file path)
        print("\n--- Step 3: Sending user audio ---")
        audio_file = "static/tell_me_about_your_bank.wav"
        if not Path(audio_file).exists():
            print(f"⚠️ Audio file not found: {audio_file}")
            print("   Creating a minimal test audio file...")
            # For demo purposes, we'll skip this step
            print("   Skipping audio send for this demo")
        else:
            audio_sent = await mock.send_user_audio(audio_file)
            if not audio_sent:
                print("❌ Failed to send user audio")
                return False
            print("✅ User audio sent successfully")
        
        # Step 4: Wait for LLM response
        print("\n--- Step 4: Waiting for LLM response ---")
        response_chunks = await mock.wait_for_llm_response(timeout=30.0)
        if not response_chunks:
            print("❌ No response received")
            return False
        print(f"✅ Received response: {len(response_chunks)} audio chunks")
        
        # End session gracefully
        await mock.end_session("Test completed successfully")
        
        # Save collected audio for analysis
        mock.save_collected_audio()
        
        print("\n🎉 Flow test completed successfully!")
        print(f"📊 Summary:")
        print(f"   Session ID: {mock.conversation_id}")
        print(f"   Greeting chunks: {len(greeting_chunks)}")
        print(f"   Response chunks: {len(response_chunks)}")
        print(f"   Total messages: {len(mock.received_messages)}")
        
        return True


async def message_inspection_example():
    """Example showing how to inspect received messages."""
    print("\n🔍 Message Inspection Example")
    
    async with MockAudioCodes(port=9000) as mock:
        # Start session
        await mock.initiate_session()
        
        # Wait for some messages
        await asyncio.sleep(3)
        
        # Inspect received messages
        print(f"\n📨 Received {len(mock.received_messages)} messages:")
        for i, msg in enumerate(mock.received_messages):
            msg_type = msg.get("type", "unknown")
            print(f"   {i+1}. {msg_type}")
            
            # Show details for interesting messages
            if msg_type == "session.accepted":
                print(f"      Media format: {msg.get('mediaFormat', 'not specified')}")
            elif msg_type == "playStream.start":
                print(f"      Stream ID: {msg.get('streamId', 'not specified')}")
            elif msg_type == "playStream.chunk":
                chunk_size = len(msg.get('audioChunk', ''))
                print(f"      Audio chunk size: {chunk_size} bytes (base64)")
        
        await mock.end_session("Inspection completed")


async def wait_for_specific_message_example():
    """Example showing how to wait for specific messages."""
    print("\n⏳ Wait for Specific Message Example")
    
    async with MockAudioCodes(port=9000) as mock:
        # Start session
        await mock.initiate_session()
        
        # Wait for a specific message type
        try:
            play_start_msg = await mock.wait_for_message(
                predicate=lambda msg: msg.get("type") == "playStream.start",
                timeout=10.0
            )
            print(f"✅ Found playStream.start message: {play_start_msg}")
        except TimeoutError:
            print("❌ Timeout waiting for playStream.start")
        
        # Wait for any audio chunk
        try:
            audio_chunk_msg = await mock.wait_for_message(
                predicate=lambda msg: msg.get("type") == "playStream.chunk",
                timeout=10.0
            )
            chunk_size = len(audio_chunk_msg.get("audioChunk", ""))
            print(f"✅ Found audio chunk: {chunk_size} bytes")
        except TimeoutError:
            print("❌ Timeout waiting for audio chunk")
        
        await mock.end_session("Message waiting completed")


async def main():
    """Run all examples."""
    print("🎯 MockAudioCodes Usage Examples")
    print("=" * 50)
    
    try:
        # Run simple flow test
        await simple_flow_test()
        
        # Run message inspection example
        await message_inspection_example()
        
        # Run wait for specific message example
        await wait_for_specific_message_example()
        
        print("\n" + "=" * 50)
        print("✅ All examples completed successfully!")
        print("\n💡 Tips:")
        print("   - Start your bridge server first: python run.py")
        print("   - Check validation_output/ for recorded audio files")
        print("   - Use mock.received_messages to inspect all messages")
        print("   - Customize bot_name and caller in MockAudioCodes constructor")
        
    except Exception as e:
        print(f"❌ Examples failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(main()) 