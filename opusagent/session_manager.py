"""Session management for OpenAI Realtime API.

This module provides functionality to manage OpenAI Realtime API sessions,
including session initialization, configuration, and conversation management.
"""

import asyncio
import json
import logging
from typing import Optional

import websockets
from opusagent.models.openai_api import (
    SessionConfig,
    SessionUpdateEvent,
    ConversationItemCreateEvent,
    ResponseCreateOptions,
)
from opusagent.pure_prompt import SESSION_PROMPT

# Configure logging
logger = logging.getLogger(__name__)

# Model constants
DEFAULT_MODEL = "gpt-4o-realtime-preview-2024-10-01"
MINI_MODEL = "gpt-4o-mini-realtime-preview-2024-12-17"
FUTURE_MODEL = "gpt-4o-realtime-preview-2025-06-03"

SELECTED_MODEL = FUTURE_MODEL
VOICE = "verse"

class SessionManager:
    """Manages OpenAI Realtime API sessions and conversations.
    
    This class handles session initialization, configuration, and conversation
    management for the OpenAI Realtime API.
    
    Attributes:
        realtime_websocket (ClientConnection): WebSocket connection to OpenAI Realtime API
        session_initialized (bool): Whether the session has been initialized
        conversation_id (Optional[str]): Current conversation ID
    """
    
    def __init__(self, realtime_websocket):
        """Initialize the session manager.
        
        Args:
            realtime_websocket: WebSocket connection to OpenAI Realtime API
        """
        self.realtime_websocket = realtime_websocket
        self.session_initialized = False
        self.conversation_id: Optional[str] = None

    async def initialize_session(self):
        """Initialize the OpenAI Realtime API session with configuration.
        
        This method sets up the initial session configuration for the OpenAI Realtime API,
        including audio format settings, voice selection, system instructions, and other
        session parameters.
        """
        session_config = SessionConfig(
            input_audio_format="pcm16",
            output_audio_format="pcm16",
            voice=VOICE,
            instructions=SESSION_PROMPT,
            modalities=["text", "audio"],
            temperature=0.8,
            model=SELECTED_MODEL,
            tools=[
                {
                    "type": "function",
                    "name": "get_balance",
                    "description": "Get the user's account balance.",
                    "parameters": {"type": "object", "properties": {}},
                },
                {
                    "type": "function",
                    "name": "transfer_funds",
                    "description": "Transfer funds to another account.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount": {"type": "number"},
                            "to_account": {"type": "string"},
                        },
                    },
                },
                {
                    "type": "function",
                    "name": "transfer_to_human",
                    "description": "Transfer the conversation to a human agent.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "The reason for transferring to a human agent",
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["low", "normal", "high"],
                                "description": "The priority level of the transfer",
                            },
                            "context": {
                                "type": "object",
                                "description": "Additional context to pass to the human agent",
                            },
                        },
                        "required": ["reason"],
                    },
                },
                {
                    "type": "function",
                    "name": "call_intent",
                    "description": "Get the user's intent.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "intent": {
                                "type": "string",
                                "enum": ["card_replacement", "account_inquiry", "other"],
                            },
                        },
                        "required": ["intent"],
                    },
                },
                {
                    "type": "function",
                    "name": "member_account_confirmation",
                    "description": "Confirm which member account/card needs replacement.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_accounts": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of available member accounts/cards",
                            },
                            "organization_name": {"type": "string"},
                        },
                    },
                },
                {
                    "type": "function",
                    "name": "replacement_reason",
                    "description": "Collect the reason for card replacement.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "card_in_context": {"type": "string"},
                            "reason": {
                                "type": "string",
                                "enum": ["Lost", "Damaged", "Stolen", "Other"],
                            },
                        },
                    },
                },
                {
                    "type": "function",
                    "name": "confirm_address",
                    "description": "Confirm the address for card delivery.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "card_in_context": {"type": "string"},
                            "address_on_file": {"type": "string"},
                            "confirmed_address": {"type": "string"},
                        },
                    },
                },
                {
                    "type": "function",
                    "name": "start_card_replacement",
                    "description": "Start the card replacement process.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "card_in_context": {"type": "string"},
                            "address_in_context": {"type": "string"},
                        },
                    },
                },
                {
                    "type": "function",
                    "name": "finish_card_replacement",
                    "description": "Finish the card replacement process and provide delivery information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "card_in_context": {"type": "string"},
                            "address_in_context": {"type": "string"},
                            "delivery_time": {"type": "string"},
                        },
                    },
                },
                {
                    "type": "function",
                    "name": "wrap_up",
                    "description": "Wrap up the call with closing remarks.",
                    "parameters": {
                        "type": "object",
                        "properties": {"organization_name": {"type": "string"}},
                    },
                },
                {
                    "type": "function",
                    "name": "process_replacement",
                    "description": "Process the card replacement",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "card": {
                                "type": "string",
                                "description": "The card to replace",
                            },
                            "reason": {
                                "type": "string",
                                "description": "The reason for the card replacement",
                            },
                            "address": {
                                "type": "string",
                                "description": "The address to send the replacement card",
                            },
                        },
                        "required": ["card", "reason", "address"],
                    },
                },
            ],
            input_audio_noise_reduction={"type": "near_field"},
            input_audio_transcription={"model": "whisper-1"},
            max_response_output_tokens=4096,
            tool_choice="auto",
        )

        session_update = SessionUpdateEvent(type="session.update", session=session_config)

        logger.info("Sending session update: %s", session_update.model_dump_json())
        await self.realtime_websocket.send(session_update.model_dump_json())
        self.session_initialized = True

    async def send_initial_conversation_item(self) -> None:
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
                "Sending initial conversation item: %s", json.dumps(initial_conversation)
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
                    "voice": VOICE,
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
                    "voice": VOICE,
                },
            }
            await self.realtime_websocket.send(json.dumps(response_create))
            logger.info("Response creation triggered")
        except Exception as e:
            logger.error(f"Error creating response: {e}")
            raise 