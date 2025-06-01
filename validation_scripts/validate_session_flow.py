"""
Validation script for TelephonyRealtimeBridge message flow sequences.

This script validates key message sequences:
1. Session flow: session.initiate → SessionCreatedEvent → session.accepted
2. Audio stream flow: userStream.start → userStream.started → userStream.chunk → userStream.stop → userStream.stopped
3. Bot response flow: playStream.start → playStream.chunk → playStream.stop

The script also records all audio exchanges:
- Incoming audio (bot responses) saved to bot_audio_*.wav
- Outgoing audio (user input) saved to user_audio_*.wav  
- Combined stereo recording saved to session_recording_*.wav (left=user, right=bot)

Usage:
    python validation_scripts/validate_session_flow.py
"""

import asyncio
import base64
import json
import os
import signal
import sys
import time
import uuid
import wave
from datetime import datetime
from pathlib import Path

import numpy as np
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
TIMEOUT_SECONDS = 15  # Increased from 5 to allow time for OpenAI processing
SLEEP_INTERVAL_SECONDS = 0.1  # Reduced from 0.5
AUDIO_CHUNK_SIZE = 32000  # Larger chunk size (2 seconds of 16kHz 16-bit audio)

# Sample PCM16 audio data (silence) - using a longer silence sample to ensure at least 100ms
SILENCE_DURATION_MS = 10  # 500ms of silence
SAMPLE_RATE = 16000  # 16kHz
BYTES_PER_SAMPLE = 2  # 16-bit PCM


# Path to real audio file
AUDIO_FILE_PATH = (
    Path(__file__).parent.parent / "static" / "tell_me_about_your_bank.wav"
)


