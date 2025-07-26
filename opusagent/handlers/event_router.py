"""Event router for handling telephony and realtime events.

This module provides a centralized event routing system for handling events
from both telephony and OpenAI Realtime API sources.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional

from opusagent.config.logging_config import configure_logging
from opusagent.models.audiocodes_api import TelephonyEventType
from opusagent.models.openai_api import LogEventType, ServerEventType

logger = configure_logging("event_router")

class EventRouter:
    """Router class for handling events from telephony and realtime sources.
    
    This class manages event routing and handling for both telephony and OpenAI Realtime API events.
    It provides a centralized way to register and dispatch event handlers.
    
    Attributes:
        telephony_handlers (Dict[TelephonyEventType, Callable]): Handlers for telephony events
        realtime_handlers (Dict[str, Callable]): Handlers for realtime events
        log_event_types (List[LogEventType]): Types of log events to handle
    """
    
    def __init__(self):
        """Initialize the event router."""
        self.telephony_handlers: Dict[TelephonyEventType, Callable] = {}
        self.realtime_handlers: Dict[str, Callable] = {}
        self.log_event_types = [
            LogEventType.ERROR,
            LogEventType.RESPONSE_CONTENT_DONE,
            LogEventType.RATE_LIMITS_UPDATED,
            LogEventType.INPUT_AUDIO_BUFFER_COMMITTED,
            LogEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED,
            LogEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED,
        ]
    
    def register_platform_handler(self, event_type: TelephonyEventType, handler: Callable) -> None:
        """Register a handler for a telephony event type.
        
        Args:
            event_type: The telephony event type to handle
            handler: The handler function to call for this event type
        """
        self.telephony_handlers[event_type] = handler
        logger.debug(f"Registered telephony handler for event type: {event_type}")
    
    def register_realtime_handler(self, event_type: str, handler: Callable) -> None:
        """Register a handler for a realtime event type.
        
        Args:
            event_type: The realtime event type to handle
            handler: The handler function to call for this event type
        """
        self.realtime_handlers[event_type] = handler
        logger.debug(f"Registered realtime handler for event type: {event_type}")
    
    def _get_platform_event_type(self, msg_type_str: str) -> Optional[TelephonyEventType]:
        """Convert a string message type to a TelephonyEventType enum value.
        
        Args:
            msg_type_str: The message type string from the raw message
            
        Returns:
            TelephonyEventType: The corresponding enum value or None if not found
        """
        try:
            return TelephonyEventType(msg_type_str)
        except ValueError:
            return None
    
    async def handle_platform_event(self, data: Dict[str, Any]) -> None:
        """Handle a platform event.
        
        Args:
            data: The event data containing the message type and other information
        """
        msg_type_str = data["type"]
        msg_type = self._get_platform_event_type(msg_type_str)
        
        if msg_type:
            # Log message type and audio chunk size if present
            if "audioChunk" in data:
                logger.info(
                    f"Received platform message: {msg_type_str} with audio chunk size: {len(data['audioChunk'])} bytes"
                )
            else:
                logger.info(f"Received platform message: {msg_type_str}")
                
            # Dispatch to the appropriate handler
            handler = self.telephony_handlers.get(msg_type)
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Error in platform event handler for {msg_type}: {e}")
            else:
                logger.warning(f"No handler for platform message type: {msg_type}")
        else:
            logger.warning(f"Unknown platform message type: {msg_type_str}")
    
    async def handle_realtime_event(self, data: Dict[str, Any]) -> None:
        """Handle a realtime event.
        
        Args:
            data: The event data containing the event type and other information
        """
        event_type = data["type"]
        logger.info(f"Received OpenAI message type: {event_type}")
        
        # Add detailed logging for important events
        if event_type in ["response.created", "response.done"]:
            logger.info(f"Response event details: {json.dumps(data, indent=2)}")
        elif event_type == "response.output_item.added":
            logger.info(f"Output item added: {json.dumps(data.get('item', {}), indent=2)}")
        elif event_type == "response.content_part.added":
            logger.info(f"Content part added: {json.dumps(data.get('part', {}), indent=2)}")
        elif event_type in ["response.audio.delta", "response.audio_transcript.delta"]:
            logger.info(f"Audio event: {event_type} - delta size: {len(data.get('delta', ''))}")
        
        # Handle log events first
        if event_type in [event.value for event in self.log_event_types]:
            await self.handle_log_event(data)
            return
        
        # Dispatch to the appropriate handler
        handler = self.realtime_handlers.get(event_type)
        if handler:
            try:
                # Special logging for function call events
                if event_type in [
                    "response.function_call_arguments.delta",
                    "response.function_call_arguments.done",
                ]:
                    logger.info(f"🎯 Routing {event_type} to handler")
                
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
        else:
            logger.warning(f"Unknown OpenAI event type: {event_type}")
            logger.info(f"Unknown event data: {json.dumps(data, indent=2)}")
    
    async def handle_log_event(self, data: Dict[str, Any]) -> None:
        """Handle a log event.
        
        Args:
            data: The log event data
        """
        event_type = data["type"]
        
        # Enhanced error logging
        if event_type == "error":
            error_code = data.get("code", "unknown")
            error_message = data.get("message", "No message provided")
            error_details = data.get("details", {})
            logger.error(f"ERROR DETAILS: code={error_code}, message='{error_message}'")
            if error_details:
                logger.error(f"ERROR ADDITIONAL DETAILS: {json.dumps(error_details)}")
            
            # Log the full error response for debugging
            logger.error(f"FULL ERROR RESPONSE: {json.dumps(data)}")
        
        # Handle response.done events to check for quota issues
        elif event_type == "response.done":
            response_data = data.get("response", {})
            status = response_data.get("status")
            status_details = response_data.get("status_details", {})
            
            if status == "failed":
                error_info = status_details.get("error", {})
                error_type = error_info.get("type")
                error_code = error_info.get("code")
                
                if error_type == "insufficient_quota" or error_code == "insufficient_quota":
                    logger.error("=" * 80)
                    logger.error("🚨 OPENAI API QUOTA EXCEEDED")
                    logger.error("=" * 80)
                    logger.error("❌ Your OpenAI API quota has been exceeded!")
                    logger.error("")
                    logger.error("💡 WHAT THIS MEANS:")
                    logger.error("   • You've run out of API credits or hit your usage limit")
                    logger.error("   • The Realtime API is expensive and uses credits quickly")
                    logger.error("   • No audio will be generated until this is resolved")
                    logger.error("")
                    logger.error("🔧 HOW TO FIX:")
                    logger.error("   1. Check your OpenAI billing: https://platform.openai.com/account/billing")
                    logger.error("   2. Add more credits to your account")
                    logger.error("   3. Check/increase your usage limits")
                    logger.error("   4. Consider upgrading your OpenAI plan if needed")
                    logger.error("")
                    logger.error("📊 USAGE INFO:")
                    usage = response_data.get("usage", {})
                    if usage:
                        logger.error(f"   • Total tokens in this request: {usage.get('total_tokens', 0)}")
                        logger.error(f"   • Input tokens: {usage.get('input_tokens', 0)}")
                        logger.error(f"   • Output tokens: {usage.get('output_tokens', 0)}")
                    logger.error("")
                    logger.error("⚠️  The bridge will now close this session to avoid hanging.")
                    logger.error("   Please resolve your billing issue and restart the validation.")
                    logger.error("=" * 80)
                    # Note: The actual closing of the bridge should be handled by the bridge class
                else:
                    logger.error(f"Response failed with error: {error_info.get('message', 'Unknown error')}")
                    logger.error(f"Error type: {error_type}, Error code: {error_code}") 