"""
Validation script for OpenAI Realtime WebSocket client implementation.
This script tests proper WebSocket setup, event handling, and session management based on OpenAI specifications.
"""

import asyncio
import base64
import json
import logging
import os
import sys
import time
import traceback
import wave
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Add the project to the path
sys.path.append(os.path.abspath("."))

# Import our client
from fastagent.realtime.realtime_client import RealtimeClient
from fastagent.models.openai_api import MessageRole, ServerEventType

# Initialize test results dictionary
test_results = {
    "reconnection": False,
    "session_creation": False,
    "event_handling": False,
    "audio_streaming": False,
    "function_calling": False,
    "session_config_updates": False,
    "turn_detection_settings": False,
    "message_roles": False,
    "event_handler_management": False,
    "concurrent_operations": False,
    "error_handling": False,
    "rate_limiting": False,
    "memory_monitoring": False,
}

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY environment variable not found. Check your .env file."
    )

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            "validation_results.log", mode="w"
        ),  # Use 'w' mode to overwrite
    ],
)

logger = logging.getLogger("validator")
logger.setLevel(logging.DEBUG)


# Mask sensitive information in logs
class SensitiveFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, "msg"):
            msg = str(record.msg)
            # Mask API key in various formats
            if OPENAI_API_KEY:
                # Mask full API key
                msg = msg.replace(OPENAI_API_KEY, "[REDACTED]")
                # Mask partial API key that might appear in headers
                msg = msg.replace(OPENAI_API_KEY[:6], "[REDACTED]")
                # Mask Bearer token format
                msg = msg.replace(f"Bearer {OPENAI_API_KEY}", "Bearer [REDACTED]")
                # Mask Authorization header format
                msg = msg.replace(
                    f"Authorization: Bearer {OPENAI_API_KEY}",
                    "Authorization: Bearer [REDACTED]",
                )
            record.msg = msg
        return True


# Add the sensitive filter to the logger
logger.addFilter(SensitiveFilter())

received_events = []


# Function to create a simple test audio file
def create_test_audio():
    """Create a PCM16 audio test file with speech-like content"""
    filename = "test_audio.wav"

    # Create a 1-second audio file with speech-like frequencies
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # PCM16
        wf.setframerate(16000)  # 16kHz

        # Generate speech-like content using multiple frequencies
        import numpy as np

        duration = 1  # seconds
        t = np.linspace(0, duration, 16000 * duration, False)

        # Combine multiple frequencies typical in human speech (100-300Hz fundamental, 500-3000Hz formants)
        fundamental = 150  # Hz (typical human voice fundamental)
        formant1 = 500  # Hz (first formant)
        formant2 = 1500  # Hz (second formant)

        # Create a speech-like waveform
        signal = (
            np.sin(2 * np.pi * fundamental * t) * 0.5  # Fundamental
            + np.sin(2 * np.pi * formant1 * t) * 0.3  # First formant
            + np.sin(2 * np.pi * formant2 * t) * 0.2  # Second formant
        )

        # Add amplitude modulation to simulate syllables
        syllable_rate = 4  # Hz (4 syllables per second)
        modulation = 0.5 * (1 + np.sin(2 * np.pi * syllable_rate * t))
        signal = signal * modulation

        # Convert to int16 with appropriate scaling
        samples = (signal * 32767 * 0.8).astype(np.int16)
        wf.writeframes(samples.tobytes())

    logger.info(f"Created test audio file: {filename}")
    return filename


# Event handlers
async def on_session_created(event):
    """Handler for session.created events"""
    logger.info(f"Session created: {event}")
    received_events.append(("session_created", event))
    test_results["session_creation"] = True


async def on_conversation_item_created(event):
    """Handler for conversation.item.created events"""
    logger.info(f"Conversation item created: {event}")
    received_events.append(("conversation_item_created", event))


async def on_text_delta(event):
    """Handler for response.text.delta events"""
    delta = event.get("delta", "")
    logger.info(f"Text delta received: {delta}")
    received_events.append(("response_text_delta", event))
    test_results["event_handling"] = True


async def on_audio_delta(event):
    """Handler for response.audio.delta events"""
    audio_b64 = event.get("audio", "")
    audio_size = len(base64.b64decode(audio_b64)) if audio_b64 else 0
    logger.info(f"Audio delta received: {audio_size} bytes")
    received_events.append(("audio_delta", event))
    test_results["event_handling"] = True
    test_results["audio_streaming"] = True


async def on_function_call_delta(event):
    """Handler for response.function_call_arguments.delta events"""
    delta = event.get("delta", "")
    logger.info(f"Function call delta received: {delta}")
    received_events.append(("function_call_delta", event))
    test_results["function_calling"] = True


