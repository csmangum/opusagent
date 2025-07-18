#!/usr/bin/env python3
"""
Example usage of the modular AudioCodes mock client.

This script demonstrates how to use the new modular AudioCodes client
for testing bridge server functionality.
"""

import asyncio
import logging
from pathlib import Path

from opusagent.local.audiocodes import MockAudioCodesClient


async def basic_conversation_example():
    """Basic conversation example."""
    print("\n=== Basic Conversation Example ===")
    
    async with MockAudioCodesClient("ws://localhost:8080") as client:
        # Initiate session
        print("Initiating session...")
        success = await client.initiate_session()
        if not success:
            print("❌ Failed to initiate session")
            return
        
        print("✅ Session initiated successfully")
        
        # Get session status
        status = client.get_session_status()
        print(f"Session status: {status['status']}")
        print(f"Conversation ID: {status['conversation_id']}")
        
        # End session
        await client.end_session("Basic test completed")
        print("✅ Session ended")


async def multi_turn_conversation_example():
    """Multi-turn conversation example."""
    print("\n=== Multi-turn Conversation Example ===")
    
    # Example audio files (you would need real audio files for testing)
    audio_files = [
        "audio/greeting.wav",
        "audio/question.wav",
        "audio/followup.wav"
    ]
    
    # Check if audio files exist
    existing_files = []
    for audio_file in audio_files:
        if Path(audio_file).exists():
            existing_files.append(audio_file)
        else:
            print(f"⚠️  Audio file not found: {audio_file}")
    
    if not existing_files:
        print("❌ No audio files found for testing")
        return
    
    async with MockAudioCodesClient("ws://localhost:8080") as client:
        print(f"Running multi-turn conversation with {len(existing_files)} audio files...")
        
        # Run multi-turn conversation
        result = await client.multi_turn_conversation(existing_files)
        
        # Print results
        print(f"\n📊 Conversation Results:")
        print(f"   Completed turns: {result.completed_turns}/{result.total_turns}")
        print(f"   Success rate: {result.success_rate:.1f}%")
        if result.duration:
            print(f"   Duration: {result.duration:.2f}s")
        
        if result.greeting_received:
            print(f"   Greeting received: {result.greeting_chunks} chunks")
        
        if result.error:
            print(f"   Error: {result.error}")
        
        # Save collected audio
        client.save_collected_audio("output/")
        print("   Audio saved to output/ directory")


async def session_management_example():
    """Session management example."""
    print("\n=== Session Management Example ===")
    
    async with MockAudioCodesClient("ws://localhost:8080") as client:
        # Initiate session
        print("Initiating session...")
        success = await client.initiate_session()
        if not success:
            print("❌ Failed to initiate session")
            return
        
        print("✅ Session initiated")
        
        # Validate connection
        print("Validating connection...")
        validated = await client.validate_connection()
        if validated:
            print("✅ Connection validated")
        else:
            print("⚠️  Connection validation failed")
        
        # Send DTMF event
        print("Sending DTMF event...")
        dtmf_sent = await client.send_dtmf_event("1")
        if dtmf_sent:
            print("✅ DTMF event sent")
        else:
            print("❌ Failed to send DTMF event")
        
        # Send custom activity
        print("Sending custom activity...")
        activity_sent = await client.send_custom_activity({
            "type": "event",
            "name": "test_event",
            "value": "example_value"
        })
        if activity_sent:
            print("✅ Custom activity sent")
        else:
            print("❌ Failed to send custom activity")
        
        # Get detailed session status
        status = client.get_session_status()
        print(f"\n📊 Session Status:")
        for key, value in status.items():
            print(f"   {key}: {value}")
        
        # End session
        await client.end_session("Session management test completed")
        print("✅ Session ended")


async def simple_test_example():
    """Simple test wrapper example."""
    print("\n=== Simple Test Example ===")
    
    # Example audio files
    audio_files = [
        "audio/test1.wav",
        "audio/test2.wav"
    ]
    
    # Check if any audio files exist
    existing_files = [f for f in audio_files if Path(f).exists()]
    if not existing_files:
        print("⚠️  No audio files found, using empty list for demonstration")
        existing_files = []
    
    async with MockAudioCodesClient("ws://localhost:8080") as client:
        print("Running simple conversation test...")
        
        # Use the simple test wrapper
        success = await client.simple_conversation_test(
            existing_files,
            session_name="SimpleTest"
        )
        
        if success:
            print("✅ Simple test completed successfully")
        else:
            print("❌ Simple test failed")


async def component_inspection_example():
    """Example showing how to inspect individual components."""
    print("\n=== Component Inspection Example ===")
    
    async with MockAudioCodesClient("ws://localhost:8080") as client:
        print("Inspecting client components...")
        
        # Session manager
        print(f"\n📋 Session Manager:")
        print(f"   Config: {client.config}")
        print(f"   Session state: {client.session_manager.session_state}")
        print(f"   Stream state: {client.session_manager.stream_state}")
        
        # Audio manager
        print(f"\n🎵 Audio Manager:")
        cache_info = client.audio_manager.get_cache_info()
        print(f"   Cache info: {cache_info}")
        
        # Message handler
        print(f"\n📨 Message Handler:")
        print(f"   Received messages: {client.message_handler.get_message_count()}")
        
        # Conversation manager
        print(f"\n💬 Conversation Manager:")
        if client.conversation_manager.conversation_state:
            summary = client.conversation_manager.get_conversation_summary()
            print(f"   Conversation summary: {summary}")
        else:
            print("   No conversation state")


async def main():
    """Main example function."""
    print("🎯 AudioCodes Mock Client Examples")
    print("=" * 50)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Run examples
        await basic_conversation_example()
        await session_management_example()
        await component_inspection_example()
        await simple_test_example()
        await multi_turn_conversation_example()
        
        print("\n✅ All examples completed!")
        
    except Exception as e:
        print(f"\n❌ Example failed with error: {e}")
        logging.exception("Example error")


if __name__ == "__main__":
    asyncio.run(main()) 