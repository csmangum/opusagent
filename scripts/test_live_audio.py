#!/usr/bin/env python3
"""
Test script for live audio capture functionality.

This script tests the live audio capture features without requiring
a bridge server connection, making it useful for development and debugging.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from opusagent.mock.audiocodes.live_audio_manager import LiveAudioManager


class LiveAudioTester:
    """Test class for live audio functionality."""

    def __init__(self):
        """Initialize the tester."""
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.audio_chunks_received = 0
        self.vad_events_received = 0
        self.last_vad_event = None

    def audio_callback(self, audio_chunk: str):
        """Callback for received audio chunks."""
        self.audio_chunks_received += 1
        if self.audio_chunks_received % 10 == 0:  # Log every 10th chunk
            self.logger.info(f"[TEST] Received audio chunk #{self.audio_chunks_received}")

    def vad_callback(self, event: dict):
        """Callback for VAD events."""
        self.vad_events_received += 1
        self.last_vad_event = event
        self.logger.info(f"[TEST] VAD event: {event['type']} (prob: {event['data'].get('speech_prob', 0):.3f})")

    async def test_device_enumeration(self):
        """Test audio device enumeration."""
        print("\n🔍 Testing Audio Device Enumeration")
        print("=" * 40)
        
        try:
            manager = LiveAudioManager(logger=self.logger)
            devices = manager.get_available_devices()
            
            print(f"Found {len(devices)} audio input devices:")
            for i, device in enumerate(devices):
                default_marker = " (DEFAULT)" if device.get("is_default", False) else ""
                print(f"  {i}: {device['name']}{default_marker}")
                print(f"     Channels: {device['channels']}, Sample Rate: {device['sample_rate']}Hz")
            
            if not devices:
                print("❌ No audio input devices found!")
                return False
            
            print("✅ Device enumeration successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Device enumeration failed: {e}")
            return False

    async def test_audio_capture(self, duration: int = 10):
        """Test basic audio capture."""
        print(f"\n🎤 Testing Audio Capture ({duration}s)")
        print("=" * 40)
        
        try:
            # Create live audio manager
            manager = LiveAudioManager(
                audio_callback=self.audio_callback,
                vad_callback=self.vad_callback,
                logger=self.logger,
                config={
                    "vad_enabled": True,
                    "vad_threshold": 0.3,
                    "vad_silence_threshold": 0.1,
                    "chunk_delay": 0.02,
                    "buffer_size": 8000,  # 0.5 second buffer
                }
            )
            
            # Reset counters
            self.audio_chunks_received = 0
            self.vad_events_received = 0
            self.last_vad_event = None
            
            # Start capture
            print("Starting audio capture...")
            success = manager.start_capture()
            if not success:
                print("❌ Failed to start audio capture")
                return False
            
            print("✅ Audio capture started")
            print(f"Speak into your microphone for {duration} seconds...")
            
            # Monitor for specified duration
            start_time = time.time()
            while time.time() - start_time < duration:
                # Display audio level
                audio_level = manager.get_audio_level()
                level_bars = int(audio_level * 20)
                level_display = "█" * level_bars + "░" * (20 - level_bars)
                
                status = manager.get_status()
                speech_status = "SPEAKING" if status.get("speech_active", False) else "SILENT"
                
                elapsed = time.time() - start_time
                remaining = duration - elapsed
                
                print(f"\r⏱️  {elapsed:5.1f}s | 🔊 {level_display} | 🎤 {speech_status} | ⏳ {remaining:4.1f}s left", end="", flush=True)
                
                await asyncio.sleep(0.1)
            
            print()  # New line after progress display
            
            # Stop capture
            manager.stop_capture()
            print("✅ Audio capture stopped")
            
            # Display results
            print(f"\n📊 Test Results:")
            print(f"   Audio chunks received: {self.audio_chunks_received}")
            print(f"   VAD events received: {self.vad_events_received}")
            print(f"   Average chunks per second: {self.audio_chunks_received / duration:.1f}")
            
            if self.last_vad_event:
                print(f"   Last VAD event: {self.last_vad_event['type']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Audio capture test failed: {e}")
            return False

    async def test_vad_functionality(self, duration: int = 15):
        """Test VAD functionality specifically."""
        print(f"\n🎯 Testing VAD Functionality ({duration}s)")
        print("=" * 40)
        
        try:
            # Create manager with VAD enabled
            manager = LiveAudioManager(
                audio_callback=self.audio_callback,
                vad_callback=self.vad_callback,
                logger=self.logger,
                config={
                    "vad_enabled": True,
                    "vad_threshold": 0.2,  # Lower threshold for easier detection
                    "vad_silence_threshold": 0.1,
                    "min_speech_duration_ms": 300,
                    "min_silence_duration_ms": 200,
                    "chunk_delay": 0.02,
                    "buffer_size": 8000,
                }
            )
            
            # Reset counters
            self.audio_chunks_received = 0
            self.vad_events_received = 0
            self.last_vad_event = None
            
            # Start capture
            print("Starting VAD test...")
            success = manager.start_capture()
            if not success:
                print("❌ Failed to start VAD test")
                return False
            
            print("✅ VAD test started")
            print("Instructions:")
            print("1. Stay silent for 3 seconds")
            print("2. Speak for 5 seconds")
            print("3. Stay silent for 3 seconds")
            print("4. Speak again for 4 seconds")
            
            # Monitor for specified duration
            start_time = time.time()
            while time.time() - start_time < duration:
                # Display audio level and VAD status
                audio_level = manager.get_audio_level()
                level_bars = int(audio_level * 20)
                level_display = "█" * level_bars + "░" * (20 - level_bars)
                
                status = manager.get_status()
                speech_status = "SPEAKING" if status.get("speech_active", False) else "SILENT"
                
                elapsed = time.time() - start_time
                remaining = duration - elapsed
                
                print(f"\r⏱️  {elapsed:5.1f}s | 🔊 {level_display} | 🎤 {speech_status} | 📊 VAD: {self.vad_events_received} events | ⏳ {remaining:4.1f}s", end="", flush=True)
                
                await asyncio.sleep(0.1)
            
            print()  # New line after progress display
            
            # Stop capture
            manager.stop_capture()
            print("✅ VAD test completed")
            
            # Display VAD results
            print(f"\n📊 VAD Test Results:")
            print(f"   Total VAD events: {self.vad_events_received}")
            print(f"   Audio chunks: {self.audio_chunks_received}")
            
            # Analyze VAD events
            if self.vad_events_received > 0:
                print("   ✅ VAD is working - events detected")
            else:
                print("   ⚠️  No VAD events detected - check microphone and thresholds")
            
            return True
            
        except Exception as e:
            self.logger.error(f"VAD test failed: {e}")
            return False

    async def test_device_selection(self):
        """Test device selection functionality."""
        print("\n🔧 Testing Device Selection")
        print("=" * 40)
        
        try:
            manager = LiveAudioManager(logger=self.logger)
            devices = manager.get_available_devices()
            
            if len(devices) < 2:
                print("⚠️  Need at least 2 devices to test device selection")
                return True
            
            # Test setting different devices
            for i, device in enumerate(devices[:2]):  # Test first 2 devices
                print(f"Testing device {i}: {device['name']}")
                
                success = manager.set_device(i)
                if success:
                    print(f"✅ Successfully set device {i}")
                else:
                    print(f"❌ Failed to set device {i}")
                
                # Get status to verify
                status = manager.get_status()
                current_device = status.get("config", {}).get("device_index")
                print(f"   Current device index: {current_device}")
                
                await asyncio.sleep(0.5)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Device selection test failed: {e}")
            return False

    async def run_all_tests(self):
        """Run all live audio tests."""
        print("🧪 Live Audio Capture Test Suite")
        print("=" * 50)
        
        test_results = []
        
        # Test 1: Device enumeration
        print("\n1️⃣  Testing device enumeration...")
        result = await self.test_device_enumeration()
        test_results.append(("Device Enumeration", result))
        
        if not result:
            print("❌ Device enumeration failed - cannot continue")
            return
        
        # Test 2: Basic audio capture
        print("\n2️⃣  Testing basic audio capture...")
        result = await self.test_audio_capture(duration=8)
        test_results.append(("Basic Audio Capture", result))
        
        # Test 3: VAD functionality
        print("\n3️⃣  Testing VAD functionality...")
        result = await self.test_vad_functionality(duration=12)
        test_results.append(("VAD Functionality", result))
        
        # Test 4: Device selection
        print("\n4️⃣  Testing device selection...")
        result = await self.test_device_selection()
        test_results.append(("Device Selection", result))
        
        # Display summary
        print("\n" + "=" * 50)
        print("📋 TEST SUMMARY")
        print("=" * 50)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Live audio capture is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")


async def main():
    """Main function to run the live audio tests."""
    print("🎤 Live Audio Capture Test Suite")
    print("=" * 50)
    
    tester = LiveAudioTester()
    
    try:
        await tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 