"""
Handler for server session events.

This module contains the handler for processing session-related events 
received from the OpenAI Realtime API.
"""

from typing import Any, Dict, Optional, Callable

from opusagent.realtime.handlers.server.base_handler import BaseServerHandler

class SessionHandler(BaseServerHandler):
    """Handler for server session events.
    
    This handler processes session-related events from the OpenAI Realtime API server,
    including session creation and updates.
    """
    
    async def handle_created(self, event_data: Dict[str, Any]) -> None:
        """Handle a session.created event.
        
        Args:
            event_data: The session created event data
        """
        session = event_data.get("session", {})
        session_id = session.get("id")
        model = session.get("model")
        
        self.logger.info(f"Session created: {session_id} with model {model}")
        self.logger.debug(f"Session details: {session}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for session.created: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_updated(self, event_data: Dict[str, Any]) -> None:
        """Handle a session.updated event.
        
        Args:
            event_data: The session updated event data
        """
        session = event_data.get("session", {})
        session_id = session.get("id")
        
        self.logger.info(f"Session updated: {session_id}")
        self.logger.debug(f"Updated session details: {session}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for session.updated: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}") 