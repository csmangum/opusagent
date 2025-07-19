"""
Message handler for processing WebSocket messages from TelephonyRealtimeBridge.

This module processes incoming messages and routes them to appropriate handlers
based on message type and content.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Callable, List, Union, Awaitable
from datetime import datetime

logger = logging.getLogger(__name__)

class MessageHandler:
    """Handles WebSocket message processing and routing."""
    
    def __init__(self):
        # Message type handlers
        self._session_handlers: List[Union[Callable[[str, Dict[str, Any]], None], Callable[[str, Dict[str, Any]], Awaitable[None]]]] = []
        self._audio_handlers: List[Union[Callable[[str, Dict[str, Any]], None], Callable[[str, Dict[str, Any]], Awaitable[None]]]] = []
        self._error_handlers: List[Union[Callable[[Dict[str, Any]], None], Callable[[Dict[str, Any]], Awaitable[None]]]] = []
        self._general_handlers: List[Union[Callable[[Dict[str, Any]], None], Callable[[Dict[str, Any]], Awaitable[None]]]] = []
        
        # Message statistics
        self.message_count = 0
        self.error_count = 0
        self.session_events = 0
        self.audio_events = 0
        
        # Session state tracking
        self.current_session_id: Optional[str] = None
        self.current_conversation_id: Optional[str] = None
        self.session_active = False
        
    def add_session_handler(self, handler: Union[Callable[[str, Dict[str, Any]], None], Callable[[str, Dict[str, Any]], Awaitable[None]]]) -> None:
        """Add a handler for session events."""
        self._session_handlers.append(handler)
    
    def add_audio_handler(self, handler: Union[Callable[[str, Dict[str, Any]], None], Callable[[str, Dict[str, Any]], Awaitable[None]]]) -> None:
        """Add a handler for audio events."""
        self._audio_handlers.append(handler)
    
    def add_error_handler(self, handler: Union[Callable[[Dict[str, Any]], None], Callable[[Dict[str, Any]], Awaitable[None]]]) -> None:
        """Add a handler for error events."""
        self._error_handlers.append(handler)
    
    def add_general_handler(self, handler: Union[Callable[[Dict[str, Any]], None], Callable[[Dict[str, Any]], Awaitable[None]]]) -> None:
        """Add a general message handler."""
        self._general_handlers.append(handler)
    
    async def handle_message(self, message: Dict[str, Any]) -> None:
        """Main message processing entry point."""
        try:
            self.message_count += 1
            
            # Extract message type
            message_type = message.get("type", "unknown")
            
            logger.debug(f"Processing message: {message_type}")
            
            # Route message based on type
            if message_type.startswith("session."):
                await self._handle_session_message(message_type, message)
            elif message_type.startswith(("userStream.", "playStream.")):
                await self._handle_audio_message(message_type, message)
            elif message_type == "error":
                await self._handle_error_message(message)
            else:
                await self._handle_general_message(message)
                
            # Call general handlers for all messages
            for handler in self._general_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                except Exception as e:
                    logger.error(f"Error in general handler: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.error_count += 1
    
    async def _handle_session_message(self, message_type: str, message: Dict[str, Any]) -> None:
        """Handle session-related messages."""
        self.session_events += 1
        
        # Update session state
        if message_type == "session.initiate":
            self.current_conversation_id = message.get("conversationId")
            logger.info(f"Session initiate: {self.current_conversation_id}")
            
        elif message_type == "session.accepted":
            self.session_active = True
            self.current_session_id = message.get("sessionId")
            logger.info(f"Session accepted: {self.current_session_id}")
            
        elif message_type == "session.end":
            self.session_active = False
            self.current_session_id = None
            self.current_conversation_id = None
            logger.info("Session ended")
        
        # Call session handlers
        for handler in self._session_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message_type, message)
                else:
                    handler(message_type, message)
            except Exception as e:
                logger.error(f"Error in session handler: {e}")
    
    async def _handle_audio_message(self, message_type: str, message: Dict[str, Any]) -> None:
        """Handle audio stream messages."""
        self.audio_events += 1
        
        # Log audio events (but not chunks to avoid spam)
        if not message_type.endswith(".chunk"):
            logger.debug(f"Audio event: {message_type}")
        
        # Call audio handlers
        for handler in self._audio_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message_type, message)
                else:
                    handler(message_type, message)
            except Exception as e:
                logger.error(f"Error in audio handler: {e}")
    
    async def _handle_error_message(self, message: Dict[str, Any]) -> None:
        """Handle error messages."""
        self.error_count += 1
        
        error_code = message.get("error", {}).get("code", "unknown")
        error_message = message.get("error", {}).get("message", "Unknown error")
        
        logger.error(f"Error received: {error_code} - {error_message}")
        
        # Call error handlers
        for handler in self._error_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Error in error handler: {e}")
    
    async def _handle_general_message(self, message: Dict[str, Any]) -> None:
        """Handle general/unknown messages."""
        message_type = message.get("type", "unknown")
        logger.debug(f"General message: {message_type}")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information."""
        return {
            "session_id": self.current_session_id,
            "conversation_id": self.current_conversation_id,
            "session_active": self.session_active,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "session_events": self.session_events,
            "audio_events": self.audio_events,
        }
    
    def reset_session(self) -> None:
        """Reset session state."""
        self.current_session_id = None
        self.current_conversation_id = None
        self.session_active = False
    
    def reset_stats(self) -> None:
        """Reset message statistics."""
        self.message_count = 0
        self.error_count = 0
        self.session_events = 0
        self.audio_events = 0


class SessionMessageBuilder:
    """Helper class for building session messages."""
    
    @staticmethod
    def create_session_initiate(conversation_id: str, bot_name: str = "voice-bot", 
                              caller: str = "tui-validator", 
                              media_formats: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a session.initiate message."""
        if media_formats is None:
            media_formats = ["raw/lpcm16"]
            
        return {
            "type": "session.initiate",
            "conversationId": conversation_id,
            "botName": bot_name,
            "caller": caller,
            "expectAudioMessages": True,
            "supportedMediaFormats": media_formats
        }
    
    @staticmethod
    def create_session_end(conversation_id: str) -> Dict[str, Any]:
        """Create a session.end message."""
        return {
            "type": "session.end",
            "conversationId": conversation_id
        }
    
    @staticmethod
    def create_user_stream_start(conversation_id: str, 
                               media_format: str = "raw/lpcm16") -> Dict[str, Any]:
        """Create a userStream.start message."""
        return {
            "type": "userStream.start",
            "conversationId": conversation_id,
            "mediaFormat": media_format
        }
    
    @staticmethod
    def create_user_stream_chunk(conversation_id: str, 
                               audio_chunk: str) -> Dict[str, Any]:
        """Create a userStream.chunk message."""
        return {
            "type": "userStream.chunk",
            "conversationId": conversation_id,
            "audioChunk": audio_chunk
        }
    
    @staticmethod
    def create_user_stream_stop(conversation_id: str) -> Dict[str, Any]:
        """Create a userStream.stop message."""
        return {
            "type": "userStream.stop",
            "conversationId": conversation_id
        }


# Import asyncio for coroutine checks
import asyncio 