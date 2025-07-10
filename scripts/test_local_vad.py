#!/usr/bin/env python3
"""
Test script for Local VAD Client

This script demonstrates how to use the LocalVADClient for real-time
microphone input with voice activity detection.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opusagent.mock.local_vad_client import LocalVADClient


async def test_local_vad():
    """Test the local VAD client."""
    print("🎤 Local VAD Client Test")
    print("=" * 50)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Bridge URL (adjust as needed)
    bridge_url = "ws://localhost:8000/caller-agent"
    
    print(f"🔗 Connecting to bridge: {bridge_url}")
    print("🎙️  Speak into your microphone to test VAD")
    print("⏱️  Test will run for 30 seconds")
    print("-" * 50)
    
    try:
        # Create and run client
        async with LocalVADClient(
            bridge_url=bridge_url,
            vad_sensitivity=0.05,  # Adjust sensitivity as needed
            vad_silence_duration=1.5,  # 1.5 seconds of silence to end speech
            sample_rate=16000,
            chunk_size=1024
        ) as client:
            
            # Run conversation
            success = await client.run_conversation(duration=30.0)
            
            if success:
                print("✅ Test completed successfully")
            else:
                print("❌ Test failed")
                
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    
    return True


async def test_vad_sensitivity():
    """Test different VAD sensitivity levels."""
    print("\n🎛️  VAD Sensitivity Test")
    print("=" * 50)
    
    sensitivities = [0.02, 0.05, 0.1, 0.2]
    
    for sensitivity in sensitivities:
        print(f"\n🔧 Testing sensitivity: {sensitivity}")
        print(f"📝 Speak at different volumes to test detection")
        
        try:
            async with LocalVADClient(
                bridge_url="ws://localhost:8000/caller-agent",
                vad_sensitivity=sensitivity,
                vad_silence_duration=1.0,
            ) as client:
                await client.run_conversation(duration=10.0)
                
        except Exception as e:
            print(f"❌ Error with sensitivity {sensitivity}: {e}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Local VAD Client")
    parser.add_argument("--bridge-url", default="ws://localhost:8000/caller-agent",
                       help="Bridge WebSocket URL")
    parser.add_argument("--duration", type=float, default=30.0,
                       help="Test duration in seconds")
    parser.add_argument("--sensitivity", type=float, default=0.05,
                       help="VAD sensitivity (0.0-1.0)")
    parser.add_argument("--silence", type=float, default=1.5,
                       help="Silence duration to end speech (seconds)")
    parser.add_argument("--test-sensitivity", action="store_true",
                       help="Test multiple sensitivity levels")
    
    args = parser.parse_args()
    
    if args.test_sensitivity:
        asyncio.run(test_vad_sensitivity())
    else:
        asyncio.run(test_local_vad())


if __name__ == "__main__":
    main() 