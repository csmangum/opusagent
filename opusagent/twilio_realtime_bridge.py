"""Bridge between Twilio Media Streams WebSocket and OpenAI Realtime API for handling real-time audio communication.

This module provides functionality to bridge between a Twilio Media Streams WebSocket connection
and the OpenAI Realtime API, enabling real-time audio communication with AI agents over phone calls.
It handles bidirectional audio streaming, session management, and event processing.
"""

import asyncio
import base64
import json
import os
import uuid
from typing import Any, Callable, Dict, Optional

import websockets
from dotenv import load_dotenv
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from opusagent.config.logging_config import configure_logging
from opusagent.function_handler import FunctionHandler

# Import OpenAI Realtime API models
from opusagent.models.openai_api import (
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

# Import Twilio models
from opusagent.models.twilio_api import (
    ClearMessage,
    ConnectedMessage,
    DTMFMessage,
    MarkMessage,
    MediaMessage,
    OutgoingMarkMessage,
    OutgoingMediaMessage,
    StartMessage,
    StopMessage,
    TwilioEventType,
)

load_dotenv()

# Configure logging
logger = configure_logging("twilio_realtime_bridge")

DEFAULT_MODEL = "gpt-4o-realtime-preview-2024-10-01"
MINI_MODEL = "gpt-4o-mini-realtime-preview-2024-12-17"
FUTURE_MODEL = "gpt-4o-realtime-preview-2025-06-03"

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PORT = int(os.getenv("PORT", 6060))
SYSTEM_MESSAGE = (
    "You are a customer service agent for Bank of Peril. You help customers with their banking needs. "
    "When a customer contacts you, first greet them warmly, then listen to their request and call the call_intent function to identify their intent. "
    "After calling call_intent, use the function result to guide your response:\n"
    "- If intent is 'card_replacement', ask which type of card they need to replace (use the available_cards from the function result)\n"
    "- If intent is 'account_inquiry', ask what specific account information they need\n"
    "- For other intents, ask clarifying questions to better understand their needs\n"
    "Always be helpful, professional, and use the information returned by functions to provide relevant follow-up questions."
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
]


class TwilioRealtimeBridge:
    """Bridge class for handling bidirectional communication between Twilio Media Streams and OpenAI Realtime API.

    This class manages the WebSocket connections between Twilio Media Streams and the OpenAI Realtime API,
    handling audio streaming, session management, and event processing in both directions.

    Attributes:
        twilio_websocket (WebSocket): FastAPI WebSocket connection for Twilio Media Streams
        realtime_websocket (websockets.WebSocketClientProtocol): WebSocket connection to OpenAI Realtime API
        stream_sid (Optional[str]): Unique identifier for the current Twilio stream
        account_sid (Optional[str]): Twilio account SID
        call_sid (Optional[str]): Twilio call SID
        media_format (Optional[str]): Audio format being used for the session
        session_initialized (bool): Whether the OpenAI Realtime API session has been initialized
        speech_detected (bool): Whether speech is currently being detected
        _closed (bool): Flag indicating whether the bridge connections are closed
        audio_chunks_sent (int): Number of audio chunks sent to the OpenAI Realtime API
        total_audio_bytes_sent (int): Total number of bytes sent to the OpenAI Realtime API
        input_transcript_buffer (list): Buffer for accumulating input audio transcriptions
        output_transcript_buffer (list): Buffer for accumulating output audio transcriptions
        function_handler (FunctionHandler): Handler for managing function calls from the OpenAI Realtime API
        audio_buffer (list): Buffer for accumulating audio data before processing
        mark_counter (int): Counter for generating unique mark identifiers
    """

    def __init__(
        self,
        twilio_websocket: WebSocket,
        realtime_websocket: websockets.WebSocketClientProtocol,
    ):
        """Initialize the bridge with WebSocket connections.

        Args:
            twilio_websocket (WebSocket): FastAPI WebSocket connection for Twilio Media Streams
            realtime_websocket (websockets.WebSocketClientProtocol): WebSocket connection to OpenAI Realtime API
        """
        self.twilio_websocket = twilio_websocket
        self.realtime_websocket = realtime_websocket
        self.stream_sid: Optional[str] = None
        self.account_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self.media_format: Optional[str] = None
        self.session_initialized = False
        self.speech_detected = False
        self._closed = False

        # Audio buffer tracking for debugging
        self.audio_chunks_sent = 0
        self.total_audio_bytes_sent = 0
        self.audio_buffer = []

        # Transcript buffers for logging full transcripts
        self.input_transcript_buffer = []  # User → AI
        self.output_transcript_buffer = []  # AI → User

        # Mark counter for audio synchronization
        self.mark_counter = 0

        # Initialize function handler
        self.function_handler = FunctionHandler(realtime_websocket)

        # Create event handler mappings for Twilio events
        self.twilio_event_handlers = {
            TwilioEventType.CONNECTED: self.handle_connected,
            TwilioEventType.START: self.handle_start,
            TwilioEventType.MEDIA: self.handle_media,
            TwilioEventType.STOP: self.handle_stop,
            TwilioEventType.DTMF: self.handle_dtmf,
            TwilioEventType.MARK: self.handle_mark,
        }

        # Create event handler mappings for realtime events
        self.realtime_event_handlers = {
            # Session events
            ServerEventType.SESSION_UPDATED: self.handle_session_update,
            ServerEventType.SESSION_CREATED: self.handle_session_update,
            # Conversation events
            ServerEventType.CONVERSATION_ITEM_CREATED: lambda x: logger.info(
                "Conversation item created"
            ),
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
            # Add new handler for function call events
            ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA: self.function_handler.handle_function_call_arguments_delta,
            ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE: self.function_handler.handle_function_call_arguments_done,
        }

    async def close(self):
        """Safely close both WebSocket connections.

        This method ensures both the Twilio and OpenAI Realtime API WebSocket connections
        are properly closed, handling any exceptions that may occur during the process.
        """
        if not self._closed:
            self._closed = True
            try:
                if (
                    self.realtime_websocket
                    and self.realtime_websocket.close_code is None
                ):
                    await self.realtime_websocket.close()
            except Exception as e:
                logger.error(f"Error closing OpenAI connection: {e}")
            try:
                if self.twilio_websocket and not self._is_websocket_closed():
                    await self.twilio_websocket.close()
            except Exception as e:
                logger.error(f"Error closing Twilio connection: {e}")

    def _is_websocket_closed(self):
        """Check if Twilio WebSocket is closed.

        Returns True if the WebSocket is closed or in an unusable state.
        """
        try:
            from starlette.websockets import WebSocketState

            return (
                not self.twilio_websocket
                or self.twilio_websocket.client_state == WebSocketState.DISCONNECTED
            )
        except ImportError:
            # Fallback check without WebSocketState
            return not self.twilio_websocket

    async def handle_connected(self, data):
        """Handle 'connected' message from Twilio.

        This is the first message sent by Twilio when a WebSocket connection is established.

        Args:
            data (dict): Connected message data
        """
        logger.info(f"Twilio connected: {data}")
        connected_msg = ConnectedMessage(**data)
        logger.info(
            f"Protocol: {connected_msg.protocol}, Version: {connected_msg.version}"
        )

    async def handle_start(self, data):
        """Handle 'start' message from Twilio.

        Contains metadata about the stream including stream SID, call SID, and media format.

        Args:
            data (dict): Start message data
        """
        logger.info(f"Twilio stream start: {data}")
        start_msg = StartMessage(**data)

        self.stream_sid = start_msg.streamSid
        self.account_sid = start_msg.start.accountSid
        self.call_sid = start_msg.start.callSid
        self.media_format = start_msg.start.mediaFormat.encoding

        logger.info(f"Stream started - SID: {self.stream_sid}, Call: {self.call_sid}")
        logger.info(
            f"Media format: {start_msg.start.mediaFormat.encoding}, "
            f"Sample rate: {start_msg.start.mediaFormat.sampleRate}, "
            f"Channels: {start_msg.start.mediaFormat.channels}"
        )
        logger.info(f"Tracks: {start_msg.start.tracks}")

        # Initialize OpenAI session if not already done
        if not self.session_initialized:
            await self.initialize_openai_session()

    async def handle_media(self, data):
        """Handle 'media' message containing audio data from Twilio.

        This method processes audio chunks and forwards them to the OpenAI Realtime API
        for processing. Audio from Twilio is in mulaw format which needs conversion.

        Args:
            data (dict): Media message data containing audio
        """
        if not self._closed and self.realtime_websocket.close_code is None:
            try:
                media_msg = MediaMessage(**data)
                audio_payload = media_msg.media.payload

                try:
                    # Decode base64 to get mulaw audio bytes
                    mulaw_bytes = base64.b64decode(audio_payload)

                    # Convert mulaw to pcm16 for OpenAI (simplified - you may want a proper conversion)
                    # For now, we'll buffer and process the audio
                    self.audio_buffer.append(mulaw_bytes)

                    # Process audio in chunks
                    if len(self.audio_buffer) >= 10:  # Process every 10 chunks
                        combined_audio = b"".join(self.audio_buffer)

                        # Convert mulaw to pcm16 (placeholder - implement proper conversion)
                        pcm16_audio = self._convert_mulaw_to_pcm16(combined_audio)
                        pcm16_b64 = base64.b64encode(pcm16_audio).decode("utf-8")

                        # Send to OpenAI
                        audio_append = InputAudioBufferAppendEvent(
                            type="input_audio_buffer.append", audio=pcm16_b64
                        )
                        await self.realtime_websocket.send(audio_append.model_dump_json())

                        self.audio_chunks_sent += 1
                        self.total_audio_bytes_sent += len(pcm16_audio)

                        logger.debug(
                            f"Sent combined audio chunk to OpenAI (mulaw->pcm16 conversion)"
                        )

                        # Clear buffer
                        self.audio_buffer.clear()

                except Exception as e:
                    logger.error(f"Error processing Twilio media: {e}")
            except Exception as e:
                logger.error(f"Error parsing Twilio media message: {e}")

    def _convert_mulaw_to_pcm16(self, mulaw_data: bytes) -> bytes:
        """Convert mulaw audio to pcm16 format.

        This is a placeholder implementation. For production, use a proper audio
        conversion library like audioop or pydub.

        Args:
            mulaw_data: Raw mulaw audio bytes

        Returns:
            bytes: PCM16 audio data
        """
        try:
            import audioop

            # Convert mulaw to linear PCM
            linear_data = audioop.ulaw2lin(
                mulaw_data, 2
            )  # 2 bytes per sample for 16-bit
            return linear_data
        except ImportError:
            logger.warning("audioop not available, using placeholder conversion")
            # Simple placeholder - just repeat each byte twice to simulate 16-bit
            # This is NOT proper audio conversion and will sound terrible
            return b"".join([bytes([b, b]) for b in mulaw_data])

    async def handle_stop(self, data):
        """Handle 'stop' message from Twilio.

        Sent when the stream has stopped or the call has ended.

        Args:
            data (dict): Stop message data
        """
        logger.info(f"Twilio stream stop: {data}")
        stop_msg = StopMessage(**data)

        # Commit any remaining audio buffer
        if self.audio_buffer and not self._closed:
            await self._commit_audio_buffer()

        logger.info(f"Stream stopped for call: {stop_msg.stop.callSid}")
        await self.close()

    async def handle_dtmf(self, data):
        """Handle 'dtmf' message from Twilio.

        Sent when a user presses a touch-tone key.

        Args:
            data (dict): DTMF message data
        """
        dtmf_msg = DTMFMessage(**data)
        digit = dtmf_msg.dtmf.digit
        logger.info(f"DTMF digit pressed: {digit}")

        # You could send this as a text message to OpenAI if needed
        # For now, just log it

    async def handle_mark(self, data):
        """Handle 'mark' message from Twilio.

        Sent when audio playback is complete (response to marks we send).

        Args:
            data (dict): Mark message data
        """
        mark_msg = MarkMessage(**data)
        logger.info(f"Audio playback completed for mark: {mark_msg.mark.name}")

    async def _commit_audio_buffer(self):
        """Commit any remaining audio in the buffer to OpenAI."""
        if self.audio_buffer and not self._closed:
            try:
                combined_audio = b"".join(self.audio_buffer)
                pcm16_audio = self._convert_mulaw_to_pcm16(combined_audio)
                pcm16_b64 = base64.b64encode(pcm16_audio).decode("utf-8")

                # Send to OpenAI
                audio_append = InputAudioBufferAppendEvent(
                    type="input_audio_buffer.append", audio=pcm16_b64
                )
                await self.realtime_websocket.send(audio_append.model_dump_json())

                # Commit the buffer
                buffer_commit = InputAudioBufferCommitEvent(
                    type="input_audio_buffer.commit"
                )
                await self.realtime_websocket.send(buffer_commit.model_dump_json())

                # Trigger response
                await self._trigger_response()

                logger.info("Committed remaining audio buffer to OpenAI")
                self.audio_buffer.clear()

            except Exception as e:
                logger.error(f"Error committing audio buffer: {e}")

    async def _trigger_response(self):
        """Trigger a response from OpenAI after committing audio."""
        try:
            response_create = {
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"],
                    "output_audio_format": "pcm16",
                    "temperature": 0.8,
                    "max_output_tokens": 4096,
                    "voice": VOICE,
                },
            }
            await self.realtime_websocket.send(json.dumps(response_create))
            logger.info("Response creation triggered")
        except Exception as e:
            logger.error(f"Error triggering response: {e}")

    # OpenAI event handlers (similar to AudioCodes bridge)

    async def handle_session_update(self, response_dict):
        """Handle session update events from the OpenAI Realtime API."""
        response_type = response_dict["type"]

        if response_type == ServerEventType.SESSION_UPDATED:
            logger.info("OpenAI session updated successfully")
        elif response_type == ServerEventType.SESSION_CREATED:
            logger.info("OpenAI session created successfully")
            self.session_initialized = True
            try:
                await self.send_initial_conversation_item()
            except Exception as e:
                logger.error(f"Error sending initial conversation item: {e}")

    async def handle_speech_detection(self, response_dict):
        """Handle speech detection events from the OpenAI Realtime API."""
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

        Converts PCM16 audio from OpenAI to mulaw and sends to Twilio.
        """
        try:
            audio_delta = ResponseAudioDeltaEvent(**response_dict)

            if self._closed or not self.stream_sid:
                logger.debug(
                    "Skipping audio delta - connection closed or no stream SID"
                )
                return

            if not self.twilio_websocket or self._is_websocket_closed():
                logger.debug("Skipping audio delta - Twilio websocket is closed")
                return

            # Convert PCM16 to mulaw for Twilio
            pcm16_data = base64.b64decode(audio_delta.delta)
            mulaw_data = self._convert_pcm16_to_mulaw(pcm16_data)
            mulaw_b64 = base64.b64encode(mulaw_data).decode("utf-8")

            # Send audio to Twilio
            media_message = OutgoingMediaMessage(
                event="media", streamSid=self.stream_sid, media={"payload": mulaw_b64}
            )

            await self.twilio_websocket.send_json(media_message.model_dump())
            logger.debug(f"Sent audio to Twilio (size: {len(mulaw_b64)} bytes mulaw)")

        except Exception as e:
            logger.error(f"Error processing audio response delta: {e}")

    def _convert_pcm16_to_mulaw(self, pcm16_data: bytes) -> bytes:
        """Convert PCM16 audio to mulaw format for Twilio.

        Args:
            pcm16_data: PCM16 audio bytes

        Returns:
            bytes: Mulaw audio data
        """
        try:
            import audioop

            # Convert linear PCM to mulaw
            mulaw_data = audioop.lin2ulaw(pcm16_data, 2)  # 2 bytes per sample
            return mulaw_data
        except ImportError:
            logger.warning("audioop not available, using placeholder conversion")
            # Simple placeholder - take every other byte
            # This is NOT proper audio conversion
            return pcm16_data[::2]

    async def handle_audio_response_completion(self, response_dict):
        """Handle audio response completion events from OpenAI."""
        logger.info("Audio response completed")

        # Send a mark to track when this audio finishes playing
        if self.stream_sid:
            self.mark_counter += 1
            mark_name = f"audio_complete_{self.mark_counter}"

            mark_message = OutgoingMarkMessage(
                event="mark", streamSid=self.stream_sid, mark={"name": mark_name}
            )

            await self.twilio_websocket.send_json(mark_message.model_dump())
            logger.info(f"Sent mark to Twilio: {mark_name}")

    async def handle_response_completion(self, response_dict):
        """Handle response completion events from OpenAI."""
        logger.info("Response completed")

    # Additional handlers (similar to AudioCodes bridge)

    async def handle_text_and_transcript(self, response_dict):
        """Handle text and transcript events from OpenAI."""
        response_type = response_dict["type"]

        if response_type == ServerEventType.RESPONSE_TEXT_DELTA:
            text_delta = ResponseTextDeltaEvent(**response_dict)
            logger.info(f"Text delta received: {text_delta.delta}")

    async def handle_audio_transcript_delta(self, response_dict):
        """Handle audio transcript delta events from OpenAI."""
        delta = response_dict.get("delta", "")
        if delta:
            self.output_transcript_buffer.append(delta)
        logger.debug(f"Audio transcript delta: {delta}")

    async def handle_audio_transcript_done(self, response_dict):
        """Handle audio transcript completion events from OpenAI."""
        full_transcript = "".join(self.output_transcript_buffer)
        logger.info(f"Full AI transcript: {full_transcript}")
        self.output_transcript_buffer.clear()

    async def handle_input_audio_transcription_delta(self, response_dict):
        """Handle input audio transcription delta events from OpenAI."""
        delta = response_dict.get("delta", "")
        if delta:
            self.input_transcript_buffer.append(delta)
        logger.debug(f"Input audio transcription delta: {delta}")

    async def handle_input_audio_transcription_completed(self, response_dict):
        """Handle input audio transcription completion events from OpenAI."""
        full_transcript = "".join(self.input_transcript_buffer)
        logger.info(f"Full user transcript: {full_transcript}")
        self.input_transcript_buffer.clear()

    async def handle_output_item_added(self, response_dict):
        """Handle output item added events from OpenAI."""
        item = response_dict.get("item", {})
        logger.info(f"Output item added: {item}")

        # Handle function calls similar to AudioCodes bridge
        if item.get("type") == "function_call":
            call_id = item.get("call_id")
            function_name = item.get("name")
            item_id = item.get("id")

            if call_id and function_name:
                if call_id not in self.function_handler.active_function_calls:
                    self.function_handler.active_function_calls[call_id] = {
                        "arguments_buffer": "",
                        "item_id": item_id,
                        "output_index": response_dict.get("output_index", 0),
                        "response_id": response_dict.get("response_id"),
                        "function_name": function_name,
                    }
                else:
                    self.function_handler.active_function_calls[call_id][
                        "function_name"
                    ] = function_name

                logger.info(
                    f"Function call captured: {function_name} (call_id: {call_id})"
                )

    async def handle_content_part_added(self, response_dict):
        """Handle content part added events from OpenAI."""
        logger.info(f"Content part added: {response_dict.get('part', {})}")

    async def handle_content_part_done(self, response_dict):
        """Handle content part completion events from OpenAI."""
        logger.info("Content part completed")

    async def handle_output_item_done(self, response_dict):
        """Handle output item completion events from OpenAI."""
        logger.info("Output item completed")

    def _get_twilio_event_type(self, event_str):
        """Convert a string event type to a TwilioEventType enum value."""
        try:
            return TwilioEventType(event_str)
        except ValueError:
            return None

    async def receive_from_twilio(self):
        """Receive and process messages from Twilio Media Streams WebSocket."""
        try:
            async for message in self.twilio_websocket.iter_text():
                if self._closed:
                    break

                data = json.loads(message)
                event_str = data["event"]

                # Convert string event type to enum
                event_type = self._get_twilio_event_type(event_str)

                if event_type:
                    # Log message type (with size for media messages)
                    if event_type == TwilioEventType.MEDIA:
                        payload_size = len(data.get("media", {}).get("payload", ""))
                        logger.debug(
                            f"Received Twilio {event_str} (payload: {payload_size} bytes)"
                        )
                    else:
                        logger.info(f"Received Twilio {event_str}")

                    # Dispatch to appropriate handler
                    handler = self.twilio_event_handlers.get(event_type)
                    if handler:
                        await handler(data)

                        # Break loop on stop event
                        if event_type == TwilioEventType.STOP:
                            break
                    else:
                        logger.warning(f"No handler for Twilio event: {event_type}")
                else:
                    logger.warning(f"Unknown Twilio event type: {event_str}")

        except WebSocketDisconnect:
            logger.info("Twilio disconnected")
            await self.close()
        except Exception as e:
            logger.error(f"Error in receive_from_twilio: {e}")
            await self.close()

    async def receive_from_realtime(self):
        """Receive and process events from the OpenAI Realtime API."""
        try:
            async for openai_message in self.realtime_websocket:
                if self._closed:
                    break

                response_dict = json.loads(openai_message)
                response_type = response_dict["type"]
                logger.debug(f"Received OpenAI message type: {response_type}")

                # Handle log events first
                if response_type in [event.value for event in LOG_EVENT_TYPES]:
                    await self.handle_log_event(response_dict)
                    continue

                # Dispatch to appropriate handler
                handler = self.realtime_event_handlers.get(response_type)
                if handler:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(response_dict)
                        else:
                            handler(response_dict)
                    except Exception as e:
                        logger.error(f"Error in handler for {response_type}: {e}")
                else:
                    logger.warning(f"Unknown OpenAI event type: {response_type}")

        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"OpenAI WebSocket connection closed: {e}")
            await self.close()
        except Exception as e:
            logger.error(f"Error in receive_from_realtime: {e}")
            if not self._closed:
                await self.close()

    async def handle_log_event(self, response_dict):
        """Handle log events from OpenAI (similar to AudioCodes bridge)."""
        response_type = response_dict["type"]

        if response_type == "error":
            error_code = response_dict.get("code", "unknown")
            error_message = response_dict.get("message", "No message provided")
            logger.error(f"OpenAI Error: {error_code} - {error_message}")

    async def initialize_openai_session(self):
        """Initialize the OpenAI Realtime API session."""
        session_config = SessionConfig(
            input_audio_format="pcm16",
            output_audio_format="pcm16",
            voice=VOICE,
            instructions=SYSTEM_MESSAGE,
            modalities=["text", "audio"],
            temperature=0.8,
            model=DEFAULT_MODEL,
            tools=[
                # Add your function tools here (same as AudioCodes bridge)
                {
                    "type": "function",
                    "name": "call_intent",
                    "description": "Get the user's intent.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "intent": {
                                "type": "string",
                                "enum": [
                                    "card_replacement",
                                    "account_inquiry",
                                    "other",
                                ],
                            },
                        },
                        "required": ["intent"],
                    },
                },
                # Add other tools as needed...
            ],
            input_audio_noise_reduction={"type": "near_field"},
            input_audio_transcription={"model": "whisper-1"},
            max_response_output_tokens=4096,
            tool_choice="auto",
        )

        session_update = SessionUpdateEvent(
            type="session.update", session=session_config
        )
        logger.info("Initializing OpenAI session for Twilio bridge")
        await self.realtime_websocket.send(session_update.model_dump_json())

    async def send_initial_conversation_item(self):
        """Send initial conversation item to start the AI interaction."""
        try:
            initial_conversation = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "You are a customer service agent for Bank of Peril. Start by saying 'Hello! How can I help you today?'",
                        }
                    ],
                },
            }

            await self.realtime_websocket.send(json.dumps(initial_conversation))
            await asyncio.sleep(1)

            # Trigger initial response
            await self._trigger_response()
            logger.info("Initial conversation flow initiated")

        except Exception as e:
            logger.error(f"Error sending initial conversation item: {e}")
