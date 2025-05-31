"""Bridge between telephony WebSocket and OpenAI Realtime API for handling real-time audio communication.

This module provides functionality to bridge between a telephony WebSocket connection
and the OpenAI Realtime API, enabling real-time audio communication with AI agents.
It handles bidirectional audio streaming, session management, and event processing.
"""

import json
import os
import uuid
from typing import Optional
import asyncio

import websockets
from dotenv import load_dotenv
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from fastagent.config.logging_config import configure_logging

# Import AudioCodes models
from fastagent.models.audiocodes_api import (
    PlayStreamChunkMessage,
    PlayStreamStartMessage,
    PlayStreamStopMessage,
    SessionAcceptedResponse,
    TelephonyEventType,
    UserStreamStartedResponse,
    UserStreamStoppedResponse,
)

# Import OpenAI Realtime API models
from fastagent.models.openai_api import (
    ConversationItemContentParam,
    ConversationItemCreateEvent,
    ConversationItemParam,
    InputAudioBufferAppendEvent,
    InputAudioBufferCommitEvent,
    LogEventType,
    MessageRole,
    ResponseAudioDeltaEvent,
    ResponseCreateEvent,
    ResponseCreateOptions,
    ResponseDoneEvent,
    ResponseTextDeltaEvent,
    ServerEventType,
    SessionConfig,
    SessionCreatedEvent,
    SessionUpdatedEvent,
    SessionUpdateEvent,
)

load_dotenv()

# Configure logging
logger = configure_logging()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PORT = int(os.getenv("PORT", 6060))
SYSTEM_MESSAGE = (
    "You are a banking agent. You are able to answer questions about the bank and the services they offer. "
    "You are also able to help with general banking questions and provide information about the bank's products and services."
)
VOICE = "alloy"
LOG_EVENT_TYPES = [
    LogEventType.ERROR,
    LogEventType.RESPONSE_CONTENT_DONE,
    LogEventType.RATE_LIMITS_UPDATED,
    LogEventType.RESPONSE_DONE,
    LogEventType.INPUT_AUDIO_BUFFER_COMMITTED,
    LogEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED,
    LogEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED,
    LogEventType.SESSION_CREATED,
]