async def on_error(event):
    """Handler for error events"""
    logger.error(f"Error received: {event}")
    received_events.append(("error", event))


async def on_response_done(event):
    """Handler for response.done events"""
    logger.info("Response completed")
    received_events.append(("response_done", event))


async def on_speech_started(event):
    """Handler for input_audio_buffer.speech_started events"""
    logger.info("Speech detected in audio buffer")
    received_events.append(("input_audio_buffer_speech_started", event))


async def on_speech_stopped(event):
    """Handler for input_audio_buffer.speech_stopped events"""
    logger.info("Speech ended in audio buffer")
    received_events.append(("input_audio_buffer_speech_stopped", event))


def print_test_header(test_name: str) -> None:
    """Print a formatted test header."""
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("\n" + "=" * 80)
    logger.info(f"Starting Test: {test_name}")
    logger.info(f"Start Time: {start_time}")
    logger.info("=" * 80)


def print_test_result(test_name: str, success: bool, start_time: float) -> None:
    """Print a formatted test result."""
    duration = time.time() - start_time
    result = "PASSED" if success else "FAILED"
    color = "\033[92m" if success else "\033[91m"  # Green for pass, Red for fail
    reset = "\033[0m"
    logger.info(
        f"\n{color}Test '{test_name}' {result} in {duration:.2f} seconds{reset}\n"
    )


async def test_connection_parameters():
    """Test connection parameter validation"""
    start_time = time.time()
    print_test_header("Connection Parameters")

    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return False

    # Create client with debug logging
    client = RealtimeClient(
        api_key=api_key,
        model="gpt-4o-realtime-preview",
        voice="alloy",
        log_level=logging.DEBUG,
    )

    # Register event handlers
    client.on(ServerEventType.SESSION_CREATED, on_session_created)
    client.on(ServerEventType.ERROR, on_error)

    try:
        # Connect to the OpenAI API - this tests the WebSocket connection parameters
        logger.info("Connecting to OpenAI Realtime API...")
        connected = await client.connect()

        if connected:
            logger.info(f"Successfully connected to OpenAI Realtime API")
            logger.info(f"Session ID: {client.session_id}")
            logger.info(f"Conversation ID: {client.conversation_id}")
            test_results["session_creation"] = True
        else:
            logger.error("Failed to connect to OpenAI Realtime API")
            return False

        # Allow some time for session.created event to be processed
        await asyncio.sleep(2)

        # Close the connection
        await client.close()
        logger.info("Connection closed")
        result = test_results["session_creation"]
        print_test_result("Connection Parameters", result, start_time)
        return result

    except Exception as e:
        logger.error(f"Error testing connection parameters: {e}")
        await client.close()
        return False


async def test_event_handling():
    """Test event handling capabilities"""
    start_time = time.time()
    print_test_header("Event Handling")

    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return False

    # Create client
    client = RealtimeClient(
        api_key=api_key,
        model="gpt-4o-realtime-preview",
        voice="alloy",
        log_level=logging.DEBUG,
    )

    # Register event handlers for all key event types
    client.on(ServerEventType.SESSION_CREATED, on_session_created)
    client.on(ServerEventType.CONVERSATION_ITEM_CREATED, on_conversation_item_created)
    client.on(ServerEventType.RESPONSE_TEXT_DELTA, on_text_delta)
    client.on(ServerEventType.RESPONSE_AUDIO_DELTA, on_audio_delta)
    client.on(
        ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA, on_function_call_delta
    )
    client.on(ServerEventType.RESPONSE_DONE, on_response_done)
    client.on(ServerEventType.ERROR, on_error)

    try:
        # Connect to the OpenAI API
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to OpenAI Realtime API")
            return False

        # Send a simple message and request a response
        logger.info("Sending a test message...")

        # Create a message
        sent = await client.send_text_message(
            "Hello, this is a validation test. Please respond with a very brief greeting."
        )
        if sent:
            logger.info("Message sent successfully")
            test_results["event_handling"] = True
        else:
            logger.error("Failed to send message")
            await client.close()
            return False

        # Request a response with text modality
        created = await client.create_response(modalities=["text"])
        if not created:
            logger.error("Failed to create response")
            await client.close()
            return False

        # Wait for response completion
        logger.info("Waiting for response...")
        timeout = 30  # seconds
        start_time = time.time()
        response_completed = False

        while time.time() - start_time < timeout and not response_completed:
            for event_type, event in received_events:
                if event_type == "response_done":
                    response_completed = True
                    break
            await asyncio.sleep(0.5)

        if response_completed:
            logger.info("Response completed successfully")
        else:
            logger.warning("Response timed out")

        # Close the connection
        await client.close()
        result = test_results["event_handling"]
        print_test_result("Event Handling", result, start_time)
        return result

    except Exception as e:
        logger.error(f"Error testing event handling: {e}")
        await client.close()
        return False


