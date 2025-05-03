import json
import logging
import uuid
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from fastagent.telephony_realtime_bridge import TelephonyRealtimeBridge
from fastagent.config.constants import LOGGER_NAME

load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Configure logging
logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(handler)

# Initialize the TelephonyRealtimeBridge singleton
bridge = TelephonyRealtimeBridge()


@app.websocket("/audiocodes")
async def audiocodes_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint to handle audio streaming from AudioCodes to OpenAI Realtime API.

    This endpoint:
    1. Accepts WebSocket connections from AudioCodes.
    2. Creates a unique conversation ID for each connection.
    3. Uses TelephonyRealtimeBridge to forward base64 audio chunks to OpenAI.
    4. Sends OpenAI audio responses back to AudioCodes.
    5. Handles connection lifecycle and cleanup.

    Args:
        websocket: FastAPI WebSocket connection object.

    Notes:
        - Expects AudioCodes to send JSON messages with base64-encoded audio chunks.
        - Sends responses in the format expected by AudioCodes (playStream.start, playStream.chunk, playStream.stop).
    """
    # Generate a unique conversation ID
    conversation_id = str(uuid.uuid4())
    logger.info(f"New WebSocket connection request received for conversation: {conversation_id}")

    try:
        # Accept the WebSocket connection
        logger.info(f"Attempting to accept WebSocket connection for conversation: {conversation_id}")
        await websocket.accept()
        logger.info(f"WebSocket connection accepted for conversation: {conversation_id}")

        # Create and initialize OpenAI Realtime client via the bridge
        logger.info(f"Creating OpenAI client for conversation: {conversation_id}")
        await bridge.create_client(conversation_id, websocket)
        logger.info(f"OpenAI client created successfully for conversation: {conversation_id}")

        # Keep the connection alive until client disconnects
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    if message.get("type") == "audioChunk":
                        audio_chunk = message.get("audioChunk")
                        if audio_chunk:
                            await bridge.send_audio_chunk(conversation_id, audio_chunk)
                            logger.debug(f"Processed audio chunk for conversation: {conversation_id}")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received for conversation: {conversation_id}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    continue

        except WebSocketDisconnect:
            logger.info(f"Client disconnected for conversation: {conversation_id}")
        except Exception as e:
            logger.error(f"Error in WebSocket connection: {str(e)}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for conversation: {conversation_id}")
    except Exception as e:
        logger.error(f"WebSocket error for conversation: {conversation_id}: {str(e)}")
    finally:
        # Clean up the client and resources
        try:
            if conversation_id:
                try:
                    # Check if WebSocket is still connected before sending stop message
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await bridge.stop_stream(conversation_id)
                except Exception as e:
                    logger.error(f"Error stopping stream for conversation {conversation_id}: {str(e)}")
                
                try:
                    await bridge.close_client(conversation_id)
                except Exception as e:
                    logger.error(f"Error closing client for conversation {conversation_id}: {str(e)}")
                
                logger.info(f"Cleaned up resources for conversation: {conversation_id}")
        except Exception as e:
            logger.error(f"Error during cleanup for conversation: {conversation_id}: {str(e)}")
