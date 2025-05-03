import asyncio
import base64
import json
import os
import wave

import numpy as np
import websockets
from dotenv import load_dotenv
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    NegotiationError,
)

load_dotenv()

# Configuration
SERVER_URL = "ws://localhost:6060/media-stream"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_WS_URL = (
    "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
)


# Generate a simple G.711 µ-law audio sample
def generate_ulaw_audio():
    # Create a simple sine wave
    sample_rate = 8000
    duration = 0.1  # 100ms
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    sine_wave = np.sin(2 * np.pi * 440 * t) * 0.5  # 440Hz tone at 50% volume

    # Convert to µ-law
    ulaw_wave = (
        np.sign(sine_wave) * np.log(1 + 255 * np.abs(sine_wave)) / np.log(1 + 255)
    )
    ulaw_wave = np.round(ulaw_wave * 127 + 128).astype(np.uint8)

    return ulaw_wave.tobytes()


TEST_AUDIO = base64.b64encode(generate_ulaw_audio()).decode("utf-8")


async def validate_openai_connection():
    """Validate the OpenAI realtime API connection."""
    try:
        print("\nValidating OpenAI realtime API connection...")
        async with websockets.connect(
            OPENAI_WS_URL,
            subprotocols=["realtime"],
            additional_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1",
            },
        ) as websocket:
            print("Successfully connected to OpenAI realtime API")

            # Send session update
            session_update = {
                "type": "session.update",
                "session": {
                    "turn_detection": {"type": "server_vad"},
                    "input_audio_format": "g711_ulaw",
                    "output_audio_format": "g711_ulaw",
                    "voice": "alloy",
                    "instructions": "You are a helpful AI assistant.",
                    "modalities": ["text", "audio"],
                },
            }
            await websocket.send(json.dumps(session_update))
            print("Sent session update")

            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            print("Received OpenAI response:", response)

            await websocket.close()
            print("OpenAI connection closed gracefully")

    except Exception as e:
        print(f"Error validating OpenAI connection: {str(e)}")
        import traceback

        print("Full traceback:")
        print(traceback.format_exc())


async def validate_websocket():
    """Validate the WebSocket endpoint by simulating Twilio messages."""
    try:
        print("\nAttempting to connect to WebSocket server...")
        async with websockets.connect(
            SERVER_URL,
            subprotocols=["binary"],
            ping_interval=5,
            ping_timeout=5,
        ) as websocket:
            print("Successfully connected to WebSocket server")
            print(f"Selected subprotocol: {websocket.subprotocol}")

            # Test 1: Send start event
            start_event = {
                "event": "start",
                "start": {
                    "streamSid": "test_stream_sid",
                    "accountSid": "test_account_sid",
                    "callSid": "test_call_sid",
                },
            }
            print("Sending start event:", json.dumps(start_event))
            await websocket.send(json.dumps(start_event))
            print("Start event sent successfully")

            # Test 2: Send media event with G.711 µ-law audio
            media_event = {"event": "media", "media": {"payload": TEST_AUDIO}}
            print("Sending media event with G.711 µ-law audio")
            await websocket.send(json.dumps(media_event))
            print("Media event sent successfully")

            # Test 3: Wait for response
            try:
                print("Waiting for response...")
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                print("Received response:", response)

                # Verify response format
                response_data = json.loads(response)
                if "event" in response_data and "media" in response_data:
                    print("Response format is valid")
                    if "payload" in response_data["media"]:
                        print("Response contains audio payload")
                else:
                    print("Warning: Response format is unexpected")

            except asyncio.TimeoutError:
                print("No response received within timeout period")

            # Test 4: Send stop event
            stop_event = {"event": "stop", "stop": {"streamSid": "test_stream_sid"}}
            print("Sending stop event")
            await websocket.send(json.dumps(stop_event))
            print("Stop event sent successfully")

            # Wait for graceful closure
            try:
                await websocket.close()
                print("WebSocket connection closed gracefully")
            except Exception as e:
                print(f"Error during WebSocket closure: {str(e)}")

    except ConnectionRefusedError:
        print(
            "Error: Could not connect to WebSocket server. Make sure the server is running."
        )
    except NegotiationError as e:
        print(f"Error: WebSocket subprotocol negotiation failed: {str(e)}")
    except ConnectionClosed as e:
        print(
            f"Error: WebSocket connection was closed unexpectedly. Code: {e.code}, Reason: {e.reason}"
        )
    except Exception as e:
        print(f"Error during validation: {str(e)}")
        import traceback

        print("Full traceback:")
        print(traceback.format_exc())


async def run_tests():
    """Run multiple test iterations to ensure stability."""
    print("Starting WebSocket validation tests...")

    # First validate OpenAI connection
    await validate_openai_connection()

    # Then validate local server
    for i in range(3):  # Run 3 test iterations
        print(f"\nTest iteration {i + 1}")
        await validate_websocket()
        await asyncio.sleep(1)  # Wait between tests


if __name__ == "__main__":
    asyncio.run(run_tests())
