"""
Handler for server response events.

This module contains the handler for processing response-related events 
received from the OpenAI Realtime API.
"""

from typing import Any, Dict

from fastagent.realtime.handlers.server.base_handler import BaseServerHandler

class ResponseHandler(BaseServerHandler):
    """Handler for server response events.
    
    This handler processes response-related events from the OpenAI Realtime API server,
    including response creation, text/audio deltas, and function call events.
    """
    
    async def handle_created(self, event_data: Dict[str, Any]) -> None:
        """Handle a response.created event.
        
        Args:
            event_data: The response created event data
        """
        response = event_data.get("response", {})
        response_id = response.get("id")
        status = response.get("status")
        
        self.logger.info(f"Response created: {response_id} with status {status}")
        self.logger.debug(f"Response details: {response}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for response.created: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_done(self, event_data: Dict[str, Any]) -> None:
        """Handle a response.done event.
        
        Args:
            event_data: The response done event data
        """
        response = event_data.get("response", {})
        response_id = response.get("id")
        status = response.get("status")
        usage = response.get("usage", {})
        
        # Log usage details if available
        if usage:
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            
            self.logger.info(
                f"Response {response_id} done with status {status}. "
                f"Usage: {input_tokens} input, {output_tokens} output, {total_tokens} total tokens"
            )
        else:
            self.logger.info(f"Response {response_id} done with status {status}")
            
        self.logger.debug(f"Final response details: {response}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for response.done: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_added(self, event_data: Dict[str, Any]) -> None:
        """Handle a response.output_item.added event.
        
        Args:
            event_data: The output item added event data
        """
        response_id = event_data.get("response_id")
        output_index = event_data.get("output_index")
        item = event_data.get("item", {})
        item_id = item.get("id")
        item_type = item.get("type")
        
        self.logger.info(
            f"Output item added to response {response_id}: {item_id} "
            f"(type: {item_type}, index: {output_index})"
        )
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for response.output_item.added: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_content_part_added(self, event_data: Dict[str, Any]) -> None:
        """Handle a response.content_part.added event.
        
        Args:
            event_data: The content part added event data
        """
        response_id = event_data.get("response_id")
        item_id = event_data.get("item_id")
        output_index = event_data.get("output_index")
        content_index = event_data.get("content_index")
        part = event_data.get("part", {})
        part_type = part.get("type")
        
        self.logger.info(
            f"Content part added to item {item_id} in response {response_id}: "
            f"type {part_type}, indices [{output_index}][{content_index}]"
        )
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for response.content_part.added: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_content_part_done(self, event_data: Dict[str, Any]) -> None:
        """Handle a response.content_part.done event.
        
        Args:
            event_data: The content part done event data
        """
        response_id = event_data.get("response_id")
        item_id = event_data.get("item_id")
        output_index = event_data.get("output_index")
        content_index = event_data.get("content_index")
        part = event_data.get("part", {})
        part_type = part.get("type")
        
        self.logger.info(
            f"Content part completed in item {item_id} of response {response_id}: "
            f"type {part_type}, indices [{output_index}][{content_index}]"
        )
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for response.content_part.done: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_text_delta(self, event_data: Dict[str, Any]) -> None:
        """Handle a response.text.delta event.
        
        Args:
            event_data: The text delta event data
        """
        response_id = event_data.get("response_id")
        item_id = event_data.get("item_id")
        output_index = event_data.get("output_index")
        content_index = event_data.get("content_index")
        delta = event_data.get("delta")
        
        # Use debug level for delta logs to avoid cluttering logs
        self.logger.debug(
            f"Text delta for item {item_id} in response {response_id}: '{delta}'"
        )
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for response.text.delta: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_text_done(self, event_data: Dict[str, Any]) -> None:
        """Handle a response.text.done event.
        
        Args:
            event_data: The text done event data
        """
        response_id = event_data.get("response_id")
        item_id = event_data.get("item_id")
        output_index = event_data.get("output_index")
        content_index = event_data.get("content_index")
        text = event_data.get("text")
        
        # Truncate text if it's too long for logging
        truncated_text = text[:100] + "..." if text and len(text) > 100 else text
        
        self.logger.info(
            f"Text completed for item {item_id} in response {response_id}: '{truncated_text}'"
        )
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for response.text.done: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_audio_transcript_delta(self, event_data: Dict[str, Any]) -> None:
        """Handle a response.audio_transcript.delta event.
        
        Args:
            event_data: The audio transcript delta event data
        """
        response_id = event_data.get("response_id")
        item_id = event_data.get("item_id")
        output_index = event_data.get("output_index")
        content_index = event_data.get("content_index")
        delta = event_data.get("delta")
        
        # Use debug level for delta logs to avoid cluttering logs
        self.logger.debug(
            f"Audio transcript delta for item {item_id} in response {response_id}: '{delta}'"
        )
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for response.audio_transcript.delta: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_audio_transcript_done(self, event_data: Dict[str, Any]) -> None:
        """Handle a response.audio_transcript.done event.
        
        Args:
            event_data: The audio transcript done event data
        """
        response_id = event_data.get("response_id")
        item_id = event_data.get("item_id")
        output_index = event_data.get("output_index")
        content_index = event_data.get("content_index")
        transcript = event_data.get("transcript")
        
        # Truncate transcript if it's too long for logging
        truncated_transcript = transcript[:100] + "..." if transcript and len(transcript) > 100 else transcript
        
        self.logger.info(
            f"Audio transcript completed for item {item_id} in response {response_id}: '{truncated_transcript}'"
        )
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for response.audio_transcript.done: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_audio_delta(self, event_data: Dict[str, Any]) -> None:
        """Handle a response.audio.delta event.
        
        Args:
            event_data: The audio delta event data
        """
        response_id = event_data.get("response_id")
        item_id = event_data.get("item_id")
        output_index = event_data.get("output_index")
        content_index = event_data.get("content_index")
        delta = event_data.get("delta")
        
        # Just log the fact that audio data was received, not the actual data
        delta_size = len(delta) if delta else 0
        self.logger.debug(
            f"Audio delta received for item {item_id} in response {response_id}: {delta_size} bytes"
        )
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for response.audio.delta: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_audio_done(self, event_data: Dict[str, Any]) -> None:
        """Handle a response.audio.done event.
        
        Args:
            event_data: The audio done event data
        """
        response_id = event_data.get("response_id")
        item_id = event_data.get("item_id")
        output_index = event_data.get("output_index")
        content_index = event_data.get("content_index")
        
        self.logger.info(
            f"Audio completed for item {item_id} in response {response_id}"
        )
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for response.audio.done: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_function_call_arguments_delta(self, event_data: Dict[str, Any]) -> None:
        """Handle a response.function_call_arguments.delta event.
        
        Args:
            event_data: The function call arguments delta event data
        """
        response_id = event_data.get("response_id")
        item_id = event_data.get("item_id")
        output_index = event_data.get("output_index")
        call_id = event_data.get("call_id")
        delta = event_data.get("delta")
        
        # Use debug level for delta logs to avoid cluttering logs
        self.logger.debug(
            f"Function call arguments delta for call {call_id} in item {item_id}: '{delta}'"
        )
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for function call arguments delta: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    async def handle_function_call_arguments_done(self, event_data: Dict[str, Any]) -> None:
        """Handle a response.function_call_arguments.done event.
        
        Args:
            event_data: The function call arguments done event data
        """
        response_id = event_data.get("response_id")
        item_id = event_data.get("item_id")
        output_index = event_data.get("output_index")
        call_id = event_data.get("call_id")
        arguments = event_data.get("arguments")
        
        # Truncate arguments if they're too long for logging
        truncated_args = arguments[:100] + "..." if arguments and len(arguments) > 100 else arguments
        
        self.logger.info(
            f"Function call arguments completed for call {call_id} in item {item_id}: {truncated_args}"
        )
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for function call arguments done: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}") 