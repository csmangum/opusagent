#!/usr/bin/env python3
"""
MockRealtimeClient - Simulates OpenAI Realtime API for testing

This client simulates the OpenAI Realtime API WebSocket connection,
allowing for testing without an actual API connection.
"""

import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable

import websockets
from websockets.asyncio.client import ClientConnection
from pydantic import BaseModel, Field

from opusagent.models.openai_api import (
    ClientEventType,
    MessageRole,
    RealtimeBaseMessage,
    RealtimeMessage,
    RealtimeMessageContent,
    RealtimeStreamMessage,
    ResponseCreateOptions,
    ServerEventType,
    SessionConfig,
)


class MockRealtimeClient:
    """
    Mock client that simulates OpenAI Realtime API.

    This client simulates the WebSocket connection and event handling
    of the OpenAI Realtime API, allowing for testing without an actual
    API connection.
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        session_config: Optional[SessionConfig] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.session_config = session_config or SessionConfig()
        
        # Session state
        self.session_id = str(uuid.uuid4())
        self.conversation_id = str(uuid.uuid4())
        self.connected = False
        self._ws: Optional[ClientConnection] = None
        
        # Event handling
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._response_queue: asyncio.Queue = asyncio.Queue()
        
        # Audio handling
        self._audio_buffer: List[bytes] = []
        self._speech_detected = False
        
        # Response state
        self._active_response_id: Optional[str] = None
        self._response_text = ""
        self._response_audio: List[bytes] = []
        
        # Register default event handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default event handlers."""
        self.register_event_handler(ClientEventType.SESSION_UPDATE, self._handle_session_update)
        self.register_event_handler(ClientEventType.INPUT_AUDIO_BUFFER_APPEND, self._handle_audio_append)
        self.register_event_handler(ClientEventType.INPUT_AUDIO_BUFFER_COMMIT, self._handle_audio_commit)
        self.register_event_handler(ClientEventType.INPUT_AUDIO_BUFFER_CLEAR, self._handle_audio_clear)
        self.register_event_handler(ClientEventType.RESPONSE_CREATE, self._handle_response_create)
        self.register_event_handler(ClientEventType.RESPONSE_CANCEL, self._handle_response_cancel)

    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def connect(self, url: str = "ws://localhost:8080"):
        """Connect to the mock server."""
        self.logger.info(f"[MOCK REALTIME] Connecting to {url}...")
        self._ws = await websockets.connect(url)
        self.connected = True
        self.logger.info("[MOCK REALTIME] Connected")
        
        # Start message handler
        asyncio.create_task(self._message_handler())
        
        # Send session created event
        await self._send_session_created()

    async def disconnect(self):
        """Disconnect from the mock server."""
        if self._ws:
            await self._ws.close()
            self.connected = False
            self.logger.info("[MOCK REALTIME] Disconnected")

    async def _message_handler(self):
        """Handle incoming messages."""
        if not self._ws:
            return
            
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    event_type = data.get("type")
                    
                    if event_type in self._event_handlers:
                        for handler in self._event_handlers[event_type]:
                            await handler(data)
                    else:
                        self.logger.warning(f"[MOCK REALTIME] No handler for event type: {event_type}")
                        
                except json.JSONDecodeError:
                    self.logger.warning(f"[MOCK REALTIME] Received non-JSON message: {message}")
                except Exception as e:
                    self.logger.error(f"[MOCK REALTIME] Error processing message: {e}")
                    
        except websockets.ConnectionClosed:
            self.logger.info("[MOCK REALTIME] Connection closed")
        except Exception as e:
            self.logger.error(f"[MOCK REALTIME] Message handler error: {e}")

    async def _send_session_created(self):
        """Send session.created event."""
        event = {
            "type": ServerEventType.SESSION_CREATED,
            "session": {
                "id": self.session_id,
                "created_at": int(datetime.now().timestamp() * 1000),
                "modalities": self.session_config.modalities,
                "model": self.session_config.model,
                "instructions": self.session_config.instructions,
                "voice": self.session_config.voice,
                "input_audio_format": self.session_config.input_audio_format,
                "output_audio_format": self.session_config.output_audio_format,
                "turn_detection": self.session_config.turn_detection,
                "tools": self.session_config.tools,
                "tool_choice": self.session_config.tool_choice,
                "temperature": self.session_config.temperature,
                "max_response_output_tokens": self.session_config.max_response_output_tokens,
                "input_audio_transcription": self.session_config.input_audio_transcription,
                "input_audio_noise_reduction": self.session_config.input_audio_noise_reduction,
            }
        }
        await self._send_event(event)

    async def _send_event(self, event: Dict[str, Any]):
        """Send an event to the client."""
        if self._ws:
            await self._ws.send(json.dumps(event))

    async def _handle_session_update(self, data: Dict[str, Any]):
        """Handle session.update event."""
        session = data.get("session", {})
        self.session_config = SessionConfig(**session)
        
        # Send session.updated event
        event = {
            "type": ServerEventType.SESSION_UPDATED,
            "session": session
        }
        await self._send_event(event)

    async def _handle_audio_append(self, data: Dict[str, Any]):
        """Handle input_audio_buffer.append event."""
        audio = data.get("audio")
        if audio:
            audio_bytes = base64.b64decode(audio)
            self._audio_buffer.append(audio_bytes)
            
            # Simulate speech detection
            if not self._speech_detected and len(self._audio_buffer) > 10:
                self._speech_detected = True
                event = {
                    "type": ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED,
                    "audio_start_ms": 0,
                    "item_id": str(uuid.uuid4())
                }
                await self._send_event(event)

    async def _handle_audio_commit(self, data: Dict[str, Any]):
        """Handle input_audio_buffer.commit event."""
        if self._audio_buffer:
            # Create a new conversation item
            item_id = str(uuid.uuid4())
            
            # Send committed event
            event = {
                "type": ServerEventType.INPUT_AUDIO_BUFFER_COMMITTED,
                "item_id": item_id
            }
            await self._send_event(event)
            
            # Clear buffer
            self._audio_buffer.clear()
            self._speech_detected = False

    async def _handle_audio_clear(self, data: Dict[str, Any]):
        """Handle input_audio_buffer.clear event."""
        self._audio_buffer.clear()
        self._speech_detected = False
        
        event = {
            "type": ServerEventType.INPUT_AUDIO_BUFFER_CLEARED
        }
        await self._send_event(event)

    async def _handle_response_create(self, data: Dict[str, Any]):
        """Handle response.create event."""
        response = data.get("response", {})
        self._active_response_id = str(uuid.uuid4())
        
        # Send response.created event
        event = {
            "type": ServerEventType.RESPONSE_CREATED,
            "response": {
                "id": self._active_response_id,
                "created_at": int(datetime.now().timestamp() * 1000)
            }
        }
        await self._send_event(event)
        
        # Start response generation
        asyncio.create_task(self._generate_response(response))

    async def _handle_response_cancel(self, data: Dict[str, Any]):
        """Handle response.cancel event."""
        response_id = data.get("response_id")
        if response_id == self._active_response_id:
            self._active_response_id = None
            
            event = {
                "type": ServerEventType.RESPONSE_CANCELLED,
                "response_id": response_id
            }
            await self._send_event(event)

    async def _generate_response(self, response: Dict[str, Any]):
        """Generate a mock response."""
        try:
            # Simulate response generation
            await asyncio.sleep(0.5)
            
            # Get response options
            options = ResponseCreateOptions(**response)
            
            # Handle function calls if tools are enabled
            if options.tools and options.tool_choice != "none":
                await self._generate_function_call(options)
                return
            
            # Generate text response
            if "text" in options.modalities:
                await self._generate_text_response(options)
            
            # Generate audio response
            if "audio" in options.modalities:
                await self._generate_audio_response(options)
            
            # Send response done
            event = {
                "type": ServerEventType.RESPONSE_DONE,
                "response": {
                    "id": self._active_response_id,
                    "created_at": int(datetime.now().timestamp() * 1000)
                }
            }
            await self._send_event(event)
            
        except Exception as e:
            self.logger.error(f"[MOCK REALTIME] Error generating response: {e}")
            
        finally:
            self._active_response_id = None

    async def _generate_text_response(self, options: ResponseCreateOptions):
        """Generate a text response."""
        # Send text deltas
        text = "This is a mock text response from the OpenAI Realtime API."
        for char in text:
            event = {
                "type": ServerEventType.RESPONSE_TEXT_DELTA,
                "response_id": self._active_response_id,
                "item_id": str(uuid.uuid4()),
                "output_index": 0,
                "content_index": 0,
                "delta": char
            }
            await self._send_event(event)
            await asyncio.sleep(0.05)
        
        # Send text done
        event = {
            "type": ServerEventType.RESPONSE_TEXT_DONE,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "content_index": 0,
            "text": text
        }
        await self._send_event(event)

    async def _generate_audio_response(self, options: ResponseCreateOptions):
        """Generate an audio response."""
        # Create mock audio data (silence)
        sample_rate = 16000
        duration = 2.0  # seconds
        num_samples = int(sample_rate * duration)
        audio_data = bytes([0] * num_samples * 2)  # 16-bit PCM
        
        # Split into chunks
        chunk_size = 3200  # 200ms chunks
        chunks = [audio_data[i:i + chunk_size] for i in range(0, len(audio_data), chunk_size)]
        
        # Send audio deltas
        for chunk in chunks:
            event = {
                "type": ServerEventType.RESPONSE_AUDIO_DELTA,
                "response_id": self._active_response_id,
                "item_id": str(uuid.uuid4()),
                "output_index": 0,
                "content_index": 0,
                "delta": base64.b64encode(chunk).decode("utf-8")
            }
            await self._send_event(event)
            await asyncio.sleep(0.2)
        
        # Send audio done
        event = {
            "type": ServerEventType.RESPONSE_AUDIO_DONE,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "content_index": 0
        }
        await self._send_event(event)

    async def _generate_function_call(self, options: ResponseCreateOptions):
        """Generate a function call response."""
        # Select a random function from available tools
        if not options.tools:
            return
            
        function = options.tools[0]
        function_name = function.get("name", "mock_function")
        
        # Generate function call arguments
        arguments = {
            "param1": "value1",
            "param2": "value2"
        }
        
        # Send function call arguments delta
        event = {
            "type": ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "call_id": str(uuid.uuid4()),
            "delta": json.dumps(arguments)
        }
        await self._send_event(event)
        
        # Send function call arguments done
        event = {
            "type": ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "call_id": str(uuid.uuid4()),
            "arguments": json.dumps(arguments)
        }
        await self._send_event(event)

    async def send_transcript_delta(self, text: str, final: bool = False):
        """Send a transcript delta event."""
        event = {
            "type": ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "content_index": 0,
            "delta": text
        }
        await self._send_event(event)
        
        if final:
            event = {
                "type": ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DONE,
                "response_id": self._active_response_id,
                "item_id": str(uuid.uuid4()),
                "output_index": 0,
                "content_index": 0,
                "transcript": text
            }
            await self._send_event(event)

    async def send_input_transcript_delta(self, item_id: str, text: str, final: bool = False):
        """Send an input audio transcription delta event."""
        event = {
            "type": ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_DELTA,
            "item_id": item_id,
            "content_index": 0,
            "delta": text
        }
        await self._send_event(event)
        
        if final:
            event = {
                "type": ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED,
                "item_id": item_id,
                "content_index": 0,
                "transcript": text
            }
            await self._send_event(event)

    async def send_input_transcript_failed(self, item_id: str, error: Dict[str, Any]):
        """Send an input audio transcription failed event."""
        event = {
            "type": ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_FAILED,
            "item_id": item_id,
            "content_index": 0,
            "error": error
        }
        await self._send_event(event)

    async def send_output_item_added(self, item: Dict[str, Any]):
        """Send an output item added event."""
        event = {
            "type": ServerEventType.RESPONSE_OUTPUT_ITEM_ADDED,
            "response_id": self._active_response_id,
            "output_index": 0,
            "item": item
        }
        await self._send_event(event)

    async def send_output_item_done(self, item: Dict[str, Any]):
        """Send an output item done event."""
        event = {
            "type": ServerEventType.RESPONSE_OUTPUT_ITEM_DONE,
            "response_id": self._active_response_id,
            "output_index": 0,
            "item": item
        }
        await self._send_event(event)

    async def send_content_part_added(self, part: Dict[str, Any]):
        """Send a content part added event."""
        event = {
            "type": ServerEventType.RESPONSE_CONTENT_PART_ADDED,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "content_index": 0,
            "part": part
        }
        await self._send_event(event)

    async def send_content_part_done(self, part: Dict[str, Any], status: str = "completed"):
        """Send a content part done event."""
        event = {
            "type": ServerEventType.RESPONSE_CONTENT_PART_DONE,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "content_index": 0,
            "part_id": str(uuid.uuid4()),
            "status": status,
            "part": part
        }
        await self._send_event(event)

    async def send_error(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Send an error event."""
        event = {
            "type": ServerEventType.ERROR,
            "code": code,
            "message": message,
            "details": details
        }
        await self._send_event(event)

    async def send_rate_limits(self, limits: List[Dict[str, Any]]):
        """Send rate limits update."""
        event = {
            "type": ServerEventType.RATE_LIMITS_UPDATED,
            "rate_limits": limits
        }
        await self._send_event(event) 