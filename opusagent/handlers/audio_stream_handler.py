"""Handler for managing audio streams between platform client and OpenAI Realtime API.

This module provides functionality for handling bidirectional audio streaming,
including audio format validation, chunk processing, and stream management.
"""

import asyncio
import base64
import json
import logging
import uuid
from typing import Any, Dict, Optional

import websockets
from fastapi import WebSocket

from opusagent.utils.audio_quality_monitor import AudioQualityMonitor, QualityThresholds
from opusagent.utils.call_recorder import CallRecorder
from opusagent.models.audiocodes_api import (
    PlayStreamChunkMessage,
    PlayStreamStartMessage,
    PlayStreamStopMessage,
    TelephonyEventType,
    UserStreamStartedResponse,
    UserStreamStoppedResponse,
    UserStreamSpeechStartedResponse,
    UserStreamSpeechStoppedResponse,
)
from opusagent.models.openai_api import (
    InputAudioBufferAppendEvent,
    InputAudioBufferCommitEvent,
    ResponseAudioDeltaEvent,
)
from opusagent.vad.vad_config import load_vad_config
from opusagent.vad.vad_factory import VADFactory
from opusagent.vad.audio_processor import to_float32_mono
from tui.utils.audio_utils import AudioUtils
from opusagent.utils.websocket_utils import WebSocketUtils

# Configure logging
logger = logging.getLogger(__name__)


