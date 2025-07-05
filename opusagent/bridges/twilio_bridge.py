"""Twilio-specific implementation of the real-time bridge.

This module provides the Twilio Media Streams implementation of the base bridge, handling
Twilio-specific event types, message formats, and responses.
"""

import asyncio
import base64
import json
import time
from typing import Optional

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

logger = configure_logging("twilio_bridge")

VOICE = "alloy"  # example voice, override as needed


class TwilioBridge(BaseRealtimeBridge):
    """Twilio Media Streams implementation of the real-time bridge."""

    def __init__(self, platform_websocket, realtime_websocket, session_config: SessionConfig):
        super().__init__(platform_websocket, realtime_websocket, session_config)
        # Twilio-specific ids / state
        self.stream_sid: Optional[str] = None
        self.account_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self.audio_buffer = []  # small buffer before relaying to OpenAI
        self.mark_counter = 0
        
        # Override the audio handler's outgoing audio method to use Twilio-specific sending
        self.audio_handler.handle_outgoing_audio = self.handle_outgoing_audio_twilio

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
        try:
            import audioop
            return audioop.ulaw2lin(mulaw_bytes, 2)
        except Exception as e:
            logger.warning(f"audioop.ulaw2lin failed, using fallback conversion: {e}")
            # Fallback: implement μ-law to PCM16 conversion
            pcm16_bytes = bytearray()
            for mulaw_byte in mulaw_bytes:
                # μ-law to linear conversion table (simplified)
                # This is a basic implementation - for production, use a proper lookup table
                mulaw_val = mulaw_byte ^ 0xFF  # Invert μ-law
                sign = mulaw_val & 0x80
                exponent = (mulaw_val >> 4) & 0x07
                mantissa = mulaw_val & 0x0F
                
                if exponent == 0:
                    linear = mantissa << 1
                else:
                    linear = (mantissa | 0x10) << (exponent - 1)
                
                if sign:
                    linear = -linear
                
                # Convert to 16-bit signed integer
                pcm16_val = max(-32768, min(32767, linear * 256))
                pcm16_bytes.extend(pcm16_val.to_bytes(2, byteorder='little', signed=True))
            
            return bytes(pcm16_bytes)

    def _convert_pcm16_to_mulaw(self, pcm16_data: bytes) -> bytes:
        try:
            import audioop
            return audioop.lin2ulaw(pcm16_data, 2)
        except Exception as e:
            logger.warning(f"audioop.lin2ulaw failed, using fallback conversion: {e}")
            # Fallback: implement PCM16 to μ-law conversion
            mulaw_bytes = bytearray()
            
            # Process 16-bit samples (2 bytes each)
            for i in range(0, len(pcm16_data), 2):
                if i + 1 >= len(pcm16_data):
                    break
                    
                # Convert 2 bytes to 16-bit signed integer
                pcm16_val = int.from_bytes(pcm16_data[i:i+2], byteorder='little', signed=True)
                
                # Clamp to valid range
                pcm16_val = max(-32768, min(32767, pcm16_val))
                
                # Convert to μ-law
                if pcm16_val < 0:
                    sign = 0x80
                    pcm16_val = -pcm16_val
                else:
                    sign = 0x00
                
                # Find the highest set bit (exponent)
                if pcm16_val == 0:
                    exponent = 0
                    mantissa = 0
                else:
                    # Find the highest set bit
                    highest_bit = pcm16_val.bit_length() - 1
                    exponent = max(0, min(7, highest_bit - 4))
                    mantissa = (pcm16_val >> (exponent + 3)) & 0x0F
                
                # Combine into μ-law byte
                mulaw_byte = sign | (exponent << 4) | mantissa
                mulaw_bytes.append(mulaw_byte ^ 0xFF)  # Invert μ-law
            
            return bytes(mulaw_bytes)

    async def send_audio_to_twilio(self, pcm16_data: bytes):
        if not self.stream_sid:
            logger.warning("Cannot send audio to Twilio: stream_sid not set")
            return
            
        logger.debug(f"Sending {len(pcm16_data)} bytes of PCM16 audio to Twilio")
        
        # Resample from 24kHz to 8kHz if needed
        # OpenAI sends 24kHz PCM16, but Twilio expects 8kHz μ-law
        resampled_pcm16 = self._resample_audio(pcm16_data, 24000, 8000)
        logger.debug(f"Resampled from 24kHz to 8kHz: {len(pcm16_data)} -> {len(resampled_pcm16)} bytes")
        
        # Convert to μ-law
        mulaw = self._convert_pcm16_to_mulaw(resampled_pcm16)
        logger.debug(f"Converted to {len(mulaw)} bytes of μ-law audio")
        
        chunk_size = 160  # 20ms at 8kHz
        chunks_sent = 0
        for i in range(0, len(mulaw), chunk_size):
            chunk = mulaw[i : i + chunk_size]
            if len(chunk) < chunk_size:
                chunk += b"\x00" * (chunk_size - len(chunk))
            payload_b64 = base64.b64encode(chunk).decode()
            await self.send_platform_json(
                OutgoingMediaMessage(
                    event=TwilioEventType.MEDIA,
                    streamSid=self.stream_sid,
                    media=OutgoingMediaPayload(payload=payload_b64),
                ).model_dump()
            )
            chunks_sent += 1
            await asyncio.sleep(0.02)
        
        logger.debug(f"Sent {chunks_sent} audio chunks to Twilio")

    def _resample_audio(self, audio_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
        """Resample audio from one sample rate to another.
        
        Args:
            audio_bytes: Raw audio bytes (16-bit PCM)
            from_rate: Source sample rate
            to_rate: Target sample rate
            
        Returns:
            Resampled audio bytes
        """
        if from_rate == to_rate:
            return audio_bytes
            
        try:
            import numpy as np
            
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float64)
            
            # Calculate resampling parameters
            ratio = to_rate / from_rate
            original_length = len(audio_array)
            new_length = int(original_length * ratio)
            
            # Use linear interpolation for resampling
            if ratio > 1:
                # Upsampling - use linear interpolation
                old_indices = np.linspace(0, original_length - 1, new_length)
                resampled_audio = np.interp(old_indices, np.arange(original_length), audio_array)
            else:
                # Downsampling - apply simple low-pass filter first to prevent aliasing
                # Simple moving average as low-pass filter
                filter_size = max(1, int(1 / ratio))
                if filter_size > 1:
                    # Apply simple moving average filter
                    filtered_audio = np.convolve(audio_array, np.ones(filter_size)/filter_size, mode='same')
                else:
                    filtered_audio = audio_array
                
                # Then downsample
                old_indices = np.linspace(0, original_length - 1, new_length)
                resampled_audio = np.interp(old_indices, np.arange(original_length), filtered_audio)
            
            # Convert back to int16 with proper clipping
            resampled_audio = np.clip(resampled_audio, -32768, 32767).astype(np.int16)
            
            # Log resampling details for debugging
            original_duration_ms = (original_length / from_rate) * 1000
            resampled_duration_ms = (new_length / to_rate) * 1000
            logger.debug(
                f"Audio resampling: {from_rate}Hz -> {to_rate}Hz, "
                f"{original_length} -> {new_length} samples, "
                f"{original_duration_ms:.1f}ms -> {resampled_duration_ms:.1f}ms"
            )
            
            return resampled_audio.tobytes()
            
        except ImportError:
            logger.warning("NumPy not available for resampling, using simple decimation")
            # Fallback: simple decimation (not ideal but better than nothing)
            if ratio < 1:
                # Downsampling - take every nth sample
                step = int(1 / ratio)
                audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
                resampled_audio = audio_array[::step]
                return resampled_audio.tobytes()
            else:
                # Upsampling - repeat samples (not ideal but simple)
                step = int(ratio)
                audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
                resampled_audio = np.repeat(audio_array, step)
                return resampled_audio.tobytes()
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

    async def handle_outgoing_audio_twilio(self, response_dict):
        """Twilio-specific implementation of handle_outgoing_audio.
        
        This method is used to override the AudioStreamHandler's handle_outgoing_audio
        method to use Twilio-specific message formats instead of AudioCodes formats.
        """
        try:
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
