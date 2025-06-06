#!/usr/bin/env python3
"""
Test script for audio functionality in the TUI Validator.

This script tests audio file loading, chunking, format conversion,
and other audio utilities.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from tui.utils.audio_utils import AudioUtils
from tui.models.audio_manager import AudioManager, AudioConfig, AudioFormat

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_audio_loading():
    """Test audio file loading."""
    print("🔊 Testing Audio File Loading...")
    
    # Test files to try
    test_files = [
        "static/tell_me_about_your_bank.wav",
        "static/sample.wav",
        "tell_me_about_your_bank.wav"
    ]
    
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"📁 Testing file: {test_file}")
            
            # Test basic WAV loading
            audio_data, sample_rate, channels = AudioUtils.load_wav_file(test_file)
            print(f"  WAV: {len(audio_data)} bytes, {sample_rate}Hz, {channels}ch")
            
            # Test universal loading
            audio_data2, sample_rate2, channels2 = AudioUtils.load_audio_file(test_file)
            print(f"  Universal: {len(audio_data2)} bytes, {sample_rate2}Hz, {channels2}ch")
            
            # Test chunking
            chunks = AudioUtils.chunk_audio_by_duration(audio_data, sample_rate, 1000, channels)
            print(f"  Chunks: {len(chunks)} x 1-second chunks")
            
            # Test visualization
            if audio_data:
                viz = AudioUtils.visualize_audio_level(audio_data[:1000])
                print(f"  Visualization: {viz}")
            
            return test_file, audio_data, sample_rate, channels
    
    print("❌ No test audio files found")
    return None, None, None, None

async def test_audio_manager():
    """Test AudioManager functionality."""
    print("\n🎧 Testing AudioManager...")
    
    try:
        # Create audio manager
        config = AudioConfig(
            sample_rate=16000,
            channels=1,
            chunk_size=1024,
            format=AudioFormat.PCM16,
            latency=0.1
        )
        
        audio_manager = AudioManager(config)
        print("✅ AudioManager created successfully")
        
        # Test device enumeration
        devices = AudioManager.get_available_devices()
        print(f"📱 Available devices:")
        print(f"  Input: {len(devices['input'])} devices")
        print(f"  Output: {len(devices['output'])} devices")
        
        # Test starting/stopping (but don't actually play audio)
        print("🎯 Testing start/stop operations...")
        
        # Start playback
        success = audio_manager.start_playback()
        print(f"  Playback start: {'✅' if success else '❌'}")
        
        # Start recording  
        success = audio_manager.start_recording()
        print(f"  Recording start: {'✅' if success else '❌'}")
        
        # Wait a moment
        await asyncio.sleep(0.5)
        
        # Get statistics
        stats = audio_manager.get_statistics()
        print(f"  Statistics: {stats}")
        
        # Stop everything
        audio_manager.stop_recording()
        audio_manager.stop_playback()
        print("🛑 Stopped audio operations")
        
        # Cleanup
        audio_manager.cleanup()
        print("🧹 Cleaned up AudioManager")
        
    except Exception as e:
        print(f"❌ AudioManager test failed: {e}")

async def test_format_conversion():
    """Test audio format conversion."""
    print("\n🔄 Testing Format Conversion...")
    
    # Create test PCM16 data (sine wave)
    import struct
    import math
    
    sample_rate = 16000
    duration = 1.0  # 1 second
    frequency = 440  # A4 note
    
    samples = []
    for i in range(int(sample_rate * duration)):
        t = i / sample_rate
        sample = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * t))
        samples.append(sample)
    
    pcm_data = struct.pack(f'<{len(samples)}h', *samples)
    print(f"📊 Generated {len(pcm_data)} bytes of PCM16 test data")
    
    # Test base64 conversion
    b64_data = AudioUtils.convert_to_base64(pcm_data)
    decoded_data = AudioUtils.convert_from_base64(b64_data)
    print(f"🔤 Base64: {len(b64_data)} chars -> {len(decoded_data)} bytes")
    print(f"  Roundtrip: {'✅' if pcm_data == decoded_data else '❌'}")
    
    # Test G.711 conversion (simplified)
    ulaw_data = AudioUtils.convert_from_pcm16(pcm_data, "ulaw")
    pcm_restored = AudioUtils.convert_to_pcm16(ulaw_data, "ulaw")
    print(f"📞 μ-law: {len(pcm_data)} -> {len(ulaw_data)} -> {len(pcm_restored)}")
    
    # Test visualization
    viz = AudioUtils.visualize_audio_level(pcm_data)
    print(f"📈 Visualization: {viz}")

async def test_chunking():
    """Test audio chunking functionality."""
    print("\n✂️ Testing Audio Chunking...")
    
    # Create test data
    test_data = b'\x00\x01' * 8000  # 16000 bytes = 1 second at 16kHz 16-bit mono
    
    # Test simple chunking
    chunks = AudioUtils.chunk_audio_data(test_data, 1600)  # 100ms chunks
    print(f"📦 Simple chunking: {len(test_data)} bytes -> {len(chunks)} chunks")
    
    # Test duration-based chunking
    chunks_duration = AudioUtils.chunk_audio_by_duration(test_data, 16000, 100)  # 100ms
    print(f"⏱️ Duration chunking: {len(test_data)} bytes -> {len(chunks_duration)} chunks of 100ms")
    
    # Test overlapping chunks
    chunks_overlap = AudioUtils.chunk_audio_data(test_data, 1600, overlap=160)  # 10% overlap
    print(f"🔄 Overlapping chunking: {len(chunks_overlap)} chunks with 10% overlap")

async def main():
    """Run all audio tests."""
    print("🎵 TUI Validator Audio Testing Suite")
    print("=" * 50)
    
    try:
        # Test audio loading
        test_file, audio_data, sample_rate, channels = await test_audio_loading()
        
        # await test_audio_manager()   # <-- Comment this out for now
        
        # Test format conversion
        await test_format_conversion()
        
        # Test chunking
        await test_chunking()
        
        print("\n🎉 All audio tests completed!")
        
        if test_file:
            print(f"\n📋 Test Summary:")
            print(f"  Loaded file: {test_file}")
            print(f"  Audio data: {len(audio_data) if audio_data else 0} bytes")
            print(f"  Sample rate: {sample_rate}Hz")
            print(f"  Channels: {channels}")
            
            if audio_data:
                duration = AudioUtils.get_audio_duration(audio_data, sample_rate, channels)
                print(f"  Duration: {duration:.2f} seconds")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 