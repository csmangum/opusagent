"""Handler for OpenAI Realtime API communication.

This module provides functionality to handle real-time communication with the OpenAI Realtime API,
including response state management, audio streaming, transcripts, and function calls.
"""

import json
from typing import Any, Dict, Optional

import websockets

from opusagent.handlers.audio_stream_handler import AudioStreamHandler
from opusagent.config.logging_config import configure_logging
from opusagent.handlers.event_router import EventRouter
from opusagent.handlers.function_handler import FunctionHandler
from opusagent.models.openai_api import ResponseDoneEvent, ServerEventType
from opusagent.handlers.session_manager import SessionManager
from opusagent.handlers.transcript_manager import TranscriptManager

# Configure logging
logger = configure_logging("realtime_handler")


class RealtimeHandler:
    """Handler for OpenAI Realtime API communication.

    This class manages all realtime communication with the OpenAI Realtime API,
    including response state management, audio streaming, transcripts, and function calls.

    Attributes:
        realtime_websocket (websockets.WebSocketClientProtocol): WebSocket connection to OpenAI Realtime API
        audio_handler (AudioStreamHandler): Handler for managing audio streams
        function_handler (FunctionHandler): Handler for managing function calls
        session_manager (SessionManager): Handler for managing OpenAI Realtime API sessions
        event_router (EventRouter): Router for handling realtime events
        transcript_manager (TranscriptManager): Manager for handling transcripts
        response_active (bool): Whether a response is currently being generated
        pending_user_input (Optional[Dict]): Queue for user input during active response
        response_id_tracker (Optional[str]): Track current response ID
        _closed (bool): Flag indicating whether the handler is closed
    """

    def __init__(
        self,
        realtime_websocket,
        audio_handler: AudioStreamHandler,
        function_handler: FunctionHandler,
        session_manager: SessionManager,
        event_router: EventRouter,
        transcript_manager: TranscriptManager,
    ):
        """Initialize the realtime handler.

        Args:
            realtime_websocket (websockets.WebSocketClientProtocol): WebSocket connection to OpenAI Realtime API
            audio_handler (AudioStreamHandler): Handler for managing audio streams
            function_handler (FunctionHandler): Handler for managing function calls
            session_manager (SessionManager): Handler for managing OpenAI Realtime API sessions
            event_router (EventRouter): Router for handling realtime events
            transcript_manager (TranscriptManager): Manager for handling transcripts
        """
        self.realtime_websocket = realtime_websocket
        self.audio_handler = audio_handler
        self.function_handler = function_handler
        self.session_manager = session_manager
        self.event_router = event_router
        self.transcript_manager = transcript_manager

        # Response state tracking
        self.response_active = False
        self.pending_user_input: Optional[Dict[str, Any]] = None
        self.response_id_tracker = None
        self._closed = False

        # Register realtime event handlers
        self._register_event_handlers()

    def _register_event_handlers(self):
        """Register handlers for realtime events."""
        self.event_router.register_realtime_handler(
            ServerEventType.SESSION_UPDATED, self.handle_session_update
        )
        self.event_router.register_realtime_handler(
            ServerEventType.SESSION_CREATED, self.handle_session_update
        )
        self.event_router.register_realtime_handler(
            ServerEventType.CONVERSATION_ITEM_CREATED,
            lambda x: logger.info("Conversation item created"),
        )
        self.event_router.register_realtime_handler(
            ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED,
            self.handle_speech_detection,
        )
        self.event_router.register_realtime_handler(
            ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED,
            self.handle_speech_detection,
        )
        self.event_router.register_realtime_handler(
            ServerEventType.INPUT_AUDIO_BUFFER_COMMITTED, self.handle_speech_detection
        )
        self.event_router.register_realtime_handler(
            ServerEventType.RESPONSE_CREATED, self.handle_response_created
        )
        self.event_router.register_realtime_handler(
            ServerEventType.RESPONSE_AUDIO_DELTA, self.handle_audio_response_delta
        )
        self.event_router.register_realtime_handler(
            ServerEventType.RESPONSE_AUDIO_DONE, self.handle_audio_response_completion
        )
        self.event_router.register_realtime_handler(
            ServerEventType.RESPONSE_TEXT_DELTA, self.handle_text_and_transcript
        )
        self.event_router.register_realtime_handler(
            ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA,
            self.handle_audio_transcript_delta,
        )
        self.event_router.register_realtime_handler(
            ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DONE,
            self.handle_audio_transcript_done,
        )
        self.event_router.register_realtime_handler(
            ServerEventType.RESPONSE_DONE, self.handle_response_completion
        )
        self.event_router.register_realtime_handler(
            ServerEventType.RESPONSE_OUTPUT_ITEM_ADDED, self.handle_output_item_added
        )
        self.event_router.register_realtime_handler(
            ServerEventType.RESPONSE_CONTENT_PART_ADDED, self.handle_content_part_added
        )
        self.event_router.register_realtime_handler(
            ServerEventType.RESPONSE_CONTENT_PART_DONE, self.handle_content_part_done
        )
        self.event_router.register_realtime_handler(
            ServerEventType.RESPONSE_OUTPUT_ITEM_DONE, self.handle_output_item_done
        )
        self.event_router.register_realtime_handler(
            ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_DELTA,
            self.handle_input_audio_transcription_delta,
        )
        self.event_router.register_realtime_handler(
            ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED,
            self.handle_input_audio_transcription_completed,
        )
        self.event_router.register_realtime_handler(
            ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA,
            self.function_handler.handle_function_call_arguments_delta,
        )
        self.event_router.register_realtime_handler(
            ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE,
            self.function_handler.handle_function_call_arguments_done,
        )

    async def handle_session_update(self, response_dict):
        """Handle session update events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        response_type = response_dict["type"]

        if response_type == ServerEventType.SESSION_UPDATED:
            logger.info("Session updated successfully")
        elif response_type == ServerEventType.SESSION_CREATED:
            logger.info("Session created successfully")

    async def handle_speech_detection(self, response_dict):
        """Handle speech detection events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        response_type = response_dict["type"]

        if response_type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
            logger.info("Speech started detected")
        elif response_type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
            logger.info("Speech stopped detected")
        elif response_type == ServerEventType.INPUT_AUDIO_BUFFER_COMMITTED:
            logger.info("Audio buffer committed")

    async def handle_audio_response_delta(self, response_dict):
        """Handle audio response delta events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API containing audio
        """
        await self.audio_handler.handle_outgoing_audio(response_dict)

    async def handle_audio_response_completion(self, response_dict):
        """Handle audio response completion events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        logger.info("Audio response completed")
        await self.audio_handler.stop_stream()

    async def handle_text_and_transcript(self, response_dict):
        """Handle text and transcript events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        response_type = response_dict["type"]

        if response_type == ServerEventType.RESPONSE_TEXT_DELTA:
            logger.info(f"Text delta received: {response_dict.get('delta', '')}")
        elif response_type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA:
            logger.info(
                f"Received audio transcript delta: {response_dict.get('delta', '')}"
            )

    async def handle_response_created(self, response_dict):
        """Handle response created events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        self.response_active = True
        response_data = response_dict.get("response", {})
        self.response_id_tracker = response_data.get("id")
        logger.info(f"Response generation started: {self.response_id_tracker}")

        # Log pending input status for debugging
        if self.pending_user_input:
            logger.info(f"Note: Pending user input exists while starting new response")

    async def handle_response_completion(self, response_dict):
        """Handle response completion events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        response_done = ResponseDoneEvent(**response_dict)
        self.response_active = False
        response_id = (
            response_done.response.get("id") if response_done.response else None
        )
        logger.info(f"Response generation completed: {response_id}")

        # Stop the current play stream if active
        await self.audio_handler.stop_stream()

        # Process any pending user input that was queued during response generation
        if self.pending_user_input:
            logger.info("Processing queued user input after response completion")
            try:
                await self.session_manager.create_response()
                logger.info("Successfully processed queued user input")
            except Exception as e:
                logger.error(f"Error processing queued user input: {e}")
            finally:
                self.pending_user_input = None

    async def handle_output_item_added(self, response_dict):
        """Handle response output item added events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        item = response_dict.get("item", {})
        logger.info(f"Output item added: {item}")

        # If this is a function call item, capture the function name for later use
        if item.get("type") == "function_call":
            call_id = item.get("call_id")
            function_name = item.get("name")
            item_id = item.get("id")

            if call_id and function_name:
                # Initialize the function call state with the function name
                if call_id not in self.function_handler.active_function_calls:
                    self.function_handler.active_function_calls[call_id] = {
                        "arguments_buffer": "",
                        "item_id": item_id,
                        "output_index": response_dict.get("output_index", 0),
                        "response_id": response_dict.get("response_id"),
                        "function_name": function_name,
                    }
                else:
                    # Update existing entry with function name
                    self.function_handler.active_function_calls[call_id][
                        "function_name"
                    ] = function_name

                logger.info(
                    f"Captured function call: {function_name} with call_id: {call_id}"
                )

    async def handle_content_part_added(self, response_dict):
        """Handle response content part added events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        logger.info(f"Content part added: {response_dict.get('part', {})}")

    async def handle_audio_transcript_delta(self, response_dict):
        """Handle audio transcript delta events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        delta = response_dict.get("delta", "")
        await self.transcript_manager.handle_output_transcript_delta(delta)

    async def handle_audio_transcript_done(self, response_dict):
        """Handle audio transcript completion events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        await self.transcript_manager.handle_output_transcript_completed()

    async def handle_content_part_done(self, response_dict):
        """Handle content part completion events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        logger.info("Content part completed")

    async def handle_output_item_done(self, response_dict):
        """Handle output item completion events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        logger.info("Output item completed")

    async def handle_input_audio_transcription_delta(self, response_dict):
        """Handle input audio transcription delta events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        delta = response_dict.get("delta", "")
        await self.transcript_manager.handle_input_transcript_delta(delta)

    async def handle_input_audio_transcription_completed(self, response_dict):
        """Handle input audio transcription completion events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        await self.transcript_manager.handle_input_transcript_completed()

    async def close(self):
        """Safely close the realtime handler.

        This method ensures all resources are properly cleaned up.
        """
        if not self._closed:
            self._closed = True
            await self.audio_handler.close()

    async def receive_from_realtime(self):
        """Receive and process events from the OpenAI Realtime API.

        This method continuously listens for messages from the OpenAI Realtime API,
        processes them, and forwards responses to the telephony WebSocket.

        Raises:
            Exception: For any errors during processing
        """
        try:
            async for openai_message in self.realtime_websocket:
                if self._closed:
                    break

                response_dict = json.loads(openai_message)
                await self.event_router.handle_realtime_event(response_dict)

        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"OpenAI WebSocket connection closed: {e}")
            await self.close()
        except TypeError as e:
            logger.error(f"Type error in receive_from_realtime: {e}")
            # Don't attempt to close if there's a NoneType error
            if not self._closed:
                self._closed = True
        except Exception as e:
            logger.error(f"Error in receive_from_realtime: {e}")
            if not self._closed:
                await self.close()
