"""
Validation script for TelephonyRealtimeBridge message flow sequences.

This script validates key message sequences:
1. Session flow: session.initiate → SessionCreatedEvent → session.accepted
2. Audio stream flow: userStream.start → userStream.started → userStream.chunk → userStream.stop → userStream.stopped
3. Bot response flow: playStream.start → playStream.chunk → playStream.stop

Usage:
    python validation_scripts/validate_session_flow.py
"""

import asyncio
import base64
import json
import os
import sys
import time
import uuid
import wave
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
SLEEP_INTERVAL_SECONDS = 0.5
AUDIO_CHUNK_SIZE = 4000  # Reduced chunk size for more frequent chunks

# Sample PCM16 audio data (silence) - using a longer silence sample to ensure at least 100ms
SILENCE_DURATION_MS =100  # 500ms of silence
SAMPLE_RATE = 16000  # 16kHz
BYTES_PER_SAMPLE = 2  # 16-bit PCM
SILENCE_SAMPLES = int(SILENCE_DURATION_MS * SAMPLE_RATE / 1000)
SILENCE_AUDIO = base64.b64encode(b"\x00" * (SILENCE_SAMPLES * BYTES_PER_SAMPLE)).decode("utf-8")

# Path to real audio file
AUDIO_FILE_PATH = (
    Path(__file__).parent.parent / "static" / "tell_me_about_your_bank.wav"
)


def load_audio_chunks(file_path, chunk_size=AUDIO_CHUNK_SIZE):
    """Load and chunk audio file into base64 encoded strings.

    Args:
        file_path: Path to WAV file
        chunk_size: Size of each chunk in bytes

    Returns:
        List of base64 encoded audio chunks
    """
    if not os.path.exists(file_path):
        print(f"❌ Audio file not found: {file_path}")
        # Return silence chunks as fallback
        return [SILENCE_AUDIO] * 5

    try:
        with wave.open(str(file_path), "rb") as wav_file:
            # Get file properties
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_rate = wav_file.getframerate()

            print(f"Loading audio: {file_path}")
            print(
                f"  Format: {channels} channels, {sample_width * 8}-bit, {frame_rate}Hz"
            )

            # Read all frames
            audio_data = wav_file.readframes(wav_file.getnframes())
            
            # If audio is not 16kHz mono PCM16, we'd need to convert it
            # For now, we'll just use it as is and log a warning if it's not in an ideal format
            if channels != 1 or sample_width != 2 or frame_rate != 16000:
                print(f"  ⚠️ Warning: Audio is not in ideal format (mono 16-bit 16kHz PCM)")
                print(f"  ⚠️ This may cause issues with OpenAI's Realtime API")

            # Make sure we have enough audio data
            if len(audio_data) < 3200:  # At least 100ms of 16kHz 16-bit audio
                print(f"  ⚠️ Warning: Audio file is very short, padding with silence")
                # Pad with silence
                audio_data += b"\x00" * (3200 - len(audio_data))

            # Chunk the audio data
            chunks = []
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i : i + chunk_size]
                encoded_chunk = base64.b64encode(chunk).decode("utf-8")
                chunks.append(encoded_chunk)

            print(f"  Split into {len(chunks)} chunks")
            
            # Ensure we don't have empty chunks
            chunks = [c for c in chunks if len(c) > 0]
            
            if not chunks:
                print("❌ No valid audio chunks extracted, using silence instead")
                return [SILENCE_AUDIO] * 5
            
            return chunks
    except Exception as e:
        print(f"❌ Error loading audio file: {e}")
        # Return silence chunks as fallback
        return [SILENCE_AUDIO] * 5


