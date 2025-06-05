"""
Handler for server input audio buffer events.

This module contains the handler for processing input audio buffer-related events 
received from the OpenAI Realtime API.
"""

from typing import Any, Dict

from opusagent.realtime.handlers.server.base_handler import BaseServerHandler

class InputAudioBufferHandler(BaseServerHandler):
    """Handler for server input audio buffer events.
    
    This handler processes input audio buffer-related events from the OpenAI Realtime API server,
    such as buffer commitment, clearing, and speech detection events.
    """
    
    async def handle_committed(self, event_data: Dict[str, Any]) -> None:
        """Handle an input_audio_buffer.committed event.
        
        Args:
            event_data: The input audio buffer committed event data
        """
        item_id = event_data.get("item_id")
        previous_item_id = event_data.get("previous_item_id")
        
        self.logger.info(f"Input audio buffer committed to item {item_id}")
        self.logger.debug(f"Previous item: {previous_item_id}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for input_audio_buffer.committed: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_cleared(self, event_data: Dict[str, Any]) -> None:
        """Handle an input_audio_buffer.cleared event.
        
        Args:
            event_data: The input audio buffer cleared event data
        """
        self.logger.info("Input audio buffer cleared")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for input_audio_buffer.cleared: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_speech_started(self, event_data: Dict[str, Any]) -> None:
        """Handle an input_audio_buffer.speech_started event.
        
        Args:
            event_data: The speech started event data
        """
        item_id = event_data.get("item_id")
        audio_start_ms = event_data.get("audio_start_ms")
        
        self.logger.info(f"Speech detected at {audio_start_ms}ms for future item {item_id}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for input_audio_buffer.speech_started: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_speech_stopped(self, event_data: Dict[str, Any]) -> None:
        """Handle an input_audio_buffer.speech_stopped event.
        
        Args:
            event_data: The speech stopped event data
        """
        item_id = event_data.get("item_id")
        audio_end_ms = event_data.get("audio_end_ms")
        
        self.logger.info(f"Speech ended at {audio_end_ms}ms for item {item_id}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for input_audio_buffer.speech_stopped: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}") 