"""
Handler for server error events.

This module contains the handler for processing error events received from the OpenAI Realtime API.
"""

import logging
from typing import Any, Callable, Dict, Optional

from fastagent.realtime.handlers.server.base_handler import BaseServerHandler

class ErrorHandler(BaseServerHandler):
    """Handler for server error events.
    
    This handler processes error events from the OpenAI Realtime API server.
    """
    
    async def handle_error(self, event_data: Dict[str, Any]) -> None:
        """Handle an error event.
        
        Args:
            event_data: The error event data
        """
        error = event_data.get("error", {})
        
        # Extract error details
        error_type = error.get("type", "unknown_error_type")
        error_code = error.get("code", "unknown_error_code")
        error_message = error.get("message", "Unknown error")
        error_param = error.get("param")
        error_details = error.get("details")
        
        # Log the error with different levels based on severity
        if error_type in ["server_error", "internal_server_error"]:
            self.logger.error(f"Server error: {error_code} - {error_message}")
        elif error_type in ["rate_limit_error"]:
            self.logger.warning(f"Rate limit error: {error_code} - {error_message}")
        else:
            self.logger.info(f"API error: {error_type} - {error_code} - {error_message}")
            
        # Log additional details if available
        if error_param:
            self.logger.debug(f"Error param: {error_param}")
        if error_details:
            self.logger.debug(f"Error details: {error_details}")
            
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for error event: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}") 