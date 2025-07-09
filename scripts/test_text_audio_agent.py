#!/usr/bin/env python3
"""
Test script for the TextAudioAgent.

This script demonstrates how to use the TextAudioAgent to:
1. Connect to the real OpenAI Realtime API with text modality only
2. Send text messages to the AI
3. Have the AI respond by calling the play_audio function to play local audio files
4. Handle audio playback locally

Usage:
    python test_text_audio_agent.py

Requirements:
    - OPENAI_API_KEY environment variable set
    - Audio files in demo/audio/ directory
    - sounddevice and other audio dependencies installed

Example Flow:
    User: "Hello, can you greet me?"
    AI: *calls play_audio("greeting.wav")*
    System: *plays greeting.wav file*
    AI: "Hello! I just played a greeting for you."
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from opusagent.text_audio_agent import TextAudioAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_requirements():
    """Check that all requirements are met."""
    issues = []
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        issues.append("❌ OPENAI_API_KEY environment variable not set")
    else:
        logger.info("✅ OpenAI API key found")
    
    # Check audio directory
    audio_dir = Path("opusagent/mock/audio")
    if not audio_dir.exists():
        issues.append(f"❌ Audio directory not found: {audio_dir}")
    else:
        audio_files = list(audio_dir.glob("**/*.wav"))
        if not audio_files:
            issues.append(f"❌ No WAV files found in {audio_dir}")
        else:
            logger.info(f"✅ Found {len(audio_files)} audio files in {audio_dir}")
    
    # Check audio dependencies
    try:
        import sounddevice
        logger.info("✅ sounddevice available for audio playback")
    except ImportError:
        issues.append("❌ sounddevice not available - install with: pip install sounddevice")
    
    try:
        from tui.utils.audio_utils import AudioUtils
        logger.info("✅ Audio utilities available")
    except ImportError:
        issues.append("❌ Audio utilities not available")
    
    return issues


async def test_audio_devices():
    """Test available audio devices."""
    print("\n🔊 Testing Audio Devices...")
    
    try:
        from tui.models.audio_manager import AudioManager
        import sounddevice as sd
        
        # Get available devices
        devices = AudioManager.get_available_devices()
        
        print(f"📱 Available audio devices:")
        print(f"   Input devices: {len(devices['input'])}")
        print(f"   Output devices: {len(devices['output'])}")
        
        if devices['output']:
            print("\n🎧 Output devices:")
            for i, device in enumerate(devices['output']):
                print(f"   {i}: {device['name']} ({device['channels']} channels)")
        else:
            print("❌ No output devices found!")
            return False
        
        # Test default device
        try:
            default_device = sd.default.device[1]  # Output device
            print(f"\n🎯 Default output device: {default_device}")
            
            # Get device info
            device_info = sd.query_devices(default_device)
            if isinstance(device_info, dict):
                print(f"   Name: {device_info.get('name', 'Unknown')}")
                print(f"   Max channels: {device_info.get('max_output_channels', 0)}")
                print(f"   Default sample rate: {device_info.get('default_samplerate', 0)}")
            else:
                print(f"   Device info: {device_info}")
            
        except Exception as e:
            print(f"❌ Error getting default device: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Audio device test failed: {e}")
        return False


async def test_audio_file_content():
    """Test if audio files actually contain audio data."""
    print("\n🔍 Testing Audio File Content...")
    
    try:
        from tui.utils.audio_utils import AudioUtils
        import numpy as np
        
        # Test a few audio files from the correct directory
        test_files = ["greetings/greetings_01.wav", "farewells/farewells_01.wav", "default/default_01.wav"]
        audio_dir = Path("opusagent/mock/audio")
        
        for filename in test_files:
            file_path = audio_dir / filename
            if not file_path.exists():
                print(f"❌ File not found: {filename}")
                continue
            
            # Load audio file
            audio_data, sample_rate, channels = AudioUtils.load_audio_file(str(file_path), target_sample_rate=16000)
            
            if not audio_data:
                print(f"❌ Failed to load: {filename}")
                continue
            
            # Convert to numpy array to analyze
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Check if audio contains non-zero data
            max_val = np.max(np.abs(audio_array))
            mean_val = np.mean(np.abs(audio_array))
            non_zero_count = np.count_nonzero(audio_array)
            total_samples = len(audio_array)
            
            print(f"📁 {filename}:")
            print(f"   Size: {len(audio_data)} bytes")
            print(f"   Samples: {total_samples}")
            print(f"   Max amplitude: {max_val}")
            print(f"   Mean amplitude: {mean_val:.1f}")
            print(f"   Non-zero samples: {non_zero_count}/{total_samples} ({non_zero_count/total_samples*100:.1f}%)")
            
            if max_val == 0:
                print(f"   ⚠️  WARNING: {filename} contains only silence!")
            elif max_val < 100:
                print(f"   ⚠️  WARNING: {filename} has very low amplitude (max={max_val})")
            else:
                print(f"   ✅ {filename} appears to have audio content")
            
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Audio file content test failed: {e}")
        return False


async def test_audio_playback():
    """Test basic audio playback functionality."""
    print("\n🔊 Testing Audio Playback...")
    
    # First test audio devices
    await test_audio_devices()
    
    # Then test audio file content
    await test_audio_file_content()
    
    try:
        # Check if audio dependencies are available
        try:
            from tui.utils.audio_utils import AudioUtils
            from tui.models.audio_manager import AudioManager, AudioConfig, AudioFormat
            import sounddevice as sd
            print("✅ Audio dependencies available")
        except ImportError as e:
            print(f"❌ Audio dependencies not available: {e}")
            return False
        
        # Test audio file loading
        audio_dir = Path("opusagent/mock/audio")
        if not audio_dir.exists():
            print(f"❌ Audio directory not found: {audio_dir}")
            return False
        
        # Find a test audio file
        test_files = list(audio_dir.glob("greetings/*.wav"))
        if not test_files:
            print(f"❌ No WAV files found in {audio_dir}/greetings")
            return False
        
        test_file = test_files[0]
        print(f"📁 Testing with audio file: {test_file}")
        
        # Load audio file
        audio_data, sample_rate, channels = AudioUtils.load_audio_file(str(test_file), target_sample_rate=16000)
        if not audio_data:
            print("❌ Failed to load audio file")
            return False
        
        print(f"✅ Loaded audio: {sample_rate}Hz, {channels}ch, {len(audio_data)} bytes")
        
        # Test audio manager
        config = AudioConfig(
            sample_rate=16000,
            channels=1,
            chunk_size=1024,
            format=AudioFormat.PCM16,
            latency=0.1
        )
        
        audio_manager = AudioManager(config)
        success = audio_manager.start_playback()
        if not success:
            print("❌ Failed to start audio playback")
            return False
        
        print("✅ Audio manager started successfully")
        
        # Test playing a short audio clip
        chunks = AudioUtils.chunk_audio_by_duration(audio_data, sample_rate, 100, channels, 2)  # 100ms chunks
        print(f"📦 Created {len(chunks)} audio chunks")
        
        # Play first few chunks as a test
        for i, chunk in enumerate(chunks[:5]):  # Play first 5 chunks
            await audio_manager.play_audio_chunk(chunk)
            await asyncio.sleep(0.1)
        
        # Wait for playback to complete
        await asyncio.sleep(1.0)
        
        # Check statistics
        stats = audio_manager.get_statistics()
        print(f"📊 Audio stats: {stats}")
        
        audio_manager.stop_playback()
        
        if stats['chunks_played'] > 0:
            print("✅ Audio playback test successful!")
            return True
        else:
            print("❌ Audio playback test failed - no chunks were played")
            return False
        
    except Exception as e:
        print(f"❌ Audio playback test failed: {e}")
        return False


async def interactive_test():
    """Run an interactive test session with the TextAudioAgent."""
    print("\n🎤 TextAudioAgent Interactive Test")
    print("=" * 50)
    
    # Test audio playback first
    if not await test_audio_playback():
        print("⚠️ Audio playback test failed. Audio may not work properly.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Initialize the agent
    agent = TextAudioAgent(
        audio_directory="opusagent/mock/audio/",
        system_prompt="""
