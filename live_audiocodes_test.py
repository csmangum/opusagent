import asyncio
import time

from opusagent.config.logging_config import configure_logging
from opusagent.local.audiocodes.client import LocalAudioCodesClient


# Configure logging
logger = configure_logging("live_audiocodes_test", log_filename="live_audiocodes_test.log")

async def main():
    
    # Default bridge URL - adjust if server is running on different host/port
    bridge_url = "ws://localhost:8080/ws/telephony"
    
    # Create client instance without connecting
    client = LocalAudioCodesClient(bridge_url, logger=logger)
    
    # List available audio devices before connecting
    devices = client.get_available_audio_devices()
    if not devices:
        print("⚠️ No audio devices found, using default")
        device_index = None
    else:
        print("\nAvailable audio devices:")
        for dev in devices:
            default_mark = " (default)" if dev["is_default"] else ""
            print(f"{dev['index']}: {dev['name']}{default_mark}")
        
        try:
            index_input = input("\nSelect device index (press Enter for default): ")
            device_index = int(index_input) if index_input else None
        except ValueError:
            print("Invalid input, using default device")
            device_index = None
    
    print("Connecting to bridge server...")
    async with client:
        # Initiate session
        if not await client.initiate_session():
            print("❌ Failed to initiate session")
            return
            
        print("✅ Session initiated successfully")
        
        # Start live audio capture with selected device
        if client.start_live_audio_capture(device_index=device_index):
            # Enable audio playback
            client.enable_audio_playback(volume=1.0)
            
            print("\n✅ Live capture and playback started")
            print("The AI will greet you. Then speak clearly into your microphone.")
            print("If nothing happens after speaking, check mic volume or select a different device.")
            print("Press Ctrl+C to stop")
            
            try:
                last_status_time = time.time()
                while True:
                    await asyncio.sleep(1)
                    
                    # Print status every 5 seconds (increased frequency for better feedback)
                    current_time = time.time()
                    if current_time - last_status_time >= 5:
                        status = client.get_session_status()
                        input_level = client.get_audio_level()
                        output_level = client.get_playback_audio_level()
                        vad_status = status.get('vad', {}).get('vad_manager_status', {})
                        
                        print("\n📊 Call Status Update:")
                        print(f"   Session: {status.get('status', 'Unknown')}")
                        print(f"   Conversation ID: {status.get('conversation_id', 'N/A')}")
                        print(f"   Input Audio Level: {input_level:.2f} (speak louder if <0.10)")
                        print(f"   Output Audio Level: {output_level:.2f}")
                        print(f"   VAD Active: {vad_status.get('speech_active', False)}")
                        print(f"   Speech Probability: {vad_status.get('last_speech_prob', 0):.2f}")
                        last_status_time = current_time
            
            except KeyboardInterrupt:
                print("\nStopping...")
            finally:
                # Cleanup
                client.stop_live_audio_capture()
                await client.end_session("Live test completed")
                print("✅ Session ended")
        else:
            print("❌ Failed to start live audio capture")
            await client.end_session("Failed to start capture")

if __name__ == "__main__":
    asyncio.run(main()) 