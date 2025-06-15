"""AudioCodes-specific implementation of the real-time bridge.

This module provides the AudioCodes-specific implementation of the base bridge class,
handling AudioCodes-specific event types, message formats, and responses.
"""

from opusagent.bridges.base_bridge import BaseRealtimeBridge
from opusagent.config.logging_config import configure_logging
from opusagent.models.audiocodes_api import (
    SessionAcceptedResponse,
    TelephonyEventType,
    UserStreamStartedResponse,
    UserStreamStoppedResponse,
)

logger = configure_logging("audiocodes_bridge")


class AudioCodesBridge(BaseRealtimeBridge):
    """AudioCodes-specific implementation of the real-time bridge.

    This class implements the AudioCodes-specific event handling and message formatting
    while inheriting the core bridge functionality from BaseRealtimeBridge.
    """

    def register_platform_event_handlers(self):
        """Register AudioCodes-specific event handlers with the event router."""
        self.event_router.register_platform_handler(
            TelephonyEventType.SESSION_INITIATE, self.handle_session_start
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

    async def send_session_accepted(self):
        """Send AudioCodes-specific session accepted response."""
        await self.send_platform_json(
            SessionAcceptedResponse(
                type=TelephonyEventType.SESSION_ACCEPTED,
                conversationId=self.conversation_id,
                mediaFormat=self.media_format,
            ).model_dump()
        )

    async def send_user_stream_started(self):
        """Send AudioCodes-specific user stream started response."""
        await self.send_platform_json(
            UserStreamStartedResponse(
                type=TelephonyEventType.USER_STREAM_STARTED,
                conversationId=self.conversation_id,
            ).model_dump()
        )

    async def send_user_stream_stopped(self):
        """Send AudioCodes-specific user stream stopped response."""
        await self.send_platform_json(
            UserStreamStoppedResponse(
                type=TelephonyEventType.USER_STREAM_STOPPED,
                conversationId=self.conversation_id,
            ).model_dump()
        )
