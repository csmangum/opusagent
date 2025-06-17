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
import base64
import json
import logging
import os
import sys
import wave
from pathlib import Path
from typing import Optional

import dotenv
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse

from opusagent.bridges.audiocodes_bridge import AudioCodesBridge
from opusagent.bridges.twilio_bridge import TwilioBridge
from opusagent.config.logging_config import configure_logging
from opusagent.session_manager import SessionManager
from opusagent.websocket_config import WebSocketConfig
from opusagent.websocket_manager import websocket_manager

load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERVER_URL = "wss://grand-collie-complete.ngrok-free.app/twilio-agent"
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.websocket("/ws/telephony")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for handling telephony connections.

    This endpoint establishes a WebSocket connection with the telephony client
    and creates a bridge to the OpenAI Realtime API using the WebSocket manager.

    Args:
        websocket (WebSocket): The WebSocket connection from the telephony client
    """
    await websocket.accept()
    logger.info("Telephony WebSocket connection accepted")

    try:
        # Get a managed connection to OpenAI Realtime API
        async with websocket_manager.connection_context() as connection:
            logger.info(f"Using OpenAI connection: {connection.connection_id}")

            # Create AudioCodes bridge instance
            bridge = AudioCodesBridge(websocket, connection.websocket)

            # Start receiving from both WebSockets
            await asyncio.gather(
                bridge.receive_from_platform(),
                bridge.receive_from_realtime(),
            )

    except WebSocketDisconnect:
        logger.info("Telephony client disconnected")
    except Exception as e:
        logger.error(f"Error in websocket_endpoint: {e}")
    finally:
        # Ensure bridge is closed
        if "bridge" in locals():
            await bridge.close()


@app.websocket("/twilio-agent")
async def handle_twilio_call(twilio_websocket: WebSocket):
    """Handle WebSocket connections between Twilio Media Streams and OpenAI."""
    client_address = twilio_websocket.client
    logger.info(f"------ Incoming Twilio connection from {client_address} ------")
    await twilio_websocket.accept()
    logger.info(f"------ Twilio connection accepted from {client_address} ------")

    try:
        logger.info("Attempting to connect to OpenAI Realtime API for Twilio...")

        # Get a managed connection to OpenAI Realtime API
        async with websocket_manager.connection_context() as connection:
            logger.info(
                f"OpenAI WebSocket connection established for Twilio: {connection.connection_id}"
            )
            bridge = TwilioBridge(twilio_websocket, connection.websocket)
            logger.info("Twilio-Realtime bridge created")

            # Start receiving from both WebSockets
            try:
                logger.info("Starting Twilio bridge tasks...")
                await asyncio.gather(
                    bridge.receive_from_platform(), bridge.receive_from_realtime()
                )
            except Exception as e:
                logger.error(f"Error in Twilio main connection loop: {e}")
                raise
            finally:
                logger.info("Closing Twilio bridge...")
                await bridge.close()

    except websockets.exceptions.InvalidStatusCode as e:
        logger.error(f"Invalid status code from OpenAI (Twilio): {e}")
        logger.error(f"Response headers: {e.response_headers}")
        await twilio_websocket.close()
    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"OpenAI connection closed (Twilio): {e}")
        logger.error(f"Close code: {e.code}")
        logger.error(f"Close reason: {e.reason}")
        await twilio_websocket.close()
    except Exception as e:
        logger.error(f"Error establishing OpenAI connection (Twilio): {e}")
        await twilio_websocket.close()


@app.post("/twilio/voice")
async def twilio_voice(request: Request):
    """Handle incoming Twilio voice calls.

    This endpoint receives incoming voice calls from Twilio and responds with TwiML
    instructions to connect the call to our WebSocket endpoint for real-time AI interaction.
    """
    logger.info(f"------ Incoming Twilio voice call ------")
    # Create a TwiML response
    response = VoiceResponse()
    logger.info(f" Response: {response}")
    # Connect the call to our WebSocket endpoint using the public URL
    connect = response.connect()
    logger.info(f"------ Connecting call to WebSocket endpoint ------")
    logger.info(f"------ {SERVER_URL} ------")
    connect.stream(url=SERVER_URL)
    logger.info(f"------ Connected call to WebSocket endpoint ------")

    # Return XML response with proper Content-Type header
    return Response(content=str(response), media_type="application/xml")


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
            "/ws/telephony": "WebSocket endpoint for AudioCodes VoiceAI Connect",
            "/twilio-agent": "WebSocket endpoint for Twilio Media Streams",
            "/twilio/voice": "Webhook endpoint for incoming Twilio voice calls",
            "/stats": "Connection statistics and health information",
            "/health": "Health check endpoint for service monitoring",
            "/config": "Current WebSocket manager configuration",
        },
    }


@app.get("/stats")
async def get_stats():
    """Get WebSocket connection statistics and health information.

    Returns:
        dict: Current connection pool statistics
    """
    return websocket_manager.get_stats()


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring service health.

    Returns:
        dict: Health status information
    """
    stats = websocket_manager.get_stats()
    is_healthy = (
        stats["healthy_connections"] > 0
        or stats["total_connections"] < stats["max_connections"]
    )

    return {
        "status": "healthy" if is_healthy else "degraded",
        "websocket_manager": {
            "healthy_connections": stats["healthy_connections"],
            "total_connections": stats["total_connections"],
            "max_connections": stats["max_connections"],
        },
        "message": (
            "Service is operational"
            if is_healthy
            else "WebSocket connection issues detected"
        ),
    }


@app.get("/config")
async def get_config():
    """Get current WebSocket manager configuration.

    Returns:
        dict: Current configuration settings
    """
    return {
        "websocket_manager": WebSocketConfig.to_dict(),
        "note": "Configuration is read from environment variables at startup",
    }


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    logger.info("Application shutting down, cleaning up WebSocket connections...")
    await websocket_manager.shutdown()


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on http://{HOST}:{PORT}")
    # Configure uvicorn with optimized settings for real-time audio
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        # Optimized WebSocket settings for low latency audio streaming
        websocket_ping_interval=10,  # Reduce ping frequency to avoid interference with audio
        websocket_max_size=4194304,  # 4MB - optimal for audio chunks without excessive buffering
        websocket_ping_timeout=30,  # Longer timeout for stability
        # Use HTTP/1.1 for lower overhead than HTTP/2
        http="h11",
        # Additional performance optimizations
        loop="asyncio",
        timeout_keep_alive=30,
        limit_concurrency=1000,
        limit_max_requests=10000,
    )