You are a helpful voice assistant that can play audio files to communicate.

You have access to a play_audio function that allows you to play audio files.
When appropriate, use this function to play relevant audio files.

Available files are organized in categories with numbered files:
- greetings/greetings_01.wav through greetings_10.wav - for welcoming users
- farewells/farewells_01.wav through farewells_10.wav - for farewells
- default/default_01.wav through default_10.wav - for general responses
- errors/errors_01.wav through errors_10.wav - for error situations

IMPORTANT: Use the exact filename including the category folder and number, for example:
- play_audio("greetings/greetings_01.wav") for a greeting
- play_audio("farewells/farewells_03.wav") for a farewell
- play_audio("default/default_05.wav") for a general response

Be conversational and use audio files to enhance your responses.
        """,
        temperature=0.7
    )
    
    print(f"🔊 Agent Status: {agent.get_status()}")
    
    # Connect to OpenAI
    print("\n⏳ Connecting to OpenAI Realtime API...")
    if not await agent.connect():
        print("❌ Failed to connect to OpenAI API")
        return
    
    print("✅ Connected to OpenAI API")
    print("\n💬 You can now chat with the agent!")
    print("📝 Type your messages below (or 'quit' to exit):")
    print("-" * 50)
    
    try:
        while True:
            # Get user input
            user_input = input("\n👤 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\n👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            # Send message to AI
            print("⏳ Sending message to AI...")
            success = await agent.send_text_message(user_input)
            
            if not success:
                print("❌ Failed to send message")
                continue
            
            print("✅ Message sent! Waiting for response...")
            
            # Give some time for the response to be processed
            await asyncio.sleep(3)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    
    finally:
        print("\n🔌 Disconnecting...")
        await agent.disconnect()
        print("✅ Disconnected")


async def automated_test():
    """Run automated tests with predefined messages."""
    print("\n🤖 TextAudioAgent Automated Test")
    print("=" * 50)
    
    # Test messages
    test_messages = [
        "Hello, can you greet me?",
        "Thank you for your help!",
        "I'm having trouble with something",
        "Goodbye!"
    ]
    
    # Initialize the agent
    agent = TextAudioAgent(
        audio_directory="opusagent/mock/audio/",
        temperature=0.8
    )
    
    print(f"🔊 Agent Status: {agent.get_status()}")
    
    # Connect to OpenAI
    print("\n⏳ Connecting to OpenAI Realtime API...")
    if not await agent.connect():
        print("❌ Failed to connect to OpenAI API")
        return
    
    print("✅ Connected to OpenAI API")
    
    try:
        for i, message in enumerate(test_messages, 1):
            print(f"\n📩 Test {i}/{len(test_messages)}: {message}")
            
            success = await agent.send_text_message(message)
            if success:
                print("✅ Message sent successfully")
                await asyncio.sleep(4)  # Wait for response
            else:
                print("❌ Failed to send message")
            
            print("-" * 30)
    
    except Exception as e:
        print(f"❌ Error during automated test: {e}")
    
    finally:
        print("\n🔌 Disconnecting...")
        await agent.disconnect()
        print("✅ Automated test completed")


def print_help():
    """Print usage help."""
    print("""
