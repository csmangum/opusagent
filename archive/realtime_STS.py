import base64
import json
import os
import threading
import time
import wave
import argparse

import pyaudio
import websocket
from dotenv import load_dotenv

from archive.realtime_models import (
    AudioBufferAppendEvent,
    InputAudioTranscription,
    SessionConfig,
    SessionUpdateEvent,
    TurnDetection,
)

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY environment variable not found. Check your .env file."
    )

# Audio recording parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000  # OpenAI expects 24kHz for realtime API
CHUNK = 2048  # Reduced from 4096 for faster processing
RECORD = False  # Global flag to control recording

# Response tracking
in_text_response = False
full_response = ""

# Audio player configuration
audio_chunks = []
audio_play_lock = threading.Lock()
audio_playback_active = False
MIN_CHUNKS_FOR_PLAYBACK = 3  # Further reduced for immediate playback
MAX_BUFFER_SIZE = 20  # Further reduced for lower latency
current_response_id = None  # Track current response to prevent mixing

# Debug flags
DEBUG_ALL_EVENTS = False  # Set to False by default
DEBUG_AUDIO = True  # Audio-specific debug info

# WebSocket configuration
MODEL_VERSION = "2025-06-03"  # Default version
url = f"wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-{MODEL_VERSION}"
headers = ["Authorization: Bearer " + OPENAI_API_KEY, "OpenAI-Beta: realtime=v1"]
MAX_RECONNECT_ATTEMPTS = 3
reconnect_count = 0

print(f"⚙️ Using model URL: {url}")


# Convert audio data to base64 encoded PCM16
def audio_to_base64(audio_data):
    return base64.b64encode(audio_data).decode("utf-8")


# Creates a WAV header for raw PCM data
# def create_wav_header(sample_rate=24000, channels=1, sample_width=2):
#     """Create a WAV header for raw PCM data"""
#     buffer = io.BytesIO()
    
#     # Create a wave file with the correct parameters
#     with wave.open(buffer, 'wb') as wf:
#         wf.setnchannels(channels)
#         wf.setsampwidth(sample_width)
#         wf.setframerate(sample_rate)
#         # Don't write any audio data yet
#         wf.writeframes(b'')
    
#     # Get the header (everything before the data)
#     header = buffer.getvalue()
#     # Find where the data chunk starts
#     data_start = header.find(b'data') + 8  # 'data' + 4 bytes for size
#     return header[:data_start]


# Decode base64 audio and add it to playback queue
def play_audio_data(audio_base64, response_id=None):
    global audio_chunks, audio_playback_active, current_response_id
    
    try:
        # If this is a new response, clear the buffer
        if response_id and response_id != current_response_id:
            with audio_play_lock:
                audio_chunks.clear()
            current_response_id = response_id
        
        # Decode base64 audio
        audio_data = base64.b64decode(audio_base64)
        
        # Add to queue with lock
        with audio_play_lock:
            if len(audio_chunks) < MAX_BUFFER_SIZE:
                audio_chunks.append(audio_data)
            else:
                # If buffer is full, remove oldest chunk
                audio_chunks.pop(0)
                audio_chunks.append(audio_data)
        
        # Start playback if not already active and we have enough chunks
        if not audio_playback_active and len(audio_chunks) >= MIN_CHUNKS_FOR_PLAYBACK:
            audio_playback_active = True
            playback_thread = threading.Thread(target=audio_playback_loop)
            playback_thread.daemon = True
            playback_thread.start()
    except Exception as e:
        print(f"❌ Error in play_audio_data: {e}")


def audio_playback_loop():
    global audio_chunks, audio_playback_active
    
    p = pyaudio.PyAudio()
    stream = None
    
    try:
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            frames_per_buffer=CHUNK,
            start=False
        )
        
        stream.start_stream()
        
        while audio_playback_active:
            # Get data from queue with lock
            current_chunks = []
            with audio_play_lock:
                if audio_chunks:
                    # Take all available chunks for maximum speed
                    current_chunks = audio_chunks[:]
                    audio_chunks.clear()
            
            if current_chunks:
                # Combine chunks
                audio_data = b''.join(current_chunks)
                
                try:
                    # Play the audio with no additional buffering
                    stream.write(audio_data, exception_on_underflow=True)
                except Exception as e:
                    print(f"❌ Error writing to audio stream: {e}")
            else:
                # Minimal sleep when no data is available
                time.sleep(0.001)
    except Exception as e:
        print(f"❌ Error in audio playback: {e}")
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        p.terminate()
        audio_playback_active = False


# Audio recording thread function
def record_audio():
    global RECORD
    p = pyaudio.PyAudio()

    try:
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        print("🎤 Microphone activated. Start speaking...")

        while RECORD:
            if ws.sock and ws.sock.connected:
                # Read audio data
                data = stream.read(CHUNK, exception_on_overflow=False)

                # Send audio data to WebSocket
                audio_base64 = audio_to_base64(data)

                # Create and validate the event with Pydantic
                append_event = AudioBufferAppendEvent(audio=audio_base64)
                ws.send(append_event.model_dump_json())
            else:
                time.sleep(0.1)  # Wait a bit if websocket isn't connected

    except Exception as e:
        print(f"❌ Error in audio recording: {e}")
    finally:
        if "stream" in locals() and stream is not None:
            stream.stop_stream()
            stream.close()
        p.terminate()
        print("🎤 Microphone deactivated")


