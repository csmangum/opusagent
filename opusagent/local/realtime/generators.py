"""
Response generators for the LocalRealtime module.

This module provides a comprehensive response generation system for the LocalRealtimeClient,
which simulates the OpenAI Realtime API. It handles the creation and streaming of various
response types with realistic timing and behavior patterns.

Key Features:
- Text Response Streaming: Character-by-character text streaming with configurable delays
- Audio Response Streaming: Chunked audio streaming with support for files and raw data
- Function Call Simulation: Realistic function call generation with argument streaming
- Transcript Generation: Audio transcription events for both input and output audio
- Error Handling: Comprehensive error event generation for testing edge cases
- Response Lifecycle: Complete response creation, streaming, and completion flow

Core Components:
- ResponseGenerator: Main class handling all response generation types
- Streaming Simulation: Realistic timing and chunking for natural conversation flow
- Audio Integration: Seamless integration with AudioManager for file-based responses
- Event Sequencing: Proper event ordering and timing for API compliance

Supported Response Types:
- Text Responses: Streaming text with character delays and completion events
- Audio Responses: Chunked audio streaming with configurable chunk sizes and delays
- Function Calls: Argument streaming with proper call structure and completion
- Transcripts: Real-time transcription events for audio content
- Error Events: Structured error reporting with codes and details

The module is designed to provide realistic, configurable responses that closely
mimic the behavior of the actual OpenAI Realtime API, enabling comprehensive
testing and development of client applications.

Usage:
    generator = ResponseGenerator(logger, audio_manager, websocket_connection)
    await generator.generate_text_response(options, config)
    await generator.generate_audio_response(options, config)
    await generator.generate_function_call(options, config)
"""

import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from opusagent.models.openai_api import ResponseCreateOptions, ServerEventType

from .models import LocalResponseConfig


