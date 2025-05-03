"""
Handler for server output audio buffer events.

This module contains the handler for processing output audio buffer-related events 
received from the OpenAI Realtime API, specifically for WebRTC connections.
"""

from typing import Any, Dict

from fastagent.realtime.handlers.server.base_handler import BaseServerHandler

class OutputAudioBufferHandler(BaseServerHandler):
    """Handler for server output audio buffer events.
    
    This handler processes output audio buffer-related events from the OpenAI Realtime API server,
    including buffer start, stop, and clear events for WebRTC connections.
    """
    
    async def handle_started(self, event_data: Dict[str, Any]) -> None:
        """Handle an output_audio_buffer.started event.
        
        Args:
            event_data: The output audio buffer started event data
        """
        response_id = event_data.get("response_id")
        
        self.logger.info(f"Output audio buffer started for response {response_id}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for output_audio_buffer.started: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_stopped(self, event_data: Dict[str, Any]) -> None:
        """Handle an output_audio_buffer.stopped event.
        
        Args:
            event_data: The output audio buffer stopped event data
        """
        response_id = event_data.get("response_id")
        
        self.logger.info(f"Output audio buffer stopped for response {response_id}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for output_audio_buffer.stopped: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_cleared(self, event_data: Dict[str, Any]) -> None:
        """Handle an output_audio_buffer.cleared event.
        
        Args:
            event_data: The output audio buffer cleared event data
        """
        response_id = event_data.get("response_id")
        
        self.logger.info(f"Output audio buffer cleared for response {response_id}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for output_audio_buffer.cleared: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}") 