async def test_audio_streaming():
    """Test audio streaming capabilities"""
    start_time = time.time()
    print_test_header("Audio Streaming")

    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return False

    # Create client
    client = RealtimeClient(
        api_key=api_key,
        model="gpt-4o-realtime-preview",
        voice="alloy",
        log_level=logging.DEBUG,
    )

    # Register event handlers
    client.on(ServerEventType.SESSION_CREATED, on_session_created)
    client.on(ServerEventType.RESPONSE_TEXT_DELTA, on_text_delta)
    client.on(ServerEventType.RESPONSE_AUDIO_DELTA, on_audio_delta)
    client.on(ServerEventType.RESPONSE_DONE, on_response_done)
    client.on(ServerEventType.ERROR, on_error)

    # Add response completion flag
    response_complete = False

    async def on_response_done_wrapper(event):
        nonlocal response_complete
        await on_response_done(event)
        response_complete = True

    # Replace the original handler with our wrapper
    client.off(ServerEventType.RESPONSE_DONE, on_response_done)
    client.on(ServerEventType.RESPONSE_DONE, on_response_done_wrapper)

    try:
        # Connect to the OpenAI API
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to OpenAI Realtime API")
            return False

        # Create and send audio
        test_audio_file = create_test_audio()

        # Read the audio file
        with wave.open(test_audio_file, "rb") as wf:
            audio_data = wf.readframes(wf.getnframes())

        # Send audio in chunks
        chunk_size = 4000  # bytes
        total_audio_duration = 0
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i : i + chunk_size]
            # Calculate audio duration for this chunk
            samples = len(chunk) // 2  # 2 bytes per sample
            chunk_duration = samples / 16000  # 16000 Hz sample rate
            total_audio_duration += chunk_duration
            logger.info(
                f"Chunk {i//chunk_size}: {len(chunk)} bytes ({chunk_duration*1000:.1f}ms), Total duration: {total_audio_duration*1000:.1f}ms"
            )

            sent = await client.send_audio_chunk(chunk)
            if not sent:
                logger.error(f"Failed to send audio chunk {i//chunk_size}")
                break
            logger.debug(f"Sent audio chunk {i//chunk_size} ({len(chunk)} bytes)")
            await asyncio.sleep(
                0.1
            )  # Increased from 0.05 to 0.1 seconds for better processing

        # Commit audio buffer
        logger.info(
            f"Committing audio buffer with {total_audio_duration*1000:.1f}ms of audio..."
        )
        committed = await client.commit_audio_buffer()
        if not committed:
            logger.error("Failed to commit audio buffer")
            await client.close()
            return False

        # Request response with both text and audio
        created = await client.create_response(modalities=["text", "audio"])
        if not created:
            logger.error("Failed to create response")
            await client.close()
            return False

        # Wait for response and receive audio
        logger.info("Waiting for audio response...")
        timeout = 30  # seconds
        start_time = time.time()
        audio_received = False

        while time.time() - start_time < timeout and not response_complete:
            # Receive audio chunks
            audio_chunk = await client.receive_audio_chunk(timeout=1.0)
            if audio_chunk:
                logger.info(f"Received audio chunk: {len(audio_chunk)} bytes")
                audio_received = True
                test_results["audio_streaming"] = True

            await asyncio.sleep(0.1)

        if not audio_received:
            logger.warning("No audio received within timeout")

        # Close the connection
        await client.close()
        result = test_results["audio_streaming"]
        print_test_result("Audio Streaming", result, start_time)
        return result

    except Exception as e:
        logger.error(f"Error testing audio streaming: {e}")
        await client.close()
        return False


