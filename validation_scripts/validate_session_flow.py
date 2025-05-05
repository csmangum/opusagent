"""
Validation script for TelephonyRealtimeBridge message flow sequences.

This script validates key message sequences:
1. Session flow: session.initiate → SessionCreatedEvent → session.accepted
2. Audio stream flow: userStream.start → userStream.started → userStream.chunk → userStream.stop → userStream.stopped

Usage:
    python validation_scripts/validate_session_flow.py
"""

import asyncio
import base64
import json
import os
import sys
import time
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
TIMEOUT_SECONDS = 15

# Sample PCM16 audio data (silence) - this is just a placeholder
SILENCE_AUDIO = base64.b64encode(b"\x00" * 1024).decode("utf-8")


async def validate_session_flow():
    """Validate the proper sequence of session initialization flow."""
    print(f"\n[1/2] Testing session.initiate to session.accepted flow...")
    print(f"Connecting to {WS_URL}...")

    try:
        async with websockets.connect(WS_URL, ping_interval=5, ping_timeout=20) as ws:
            print("✅ WebSocket connection established")

            # Step 1: Send session.initiate
            conversation_id = f"test_session_{int(time.time())}"
            session_initiate = {
                "type": "session.initiate",
                "conversationId": conversation_id,
                "expectAudioMessages": True,
                "botName": "TestBot",
                "caller": "+15551234567",
                "supportedMediaFormats": ["raw/lpcm16"],
            }

            start_time = time.time()
            await ws.send(json.dumps(session_initiate))
            print(f"✅ Sent session.initiate with conversationId: {conversation_id}")

            # Step 2: Wait for session.accepted response
            print("Waiting for session.accepted response...")
            session_accepted = False

            for _ in range(
                TIMEOUT_SECONDS * 2
            ):  # Check every 0.5 seconds for timeout seconds
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    response_data = json.loads(response)
                    msg_type = response_data.get("type")

                    # Print all messages for debugging
                    print(f"   Received message: {msg_type}")

                    if msg_type == "session.accepted":
                        session_accepted = True
                        elapsed_time = time.time() - start_time
                        print(
                            f"✅ Session accepted successfully after {elapsed_time:.2f} seconds"
                        )
                        print(f"   Media format: {response_data.get('mediaFormat')}")
                        break

                except asyncio.TimeoutError:
                    # Send a ping to keep the connection alive
                    await ws.ping()
                    continue

            if not session_accepted:
                print("❌ ERROR: session.accepted was not received within timeout")
                return False

            # End the session gracefully
            try:
                session_end = {
                    "type": "session.end",
                    "conversationId": conversation_id,
                    "reasonCode": "normal",
                    "reason": "Validation completed",
                }
                await ws.send(json.dumps(session_end))
                print("✅ Sent session.end event")

                # Allow a moment for clean shutdown
                await asyncio.sleep(1)
            except websockets.exceptions.ConnectionClosed:
                print("❌ Connection closed before ending session")

            return session_accepted

    except ConnectionRefusedError:
        print("❌ Connection refused. Is the server running?")
        return False
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ Connection closed unexpectedly: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        return False


