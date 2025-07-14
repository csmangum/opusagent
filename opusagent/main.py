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
from websockets.exceptions import ConnectionClosed

from opusagent.bridges.audiocodes_bridge import AudioCodesBridge
from opusagent.bridges.call_agent_bridge import CallAgentBridge
from opusagent.bridges.twilio_bridge import TwilioBridge
from opusagent.bridges.dual_agent_bridge import DualAgentBridge
from opusagent.config.logging_config import configure_logging
from opusagent.customer_service_agent import session_config
from opusagent.session_manager import SessionManager
from opusagent.config.websocket_config import WebSocketConfig
from opusagent.websocket_manager import get_websocket_manager, WebSocketManager
from opusagent.callers import get_available_caller_types, get_caller_description

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

# VAD configuration - enable by default, can be disabled via environment variable
VAD_ENABLED = os.getenv("VAD_ENABLED", "true").lower() in ("true", "1", "yes", "on")

# Local realtime configuration
USE_LOCAL_REALTIME = os.getenv("USE_LOCAL_REALTIME", "false").lower() in ("true", "1", "yes", "on")
LOCAL_REALTIME_CONFIG = {
    "enable_transcription": os.getenv("LOCAL_REALTIME_ENABLE_TRANSCRIPTION", "false").lower() in ("true", "1", "yes", "on"),
    "setup_smart_responses": os.getenv("LOCAL_REALTIME_SETUP_SMART_RESPONSES", "true").lower() in ("true", "1", "yes", "on"),
    "vad_config": {
        "backend": os.getenv("LOCAL_REALTIME_VAD_BACKEND", "silero"),
        "threshold": float(os.getenv("LOCAL_REALTIME_VAD_THRESHOLD", "0.5")),
        "sample_rate": int(os.getenv("LOCAL_REALTIME_VAD_SAMPLE_RATE", "16000")),
    },
    "transcription_config": {
        "backend": os.getenv("LOCAL_REALTIME_TRANSCRIPTION_BACKEND", "pocketsphinx"),
        "language": os.getenv("LOCAL_REALTIME_TRANSCRIPTION_LANGUAGE", "en"),
        "model_size": os.getenv("LOCAL_REALTIME_TRANSCRIPTION_MODEL_SIZE", "base"),
    }
}