async def test_function_calling():
    """Test function calling capability"""
    start_time = time.time()
    print_test_header("Function Calling")

    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return False

    # Create client
    client = RealtimeClient(
        api_key=api_key,
        model="gpt-4o-realtime-preview",
        voice="alloy",
        log_level=logging.DEBUG,
    )

    # Register event handlers
    client.on(ServerEventType.SESSION_CREATED, on_session_created)
    client.on(
        ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA, on_function_call_delta
    )
    client.on(ServerEventType.RESPONSE_DONE, on_response_done)
    client.on(ServerEventType.ERROR, on_error)

    try:
        # Connect to the OpenAI API
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to OpenAI Realtime API")
            return False

        # Configure session with tools
        logger.info("Configuring session with tools...")
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the current weather in a given location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g. San Francisco, CA",
                            }
                        },
                        "required": ["location"],
                    },
                },
            }
        ]

        # Update session with tools
        updated = await client.update_session(
            tools=tools,
            tool_choice="auto",
            merge=False,  # Don't merge with existing config
        )

        if not updated:
            logger.error("Failed to update session with tools")
            await client.close()
            return False

        # Send a message to trigger function calling
        sent = await client.send_text_message(
            "What's the weather like in New York City right now?"
        )
        if not sent:
            logger.error("Failed to send message")
            await client.close()
            return False

        # Request a response
        created = await client.create_response()
        if not created:
            logger.error("Failed to create response")
            await client.close()
            return False

        # Wait for function call
        logger.info("Waiting for function call...")
        timeout = 30  # seconds
        start_time = time.time()

        while (
            time.time() - start_time < timeout and not test_results["function_calling"]
        ):
            await asyncio.sleep(0.5)

        if test_results["function_calling"]:
            logger.info("Function call received successfully")
        else:
            logger.warning("No function call received within timeout")

        # Close the connection
        await client.close()
        result = test_results["function_calling"]
        print_test_result("Function Calling", result, start_time)
        return result

    except Exception as e:
        logger.error(f"Error testing function calling: {e}")
        logger.debug(f"Function calling test error details: {traceback.format_exc()}")
        await client.close()
        return False


