"""
Validation script for the TelephonyRealtimeBridge initialization.

This script simulates a telephony client connecting to the bridge and validates
that initialization works correctly. It checks:
1. WebSocket connection establishment
2. Session initialization
3. Initial greeting response from the AI

Usage:
    python validation_scripts/validate_telephony_bridge.py
"""

import asyncio
import base64
import json
import os
import sys
from pathlib import Path

import websockets
from dotenv import load_dotenv

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Configuration
HOST = os.getenv("HOST", "localhost")
PORT = int(os.getenv("PORT", "8000"))
WS_URL = f"ws://{HOST}:{PORT}/voice-bot"

# Sample PCM16 audio data (silence) - this is just a placeholder
# In a real scenario, you'd have actual audio data
SILENCE_AUDIO = base64.b64encode(b'\x00' * 1024).decode('utf-8')


async def simulate_telephony_client():
    """Simulate a telephony client connecting to our bridge."""
    print(f"Connecting to {WS_URL}...")
    
    try:
        async with websockets.connect(WS_URL, ping_interval=5, ping_timeout=20) as ws:
            print("✅ WebSocket connection established")
            
            # 1. Send a session initiate event (using AudioCodes model format)
            conversation_id = "test_conversation_" + asyncio.current_task().get_name()[-6:]
            session_initiate = {
                "type": "session.initiate",
                "conversationId": conversation_id,
                "expectAudioMessages": True,
                "botName": "TestBot",
                "caller": "+15551234567",
                "supportedMediaFormats": ["raw/lpcm16"]
            }
            await ws.send(json.dumps(session_initiate))
            print(f"✅ Sent session.initiate event with conversationId: {conversation_id}")
            
            # 2. Wait for session accepted response
            print("Waiting for session.accepted response...")
            
            # 3. Send a stream start event (using AudioCodes model format)
            user_stream_start = {
                "type": "userStream.start",
                "conversationId": conversation_id
            }
            await ws.send(json.dumps(user_stream_start))
            print(f"✅ Sent userStream.start event for conversation: {conversation_id}")
            
            # 4. Wait for initial response from AI (should respond automatically)
            print("Waiting for initial AI greeting...")
            response_received = False
            audio_chunks_received = 0
            session_created = False
            
            # Set a timeout for receiving the initial greeting
            try:
                # Wait for up to 60 seconds to receive the initial greeting
                for _ in range(120):  # Try 120 times with 0.5 second delays
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                        response_data = json.loads(response)
                        
                        # Handle media events (no type field)
                        if 'event' in response_data and response_data['event'] == 'media':
                            if response_data.get('media', {}).get('payload'):
                                audio_size = len(response_data['media']['payload'])
                                print(f"✅ Received audio data from server (size: {audio_size} bytes)")
                                audio_chunks_received += 1
                                if not response_received:
                                    print("✅ Received first audio chunk from AI")
                                    response_received = True
                            continue
                        
                        # Print all messages for debugging
                        print(f"   Received message type: {response_data.get('type')}")
                        
                        # Check for session creation
                        if response_data.get("type") == "session.accepted":
                            print("✅ Session accepted successfully")
                            session_created = True
                            continue
                        
                        # Check for userStream.started response
                        if response_data.get("type") == "userStream.started":
                            print("✅ User stream started successfully")
                            continue
                        
                        # Check for response creation
                        if response_data.get("type") == "response.created":
                            print("✅ Response created successfully")
                            continue
                        
                        # Check for audio response
                        if response_data.get("type") == "response.audio.delta" and "audio" in response_data:
                            audio_size = len(response_data["audio"])
                            print(f"✅ Received audio response from OpenAI (size: {audio_size} bytes)")
                            continue
                        
                        # Check for playStream messages
                        if response_data.get("type") == "playStream.start":
                            print("✅ Play stream started from server")
                            continue
                            
                        if response_data.get("type") == "playStream.chunk":
                            print(f"✅ Received audio chunk from server (stream: {response_data.get('streamId', 'unknown')})")
                            audio_chunks_received += 1
                            if not response_received:
                                print("✅ Received first audio chunk from AI")
                                response_received = True
                            continue
                        
                        # Check for response done
                        if response_data.get("type") == "response.done" or response_data.get("type") == "playStream.stop":
                            print("✅ Response completed")
                            break
                        
                        # Check for errors
                        if response_data.get("type") == "session.error":
                            print(f"❌ Session error: {response_data.get('reason')}")
                            break
                            
                        # Print any other message types for debugging
                        print(f"   Unhandled message type: {response_data.get('type')}")
                        print(f"   Full message: {response_data}")
                        
                    except asyncio.TimeoutError:
                        # Send a ping to keep the connection alive
                        await ws.ping()
                        continue
                
                if not session_created:
                    print("❌ Session was not accepted within the timeout period")
                    return
                
                if not response_received:
                    print("❌ No audio response received within the timeout period")
                    return
            
            except asyncio.TimeoutError:
                print("⚠️ Timeout waiting for AI response after 60 seconds")
            
            # 5. Send some audio data to simulate user speaking
            if response_received:
                # Send audio data continuously
                print("Sending audio data...")
                for i in range(20):  # Send more audio chunks
                    try:
                        audio_chunk = {
                            "type": "userStream.chunk",
                            "conversationId": conversation_id,
                            "audioChunk": SILENCE_AUDIO
                        }
                        await ws.send(json.dumps(audio_chunk))
                        print(f"   Sent audio chunk {i+1}")
                        await asyncio.sleep(0.1)  # Smaller delay between chunks
                    except websockets.exceptions.ConnectionClosed:
                        print("❌ Connection closed while sending audio")
                        break
                
                # Wait for AI response to our audio
                print("Waiting for AI response to our audio...")
                audio_chunks_received = 0
                try:
                    for _ in range(60):  # Try more times with smaller delays
                        try:
                            response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                            response_data = json.loads(response)
                            
                            if response_data.get("type") == "playStream.chunk":
                                audio_chunks_received += 1
                                print(f"✅ Received audio chunk {audio_chunks_received} in response to our input")
                            
                            # Check for response done
                            if response_data.get("type") == "playStream.stop" or response_data.get("type") == "response.done":
                                print("✅ Response completed")
                                break
                            
                            # Print all messages for debugging
                            print(f"   Received message type: {response_data.get('type')}")
                        except asyncio.TimeoutError:
                            # Send a ping to keep the connection alive
                            await ws.ping()
                            continue
                except asyncio.TimeoutError:
                    print("⚠️ Timeout waiting for AI response to our audio")
            
            # 6. Send stream stop and session end
            try:
                # Stop the user stream
                user_stream_stop = {
                    "type": "userStream.stop",
                    "conversationId": conversation_id
                }
                await ws.send(json.dumps(user_stream_stop))
                print("✅ Sent userStream.stop event")
                
                # End the session
                session_end = {
                    "type": "session.end",
                    "conversationId": conversation_id,
                    "reasonCode": "normal",
                    "reason": "Test completed"
                }
                await ws.send(json.dumps(session_end))
                print("✅ Sent session.end event")
            except websockets.exceptions.ConnectionClosed:
                print("❌ Connection closed before sending stop event")
            
            # Allow a moment for clean shutdown
            await asyncio.sleep(1)
            
    except ConnectionRefusedError:
        print("❌ Connection refused. Is the server running?")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ Connection closed: {e}")
    except Exception as e:
        print(f"❌ Error during validation: {e}")


async def main():
    """Run the validation script."""
    print("=== TelephonyRealtimeBridge Initialization Validation ===")
    print("This script validates the initialization of the telephony bridge.")
    
    # Check if server is running
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((HOST, PORT))
    sock.close()
    
    if result != 0:
        print(f"❌ Server not found at {HOST}:{PORT}")
        print("Please start the server with: python run.py")
        return
    
    # Run the validation
    await simulate_telephony_client()


if __name__ == "__main__":
    # Create validation_scripts directory if it doesn't exist
    Path("validation_scripts").mkdir(exist_ok=True)
    
    # Run the validation
    asyncio.run(main()) 