# Log configuration
logger.info(f"Server configuration:")
logger.info(f"  - VAD Enabled: {VAD_ENABLED}")
logger.info(f"  - Use Local Realtime: {USE_LOCAL_REALTIME}")
if USE_LOCAL_REALTIME:
    logger.info(f"  - Local Realtime Config: {LOCAL_REALTIME_CONFIG}")

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
    and creates a bridge to either the OpenAI Realtime API or Local Realtime Client
    using the WebSocket manager.

    Args:
        websocket (WebSocket): The WebSocket connection from the telephony client
    """
    await websocket.accept()
    logger.info("Telephony WebSocket connection accepted")

    try:
        if USE_LOCAL_REALTIME:
            # Use local realtime client directly
            logger.info("Using local realtime client for telephony")
            
            # Create AudioCodes bridge with local realtime client
            bridge = AudioCodesBridge(
                websocket, 
                None,  # No realtime websocket needed for local client
                session_config, 
                vad_enabled=VAD_ENABLED,
                bridge_type='audiocodes',
                use_local_realtime=True,
                local_realtime_config=LOCAL_REALTIME_CONFIG
            )
        else:
            # Get a managed connection to OpenAI Realtime API
            async with get_websocket_manager().connection_context() as connection:
                logger.info(f"Using OpenAI connection: {connection.connection_id}")

                # Create AudioCodes bridge instance
                bridge = AudioCodesBridge(
                    websocket, 
                    connection.websocket, 
                    session_config, 
                    vad_enabled=VAD_ENABLED,
                    bridge_type='audiocodes'
                )

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


@app.websocket("/caller-agent")
async def handle_caller_call(caller_websocket: WebSocket):
    """Handle WebSocket connections from a *caller* agent (MockAudioCodesClient).

    The caller-agent shares the same AudioCodes VAIC message schema as the
    inbound /ws/telephony endpoint, but is used by our test harness / synthetic
    caller agents defined in ``caller_agent.py``.  We keep it on a dedicated
    route to avoid interfering with production traffic and so that we can apply
    separate security rules in the future.
    """

    await caller_websocket.accept()
    client_address = caller_websocket.client
    logger.info(f"------ Caller connection accepted from {client_address} ------")

    try:
        if USE_LOCAL_REALTIME:
            # Use local realtime client directly
            logger.info("Using local realtime client for caller agent")
            
            # Instantiate our caller side bridge with local realtime client
            bridge = CallAgentBridge(
                caller_websocket, 
                None,  # No realtime websocket needed for local client
                session_config, 
                vad_enabled=VAD_ENABLED,
                use_local_realtime=True,
                local_realtime_config=LOCAL_REALTIME_CONFIG
            )
            logger.info("Caller-Realtime bridge created with local client")
        else:
            logger.info("Attempting to connect to OpenAI Realtime API for Caller...")

            # Get a managed connection to OpenAI Realtime API
            async with get_websocket_manager().connection_context() as connection:
                logger.info(
                    f"OpenAI WebSocket connection established for Caller: {connection.connection_id}"
                )

                # Instantiate our caller side bridge
                bridge = CallAgentBridge(
                    caller_websocket, 
                    connection.websocket, 
                    session_config, 
                    vad_enabled=VAD_ENABLED
                )
                logger.info("Caller-Realtime bridge created")

        # Start bidirectional tasks
        try:
            logger.info("Starting Caller bridge tasks...")
            await asyncio.gather(
                bridge.receive_from_platform(), bridge.receive_from_realtime()
            )
        except Exception as e:
            logger.error(f"Error in Caller connection loop: {e}")
            raise
        finally:
            logger.info("Closing Caller bridge...")
            await bridge.close()

    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"OpenAI connection closed (Caller): {e}")
        logger.error(f"Close code: {e.code}")
        logger.error(f"Close reason: {e.reason}")
        await caller_websocket.close()
    except Exception as e:
        logger.error(f"Error establishing connection (Caller): {e}")
        await caller_websocket.close()


@app.websocket("/twilio-agent")
async def handle_twilio_call(twilio_websocket: WebSocket):
    """Handle WebSocket connections between Twilio Media Streams and OpenAI."""
    client_address = twilio_websocket.client
    logger.info(f"------ Incoming Twilio connection from {client_address} ------")
    await twilio_websocket.accept()
    logger.info(f"------ Twilio connection accepted from {client_address} ------")

    try:
        if USE_LOCAL_REALTIME:
            # Use local realtime client directly
            logger.info("Using local realtime client for Twilio")
            
            # Create Twilio bridge with local realtime client
            bridge = TwilioBridge(
                twilio_websocket, 
                None,  # No realtime websocket needed for local client
                session_config,
                use_local_realtime=True,
                local_realtime_config=LOCAL_REALTIME_CONFIG
            )
            logger.info("Twilio-Realtime bridge created with local client")
        else:
            logger.info("Attempting to connect to OpenAI Realtime API for Twilio...")

            # Get a managed connection to OpenAI Realtime API
            async with get_websocket_manager().connection_context() as connection:
                logger.info(
                    f"OpenAI WebSocket connection established for Twilio: {connection.connection_id}"
                )
                bridge = TwilioBridge(
                    twilio_websocket, 
                    connection.websocket, 
                    session_config
                )
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

    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"OpenAI connection closed (Twilio): {e}")
        logger.error(f"Close code: {e.code}")
        logger.error(f"Close reason: {e.reason}")
        await twilio_websocket.close()
    except Exception as e:
        logger.error(f"Error establishing connection (Twilio): {e}")
        await twilio_websocket.close()


@app.websocket("/agent-conversation")
async def agent_conversation_endpoint(websocket: WebSocket, caller_type: str = "typical"):
    """WebSocket endpoint for caller agent to CS agent conversations.
    
    This endpoint enables direct conversations between a caller agent and
    customer service agent without external telephony platforms.
    
    Args:
        websocket: The WebSocket connection
        caller_type: Type of caller to use (typical, frustrated, elderly, hurried)
    """
    await websocket.accept()
    client_address = websocket.client
    logger.info(f"------ Agent conversation request from {client_address} with {caller_type} caller ------")
    
    try:
        # Create and initialize dual agent bridge with specified caller type
        bridge = DualAgentBridge(caller_type=caller_type)
        logger.info(f"Created dual agent bridge: {bridge.conversation_id}")
        
        # Initialize both OpenAI connections and start conversation
        await bridge.initialize_connections()
        
    except Exception as e:
        logger.error(f"Error in agent conversation: {e}")
        if 'bridge' in locals():
            await bridge.close()
    finally:
        logger.info("Agent conversation ended")
        await websocket.close()


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
    connect.stream(url=SERVER_URL) # type: ignore
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
        "configuration": {
            "vad_enabled": VAD_ENABLED,
            "use_local_realtime": USE_LOCAL_REALTIME,
            "local_realtime_config": LOCAL_REALTIME_CONFIG if USE_LOCAL_REALTIME else None,
        },
        "endpoints": {
            "/ws/telephony": "WebSocket endpoint for AudioCodes VoiceAI Connect",
            "/twilio-agent": "WebSocket endpoint for Twilio Media Streams",
            "/twilio/voice": "Webhook endpoint for incoming Twilio voice calls",
            "/caller-agent": "WebSocket endpoint for Caller test agents",
            "/agent-conversation": "WebSocket endpoint for caller agent to CS agent conversations (use ?caller_type=<type>)",
            "/caller-types": "Get available caller types and their descriptions",
            "/stats": "Connection statistics and health information",
            "/health": "Health check endpoint for service monitoring",
            "/config": "Current WebSocket manager configuration",
        },
        "caller_types": {
            "typical": "Cooperative, patient caller",
            "frustrated": "Impatient, demanding caller", 
            "elderly": "Patient, polite caller needing guidance",
            "hurried": "Caller in a rush wanting quick service"
        },
        "environment_variables": {
            "VAD_ENABLED": "Enable/disable Voice Activity Detection (default: true)",
            "USE_LOCAL_REALTIME": "Use local realtime client instead of OpenAI API (default: false)",
            "LOCAL_REALTIME_ENABLE_TRANSCRIPTION": "Enable local transcription (default: false)",
            "LOCAL_REALTIME_SETUP_SMART_RESPONSES": "Setup smart response examples (default: true)",
            "LOCAL_REALTIME_VAD_BACKEND": "VAD backend (silero/pocketsphinx, default: silero)",
            "LOCAL_REALTIME_VAD_THRESHOLD": "VAD threshold (0.0-1.0, default: 0.5)",
            "LOCAL_REALTIME_VAD_SAMPLE_RATE": "VAD sample rate (default: 16000)",
            "LOCAL_REALTIME_TRANSCRIPTION_BACKEND": "Transcription backend (pocketsphinx/whisper, default: pocketsphinx)",
            "LOCAL_REALTIME_TRANSCRIPTION_LANGUAGE": "Transcription language (default: en)",
            "LOCAL_REALTIME_TRANSCRIPTION_MODEL_SIZE": "Whisper model size (default: base)",
        },
        "example_usage": {
            "agent_conversation": "/agent-conversation?caller_type=frustrated",
            "caller_types": "/caller-types",
            "local_realtime": "Set USE_LOCAL_REALTIME=true to use local client",
            "custom_responses": "Configure LOCAL_REALTIME_CONFIG for custom responses"
        }
    }


@app.get("/stats")
async def get_stats():
    """Get WebSocket connection statistics and health information.

    Returns:
        dict: Current connection pool statistics
    """
    return get_websocket_manager().get_stats()


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring service health.

    Returns:
        dict: Health status information
    """
    stats = get_websocket_manager().get_stats()
    is_healthy = stats["healthy_connections"] > 0

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


@app.get("/caller-types")
async def get_caller_types():
    """Get available caller types and their descriptions.
    
    Returns:
        dict: Available caller types with descriptions
    """
    caller_types = {}
    for caller_type in get_available_caller_types():
        caller_types[caller_type] = get_caller_description(caller_type)
    
    return {
        "available_caller_types": caller_types,
        "usage": "Use ?caller_type=<type> query parameter with /agent-conversation endpoint",
        "example": "/agent-conversation?caller_type=frustrated"
    }


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    logger.info("Application shutting down, cleaning up WebSocket connections...")
    try:
        await get_websocket_manager().shutdown()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        # Continue with shutdown even if there's an error


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on http://{HOST}:{PORT}")
    # Configure uvicorn with optimized settings for real-time audio
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        http="h11",
        # Additional performance optimizations
        loop="asyncio",
        timeout_keep_alive=30,
        limit_concurrency=1000,
        limit_max_requests=10000,
    )
