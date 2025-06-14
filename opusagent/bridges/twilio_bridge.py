"""Twilio-specific implementation of the real-time bridge.

This module provides the Twilio Media Streams implementation of the base bridge, handling
Twilio-specific event types, message formats, and responses.
"""

import asyncio
import base64
import json
import time
from typing import Optional

import websockets

from opusagent.bridges.base_bridge import BaseRealtimeBridge
from opusagent.config.logging_config import configure_logging
from opusagent.models.openai_api import InputAudioBufferAppendEvent, InputAudioBufferCommitEvent
from opusagent.models.twilio_api import (
    TwilioEventType,
    ConnectedMessage,
    StartMessage,
    MediaMessage,
    StopMessage,
    DTMFMessage,
    MarkMessage,
    OutgoingMediaMessage,
    OutgoingMarkMessage,
)

logger = configure_logging("twilio_bridge")

VOICE = "alloy"  # example voice, override as needed

class TwilioBridge(BaseRealtimeBridge):
    """Twilio Media Streams implementation of the real-time bridge."""

    def __init__(self, platform_websocket, realtime_websocket: websockets.WebSocketClientProtocol):
        super().__init__(platform_websocket, realtime_websocket)
        # Twilio-specific ids / state
        self.stream_sid: Optional[str] = None
        self.account_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self.audio_buffer = []  # small buffer before relaying to OpenAI
        self.mark_counter = 0

    # ------------------------------------------------------------------
    # Platform-specific plumbing
    # ------------------------------------------------------------------
    async def send_platform_json(self, payload: dict):
        """Send a JSON payload to Twilio websocket."""
        await self.platform_websocket.send_json(payload)

    def register_platform_event_handlers(self):
        self.event_router.register_platform_handler(TwilioEventType.CONNECTED, self.handle_connected)
        self.event_router.register_platform_handler(TwilioEventType.START, self.handle_session_start)
        self.event_router.register_platform_handler(TwilioEventType.MEDIA, self.handle_audio_data)
        self.event_router.register_platform_handler(TwilioEventType.STOP, self.handle_session_end)
        self.event_router.register_platform_handler(TwilioEventType.DTMF, self.handle_dtmf)
        self.event_router.register_platform_handler(TwilioEventType.MARK, self.handle_mark)

    # ------------------------------------------------------------------
    # Required abstract method implementations
    # ------------------------------------------------------------------
    async def handle_session_start(self, data: dict):
        """Handle session start from Twilio.

        Args:
            data (dict): Start message data
        """
        start_msg = StartMessage(**data)
        self.stream_sid = start_msg.streamSid
        self.account_sid = start_msg.start.accountSid
        self.call_sid = start_msg.start.callSid
        self.media_format = start_msg.start.mediaFormat.encoding
        logger.info(f"Twilio stream started (SID: {self.stream_sid})")
        
        # Initialize conversation with call SID as conversation ID
        await self.initialize_conversation(self.call_sid)

    async def handle_audio_start(self, data: dict):
        """Handle start of audio stream from Twilio.
        
        Note: Twilio doesn't have a separate audio start event, audio starts
        with the first media message.
        
        Args:
            data (dict): Audio start message data
        """
        pass

    async def handle_audio_data(self, data: dict):
        """Handle audio data from Twilio.

        Args:
            data (dict): Media message data containing audio
        """
        try:
            media_msg = MediaMessage(**data)
            audio_payload = media_msg.media.payload
            mulaw_bytes = base64.b64decode(audio_payload)
            self.audio_buffer.append(mulaw_bytes)
            if len(self.audio_buffer) >= 2:  # ~40ms
                combined = b"".join(self.audio_buffer)
                pcm16 = self._convert_mulaw_to_pcm16(combined)
                b64_pcm = base64.b64encode(pcm16).decode()
                await self.realtime_websocket.send(InputAudioBufferAppendEvent(type="input_audio_buffer.append", audio=b64_pcm).model_dump_json())
                self.audio_buffer.clear()
        except Exception as e:
            logger.error(f"Error handling Twilio media: {e}")

    async def handle_audio_end(self, data: dict):
        """Handle end of audio stream from Twilio.
        
        Note: Twilio doesn't have a separate audio end event, audio ends
        with the stop message.
        
        Args:
            data (dict): Audio end message data
        """
        pass

    async def handle_session_end(self, data: dict):
        """Handle end of session from Twilio.

        Args:
            data (dict): Stop message data
        """
        _ = StopMessage(**data)
        await self.audio_handler.commit_audio_buffer()
        await self.close()

    # ------------------------------------------------------------------
    # Twilio-specific event handlers
    # ------------------------------------------------------------------
    async def handle_connected(self, data):
        """Handle Twilio connected event."""
        logger.info(f"Twilio connected: {data}")
        _ = ConnectedMessage(**data)

    async def handle_dtmf(self, data):
        """Handle Twilio DTMF event."""
        msg = DTMFMessage(**data)
        logger.info(f"DTMF digit: {msg.dtmf.digit}")

    async def handle_mark(self, data):
        """Handle Twilio mark event."""
        msg = MarkMessage(**data)
        logger.info(f"Received Twilio mark: {msg.mark.name}")

    # ------------------------------------------------------------------
    # Helper conversions
    # ------------------------------------------------------------------
    def _convert_mulaw_to_pcm16(self, mulaw_bytes: bytes) -> bytes:
        try:
            import audioop
            return audioop.ulaw2lin(mulaw_bytes, 2)
        except Exception:
            return b"".join(bytes([b, b]) for b in mulaw_bytes)

    def _convert_pcm16_to_mulaw(self, pcm16_data: bytes) -> bytes:
        try:
            import audioop
            return audioop.lin2ulaw(pcm16_data, 2)
        except Exception:
            return pcm16_data[::2]

    async def send_audio_to_twilio(self, pcm16_data: bytes):
        mulaw = self._convert_pcm16_to_mulaw(pcm16_data)
        chunk_size = 160  # 20ms at 8kHz
        for i in range(0, len(mulaw), chunk_size):
            chunk = mulaw[i:i+chunk_size]
            if len(chunk) < chunk_size:
                chunk += b"\x00" * (chunk_size - len(chunk))
            payload_b64 = base64.b64encode(chunk).decode()
            await self.send_platform_json(OutgoingMediaMessage(event="media", streamSid=self.stream_sid, media={"payload": payload_b64}).model_dump())
            await asyncio.sleep(0.02)

    # ------------------------------------------------------------------
    # Overriding realtime audio handler for outgoing audio
    # ------------------------------------------------------------------
    async def handle_audio_response_delta(self, response_dict):
        delta = response_dict.get("delta")
        if not delta:
            return
        try:
            pcm16 = base64.b64decode(delta)
            await self.send_audio_to_twilio(pcm16)
        except Exception as e:
            logger.error(f"Error sending audio delta to Twilio: {e}") 