🎤 TextAudioAgent Test Script

This script tests the TextAudioAgent that connects to the real OpenAI Realtime API
using text modality only, but can trigger local audio file playback.

Usage:
    python test_text_audio_agent.py [options]

Options:
    --interactive, -i    Run interactive test session (default)
    --automated, -a      Run automated test with predefined messages
    --check, -c          Check requirements only
    --help, -h           Show this help message

Environment:
    OPENAI_API_KEY       Your OpenAI API key (required)

Audio Files:
    Place audio files (.wav, .mp3) in demo/audio/ directory
    
Example:
    export OPENAI_API_KEY="your-api-key-here"
    python test_text_audio_agent.py --interactive
    """)


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the TextAudioAgent")
    parser.add_argument("--interactive", "-i", action="store_true", default=True,
                       help="Run interactive test session")
    parser.add_argument("--automated", "-a", action="store_true",
                       help="Run automated test")
    parser.add_argument("--check", "-c", action="store_true",
                       help="Check requirements only")
    
    args = parser.parse_args()
    
    if args.check:
        print("🔍 Checking Requirements...")
        issues = check_requirements()
        if issues:
            print("\n❌ Issues found:")
            for issue in issues:
                print(f"  {issue}")
            sys.exit(1)
        else:
            print("\n✅ All requirements met!")
            return
    
    # Check requirements first
    issues = check_requirements()
    if issues:
        print("❌ Requirements not met:")
        for issue in issues:
            print(f"  {issue}")
        print("\nPlease fix these issues before running the test.")
        sys.exit(1)
    
    if args.automated:
        await automated_test()
    else:
        await interactive_test()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1) 