"""Twilio-specific implementation of the real-time bridge.

This module provides the Twilio Media Streams implementation of the base bridge, handling
Twilio-specific event types, message formats, and responses.
"""

import asyncio
import base64
import json
import time
from typing import Any, Dict, Optional

from opusagent.bridges.base_bridge import BaseRealtimeBridge
from opusagent.config.logging_config import configure_logging
from opusagent.models.openai_api import InputAudioBufferAppendEvent, SessionConfig
from opusagent.models.twilio_api import (
    ConnectedMessage,
    DTMFMessage,
    MarkMessage,
    MediaMessage,
    OutgoingMediaMessage,
    OutgoingMediaPayload,
    StartMessage,
    StopMessage,
    TwilioEventType,
)

# Import the proper audio utilities
from tui.utils.audio_utils import AudioUtils

logger = configure_logging("twilio_bridge")

VOICE = "alloy"  # example voice, override as needed


class TwilioBridge(BaseRealtimeBridge):
    """Twilio Media Streams implementation of the real-time bridge."""

    def __init__(self, platform_websocket, realtime_websocket, session_config: SessionConfig, **kwargs):
        super().__init__(platform_websocket, realtime_websocket, session_config, bridge_type='twilio', **kwargs)
        # Twilio-specific ids / state
        self.stream_sid: Optional[str] = None
        self.account_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self.audio_buffer = []  # small buffer before relaying to OpenAI
        self.mark_counter = 0
        
        # Check audio processing dependencies
        self._check_audio_dependencies()
        
        # Override the audio handler's outgoing audio method to use Twilio-specific sending
        self.audio_handler.handle_outgoing_audio = self.handle_outgoing_audio_twilio

    def _check_audio_dependencies(self):
        """Check if audio processing dependencies are available."""
        try:
            # Try to import required libraries
            import librosa
            import numpy as np
            logger.info("High-quality audio processing available (librosa + numpy)")
        except ImportError as e:
            logger.warning(f"Audio processing dependencies not available: {e}")
            logger.warning("Audio quality may be degraded. Install librosa and numpy for best results.")

    # ------------------------------------------------------------------
    # Platform-specific plumbing
    # ------------------------------------------------------------------
    async def send_platform_json(self, payload: dict):
        """Send a JSON payload to Twilio websocket."""
        await self.platform_websocket.send_json(payload)

    def register_platform_event_handlers(self):
        """Register Twilio-specific event handlers.
        
        This method creates a mapping of Twilio event types to their handlers
        """
        # Create event handler mappings for Twilio events
        self.twilio_event_handlers = {
            TwilioEventType.CONNECTED: self.handle_connected,
            TwilioEventType.START: self.handle_session_start,
            TwilioEventType.MEDIA: self.handle_audio_data,
            TwilioEventType.STOP: self.handle_session_end,
            TwilioEventType.DTMF: self.handle_dtmf,
            TwilioEventType.MARK: self.handle_mark,
        }

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
                await self.realtime_websocket.send(
                    InputAudioBufferAppendEvent(
                        type="input_audio_buffer.append", audio=b64_pcm
                    ).model_dump_json()
                )
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
        """Convert μ-law to PCM16 using audioop or proper fallback."""
        try:
            import audioop
            return audioop.ulaw2lin(mulaw_bytes, 2)
        except Exception as e:
            logger.warning(f"audioop.ulaw2lin failed, using AudioUtils fallback: {e}")
            # Use proper μ-law conversion from AudioUtils
            return AudioUtils._ulaw_to_pcm16(mulaw_bytes)

    def _convert_pcm16_to_mulaw(self, pcm16_data: bytes) -> bytes:
        """Convert PCM16 to μ-law using audioop or proper fallback."""
        try:
            import audioop
            return audioop.lin2ulaw(pcm16_data, 2)
        except Exception as e:
            logger.warning(f"audioop.lin2ulaw failed, using AudioUtils fallback: {e}")
            # Use proper μ-law conversion from AudioUtils
            return AudioUtils._pcm16_to_ulaw(pcm16_data)

    async def send_audio_to_twilio(self, pcm16_data: bytes):
        """Send audio to Twilio with improved quality and error handling.
        
        Key improvements:
        - High-quality resampling using librosa with proper anti-aliasing
        - Correct μ-law conversion using lookup tables
        - Audio level monitoring and quality validation
        - Proper μ-law silence padding (0x80 instead of 0x00)
        - Better timing control for consistent 20ms intervals
        - Comprehensive error handling
        """
        if not self.stream_sid:
            logger.warning("Cannot send audio to Twilio: stream_sid not set")
            return
            
        if not pcm16_data:
            logger.debug("Skipping empty audio data")
            return
            
        logger.debug(f"Sending {len(pcm16_data)} bytes of PCM16 audio to Twilio")
        
        # Calculate audio level for monitoring and quality validation
        try:
            audio_level = AudioUtils.visualize_audio_level(pcm16_data, max_bars=5)
            logger.debug(f"Audio level: {audio_level}")
            
            # Validate audio quality - warn about potential issues
            if audio_level.count("▁") == len(audio_level):
                logger.warning("Audio appears to be silent or very quiet")
            elif audio_level.count("█") > len(audio_level) * 0.8:
                logger.warning("Audio may be clipping - levels very high")
        except Exception as e:
            logger.debug(f"Could not calculate audio level: {e}")
        
        # Resample from 24kHz to 8kHz if needed
        # OpenAI sends 24kHz PCM16, but Twilio expects 8kHz μ-law
        resampled_pcm16 = self._resample_audio(pcm16_data, 24000, 8000)
        logger.debug(f"Resampled from 24kHz to 8kHz: {len(pcm16_data)} -> {len(resampled_pcm16)} bytes")
        
        # Convert to μ-law
        mulaw = self._convert_pcm16_to_mulaw(resampled_pcm16)
        logger.debug(f"Converted to {len(mulaw)} bytes of μ-law audio")
        
        # Send audio in 20ms chunks (160 bytes at 8kHz)
        chunk_size = 160  # 20ms at 8kHz
        chunks_sent = 0
        start_time = time.time()
        
        for i in range(0, len(mulaw), chunk_size):
            chunk = mulaw[i : i + chunk_size]
            if len(chunk) < chunk_size:
                # Pad with silence instead of zeros for better audio quality
                chunk += b"\x80" * (chunk_size - len(chunk))  # μ-law silence is 0x80, not 0x00
            
            payload_b64 = base64.b64encode(chunk).decode()
            
            try:
                await self.send_platform_json(
                    OutgoingMediaMessage(
                        event=TwilioEventType.MEDIA,
                        streamSid=self.stream_sid,
                        media=OutgoingMediaPayload(payload=payload_b64),
                    ).model_dump()
                )
                chunks_sent += 1
                
                # Better timing control - maintain consistent 20ms intervals
                expected_time = start_time + (chunks_sent * 0.02)
                current_time = time.time()
                sleep_time = max(0, expected_time - current_time)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"Error sending audio chunk {chunks_sent}: {e}")
                break
        
        total_time = time.time() - start_time
        logger.debug(f"Sent {chunks_sent} audio chunks to Twilio in {total_time:.2f}s")

    def _resample_audio(self, audio_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
        """Resample audio using high-quality AudioUtils implementation.
        
        Args:
            audio_bytes: Raw audio bytes (16-bit PCM)
            from_rate: Source sample rate
            to_rate: Target sample rate
            
        Returns:
            Resampled audio bytes
        """
        if from_rate == to_rate:
            return audio_bytes
            
        # Use AudioUtils for high-quality resampling with proper anti-aliasing
        try:
            resampled_audio = AudioUtils.resample_audio(
                audio_bytes, 
                from_rate, 
                to_rate, 
                channels=1, 
                sample_width=2
            )
            
            # Log resampling details for debugging
            original_samples = len(audio_bytes) // 2
            resampled_samples = len(resampled_audio) // 2
            original_duration_ms = (original_samples / from_rate) * 1000
            resampled_duration_ms = (resampled_samples / to_rate) * 1000
            logger.debug(
                f"Audio resampling: {from_rate}Hz -> {to_rate}Hz, "
                f"{original_samples} -> {resampled_samples} samples, "
                f"{original_duration_ms:.1f}ms -> {resampled_duration_ms:.1f}ms"
            )
            
            return resampled_audio
            
        except Exception as e:
            logger.error(f"Error resampling audio from {from_rate}Hz to {to_rate}Hz: {e}")
            return audio_bytes  # Return original on error

    # ------------------------------------------------------------------
    # Override platform message handling for Twilio
    # ------------------------------------------------------------------
    async def receive_from_platform(self):
        """Receive and process data from the Twilio WebSocket.

        This method continuously listens for messages from the Twilio WebSocket,
        processes them using Twilio-specific event handlers, and forwards them
        to the OpenAI Realtime API.

        Raises:
            Exception: For any errors during processing
        """
        try:
            async for message in self.platform_websocket.iter_text():
                if self._closed:
                    break

                data = json.loads(message)
                event_str = data.get("event")
                
                if event_str:
                    # Convert string event type to enum
                    try:
                        event_type = TwilioEventType(event_str)
                    except ValueError:
                        logger.warning(f"Unknown Twilio event type: {event_str}")
                        continue

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
                        try:
                            await handler(data)
                            
                            # Break loop on stop event
                            if event_type == TwilioEventType.STOP:
                                break
                        except Exception as e:
                            logger.error(f"Error in Twilio event handler for {event_type}: {e}")
                    else:
                        logger.warning(f"No handler for Twilio event: {event_type}")
                else:
                    logger.warning(f"Message missing event field: {data}")

        except Exception as e:
            logger.error(f"Error in receive_from_platform: {e}")
            await self.close()

    async def handle_outgoing_audio_twilio(self, response_dict: Dict[str, Any]) -> None:
        """Twilio-specific implementation of handle_outgoing_audio.
        
        This method is used to override the AudioStreamHandler's handle_outgoing_audio
        method to use Twilio-specific message formats instead of AudioCodes formats.
        """
        try:
            # Validate that we have the required fields before parsing
            required_fields = ["response_id", "item_id", "output_index", "content_index", "delta"]
            missing_fields = [field for field in required_fields if field not in response_dict]
            
            if missing_fields:
                logger.warning(f"Incomplete audio delta event - missing fields: {missing_fields}")
                logger.debug(f"Received data: {response_dict}")
                return
            
            # Parse audio delta event
            from opusagent.models.openai_api import ResponseAudioDeltaEvent
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

            # Send audio to Twilio using our Twilio-specific method
            pcm16 = base64.b64decode(audio_delta.delta)
            await self.send_audio_to_twilio(pcm16)
            
        except Exception as e:
            logger.error(f"Error in Twilio audio handler: {e}")
            # Log the problematic data for debugging
            logger.debug(f"Problematic response_dict: {response_dict}")
