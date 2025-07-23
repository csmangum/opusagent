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

import websockets
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse

from opusagent.bridges.audiocodes_bridge import AudioCodesBridge
from opusagent.bridges.call_agent_bridge import CallAgentBridge
from opusagent.bridges.dual_agent_bridge import DualAgentBridge
from opusagent.bridges.twilio_bridge import TwilioBridge

from opusagent.config import get_config, server_config, mock_config, vad_config, transcription_config
from opusagent.config.env_loader import load_env_file
from opusagent.config.logging_config import configure_logging
from opusagent.config.models import WebSocketConfig
from opusagent.customer_service_agent import session_config
from opusagent.session_manager import SessionManager
from opusagent.websocket_manager import get_websocket_manager, WebSocketManager
from opusagent.callers import get_available_caller_types, get_caller_description
from opusagent.local.realtime import create_mock_websocket_connection
from opusagent.websocket_manager import get_websocket_manager

# Load environment variables before accessing configuration
load_env_file()

# Get centralized configuration
config = get_config()


# Configure logging using centralized config
logger = configure_logging("main")

# Server configuration from centralized config
PORT = config.server.port
HOST = config.server.host
SERVER_URL = f"http://{HOST}:{PORT}"

# VAD configuration from centralized config
VAD_ENABLED = config.vad.enabled