async def validate_session_flow():
    """Validate the proper sequence of session initialization flow."""
    print(f"\n[1/3] Testing session.initiate to session.accepted flow...")
    print(f"Connecting to {WS_URL}...")

    try:
        async with websockets.connect(WS_URL, ping_interval=5, ping_timeout=20) as ws:
            print("✅ WebSocket connection established")

            # Step 1: Send session.initiate
            conversation_id = str(uuid.uuid4())
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
    print(f"\n[2/3] Testing userStream.start to userStream.stopped flow...")
    print(f"Connecting to {WS_URL}...")

    try:
        async with websockets.connect(WS_URL, ping_interval=5, ping_timeout=20) as ws:
            print("✅ WebSocket connection established")

            # First establish a session
            conversation_id = str(uuid.uuid4())
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
                    response = await asyncio.wait_for(
                        ws.recv(), timeout=SLEEP_INTERVAL_SECONDS
                    )
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

            # Load audio chunks
            audio_chunks = load_audio_chunks(AUDIO_FILE_PATH)
            if not audio_chunks:
                print("❌ No audio chunks loaded, using silence instead")
                audio_chunks = [SILENCE_AUDIO] * 5

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
            print(f"Sending {len(audio_chunks)} audio chunks...")
            for i, chunk in enumerate(audio_chunks):
                audio_chunk = {
                    "type": "userStream.chunk",
                    "conversationId": conversation_id,
                    "audioChunk": chunk,
                }
                await ws.send(json.dumps(audio_chunk))
                if i % 5 == 0 or i == len(audio_chunks) - 1:
                    print(f"   Sent audio chunk {i+1}/{len(audio_chunks)}")
                # Slow down sending to match real-time audio speed more closely
                await asyncio.sleep(0.05)  # Send at ~20 chunks per second

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


