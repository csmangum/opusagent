#!/usr/bin/env python3
"""
Live Audio Capture Example for MockAudioCodesClient.

This script demonstrates how to use the live microphone input functionality
for realistic testing of the AudioCodes bridge server.
"""

import asyncio
import logging
import signal
import sys
import time
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from opusagent.mock.audiocodes import MockAudioCodesClient


class LiveAudioExample:
    """Example class demonstrating live audio capture functionality."""

    def __init__(self, bridge_url: str = "ws://localhost:8080"):
        """
        Initialize the live audio example.

        Args:
            bridge_url (str): WebSocket URL for the bridge server
        """
        self.bridge_url = bridge_url
        self.client = None
        self.running = False
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    async def run_basic_example(self):
        """Run a basic live audio capture example."""
        print("\n🎤 Live Audio Capture Example")
        print("=" * 50)
        
        try:
            async with MockAudioCodesClient(self.bridge_url) as client:
                self.client = client
                
                # Get available audio devices
                print("\n📱 Available Audio Devices:")
                devices = client.get_available_audio_devices()
                for i, device in enumerate(devices):
                    default_marker = " (DEFAULT)" if device.get("is_default", False) else ""
                    print(f"  {i}: {device['name']}{default_marker}")
                    print(f"     Channels: {device['channels']}, Sample Rate: {device['sample_rate']}Hz")
                
                if not devices:
                    print("  ❌ No audio input devices found!")
                    return
                
                # Initiate session
                print(f"\n🔗 Connecting to bridge at {self.bridge_url}...")
                success = await client.initiate_session()
                if not success:
                    print("❌ Failed to initiate session")
                    return
                
                print("✅ Session initiated successfully")
                
                # Start live audio capture
                print("\n🎤 Starting live audio capture...")
                live_config = {
                    "vad_enabled": True,
                    "vad_threshold": 0.3,  # Lower threshold for easier detection
                    "vad_silence_threshold": 0.1,
                    "chunk_delay": 0.02,
                    "buffer_size": 16000,  # 1 second buffer
                }
                
                success = client.start_live_audio_capture(config=live_config)
                if not success:
                    print("❌ Failed to start live audio capture")
                    return
                
                print("✅ Live audio capture started")
                print("   Speak into your microphone to test...")
                print("   Press Ctrl+C to stop")
                
                # Start user stream
                print("\n📡 Starting user stream...")
                user_stream_start = {
                    "type": "userStream.start",
                    "conversationId": client.session_manager.get_conversation_id(),
                }
                await client._ws.send(user_stream_start)
                
                # Monitor audio levels and VAD events
                self.running = True
                await self._monitor_audio()
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping live audio capture...")
        except Exception as e:
            self.logger.error(f"Example error: {e}")
        finally:
            if self.client:
                self.client.stop_live_audio_capture()
                await self.client.end_session("Live audio test completed")

    async def run_interactive_example(self):
        """Run an interactive live audio example with user input."""
        print("\n🎤 Interactive Live Audio Example")
        print("=" * 50)
        
        try:
            async with MockAudioCodesClient(self.bridge_url) as client:
                self.client = client
                
                # Get available devices
                devices = client.get_available_audio_devices()
                if not devices:
                    print("❌ No audio input devices found!")
                    return
                
                # Let user select device
                print("\n📱 Select Audio Device:")
                for i, device in enumerate(devices):
                    default_marker = " (DEFAULT)" if device.get("is_default", False) else ""
                    print(f"  {i}: {device['name']}{default_marker}")
                
                try:
                    device_choice = input(f"\nEnter device number (0-{len(devices)-1}): ").strip()
                    device_index = int(device_choice)
                    if device_index < 0 or device_index >= len(devices):
                        print("Invalid device selection, using default")
                        device_index = None
                except (ValueError, KeyboardInterrupt):
                    print("Using default device")
                    device_index = None
                
                # Configure VAD
                print("\n🎯 VAD Configuration:")
                try:
                    vad_threshold = float(input("VAD threshold (0.1-1.0, default 0.5): ").strip() or "0.5")
                    silence_threshold = float(input("Silence threshold (0.1-1.0, default 0.3): ").strip() or "0.3")
                except (ValueError, KeyboardInterrupt):
                    vad_threshold = 0.5
                    silence_threshold = 0.3
                
                # Initiate session
                print(f"\n🔗 Connecting to bridge...")
                success = await client.initiate_session()
                if not success:
                    print("❌ Failed to initiate session")
                    return
                
                # Start live audio with custom config
                live_config = {
                    "vad_enabled": True,
                    "vad_threshold": vad_threshold,
                    "vad_silence_threshold": silence_threshold,
                    "min_speech_duration_ms": 500,
                    "min_silence_duration_ms": 300,
                    "chunk_delay": 0.02,
                    "buffer_size": 16000,
                }
                
                success = client.start_live_audio_capture(config=live_config, device_index=device_index)
                if not success:
                    print("❌ Failed to start live audio capture")
                    return
                
                print("✅ Live audio capture started")
                print("\n🎤 Speak into your microphone to test the system!")
                print("   Commands:")
                print("   - Press 's' to show status")
                print("   - Press 'd' to show devices")
                print("   - Press 'q' to quit")
                print("   - Press Ctrl+C to stop immediately")
                
                # Start user stream
                user_stream_start = {
                    "type": "userStream.start",
                    "conversationId": client.session_manager.get_conversation_id(),
                }
                await client._ws.send(user_stream_start)
                
                # Interactive loop
                await self._interactive_loop()
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping...")
        except Exception as e:
            self.logger.error(f"Interactive example error: {e}")
        finally:
            if self.client:
                self.client.stop_live_audio_capture()
                await self.client.end_session("Interactive test completed")

    async def _monitor_audio(self):
        """Monitor audio levels and VAD events."""
        start_time = time.time()
        
        while self.running:
            try:
                # Get audio level
                audio_level = self.client.get_audio_level()
                
                # Create simple audio level visualization
                level_bars = int(audio_level * 20)
                level_display = "█" * level_bars + "░" * (20 - level_bars)
                
                # Get live audio status
                status = self.client.get_live_audio_status()
                speech_status = "SPEAKING" if status.get("speech_active", False) else "SILENT"
                
                # Display status
                elapsed = time.time() - start_time
                print(f"\r⏱️  {elapsed:6.1f}s | 🔊 {level_display} | 🎤 {speech_status}", end="", flush=True)
                
                await asyncio.sleep(0.1)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Monitor error: {e}")
                break

    async def _interactive_loop(self):
        """Interactive command loop."""
        import threading
        import queue
        
        # Create a queue for user input
        input_queue = queue.Queue()
        
        def input_worker():
            """Worker thread for handling user input."""
            try:
                while self.running:
                    try:
                        user_input = input().strip().lower()
                        input_queue.put(user_input)
                    except (EOFError, KeyboardInterrupt):
                        input_queue.put("quit")
                        break
            except Exception:
                pass
        
        # Start input worker thread
        input_thread = threading.Thread(target=input_worker, daemon=True)
        input_thread.start()
        
        start_time = time.time()
        
        while self.running:
            try:
                # Check for user input
                try:
                    user_input = input_queue.get_nowait()
                    if user_input == "q" or user_input == "quit":
                        break
                    elif user_input == "s":
                        await self._show_status()
                    elif user_input == "d":
                        await self._show_devices()
                    else:
                        print(f"Unknown command: {user_input}")
                except queue.Empty:
                    pass
                
                # Display audio level
                audio_level = self.client.get_audio_level()
                level_bars = int(audio_level * 20)
                level_display = "█" * level_bars + "░" * (20 - level_bars)
                
                status = self.client.get_live_audio_status()
                speech_status = "SPEAKING" if status.get("speech_active", False) else "SILENT"
                
                elapsed = time.time() - start_time
                print(f"\r⏱️  {elapsed:6.1f}s | 🔊 {level_display} | 🎤 {speech_status} | 💬 Type 's', 'd', or 'q'", end="", flush=True)
                
                await asyncio.sleep(0.1)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Interactive loop error: {e}")
                break

    async def _show_status(self):
        """Show current status information."""
        print("\n" + "=" * 50)
        print("📊 CURRENT STATUS")
        print("=" * 50)
        
        # Session status
        session_status = self.client.get_session_status()
        print(f"Session: {session_status.get('status', 'Unknown')}")
        print(f"Conversation ID: {session_status.get('conversation_id', 'None')}")
        
        # Live audio status
        live_status = self.client.get_live_audio_status()
        print(f"Live Audio: {'Running' if live_status.get('running', False) else 'Stopped'}")
        print(f"Speech Active: {'Yes' if live_status.get('speech_active', False) else 'No'}")
        print(f"Audio Level: {self.client.get_audio_level():.3f}")
        
        # VAD status
        vad_status = self.client.get_vad_status()
        print(f"VAD Enabled: {'Yes' if vad_status.get('enabled', False) else 'No'}")
        
        print("=" * 50)

    async def _show_devices(self):
        """Show available audio devices."""
        print("\n" + "=" * 50)
        print("📱 AVAILABLE AUDIO DEVICES")
        print("=" * 50)
        
        devices = self.client.get_available_audio_devices()
        for i, device in enumerate(devices):
            default_marker = " (DEFAULT)" if device.get("is_default", False) else ""
            print(f"{i}: {device['name']}{default_marker}")
            print(f"   Channels: {device['channels']}, Sample Rate: {device['sample_rate']}Hz")
        
        print("=" * 50)


async def main():
    """Main function to run the live audio examples."""
    print("🎤 MockAudioCodesClient - Live Audio Capture Examples")
    print("=" * 60)
    
    # Get bridge URL from command line or use default
    bridge_url = "ws://localhost:8080"
    if len(sys.argv) > 1:
        bridge_url = sys.argv[1]
    
    print(f"Bridge URL: {bridge_url}")
    
    # Create example instance
    example = LiveAudioExample(bridge_url)
    
    # Choose example type
    print("\nChoose example type:")
    print("1. Basic live audio capture")
    print("2. Interactive live audio capture")
    
    try:
        choice = input("\nEnter choice (1-2, default 1): ").strip()
        if choice == "2":
            await example.run_interactive_example()
        else:
            await example.run_basic_example()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run the example
    asyncio.run(main()) 