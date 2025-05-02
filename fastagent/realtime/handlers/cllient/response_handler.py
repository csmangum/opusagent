"""
Handler for response events.

Response events manage the model's responses to conversation items:

- response.create: Create a new model response
- response.cancel: Cancel an active response

The model can respond with different types of content:
- Text: Regular text responses
- Audio: Spoken responses (if audio modality is enabled)
- Function calls: Calls to external functions
- Function call outputs: Results of function calls

Responses can be in progress, completed, or cancelled.
"""

from typing import Any, Dict, Optional, Callable, Awaitable, List
import time
import asyncio
from fastagent.models.openai_api import (
    ResponseCreateEvent,
    ResponseCancelEvent,
    ResponseCreateOptions
)

class ResponseHandler:
    def __init__(
        self,
        send_event_callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ):
        """
        Initialize the response handler.
        
        Args:
            send_event_callback: Callback function to send events back to the server
        """
        self.send_event = send_event_callback
        self.active_responses: Dict[str, Dict[str, Any]] = {}  # Store active responses by ID
        self._response_tasks: Dict[str, asyncio.Task] = {}  # Store response generation tasks
        
    async def handle_create(self, event: Dict[str, Any]) -> None:
        """
        Handle the response.create event.
        
        This creates a new model response.
        
        Args:
            event: The response.create event data containing:
                - event_id: Optional client-generated ID for the event
                - type: Must be "response.create"
                - response: Response parameters including modalities, instructions, etc.
        """
        try:
            create_event = ResponseCreateEvent(**event)
            response_id = f"response_{len(self.active_responses) + 1}"  # Generate a unique ID
            
            # Create the response
            new_response = {
                "id": response_id,
                "status": "in_progress",
                "created_at": int(time.time() * 1000),  # Current timestamp in milliseconds
                "modalities": create_event.response.modalities,
                "instructions": create_event.response.instructions,
                "voice": create_event.response.voice,
                "output_audio_format": create_event.response.output_audio_format,
                "tools": create_event.response.tools,
                "tool_choice": create_event.response.tool_choice,
                "temperature": create_event.response.temperature,
                "max_output_tokens": create_event.response.max_output_tokens
            }
            
            self.active_responses[response_id] = new_response
            
            # Send response.created event
            await self.send_event({
                "type": "response.created",
                "event_id": event.get("event_id"),
                "response": new_response
            })
            
            # Start response generation task
            task = asyncio.create_task(self._generate_response(
                response_id,
                event.get("event_id"),
                create_event.response
            ))
            self._response_tasks[response_id] = task
            
        except Exception as e:
            await self._send_error_response(
                event.get("event_id"),
                "invalid_request_error",
                f"Failed to create response: {str(e)}"
            )
            
    async def handle_cancel(self, event: Dict[str, Any]) -> None:
        """
        Handle the response.cancel event.
        
        This cancels an active response.
        
        Args:
            event: The response.cancel event data containing:
                - event_id: Optional client-generated ID for the event
                - type: Must be "response.cancel"
                - response_id: Optional ID of the response to cancel
        """
        try:
            cancel_event = ResponseCancelEvent(**event)
            response_id = cancel_event.response_id
            
            # If no response_id provided, cancel the most recent active response
            if not response_id:
                if not self.active_responses:
                    await self._send_error_response(
                        event.get("event_id"),
                        "invalid_request_error",
                        "No active responses to cancel"
                    )
                    return
                response_id = list(self.active_responses.keys())[-1]
            
            if response_id not in self.active_responses:
                await self._send_error_response(
                    event.get("event_id"),
                    "invalid_request_error",
                    f"Response {response_id} not found"
                )
                return
                
            # Cancel the response task if it exists
            if response_id in self._response_tasks:
                self._response_tasks[response_id].cancel()
                del self._response_tasks[response_id]
            
            # Update response status
            self.active_responses[response_id]["status"] = "cancelled"
            
            await self.send_event({
                "type": "response.cancelled",
                "event_id": event.get("event_id"),
                "response_id": response_id
            })
            
            # Remove the response from active responses
            del self.active_responses[response_id]
            
        except Exception as e:
            await self._send_error_response(
                event.get("event_id"),
                "internal_error",
                f"Failed to cancel response: {str(e)}"
            )
            
    async def _generate_response(
        self,
        response_id: str,
        event_id: Optional[str],
        options: ResponseCreateOptions
    ) -> None:
        """Generate a response with streaming content."""
        try:
            # Here you would implement the actual response generation logic
            # This is a placeholder that demonstrates the event flow
            
            # Simulate text streaming
            if "text" in options.modalities:
                text = "This is a sample response."
                for i in range(len(text)):
                    await self.send_event({
                        "type": "response.text.delta",
                        "event_id": event_id,
                        "delta": text[i]
                    })
            
            # Simulate audio streaming
            if "audio" in options.modalities:
                # Simulate audio chunks
                for i in range(3):
                    await self.send_event({
                        "type": "response.audio.delta",
                        "event_id": event_id,
                        "delta": f"audio_chunk_{i}"  # Base64 encoded audio data
                    })
            
            # Simulate function call if tools are provided
            if options.tools:
                await self.send_event({
                    "type": "response.content_part.added",
                    "response_id": response_id,
                    "item_id": f"item_{response_id}",
                    "output_index": 0,
                    "content_index": 0,
                    "part": {
                        "type": "function_call",
                        "name": "example_function",
                        "arguments": {"arg1": "value1"}
                    }
                })
                
                # Simulate function result
                await self.send_event({
                    "type": "response.content_part.done",
                    "event_id": event_id,
                    "response_id": response_id,
                    "item_id": f"item_{response_id}",
                    "output_index": 0,
                    "content_index": 0,
                    "part": {
                        "type": "function_result",
                        "name": "example_function",
                        "content": "Function result"
                    }
                })
            
            # Mark response as complete
            await self._complete_response(response_id, event_id)
            
        except asyncio.CancelledError:
            # Handle cancellation
            await self.send_event({
                "type": "response.cancelled",
                "event_id": event_id,
                "response_id": response_id
            })
        except Exception as e:
            await self._send_error_response(
                event_id,
                "internal_error",
                f"Failed to generate response: {str(e)}"
            )
            
    async def _complete_response(self, response_id: str, event_id: Optional[str]) -> None:
        """Complete a response by sending the done event."""
        if response_id in self.active_responses:
            self.active_responses[response_id]["status"] = "completed"
            
            await self.send_event({
                "type": "response.done",
                "event_id": event_id,
                "response_id": response_id
            })
            
            # Clean up
            if response_id in self._response_tasks:
                del self._response_tasks[response_id]
            del self.active_responses[response_id]
            
    async def _send_error_response(
        self, 
        event_id: Optional[str], 
        code: str, 
        message: str
    ) -> None:
        """Send an error response."""
        await self.send_event({
            "type": "error",
            "event_id": event_id,
            "code": code,
            "message": message
        }) 