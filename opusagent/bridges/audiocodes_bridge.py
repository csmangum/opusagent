"""AudioCodes-specific implementation of the real-time bridge.

This module provides the AudioCodes-specific implementation of the base bridge class,
handling AudioCodes-specific event types, message formats, and responses.

The AudioCodesBridge class extends BaseRealtimeBridge to provide:
- AudioCodes-specific event handling (session management, audio streams, activities)
- Proper message formatting for AudioCodes WebSocket protocol
- Voice Activity Detection (VAD) event forwarding
- Direct audio streaming (AudioCodes natively supports 24kHz PCM16)
- Participant tracking for multi-party calls

Example:
    ```python
    bridge = AudioCodesBridge(
        platform_websocket=websocket,
        realtime_websocket=realtime_ws,
        vad_enabled=True
    )
    await bridge.start()
    ```
"""

import base64
import uuid
from typing import Any, Dict

from opusagent.bridges.base_bridge import BaseRealtimeBridge
from opusagent.config.logging_config import configure_logging
from opusagent.models.audiocodes_api import (
    ConnectionValidatedResponse,
    PlayStreamChunkMessage,
    PlayStreamStartMessage,
    SessionAcceptedResponse,
    TelephonyEventType,
    UserStreamSpeechCommittedResponse,
    UserStreamSpeechStartedResponse,
    UserStreamSpeechStoppedResponse,
    UserStreamStartedResponse,
    UserStreamStoppedResponse,
)
from opusagent.models.openai_api import ResponseAudioDeltaEvent

logger = configure_logging("audiocodes_bridge")