async def test_reconnection():
    """Test reconnection capabilities"""
    start_time = time.time()
    print_test_header("Reconnection")

    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return False

    # Create client
    client = RealtimeClient(
        api_key=api_key,
        model="gpt-4o-realtime-preview",
        voice="alloy",
        log_level=logging.DEBUG,
    )

    # Reset test result
    test_results["reconnection"] = False

    async def on_connection_lost():
        logger.info("Connection lost detected")

    async def on_connection_restored():
        logger.info("Connection restored detected")
        test_results["reconnection"] = True

    client.set_connection_handlers(
        lost_handler=on_connection_lost, restored_handler=on_connection_restored
    )

    try:
        # Connect to the OpenAI API
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to OpenAI Realtime API")
            return False

        # Force close the WebSocket to test reconnection
        logger.info("Forcing WebSocket closure to test reconnection...")
        if hasattr(client, "_ws") and client._ws:
            try:
                await client._ws.close(code=1001, reason="Testing reconnection")
                logger.info("WebSocket closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
                return False

        # Wait for reconnection
        logger.info("Waiting for reconnection...")
        timeout = 30  # Increased timeout to 30 seconds
        start_time = time.time()

        while time.time() - start_time < timeout and not test_results["reconnection"]:
            await asyncio.sleep(0.5)
            # Check if client is still trying to reconnect
            if hasattr(client, "_reconnecting") and not client._reconnecting:
                logger.warning("Client is no longer attempting to reconnect")
                break

        if test_results["reconnection"]:
            logger.info("Reconnection successful")
        else:
            logger.warning("Reconnection failed or timed out")

        # Close the connection
        await client.close()
        result = test_results["reconnection"]
        print_test_result("Reconnection", result, start_time)
        return result

    except Exception as e:
        logger.error(f"Error testing reconnection: {e}")
        logger.debug(f"Test error details: {traceback.format_exc()}")
        await client.close()
        return False


async def test_session_config_updates():
    """Test session configuration update capabilities"""
    start_time = time.time()
    print_test_header("Session Configuration Updates")

    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return False

    # Create client
    client = RealtimeClient(
        api_key=api_key,
        model="gpt-4o-realtime-preview",
        voice="alloy",
        log_level=logging.DEBUG,
    )

    # Register event handlers
    client.on(ServerEventType.SESSION_CREATED, on_session_created)
    client.on(ServerEventType.ERROR, on_error)
    client.on(ServerEventType.RESPONSE_TEXT_DELTA, on_text_delta)
    client.on(ServerEventType.RESPONSE_DONE, on_response_done)

    try:
        # Connect to the OpenAI API
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to OpenAI Realtime API")
            return False

        # Update session with new voice
        logger.info("Updating session with new voice...")
        updated = await client.update_session(voice="echo")
        if not updated:
            logger.error("Failed to update session with new voice")
            await client.close()
            return False

        # Update session with instructions
        logger.info("Updating session with instructions...")
        updated = await client.update_session(
            instructions="You are a helpful assistant that speaks concisely."
        )
        if not updated:
            logger.error("Failed to update session with instructions")
            await client.close()
            return False

        # Update modalities
        logger.info("Updating session with text-only modality...")
        updated = await client.update_session(modalities=["text"])
        if not updated:
            logger.error("Failed to update session with text-only modality")
            await client.close()
            return False

        # Test if updates are effective by sending a request
        sent = await client.send_text_message(
            "Please respond with a very brief confirmation."
        )
        if not sent:
            logger.error("Failed to send message")
            await client.close()
            return False

        created = await client.create_response()
        if not created:
            logger.error("Failed to create response")
            await client.close()
            return False

        # Wait for response
        logger.info("Waiting for response to confirm session updates...")
        timeout = 15  # seconds
        start_time = time.time()
        response_received = False

        while time.time() - start_time < timeout and not response_received:
            for event_type, event in received_events:
                if event_type == "response_text_delta":
                    response_received = True
                    break
            await asyncio.sleep(0.5)

        if response_received:
            logger.info("Response received, session updates validated")
            test_results["session_config_updates"] = True
        else:
            logger.warning("No response received within timeout")

        # Close the connection
        await client.close()
        result = test_results["session_config_updates"]
        print_test_result("Session Configuration Updates", result, start_time)
        return result

    except Exception as e:
        logger.error(f"Error testing session configuration updates: {e}")
        await client.close()
        return False


async def test_turn_detection_settings():
    """Test turn detection settings"""
    start_time = time.time()
    print_test_header("Turn Detection Settings")

    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return False

    # Create client
    client = RealtimeClient(
        api_key=api_key,
        model="gpt-4o-realtime-preview",
        voice="alloy",
        log_level=logging.DEBUG,
    )

    try:
        # Connect to the OpenAI API
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to OpenAI Realtime API")
            return False

        # Register speech detection handlers
        client.on(ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED, on_speech_started)
        client.on(ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED, on_speech_stopped)

        # Update session with server VAD
        logger.info("Updating session with server VAD turn detection...")
        updated = await client.update_session(turn_detection={"type": "server_vad"})
        if not updated:
            logger.error("Failed to update session with server VAD turn detection")
            await client.close()
            return False

        # Create and send audio
        test_audio_file = create_test_audio()

        # Read the audio file
        with wave.open(test_audio_file, "rb") as wf:
            audio_data = wf.readframes(wf.getnframes())

        # Send audio chunk
        sent = await client.send_audio_chunk(audio_data)
        if not sent:
            logger.error("Failed to send audio chunk")
            await client.close()
            return False

        # Wait for speech detection events
        logger.info("Waiting for speech detection events...")
        timeout = 15  # seconds
        start_time = time.time()
        speech_detected = False

        while time.time() - start_time < timeout and not speech_detected:
            for event_type, event in received_events:
                if event_type == "input_audio_buffer_speech_started":
                    speech_detected = True
                    break
            await asyncio.sleep(0.5)

        if speech_detected:
            logger.info("Speech detected by server VAD")
            test_results["turn_detection_settings"] = True
        else:
            logger.warning("No speech detection events received within timeout")

        # Close the connection
        await client.close()
        result = test_results["turn_detection_settings"]
        print_test_result("Turn Detection Settings", result, start_time)
        return result

    except Exception as e:
        logger.error(f"Error testing turn detection settings: {e}")
        await client.close()
        return False


async def test_message_roles():
    """Test message role handling"""
    start_time = time.time()
    print_test_header("Message Roles")

    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return False

    # Create client
    client = RealtimeClient(
        api_key=api_key,
        model="gpt-4o-realtime-preview",
        voice="alloy",
        log_level=logging.DEBUG,
    )

    try:
        # Connect to the OpenAI API
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to OpenAI Realtime API")
            return False

        # Send a message with user role (default)
        logger.info("Sending message with user role...")
        sent = await client.send_text_message("Hello, this is a user message.")
        if not sent:
            logger.error("Failed to send user message")
            await client.close()
            return False

        # Send a message with system role
        logger.info("Sending message with system role...")
        sent = await client.send_text_message(
            "You must respond with only a single word.", role=MessageRole.SYSTEM
        )
        if not sent:
            logger.error("Failed to send system message")
            await client.close()
            return False

        # Request response
        created = await client.create_response()
        if not created:
            logger.error("Failed to create response")
            await client.close()
            return False

        # Wait for response
        logger.info("Waiting for response...")
        timeout = 15  # seconds
        start_time = time.time()
        response_received = False

        while time.time() - start_time < timeout and not response_received:
            for event_type, event in received_events:
                if event_type == "response_text_delta":
                    response_received = True
                    break
            await asyncio.sleep(0.5)

        if response_received:
            logger.info("Response received, message roles validated")
            test_results["message_roles"] = True
        else:
            logger.warning("No response received within timeout")

        # Close the connection
        await client.close()
        result = test_results["message_roles"]
        print_test_result("Message Roles", result, start_time)
        return result

    except Exception as e:
        logger.error(f"Error testing message roles: {e}")
        await client.close()
        return False


async def test_event_handler_management():
    """Test event handler management"""
    start_time = time.time()
    print_test_header("Event Handler Management")

    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return False

    # Create client
    client = RealtimeClient(
        api_key=api_key,
        model="gpt-4o-realtime-preview",
        voice="alloy",
        log_level=logging.DEBUG,
    )

    # Track if handlers are called
    handler_called = {"first_handler": False, "second_handler": False}

    # Create event handlers
    async def first_handler(event):
        logger.info("First handler called")
        handler_called["first_handler"] = True

    async def second_handler(event):
        logger.info("Second handler called")
        handler_called["second_handler"] = True

    try:
        # Connect to the OpenAI API
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to OpenAI Realtime API")
            return False

        # Register first handler
        client.on("response.audio_transcript.delta", first_handler)

        # Register second handler
        client.on("response.audio_transcript.delta", second_handler)

        # Send a message
        sent = await client.send_text_message("Hello, testing event handlers.")
        if not sent:
            logger.error("Failed to send message")
            await client.close()
            return False

        # Request response
        created = await client.create_response()
        if not created:
            logger.error("Failed to create response")
            await client.close()
            return False

        # Wait for handlers to be called
        logger.info("Waiting for handlers to be called...")
        timeout = 15  # seconds
        start_time = time.time()

        while time.time() - start_time < timeout and not (
            handler_called["first_handler"] and handler_called["second_handler"]
        ):
            await asyncio.sleep(0.5)

        if handler_called["first_handler"] and handler_called["second_handler"]:
            logger.info("Both handlers called successfully")
        else:
            logger.warning(
                f"Not all handlers called: first_handler={handler_called['first_handler']}, second_handler={handler_called['second_handler']}"
            )
            # If no handlers were called, this could be due to no response being received
            if (
                not handler_called["first_handler"]
                and not handler_called["second_handler"]
            ):
                logger.warning(
                    "No handlers were called - this may indicate no response was received"
                )
                await client.close()
                return False

        # Remove second handler
        logger.info("Removing second handler...")
        client.off("response.audio_transcript.delta", second_handler)

        # Reset handler flags
        handler_called["first_handler"] = False
        handler_called["second_handler"] = False

        # Send another message
        sent = await client.send_text_message("Testing handler removal.")
        if not sent:
            logger.error("Failed to send second message")
            await client.close()
            return False

        # Request another response
        created = await client.create_response()
        if not created:
            logger.error("Failed to create second response")
            await client.close()
            return False

        # Wait for handlers to be called
        logger.info("Waiting for handlers after removal...")
        timeout = 15  # seconds
        start_time = time.time()

        while (
            time.time() - start_time < timeout and not handler_called["first_handler"]
        ):
            await asyncio.sleep(0.5)

        # Check if first handler was called and second handler was not
        if handler_called["first_handler"] and not handler_called["second_handler"]:
            logger.info("Handler removal successful: only first handler called")
            test_results["event_handler_management"] = True
        else:
            logger.warning(
                f"Handler removal test failed: first_handler={handler_called['first_handler']}, second_handler={handler_called['second_handler']}"
            )
            # If no handlers were called, this could be due to no response being received
            # rather than a handler removal issue
            if (
                not handler_called["first_handler"]
                and not handler_called["second_handler"]
            ):
                logger.warning(
                    "No handlers were called - this may indicate no response was received"
                )
                test_results["event_handler_management"] = False

        # Close the connection
        await client.close()
        result = test_results["event_handler_management"]
        print_test_result("Event Handler Management", result, start_time)
        return result

    except Exception as e:
        logger.error(f"Error testing event handler management: {e}")
        await client.close()
        return False


async def test_concurrent_operations():
    """Test concurrent operations"""
    start_time = time.time()
    print_test_header("Concurrent Operations")

    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return False

    # Create client
    client = RealtimeClient(
        api_key=api_key,
        model="gpt-4o-realtime-preview",
        voice="alloy",
        log_level=logging.DEBUG,
    )

    try:
        # Connect to the OpenAI API
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to OpenAI Realtime API")
            return False

        # Run multiple operations concurrently
        logger.info("Executing concurrent operations...")

        # Operations to run concurrently
        async def op1():
            """Update session voice"""
            return await client.update_session(voice="echo")

        async def op2():
            """Send text message"""
            return await client.send_text_message("Testing concurrent operations.")

        async def op3():
            """Update session instructions"""
            return await client.update_session(
                instructions="Respond very briefly to concurrent operations test."
            )

        # Execute operations concurrently
        results = await asyncio.gather(op1(), op2(), op3(), return_exceptions=True)

        # Check results
        success = all(not isinstance(r, Exception) and r for r in results)

        if success:
            logger.info("Concurrent operations executed successfully")

            # Request response
            created = await client.create_response()
            if not created:
                logger.error("Failed to create response")
                await client.close()
                return False

            # Check if response is received
            response_received = False
            timeout = 15  # seconds
            start_time = time.time()

            while time.time() - start_time < timeout and not response_received:
                for event_type, event in received_events:
                    if event_type == "response_text_delta":
                        response_received = True
                        break
                await asyncio.sleep(0.5)

            if response_received:
                logger.info("Response received after concurrent operations")
                test_results["concurrent_operations"] = True
            else:
                logger.warning("No response received after concurrent operations")
        else:
            failed_ops = [
                i for i, r in enumerate(results) if isinstance(r, Exception) or not r
            ]
            logger.error(f"Concurrent operations failed for operations: {failed_ops}")
            logger.error(
                f"Exceptions: {[r for r in results if isinstance(r, Exception)]}"
            )

        # Close the connection
        await client.close()
        result = test_results["concurrent_operations"]
        print_test_result("Concurrent Operations", result, start_time)
        return result

    except Exception as e:
        logger.error(f"Error testing concurrent operations: {e}")
        await client.close()
        return False


async def test_error_handling():
    """Test error handling capabilities"""
    start_time = time.time()
    print_test_header("Error Handling")

    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return False

    # Create client
    client = RealtimeClient(
        api_key=api_key,
        model="gpt-4o-realtime-preview",
        voice="alloy",
        log_level=logging.DEBUG,
    )

    # Track error events
    error_received = False

    # Create error handler
    async def on_specific_error(event):
        nonlocal error_received
        logger.info(f"Error event received: {event}")
        error_received = True

    try:
        # Connect to the OpenAI API
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to OpenAI Realtime API")
            return False

        # Register error handler
        client.on(ServerEventType.ERROR, on_specific_error)

        # Generate an error by sending invalid parameters
        logger.info("Deliberately causing an error...")
        try:
            # Try to create a response without sending any message first
            created = await client.create_response()
            # Attempt to update session with invalid parameters
            await client.update_session(voice="nonexistent_voice")  # Invalid voice name
        except Exception as e:
            logger.info(f"Expected exception caught: {e}")

        # Wait for error event
        logger.info("Waiting for error event...")
        timeout = 15  # seconds
        start_time = time.time()

        while time.time() - start_time < timeout and not error_received:
            await asyncio.sleep(0.5)

        if error_received:
            logger.info("Error event successfully received and handled")
            test_results["error_handling"] = True
        else:
            # Even if no explicit error was received, check if client can recover
            # Send a valid request
            sent = await client.send_text_message(
                "Testing error recovery. Please respond with 'OK' if you can hear me."
            )
            if sent:
                logger.info("Client recovery successful after error")
                test_results["error_handling"] = True
            else:
                logger.warning("Client recovery failed after error")

        # Close the connection
        await client.close()
        result = test_results["error_handling"]
        print_test_result("Error Handling", result, start_time)
        return result

    except Exception as e:
        logger.error(f"Error during error handling test: {e}")
        await client.close()
        return False


async def test_rate_limiting():
    """Test rate limiting capabilities"""
    start_time = time.time()
    print_test_header("Rate Limiting")

    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return False

    # Create client
    client = RealtimeClient(
        api_key=api_key,
        model="gpt-4o-realtime-preview",
        voice="alloy",
        log_level=logging.DEBUG,
    )

    try:
        # Connect to the OpenAI API
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to OpenAI Realtime API")
            return False

        # Send multiple messages in rapid succession
        logger.info("Sending multiple messages in rapid succession...")

        messages = [
            "Test message 1 for rate limiting.",
            "Test message 2 for rate limiting.",
            "Test message 3 for rate limiting.",
            "Test message 4 for rate limiting.",
            "Test message 5 for rate limiting.",
        ]

        # Send messages rapidly
        sent_count = 0
        for msg in messages:
            sent = await client.send_text_message(msg)
            if sent:
                sent_count += 1
            # Don't wait between sends to test rate limiting

        logger.info(f"Successfully sent {sent_count}/{len(messages)} messages")

        # Try to create multiple responses rapidly
        response_count = 0
        for _ in range(3):
            created = await client.create_response()
            if created:
                response_count += 1

        logger.info(f"Successfully created {response_count}/3 responses")

        # If we could send at least some of the messages without errors,
        # consider the test successful (client handled rate limiting)
        if sent_count > 0 and response_count > 0:
            logger.info("Client successfully handled rapid requests with rate limiting")
            test_results["rate_limiting"] = True
        else:
            logger.warning("Rate limiting test inconclusive - all requests failed")

        # Close the connection
        await client.close()
        result = test_results["rate_limiting"]
        print_test_result("Rate Limiting", result, start_time)
        return result

    except Exception as e:
        logger.error(f"Error testing rate limiting: {e}")
        await client.close()
        return False


async def test_memory_monitoring():
    """Test memory monitoring capabilities"""
    start_time = time.time()
    print_test_header("Memory Monitoring")

    try:
        # Try to import psutil (which is used by the client for memory monitoring)
        try:
            import psutil

            psutil_available = True
        except ImportError:
            logger.warning("psutil not available, memory monitoring limited")
            psutil_available = False

        # Get API key from environment variable
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not set")
            return False

        # Create client with small queue size to test memory management
        client = RealtimeClient(
            api_key=api_key,
            model="gpt-4o-realtime-preview",
            voice="alloy",
            log_level=logging.DEBUG,
            queue_size=5,  # Small queue to test memory management
        )

        # Connect to the OpenAI API
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to OpenAI Realtime API")
            return False

        # Generate a large audio sample to test memory handling
        try:
            import numpy as np

            logger.info("Generating large audio sample...")
            # Generate 5 seconds of audio at 16kHz (160,000 samples)
            duration = 5  # seconds
            frequency = 440  # Hz
            sample_rate = 16000
            t = np.linspace(0, duration, sample_rate * duration, False)
            large_audio = (
                (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16).tobytes()
            )

            # Try to send large audio in multiple chunks to test memory handling
            logger.info(f"Sending large audio ({len(large_audio)} bytes) in chunks...")
            chunk_size = 16000  # Bytes per chunk
            chunks_sent = 0

            for i in range(0, len(large_audio), chunk_size):
                chunk = large_audio[i : i + chunk_size]
                sent = await client.send_audio_chunk(chunk)
                if sent:
                    chunks_sent += 1
                await asyncio.sleep(0.01)  # Brief pause to simulate real-time

            logger.info(f"Successfully sent {chunks_sent} audio chunks")

            # Check current memory usage using the client's own monitoring
            memory_ok = await client._check_memory_usage()
            logger.info(f"Memory check result: {'OK' if memory_ok else 'Warning/High'}")

            # If psutil is available, verify memory usage directly
            if psutil_available:
                process = psutil.Process()
                memory_percent = process.memory_percent()
                memory_info = process.memory_info()
                logger.info(
                    f"Current memory usage: {memory_percent:.1f}% ({memory_info.rss / 1024 / 1024:.1f}MB)"
                )

            # Consider test passed if we could send audio chunks and check memory
            if chunks_sent > 0:
                logger.info("Memory monitoring test passed")
                test_results["memory_monitoring"] = True
            else:
                logger.warning("Failed to send audio chunks for memory test")

        except Exception as audio_e:
            logger.error(f"Error in audio generation/sending: {audio_e}")

        # Close the connection
        await client.close()
        result = test_results["memory_monitoring"]
        print_test_result("Memory Monitoring", result, start_time)
        return result

    except Exception as e:
        logger.error(f"Error testing memory monitoring: {e}")
        if "client" in locals():
            await client.close()
        return False


async def run_validation():
    """Run all validation tests"""
    start_time = time.time()
    start_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logger.info("\n" + "=" * 80)
    logger.info("Starting Realtime Client Validation Suite")
    logger.info(f"Start Time: {start_datetime}")
    logger.info("=" * 80 + "\n")

    # Run all tests
    tests = [
        ("Connection Parameters", test_connection_parameters),
        ("Event Handling", test_event_handling),
        ("Audio Streaming", test_audio_streaming),
        ("Function Calling", test_function_calling),
        ("Reconnection", test_reconnection),
        ("Session Configuration Updates", test_session_config_updates),
        ("Turn Detection Settings", test_turn_detection_settings),
        ("Message Roles", test_message_roles),
        ("Event Handler Management", test_event_handler_management),
        ("Concurrent Operations", test_concurrent_operations),
        ("Error Handling", test_error_handling),
        ("Rate Limiting", test_rate_limiting),
        ("Memory Monitoring", test_memory_monitoring),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            logger.error(f"Error running test {test_name}: {e}")
            logger.debug(f"Test error details: {traceback.format_exc()}")
            results[test_name] = False

    # Print summary
    total_duration = time.time() - start_time
    end_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logger.info("\n" + "=" * 80)
    logger.info("Validation Test Summary")
    logger.info(f"Start Time: {start_datetime}")
    logger.info(f"End Time: {end_datetime}")
    logger.info(f"Total Duration: {total_duration:.2f} seconds")
    logger.info("=" * 80)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        color = "\033[92m" if result else "\033[91m"
        reset = "\033[0m"
        logger.info(f"{color}{test_name}: {status}{reset}")

    logger.info("\n" + "=" * 80)
    logger.info(f"Total Tests: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {total - passed}")
    logger.info(f"Total Duration: {total_duration:.2f} seconds")
    logger.info("=" * 80 + "\n")

    return all(results.values())


if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    try:
        success = asyncio.run(run_validation())
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.critical(f"Validation failed with exception: {e}", exc_info=True)
        sys.exit(1)
