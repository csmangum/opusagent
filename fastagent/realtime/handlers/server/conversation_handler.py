"""
Handler for server conversation events.

This module contains the handler for processing conversation-related events 
received from the OpenAI Realtime API.
"""

from typing import Any, Dict

from fastagent.realtime.handlers.server.base_handler import BaseServerHandler

class ConversationHandler(BaseServerHandler):
    """Handler for server conversation events.
    
    This handler processes conversation-related events from the OpenAI Realtime API server,
    such as conversation creation.
    """
    
    async def handle_created(self, event_data: Dict[str, Any]) -> None:
        """Handle a conversation.created event.
        
        Args:
            event_data: The conversation created event data
        """
        conversation = event_data.get("conversation", {})
        conversation_id = conversation.get("id")
        
        self.logger.info(f"Conversation created: {conversation_id}")
        self.logger.debug(f"Conversation details: {conversation}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for conversation.created: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}") 