"""
FastAPI server for AudioCodes VoiceAI Connect real-time voice agent integration.

This module initializes and configures the FastAPI application that serves as
the webhook endpoint for AudioCodes VoiceAI Connect Enterprise platform. It
implements the WebSocket protocol defined by the AudioCodes Bot API to enable
real-time voice interactions between users and AI voice agents.

The server handles incoming WebSocket connections, routes messages to appropriate
handlers, and maintains conversation state throughout the call session.
"""

import asyncio
import os
from pathlib import Path

import dotenv
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket

from fastagent.config.logging_config import configure_logging
from fastagent.telephony_realtime_bridge import (
    TelephonyRealtimeBridge,
    initialize_session,
)

load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Load environment variables from .env file if it exists
env_path = Path(".") / ".env"
if env_path.exists():
    dotenv.load_dotenv(env_path)

# Configure logging
logger = configure_logging("main")
# Get configuration from environment variables
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

# Create FastAPI application
app = FastAPI(
    title="Real-Time Voice Agent",
    description="Integration between AudioCodes VoiceAI Connect and OpenAI Realtime API",
    version="1.0.0",
)


@app.websocket("/voice-bot")
async def handle_call(telephony_websocket: WebSocket):
    """Handle WebSocket connections between telephony provider and OpenAI."""
    client_address = telephony_websocket.client
    logger.info(f"------ Incoming telephony connection from {client_address} ------")
    await telephony_websocket.accept()
    logger.info(f"------ Telephony connection accepted from {client_address} ------")

    try:
        logger.info("Attempting to connect to OpenAI Realtime API...")
        
        async with websockets.connect(
            "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01",
            subprotocols=["realtime"],
            additional_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1",
            },
            ping_interval=5,
            ping_timeout=20,
            close_timeout=10,
        ) as realtime_websocket:
            logger.info("OpenAI WebSocket connection established")
            bridge = TelephonyRealtimeBridge(telephony_websocket, realtime_websocket)
            logger.info("Telephony-Realtime bridge created")
            
            try:
                logger.info("Initializing realtime-websocket session...")
                await initialize_session(realtime_websocket)
                logger.info("realtime-websocket session initialized")
            except Exception as e:
                logger.error(f"Error initializing realtime-websocket session: {e}")
                raise

            # Run both tasks and handle cleanup
            try:
                logger.info("Starting bridge tasks...")
                await asyncio.gather(
                    bridge.receive_from_telephony(), bridge.receive_from_realtime()
                )
            except Exception as e:
                logger.error(f"Error in main connection loop: {e}")
                raise
            finally:
                logger.info("Closing bridge...")
                await bridge.close()
    except websockets.exceptions.InvalidStatusCode as e:
        logger.error(f"Invalid status code from OpenAI: {e}")
        logger.error(f"Response headers: {e.response_headers}")
        await telephony_websocket.close()
    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"OpenAI connection closed: {e}")
        logger.error(f"Close code: {e.code}")
        logger.error(f"Close reason: {e.reason}")
        await telephony_websocket.close()
    except Exception as e:
        logger.error(f"Error establishing OpenAI connection: {e}")
        await telephony_websocket.close()


@app.get("/")
async def root():
    """Root endpoint to display basic information about the API.

    Returns:
        dict: Basic information about the API and its purpose.
    """
    return {
        "name": "Real-Time Voice Agent",
        "description": "Integration between AudioCodes VoiceAI Connect and OpenAI Realtime API",
        "version": "1.0.0",
        "endpoints": {
            "/ws": "WebSocket endpoint for AudioCodes VoiceAI Connect",
        },
    }


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on http://{HOST}:{PORT}")
    # Configure uvicorn with low buffer sizes for minimal latency
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        # Low write buffer size to minimize buffering and reduce latency
        # This ensures WebSocket messages are sent as soon as possible
        websocket_ping_interval=5,  # More frequent pings to keep connections alive
        websocket_max_size=16777216,  # 16MB - large enough for audio chunks
        websocket_ping_timeout=20,  # Timeout for pings to detect dead connections
        # Use HTTP/1.1 for lower overhead than HTTP/2
        http="h11",
    )