# Mock/Local realtime configuration from centralized config
USE_LOCAL_REALTIME = config.mock.use_local_realtime
LOCAL_REALTIME_CONFIG = {
    "enable_transcription": config.mock.enable_transcription,
    "setup_smart_responses": config.mock.setup_smart_responses,

    "vad_config": {
        "backend": config.vad.backend,
        "threshold": config.vad.confidence_threshold,
        "sample_rate": config.vad.sample_rate,
    },
    "transcription_config": {
        "backend": config.transcription.backend,
        "language": config.transcription.language,
        "model_size": config.transcription.model_size,
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
            # Use mock WebSocket connection with local realtime client
            logger.info("Using mock WebSocket connection with local realtime client")

            # Create mock WebSocket connection that wraps LocalRealtimeClient
            mock_connection = await create_mock_websocket_connection(
                session_config=session_config,
                local_realtime_config=LOCAL_REALTIME_CONFIG,
                setup_smart_responses=LOCAL_REALTIME_CONFIG.get(
                    "setup_smart_responses", True
                ),
                enable_vad=VAD_ENABLED,
                enable_transcription=LOCAL_REALTIME_CONFIG.get(
                    "enable_transcription", False
                ),
            )

            # Create AudioCodes bridge with mock connection
            bridge = AudioCodesBridge(
                websocket,
                mock_connection,  # Use mock connection instead of None
                session_config,
                vad_enabled=VAD_ENABLED,
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
    """Handle WebSocket connections from a *caller* agent (LocalAudioCodesClient).

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
            # Use mock WebSocket connection with local realtime client
            logger.info(
                "Using mock WebSocket connection with local realtime client for caller agent"
            )

            # Create mock WebSocket connection that wraps LocalRealtimeClient
            mock_connection = await create_mock_websocket_connection(
                session_config=session_config,
                local_realtime_config=LOCAL_REALTIME_CONFIG,
                setup_smart_responses=LOCAL_REALTIME_CONFIG.get(
                    "setup_smart_responses", True
                ),
                enable_vad=VAD_ENABLED,
                enable_transcription=LOCAL_REALTIME_CONFIG.get(
                    "enable_transcription", False
                ),
            )

            # Instantiate our caller side bridge with mock connection
            bridge = CallAgentBridge(
                caller_websocket,
                mock_connection,  # Use mock connection instead of None
                session_config,
                vad_enabled=VAD_ENABLED,
            )
            logger.info("Caller-Realtime bridge created with mock connection")
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
                    vad_enabled=VAD_ENABLED,
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
            # Use mock WebSocket connection with local realtime client
            logger.info(
                "Using mock WebSocket connection with local realtime client for Twilio"
            )

            # Create mock WebSocket connection that wraps LocalRealtimeClient
            mock_connection = await create_mock_websocket_connection(
                session_config=session_config,
                local_realtime_config=LOCAL_REALTIME_CONFIG,
                setup_smart_responses=LOCAL_REALTIME_CONFIG.get(
                    "setup_smart_responses", True
                ),
                enable_vad=VAD_ENABLED,
                enable_transcription=LOCAL_REALTIME_CONFIG.get(
                    "enable_transcription", False
                ),
            )

            # Create Twilio bridge with mock connection
            bridge = TwilioBridge(
                twilio_websocket,
                mock_connection,  # Use mock connection instead of None
                session_config,
            )
            logger.info("Twilio-Realtime bridge created with mock connection")
        else:
            logger.info("Attempting to connect to OpenAI Realtime API for Twilio...")

            # Get a managed connection to OpenAI Realtime API
            async with get_websocket_manager().connection_context() as connection:
                logger.info(
                    f"OpenAI WebSocket connection established for Twilio: {connection.connection_id}"
                )
                bridge = TwilioBridge(
                    twilio_websocket, connection.websocket, session_config
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
async def agent_conversation_endpoint(
    websocket: WebSocket, caller_type: str = "typical"
):
    """WebSocket endpoint for caller agent to CS agent conversations.

    This endpoint enables direct conversations between a caller agent and
    customer service agent without external telephony platforms.

    Args:
        websocket: The WebSocket connection
        caller_type: Type of caller to use (typical, frustrated, elderly, hurried)
    """
    await websocket.accept()
    client_address = websocket.client
    logger.info(
        f"------ Agent conversation request from {client_address} with {caller_type} caller ------"
    )

    try:
        # Create and initialize dual agent bridge with specified caller type
        bridge = DualAgentBridge(caller_type=caller_type)
        logger.info(f"Created dual agent bridge: {bridge.conversation_id}")

        # Initialize both OpenAI connections and start conversation
        await bridge.initialize_connections()

    except Exception as e:
        logger.error(f"Error in agent conversation: {e}")
        if "bridge" in locals():
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
    connect.stream(url=SERVER_URL)  # type: ignore
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
            "vad_enabled": config.vad.enabled,
            "use_local_realtime": config.mock.use_local_realtime,
            "local_realtime_config": LOCAL_REALTIME_CONFIG if config.mock.use_local_realtime else None,
            "environment": config.server.environment.value,
            "openai_model": config.openai.model,
            "audio_format": config.audio.format,
            "sample_rate": config.audio.sample_rate,
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
            "hurried": "Caller in a rush wanting quick service",
        },
        "environment_variables": {
            "OPENAI_API_KEY": "OpenAI API key (required for real mode)",
            "HOST": f"Server host (current: {config.server.host})",
            "PORT": f"Server port (current: {config.server.port})",
            "ENV": f"Environment (current: {config.server.environment.value})",
            "LOG_LEVEL": f"Log level (current: {config.logging.level.value})",
            "VAD_ENABLED": f"Enable/disable VAD (current: {config.vad.enabled})",
            "VAD_BACKEND": f"VAD backend (current: {config.vad.backend})",
            "USE_LOCAL_REALTIME": f"Use local realtime client (current: {config.mock.use_local_realtime})",
            "OPUSAGENT_USE_MOCK": f"Enable mock mode (current: {config.mock.enabled})",
            "TRANSCRIPTION_BACKEND": f"Transcription backend (current: {config.transcription.backend})",
            "AUDIO_SAMPLE_RATE": f"Audio sample rate (current: {config.audio.sample_rate})",
        },
        "example_usage": {
            "agent_conversation": "/agent-conversation?caller_type=frustrated",
            "caller_types": "/caller-types",
            "local_realtime": "Set USE_LOCAL_REALTIME=true to use local client",
            "custom_responses": "Configure LOCAL_REALTIME_CONFIG for custom responses",
        },
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
async def get_app_config():
    """Get current application configuration.

    Returns:
        dict: Current configuration settings from centralized config system
    """
    return {
        "server": {
            "host": config.server.host,
            "port": config.server.port,
            "environment": config.server.environment.value,
            "debug": config.server.debug,
        },
        "openai": {
            "model": config.openai.model,
            "base_url": config.openai.base_url,
            "api_key_configured": bool(config.openai.api_key),
        },
        "audio": {
            "sample_rate": config.audio.sample_rate,
            "format": config.audio.format,
            "channels": config.audio.channels,
            "chunk_size": config.audio.chunk_size,
        },
        "vad": {
            "enabled": config.vad.enabled,
            "backend": config.vad.backend,
            "confidence_threshold": config.vad.confidence_threshold,
            "sample_rate": config.vad.sample_rate,
        },
        "transcription": {
            "enabled": config.transcription.enabled,
            "backend": config.transcription.backend,
            "language": config.transcription.language,
            "model_size": config.transcription.model_size,
        },
        "websocket_manager": {
            "max_connections": config.websocket.max_connections,
            "max_connection_age": config.websocket.max_connection_age,
            "max_idle_time": config.websocket.max_idle_time,
            "health_check_interval": config.websocket.health_check_interval,
            "max_sessions_per_connection": config.websocket.max_sessions_per_connection,
            "ping_interval": config.websocket.ping_interval,
            "ping_timeout": config.websocket.ping_timeout,
            "close_timeout": config.websocket.close_timeout,
            "openai_model": config.openai.model,
            "websocket_url": config.openai.get_websocket_url(),
        },
        "mock": {
            "enabled": config.mock.enabled,
            "server_url": config.mock.server_url,
            "use_local_realtime": config.mock.use_local_realtime,
        },
        "note": "Configuration loaded from centralized config system with environment variable overrides",
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
        "example": "/agent-conversation?caller_type=frustrated",
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