class AudioStreamHandler:
    """Handler for managing audio streams between platform client and OpenAI Realtime API.

    This class handles all audio-related functionality including:
    - Processing incoming audio chunks from platform client
    - Processing outgoing audio chunks to platform client
    - Managing audio stream state and metadata
    - Handling audio format conversion and validation
    - Tracking audio statistics and metrics

    Attributes:
        platform_websocket (WebSocket): FastAPI WebSocket connection for platform
        realtime_websocket (Any): WebSocket connection to OpenAI Realtime API
        conversation_id (Optional[str]): Unique identifier for the current conversation
        media_format (Optional[str]): Audio format being used for the session
        active_stream_id (Optional[str]): Identifier for the current audio stream being played
        call_recorder (Optional[CallRecorder]): Call recorder for logging audio
        audio_chunks_sent (int): Number of audio chunks sent to the OpenAI Realtime API
        total_audio_bytes_sent (int): Total number of bytes sent to the OpenAI Realtime API
        _closed (bool): Flag indicating whether the handler is closed
    """

    def __init__(
        self,
        platform_websocket: WebSocket,
        realtime_websocket: Any,
        call_recorder: Optional[CallRecorder] = None,
        enable_quality_monitoring: bool = False,
        quality_thresholds: Optional[QualityThresholds] = None,
        bridge_type: str = 'unknown',
    ):
        """Initialize the audio stream handler.

        Args:
            platform_websocket (WebSocket): FastAPI WebSocket connection for platform
            realtime_websocket (Any): WebSocket connection to OpenAI Realtime API
            call_recorder (Optional[CallRecorder]): Call recorder for logging audio
            enable_quality_monitoring (bool): Enable real-time audio quality monitoring
            quality_thresholds (Optional[QualityThresholds]): Quality monitoring thresholds
        """
        self.platform_websocket = platform_websocket
        self.realtime_websocket = realtime_websocket
        self.call_recorder = call_recorder
        self.enable_quality_monitoring = enable_quality_monitoring
        self.quality_monitor = None
        self.conversation_id = None
        self.media_format = None
        self.active_stream_id = None
        self.audio_chunks_sent = 0
        self.total_audio_bytes_sent = 0
        self._closed = False
        self.bridge_type = bridge_type
        self.internal_sample_rate = 16000

        # Quality monitoring
        if self.enable_quality_monitoring:
            self.quality_monitor = AudioQualityMonitor(
                sample_rate=16000,
                chunk_size=1024,
                thresholds=quality_thresholds or QualityThresholds(),
                history_size=100,
            )

            # Set up quality alert callback
            self.quality_monitor.on_quality_alert = self._on_quality_alert
            logger.info("Audio quality monitoring enabled")

        # VAD integration
        vad_config = load_vad_config()
        self.vad = VADFactory.create_vad(vad_config)
        self.vad_enabled = vad_config.get('backend', 'silero') is not None
        self._speech_active = False  # Track speech state for VAD events
        if self.vad_enabled and self.vad:
            self.vad.sample_rate = self.internal_sample_rate
            if self.internal_sample_rate == 16000:
                self.vad.chunk_size = 512
            elif self.internal_sample_rate == 8000:
                self.vad.chunk_size = 256
            else:
                logger.warning(f"Unsupported internal sample rate for VAD: {self.internal_sample_rate}")
            logger.debug(f"Set VAD to {self.internal_sample_rate}Hz, chunk_size {self.vad.chunk_size}")

    async def initialize_stream(self, conversation_id: str, media_format: str) -> None:
        """Initialize a new audio stream.

        Args:
            conversation_id (str): Unique identifier for the conversation
            media_format (str): Audio format to use for the stream
        """
        self.conversation_id = conversation_id
        self.media_format = media_format
        self.audio_chunks_sent = 0
        self.total_audio_bytes_sent = 0
        logger.info(f"Audio stream initialized for conversation: {conversation_id}")

    async def handle_incoming_audio(self, data: Dict[str, Any]) -> None:
        """Handle incoming audio chunk from platform client.

        This method processes audio chunks and forwards them to the OpenAI Realtime API.
        It validates the audio format and ensures chunks meet minimum size requirements.

        Args:
            data (Dict[str, Any]): Audio chunk data containing base64 encoded audio
        """
        if self._closed or self.realtime_websocket.close_code is not None:
            logger.warning(
                "Skipping audio chunk - connection closed or websocket unavailable"
            )
            return

        audio_chunk_b64 = data["audioChunk"]

        try:
            # Decode base64 to get raw audio bytes
            audio_bytes = base64.b64decode(audio_chunk_b64)
            original_size = len(audio_bytes)

            # Determine original sample rate
            original_rate = {
                'twilio': 8000,
                'audiocodes': 16000,
                'call_agent': 16000,
            }.get(self.bridge_type, 16000)

            # Resample to internal rate if necessary
            if original_rate != self.internal_sample_rate:
                audio_bytes = AudioUtils.resample_audio(
                    audio_bytes, original_rate, self.internal_sample_rate
                )
                logger.debug(f"Resampled from {original_rate}Hz to {self.internal_sample_rate}Hz")

            # Calculate min chunk size for internal rate
            min_chunk_size = int(0.1 * self.internal_sample_rate * 2)  # 100ms

            # Check if chunk is too small
            if len(audio_bytes) < min_chunk_size:
                logger.warning(
                    f"Audio chunk too small: {len(audio_bytes)} bytes. "
                    f"Padding with silence to {min_chunk_size} bytes for 100ms at {self.internal_sample_rate}Hz."
                )
                padding_needed = min_chunk_size - len(audio_bytes)
                audio_bytes += b"\x00" * padding_needed
                audio_chunk_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            # VAD processing (local)
            if self.vad_enabled and self.vad:
                # Convert to float32 mono for VAD
                try:
                    audio_arr = to_float32_mono(audio_bytes, sample_width=2, channels=1)
                    logger.debug(f"[VAD] Processing audio chunk: {len(audio_arr)} samples")
                    vad_result = self.vad.process_audio(audio_arr)
                    is_speech = vad_result.get('is_speech', False)
                    speech_prob = vad_result.get('speech_prob', 0.0)
                    logger.debug(f"[VAD] Result: speech={is_speech}, prob={speech_prob:.3f}")
                    
                    # Emit VAD events on state transitions
                    if is_speech and not self._speech_active:
                        # Speech started
                        vad_event = UserStreamSpeechStartedResponse(
                            type=TelephonyEventType.USER_STREAM_SPEECH_STARTED,
                            conversationId=self.conversation_id,
                            participant="caller",
                            participantId="caller",
                        )
                        await self.platform_websocket.send_json(vad_event.model_dump())
                        self._speech_active = True
                        logger.info(f"[VAD] Speech started event sent (prob: {speech_prob:.3f})")
                    elif not is_speech and self._speech_active:
                        # Speech stopped
                        vad_event = UserStreamSpeechStoppedResponse(
                            type=TelephonyEventType.USER_STREAM_SPEECH_STOPPED,
                            conversationId=self.conversation_id,
                            participant="caller",
                            participantId="caller",
                        )
                        await self.platform_websocket.send_json(vad_event.model_dump())
                        self._speech_active = False
                        logger.info(f"[VAD] Speech stopped event sent (prob: {speech_prob:.3f})")
                except Exception as e:
                    logger.warning(f"VAD processing error: {e}")
                    import traceback
                    logger.debug(f"VAD error traceback: {traceback.format_exc()}")

            # Update tracking counters (moved later for accurate sent bytes)
            self.audio_chunks_sent += 1

            # Analyze audio quality if monitoring is enabled
            if self.enable_quality_monitoring and self.quality_monitor:
                try:
                    quality_metrics = self.quality_monitor.analyze_audio_chunk(
                        audio_bytes
                    )
                    logger.debug(
                        f"Audio quality - SNR: {quality_metrics.snr_db:.1f}dB, "
                        f"THD: {quality_metrics.thd_percent:.2f}%, "
                        f"Clipping: {quality_metrics.clipping_percent:.2f}%, "
                        f"Score: {quality_metrics.quality_score:.1f} ({quality_metrics.quality_level.value})"
                    )
                except Exception as e:
                    logger.warning(f"Error analyzing audio quality: {e}")

            # Record caller audio if recorder is available
            if self.call_recorder:
                await self.call_recorder.record_caller_audio(audio_chunk_b64)

            # Resample to OpenAI 24kHz
            openai_rate = 24000
            openai_audio = AudioUtils.resample_audio(
                audio_bytes, self.internal_sample_rate, openai_rate
            )
            audio_chunk_b64 = base64.b64encode(openai_audio).decode("utf-8")

            # Update total bytes with actual sent bytes
            self.total_audio_bytes_sent += len(openai_audio)

            # Log audio chunk details
            duration_ms = (len(audio_bytes) / (self.internal_sample_rate * 2)) * 1000
            logger.debug(
                f"Processing audio chunk #{self.audio_chunks_sent}: {original_size} -> {len(audio_bytes)} bytes internal "
                f"(~{duration_ms:.1f}ms), {len(openai_audio)} bytes to OpenAI. Total sent: {self.total_audio_bytes_sent} bytes"
            )

            # Send to OpenAI
            audio_append = InputAudioBufferAppendEvent(
                type="input_audio_buffer.append", audio=audio_chunk_b64
            )
            logger.debug(
                f"Sending audio to realtime-websocket (size: {len(audio_chunk_b64)} bytes base64)"
            )
            if WebSocketUtils.is_websocket_closed(self.realtime_websocket):
                logger.warning("Attempted to send audio to realtime-websocket after close; message not sent.")
                return
            await self.realtime_websocket.send(audio_append.model_dump_json())

        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")

    async def handle_outgoing_audio(self, response_dict: Dict[str, Any]) -> None:
        """Handle outgoing audio chunk from OpenAI Realtime API.

        This method processes audio chunks from OpenAI and forwards them to the platform client.
        It manages audio stream creation and cleanup.

        Args:
            response_dict (Dict[str, Any]): Response data containing audio delta
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
            audio_delta = ResponseAudioDeltaEvent(**response_dict)

            # Check if connections are still active
            if self._closed or not self.conversation_id:
                logger.debug(
                    "Skipping audio delta - connection closed or no conversation ID"
                )
                return

            # Check if platform websocket is available and not closed
            if not self.platform_websocket or self._is_websocket_closed() or WebSocketUtils.is_websocket_closed(self.platform_websocket):
                logger.debug(
                    "Skipping audio delta - platform websocket is closed or unavailable"
                )
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
                        participant="caller",
                        altText=None,
                        activityParams=None,
                    )
                    await self.platform_websocket.send_json(stream_start.model_dump())
                    logger.info(f"Started play stream: {self.active_stream_id}")
                except Exception as e:
                    logger.error(f"Error starting audio stream: {e}")
                    logger.warning("Platform WebSocket appears to be disconnected")
                    self.active_stream_id = None
                    return

            try:
                # Record bot audio if recorder is available
                if self.call_recorder:
                    await self.call_recorder.record_bot_audio(audio_delta.delta)

                # Send audio chunk to platform client
                stream_chunk = PlayStreamChunkMessage(
                    type=TelephonyEventType.PLAY_STREAM_CHUNK,
                    conversationId=self.conversation_id,
                    streamId=self.active_stream_id,
                    audioChunk=audio_delta.delta,
                    participant="caller",
                )
                await self.platform_websocket.send_json(stream_chunk.model_dump())
                logger.debug(
                    f"Sent audio chunk to client (size: {len(audio_delta.delta)} bytes)"
                )
            except Exception as e:
                logger.error(f"Error sending audio chunk: {e}")
                logger.warning(
                    "Platform WebSocket appears to be disconnected, stopping audio stream"
                )
                self.active_stream_id = None

        except Exception as e:
            logger.error(f"Error processing audio data: {e}")
            # Log the problematic data for debugging
            logger.debug(f"Problematic response_dict: {response_dict}")

    async def commit_audio_buffer(self) -> None:
        """Commit the audio buffer to OpenAI Realtime API.

        This method signals the end of speech by committing the audio buffer.
        """
        if not self._closed and self.realtime_websocket.close_code is None:
            # Log buffer state before committing
            total_duration_ms = (
                (self.total_audio_bytes_sent / (16000 * 2)) * 1000
                if self.total_audio_bytes_sent > 0
                else 0
            )
            logger.info(
                f"Buffer state before commit: {self.audio_chunks_sent} chunks, "
                f"{self.total_audio_bytes_sent} bytes (~{total_duration_ms:.1f}ms of audio)"
            )

            # OpenAI requires at least 100ms of audio (3200 bytes for 16kHz 16-bit mono)
            min_audio_bytes = 3200  # 100ms of 16kHz 16-bit mono audio

            if self.total_audio_bytes_sent >= min_audio_bytes:
                buffer_commit = InputAudioBufferCommitEvent(
                    type="input_audio_buffer.commit"
                )
                try:
                    await self.realtime_websocket.send(buffer_commit.model_dump_json())
                    logger.info(
                        f"Audio buffer committed with {self.audio_chunks_sent} chunks ({self.total_audio_bytes_sent} bytes)"
                    )
                except Exception as e:
                    logger.error(f"Error sending audio buffer commit: {e}")
            else:
                logger.info(
                    f"Skipping audio buffer commit - insufficient audio data: "
                    f"{self.total_audio_bytes_sent} bytes ({total_duration_ms:.1f}ms) "
                    f"< {min_audio_bytes} bytes (100ms minimum required by OpenAI)"
                )

    async def stop_stream(self) -> None:
        """Stop the current audio stream.

        This method stops any active audio stream and cleans up resources.
        """
        if self.active_stream_id and self.conversation_id:
            try:
                stream_stop = PlayStreamStopMessage(
                    type=TelephonyEventType.PLAY_STREAM_STOP,
                    conversationId=self.conversation_id,
                    streamId=self.active_stream_id,
                    participant="caller",
                )
                await self.platform_websocket.send_json(stream_stop.model_dump())
                logger.info(f"Stopped play stream: {self.active_stream_id}")
            except Exception as e:
                logger.error(f"Error stopping audio stream: {e}")
            finally:
                self.active_stream_id = None

    def get_audio_stats(self) -> Dict[str, Any]:
        """Get current audio statistics.

        Returns:
            Dict[str, Any]: Dictionary containing audio statistics
        """
        # Calculate duration based on 24kHz since total_audio_bytes_sent represents bytes sent to OpenAI
        openai_sample_rate = 24000
        stats = {
            "audio_chunks_sent": self.audio_chunks_sent,
            "total_audio_bytes_sent": self.total_audio_bytes_sent,
            "total_duration_ms": (
                (self.total_audio_bytes_sent / (openai_sample_rate * 2)) * 1000
                if self.total_audio_bytes_sent > 0
                else 0
            ),
        }

        # Add quality monitoring stats if enabled
        if self.enable_quality_monitoring and self.quality_monitor:
            quality_summary = self.quality_monitor.get_quality_summary()
            stats["quality_monitoring"] = quality_summary

        return stats

    def _on_quality_alert(self, alert) -> None:
        """Handle quality alerts from the quality monitor.

        Args:
            alert: QualityAlert object containing alert information
        """
        if not self.enable_quality_monitoring:
            return

        # Log the alert with appropriate level
        if alert.severity == "error":
            logger.error(f"Audio Quality Error: {alert.message}")
        else:
            logger.warning(f"Audio Quality Warning: {alert.message}")

        # Log detailed metrics for debugging
        logger.debug(
            f"Quality metrics - SNR: {alert.metrics.snr_db:.1f}dB, "
            f"THD: {alert.metrics.thd_percent:.2f}%, "
            f"Clipping: {alert.metrics.clipping_percent:.2f}%, "
            f"Score: {alert.metrics.quality_score:.1f}"
        )

    def _is_websocket_closed(self) -> bool:
        """Check if platform WebSocket is closed.

        Returns:
            bool: True if the WebSocket is closed or in an unusable state
        """
        try:
            from starlette.websockets import WebSocketState

            return (
                not self.platform_websocket
                or self.platform_websocket.client_state == WebSocketState.DISCONNECTED
            )
        except ImportError:
            # Fallback check without WebSocketState
            return not self.platform_websocket

    async def close(self) -> None:
        """Close the audio stream handler and clean up resources."""
        if not self._closed:
            self._closed = True
            await self.stop_stream()
            logger.info("Audio stream handler closed")
