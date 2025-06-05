"""
Handler for server conversation item events.

This module contains the handler for processing conversation item-related events 
received from the OpenAI Realtime API.
"""

from typing import Any, Dict

from opusagent.realtime.handlers.server.base_handler import BaseServerHandler

class ConversationItemHandler(BaseServerHandler):
    """Handler for server conversation item events.
    
    This handler processes conversation item-related events from the OpenAI Realtime API server,
    such as item creation, retrieval, and transcription events.
    """
    
    async def handle_created(self, event_data: Dict[str, Any]) -> None:
        """Handle a conversation.item.created event.
        
        Args:
            event_data: The conversation item created event data
        """
        item = event_data.get("item", {})
        item_id = item.get("id")
        item_type = item.get("type")
        item_role = item.get("role") if item_type == "message" else None
        previous_item_id = event_data.get("previous_item_id")
        
        self.logger.info(f"Conversation item created: {item_id} (type: {item_type}, role: {item_role})")
        self.logger.debug(f"Item details: {item}, previous item: {previous_item_id}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for conversation.item.created: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_retrieved(self, event_data: Dict[str, Any]) -> None:
        """Handle a conversation.item.retrieved event.
        
        Args:
            event_data: The conversation item retrieved event data
        """
        item = event_data.get("item", {})
        item_id = item.get("id")
        item_type = item.get("type")
        
        self.logger.info(f"Conversation item retrieved: {item_id} (type: {item_type})")
        self.logger.debug(f"Retrieved item details: {item}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for conversation.item.retrieved: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_completed(self, event_data: Dict[str, Any]) -> None:
        """Handle a conversation.item.input_audio_transcription.completed event.
        
        Args:
            event_data: The transcription completed event data
        """
        item_id = event_data.get("item_id")
        content_index = event_data.get("content_index")
        transcript = event_data.get("transcript")
        
        self.logger.info(f"Audio transcription completed for item {item_id}, content index {content_index}")
        self.logger.debug(f"Transcript: {transcript}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for transcription completed: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_delta(self, event_data: Dict[str, Any]) -> None:
        """Handle a conversation.item.input_audio_transcription.delta event.
        
        Args:
            event_data: The transcription delta event data
        """
        item_id = event_data.get("item_id")
        content_index = event_data.get("content_index")
        delta = event_data.get("delta")
        
        self.logger.debug(f"Audio transcription delta for item {item_id}, content index {content_index}: {delta}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for transcription delta: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_failed(self, event_data: Dict[str, Any]) -> None:
        """Handle a conversation.item.input_audio_transcription.failed event.
        
        Args:
            event_data: The transcription failed event data
        """
        item_id = event_data.get("item_id")
        content_index = event_data.get("content_index")
        error = event_data.get("error", {})
        error_code = error.get("code", "unknown_error")
        error_message = error.get("message", "Unknown error")
        
        self.logger.warning(
            f"Audio transcription failed for item {item_id}, content index {content_index}: "
            f"{error_code} - {error_message}"
        )
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for transcription failed: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_truncated(self, event_data: Dict[str, Any]) -> None:
        """Handle a conversation.item.truncated event.
        
        Args:
            event_data: The item truncated event data
        """
        item_id = event_data.get("item_id")
        content_index = event_data.get("content_index")
        audio_end_ms = event_data.get("audio_end_ms")
        
        self.logger.info(
            f"Conversation item {item_id} truncated at {audio_end_ms}ms for content index {content_index}"
        )
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for item truncated: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_deleted(self, event_data: Dict[str, Any]) -> None:
        """Handle a conversation.item.deleted event.
        
        Args:
            event_data: The item deleted event data
        """
        item_id = event_data.get("item_id")
        
        self.logger.info(f"Conversation item deleted: {item_id}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for item deleted: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}") 