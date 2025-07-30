"""Event router for handling telephony and realtime events.

This module provides a centralized event routing system for handling events
from both telephony and OpenAI Realtime API sources.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional, List, Tuple

from opusagent.config.logging_config import configure_logging
from opusagent.models.audiocodes_api import TelephonyEventType
from opusagent.models.openai_api import LogEventType, ServerEventType

logger = configure_logging("event_router")

class EventRouter:
    """Router class for handling events from telephony and realtime sources.
    
    This class manages event routing and handling for both telephony and OpenAI Realtime API events.
    It provides a centralized way to register and dispatch event handlers with support for multiple
    handlers per event type, priority ordering, and handler chaining.
    
    Enhanced Features:
    - Multiple handlers per event type with priority ordering
    - Handler chaining with data passing between handlers
    - Event filtering and transformation
    - Handler lifecycle management
    - Error isolation to prevent handler failures from affecting other handlers
    
    Attributes:
        telephony_handlers (Dict[TelephonyEventType, List[Tuple[int, Callable]]]): Priority-ordered handlers for telephony events
        realtime_handlers (Dict[str, List[Tuple[int, Callable]]]): Priority-ordered handlers for realtime events
        log_event_types (List[LogEventType]): Types of log events to handle
        _handler_middleware (List[Callable]): Middleware functions for event processing
    """
    
    def __init__(self):
        """Initialize the event router."""
        self.telephony_handlers: Dict[TelephonyEventType, List[Tuple[int, Callable]]] = {}
        self.realtime_handlers: Dict[str, List[Tuple[int, Callable]]] = {}
        self._handler_middleware: List[Callable] = []
        self.log_event_types = [
            LogEventType.ERROR,
            LogEventType.RESPONSE_CONTENT_DONE,
            LogEventType.RATE_LIMITS_UPDATED,
            LogEventType.INPUT_AUDIO_BUFFER_COMMITTED,
            LogEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED,
            LogEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED,
        ]
    
    def register_platform_handler(
        self, 
        event_type: TelephonyEventType, 
        handler: Callable,
        priority: int = 0
    ) -> None:
        """Register a handler for a telephony event type.
        
        Args:
            event_type: The telephony event type to handle
            handler: The handler function to call for this event type
            priority: Handler priority (higher numbers execute first)
        """
        if event_type not in self.telephony_handlers:
            self.telephony_handlers[event_type] = []
        
        self.telephony_handlers[event_type].append((priority, handler))
        self.telephony_handlers[event_type].sort(key=lambda x: x[0], reverse=True)
        logger.debug(f"Registered telephony handler for event type: {event_type} (priority: {priority})")
    
    def register_realtime_handler(
        self, 
        event_type: str, 
        handler: Callable,
        priority: int = 0
    ) -> None:
        """Register a handler for a realtime event type.
        
        Args:
            event_type: The realtime event type to handle
            handler: The handler function to call for this event type
            priority: Handler priority (higher numbers execute first)
        """
        if event_type not in self.realtime_handlers:
            self.realtime_handlers[event_type] = []
        
        self.realtime_handlers[event_type].append((priority, handler))
        self.realtime_handlers[event_type].sort(key=lambda x: x[0], reverse=True)
        logger.debug(f"Registered realtime handler for event type: {event_type} (priority: {priority})")
    
    def unregister_platform_handler(
        self, 
        event_type: TelephonyEventType, 
        handler: Callable
    ) -> bool:
        """Unregister a telephony event handler.
        
        Args:
            event_type: The telephony event type
            handler: The handler function to remove
            
        Returns:
            bool: True if handler was found and removed
        """
        if event_type not in self.telephony_handlers:
            return False
        
        handlers = self.telephony_handlers[event_type]
        for i, (priority, h) in enumerate(handlers):
            if h == handler:
                handlers.pop(i)
                logger.debug(f"Unregistered telephony handler for event type: {event_type}")
                return True
        return False
    
    def unregister_realtime_handler(
        self, 
        event_type: str, 
        handler: Callable
    ) -> bool:
        """Unregister a realtime event handler.
        
        Args:
            event_type: The realtime event type
            handler: The handler function to remove
            
        Returns:
            bool: True if handler was found and removed
        """
        if event_type not in self.realtime_handlers:
            return False
        
        handlers = self.realtime_handlers[event_type]
        for i, (priority, h) in enumerate(handlers):
            if h == handler:
                handlers.pop(i)
                logger.debug(f"Unregistered realtime handler for event type: {event_type}")
                return True
        return False
    
    def register_middleware(self, middleware: Callable, priority: int = 0) -> None:
        """Register middleware for event processing.
        
        Middleware functions are called before event handlers and can modify
        or filter events. They should return the modified event data or None
        to stop processing.
        
        Args:
            middleware: Middleware function that takes (event_type, data) and returns modified data or None
            priority: Middleware priority (higher numbers execute first)
        """
        self._handler_middleware.append((priority, middleware))
        self._handler_middleware.sort(key=lambda x: x[0], reverse=True)
        logger.debug(f"Registered event middleware with priority {priority}")
    
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
            
            # Apply middleware
            processed_data = await self._apply_middleware(msg_type_str, data)
            if processed_data is None:
                logger.debug(f"Event {msg_type_str} filtered out by middleware")
                return
                
            # Dispatch to the appropriate handlers (multiple handlers supported)
            handlers = self.telephony_handlers.get(msg_type, [])
            if handlers:
                await self._execute_handlers(handlers, processed_data, f"platform event {msg_type}")
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
        
        # Apply middleware
        processed_data = await self._apply_middleware(event_type, data)
        if processed_data is None:
            logger.debug(f"Event {event_type} filtered out by middleware")
            return
        
        # Dispatch to the appropriate handlers (multiple handlers supported)
        handlers = self.realtime_handlers.get(event_type, [])
        if handlers:
            # Special logging for function call events
            if event_type in [
                "response.function_call_arguments.delta",
                "response.function_call_arguments.done",
            ]:
                logger.info(f"🎯 Routing {event_type} to {len(handlers)} handler(s)")
            
            await self._execute_handlers(handlers, processed_data, f"realtime event {event_type}")
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
    
    async def _apply_middleware(self, event_type: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Apply middleware functions to event data.
        
        Args:
            event_type: The event type
            data: The event data
            
        Returns:
            Optional[Dict]: Modified event data or None if filtered out
        """
        current_data = data
        
        for priority, middleware in self._handler_middleware:
            try:
                if asyncio.iscoroutinefunction(middleware):
                    result = await middleware(event_type, current_data)
                else:
                    result = middleware(event_type, current_data)
                
                if result is None:
                    # Middleware filtered out the event
                    return None
                
                current_data = result
                
            except Exception as e:
                logger.error(f"Error in event middleware: {e}")
                # Continue with original data if middleware fails
                continue
        
        return current_data
    
    async def _execute_handlers(
        self, 
        handlers: List[Tuple[int, Callable]], 
        data: Dict[str, Any], 
        context: str
    ) -> None:
        """Execute multiple handlers with error isolation.
        
        Args:
            handlers: List of (priority, handler) tuples
            data: Event data to pass to handlers
            context: Context description for error logging
        """
        for priority, handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in {context} handler (priority {priority}): {e}")
                # Continue executing other handlers even if one fails
    
    def get_handler_stats(self) -> Dict[str, Any]:
        """Get statistics about registered handlers.
        
        Returns:
            Dict containing handler statistics
        """
        telephony_count = sum(len(handlers) for handlers in self.telephony_handlers.values())
        realtime_count = sum(len(handlers) for handlers in self.realtime_handlers.values())
        
        return {
            "telephony_handlers": {
                "total": telephony_count,
                "by_type": {
                    event_type.value: len(handlers) 
                    for event_type, handlers in self.telephony_handlers.items()
                }
            },
            "realtime_handlers": {
                "total": realtime_count,
                "by_type": {
                    event_type: len(handlers) 
                    for event_type, handlers in self.realtime_handlers.items()
                }
            },
            "middleware_count": len(self._handler_middleware)
        } 