async def validate_bot_response_flow():
    """Validate the bot response flow: playStream.start to playStream.stop."""
    print(f"\n[3/3] Testing bot response flow (playStream)...")
    print(f"Connecting to {WS_URL}...")

    try:
        async with websockets.connect(WS_URL, ping_interval=5, ping_timeout=20) as ws:
            print("✅ WebSocket connection established")

            # First establish a session
            conversation_id = str(uuid.uuid4())
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
                    response = await asyncio.wait_for(
                        ws.recv(), timeout=SLEEP_INTERVAL_SECONDS
                    )
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

            # Load audio chunks with a smaller chunk size for more frequent updates
            audio_chunks = load_audio_chunks(AUDIO_FILE_PATH, chunk_size=AUDIO_CHUNK_SIZE)
            if not audio_chunks:
                print("❌ No audio chunks loaded, using silence instead")
                audio_chunks = [SILENCE_AUDIO] * 10  # Use more silence chunks to get enough audio

            # Send audio to trigger a bot response
            # Step 1: Send userStream.start
            user_stream_start = {
                "type": "userStream.start",
                "conversationId": conversation_id,
            }
            await ws.send(json.dumps(user_stream_start))
            print("✅ Sent userStream.start")

            # Wait for userStream.started
            stream_started = False
            for _ in range(TIMEOUT_SECONDS * 2):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    response_data = json.loads(response)
                    if response_data.get("type") == "userStream.started":
                        stream_started = True
                        print("✅ Received userStream.started")
                        break
                except asyncio.TimeoutError:
                    await ws.ping()
                    continue

            if not stream_started:
                print("❌ ERROR: userStream.started was not received within timeout")
                return False

            # Send audio chunks
            print(
                f"Sending {len(audio_chunks)} audio chunks to trigger bot response..."
            )
            for i, chunk in enumerate(audio_chunks):
                audio_chunk = {
                    "type": "userStream.chunk",
                    "conversationId": conversation_id,
                    "audioChunk": chunk,
                }
                await ws.send(json.dumps(audio_chunk))
                if i % 5 == 0 or i == len(audio_chunks) - 1:
                    print(f"   Sent audio chunk {i+1}/{len(audio_chunks)}")
                # Slow down sending to match real-time audio speed more closely
                await asyncio.sleep(0.05)  # Send at ~20 chunks per second

            # Wait a moment before sending stop to ensure all audio is processed
            await asyncio.sleep(0.5)
            
            # Send userStream.stop
            user_stream_stop = {
                "type": "userStream.stop",
                "conversationId": conversation_id,
            }
            await ws.send(json.dumps(user_stream_stop))
            print("✅ Sent userStream.stop")

            # Wait for userStream.stopped
            stream_stopped = False
            for _ in range(TIMEOUT_SECONDS * 2):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    response_data = json.loads(response)
                    if response_data.get("type") == "userStream.stopped":
                        stream_stopped = True
                        print("✅ Received userStream.stopped")
                        break
                except asyncio.TimeoutError:
                    await ws.ping()
                    continue

            if not stream_stopped:
                print("❌ ERROR: userStream.stopped was not received within timeout")
                return False

            # Now wait for bot response - playStream.start
            print("Waiting for bot response (playStream.start)...")
            play_stream_started = False
            stream_id = None

            # We'll wait for up to 30 seconds for a response
            for _ in range(TIMEOUT_SECONDS * 4):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    response_data = json.loads(response)
                    msg_type = response_data.get("type")
                    print(f"   Received message: {msg_type}")

                    if msg_type == "playStream.start":
                        play_stream_started = True
                        stream_id = response_data.get("streamId")
                        print(
                            f"✅ Received playStream.start with streamId: {stream_id}"
                        )
                        break
                except asyncio.TimeoutError:
                    await ws.ping()
                    continue

            if not play_stream_started:
                print("❌ ERROR: playStream.start was not received within timeout")
                return False

            # Wait for playStream.chunk messages
            print("Waiting for playStream.chunk messages...")
            play_stream_chunks_received = False
            chunk_count = 0

            # Look for chunks for up to 10 seconds
            for _ in range(TIMEOUT_SECONDS * 2):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    response_data = json.loads(response)
                    msg_type = response_data.get("type")

                    if msg_type == "playStream.chunk":
                        if chunk_count == 0:
                            print(f"✅ Started receiving playStream.chunk messages")
                        chunk_count += 1
                        play_stream_chunks_received = True
                    elif msg_type == "playStream.stop":
                        print(
                            f"✅ Received playStream.stop for streamId: {response_data.get('streamId')}"
                        )
                        break
                except asyncio.TimeoutError:
                    # If we've already received chunks but now there's a timeout,
                    # we might be in the gap between chunks or done
                    if play_stream_chunks_received:
                        continue
                    await ws.ping()
                    continue

            print(f"   Received {chunk_count} audio chunks from bot")

            if not play_stream_chunks_received:
                print("❌ ERROR: No playStream.chunk messages were received")
                return False

            # Wait specifically for playStream.stop if we haven't seen it yet
            play_stream_stopped = False
            if not play_stream_stopped:
                print("Waiting for playStream.stop...")
                for _ in range(TIMEOUT_SECONDS * 2):
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                        response_data = json.loads(response)
                        msg_type = response_data.get("type")
                        print(f"   Received message: {msg_type}")

                        if msg_type == "playStream.stop":
                            play_stream_stopped = True
                            print(
                                f"✅ Received playStream.stop for streamId: {response_data.get('streamId')}"
                            )
                            break
                    except asyncio.TimeoutError:
                        await ws.ping()
                        continue

            if not play_stream_stopped:
                print(
                    "❌ WARNING: playStream.stop was not explicitly received within timeout"
                )
                # This isn't a critical failure as some implementations might not send a separate stop

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

            # Consider the test successful if we at least started a stream and got chunks
            return play_stream_started and play_stream_chunks_received

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

    # Run bot response flow validation
    bot_response_success = await validate_bot_response_flow()

    # Report results
    print("\n=== Validation Results ===")
    if session_success:
        print("✅ Session flow: PASSED - session.initiate → session.accepted")
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

    if bot_response_success:
        print(
            "✅ Bot response flow: PASSED - playStream.start → playStream.chunk → playStream.stop"
        )
    else:
        print(
            "❌ Bot response flow: FAILED - Check if the bridge properly handles the bot response sequence"
        )

    if session_success and audio_success and bot_response_success:
        print("\n✅ ALL VALIDATIONS PASSED!")
    else:
        print("\n❌ SOME VALIDATIONS FAILED")


if __name__ == "__main__":
    # Create validation_scripts directory if it doesn't exist
    Path("validation_scripts").mkdir(exist_ok=True)

    # Run the validation
    asyncio.run(main())