class ResponseGenerator:
    """
    Generates different types of responses for the LocalRealtimeClient.
    
    This class handles the generation of text, audio, and function call
    responses with configurable timing and streaming behavior.
    
    Attributes:
        logger (logging.Logger): Logger instance for debugging
        audio_manager: AudioManager instance for loading audio files
        _ws: WebSocket connection for sending events
        _active_response_id: ID of the currently active response
    """
    
    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        audio_manager=None,
        websocket_connection=None
    ):
        """
        Initialize the ResponseGenerator.
        
        Args:
            logger (Optional[logging.Logger]): Logger instance for debugging.
            audio_manager: AudioManager instance for loading audio files.
            websocket_connection: WebSocket connection for sending events.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.audio_manager = audio_manager
        self._ws = websocket_connection
        self._active_response_id: Optional[str] = None
    
    def set_websocket_connection(self, ws) -> None:
        """
        Set the WebSocket connection for sending events.
        
        Args:
            ws: WebSocket connection to use for sending events.
        """
        self._ws = ws
    
    def set_active_response_id(self, response_id: str) -> None:
        """
        Set the active response ID.
        
        Args:
            response_id (str): ID of the active response.
        """
        self._active_response_id = response_id
    
    async def _send_event(self, event: Dict[str, Any]) -> None:
        """
        Send an event to the connected WebSocket client.
        
        Args:
            event (Dict[str, Any]): Event data to send.
        
        Raises:
            Exception: If sending fails.
        """
        from opusagent.utils.websocket_utils import WebSocketUtils
        
        success = await WebSocketUtils.safe_send_event(self._ws, event, self.logger)
        if not success:
            raise Exception("Failed to send event to WebSocket")
    
    def _determine_response_key(self, options: ResponseCreateOptions) -> Optional[str]:
        """
        Determine which response configuration to use based on the request.
        
        This method implements the response selection logic. Currently, it uses
        a simple strategy of returning the first available response configuration
        key. This can be customized to implement more sophisticated selection
        logic based on conversation context, user input, or other factors.
        
        Args:
            options (ResponseCreateOptions): Response creation options from the client.
        
        Returns:
            Optional[str]: Key for the response configuration to use, or None for default.
        
        Note:
            This is a simple implementation that can be extended for more
            sophisticated response selection based on:
            - Conversation history
            - User input content
            - Requested modalities
            - Tool configurations
            - Session context
        """
        # This is a placeholder - the actual logic will be implemented in the main client
        # that has access to the response configurations
        return None
    
    async def generate_text_response(
        self,
        options: ResponseCreateOptions,
        config: LocalResponseConfig
    ) -> None:
        """
        Generate a text response with streaming simulation.
        
        This method generates a text response by streaming individual characters
        with configurable delays to simulate realistic typing behavior. It sends
        text delta events for each character and a final text done event.
        
        Args:
            options (ResponseCreateOptions): Response creation options.
            config (LocalResponseConfig): Configuration for this response.
        
        The streaming process:
        1. Sends text.delta events for each character
        2. Applies configurable delays between characters
        3. Sends text.done event with complete text
        """
        # Send text deltas
        text = config.text
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
            await asyncio.sleep(config.delay_seconds)
        
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
        
        self.logger.debug(f"[MOCK REALTIME] Text response completed: {len(text)} characters")
    
    async def generate_audio_response(
        self,
        options: ResponseCreateOptions,
        config: LocalResponseConfig
    ) -> None:
        """
        Generate an audio response with streaming simulation.
        
        This method generates an audio response by streaming audio data in chunks
        with configurable delays. It can use saved audio files, raw audio data,
        or generate silence as a fallback.
        
        Args:
            options (ResponseCreateOptions): Response creation options.
            config (LocalResponseConfig): Configuration for this response.
        
        Audio sources (in order of precedence):
        1. config.audio_data (raw bytes)
        2. config.audio_file (file path)
        3. Generated silence (fallback)
        
        The streaming process:
        1. Loads or generates audio data
        2. Splits data into chunks (3200 bytes = 200ms at 16kHz 16-bit)
        3. Sends audio.delta events for each chunk
        4. Applies configurable delays between chunks
        5. Sends audio.done event
        """
        # Get audio data
        if config.audio_data:
            audio_data = config.audio_data
            self.logger.debug("[MOCK REALTIME] Using raw audio data")
        elif config.audio_file and self.audio_manager:
            audio_data = await self.audio_manager.load_audio_file(config.audio_file)
            self.logger.debug(f"[MOCK REALTIME] Using audio file: {config.audio_file}")
        else:
            # Generate silence as fallback
            if self.audio_manager:
                audio_data = self.audio_manager._generate_silence()
            else:
                # Fallback if no audio manager
                audio_data = bytes([0] * 32000)  # 1 second of silence
            self.logger.debug("[MOCK REALTIME] Using generated silence")
        
        # Split into chunks (3200 bytes = 200ms at 16kHz 16-bit)
        chunk_size = 3200
        chunks = [audio_data[i:i + chunk_size] for i in range(0, len(audio_data), chunk_size)]
        
        self.logger.debug(f"[MOCK REALTIME] Streaming {len(chunks)} audio chunks")
        
        # Send audio deltas
        for i, chunk in enumerate(chunks):
            event = {
                "type": ServerEventType.RESPONSE_AUDIO_DELTA,
                "response_id": self._active_response_id,
                "item_id": str(uuid.uuid4()),
                "output_index": 0,
                "content_index": 0,
                "delta": base64.b64encode(chunk).decode("utf-8")
            }
            await self._send_event(event)
            await asyncio.sleep(config.audio_chunk_delay)
        
        # Send audio done
        event = {
            "type": ServerEventType.RESPONSE_AUDIO_DONE,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "content_index": 0
        }
        await self._send_event(event)
        
        self.logger.debug(f"[MOCK REALTIME] Audio response completed: {len(audio_data)} bytes")
    
    async def generate_function_call(
        self,
        options: ResponseCreateOptions,
        config: LocalResponseConfig
    ) -> None:
        """
        Generate a function call response.
        
        This method generates a function call response by streaming function
        call arguments and sending appropriate events. It can use a configured
        function call or generate a default one.
        
        Args:
            options (ResponseCreateOptions): Response creation options.
            config (LocalResponseConfig): Configuration for this response.
        
        The function call process:
        1. Determines function call to simulate
        2. Sends function_call_arguments.delta events
        3. Sends function_call_arguments.done event
        4. Includes function name and arguments
        """
        # Use config function call if available, otherwise use default
        if config.function_call:
            function_call = config.function_call
            self.logger.debug(f"[MOCK REALTIME] Using configured function call: {function_call.get('name')}")
        else:
            # Default function call
            function_call = {
                "name": "mock_function",
                "arguments": {"param1": "value1", "param2": "value2"}
            }
            self.logger.debug("[MOCK REALTIME] Using default function call")
        
        # Send function call arguments delta
        event = {
            "type": ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "call_id": str(uuid.uuid4()),
            "delta": json.dumps(function_call["arguments"])
        }
        await self._send_event(event)
        
        # Send function call arguments done
        event = {
            "type": ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "call_id": str(uuid.uuid4()),
            "arguments": json.dumps(function_call["arguments"])
        }
        await self._send_event(event)
        
        self.logger.info(f"[MOCK REALTIME] Function call completed: {function_call.get('name')}")
    
    async def generate_response_done(self) -> None:
        """
        Send a response.done event to complete the response.
        
        This method sends the final response.done event that indicates
        the response generation is complete.
        """
        event = {
            "type": ServerEventType.RESPONSE_DONE,
            "response": {
                "id": self._active_response_id,
                "created_at": int(datetime.now().timestamp() * 1000)
            }
        }
        await self._send_event(event)
        
        self.logger.info(f"[MOCK REALTIME] Response generation completed: {self._active_response_id}")
    
    async def send_error(self, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Send an error event.
        
        This method sends an error event to the client. It's useful for
        testing error handling and edge cases.
        
        Args:
            code (str): Error code.
            message (str): Error message.
            details (Optional[Dict[str, Any]]): Additional error details.
        """
        event = {
            "type": ServerEventType.ERROR,
            "code": code,
            "message": message
        }
        if details is not None:
            event["details"] = details
        await self._send_event(event)
    
    async def send_transcript_delta(self, text: str, final: bool = False) -> None:
        """
        Send a transcript delta event for generated audio.
        
        This method sends transcript events that correspond to generated audio.
        It's useful for testing audio transcription features.
        
        Args:
            text (str): Transcript text to send.
            final (bool): Whether this is the final transcript chunk.
        """
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
    
    async def send_input_transcript_delta(self, item_id: str, text: str, final: bool = False) -> None:
        """
        Send an input audio transcription delta event.
        
        This method sends transcript events for user input audio.
        It's useful for testing input audio transcription features.
        
        Args:
            item_id (str): ID of the conversation item.
            text (str): Transcript text to send.
            final (bool): Whether this is the final transcript chunk.
        """
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
    
    async def send_input_transcript_failed(self, item_id: str, error: Dict[str, Any]) -> None:
        """
        Send an input audio transcription failed event.
        
        This method sends a failure event for input audio transcription.
        It's useful for testing error handling scenarios.
        
        Args:
            item_id (str): ID of the conversation item.
            error (Dict[str, Any]): Error details.
        """
        event = {
            "type": ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_FAILED,
            "item_id": item_id,
            "content_index": 0,
            "error": error
        }
        await self._send_event(event)
    
    async def generate_input_transcript_delta(
        self, item_id: str, text: str, confidence: float = 0.0
    ) -> None:
        """
        Generate an input audio transcription delta event.
        
        This method sends real-time transcription delta events for incoming
        audio from the caller. It's used by the transcription system to
        emit transcription results as they become available.
        
        Args:
            item_id (str): ID of the conversation item being transcribed.
            text (str): Transcription delta text.
            confidence (float): Confidence score for the transcription.
        """
        event = {
            "type": ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_DELTA,
            "item_id": item_id,
            "content_index": 0,
            "delta": text
        }
        await self._send_event(event)
        
        self.logger.debug(f"[MOCK REALTIME] Input transcript delta: '{text}' (confidence: {confidence:.2f})")
    
    async def generate_input_transcript_completed(
        self, item_id: str, text: str, confidence: float = 0.0
    ) -> None:
        """
        Generate an input audio transcription completed event.
        
        This method sends the final transcription result for a completed
        audio segment from the caller.
        
        Args:
            item_id (str): ID of the conversation item being transcribed.
            text (str): Complete transcription text.
            confidence (float): Overall confidence score for the transcription.
        """
        event = {
            "type": ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED,
            "item_id": item_id,
            "content_index": 0,
            "transcript": text
        }
        await self._send_event(event)
        
        self.logger.info(f"[MOCK REALTIME] Input transcript completed: '{text}' (confidence: {confidence:.2f})")
    
    async def generate_input_transcript_failed(
        self, item_id: str, error_message: str, error_code: str = "transcription_failed"
    ) -> None:
        """
        Generate an input audio transcription failed event.
        
        This method sends a transcription failure event when the transcription
        system encounters an error processing the audio.
        
        Args:
            item_id (str): ID of the conversation item that failed transcription.
            error_message (str): Human-readable error message.
            error_code (str): Error code for the failure.
        """
        error_details = {
            "code": error_code,
            "message": error_message
        }
        
        event = {
            "type": ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_FAILED,
            "item_id": item_id,
            "content_index": 0,
            "error": error_details
        }
        await self._send_event(event)
        
        self.logger.error(f"[MOCK REALTIME] Input transcript failed for {item_id}: {error_message}")