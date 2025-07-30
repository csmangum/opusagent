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

    def __init__(
        self,
        platform_websocket,
        realtime_websocket,
        session_config: SessionConfig,
        **kwargs,
    ):
        super().__init__(
            platform_websocket,
            realtime_websocket,
            session_config,
            bridge_type="twilio",
            **kwargs,
        )
        # Twilio-specific ids / state
        self.stream_sid: Optional[str] = None
        self.account_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self.audio_buffer = []  # small buffer before relaying to OpenAI
        self.mark_counter = 0
        
        # Participant tracking for multi-party calls (future-proofing)
        self.current_participant: str = "caller"  # Default participant for single-party calls

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
            logger.warning(
                "Audio quality may be degraded. Install librosa and numpy for best results."
            )

    # ------------------------------------------------------------------
    # Platform-specific plumbing
    # ------------------------------------------------------------------
    async def send_platform_json(self, payload: dict):
        """Send a JSON payload to Twilio websocket.
        
        Args:
            payload (dict): The JSON payload to send to Twilio
            
        Note:
            This method includes connection checking to prevent sending on closed
            WebSocket connections, which can cause ASGI errors.
        """
        # Check if connection is still active before sending
        websocket_closed = False
        try:
            websocket_closed = self._is_websocket_closed()
        except AttributeError:
            # Method not available yet, assume websocket is not closed
            websocket_closed = False
            
        if self._closed or not self.platform_websocket or websocket_closed:
            logger.debug("Skipping platform message - connection closed or unavailable")
            return

        try:
            await self.platform_websocket.send_json(payload)
        except Exception as e:
            logger.error(f"Failed to send platform message: {e}")
            # Don't raise the exception to prevent cascading failures

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
        
        # Register VAD event handlers for OpenAI Realtime API only if VAD is enabled
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
        
        # Enhanced logging for session lifecycle
        logger.info(f"Twilio stream started (SID: {self.stream_sid}, Call: {self.call_sid})")
        logger.info(f"Account SID: {self.account_sid}, Media Format: {self.media_format}")
        
        # Log custom parameters if available
        if start_msg.start.customParameters:
            logger.info(f"Custom parameters: {start_msg.start.customParameters}")

        # Initialize conversation with call SID as conversation ID
        await self.initialize_conversation(self.call_sid)
        
        # Send session accepted response (if Twilio expects it)
        await self.send_session_accepted()
        
        # Log session initialization success
        logger.info(f"Session initialization completed for call: {self.call_sid}")

    async def handle_session_resume(self, data: dict):
        """Handle session resume from Twilio.
        
        Since Twilio Media Streams doesn't have native session resume events,
        this method provides a custom session resume mechanism using the call SID.
        
        Args:
            data (dict): Session resume message data containing:
                - callSid (str): Unique identifier for the call
                - streamSid (str): Stream identifier
                - accountSid (str): Account identifier
                
        Note:
            This method attempts to restore the session state from storage.
            If successful, it restores conversation context, audio buffers,
            and function state. If unsuccessful, it falls back to creating
            a new session.
        """
        logger.info(f"Session resume received: {data}")
        
        # Extract call information
        call_sid = data.get("callSid")
        stream_sid = data.get("streamSid")
        account_sid = data.get("accountSid")
        
        if not call_sid:
            logger.error("Session resume failed: missing callSid")
            return
            
        # Update bridge state
        self.call_sid = call_sid
        self.stream_sid = stream_sid
        self.account_sid = account_sid
        
        # Set media format if provided
        if "mediaFormat" in data:
            self.media_format = data["mediaFormat"].get("encoding", "audio/x-mulaw")
            logger.info(f"Media format updated: {self.media_format}")
        
        try:
            # Initialize conversation (will attempt resume)
            await self.initialize_conversation(call_sid)

            if self.session_state and self.session_state.resumed_count > 0:
                # Successfully resumed
                await self.send_session_resumed()
                logger.info(f"Session resumed successfully: {call_sid} (resume count: {self.session_state.resumed_count})")
            else:
                # Failed to resume, treat as new session
                await self.send_session_accepted()
                logger.info(f"Session resume failed, created new session: {call_sid}")

        except Exception as e:
            logger.error(f"Error during session resume: {e}")
            # Fall back to new session creation
            await self.initialize_conversation(call_sid)
            await self.send_session_accepted()

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
            
            # Extract participant information if available (for multi-party calls)
            track = media_msg.media.track
            if track and track != "inbound":
                self.current_participant = track
                logger.debug(f"Audio from participant: {track}")
            
            # Enhanced audio processing logging
            chunk_size = len(audio_payload)
            logger.debug(f"Received audio chunk: {chunk_size} bytes, track: {track}")
            
            mulaw_bytes = base64.b64decode(audio_payload)
            self.audio_buffer.append(mulaw_bytes)
            if len(self.audio_buffer) >= 2:  # ~40ms
                combined = b"".join(self.audio_buffer)
                pcm16 = self._convert_mulaw_to_pcm16(combined)
                b64_pcm = base64.b64encode(pcm16).decode()
                
                # Log audio processing metrics
                total_bytes = len(combined)
                logger.debug(f"Processing audio: {len(self.audio_buffer)} chunks, {total_bytes} bytes")
                
                # Check if realtime websocket is still active before sending
                if self._closed or not self.realtime_websocket:
                    logger.debug("Skipping realtime message - connection closed or unavailable")
                    return
                
                try:
                    await self.realtime_websocket.send(
                        InputAudioBufferAppendEvent(
                            type="input_audio_buffer.append", audio=b64_pcm
                        ).model_dump_json()
                    )
                    self.audio_buffer.clear()
                    
                    # Update audio metrics
                    self.audio_chunks_sent += 1
                    self.total_audio_bytes_sent += total_bytes
                    
                    # Log periodic audio metrics
                    if self.audio_chunks_sent % 100 == 0:
                        logger.info(f"Audio processing stats: {self.audio_chunks_sent} chunks, {self.total_audio_bytes_sent} bytes sent")
                        
                except Exception as e:
                    logger.error(f"Failed to send realtime message: {e}")
                    # Don't raise the exception to prevent cascading failures
        except Exception as e:
            logger.error(f"Error handling Twilio media: {e}")
            # Log additional context for debugging
            logger.debug(f"Problematic media data: {data}")

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
        stop_msg = StopMessage(**data)
        
        # Enhanced session end logging
        logger.info(f"Session ending: {self.conversation_id} (Stream: {self.stream_sid})")
        logger.info(f"Final audio stats: {self.audio_chunks_sent} chunks, {self.total_audio_bytes_sent} bytes processed")
        
        await self.audio_handler.commit_audio_buffer()
        await self.close()
        
        logger.info(f"Session cleanup completed for call: {self.call_sid}")

    # ------------------------------------------------------------------
    # Twilio-specific event handlers
    # ------------------------------------------------------------------
    async def handle_connected(self, data):
        """Handle Twilio connected event."""
        connected_msg = ConnectedMessage(**data)
        logger.info(f"Twilio connected: protocol={connected_msg.protocol}, version={connected_msg.version}")

    async def handle_dtmf(self, data):
        """Handle Twilio DTMF event."""
        msg = DTMFMessage(**data)
        logger.info(f"DTMF digit: {msg.dtmf.digit} (track: {msg.dtmf.track})")

    async def handle_mark(self, data):
        """Handle Twilio mark event."""
        msg = MarkMessage(**data)
        logger.info(f"Received Twilio mark: {msg.mark.name} (sequence: {msg.sequenceNumber})")

    # ------------------------------------------------------------------
    # VAD (Voice Activity Detection) support
    # ------------------------------------------------------------------
    async def handle_speech_started(self, data: dict):
        """Handle speech started event from OpenAI Realtime API.
        
        Processes VAD speech start events from OpenAI and logs them
        for debugging and monitoring purposes.
        
        Args:
            data (dict): Speech started event data from OpenAI Realtime API
            
        Note:
            Only processes events if VAD is enabled. Since Twilio Media Streams
            doesn't support VAD events natively, this method primarily logs
            the events for debugging and monitoring.
        """
        if not self.vad_enabled:
            logger.warning("VAD disabled - ignoring speech started event")
            return
            
        logger.info("Speech started detected from OpenAI Realtime API")
        await self.send_speech_started()

    async def handle_speech_stopped(self, data: dict):
        """Handle speech stopped event from OpenAI Realtime API.
        
        Processes VAD speech stop events from OpenAI and logs them
        for debugging and monitoring purposes.
        
        Args:
            data (dict): Speech stopped event data from OpenAI Realtime API
            
        Note:
            Only processes events if VAD is enabled. Since Twilio Media Streams
            doesn't support VAD events natively, this method primarily logs
            the events for debugging and monitoring.
        """
        if not self.vad_enabled:
            logger.warning("VAD disabled - ignoring speech stopped event")
            return
            
        logger.info("Speech stopped detected from OpenAI Realtime API")
        await self.send_speech_stopped()

    async def handle_speech_committed(self, data: dict):
        """Handle speech committed event from OpenAI Realtime API.
        
        Processes VAD speech commit events from OpenAI and logs them
        for debugging and monitoring purposes.
        
        Args:
            data (dict): Speech committed event data from OpenAI Realtime API
            
        Note:
            Only processes events if VAD is enabled. Since Twilio Media Streams
            doesn't support VAD events natively, this method primarily logs
            the events for debugging and monitoring.
        """
        if not self.vad_enabled:
            logger.warning("VAD disabled - ignoring speech committed event")
            return
            
        logger.info("Speech committed detected from OpenAI Realtime API")
        await self.send_speech_committed()

    async def send_speech_started(self):
        """Send Twilio-specific speech started response.
        
        Logs speech started events for debugging and monitoring purposes.
        
        Note:
            Since Twilio Media Streams doesn't support VAD events natively,
            this method primarily logs the events for debugging and monitoring.
        """
        logger.info(f"Speech started: {self.conversation_id} (Participant: {self.current_participant})")
        # Twilio Media Streams doesn't support VAD events, so we just log

    async def send_speech_stopped(self):
        """Send Twilio-specific speech stopped response.
        
        Logs speech stopped events for debugging and monitoring purposes.
        
        Note:
            Since Twilio Media Streams doesn't support VAD events natively,
            this method primarily logs the events for debugging and monitoring.
        """
        logger.info(f"Speech stopped: {self.conversation_id} (Participant: {self.current_participant})")
        # Twilio Media Streams doesn't support VAD events, so we just log

    async def send_speech_committed(self):
        """Send Twilio-specific speech committed response.
        
        Logs speech committed events for debugging and monitoring purposes.
        
        Note:
            Since Twilio Media Streams doesn't support VAD events natively,
            this method primarily logs the events for debugging and monitoring.
        """
        logger.info(f"Speech committed: {self.conversation_id} (Participant: {self.current_participant})")
        # Twilio Media Streams doesn't support VAD events, so we just log

    # ------------------------------------------------------------------
    # Session management responses
    # ------------------------------------------------------------------
    async def send_session_accepted(self):
        """Send Twilio-specific session accepted response.
        
        Sends a session accepted message to Twilio confirming the
        session has been established and is ready for audio communication.
        
        Note:
            Since Twilio Media Streams doesn't expect specific session
            responses, this method logs the session acceptance for
            debugging and monitoring purposes.
        """
        logger.info(f"Session accepted: {self.conversation_id} (Stream: {self.stream_sid})")
        # Twilio Media Streams doesn't expect session responses, so we just log

    async def send_session_resumed(self):
        """Send Twilio-specific session resumed response.
        
        Sends a session resumed message to Twilio confirming that
        the session has been successfully resumed.
        
        Note:
            Since Twilio Media Streams doesn't expect specific session
            responses, this method logs the session resumption for
            debugging and monitoring purposes.
        """
        logger.info(f"Session resumed: {self.conversation_id} (Stream: {self.stream_sid})")
        # Twilio Media Streams doesn't expect session responses, so we just log

    async def send_user_stream_started(self):
        """Send Twilio-specific user stream started response.
        
        Sends a user stream started message to Twilio confirming
        that the incoming audio stream has been acknowledged.
        
        Note:
            Since Twilio Media Streams doesn't expect specific stream
            responses, this method logs the stream start for
            debugging and monitoring purposes.
        """
        logger.info(f"User stream started: {self.conversation_id} (Participant: {self.current_participant})")
        # Twilio Media Streams doesn't expect stream responses, so we just log

    async def send_user_stream_stopped(self):
        """Send Twilio-specific user stream stopped response.
        
        Sends a user stream stopped message to Twilio confirming
        that the end of the incoming audio stream has been acknowledged.
        
        Note:
            Since Twilio Media Streams doesn't expect specific stream
            responses, this method logs the stream stop for
            debugging and monitoring purposes.
        """
        logger.info(f"User stream stopped: {self.conversation_id} (Participant: {self.current_participant})")
        # Twilio Media Streams doesn't expect stream responses, so we just log

    # ------------------------------------------------------------------
    # Connection validation support
    # ------------------------------------------------------------------
    async def handle_connection_validate(self, data: dict):
        """Handle connection validation from Twilio.
        
        Since Twilio Media Streams doesn't have native connection validation events,
        this method provides a custom connection validation mechanism.
        
        Args:
            data (dict): Connection validate message data
            
        Note:
            This method validates the WebSocket connection health and responds
            with validation confirmation. It can be triggered by custom
            validation messages or periodic health checks.
        """
        logger.info(f"Connection validation received: {data}")
        
        # Validate connection health
        is_healthy = await self._validate_connection_health()
        
        if is_healthy:
            await self.send_connection_validated()
            logger.info("Connection validation successful")
        else:
            logger.warning("Connection validation failed - connection may be unhealthy")
            # Don't send validation response if connection is unhealthy

    async def send_connection_validated(self):
        """Send Twilio-specific connection validated response.
        
        Sends a connection validated message to Twilio confirming
        that the WebSocket connection is healthy and ready for use.
        
        Note:
            Since Twilio Media Streams doesn't expect specific validation
            responses, this method logs the validation for debugging
            and monitoring purposes.
        """
        logger.info(f"Connection validated: {self.conversation_id} (Stream: {self.stream_sid})")
        # Twilio Media Streams doesn't expect validation responses, so we just log

    async def _validate_connection_health(self) -> bool:
        """Validate the health of the WebSocket connection.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            # Check if connections are still active
            if self._closed:
                logger.debug("Connection validation failed: bridge is closed")
                return False
                
            if not self.platform_websocket:
                logger.debug("Connection validation failed: platform websocket is None")
                return False
                
            websocket_closed = False
            try:
                websocket_closed = self._is_websocket_closed()
            except AttributeError:
                # Method not available yet, assume websocket is not closed
                websocket_closed = False
                
            if websocket_closed:
                logger.debug("Connection validation failed: platform websocket is closed")
                return False
                
            if not self.realtime_websocket:
                logger.debug("Connection validation failed: realtime websocket is None")
                return False
                
            # Additional health checks could be added here:
            # - Ping/pong tests
            # - Audio flow validation
            # - Session state validation
            
            return True
            
        except Exception as e:
            logger.error(f"Error during connection health validation: {e}")
            return False

    async def start_connection_health_monitor(self):
        """Start periodic connection health monitoring.
        
        This method starts a background task that periodically checks
        the health of the WebSocket connections and logs any issues.
        
        Note:
            This is an optional feature that can be enabled for better
            connection monitoring and debugging.
        """
        async def health_monitor():
            """Background task for monitoring connection health."""
            while not self._closed:
                try:
                    is_healthy = await self._validate_connection_health()
                    if not is_healthy:
                        logger.warning("Connection health check failed")
                    else:
                        logger.debug("Connection health check passed")
                        
                    # Wait 30 seconds before next check
                    await asyncio.sleep(30)
                    
                except Exception as e:
                    logger.error(f"Error in connection health monitor: {e}")
                    await asyncio.sleep(10)  # Shorter wait on error
                    
        # Start the health monitor task
        asyncio.create_task(health_monitor())
        logger.info("Connection health monitor started")

    # ------------------------------------------------------------------
    # Advanced features and performance optimizations
    # ------------------------------------------------------------------
    async def start_audio_quality_monitor(self):
        """Start audio quality monitoring for performance optimization.
        
        This method starts a background task that monitors audio quality
        metrics and provides insights for debugging and optimization.
        
        Note:
            This is an optional feature that can be enabled for better
            audio quality monitoring and debugging.
        """
        async def audio_quality_monitor():
            """Background task for monitoring audio quality."""
            while not self._closed:
                try:
                    # Calculate audio quality metrics
                    if self.audio_chunks_sent > 0:
                        avg_chunk_size = self.total_audio_bytes_sent / self.audio_chunks_sent
                        logger.debug(f"Audio quality metrics: {self.audio_chunks_sent} chunks, "
                                   f"{self.total_audio_bytes_sent} bytes, "
                                   f"avg chunk size: {avg_chunk_size:.1f} bytes")
                        
                        # Warn about potential issues
                        if avg_chunk_size < 100:
                            logger.warning("Audio chunks seem small - potential quality issues")
                        elif avg_chunk_size > 1000:
                            logger.warning("Audio chunks seem large - potential buffering issues")
                    
                    # Wait 60 seconds before next check
                    await asyncio.sleep(60)
                    
                except Exception as e:
                    logger.error(f"Error in audio quality monitor: {e}")
                    await asyncio.sleep(30)  # Shorter wait on error
                    
        # Start the audio quality monitor task
        asyncio.create_task(audio_quality_monitor())
        logger.info("Audio quality monitor started")

    async def start_performance_monitor(self):
        """Start performance monitoring for optimization insights.
        
        This method starts a background task that monitors various
        performance metrics and provides insights for optimization.
        
        Note:
            This is an optional feature that can be enabled for better
            performance monitoring and optimization.
        """
        async def performance_monitor():
            """Background task for monitoring performance metrics."""
            start_time = time.time()
            last_check_time = start_time
            
            while not self._closed:
                try:
                    current_time = time.time()
                    session_duration = current_time - start_time
                    time_since_last_check = current_time - last_check_time
                    
                    # Calculate performance metrics
                    if time_since_last_check > 0:
                        audio_rate = self.audio_chunks_sent / time_since_last_check
                        data_rate = self.total_audio_bytes_sent / time_since_last_check
                        
                        logger.debug(f"Performance metrics: session duration: {session_duration:.1f}s, "
                                   f"audio rate: {audio_rate:.1f} chunks/s, "
                                   f"data rate: {data_rate:.1f} bytes/s")
                    
                    last_check_time = current_time
                    
                    # Wait 120 seconds before next check
                    await asyncio.sleep(120)
                    
                except Exception as e:
                    logger.error(f"Error in performance monitor: {e}")
                    await asyncio.sleep(60)  # Shorter wait on error
                    
        # Start the performance monitor task
        asyncio.create_task(performance_monitor())
        logger.info("Performance monitor started")

    async def enable_advanced_monitoring(self):
        """Enable all advanced monitoring features.
        
        This method enables connection health monitoring, audio quality
        monitoring, and performance monitoring for comprehensive insights.
        
        Note:
            This method should be called after the bridge is initialized
            to enable all monitoring features.
        """
        await self.start_connection_health_monitor()
        await self.start_audio_quality_monitor()
        await self.start_performance_monitor()
        logger.info("Advanced monitoring features enabled")

    async def get_bridge_statistics(self) -> dict:
        """Get comprehensive bridge statistics.
        
        Returns:
            dict: Dictionary containing various bridge statistics including
                session information, audio metrics, and performance data.
        """
        stats = {
            "session": {
                "conversation_id": self.conversation_id,
                "stream_sid": self.stream_sid,
                "call_sid": self.call_sid,
                "account_sid": self.account_sid,
                "media_format": self.media_format,
                "current_participant": self.current_participant,
                "session_duration": time.time() - getattr(self, '_session_start_time', time.time()),
            },
            "audio": {
                "chunks_sent": self.audio_chunks_sent,
                "total_bytes_sent": self.total_audio_bytes_sent,
                "avg_chunk_size": self.total_audio_bytes_sent / max(self.audio_chunks_sent, 1),
                "buffer_size": len(self.audio_buffer),
            },
            "connection": {
                "closed": self._closed,
                "platform_websocket_active": self.platform_websocket is not None,
                "realtime_websocket_active": self.realtime_websocket is not None,
                "websocket_closed": self._is_websocket_closed() if hasattr(self, '_is_websocket_closed') else False,
            },
            "features": {
                "vad_enabled": self.vad_enabled,
                "bridge_type": self.bridge_type,
            }
        }
        
        # Add session state information if available
        if hasattr(self, 'session_state') and self.session_state:
            stats["session"]["resumed_count"] = getattr(self.session_state, 'resumed_count', 0)
            stats["session"]["status"] = getattr(self.session_state, 'status', 'unknown')
        
        return stats

    async def log_bridge_statistics(self):
        """Log comprehensive bridge statistics for debugging and monitoring.
        
        This method logs detailed statistics about the bridge state,
        which can be useful for debugging and monitoring purposes.
        """
        stats = await self.get_bridge_statistics()
        
        logger.info("Bridge Statistics:")
        logger.info(f"  Session: {stats['session']}")
        logger.info(f"  Audio: {stats['audio']}")
        logger.info(f"  Connection: {stats['connection']}")
        logger.info(f"  Features: {stats['features']}")

    async def handle_graceful_shutdown(self, reason: str = "Graceful shutdown"):
        """Handle graceful shutdown of the bridge.
        
        This method provides a clean shutdown mechanism that ensures
        all resources are properly cleaned up and statistics are logged.
        
        Args:
            reason (str): Reason for the shutdown
        """
        logger.info(f"Starting graceful shutdown: {reason}")
        
        # Log final statistics
        await self.log_bridge_statistics()
        
        # Perform normal close operations
        await self.close()
        
        logger.info("Graceful shutdown completed")

    async def handle_error_recovery(self, error: Exception, context: str = "Unknown"):
        """Handle error recovery with enhanced logging and recovery mechanisms.
        
        This method provides enhanced error handling with detailed logging
        and potential recovery mechanisms.
        
        Args:
            error (Exception): The error that occurred
            context (str): Context where the error occurred
        """
        logger.error(f"Error in {context}: {error}")
        logger.error(f"Error type: {type(error).__name__}")
        logger.error(f"Error details: {str(error)}")
        
        # Log bridge state for debugging
        try:
            await self.log_bridge_statistics()
        except Exception as e:
            logger.error(f"Failed to log bridge statistics during error recovery: {e}")
        
        # Attempt recovery based on error type
        if isinstance(error, ConnectionError):
            logger.warning("Connection error detected - attempting reconnection logic")
            # Could implement reconnection logic here
        elif isinstance(error, TimeoutError):
            logger.warning("Timeout error detected - checking connection health")
            # Could implement timeout recovery logic here
        else:
            logger.warning("Unknown error type - logging for analysis")

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
        logger.debug(
            f"Resampled from 24kHz to 8kHz: {len(pcm16_data)} -> {len(resampled_pcm16)} bytes"
        )

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
                chunk += b"\x80" * (
                    chunk_size - len(chunk)
                )  # μ-law silence is 0x80, not 0x00

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

    def _resample_audio(
        self, audio_bytes: bytes, from_rate: int, to_rate: int
    ) -> bytes:
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
                audio_bytes, from_rate, to_rate, channels=1, sample_width=2
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
            logger.error(
                f"Error resampling audio from {from_rate}Hz to {to_rate}Hz: {e}"
            )
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
                            logger.error(
                                f"Error in Twilio event handler for {event_type}: {e}"
                            )
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
                logger.debug("Skipping audio delta - platform websocket is unavailable")
                return

            # Record bot audio if recorder is available
            if self.call_recorder:
                await self.call_recorder.record_bot_audio(audio_delta.delta)

            # Validate audio delta before sending
            if not audio_delta.delta or audio_delta.delta.strip() == "":
                logger.warning("Empty audio delta received, skipping audio chunk")
                return

            # Validate base64 encoding
            try:
                base64.b64decode(audio_delta.delta)
            except Exception as e:
                logger.error(f"Invalid base64 audio delta: {e}")
                return

            # Send audio to Twilio using our Twilio-specific method
            pcm16 = base64.b64decode(audio_delta.delta)
            await self.send_audio_to_twilio(pcm16)

        except Exception as e:
            logger.error(f"Error in Twilio audio handler: {e}")
            # Log the problematic data for debugging
            logger.debug(f"Problematic response_dict: {response_dict}")