async def validate_audio_stream_flow():
    """Validate the userStream.start to userStream.stopped flow."""
    print(f"\n[2/2] Testing userStream.start to userStream.stopped flow...")
    print(f"Connecting to {WS_URL}...")

    try:
        async with websockets.connect(WS_URL, ping_interval=5, ping_timeout=20) as ws:
            print("✅ WebSocket connection established")

            # First establish a session
            conversation_id = f"test_audio_{int(time.time())}"
            session_initiate = {
                "type": "session.initiate",
                "conversationId": conversation_id,
                "expectAudioMessages": True,
                "botName": "TestBot",
                "caller": "+15551234567",
                "supportedMediaFormats": ["raw/lpcm16"],
            }

            await ws.send(json.dumps(session_initiate))
            print(f"Sent session.initiate with conversationId: {conversation_id}")

            # Wait for session.accepted
            session_accepted = False
            for _ in range(TIMEOUT_SECONDS * 2):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    response_data = json.loads(response)
                    if response_data.get("type") == "session.accepted":
                        session_accepted = True
                        print("✅ Session accepted")
                        break
                except asyncio.TimeoutError:
                    await ws.ping()
                    continue

            if not session_accepted:
                print("❌ Session establishment failed")
                return False

            # Step 1: Send userStream.start
            user_stream_start = {
                "type": "userStream.start",
                "conversationId": conversation_id,
            }
            await ws.send(json.dumps(user_stream_start))
            print("✅ Sent userStream.start")

            # Step 2: Wait for userStream.started
            stream_started = False
            for _ in range(TIMEOUT_SECONDS * 2):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    response_data = json.loads(response)
                    msg_type = response_data.get("type")
                    print(f"   Received message: {msg_type}")

                    if msg_type == "userStream.started":
                        stream_started = True
                        print("✅ Received userStream.started")
                        break
                except asyncio.TimeoutError:
                    await ws.ping()
                    continue

            if not stream_started:
                print("❌ ERROR: userStream.started was not received within timeout")
                return False

            # Step 3: Send audio chunks
            print("Sending audio chunks...")
            for i in range(5):
                audio_chunk = {
                    "type": "userStream.chunk",
                    "conversationId": conversation_id,
                    "audioChunk": SILENCE_AUDIO,
                }
                await ws.send(json.dumps(audio_chunk))
                print(f"   Sent audio chunk {i+1}")
                await asyncio.sleep(0.1)

            # Step 4: Send userStream.stop
            user_stream_stop = {
                "type": "userStream.stop",
                "conversationId": conversation_id,
            }
            await ws.send(json.dumps(user_stream_stop))
            print("✅ Sent userStream.stop")

            # Step 5: Wait for userStream.stopped
            stream_stopped = False
            for _ in range(TIMEOUT_SECONDS * 2):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    response_data = json.loads(response)
                    msg_type = response_data.get("type")
                    print(f"   Received message: {msg_type}")

                    if msg_type == "userStream.stopped":
                        stream_stopped = True
                        print("✅ Received userStream.stopped")
                        break

                    # Skip processing other message types but keep waiting for userStream.stopped
                except asyncio.TimeoutError:
                    await ws.ping()
                    continue

            if not stream_stopped:
                print("❌ ERROR: userStream.stopped was not received within timeout")
                return False

            # End the session gracefully
            try:
                session_end = {
                    "type": "session.end",
                    "conversationId": conversation_id,
                    "reasonCode": "normal",
                    "reason": "Validation completed",
                }
                await ws.send(json.dumps(session_end))
                print("✅ Sent session.end event")

                # Allow a moment for clean shutdown
                await asyncio.sleep(1)
            except websockets.exceptions.ConnectionClosed:
                print("❌ Connection closed before ending session")

            return stream_stopped

    except ConnectionRefusedError:
        print("❌ Connection refused. Is the server running?")
        return False
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ Connection closed unexpectedly: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        return False


async def main():
    """Run the validation script."""
    print("=== TelephonyRealtimeBridge Message Flow Validation ===")

    # Check if server is running
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((HOST, PORT))
    sock.close()

    if result != 0:
        print(f"❌ Server not found at {HOST}:{PORT}")
        print("Please start the server with: python run.py")
        return

    # Run session flow validation
    session_success = await validate_session_flow()

    # Run audio stream flow validation
    audio_success = await validate_audio_stream_flow()

    # Report results
    print("\n=== Validation Results ===")
    if session_success:
        print(
            "✅ Session flow: PASSED - session.initiate → SessionCreatedEvent → session.accepted"
        )
    else:
        print(
            "❌ Session flow: FAILED - Check if the bridge properly handles the session initialization sequence"
        )

    if audio_success:
        print(
            "✅ Audio stream flow: PASSED - userStream.start → userStream.started → userStream.chunk → userStream.stop → userStream.stopped"
        )
    else:
        print(
            "❌ Audio stream flow: FAILED - Check if the bridge properly handles the audio streaming sequence"
        )

    if session_success and audio_success:
        print("\n✅ ALL VALIDATIONS PASSED!")
    else:
        print("\n❌ SOME VALIDATIONS FAILED")


if __name__ == "__main__":
    # Create validation_scripts directory if it doesn't exist
    Path("validation_scripts").mkdir(exist_ok=True)

    # Run the validation
    asyncio.run(main())