class AudioCodesBridge(BaseRealtimeBridge):
    """AudioCodes-specific implementation of the real-time bridge.

    This class implements the AudioCodes-specific event handling and message formatting
    while inheriting the core bridge functionality from BaseRealtimeBridge.

    The bridge handles the complete lifecycle of AudioCodes telephony sessions:
    - Session initiation and acceptance
    - Real-time audio streaming in both directions
    - Voice Activity Detection (VAD) event forwarding
    - DTMF and hangup activity handling
    - Session resumption and termination

    Attributes:
        current_participant (str): The current participant identifier, defaults to "caller"
        media_format (str): The audio media format supported by the session

    Example:
        ```python
        bridge = AudioCodesBridge(
            platform_websocket=audiocodes_ws,
            realtime_websocket=openai_ws,
            vad_enabled=True
        )
        await bridge.start()
        ```
    """

    def __init__(self, *args, **kwargs):
        """Initialize AudioCodes bridge with participant tracking.

        Args:
            *args: Positional arguments passed to BaseRealtimeBridge
            **kwargs: Keyword arguments passed to BaseRealtimeBridge

        Note:
            Sets bridge_type to "audiocodes" and initializes participant tracking.
            Overrides the audio handler's outgoing audio method to use AudioCodes-specific
            audio processing with direct 24kHz PCM16 streaming (no resampling needed).
        """
        super().__init__(*args, bridge_type="audiocodes", **kwargs)
        self.current_participant: str = (
            "caller"  # Default participant for single-party calls
        )

        # Override the audio handler's outgoing audio method to use AudioCodes-specific sending
        self.audio_handler.handle_outgoing_audio = self.handle_outgoing_audio_audiocodes

    def register_platform_event_handlers(self):
        """Register AudioCodes-specific event handlers with the event router.

        Registers handlers for all AudioCodes telephony events:
        - Session management (initiate, resume, end)
        - Audio streaming (start, chunk, stop)
        - Activities (DTMF, hangup, etc.)
        - Connection validation
        - VAD events (if enabled)

        Note:
            VAD event handlers are only registered if VAD is enabled in the bridge
            configuration. These handlers forward OpenAI Realtime API VAD events
            to AudioCodes as speech detection events.
        """
        self.event_router.register_platform_handler(
            TelephonyEventType.SESSION_INITIATE, self.handle_session_start
        )
        self.event_router.register_platform_handler(
            TelephonyEventType.SESSION_RESUME, self.handle_session_resume
        )
        self.event_router.register_platform_handler(
            TelephonyEventType.USER_STREAM_START, self.handle_audio_start
        )
        self.event_router.register_platform_handler(
            TelephonyEventType.USER_STREAM_CHUNK, self.handle_audio_data
        )
        self.event_router.register_platform_handler(
            TelephonyEventType.USER_STREAM_STOP, self.handle_audio_end
        )
        self.event_router.register_platform_handler(
            TelephonyEventType.SESSION_END, self.handle_session_end
        )
        self.event_router.register_platform_handler(
            TelephonyEventType.ACTIVITIES, self.handle_activities
        )
        self.event_router.register_platform_handler(
            TelephonyEventType.CONNECTION_VALIDATE, self.handle_connection_validate
        )

        # Register handlers for VAD speech events from AudioCodes platform
        self.event_router.register_platform_handler(
            TelephonyEventType.USER_STREAM_SPEECH_STARTED,
            self.handle_platform_speech_started,
        )
        self.event_router.register_platform_handler(
            TelephonyEventType.USER_STREAM_SPEECH_STOPPED,
            self.handle_platform_speech_stopped,
        )
        self.event_router.register_platform_handler(
            TelephonyEventType.USER_STREAM_SPEECH_COMMITTED,
            self.handle_platform_speech_committed,
        )
        self.event_router.register_platform_handler(
            TelephonyEventType.USER_STREAM_SPEECH_HYPOTHESIS,
            self.handle_platform_speech_hypothesis,
        )

        # Register handlers for VAD speech events from OpenAI Realtime API only if VAD is enabled
        if self.vad_enabled:
            logger.info("Registering VAD event handlers for OpenAI Realtime API")
            self.event_router.register_realtime_handler(
                "input_audio_buffer.speech_started", self.handle_speech_started
            )
            self.event_router.register_realtime_handler(
                "input_audio_buffer.speech_stopped", self.handle_speech_stopped
            )
            self.event_router.register_realtime_handler(
                "input_audio_buffer.committed", self.handle_speech_committed
            )
        else:
            logger.info("VAD disabled - skipping VAD event handler registration")

    async def send_platform_json(self, payload: dict):
        """Send JSON payload to the AudioCodes WebSocket.

        Args:
            payload (dict): The JSON payload to send to AudioCodes

        Raises:
            WebSocketException: If the WebSocket connection is closed or unavailable
            Exception: For other WebSocket-related errors

        Note:
            This method is used by all AudioCodes-specific response methods to
            send properly formatted messages back to the AudioCodes platform.
        """
        # Check if connection is still active before sending
        if self._closed or not self.platform_websocket or self._is_websocket_closed():
            logger.debug("Skipping platform message - connection closed or unavailable")
            return

        try:
            await self.platform_websocket.send_json(payload)
        except Exception as e:
            logger.error(f"Failed to send platform message: {e}")
            # Don't raise the exception to prevent cascading failures

    async def handle_session_start(self, data: dict):
        """Handle session initiation from AudioCodes.

        Processes the initial session setup message from AudioCodes, extracts
        conversation ID and media format, and initializes the conversation
        with the OpenAI Realtime API.

        Args:
            data (dict): Session initiate message data containing:
                - conversationId (str): Unique identifier for the conversation
                - supportedMediaFormats (list): List of supported audio formats

        Note:
            Sets the media_format attribute and calls initialize_conversation()
            to establish the OpenAI Realtime API connection. Sends a session
            accepted response back to AudioCodes.
        """
        logger.info(f"Session initiate received: {data}")
        conversation_id = data.get("conversationId")
        supported_formats = data.get("supportedMediaFormats", ["raw/lpcm16"])

        # Prefer 24kHz format if available (AudioCodes supports it natively)
        if "raw/lpcm16_24" in supported_formats:
            self.media_format = "raw/lpcm16_24"
            logger.info("Using 24kHz PCM16 format for optimal audio quality")
        else:
            self.media_format = supported_formats[0]
            logger.info(f"Using media format: {self.media_format}")

        await self.initialize_conversation(conversation_id)
        await self.send_session_accepted()

    async def handle_audio_start(self, data: dict):
        """Handle start of user audio stream from AudioCodes.

        Processes the beginning of an incoming audio stream from the caller.
        Extracts participant information for multi-party calls and resets
        audio tracking counters.

        Args:
            data (dict): User stream start message data containing:
                - participant (str, optional): Participant identifier for multi-party calls

        Note:
            Updates current_participant if provided, resets audio tracking
            counters, and sends a user stream started response to AudioCodes.
        """
        logger.info(f"User stream start received: {data}")

        # Extract participant if provided (for Agent Assist mode)
        participant = data.get("participant")
        if participant:
            self.current_participant = participant
            logger.info(f"Audio stream participant: {participant}")

        # Reset audio tracking counters for new stream
        self.audio_chunks_sent = 0
        self.total_audio_bytes_sent = 0

        # Send user stream started response
        await self.send_user_stream_started()

    async def handle_audio_data(self, data: dict):
        """Handle chunk of user audio data from AudioCodes.

        Processes incoming audio chunks from the caller and forwards them
        to the audio handler for processing and transmission to OpenAI.

        Args:
            data (dict): User stream chunk message data containing:
                - audioChunk (str): Base64-encoded audio data
                - participant (str, optional): Participant identifier

        Note:
            This method delegates to the audio handler which manages the
            audio processing pipeline including buffering and forwarding
            to the OpenAI Realtime API.
        """
        await self.audio_handler.handle_incoming_audio(data)

    async def handle_audio_end(self, data: dict):
        """Handle end of user audio stream from AudioCodes.

        Processes the end of an incoming audio stream and triggers
        audio commit processing to generate responses.

        Args:
            data (dict): User stream stop message data

        Note:
            Sends a user stream stopped response to AudioCodes and calls
            handle_audio_commit() to process the completed audio and
            generate appropriate responses.
        """
        logger.info(
            f"User stream stop received for conversation: {self.conversation_id}"
        )

        # Send user stream stopped response
        await self.send_user_stream_stopped()

        # Handle audio commit and response triggering
        await self.handle_audio_commit()

    async def handle_session_end(self, data: dict):
        """Handle end of session from AudioCodes.

        Processes session termination requests from AudioCodes and
        performs cleanup operations.

        Args:
            data (dict): Session end message data containing:
                - reason (str): Reason for session termination

        Note:
            Logs the session end reason and calls close() to perform
            proper cleanup of all connections and resources.
        """
        logger.info(f"Session end received: {data.get('reason', 'No reason provided')}")
        await self.close()
        logger.info("AudioCodes-Realtime bridge closed")

    async def handle_session_resume(self, data: dict):
        """Handle session resume from AudioCodes.

        Processes session resumption requests from AudioCodes and attempts
        to restore session state from persistent storage.

        Args:
            data (dict): Session resume message data containing:
                - conversationId (str): Unique identifier for the conversation
                - supportedMediaFormats (list): List of supported audio formats

        Note:
            This method attempts to restore the session state from storage.
            If successful, it restores conversation context, audio buffers,
            and function state. If unsuccessful, it falls back to creating
            a new session.
        """
        logger.info(f"Session resume received: {data}")
        conversation_id = data.get("conversationId")
        supported_formats = data.get("supportedMediaFormats", ["raw/lpcm16"])

        # Prefer 24kHz format if available (AudioCodes supports it natively)
        if "raw/lpcm16_24" in supported_formats:
            self.media_format = "raw/lpcm16_24"
            logger.info("Using 24kHz PCM16 format for optimal audio quality")
        else:
            self.media_format = supported_formats[0]
            logger.info(f"Using media format: {self.media_format}")

        try:
            # Initialize conversation (will attempt resume)
            await self.initialize_conversation(conversation_id)

            if self.session_state and self.session_state.resumed_count > 0:
                # Successfully resumed
                await self.send_session_resumed()
                logger.info(f"Session resumed successfully: {conversation_id}")
            else:
                # Failed to resume, treat as new session
                await self.send_session_accepted()
                logger.info(
                    f"Session resume failed, created new session: {conversation_id}"
                )

        except Exception as e:
            logger.error(f"Error during session resume: {e}")
            # Fall back to new session creation
            await self.initialize_conversation(conversation_id)
            await self.send_session_accepted()

    async def handle_activities(self, data: dict):
        """Handle activities/events from AudioCodes.

        Processes various telephony activities such as DTMF tones,
        hangup requests, and call start events.

        Args:
            data (dict): Activities message data containing:
                - activities (list): List of activity objects with type, name, and value

        Note:
            Currently handles:
            - DTMF events: Logs the DTMF value (could be routed to function handlers)
            - Hangup events: Initiates call termination
            - Start events: Logs call start
            - Unknown activities: Logs for debugging purposes
        """
        logger.info(f"Activities received: {data}")
        activities = data.get("activities", [])

        for activity in activities:
            activity_type = activity.get("type")
            activity_name = activity.get("name")
            activity_value = activity.get("value")

            logger.info(
                f"Processing activity: {activity_type}/{activity_name} = {activity_value}"
            )

            if activity_name == "dtmf":
                # Handle DTMF event
                logger.info(f"DTMF event received: {activity_value}")
                # You could route this to a function handler or process it directly

            elif activity_name == "hangup":
                # Handle hangup event
                logger.info("Hangup event received")
                await self.hang_up("User requested hangup")

            elif activity_name == "start":
                # Handle call start event
                logger.info("Call start event received")

            else:
                logger.info(f"Unknown activity: {activity_name}")

    async def handle_connection_validate(self, data: dict):
        """Handle connection validation from AudioCodes.

        Processes connection validation requests from AudioCodes and
        responds with validation confirmation.

        Args:
            data (dict): Connection validate message data

        Note:
            Sends a connection validated response to confirm the WebSocket
            connection is healthy and ready for communication.
        """
        logger.info(f"Connection validation received: {data}")

        # Send connection validated response
        await self.send_connection_validated()

    async def handle_speech_started(self, data: dict):
        """Handle speech started event from OpenAI Realtime API.

        Processes VAD speech start events from OpenAI and forwards them
        to AudioCodes as speech detection events.

        Args:
            data (dict): Speech started event data from OpenAI Realtime API

        Note:
            Only processes events if VAD is enabled. Sends a speech started
            response to AudioCodes to indicate the caller has begun speaking.
        """
        if not self.vad_enabled:
            logger.warning("VAD disabled - ignoring speech started event")
            return

        logger.info("Speech started detected - sending to AudioCodes")
        await self.send_speech_started()

    async def handle_speech_stopped(self, data: dict):
        """Handle speech stopped event from OpenAI Realtime API.

        Processes VAD speech stop events from OpenAI and forwards them
        to AudioCodes as speech detection events.

        Args:
            data (dict): Speech stopped event data from OpenAI Realtime API

        Note:
            Only processes events if VAD is enabled. Sends a speech stopped
            response to AudioCodes to indicate the caller has stopped speaking.
        """
        if not self.vad_enabled:
            logger.warning("VAD disabled - ignoring speech stopped event")
            return

        logger.info("Speech stopped detected - sending to AudioCodes")
        await self.send_speech_stopped()

    async def handle_speech_committed(self, data: dict):
        """Handle speech committed event from OpenAI Realtime API.

        Processes VAD speech commit events from OpenAI and forwards them
        to AudioCodes as speech detection events.

        Args:
            data (dict): Speech committed event data from OpenAI Realtime API

        Note:
            Only processes events if VAD is enabled. Sends a speech committed
            response to AudioCodes to indicate the speech segment has been
            committed for processing.
        """
        if not self.vad_enabled:
            logger.warning("VAD disabled - ignoring speech committed event")
            return

        logger.info("Speech committed detected - sending to AudioCodes")
        await self.send_speech_committed()

    async def handle_platform_speech_started(self, data: dict):
        """Handle speech started event from AudioCodes platform.

        This method processes speech started events that come from AudioCodes
        itself, indicating that AudioCodes has detected the start of speech.

        Args:
            data (dict): Speech started event data from AudioCodes platform

        Note:
            This handler processes VAD events that originate from AudioCodes,
            as opposed to those that come from the OpenAI Realtime API.
        """
        logger.info("Speech started event from AudioCodes platform")
        # Log the event details for debugging
        if "participant" in data:
            logger.info(f"Speech started for participant: {data['participant']}")
        if "participantId" in data:
            logger.info(f"Speech started for participant ID: {data['participantId']}")

    async def handle_platform_speech_stopped(self, data: dict):
        """Handle speech stopped event from AudioCodes platform.

        This method processes speech stopped events that come from AudioCodes
        itself, indicating that AudioCodes has detected the end of speech.

        Args:
            data (dict): Speech stopped event data from AudioCodes platform

        Note:
            This handler processes VAD events that originate from AudioCodes,
            as opposed to those that come from the OpenAI Realtime API.
        """
        logger.info("Speech stopped event from AudioCodes platform")
        # Log the event details for debugging
        if "participant" in data:
            logger.info(f"Speech stopped for participant: {data['participant']}")
        if "participantId" in data:
            logger.info(f"Speech stopped for participant ID: {data['participantId']}")

    async def handle_platform_speech_committed(self, data: dict):
        """Handle speech committed event from AudioCodes platform.

        This method processes speech committed events that come from AudioCodes
        itself, indicating that AudioCodes has committed speech for processing.

        Args:
            data (dict): Speech committed event data from AudioCodes platform

        Note:
            This handler processes VAD events that originate from AudioCodes,
            as opposed to those that come from the OpenAI Realtime API.
        """
        logger.info("Speech committed event from AudioCodes platform")
        # Log the event details for debugging
        if "participant" in data:
            logger.info(f"Speech committed for participant: {data['participant']}")
        if "participantId" in data:
            logger.info(f"Speech committed for participant ID: {data['participantId']}")

    async def handle_platform_speech_hypothesis(self, data: dict):
        """Handle speech hypothesis event from AudioCodes platform.

        This method processes speech hypothesis events that come from AudioCodes
        itself, indicating that AudioCodes has detected interim speech recognition
        results.

        Args:
            data (dict): Speech hypothesis event data from AudioCodes platform

        Note:
            This handler processes VAD events that originate from AudioCodes,
            as opposed to those that come from the OpenAI Realtime API.
        """
        logger.info("Speech hypothesis event from AudioCodes platform")
        # Log the event details for debugging
        if "participant" in data:
            logger.info(f"Speech hypothesis for participant: {data['participant']}")
        if "participantId" in data:
            logger.info(
                f"Speech hypothesis for participant ID: {data['participantId']}"
            )
        if "alternatives" in data:
            logger.info(f"Speech hypothesis alternatives: {data['alternatives']}")

    async def send_session_accepted(self):
        """Send AudioCodes-specific session accepted response.

        Sends a session accepted message to AudioCodes confirming the
        session has been established and is ready for audio communication.

        Note:
            Includes conversation ID, media format, and participant information
            in the response. Uses the current media format or defaults to
            "raw/lpcm16" if not specified.
        """
        kwargs = {
            "type": TelephonyEventType.SESSION_ACCEPTED,
            "conversationId": self.conversation_id,
            "mediaFormat": self.media_format or "raw/lpcm16",
            "participant": self.current_participant,
        }
        await self.send_platform_json(SessionAcceptedResponse(**kwargs).model_dump())

    async def send_user_stream_started(self):
        """Send AudioCodes-specific user stream started response.

        Sends a user stream started message to AudioCodes confirming
        that the incoming audio stream has been acknowledged.

        Note:
            Includes conversation ID and participant information in the response.
        """
        kwargs = {
            "type": TelephonyEventType.USER_STREAM_STARTED,
            "conversationId": self.conversation_id,
            "participant": self.current_participant,
        }
        await self.send_platform_json(UserStreamStartedResponse(**kwargs).model_dump())

    async def send_user_stream_stopped(self):
        """Send AudioCodes-specific user stream stopped response.

        Sends a user stream stopped message to AudioCodes confirming
        that the end of the incoming audio stream has been acknowledged.

        Note:
            Includes conversation ID and participant information in the response.
        """
        kwargs = {
            "type": TelephonyEventType.USER_STREAM_STOPPED,
            "conversationId": self.conversation_id,
            "participant": self.current_participant,
        }
        await self.send_platform_json(UserStreamStoppedResponse(**kwargs).model_dump())

    async def send_speech_started(self):
        """Send AudioCodes-specific speech started response.

        Sends a speech started message to AudioCodes indicating that
        VAD has detected the beginning of speech from the caller.

        Note:
            Includes conversation ID and participant ID (if not "caller")
            in the response. This is used for VAD event forwarding.
        """
        kwargs = {
            "type": TelephonyEventType.USER_STREAM_SPEECH_STARTED,
            "conversationId": self.conversation_id,
        }
        if self.current_participant != "caller":
            kwargs["participantId"] = self.current_participant
        await self.send_platform_json(
            UserStreamSpeechStartedResponse(**kwargs).model_dump()
        )

    async def send_speech_stopped(self):
        """Send AudioCodes-specific speech stopped response.

        Sends a speech stopped message to AudioCodes indicating that
        VAD has detected the end of speech from the caller.

        Note:
            Includes conversation ID and participant ID (if not "caller")
            in the response. This is used for VAD event forwarding.
        """
        kwargs = {
            "type": TelephonyEventType.USER_STREAM_SPEECH_STOPPED,
            "conversationId": self.conversation_id,
        }
        if self.current_participant != "caller":
            kwargs["participantId"] = self.current_participant
        await self.send_platform_json(
            UserStreamSpeechStoppedResponse(**kwargs).model_dump()
        )

    async def send_speech_committed(self):
        """Send AudioCodes-specific speech committed response.

        Sends a speech committed message to AudioCodes indicating that
        VAD has committed a speech segment for processing.

        Note:
            Includes conversation ID and participant ID (if not "caller")
            in the response. This is used for VAD event forwarding.
        """
        kwargs = {
            "type": TelephonyEventType.USER_STREAM_SPEECH_COMMITTED,
            "conversationId": self.conversation_id,
        }
        if self.current_participant != "caller":
            kwargs["participantId"] = self.current_participant
        await self.send_platform_json(
            UserStreamSpeechCommittedResponse(**kwargs).model_dump()
        )

    async def send_session_end(self, reason: str):
        """Send AudioCodes-specific session end message.

        Sends a session end message to AudioCodes to terminate the
        telephony session gracefully.

        Args:
            reason (str): The reason for ending the session

        Note:
            Uses "normal" as the reason code and includes the provided
            reason text. Logs success or failure of the message sending
            but doesn't raise exceptions to allow proper cleanup.
        """
        logger.info(f"Sending session end to AudioCodes: {reason}")

        session_end_message = {
            "type": "session.end",
            "conversationId": self.conversation_id,
            "reasonCode": "normal",
            "reason": reason,
        }

        try:
            await self.send_platform_json(session_end_message)
            logger.info("✅ Session end message sent to AudioCodes")
        except Exception as e:
            logger.error(f"❌ Error sending session end to AudioCodes: {e}")
            # Don't raise - we still want to close the connection

    async def send_session_resumed(self):
        """Send AudioCodes-specific session resumed response.

        Sends a session resumed message to AudioCodes confirming that
        the session has been successfully resumed.

        Note:
            Currently uses the same format as session accepted. Includes
            conversation ID, media format, and participant information.
        """
        kwargs = {
            "type": TelephonyEventType.SESSION_ACCEPTED,  # Use same as accepted for now
            "conversationId": self.conversation_id,
            "mediaFormat": self.media_format or "raw/lpcm16",
            "participant": self.current_participant,
        }
        await self.send_platform_json(SessionAcceptedResponse(**kwargs).model_dump())
        logger.info("✅ Session resumed response sent to AudioCodes")

    async def send_connection_validated(self):
        """Send AudioCodes-specific connection validated response.

        Sends a connection validated message to AudioCodes confirming
        that the WebSocket connection is healthy and ready for use.

        Note:
            Includes conversation ID and success status in the response.
        """
        kwargs = {
            "type": TelephonyEventType.CONNECTION_VALIDATED,
            "conversationId": self.conversation_id,
            "success": True,
        }
        await self.send_platform_json(
            ConnectionValidatedResponse(**kwargs).model_dump()
        )
        logger.info("✅ Connection validated response sent to AudioCodes")

    async def handle_outgoing_audio_audiocodes(
        self, response_dict: Dict[str, Any]
    ) -> None:
        """AudioCodes-specific implementation of handle_outgoing_audio.

        Processes outgoing audio from OpenAI Realtime API and sends it to AudioCodes.
        AudioCodes natively supports 24kHz PCM16, so no resampling is needed.

        Args:
            response_dict (Dict[str, Any]): Audio delta event from OpenAI containing:
                - delta (str): Base64-encoded audio data at 24kHz sample rate

        Note:
            This method:
            1. Parses the audio delta event from OpenAI
            2. Records bot audio if call recording is enabled
            3. Sends playStream.start if starting a new stream
            4. Sends audio directly to AudioCodes without resampling (24kHz PCM16)
            5. Creates a new stream ID if none exists

        Raises:
            Exception: Logs errors but doesn't raise to prevent audio pipeline disruption
        """
        try:
            # Validate that we have the required fields before parsing
            required_fields = [
                "response_id",
                "item_id",
                "output_index",
                "content_index",
                "delta",
            ]
            missing_fields = [
                field for field in required_fields if field not in response_dict
            ]

            if missing_fields:
                logger.warning(
                    f"Incomplete audio delta event - missing fields: {missing_fields}"
                )
                logger.debug(f"Received data: {response_dict}")
                return

            # Parse audio delta event
            audio_delta = ResponseAudioDeltaEvent(**response_dict)

            # Check if connections are still active
            if self._closed or not self.conversation_id:
                logger.debug(
                    "Skipping audio delta - connection closed or no conversation ID"
                )
                return

            # Check if platform websocket is available and not closed
            if not self.platform_websocket or self._is_websocket_closed():
                logger.debug(
                    "Skipping audio delta - platform websocket is unavailable or closed"
                )
                return

            # Record bot audio if recorder is available
            if self.call_recorder:
                await self.call_recorder.record_bot_audio(audio_delta.delta)

            # Start a new audio stream if needed
            if not self.audio_handler.active_stream_id:
                logger.debug("No active stream, creating new one")
                self.audio_handler.active_stream_id = str(uuid.uuid4())

                # Send playStream.start message
                stream_start = PlayStreamStartMessage(
                    type=TelephonyEventType.PLAY_STREAM_START,
                    conversationId=self.conversation_id,
                    streamId=self.audio_handler.active_stream_id,
                    mediaFormat=self.media_format or "raw/lpcm16",
                    participant="caller",
                    altText=None,
                    activityParams=None,
                )
                try:
                    await self.platform_websocket.send_json(stream_start.model_dump())
                    logger.info(
                        f"Started play stream: {self.audio_handler.active_stream_id}"
                    )
                except Exception as e:
                    logger.error(f"Failed to send playStream.start: {e}")
                    return

            # Validate audio delta before sending chunk
            if not audio_delta.delta or audio_delta.delta.strip() == "":
                logger.warning("Empty audio delta received, skipping audio chunk")
                return

            # Validate base64 encoding
            try:
                base64.b64decode(audio_delta.delta)
            except Exception as e:
                logger.error(f"Invalid base64 audio delta: {e}")
                return

            # Send audio chunk to platform client (no resampling needed - AudioCodes supports 24kHz)
            stream_chunk = PlayStreamChunkMessage(
                type=TelephonyEventType.PLAY_STREAM_CHUNK,
                conversationId=self.conversation_id,
                streamId=self.audio_handler.active_stream_id,
                audioChunk=audio_delta.delta,  # Send original 24kHz audio directly
                participant="caller",
            )
            try:
                await self.platform_websocket.send_json(stream_chunk.model_dump())
            except Exception as e:
                logger.error(f"Failed to send audio chunk: {e}")
                return

        except Exception as e:
            logger.error(f"Error in AudioCodes audio handler: {e}")
            # Log the problematic data for debugging
            logger.debug(f"Problematic response_dict: {response_dict}")
