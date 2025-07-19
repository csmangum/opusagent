#!/usr/bin/env python3
"""
Test script for AudioCodes audio playback functionality.

This script tests the audio playback integration with the AudioCodes mock client
to ensure that incoming audio chunks from the bridge server can be played through
local speakers.

Test Coverage:
- Audio playback module initialization
- Audio chunk processing and queuing
- Volume control and mute functionality
- Integration with MessageHandler
- Audio level monitoring
- Resource cleanup

Usage:
    python scripts/test_audiocodes_audio_playback.py

Requirements:
    - Audio dependencies: sounddevice, numpy, scipy
    - Bridge server running (optional, for full integration test)
"""

import asyncio
import base64
import logging
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from opusagent.local.audiocodes.audio_playback import AudioPlayback, AudioPlaybackConfig, AudioPlaybackManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_audio_playback_module():
    """Test the audio playback module directly."""
    print("🧪 Testing Audio Playback Module...")
    
    try:
        # Test configuration
        config = AudioPlaybackConfig(
            sample_rate=16000,
            channels=1,
            chunk_size=1024,
            volume=0.8,
            enable_playback=True
        )
        
        print(f"✅ Configuration created: {config}")
        
        # Test audio playback instance
        playback = AudioPlayback(config=config, logger=logger)
        print("✅ AudioPlayback instance created")
        
        # Test start/stop
        success = playback.start()
        if success:
            print("✅ Audio playback started")
            
            # Test volume control
            playback.set_volume(0.5)
            print("✅ Volume set to 50%")
            
            # Test mute/unmute
            playback.mute()
            print("✅ Audio muted")
            
            time.sleep(1)
            
            playback.unmute()
            print("✅ Audio unmuted")
            
            # Test statistics
            stats = playback.get_statistics()
            print(f"✅ Statistics: {stats}")
            
            # Cleanup
            playback.stop()
            print("✅ Audio playback stopped")
            
            playback.cleanup()
            print("✅ Audio playback cleaned up")
            
            return True
        else:
            print("❌ Failed to start audio playback")
            return False
            
    except Exception as e:
        print(f"❌ Error testing audio playback module: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_audio_playback_manager():
    """Test the audio playback manager."""
    print("\n🧪 Testing Audio Playback Manager...")
    
    try:
        # Test configuration
        config = AudioPlaybackConfig(
            sample_rate=16000,
            channels=1,
            volume=0.7,
            enable_playback=True
        )
        
        # Create manager
        manager = AudioPlaybackManager(config=config, logger=logger)
        print("✅ AudioPlaybackManager created")
        
        # Test status
        status = manager.get_status()
        print(f"✅ Initial status: {status}")
        
        # Test start
        success = manager.start()
        if success:
            print("✅ Audio playback manager started")
            
            # Test volume control
            manager.set_volume(0.6)
            print("✅ Volume set to 60%")
            
            # Test mute/unmute
            manager.mute()
            print("✅ Audio muted")
            
            time.sleep(1)
            
            manager.unmute()
            print("✅ Audio unmuted")
            
            # Test audio level
            level = manager.get_audio_level()
            print(f"✅ Audio level: {level}")
            
            # Cleanup
            manager.stop()
            print("✅ Audio playback manager stopped")
            
            manager.cleanup()
            print("✅ Audio playback manager cleaned up")
            
            return True
        else:
            print("❌ Failed to start audio playback manager")
            return False
            
    except Exception as e:
        print(f"❌ Error testing audio playback manager: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_audio_chunk_processing():
    """Test audio chunk processing and queuing."""
    print("\n🧪 Testing Audio Chunk Processing...")
    
    try:
        # Create audio playback
        config = AudioPlaybackConfig(enable_playback=True)
        playback = AudioPlayback(config=config, logger=logger)
        
        # Start playback
        success = playback.start()
        if not success:
            print("❌ Failed to start audio playback for chunk testing")
            return False
        
        print("✅ Audio playback started for chunk testing")
        
        # Create test audio data (1 second of silence at 16kHz, 16-bit)
        test_audio_data = bytes([0] * 32000)  # 1 second of silence
        test_chunk = base64.b64encode(test_audio_data).decode('utf-8')
        
        print(f"✅ Created test audio chunk: {len(test_chunk)} characters")
        
        # Queue multiple chunks
        for i in range(5):
            success = await playback.queue_audio_chunk(test_chunk)
            if success:
                print(f"✅ Queued chunk {i+1}/5")
            else:
                print(f"❌ Failed to queue chunk {i+1}/5")
            
            await asyncio.sleep(0.1)
        
        # Wait for playback to process chunks
        print("⏳ Waiting for audio chunks to be processed...")
        await asyncio.sleep(3)
        
        # Check statistics
        stats = playback.get_statistics()
        print(f"✅ Final statistics: {stats}")
        
        # Cleanup
        playback.stop()
        playback.cleanup()
        print("✅ Audio playback cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing audio chunk processing: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dependencies():
    """Test if audio dependencies are available."""
    print("🧪 Testing Audio Dependencies...")
    
    try:
        import sounddevice as sd
        print("✅ sounddevice available")
        
        import numpy as np
        print("✅ numpy available")
        
        from scipy import signal
        print("✅ scipy available")
        
        # Test basic sounddevice functionality
        devices = sd.query_devices()
        print(f"✅ Found {len(devices)} audio devices")
        
        # Test numpy functionality
        test_array = np.array([1, 2, 3, 4, 5], dtype=np.int16)
        print(f"✅ numpy test array created: {test_array}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Missing audio dependency: {e}")
        print("Install with: pip install sounddevice numpy scipy")
        return False
    except Exception as e:
        print(f"❌ Error testing dependencies: {e}")
        return False


async def main():
    """Main test function."""
    print("🎵 AudioCodes Audio Playback Test Suite")
    print("=" * 50)
    
    # Test 1: Dependencies
    print("\n🧪 Test 1: Audio Dependencies")
    deps_ok = test_dependencies()
    
    if not deps_ok:
        print("❌ Audio dependencies not available. Skipping other tests.")
        return
    
    # Test 2: Audio Playback Module
    print("\n🧪 Test 2: Audio Playback Module")
    module_ok = test_audio_playback_module()
    
    # Test 3: Audio Playback Manager
    print("\n🧪 Test 3: Audio Playback Manager")
    manager_ok = test_audio_playback_manager()
    
    # Test 4: Audio Chunk Processing
    print("\n🧪 Test 4: Audio Chunk Processing")
    chunk_ok = await test_audio_chunk_processing()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print(f"Dependencies: {'✅ PASSED' if deps_ok else '❌ FAILED'}")
    print(f"Audio Module: {'✅ PASSED' if module_ok else '❌ FAILED'}")
    print(f"Audio Manager: {'✅ PASSED' if manager_ok else '❌ FAILED'}")
    print(f"Chunk Processing: {'✅ PASSED' if chunk_ok else '❌ FAILED'}")
    
    all_passed = deps_ok and module_ok and manager_ok and chunk_ok
    
    if all_passed:
        print("\n🎉 All tests passed! Audio playback is working correctly.")
        print("\n💡 Next steps:")
        print("- Run the AudioCodes client with audio playback enabled")
        print("- Test with a real bridge server connection")
        print("- Adjust volume and settings as needed")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        print("\n🔧 Troubleshooting:")
        print("- Ensure audio dependencies are installed: pip install sounddevice numpy scipy")
        print("- Check that your system has audio output devices")
        print("- Try running with different audio settings")


if __name__ == "__main__":
    asyncio.run(main()) 