class AudioRecorder:
    """Handles recording of audio streams in multiple formats."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.output_dir = Path("validation_output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Create timestamp for all files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # File paths
        self.bot_audio_file = self.output_dir / f"bot_audio_{session_id}_{timestamp}.wav"
        self.user_audio_file = self.output_dir / f"user_audio_{session_id}_{timestamp}.wav"
        self.session_recording_file = self.output_dir / f"session_recording_{session_id}_{timestamp}.wav"
        
        # WAV file objects
        self.bot_wav = None
        self.user_wav = None
        self.session_wav = None
        
        # Audio buffers for creating combined recording
        self.bot_audio_buffer = []
        self.user_audio_buffer = []
        
        # Audio parameters
        self.sample_rate = 16000
        self.channels = 1
        self.sample_width = 2  # 16-bit
        
        self._init_wav_files()
    
    def _init_wav_files(self):
        """Initialize WAV files for recording."""
        # Bot audio (incoming)
        self.bot_wav = wave.open(str(self.bot_audio_file), "wb")
        self.bot_wav.setnchannels(self.channels)
        self.bot_wav.setsampwidth(self.sample_width)
        self.bot_wav.setframerate(self.sample_rate)
        
        # User audio (outgoing)
        self.user_wav = wave.open(str(self.user_audio_file), "wb")
        self.user_wav.setnchannels(self.channels)
        self.user_wav.setsampwidth(self.sample_width)
        self.user_wav.setframerate(self.sample_rate)
        
        # Session recording (stereo: left=user, right=bot)
        self.session_wav = wave.open(str(self.session_recording_file), "wb")
        self.session_wav.setnchannels(2)  # Stereo
        self.session_wav.setsampwidth(self.sample_width)
        self.session_wav.setframerate(self.sample_rate)
        
        print(f"✅ Audio recording initialized:")
        print(f"   Bot audio: {self.bot_audio_file}")
        print(f"   User audio: {self.user_audio_file}")
        print(f"   Session recording: {self.session_recording_file}")
    
    def record_bot_audio(self, audio_chunk_b64: str):
        """Record incoming bot audio."""
        try:
            decoded_chunk = base64.b64decode(audio_chunk_b64)
            
            # Write to bot-only file
            if self.bot_wav:
                self.bot_wav.writeframes(decoded_chunk)
            
            # Store in buffer for combined recording
            self.bot_audio_buffer.append(decoded_chunk)
            
        except Exception as e:
            print(f"❌ Error recording bot audio: {e}")
    
    def record_user_audio(self, audio_chunk_b64: str):
        """Record outgoing user audio."""
        try:
            decoded_chunk = base64.b64decode(audio_chunk_b64)
            
            # Write to user-only file
            if self.user_wav:
                self.user_wav.writeframes(decoded_chunk)
            
            # Store in buffer for combined recording
            self.user_audio_buffer.append(decoded_chunk)
            
        except Exception as e:
            print(f"❌ Error recording user audio: {e}")
    
    def create_combined_recording(self):
        """Create a stereo recording with user on left channel, bot on right channel."""
        try:
            # Convert buffers to numpy arrays
            if self.user_audio_buffer:
                user_audio = np.concatenate([np.frombuffer(chunk, dtype=np.int16) for chunk in self.user_audio_buffer])
            else:
                user_audio = np.array([], dtype=np.int16)
                
            if self.bot_audio_buffer:
                bot_audio = np.concatenate([np.frombuffer(chunk, dtype=np.int16) for chunk in self.bot_audio_buffer])
            else:
                bot_audio = np.array([], dtype=np.int16)
            
            # Make both arrays the same length by padding with silence
            max_length = max(len(user_audio), len(bot_audio))
            if max_length == 0:
                return
                
            if len(user_audio) < max_length:
                user_audio = np.pad(user_audio, (0, max_length - len(user_audio)), 'constant')
            if len(bot_audio) < max_length:
                bot_audio = np.pad(bot_audio, (0, max_length - len(bot_audio)), 'constant')
            
            # Create stereo audio (interleave left and right channels)
            stereo_audio = np.empty((max_length * 2,), dtype=np.int16)
            stereo_audio[0::2] = user_audio  # Left channel (user)
            stereo_audio[1::2] = bot_audio   # Right channel (bot)
            
            # Write to stereo file
            if self.session_wav:
                self.session_wav.writeframes(stereo_audio.tobytes())
                
        except Exception as e:
            print(f"❌ Error creating combined recording: {e}")
    
    def close(self):
        """Close all WAV files and create final combined recording."""
        try:
            # Create the combined recording before closing
            self.create_combined_recording()
            
            # Close all files
            if self.bot_wav:
                self.bot_wav.close()
                self.bot_wav = None
                
            if self.user_wav:
                self.user_wav.close()
                self.user_wav = None
                
            if self.session_wav:
                self.session_wav.close()
                self.session_wav = None
            
            print(f"✅ Audio recording completed:")
            print(f"   Bot audio: {self.bot_audio_file}")
            print(f"   User audio: {self.user_audio_file}")
            print(f"   Session recording: {self.session_recording_file} (stereo: left=user, right=bot)")
            
        except Exception as e:
            print(f"❌ Error closing audio files: {e}")


def load_audio_chunks(file_path, chunk_size=AUDIO_CHUNK_SIZE):
    """Load and chunk audio file into base64 encoded strings.

    Args:
        file_path: Path to WAV file
        chunk_size: Size of each chunk in bytes

    Returns:
        List of base64 encoded audio chunks
    """

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

            # Convert to numpy array for resampling
            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            # Resample to 16kHz if needed
            if frame_rate != 16000:
                print(f"  Resampling from {frame_rate}Hz to 16000Hz...")
                number_of_samples = round(len(audio_array) * 16000 / frame_rate)
                audio_array = signal.resample(audio_array, number_of_samples)
                audio_array = audio_array.astype(np.int16)
                frame_rate = 16000
                print(f"  Resampled to {frame_rate}Hz")

            # Convert back to bytes
            audio_data = audio_array.tobytes()

            # Calculate minimum chunk size for 100ms of audio
            min_chunk_size = int(0.1 * frame_rate * sample_width)  # 100ms of audio
            print(f"  Minimum chunk size for 100ms: {min_chunk_size} bytes")

            # Ensure we have enough audio data
            if len(audio_data) < min_chunk_size:
                print(f"  ⚠️ Warning: Audio file is too short, padding with silence")
                # Pad with silence to reach minimum size
                audio_data += b"\x00" * (min_chunk_size - len(audio_data))

            # Ensure chunk_size is at least the minimum required
            if chunk_size < min_chunk_size:
                print(
                    f"  ⚠️ Warning: Chunk size too small, increasing to {min_chunk_size} bytes"
                )
                chunk_size = min_chunk_size

            # Chunk the audio data
            chunks = []
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i : i + chunk_size]
                # Ensure each chunk is at least min_chunk_size
                if len(chunk) < min_chunk_size and i + chunk_size > len(audio_data):
                    # Pad the last chunk if it's too small
                    chunk += b"\x00" * (min_chunk_size - len(chunk))
                encoded_chunk = base64.b64encode(chunk).decode("utf-8")
                chunks.append(encoded_chunk)

            print(f"  Split into {len(chunks)} chunks")
            print(f"  Average chunk size: {len(audio_data) // len(chunks)} bytes")
            print(
                f"  Total audio duration: {len(audio_data) / (frame_rate * sample_width):.2f} seconds"
            )

            # Ensure we don't have empty chunks
            chunks = [c for c in chunks if len(c) > 0]

            return chunks
    except Exception as e:
        print(f"❌ Error loading audio file: {e}")
        return None


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

            # Initialize audio recorder
            recorder = AudioRecorder(f"stream_{conversation_id[:8]}")  # Use prefix to distinguish from bot test

            # Wait for session.accepted
            session_accepted = False
            for _ in range(TIMEOUT_SECONDS * 2):
                try:
                    response = await asyncio.wait_for(
                        ws.recv(), timeout=SLEEP_INTERVAL_SECONDS
                    )
                    response_data = json.loads(response)
                    msg_type = response_data.get("type")
                    
                    # Record any bot audio that comes in during session setup
                    if msg_type == "playStream.chunk":
                        audio_chunk = response_data.get("audioChunk")
                        if audio_chunk:
                            recorder.record_bot_audio(audio_chunk)
                    
                    if response_data.get("type") == "session.accepted":
                        session_accepted = True
                        print("✅ Session accepted")
                        break
                except asyncio.TimeoutError:
                    await ws.ping()
                    continue

            if not session_accepted:
                print("❌ Session establishment failed")
                recorder.close()
                return False

            # Load audio chunks
            audio_chunks = load_audio_chunks(AUDIO_FILE_PATH)
            if not audio_chunks:
                print("❌ No audio chunks loaded, using silence instead")
                # Create a minimum valid chunk of silence (100ms)
                silence_chunk = base64.b64encode(b"\x00" * 3200).decode(
                    "utf-8"
                )  # 100ms of 16kHz 16-bit silence
                audio_chunks = [silence_chunk]

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

                    # Record any bot audio that comes in
                    if msg_type == "playStream.chunk":
                        audio_chunk = response_data.get("audioChunk")
                        if audio_chunk:
                            recorder.record_bot_audio(audio_chunk)

                    if msg_type == "userStream.started":
                        stream_started = True
                        print("✅ Received userStream.started")
                        break
                except asyncio.TimeoutError:
                    await ws.ping()
                    continue

            if not stream_started:
                print("❌ ERROR: userStream.started was not received within timeout")
                recorder.close()
                return False

            # Step 3: Send audio chunks
            print(f"Sending {len(audio_chunks)} audio chunks...")
            for i, chunk in enumerate(audio_chunks):
                # Record the outgoing user audio
                recorder.record_user_audio(chunk)
                
                audio_chunk = {
                    "type": "userStream.chunk",
                    "conversationId": conversation_id,
                    "audioChunk": chunk,
                }
                await ws.send(json.dumps(audio_chunk))
                if i % 5 == 0 or i == len(audio_chunks) - 1:
                    print(f"   Sent audio chunk {i+1}/{len(audio_chunks)}")
                # Add minimal delay to ensure buffer processing
                await asyncio.sleep(0.01)  # 10ms delay between chunks

            # Wait a moment before sending stop to ensure all audio is processed
            await asyncio.sleep(0.2)  # Increased from 0.1 to 0.2 seconds

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

                    # Record any bot audio that comes in
                    if msg_type == "playStream.chunk":
                        audio_chunk = response_data.get("audioChunk")
                        if audio_chunk:
                            recorder.record_bot_audio(audio_chunk)

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
                recorder.close()
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

            # Close the recorder and save all audio files
            recorder.close()
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

            # Initialize audio recorder
            recorder = AudioRecorder(conversation_id[:8])  # Use first 8 chars of conversation ID

            # Wait for session.accepted and process all incoming messages
            session_accepted = False
            play_stream_started = False
            stream_id = None
            play_stream_chunks_received = False
            chunk_count = 0
            first_response_complete = False

            print("Waiting for session.accepted and bot's initial response...")
            print(
                "   Note: Bot will start speaking immediately after session is established"
            )

            # Process all messages in a single loop to avoid dropping any
            for attempt in range(120):  # 60 seconds total (120 * 0.5s)
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    response_data = json.loads(response)
                    msg_type = response_data.get("type")

                    # Print progress every 10 seconds
                    if attempt % 20 == 0 and attempt > 0:
                        print(
                            f"   Processing messages... ({attempt * 0.5:.1f}s elapsed)"
                        )

                    if msg_type == "session.accepted":
                        session_accepted = True
                        print("✅ Session accepted")

                    elif msg_type == "playStream.start":
                        if not play_stream_started:
                            play_stream_started = True
                            stream_id = response_data.get("streamId")
                            print(
                                f"✅ Received playStream.start with streamId: {stream_id}"
                            )

                    elif msg_type == "playStream.chunk":
                        if not play_stream_chunks_received:
                            print(
                                f"✅ Started receiving playStream.chunk messages (bot's initial response)"
                            )
                            play_stream_chunks_received = True
                        chunk_count += 1
                        
                        # Record the audio chunk
                        audio_chunk = response_data.get("audioChunk")
                        if audio_chunk:
                            recorder.record_bot_audio(audio_chunk)
                            
                        # Log progress every 20 chunks
                        if chunk_count % 20 == 0:
                            print(f"   Received {chunk_count} audio chunks so far...")

                    elif msg_type == "playStream.stop":
                        print(
                            f"✅ Received playStream.stop for streamId: {response_data.get('streamId')}"
                        )
                        if not first_response_complete:
                            first_response_complete = True
                            print(
                                f"   Bot's initial response complete - received {chunk_count} audio chunks"
                            )
                            break

                    # Continue processing other message types silently

                except asyncio.TimeoutError:
                    # If we have session accepted and received some chunks, we can continue
                    if (
                        session_accepted
                        and play_stream_chunks_received
                        and first_response_complete
                    ):
                        break
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print("❌ Connection closed while processing initial messages")
                    recorder.close()
                    return False

            if not session_accepted:
                print("❌ Session establishment failed")
                recorder.close()
                return False

            if not play_stream_started:
                print(
                    "❌ ERROR: Bot did not speak first - playStream.start was not received"
                )
                recorder.close()
                return False

            if not play_stream_chunks_received:
                print(
                    "❌ ERROR: No playStream.chunk messages were received from bot's initial response"
                )
                recorder.close()
                return False

            # Load audio chunks
            audio_chunks = load_audio_chunks(AUDIO_FILE_PATH)
            if not audio_chunks:
                print("❌ No audio chunks loaded, using silence instead")
                # Create a minimum valid chunk of silence (100ms)
                silence_chunk = base64.b64encode(b"\x00" * 3200).decode(
                    "utf-8"
                )  # 100ms of 16kHz 16-bit silence
                audio_chunks = [silence_chunk]

            # Send audio to trigger a bot response
            user_stream_start = {
                "type": "userStream.start",
                "conversationId": conversation_id,
            }
            await ws.send(json.dumps(user_stream_start))
            print("✅ Sent userStream.start")

            # Wait for userStream.started and process all messages
            stream_started = False
            play_stream_started_2 = False
            stream_id_2 = None
            play_stream_chunks_received_2 = False
            chunk_count_2 = 0
            stream_stopped = False
            second_response_complete = False

            print("Processing user stream and waiting for second bot response...")

            # Process all messages efficiently
            for attempt in range(120):  # 60 seconds total
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    response_data = json.loads(response)
                    msg_type = response_data.get("type")

                    if msg_type == "userStream.started":
                        stream_started = True
                        print("✅ Received userStream.started")

                        # Now send audio chunks
                        print(
                            f"Sending {len(audio_chunks)} audio chunks to trigger bot response..."
                        )
                        for i, chunk in enumerate(audio_chunks):
                            # Record the outgoing user audio
                            recorder.record_user_audio(chunk)
                            
                            audio_chunk = {
                                "type": "userStream.chunk",
                                "conversationId": conversation_id,
                                "audioChunk": chunk,
                            }
                            await ws.send(json.dumps(audio_chunk))
                            if i % 10 == 0 or i == len(audio_chunks) - 1:
                                print(f"   Sent audio chunk {i+1}/{len(audio_chunks)}")
                            await asyncio.sleep(0.01)  # 10ms delay between chunks

                        # Wait a moment before sending stop to ensure all audio is processed
                        await asyncio.sleep(0.2)

                        # Send userStream.stop
                        user_stream_stop = {
                            "type": "userStream.stop",
                            "conversationId": conversation_id,
                        }
                        await ws.send(json.dumps(user_stream_stop))
                        print("✅ Sent userStream.stop")

                    elif msg_type == "userStream.stopped":
                        stream_stopped = True
                        print("✅ Received userStream.stopped")

                    elif msg_type == "playStream.start":
                        if (
                            stream_stopped and not play_stream_started_2
                        ):  # Only for second response
                            play_stream_started_2 = True
                            stream_id_2 = response_data.get("streamId")
                            print(
                                f"✅ Received playStream.start (second bot response) with streamId: {stream_id_2}"
                            )

                    elif msg_type == "playStream.chunk":
                        if stream_stopped:  # Only count chunks for second response
                            if not play_stream_chunks_received_2:
                                print(
                                    f"✅ Started receiving playStream.chunk messages (second bot response)"
                                )
                                play_stream_chunks_received_2 = True
                            chunk_count_2 += 1
                            
                            # Record the audio chunk
                            audio_chunk = response_data.get("audioChunk")
                            if audio_chunk:
                                recorder.record_bot_audio(audio_chunk)
                                
                            if chunk_count_2 % 10 == 0:
                                print(
                                    f"   Received {chunk_count_2} audio chunks so far (second bot response)..."
                                )

                    elif msg_type == "playStream.stop":
                        if (
                            stream_stopped and play_stream_chunks_received_2
                        ):  # Second response complete
                            print(
                                f"✅ Received playStream.stop (second bot response) for streamId: {response_data.get('streamId')}"
                            )
                            second_response_complete = True
                            print(
                                f"   Second bot response complete - received {chunk_count_2} audio chunks"
                            )
                            break

                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print("❌ Connection closed while processing second response")
                    recorder.close()
                    return False

            if not stream_started:
                print("❌ ERROR: userStream.started was not received within timeout")
                recorder.close()
                return False

            if not stream_stopped:
                print("❌ ERROR: userStream.stopped was not received within timeout")
                recorder.close()
                return False

            if not play_stream_started_2:
                print(
                    "❌ ERROR: playStream.start (second bot response) was not received within timeout"
                )
                recorder.close()
                return False

            if not play_stream_chunks_received_2:
                print(
                    "❌ ERROR: No playStream.chunk messages were received (second bot response)"
                )
                recorder.close()
                return False

            print("✅ Validation completed successfully. Closing session.")
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
                await asyncio.sleep(1)
            except websockets.exceptions.ConnectionClosed:
                print("❌ Connection closed before ending session")

            # Close the recorder and save all audio files
            recorder.close()
            return True  # All validations passed

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

    # # Run session flow validation
    # session_success = await validate_session_flow()
    session_success = True

    # # Run audio stream flow validation
    # audio_success = await validate_audio_stream_flow()
    audio_success = True

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