def on_open(ws):
    print("✅ Connected to OpenAI Realtime API")

    # Send session configuration
    print("🔧 Configuring session...")

    try:
        # Create a session configuration with audio prioritized
        session = SessionConfig(
            modalities=["audio", "text"], # Audio first to prioritize it
            voice="alloy",  # Try other voices: echo, fable, onyx, nova, shimmer
            input_audio_format="pcm16",
            output_audio_format="pcm16",  # Explicitly set output format
            instructions="You are a helpful voice assistant. Always respond with both audio and text.",
            input_audio_transcription=InputAudioTranscription(model="whisper-1"),
            turn_detection=TurnDetection(
                type="server_vad",
                threshold=0.7,  # Increased from 0.5 to be less sensitive
                prefix_padding_ms=500,  # Increased from 300ms
                silence_duration_ms=500,  # Increased from 200ms to allow for natural pauses
                create_response=True,
            ),
        )

        # Create and validate the event with Pydantic
        update_event = SessionUpdateEvent(session=session)
        event_json = update_event.model_dump_json()

        # Debug the JSON being sent
        if DEBUG_ALL_EVENTS:
            print(f"📤 Sending session update: {event_json}")

        ws.send(event_json)

        global RECORD
        RECORD = True

        # Start recording in a separate thread
        audio_thread = threading.Thread(target=record_audio)
        audio_thread.daemon = True
        audio_thread.start()
    except Exception as e:
        print(f"❌ Error in on_open: {e}")


def on_message(ws, message):
    global in_text_response, full_response, current_response_id

    try:
        data = json.loads(message)
        event_type = data.get("type", "")
        response_id = data.get("response_id")
        
        # Debug all events if flag is enabled
        if DEBUG_ALL_EVENTS:
            print(f"📥 Event: {event_type}")
            if event_type not in [
                "input_audio_buffer.delta",
                "response.audio_delta",
            ]:
                print(f"📄 {json.dumps(data, indent=2)}")

        if event_type == "response.created":
            # Reset state for new response
            in_text_response = False
            full_response = ""
            current_response_id = response_id
            print("\n🤖 ", end="", flush=True)  # Print robot emoji at start of response
        
        elif event_type == "response.audio.delta":
            # Handle audio response data immediately
            audio_base64 = data.get("delta", '')
            if audio_base64:
                play_audio_data(audio_base64, response_id)
                return  # Process audio immediately and return

        # Process other events
        if event_type == "session.updated":
            print("✅ Session configured successfully")

        elif event_type == "error":
            error_data = data.get("error", {})
            print(f"❌ API Error: {error_data.get('message', 'Unknown error')}")
            print(f"📋 Error details: {json.dumps(error_data, indent=2)}")

        elif event_type == "input_audio_buffer.speech_started":
            print("🔊 Speech detected...")

        elif event_type == "input_audio_buffer.speech_stopped":
            print("🔊 Speech ended, processing...")

        elif event_type == "conversation.item.audio_transcription.completed":
            text = data.get("transcript", "")
            print(f'🗣️ You said: "{text}"')

        elif event_type == "response.audio_transcript.delta":
            # Get the delta text
            delta = data.get("delta", "")
            if delta:
                full_response += delta
                print(f"{delta}", end="", flush=True)
        
        elif event_type == "response.done":
            print("\n")  # New line after response is complete
            in_text_response = False
            
    except Exception as e:
        print(f"❌ Error in on_message: {e}")


def on_error(ws, error):
    print(f"❌ WebSocket Error: {error}")
    # Don't immediately close, let the run_forever loop handle reconnection


def on_close(ws, close_status_code, close_msg):
    global RECORD, audio_playback_active
    RECORD = False
    audio_playback_active = False
    print(f"🔌 Connection closed: {close_status_code} - {close_msg}")
    if close_status_code == 1000:
        print(
            "Normal closure (1000) - This is the standard close code for a normal closure"
        )
    elif close_status_code == 1006:
        print(
            "Abnormal closure (1006) - Connection closed abnormally, possibly a network issue"
        )
    elif close_status_code == 1008:
        print(
            "Policy violation (1008) - Likely an issue with API key or authentication"
        )
    elif close_status_code == 1011:
        print("Internal server error (1011) - Server encountered an error")


def start_connection():
    global ws
    ws = websocket.WebSocketApp(
        url,
        header=headers,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    # Disable detailed WebSocket logs to reduce clutter
    websocket.enableTrace(False)

    # Start the WebSocket connection
    print("🔄 Connecting to OpenAI Realtime API...")
    ws.run_forever()


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='OpenAI Realtime Voice Chat')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--voice', type=str, default='alloy', 
                       choices=['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
                       help='Voice to use for audio responses')
    args = parser.parse_args()
    
    if args.debug:
        DEBUG_ALL_EVENTS = True
        print("🐛 Debug mode enabled")


    print("=" * 50)
    print("🎙️  OpenAI Realtime Voice Chat")
    print("=" * 50)
    print("- Speak into your microphone to interact with the AI")
    print("- Press Ctrl+C to exit")
    print("- Run with --debug flag for verbose logging")
    print(f"- Current voice: {args.voice}")
    print("=" * 50)

    try:
        start_connection()
    except KeyboardInterrupt:
        print("\n👋 Stopping application...")
        RECORD = False
        audio_playback_active = False
