"""Session management for OpenAI Realtime API.

This module provides functionality to manage OpenAI Realtime API sessions,
including session initialization, configuration, and conversation management.
"""

import asyncio
import json
from typing import Optional

from opusagent.config.logging_config import configure_logging
from opusagent.models.openai_api import SessionConfig, SessionUpdateEvent

# Configure logging
logger = configure_logging("session_manager")

# Model constants
#! Move to config
DEFAULT_MODEL = "gpt-4o-realtime-preview-2024-10-01"
MINI_MODEL = "gpt-4o-mini-realtime-preview-2024-12-17"
FUTURE_MODEL = "gpt-4o-realtime-preview-2025-06-03"

#! Move to config
SELECTED_MODEL = FUTURE_MODEL
VOICE = "verse"


class SessionManager:
    """Manages OpenAI Realtime API sessions and conversations.

    This class handles session initialization, configuration, and conversation
    management for the OpenAI Realtime API.

    Attributes:
        realtime_websocket (ClientConnection): WebSocket connection to OpenAI Realtime API
        session_config (SessionConfig): Predefined session configuration
        session_initialized (bool): Whether the session has been initialized
        conversation_id (Optional[str]): Current conversation ID
    """

    def __init__(self, realtime_websocket, session_config: SessionConfig):
        """Initialize the session manager.

        Args:
            realtime_websocket: WebSocket connection to OpenAI Realtime API
            session_config: Predefined session configuration
        """
        self.realtime_websocket = realtime_websocket
        self.session_config = session_config
        self.session_initialized = False
        self.conversation_id: Optional[str] = None

    async def initialize_session(self):
        """Initialize the OpenAI Realtime API session with configuration.

        This method sets up the initial session configuration for the OpenAI Realtime API,
        using the predefined session config passed to the constructor.
        """
        session_update = SessionUpdateEvent(
            type="session.update", session=self.session_config
        )

        logger.info("Sending session update: %s", session_update.model_dump_json())
        await self.realtime_websocket.send(session_update.model_dump_json())
        self.session_initialized = True

    async def send_initial_conversation_item(self) -> None:
        #! Agent should have this
        """Send the initial conversation item to start the AI interaction.

        This method creates and sends the first conversation item to the OpenAI Realtime API,
        initiating the conversation with a greeting and request for an introduction and joke.
        """
        try:
            # Create initial conversation item using plain JSON to avoid model validation issues
            initial_conversation = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "You are a customer service agent. You are given a task to help the customer with their banking needs. Start by saying 'Hello! How can I help you today?' You will infer the customer's intent from their response and call the call_intent function.",
                        }
                    ],
                },
            }

            logger.info(
                "Sending initial conversation item: %s",
                json.dumps(initial_conversation),
            )
            await self.realtime_websocket.send(json.dumps(initial_conversation))

            # Wait for the conversation item to be processed
            await asyncio.sleep(2)

            # Create response using the correct structure for OpenAI Realtime API
            response_create = {
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"],
                    "output_audio_format": "pcm16",
                    "temperature": 0.8,
                    "max_output_tokens": 4096,
                    "voice": self.session_config.voice,
                },
            }

            logger.info("Sending response create: %s", json.dumps(response_create))
            await self.realtime_websocket.send(json.dumps(response_create))
            logger.info("Initial conversation flow initiated successfully")

        except Exception as e:
            logger.error(f"Error in send_initial_conversation_item: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def create_response(self):
        #! Is this needed?
        """Create a new response request to OpenAI Realtime API.

        This method creates a new response request with the specified configuration.
        """
        try:
            response_create = {
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"],
                    "output_audio_format": "pcm16",
                    "temperature": 0.8,
                    "max_output_tokens": 4096,
                    "voice": self.session_config.voice,
                },
            }
            await self.realtime_websocket.send(json.dumps(response_create))
            logger.info("Response creation triggered")
        except Exception as e:
            logger.error(f"Error creating response: {e}")
            raise
