#!/usr/bin/env python3
"""
Simple test script to verify audio playback is working.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_audio_playback():
    """Test basic audio playback functionality."""
    print("🎵 Testing Audio Playback...")
    
    try:
        # Import audio components
        from tui.utils.audio_utils import AudioUtils
        from tui.models.audio_manager import AudioManager, AudioConfig, AudioFormat
        
        print("✅ Audio components imported successfully")
        
        # Check if we have audio files
        audio_dir = Path("demo/audio")
        if not audio_dir.exists():
            print(f"❌ Audio directory not found: {audio_dir}")
            return
        
        audio_files = list(audio_dir.glob("*.wav"))
        if not audio_files:
            print(f"❌ No WAV files found in {audio_dir}")
            return
        
        print(f"✅ Found {len(audio_files)} audio files")
        
        # Create audio manager
        config = AudioConfig(
            sample_rate=16000,
            channels=1,
            chunk_size=1024,
            format=AudioFormat.PCM16,
            latency=0.1
        )
        
        audio_manager = AudioManager(config)
        print("✅ AudioManager created")
        
        # Start playback
        success = audio_manager.start_playback()
        if not success:
            print("❌ Failed to start audio playback")
            return
        
        print("✅ Audio playback started")
        
        # Load and play a test audio file
        test_file = audio_files[0]  # Use first available file
        print(f"🎵 Testing with file: {test_file.name}")
        
        # Load audio file
        audio_data, sample_rate, channels = AudioUtils.load_audio_file(str(test_file), target_sample_rate=16000)
        if not audio_data:
            print("❌ Failed to load audio data")
            return
        
        print(f"✅ Loaded audio: {len(audio_data)} bytes, {sample_rate}Hz, {channels} channels")
        
        # Chunk the audio
        chunks = AudioUtils.chunk_audio_by_duration(audio_data, sample_rate, 200, channels)
        print(f"✅ Created {len(chunks)} audio chunks")
        
        # Queue chunks for playback
        print("🎵 Queuing audio chunks for playback...")
        for i, chunk in enumerate(chunks):
            await audio_manager.play_audio_chunk(chunk)
            await asyncio.sleep(0.01)  # Small delay between chunks
        
        print("✅ Audio chunks queued")
        
        # Wait for playback to complete
        print("⏳ Waiting for audio playback to complete...")
        await asyncio.sleep(5)  # Wait 5 seconds for playback
        
        # Get statistics
        stats = audio_manager.get_statistics()
        print(f"📊 Audio statistics: {stats}")
        
        # Stop playback
        audio_manager.stop_playback()
        print("🛑 Audio playback stopped")
        
        # Cleanup
        audio_manager.cleanup()
        print("🧹 AudioManager cleaned up")
        
        print("✅ Audio playback test completed successfully!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you have sounddevice and other audio dependencies installed:")
        print("pip install sounddevice scipy librosa numpy")
    except Exception as e:
        print(f"❌ Error during audio test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_audio_playback()) 