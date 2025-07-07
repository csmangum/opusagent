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

from opusagent.audio_quality_monitor import AudioQualityMonitor, QualityThresholds
from opusagent.call_recorder import CallRecorder
from opusagent.models.audiocodes_api import (
    PlayStreamChunkMessage,
    PlayStreamStartMessage,
    PlayStreamStopMessage,
    TelephonyEventType,
    UserStreamStartedResponse,
    UserStreamStoppedResponse,
)
from opusagent.models.openai_api import (
    InputAudioBufferAppendEvent,
    InputAudioBufferCommitEvent,
    ResponseAudioDeltaEvent,
)

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
        self.conversation_id: Optional[str] = None
        self.media_format: Optional[str] = None
        self.active_stream_id: Optional[str] = None
        self._closed = False

        # Audio buffer tracking for debugging
        self.audio_chunks_sent = 0
        self.total_audio_bytes_sent = 0

        # Quality monitoring
        self.enable_quality_monitoring = enable_quality_monitoring
        self.quality_monitor: Optional[AudioQualityMonitor] = None
        
        if self.enable_quality_monitoring:
            self.quality_monitor = AudioQualityMonitor(
                sample_rate=16000,
                chunk_size=1024,
                thresholds=quality_thresholds or QualityThresholds(),
                history_size=100
            )
            
            # Set up quality alert callback
            self.quality_monitor.on_quality_alert = self._on_quality_alert
            logger.info("Audio quality monitoring enabled")

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

            # OpenAI requires at least 100ms of 16kHz 16-bit audio (3200 bytes minimum)
            min_chunk_size = 3200  # 100ms of 16kHz 16-bit mono audio

            # Check if chunk is too small
            if len(audio_bytes) < min_chunk_size:
                logger.warning(
                    f"Audio chunk too small: {len(audio_bytes)} bytes. "
                    f"OpenAI requires at least {min_chunk_size} bytes (100ms of 16kHz 16-bit audio). "
                    f"Padding with silence."
                )
                # Pad with silence to meet minimum requirements
                padding_needed = min_chunk_size - len(audio_bytes)
                audio_bytes += b"\x00" * padding_needed

                # Re-encode to base64
                audio_chunk_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            # Update tracking counters
            self.audio_chunks_sent += 1
            self.total_audio_bytes_sent += len(audio_bytes)

            # Log audio chunk details
            duration_ms = (len(audio_bytes) / (16000 * 2)) * 1000
            logger.debug(
                f"Processing audio chunk #{self.audio_chunks_sent}: {original_size} -> {len(audio_bytes)} bytes "
                f"(~{duration_ms:.1f}ms of audio). Total sent: {self.total_audio_bytes_sent} bytes"
            )

            # Analyze audio quality if monitoring is enabled
            if self.enable_quality_monitoring and self.quality_monitor:
                try:
                    quality_metrics = self.quality_monitor.analyze_audio_chunk(audio_bytes)
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

            # Send audio to OpenAI Realtime API
            audio_append = InputAudioBufferAppendEvent(
                type="input_audio_buffer.append", audio=audio_chunk_b64
            )
            logger.debug(
                f"Sending audio to realtime-websocket (size: {len(audio_chunk_b64)} bytes base64)"
            )
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
        stats = {
            "audio_chunks_sent": self.audio_chunks_sent,
            "total_audio_bytes_sent": self.total_audio_bytes_sent,
            "total_duration_ms": (
                (self.total_audio_bytes_sent / (16000 * 2)) * 1000
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