class TelephonyRealtimeBridge:
    """Bridge class for handling bidirectional communication between telephony and OpenAI Realtime API.

    This class manages the WebSocket connections between a telephony system and the OpenAI Realtime API,
    handling audio streaming, session management, and event processing in both directions.

    Attributes:
        telephony_websocket (WebSocket): FastAPI WebSocket connection for telephony communication
        realtime_websocket (websockets.WebSocketClientProtocol): WebSocket connection to OpenAI Realtime API
        conversation_id (Optional[str]): Unique identifier for the current conversation
        media_format (Optional[str]): Audio format being used for the session
        active_stream_id (Optional[str]): Identifier for the current audio stream being played
        session_initialized (bool): Whether the OpenAI Realtime API session has been initialized
        speech_detected (bool): Whether speech is currently being detected
        _closed (bool): Flag indicating whether the bridge connections are closed
    """

    def __init__(
        self,
        telephony_websocket: WebSocket,
        realtime_websocket: websockets.WebSocketClientProtocol,
    ):
        """Initialize the bridge with WebSocket connections.

        Args:
            telephony_websocket (WebSocket): FastAPI WebSocket connection for telephony
            realtime_websocket (websockets.WebSocketClientProtocol): WebSocket connection to OpenAI Realtime API
        """
        self.telephony_websocket = telephony_websocket
        self.realtime_websocket = realtime_websocket
        self.conversation_id: Optional[str] = None
        self.media_format: Optional[str] = None
        self.active_stream_id: Optional[str] = None
        self.session_initialized = False
        self.speech_detected = False
        self._closed = False

        # Create event handler mappings for telephony events
        self.telephony_event_handlers = {
            TelephonyEventType.SESSION_INITIATE: self.handle_session_initiate,
            TelephonyEventType.USER_STREAM_START: self.handle_user_stream_start,
            TelephonyEventType.USER_STREAM_CHUNK: self.handle_user_stream_chunk,
            TelephonyEventType.USER_STREAM_STOP: self.handle_user_stream_stop,
            TelephonyEventType.SESSION_END: self.handle_session_end,
        }

        # Create event handler mappings for realtime events
        self.realtime_event_handlers = {
            # Session events
            ServerEventType.SESSION_UPDATED: self.handle_session_update,
            ServerEventType.SESSION_CREATED: self.handle_session_update,
            # Conversation events
            ServerEventType.CONVERSATION_ITEM_CREATED: lambda x: logger.info("Conversation item created"),
            # Speech detection events
            ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED: self.handle_speech_detection,
            ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED: self.handle_speech_detection,
            ServerEventType.INPUT_AUDIO_BUFFER_COMMITTED: self.handle_speech_detection,
            # Response events
            ServerEventType.RESPONSE_CREATED: lambda x: logger.info(
                "Response creation started"
            ),
            ServerEventType.RESPONSE_AUDIO_DELTA: self.handle_audio_response_delta,
            ServerEventType.RESPONSE_AUDIO_DONE: self.handle_audio_response_completion,
            ServerEventType.RESPONSE_TEXT_DELTA: self.handle_text_and_transcript,
            ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA: self.handle_audio_transcript_delta,
            ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DONE: self.handle_audio_transcript_done,
            ServerEventType.RESPONSE_DONE: self.handle_response_completion,
            # Add new handlers for output item and content part events
            ServerEventType.RESPONSE_OUTPUT_ITEM_ADDED: self.handle_output_item_added,
            ServerEventType.RESPONSE_CONTENT_PART_ADDED: self.handle_content_part_added,
            ServerEventType.RESPONSE_CONTENT_PART_DONE: self.handle_content_part_done,
            ServerEventType.RESPONSE_OUTPUT_ITEM_DONE: self.handle_output_item_done,
            # Add handlers for input audio transcription events
            ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_DELTA: self.handle_input_audio_transcription_delta,
            ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED: self.handle_input_audio_transcription_completed,
        }

    async def close(self):
        """Safely close both WebSocket connections.

        This method ensures both the telephony and OpenAI Realtime API WebSocket connections
        are properly closed, handling any exceptions that may occur during the process.
        """
        if not self._closed:
            self._closed = True
            try:
                if self.realtime_websocket and self.realtime_websocket.close_code is None:
                    await self.realtime_websocket.close()
            except Exception as e:
                logger.error(f"Error closing OpenAI connection: {e}")
            try:
                if self.telephony_websocket and not self.telephony_websocket.client_state.DISCONNECTED:
                    await self.telephony_websocket.close()
            except Exception as e:
                logger.error(f"Error closing telephony connection: {e}")

    async def handle_session_initiate(self, data):
        """Handle session.initiate message from telephony client.

        This method processes the session initiation request, extracts necessary data,
        and sets up the conversation state.

        Args:
            data (dict): Session initiate message data
        """
        logger.info(f"Session initiate received: {data}")
        self.conversation_id = data.get("conversationId") or str(uuid.uuid4())
        logger.info(f"Conversation started: {self.conversation_id}")

        # Get media format
        self.media_format = data.get("supportedMediaFormats", ["raw/lpcm16"])[0]

        # Set flag to indicate we're waiting for session acceptance
        self.waiting_for_session_creation = True
        self.session_initialized = True

        # Send session.accepted response immediately since session is already initialized
        session_accepted = SessionAcceptedResponse(
            type=TelephonyEventType.SESSION_ACCEPTED,
            conversationId=self.conversation_id,
            mediaFormat=self.media_format,
        )
        await self.telephony_websocket.send_json(session_accepted.model_dump())
        logger.info(f"Session accepted with format: {self.media_format}")
        self.waiting_for_session_creation = False

    async def handle_user_stream_start(self, data):
        """Handle userStream.start message from telephony client.

        This method processes the start of an audio stream from the client,
        and sends the appropriate acknowledgment response.

        Args:
            data (dict): UserStream start message data
        """
        logger.info(f"User stream start received: {data}")
        # Send userStream.started response
        stream_started = UserStreamStartedResponse(
            type=TelephonyEventType.USER_STREAM_STARTED,
            conversationId=self.conversation_id,
        )
        await self.telephony_websocket.send_json(stream_started.model_dump())
        logger.info(f"User stream started for conversation: {self.conversation_id}")

    async def handle_user_stream_chunk(self, data):
        """Handle userStream.chunk message containing audio data from telephony client.

        This method processes audio chunks and forwards them to the OpenAI Realtime API
        for processing. It only forwards the audio if the connection is still active.

        Args:
            data (dict): UserStream chunk message data containing audio
        """
        if not self._closed and self.realtime_websocket.close_code is None:
            # Use our Pydantic model for buffer append
            audio_append = InputAudioBufferAppendEvent(
                type="input_audio_buffer.append", audio=data["audioChunk"]
            )
            logger.debug(
                f"Sending audio to realtime-websocket (size: {len(data['audioChunk'])} bytes)"
            )
            await self.realtime_websocket.send(audio_append.model_dump_json())

    async def handle_user_stream_stop(self, data):
        """Handle userStream.stop message from telephony client.

        This method processes the end of an audio stream from the client,
        commits the audio buffer to OpenAI to signal end of speech,
        and sends the appropriate acknowledgment response.

        Args:
            data (dict): UserStream stop message data
        """
        logger.info(
            f"User stream stop received for conversation: {self.conversation_id}"
        )
        # Commit the audio buffer to signal end of speech
        if not self._closed and self.realtime_websocket.close_code is None:
            buffer_commit = InputAudioBufferCommitEvent(
                type="input_audio_buffer.commit"
            )
            await self.realtime_websocket.send(buffer_commit.model_dump_json())
            logger.info("Audio buffer committed")

            # Send userStream.stopped response
            stream_stopped = UserStreamStoppedResponse(
                type=TelephonyEventType.USER_STREAM_STOPPED,
                conversationId=self.conversation_id,
            )
            await self.telephony_websocket.send_json(stream_stopped.model_dump())

    async def handle_session_end(self, data):
        """Handle session.end message from telephony client.

        This method processes the end of a session, closes all connections,
        and logs the reason for session termination.

        Args:
            data (dict): Session end message data
        """
        logger.info(f"Session end received: {data.get('reason', 'No reason provided')}")
        await self.close()
        logger.info(f"Telephony-Realtime bridge closed")

    async def handle_log_event(self, response_dict):
        """Handle log events from the OpenAI Realtime API.

        This method processes log events, with special handling for error events
        to provide detailed error information for debugging.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        response_type = response_dict["type"]

        # Enhanced error logging
        if response_type == "error":
            error_code = response_dict.get("code", "unknown")
            error_message = response_dict.get("message", "No message provided")
            error_details = response_dict.get("details", {})
            logger.error(f"ERROR DETAILS: code={error_code}, message='{error_message}'")
            if error_details:
                logger.error(f"ERROR ADDITIONAL DETAILS: {json.dumps(error_details)}")

            # Log the full error response for debugging
            logger.error(f"FULL ERROR RESPONSE: {json.dumps(response_dict)}")

    async def handle_session_update(self, response_dict):
        """Handle session update events from the OpenAI Realtime API.

        This method processes session created and updated events.

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

        This method processes speech detection events including speech started,
        speech stopped, and audio buffer committed events.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        response_type = response_dict["type"]

        if response_type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
            logger.info("Speech started detected")
            self.speech_detected = True
        elif response_type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
            logger.info("Speech stopped detected")
            self.speech_detected = False
        elif response_type == ServerEventType.INPUT_AUDIO_BUFFER_COMMITTED:
            logger.info("Audio buffer committed")

    async def handle_audio_response_delta(self, response_dict):
        """Handle audio response delta events from the OpenAI Realtime API.

        This method processes audio data chunks, creates audio streams when needed,
        and forwards the audio to the telephony client.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API containing audio
        """
        try:
            # Parse using our updated model - note the "delta" field instead of "audio"
            audio_delta = ResponseAudioDeltaEvent(**response_dict)

            # Check if connections are still active
            if self._closed or not self.conversation_id:
                logger.debug("Skipping audio delta - connection closed or no conversation ID")
                return

            # Check if telephony websocket is still connected
            if not self.telephony_websocket or self.telephony_websocket.client_state.DISCONNECTED:
                logger.debug("Skipping audio delta - telephony websocket disconnected")
                return

            # Start a new audio stream if needed
            if not self.active_stream_id:
                try:
                    # Start a new audio stream
                    self.active_stream_id = str(uuid.uuid4())
                    stream_start = PlayStreamStartMessage(
                        type=TelephonyEventType.PLAY_STREAM_START,
                        conversationId=self.conversation_id,
                        streamId=self.active_stream_id,
                        mediaFormat=self.media_format or "raw/lpcm16",
                    )
                    await self.telephony_websocket.send_json(stream_start.model_dump())
                    logger.info(f"Started play stream: {self.active_stream_id}")
                except Exception as e:
                    logger.error(f"Error starting audio stream: {e}")
                    self.active_stream_id = None
                    return

            try:
                # Send audio chunk with the delta value as the audio data
                stream_chunk = PlayStreamChunkMessage(
                    type=TelephonyEventType.PLAY_STREAM_CHUNK,
                    conversationId=self.conversation_id,
                    streamId=self.active_stream_id,
                    audioChunk=audio_delta.delta,  # Use delta field for audio data
                )
                await self.telephony_websocket.send_json(stream_chunk.model_dump())
                logger.debug(
                    f"Sent audio chunk to client (size: {len(audio_delta.delta)} bytes)"
                )
            except Exception as e:
                logger.error(f"Error sending audio chunk: {e}")
                # Don't close the connection here, just log the error
                # The connection will be closed by the main error handler if needed

        except Exception as e:
            logger.error(f"Error processing audio data: {e}")
            # Don't close the connection here, just log the error
            # The connection will be closed by the main error handler if needed

    async def handle_audio_response_completion(self, response_dict):
        """Handle audio response completion events from the OpenAI Realtime API.

        This method processes the completion of audio responses and stops
        any active audio streams to the telephony client.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        logger.info("Audio response completed")
        # Stop the play stream
        if self.active_stream_id and self.conversation_id:
            stream_stop = PlayStreamStopMessage(
                type=TelephonyEventType.PLAY_STREAM_STOP,
                conversationId=self.conversation_id,
                streamId=self.active_stream_id,
            )
            await self.telephony_websocket.send_json(stream_stop.model_dump())
            logger.info(f"Stopped play stream: {self.active_stream_id}")
            self.active_stream_id = None

    async def handle_text_and_transcript(self, response_dict):
        """Handle text and transcript events from the OpenAI Realtime API.

        This method processes text deltas and audio transcript deltas,
        logging them for monitoring and debugging purposes.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        response_type = response_dict["type"]

        if response_type == ServerEventType.RESPONSE_TEXT_DELTA:
            text_delta = ResponseTextDeltaEvent(**response_dict)
            logger.info(f"Text delta received: {text_delta.delta}")
        elif response_type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA:
            logger.info(
                f"Received audio transcript delta: {response_dict.get('delta', '')}"
            )

    async def handle_response_completion(self, response_dict):
        """Handle response completion events from the OpenAI Realtime API.

        This method processes the final completion of a response and ensures
        that any active audio streams are properly stopped.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        response_done = ResponseDoneEvent(**response_dict)
        logger.info("Response completed")
        # Stop the current play stream if active
        if self.active_stream_id and self.conversation_id:
            stream_stop = PlayStreamStopMessage(
                type=TelephonyEventType.PLAY_STREAM_STOP,
                conversationId=self.conversation_id,
                streamId=self.active_stream_id,
            )
            await self.telephony_websocket.send_json(stream_stop.model_dump())
            logger.info(
                f"Stopped play stream at end of response: {self.active_stream_id}"
            )
            self.active_stream_id = None

    async def handle_output_item_added(self, response_dict):
        """Handle response output item added events from the OpenAI Realtime API.

        This method processes when a new output item is added to the response,
        logging the event for monitoring purposes.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        logger.info(f"Output item added: {response_dict.get('item', {})}")

    async def handle_content_part_added(self, response_dict):
        """Handle response content part added events from the OpenAI Realtime API.

        This method processes when a new content part is added to a response,
        logging the event for monitoring purposes.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        logger.info(f"Content part added: {response_dict.get('part', {})}")

    async def handle_audio_transcript_delta(self, response_dict):
        """Handle audio transcript delta events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        logger.debug(f"Received audio transcript delta: {response_dict.get('delta', '')}")

    async def handle_audio_transcript_done(self, response_dict):
        """Handle audio transcript completion events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        logger.info("Audio transcript completed")

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
        logger.debug(f"Received input audio transcription delta: {response_dict.get('delta', '')}")

    async def handle_input_audio_transcription_completed(self, response_dict):
        """Handle input audio transcription completion events from the OpenAI Realtime API.

        Args:
            response_dict (dict): The response data from the OpenAI Realtime API
        """
        logger.info("Input audio transcription completed")

    def _get_telephony_event_type(self, msg_type_str):
        """Convert a string message type to a TelephonyEventType enum value.

        Args:
            msg_type_str (str): The message type string from the raw message

        Returns:
            TelephonyEventType: The corresponding enum value or None if not found
        """
        try:
            return TelephonyEventType(msg_type_str)
        except ValueError:
            return None

    async def receive_from_telephony(self):
        """Receive and process audio data from the telephony WebSocket.

        This method continuously listens for messages from the telephony WebSocket,
        processes audio data, and forwards it to the OpenAI Realtime API. It handles
        various events including session initiation, audio streaming, and disconnections.

        Supports the AudioCodes API format messages.

        Raises:
            WebSocketDisconnect: When the telephony client disconnects
            Exception: For any other errors during processing
        """
        try:
            async for message in self.telephony_websocket.iter_text():
                if self._closed:
                    break

                data = json.loads(message)
                msg_type_str = data["type"]

                # Convert string message type to enum
                msg_type = self._get_telephony_event_type(msg_type_str)

                if msg_type:
                    # Log only message type and audio chunk size if present
                    if 'audioChunk' in data:
                        logger.info(f"Received telephony message: {msg_type_str} with audio chunk size: {len(data['audioChunk'])} bytes")
                    else:
                        logger.info(f"Received telephony message: {msg_type_str}")
                    # Dispatch to the appropriate event handler
                    handler = self.telephony_event_handlers.get(msg_type)
                    if handler:
                        await handler(data)
                        # Special case for session.end to break the loop
                        if msg_type == TelephonyEventType.SESSION_END:
                            break
                    else:
                        logger.warning(
                            f"No handler for telephony message type: {msg_type}"
                        )
                else:
                    logger.info(f"Received telephony message: {message}")
                    logger.warning(f"Unknown telephony message type: {msg_type_str}")

        except WebSocketDisconnect:
            logger.info("Client disconnected.")
            await self.close()
        except Exception as e:
            logger.error(f"Error in receive_from_telephony: {e}")
            await self.close()

    async def receive_from_realtime(self):
        """Receive and process events from the OpenAI Realtime API.

        This method continuously listens for messages from the OpenAI Realtime API,
        processes them, and forwards responses to the telephony WebSocket. It handles
        various events including audio responses, session updates, and transcripts.

        Supports sending responses in AudioCodes API format.

        Raises:
            Exception: For any errors during processing
        """
        try:
            async for openai_message in self.realtime_websocket:
                if self._closed:
                    break

                response_dict = json.loads(openai_message)
                response_type = response_dict["type"]
                logger.info(f"Received OpenAI message type: {response_type}")

                # Handle log events first
                if response_type in [event.value for event in LOG_EVENT_TYPES]:
                    await self.handle_log_event(response_dict)
                    continue

                # Dispatch to the appropriate event handler
                handler = self.realtime_event_handlers.get(response_type)
                if handler:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(response_dict)
                        else:
                            handler(response_dict)
                    except Exception as e:
                        logger.error(f"Error in event handler for {response_type}: {e}")
                else:
                    logger.warning(f"Unknown OpenAI event type: {response_type}")

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


async def send_initial_conversation_item(realtime_websocket):
    """Send the initial conversation item to start the AI interaction.

    This function creates and sends the first conversation item to the OpenAI Realtime API,
    initiating the conversation with a greeting and request for an introduction and joke.

    Args:
        realtime_websocket (websockets.WebSocketClientProtocol): WebSocket connection to OpenAI Realtime API
    """
    # Create initial conversation item using our model
    initial_conversation = ConversationItemCreateEvent(
        type="conversation.item.create",
        item=ConversationItemParam(
            type="message",
            role=MessageRole.USER,
            content=[
                ConversationItemContentParam(
                    type="input_text",
                    text="Hello! Please introduce yourself and tell me a joke.",
                )
            ],
        ),
    )

    logger.info(
        "Sending initial conversation item: %s", initial_conversation.model_dump_json()
    )
    await realtime_websocket.send(initial_conversation.model_dump_json())

    # Wait a moment to allow the item to be processed
    await asyncio.sleep(1)

    # Create response using our model with default options
    response_create = ResponseCreateEvent(
        type="response.create",
        response=ResponseCreateOptions(
            modalities=["text", "audio"],
            voice=VOICE,
            instructions=SYSTEM_MESSAGE,
            output_audio_format="pcm16",
            temperature=0.8,
            max_output_tokens=4096,  # Maximum allowed value
            tool_choice="none",  # Disable function calling
        ),
    )
    await realtime_websocket.send(response_create.model_dump_json())


async def initialize_session(realtime_websocket):
    """Initialize the OpenAI Realtime API session with configuration.

    This function sets up the initial session configuration for the OpenAI Realtime API,
    including audio format settings, voice selection, system instructions, and other
    session parameters. It also triggers the initial conversation.

    Args:
        realtime_websocket (websockets.WebSocketClientProtocol): WebSocket connection to OpenAI Realtime API
    """
    # Use our SessionConfig and SessionUpdateEvent models
    session_config = SessionConfig(
        turn_detection={
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 200,
            "create_response": True,
            "interrupt_response": True,
        },
        input_audio_format="pcm16",
        output_audio_format="pcm16",
        voice=VOICE,
        instructions=SYSTEM_MESSAGE,
        modalities=["text", "audio"],
        temperature=0.8,
        model="gpt-4o-realtime-preview-2024-10-01",
        tools=[],
        input_audio_noise_reduction={"type": "near_field"},
        input_audio_transcription={"model": "whisper-1"},
        max_response_output_tokens=4096,  # Maximum allowed value
        tool_choice="auto",
    )

    session_update = SessionUpdateEvent(type="session.update", session=session_config)

    logger.info("Sending session update: %s", session_update.model_dump_json())
    await realtime_websocket.send(session_update.model_dump_json())

    # Wait for the session to be updated before proceeding
    # The initial conversation will be triggered by the client when needed
