"""AudioCodes-specific implementation of the real-time bridge.

This module provides the AudioCodes-specific implementation of the base bridge class,
handling AudioCodes-specific event types, message formats, and responses.
"""

from opusagent.bridges.base_bridge import BaseRealtimeBridge
from opusagent.config.logging_config import configure_logging
from opusagent.models.audiocodes_api import (
    ConnectionValidatedResponse,
    SessionAcceptedResponse,
    TelephonyEventType,
    UserStreamSpeechCommittedResponse,
    UserStreamSpeechStartedResponse,
    UserStreamSpeechStoppedResponse,
    UserStreamStartedResponse,
    UserStreamStoppedResponse,
)
from opusagent.models.openai_api import ResponseAudioDeltaEvent
from tui.utils.audio_utils import AudioUtils
from opusagent.models.audiocodes_api import PlayStreamChunkMessage

import base64
import uuid
from typing import Dict, Any

logger = configure_logging("audiocodes_bridge")


class AudioCodesBridge(BaseRealtimeBridge):
    """AudioCodes-specific implementation of the real-time bridge.

    This class implements the AudioCodes-specific event handling and message formatting
    while inheriting the core bridge functionality from BaseRealtimeBridge.
    """

    def __init__(self, *args, **kwargs):
        """Initialize AudioCodes bridge with participant tracking."""
        super().__init__(*args, bridge_type='audiocodes', **kwargs)
        self.current_participant: str = (
            "caller"  # Default participant for single-party calls
        )

        # Override the audio handler's outgoing audio method to use AudioCodes-specific sending
        self.audio_handler.handle_outgoing_audio = self.handle_outgoing_audio_audiocodes

    def register_platform_event_handlers(self):
        """Register AudioCodes-specific event handlers with the event router."""
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
            payload (dict): The JSON payload to send
        """
        await self.platform_websocket.send_json(payload)

    async def handle_session_start(self, data: dict):
        """Handle session initiation from AudioCodes.

        Args:
            data (dict): Session initiate message data
        """
        logger.info(f"Session initiate received: {data}")
        conversation_id = data.get("conversationId")
        self.media_format = data.get("supportedMediaFormats", ["raw/lpcm16"])[0]

        await self.initialize_conversation(conversation_id)
        await self.send_session_accepted()

    async def handle_audio_start(self, data: dict):
        """Handle start of user audio stream from AudioCodes.

        Args:
            data (dict): User stream start message data
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

        Args:
            data (dict): User stream chunk message data containing audio
        """
        await self.audio_handler.handle_incoming_audio(data)

    async def handle_audio_end(self, data: dict):
        """Handle end of user audio stream from AudioCodes.

        Args:
            data (dict): User stream stop message data
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

        Args:
            data (dict): Session end message data
        """
        logger.info(f"Session end received: {data.get('reason', 'No reason provided')}")
        await self.close()
        logger.info("AudioCodes-Realtime bridge closed")

    async def handle_session_resume(self, data: dict):
        """Handle session resume from AudioCodes.

        Args:
            data (dict): Session resume message data
        """
        logger.info(f"Session resume received: {data}")
        conversation_id = data.get("conversationId")
        self.media_format = data.get("supportedMediaFormats", ["raw/lpcm16"])[0]

        # For now, treat resume the same as initiate
        # In a real implementation, you would restore session state from storage
        await self.initialize_conversation(conversation_id)
        await self.send_session_resumed()

    async def handle_activities(self, data: dict):
        """Handle activities/events from AudioCodes.

        Args:
            data (dict): Activities message data
        """
        logger.info(f"Activities received: {data}")
        activities = data.get("activities", [])
        
        for activity in activities:
            activity_type = activity.get("type")
            activity_name = activity.get("name")
            activity_value = activity.get("value")
            
            logger.info(f"Processing activity: {activity_type}/{activity_name} = {activity_value}")
            
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

        Args:
            data (dict): Connection validate message data
        """
        logger.info(f"Connection validation received: {data}")
        
        # Send connection validated response
        await self.send_connection_validated()

    async def handle_speech_started(self, data: dict):
        """Handle speech started event from OpenAI Realtime API.

        Args:
            data (dict): Speech started event data
        """
        if not self.vad_enabled:
            logger.warning("VAD disabled - ignoring speech started event")
            return
            
        logger.info("Speech started detected - sending to AudioCodes")
        await self.send_speech_started()

    async def handle_speech_stopped(self, data: dict):
        """Handle speech stopped event from OpenAI Realtime API.

        Args:
            data (dict): Speech stopped event data
        """
        if not self.vad_enabled:
            logger.warning("VAD disabled - ignoring speech stopped event")
            return
            
        logger.info("Speech stopped detected - sending to AudioCodes")
        await self.send_speech_stopped()

    async def handle_speech_committed(self, data: dict):
        """Handle speech committed event from OpenAI Realtime API.

        Args:
            data (dict): Speech committed event data
        """
        if not self.vad_enabled:
            logger.warning("VAD disabled - ignoring speech committed event")
            return
            
        logger.info("Speech committed detected - sending to AudioCodes")
        await self.send_speech_committed()

    async def send_session_accepted(self):
        """Send AudioCodes-specific session accepted response."""
        kwargs = {
            "type": TelephonyEventType.SESSION_ACCEPTED,
            "conversationId": self.conversation_id,
            "mediaFormat": self.media_format or "raw/lpcm16",
            "participant": self.current_participant,
        }
        await self.send_platform_json(SessionAcceptedResponse(**kwargs).model_dump())

    async def send_user_stream_started(self):
        """Send AudioCodes-specific user stream started response."""
        kwargs = {
            "type": TelephonyEventType.USER_STREAM_STARTED,
            "conversationId": self.conversation_id,
            "participant": self.current_participant,
        }
        await self.send_platform_json(UserStreamStartedResponse(**kwargs).model_dump())

    async def send_user_stream_stopped(self):
        """Send AudioCodes-specific user stream stopped response."""
        kwargs = {
            "type": TelephonyEventType.USER_STREAM_STOPPED,
            "conversationId": self.conversation_id,
            "participant": self.current_participant,
        }
        await self.send_platform_json(UserStreamStoppedResponse(**kwargs).model_dump())

    async def send_speech_started(self):
        """Send AudioCodes-specific speech started response."""
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
        """Send AudioCodes-specific speech stopped response."""
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
        """Send AudioCodes-specific speech committed response."""
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

        Args:
            reason: The reason for ending the session
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
        """Send AudioCodes-specific session resumed response."""
        kwargs = {
            "type": TelephonyEventType.SESSION_ACCEPTED,  # Use same as accepted for now
            "conversationId": self.conversation_id,
            "mediaFormat": self.media_format or "raw/lpcm16",
            "participant": self.current_participant,
        }
        await self.send_platform_json(SessionAcceptedResponse(**kwargs).model_dump())
        logger.info("✅ Session resumed response sent to AudioCodes")

    async def send_connection_validated(self):
        """Send AudioCodes-specific connection validated response."""
        kwargs = {
            "type": TelephonyEventType.CONNECTION_VALIDATED,
            "conversationId": self.conversation_id,
            "success": True,
        }
        await self.send_platform_json(ConnectionValidatedResponse(**kwargs).model_dump())
        logger.info("✅ Connection validated response sent to AudioCodes")

    async def handle_outgoing_audio_audiocodes(self, response_dict: Dict[str, Any]) -> None:
        """AudioCodes-specific implementation of handle_outgoing_audio."""
        try:
            # Parse audio delta event
            audio_delta = ResponseAudioDeltaEvent(**response_dict)

            # Check if connections are still active
            if self._closed or not self.conversation_id:
                logger.debug(
                    "Skipping audio delta - connection closed or no conversation ID"
                )
                return

            # Check if platform websocket is available and not closed
            if not self.platform_websocket:
                logger.debug(
                    "Skipping audio delta - platform websocket is unavailable"
                )
                return

            # Record bot audio if recorder is available
            if self.call_recorder:
                await self.call_recorder.record_bot_audio(audio_delta.delta)

            # Decode base64 to get raw audio bytes
            pcm16_data = base64.b64decode(audio_delta.delta)

            # Resample from 24kHz to 16kHz
            resampled_pcm16 = AudioUtils.resample_audio(pcm16_data, 24000, 16000)

            # Re-encode to base64
            resampled_b64 = base64.b64encode(resampled_pcm16).decode("utf-8")

            # Ensure we have an active stream
            if not self.audio_handler.active_stream_id:
                logger.debug("No active stream, creating new one")
                self.audio_handler.active_stream_id = str(uuid.uuid4())

            # Send audio chunk to platform client
            stream_chunk = PlayStreamChunkMessage(
                type=TelephonyEventType.PLAY_STREAM_CHUNK,
                conversationId=self.conversation_id,
                streamId=self.audio_handler.active_stream_id,
                audioChunk=resampled_b64,
                participant="caller",
            )
            await self.platform_websocket.send_json(stream_chunk.model_dump())

        except Exception as e:
            logger.error(f"Error in AudioCodes audio handler: {e}")
