import websocket
import json
import base64
import numpy as np
import logging
import time
import threading
import pyaudio
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# WebSocket server URL (adjust if FastAPI server is hosted elsewhere)
WEBSOCKET_URL = "ws://localhost:8000/audiocodes"

# Audio parameters for microphone input
SAMPLE_RATE = 16000  # 16kHz, common for telephony
CHUNK_SIZE = 1600  # 100ms chunks at 16kHz
CHANNELS = 1  # Mono audio
FORMAT = pyaudio.paInt16  # 16-bit PCM
AUDIO_FORMAT = "raw/lpcm16"  # Matches bridge expectation

class AudioCodesTestClient:
    """
    A test client to capture audio from microphone and send to the FastAPI WebSocket endpoint.

    This client:
    1. Connects to the FastAPI WebSocket endpoint.
    2. Captures audio from microphone in real-time and sends as base64-encoded JSON.
    3. Receives and logs response audio chunks from the OpenAI Realtime API via the endpoint.
    4. Handles connection lifecycle and errors.

    Attributes:
        ws: WebSocket connection object.
        running: Flag to control the audio sending loop.
        connected: Flag to track the connection state.
        pyaudio: PyAudio instance for microphone input.
        stream: Audio stream for microphone input.
    """
    def __init__(self):
        self.ws: Optional[websocket.WebSocketApp] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.connected = False
        self.pyaudio = pyaudio.PyAudio()
        self.stream = None

    def on_open(self, ws: websocket.WebSocketApp):
        """Called when WebSocket connection is established."""
        logger.info("WebSocket connection opened")
        self.connected = True
        self.running = True
        # Start sending audio chunks in a separate thread
        self.thread = threading.Thread(target=self.send_audio_chunks)
        self.thread.start()

    def on_message(self, ws: websocket.WebSocketApp, message: str):
        """Called when a message is received from the WebSocket server."""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            stream_id = data.get("streamId")

            if message_type == "playStream.start":
                logger.info(f"Received playStream.start for streamId: {stream_id}")
            elif message_type == "playStream.chunk":
                audio_chunk = data.get("audioChunk")
                logger.info(f"Received playStream.chunk for streamId: {stream_id}, chunk size: {len(audio_chunk)}")
            elif message_type == "playStream.stop":
                logger.info(f"Received playStream.stop for streamId: {stream_id}")
                self.running = False  # Stop sending audio
            else:
                logger.warning(f"Unknown message type: {message_type}")
        except json.JSONDecodeError:
            logger.error("Failed to parse message as JSON")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

    def on_error(self, ws: websocket.WebSocketApp, error: Exception):
        """Called when a WebSocket error occurs."""
        logger.error(f"WebSocket error: {str(error)}")
        self.running = False

    def on_close(self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str):
        """Called when the WebSocket connection is closed."""
        logger.info(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        self.running = False

    def send_audio_chunks(self):
        """Send audio chunks from microphone to the WebSocket server while running."""
        try:
            # Open microphone stream
            self.stream = self.pyaudio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            logger.info("Microphone stream opened")

            # Wait a short time before starting to send chunks
            time.sleep(0.5)
            
            while self.running and self.connected:
                try:
                    # Read audio data from microphone
                    audio_data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    
                    # Create message
                    message = {
                        "type": "audioChunk",
                        "audioChunk": base64.b64encode(audio_data).decode("utf-8"),
                        "format": AUDIO_FORMAT
                    }
                    
                    # Send message
                    if self.ws and self.ws.sock and self.ws.sock.connected:
                        self.ws.send(json.dumps(message))
                        logger.debug(f"Sent audio chunk of size {len(audio_data)} bytes")
                    else:
                        logger.error("WebSocket connection lost while sending chunks")
                        break
                        
                except Exception as e:
                    logger.error(f"Error sending audio chunk: {str(e)}")
                    break

            # Clean up microphone stream
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                logger.info("Microphone stream closed")

        except Exception as e:
            logger.error(f"Error in audio sending loop: {str(e)}")
            self.running = False

    def connect(self):
        """Establish WebSocket connection and start the client."""
        try:
            # Enable trace for debugging
            websocket.enableTrace(True)
            
            self.ws = websocket.WebSocketApp(
                WEBSOCKET_URL,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            # Run WebSocket in a separate thread to handle async events
            self.thread = threading.Thread(
                target=self.ws.run_forever,
                kwargs={
                    "ping_interval": 5,  # More frequent pings
                    "ping_timeout": 3,   # Shorter timeout
                    "sslopt": {"cert_reqs": False}  # Disable SSL verification for local testing
                }
            )
            self.thread.daemon = True
            self.thread.start()
            logger.info(f"Connecting to WebSocket server at {WEBSOCKET_URL}")
            
            # Wait for connection to be established
            connection_timeout = 10  # Wait up to 10 seconds for connection
            start_time = time.time()
            while not self.connected and time.time() - start_time < connection_timeout:
                time.sleep(0.1)
            
            if not self.connected:
                logger.error(f"Failed to establish WebSocket connection after {connection_timeout} seconds")
                self.stop()
                return
                
            logger.info("WebSocket connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket server: {str(e)}")
            self.running = False

    def stop(self):
        """Stop the client and close the WebSocket connection."""
        self.running = False
        self.connected = False
        
        # Stop and close microphone stream
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error closing microphone stream: {str(e)}")
        
        # Close PyAudio
        try:
            self.pyaudio.terminate()
        except Exception as e:
            logger.error(f"Error terminating PyAudio: {str(e)}")
        
        # Close WebSocket
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {str(e)}")
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        logger.info("Test client stopped")

def main():
    """Run the test client."""
    client = AudioCodesTestClient()
    try:
        client.connect()
        # Run until stopped
        while client.running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    finally:
        client.stop()

if __name__ == "__main__":
    main()