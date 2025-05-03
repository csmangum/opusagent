import base64
import json
import os
import threading
import time
import wave

import numpy as np
import pyaudio
import websocket
from dotenv import load_dotenv

from archive.realtime_models import (
    AudioBufferAppendEvent,
    InputAudioTranscription,
    ResponseCreateEvent,
    ResponseCreateOptions,
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
CHUNK = 1024
RECORD = False  # Global flag to control recording

# Response tracking
in_text_response = False
full_response = ""

# WebSocket configuration
# Try different model versions if one doesn't work
MODEL_VERSION = "2024-12-17"  # Default version
url = f"wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-{MODEL_VERSION}"
headers = ["Authorization: Bearer " + OPENAI_API_KEY, "OpenAI-Beta: realtime=v1"]

print(f"⚙️ Using model URL: {url}")


# Convert audio data to base64 encoded PCM16
def audio_to_base64(audio_data):
    return base64.b64encode(audio_data).decode("utf-8")


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
        # Create a session configuration that matches the original working configuration
        session = SessionConfig(
            modalities=["audio", "text"],
            voice="alloy",
            input_audio_format="pcm16",
            instructions="You are a helpful voice assistant.",  # Provide instructions (required)
            input_audio_transcription=InputAudioTranscription(model="whisper-1"),
            turn_detection=TurnDetection(
                type="server_vad",
                threshold=0.5,
                prefix_padding_ms=300,
                silence_duration_ms=200,
                create_response=True,
            ),
        )

        # Create and validate the event with Pydantic
        update_event = SessionUpdateEvent(session=session)
        event_json = update_event.model_dump_json()

        # Debug the JSON being sent
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
    global in_text_response, full_response

    try:
        data = json.loads(message)
        event_type = data.get("type", "")

        # Only log important events to reduce console spam
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

        elif event_type == "response.created":
            # Reset state for new response
            in_text_response = False
            full_response = ""

        elif event_type == "response.audio_transcript.delta":
            # Get the delta text, but don't strip whitespace
            delta = data.get("delta", "")

            if delta:
                # Add to full response
                full_response += delta

                if not in_text_response:
                    # Print robot emoji only at the beginning of a response
                    print("\n🤖 ", end="", flush=True)
                    in_text_response = True

                # Print the delta with proper spacing
                print(f"{delta}", end="", flush=True)

        elif event_type == "response.done":
            # Reset response state
            in_text_response = False

            # Clean up the display with proper spacing
            if full_response:
                # Optionally format the full response nicely - uncomment if needed
                # formatted_response = full_response.replace(".", ". ").replace("!", "! ").replace("?", "? ")
                # print(f"\n🤖 {formatted_response}")
                pass

            print("\n✅ Response completed")
    except Exception as e:
        print(f"❌ Error in on_message: {e}")


def on_error(ws, error):
    print(f"❌ WebSocket Error: {error}")


def on_close(ws, close_status_code, close_msg):
    global RECORD
    RECORD = False
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


def create_manual_response():
    """Manually create a response (for testing purposes)"""
    response_options = ResponseCreateOptions(
        modalities=["text", "audio"],
        voice="alloy",
        instructions="Respond in a friendly and helpful manner",
    )

    response_event = ResponseCreateEvent(response=response_options)
    return response_event.model_dump_json()


if __name__ == "__main__":
    # Check for PyAudio
    try:
        p = pyaudio.PyAudio()
        p.terminate()
    except:
        print("❌ Error: PyAudio not installed or microphone not available")
        print("Install with: pip install pyaudio")
        exit(1)

    print("=" * 50)
    print("🎙️  OpenAI Realtime Voice Chat")
    print("=" * 50)
    print("- Speak into your microphone to interact with the AI")
    print("- Press Ctrl+C to exit")
    print("=" * 50)

    try:
        start_connection()
    except KeyboardInterrupt:
        print("\n👋 Stopping application...")
        RECORD = False
