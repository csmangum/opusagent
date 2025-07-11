"""
Enhanced Audio Stream Handler with Resilience

This module provides an enhanced version of the audio stream handler that
integrates comprehensive error handling, circuit breakers, retry mechanisms,
and adaptive quality management for improved reliability in real-world conditions.
"""

import asyncio
import base64
import logging
import time
import uuid
from collections import deque
from typing import Any, Dict, Optional

from opusagent.resilience import (
    AudioDataValidator,
    AudioChunkRecovery,
    CircuitBreaker,
    AdaptiveQualityManager,
    ReliableMessageSender
)
from opusagent.audio_stream_handler import AudioStreamHandler
from opusagent.config.quality_config import QualityThresholds

logger = logging.getLogger(__name__)


class EnhancedAudioStreamHandler(AudioStreamHandler):
    """
    Enhanced audio stream handler with comprehensive resilience features.
    
    This class extends the base AudioStreamHandler with:
    - Robust audio data validation and corruption handling
    - Network jitter recovery and timing compensation
    - Circuit breaker protection for external services
    - Adaptive quality management based on performance metrics
    - Reliable message delivery with retry logic
    """
    
    def __init__(
        self,
        platform_websocket,
        realtime_websocket,
        call_recorder=None,
        enable_quality_monitoring: bool = False,
        quality_thresholds: Optional[QualityThresholds] = None,
        bridge_type: str = 'unknown',
        enable_resilience: bool = True
    ):
        """
        Initialize enhanced audio stream handler.
        
        Args:
            platform_websocket: Platform WebSocket connection
            realtime_websocket: OpenAI Realtime WebSocket connection
            call_recorder: Optional call recorder instance
            enable_quality_monitoring: Whether to enable quality monitoring
            quality_thresholds: Quality monitoring thresholds
            bridge_type: Type of bridge (twilio, audiocodes, etc.)
            enable_resilience: Whether to enable resilience features
        """
        # Initialize base class
        super().__init__(
            platform_websocket=platform_websocket,
            realtime_websocket=realtime_websocket,
            call_recorder=call_recorder,
            enable_quality_monitoring=enable_quality_monitoring,
            quality_thresholds=quality_thresholds,
            bridge_type=bridge_type
        )
        
        self.enable_resilience = enable_resilience
        
        if enable_resilience:
            # Initialize resilience components
            self._init_resilience_components()
        
        logger.info(f"Enhanced audio stream handler initialized (resilience: {enable_resilience})")
    
    def _init_resilience_components(self):
        """Initialize resilience components."""
        # Audio validation and recovery
        self.audio_validator = AudioDataValidator()
        self.chunk_recovery = AudioChunkRecovery(
            max_chunk_delay_ms=500,
            sample_rate=self.internal_sample_rate
        )
        
        # Circuit breakers for external services
        self.openai_circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30.0,
            name="openai_api"
        )
        
        self.platform_circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=10.0,
            name="platform_websocket"
        )
        
        # Quality management
        self.quality_manager = AdaptiveQualityManager(initial_quality='high')
        
        # Message delivery
        self.message_sender = ReliableMessageSender(
            max_retries=3,
            ack_timeout=2.0,
            enable_acks=False  # Disable acks for now to maintain compatibility
        )
        
        # Performance tracking with memory management
        self.performance_metrics = {
            'audio_processing_times': deque(maxlen=100),  # Limit to last 100 samples
            'network_latencies': deque(maxlen=100),      # Limit to last 100 samples
            'error_counts': {'validation': 0, 'network': 0, 'service': 0},
            'recovery_events': 0
        }
        
        logger.info("Resilience components initialized")
    
    async def handle_incoming_audio(self, data: Dict[str, Any]) -> None:
        """
        Enhanced incoming audio handling with comprehensive error recovery.
        
        Args:
            data: Audio chunk data containing base64 encoded audio
        """
        start_time = time.time()
        
        if self._closed or self.realtime_websocket.close_code is not None:
            logger.warning("Skipping audio chunk - connection closed or websocket unavailable")
            return
        
        audio_chunk_b64 = data.get("audioChunk")
        if not audio_chunk_b64:
            logger.warning("No audio chunk data provided")
            return
        
        try:
            # Enhanced audio processing with resilience
            if self.enable_resilience:
                await self._handle_incoming_audio_with_resilience(audio_chunk_b64, start_time)
            else:
                # Fallback to original implementation
                await super().handle_incoming_audio(data)
                
        except Exception as e:
            logger.error(f"Error in enhanced audio processing: {e}")
            self._record_error('service', time.time() - start_time)
    
    async def _handle_incoming_audio_with_resilience(self, audio_chunk_b64: str, start_time: float):
        """Handle incoming audio with comprehensive resilience features."""
        try:
            # Step 1: Validate and decode audio with recovery
            audio_bytes = await self._validate_and_decode_audio(audio_chunk_b64)
            if not audio_bytes:
                logger.warning("Audio validation failed, skipping chunk")
                return
            
            # Step 2: Process chunk with timing recovery
            recovery_result = await self.chunk_recovery.process_chunk_with_recovery(
                audio_chunk_b64, 
                timestamp=start_time
            )
            
            if recovery_result['recovery_applied']:
                logger.info(f"Applied recovery: {recovery_result['recovery_type']}")
                self.performance_metrics['recovery_events'] += 1
            
            # Step 3: Quality analysis and adaptive adjustment
            quality_metrics = self.audio_validator.validate_audio_quality(
                audio_bytes, 
                sample_rate=self.internal_sample_rate
            )
            
            if quality_metrics['issues']:
                logger.warning(f"Audio quality issues detected: {quality_metrics['issues']}")
            
            # Step 4: Adaptive quality management
            if self.quality_manager.should_adjust_quality():
                logger.debug(f"Quality adjustment triggered - current: {self.quality_manager.current_quality}")
                new_quality = self.quality_manager.adjust_quality()
                if new_quality:
                    logger.info(f"Quality adjusted from {self.quality_manager.current_quality} to: {new_quality}")
                    await self._apply_quality_settings(new_quality)
                else:
                    logger.debug("Quality adjustment evaluated but no change needed")
            else:
                logger.debug(f"Quality adjustment not triggered - current: {self.quality_manager.current_quality}")
            
            # Step 5: Process audio with circuit breaker protection
            await self._process_audio_with_circuit_breaker(audio_bytes, start_time)
            
            # Record performance metrics
            processing_time = time.time() - start_time
            self._record_performance_metrics(processing_time)
            
        except Exception as e:
            logger.error(f"Resilient audio processing failed: {e}")
            self._record_error('service', time.time() - start_time)
    
    async def _validate_and_decode_audio(self, audio_chunk_b64: str) -> Optional[bytes]:
        """Validate and decode audio with comprehensive error handling."""
        try:
            # Use enhanced validation
            audio_bytes = self.audio_validator.validate_and_decode_audio(
                audio_chunk_b64,
                expected_size_range=(100, 10000),  # Reasonable size range
                fallback_silence_ms=100,
                sample_rate=self.internal_sample_rate
            )
            
            # Additional quality checks
            quality_metrics = self.audio_validator.validate_audio_quality(
                audio_bytes, 
                sample_rate=self.internal_sample_rate
            )
            
            if not quality_metrics['valid']:
                logger.warning(f"Audio quality validation failed: {quality_metrics.get('error')}")
                # Return sanitized audio
                audio_bytes = self.audio_validator.sanitize_audio_data(audio_bytes)
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Audio validation failed: {e}")
            self._record_error('validation', 0)
            # Return silence as fallback
            return b"\x00" * 3200  # 100ms at 16kHz
    
    async def _process_audio_with_circuit_breaker(self, audio_bytes: bytes, start_time: float):
        """Process audio with circuit breaker protection for external services."""
        try:
            # Determine original sample rate
            original_rate = {
                'twilio': 8000,
                'audiocodes': 16000,
                'call_agent': 16000,
            }.get(self.bridge_type, 16000)
            
            # Resample to internal rate if necessary
            if original_rate != self.internal_sample_rate:
                audio_bytes = await self._resample_audio_with_circuit_breaker(
                    audio_bytes, original_rate, self.internal_sample_rate
                )
            
            # VAD processing (if enabled)
            if self.vad_enabled and self.vad:
                await self._process_vad_with_recovery(audio_bytes)
            
            # Quality monitoring
            if self.enable_quality_monitoring and self.quality_monitor:
                await self._monitor_quality_with_recovery(audio_bytes)
            
            # Record caller audio
            if self.call_recorder:
                await self._record_audio_with_recovery(audio_bytes)
            
            # Send to OpenAI with circuit breaker protection
            await self._send_to_openai_with_circuit_breaker(audio_bytes)
            
        except Exception as e:
            logger.error(f"Audio processing with circuit breaker failed: {e}")
            self._record_error('service', time.time() - start_time)
    
    async def _resample_audio_with_circuit_breaker(self, audio_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
        """Resample audio with circuit breaker protection."""
        try:
            # Use circuit breaker for resampling operation
            result = await self.openai_circuit_breaker.call(
                self._resample_audio_safe, audio_bytes, from_rate, to_rate
            )
            return result
        except Exception as e:
            logger.warning(f"Resampling failed, using original audio: {e}")
            return audio_bytes
    
    def _resample_audio_safe(self, audio_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
        """Safe resampling operation."""
        try:
            from opusagent.audio_stream_handler import AudioUtils
            return AudioUtils.resample_audio(audio_bytes, from_rate, to_rate)
        except Exception as e:
            logger.error(f"Resampling error: {e}")
            raise
    
    async def _process_vad_with_recovery(self, audio_bytes: bytes):
        """Process VAD with error recovery."""
        try:
            from opusagent.audio_stream_handler import to_float32_mono
            
            # Convert to float32 mono for VAD
            audio_arr = to_float32_mono(audio_bytes, sample_width=2, channels=1)
            vad_result = self.vad.process_audio(audio_arr)
            
            # Handle VAD state transitions
            await self._handle_vad_transitions(vad_result)
            
        except Exception as e:
            logger.warning(f"VAD processing failed: {e}")
            # Continue without VAD
            pass
    
    async def _handle_vad_transitions(self, vad_result: Dict[str, Any]):
        """Handle VAD state transitions with error recovery."""
        try:
            is_speech = vad_result.get('is_speech', False)
            speech_prob = vad_result.get('speech_prob', 0.0)
            
            # Emit VAD events on state transitions
            if is_speech and not self._speech_active:
                await self._send_vad_event('speech_started', speech_prob)
                self._speech_active = True
            elif not is_speech and self._speech_active:
                await self._send_vad_event('speech_stopped', speech_prob)
                self._speech_active = False
                
        except Exception as e:
            logger.warning(f"VAD transition handling failed: {e}")
    
    async def _send_vad_event(self, event_type: str, speech_prob: float):
        """Send VAD event with reliable delivery."""
        try:
            from opusagent.models.audiocodes_api import (
                UserStreamSpeechStartedResponse,
                UserStreamSpeechStoppedResponse,
                TelephonyEventType
            )
            
            if event_type == 'speech_started':
                vad_event = UserStreamSpeechStartedResponse(
                    type=TelephonyEventType.USER_STREAM_SPEECH_STARTED,
                    conversationId=self.conversation_id,
                    participant="caller",
                    participantId="caller",
                )
            else:
                vad_event = UserStreamSpeechStoppedResponse(
                    type=TelephonyEventType.USER_STREAM_SPEECH_STOPPED,
                    conversationId=self.conversation_id,
                    participant="caller",
                    participantId="caller",
                )
            
            # Send with reliable delivery
            success = await self.message_sender.send_with_ack(
                self.platform_websocket, 
                vad_event.model_dump(),
                f"vad_{event_type}"
            )
            
            if success:
                logger.info(f"VAD {event_type} event sent (prob: {speech_prob:.3f})")
            else:
                logger.warning(f"Failed to send VAD {event_type} event")
                
        except Exception as e:
            logger.error(f"Error sending VAD event: {e}")
    
    async def _monitor_quality_with_recovery(self, audio_bytes: bytes):
        """Monitor audio quality with error recovery."""
        try:
            if self.quality_monitor is None:
                return
                
            quality_metrics = self.quality_monitor.analyze_audio_chunk(audio_bytes)
            
            # Record quality metrics for adaptive management
            self.quality_manager.record_success(quality_metrics.quality_score)
            
            logger.debug(
                f"Audio quality - SNR: {quality_metrics.snr_db:.1f}dB, "
                f"Score: {quality_metrics.quality_score:.1f}"
            )
            
        except Exception as e:
            logger.warning(f"Quality monitoring failed: {e}")
            self.quality_manager.record_error(0.0)  # Record error for adaptive management
    
    async def _record_audio_with_recovery(self, audio_bytes: bytes):
        """Record audio with error recovery."""
        try:
            if self.call_recorder is None:
                return
                
            audio_chunk_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            await self.call_recorder.record_caller_audio(audio_chunk_b64)
        except Exception as e:
            logger.warning(f"Audio recording failed: {e}")
    
    async def _send_to_openai_with_circuit_breaker(self, audio_bytes: bytes):
        """Send audio to OpenAI with circuit breaker protection."""
        try:
            # Resample to OpenAI 24kHz
            openai_rate = 24000
            openai_audio = await self.openai_circuit_breaker.call(
                self._resample_audio_safe, audio_bytes, self.internal_sample_rate, openai_rate
            )
            
            audio_chunk_b64 = base64.b64encode(openai_audio).decode("utf-8")
            
            # Update tracking
            self.total_audio_bytes_sent += len(openai_audio)
            self.audio_chunks_sent += 1
            
            # Send to OpenAI with reliable delivery
            from opusagent.models.openai_api import InputAudioBufferAppendEvent
            
            audio_append = InputAudioBufferAppendEvent(
                type="input_audio_buffer.append", 
                audio=audio_chunk_b64
            )
            
            success = await self.message_sender.send_with_ack(
                self.realtime_websocket,
                audio_append.model_dump(),
                "audio_append"
            )
            
            if success:
                logger.debug(f"Audio sent to OpenAI: {len(openai_audio)} bytes")
            else:
                logger.warning("Failed to send audio to OpenAI")
                
        except Exception as e:
            logger.error(f"OpenAI audio sending failed: {e}")
            self._record_error('service', 0)
    
    async def _apply_quality_settings(self, quality_level: str):
        """Apply new quality settings."""
        try:
            quality_config = self.quality_manager.get_quality_level_config(quality_level)
            if quality_config:
                # Update internal sample rate based on quality
                self.internal_sample_rate = quality_config.sample_rate
                logger.info(f"Applied quality settings: {quality_level} ({quality_config.sample_rate}Hz)")
        except Exception as e:
            logger.error(f"Failed to apply quality settings: {e}")
    
    def _record_performance_metrics(self, processing_time: float):
        """Record performance metrics for adaptive management."""
        self.performance_metrics['audio_processing_times'].append(processing_time)
        
        # Update quality manager (deque automatically manages size)
        if self.performance_metrics['audio_processing_times']:
            avg_processing_time = sum(self.performance_metrics['audio_processing_times']) / len(self.performance_metrics['audio_processing_times'])
            self.quality_manager.record_success(avg_processing_time * 1000)  # Convert to ms
    
    def _record_error(self, error_type: str, processing_time: float):
        """Record error for monitoring and adaptive management."""
        self.performance_metrics['error_counts'][error_type] += 1
        self.quality_manager.record_error(processing_time * 1000)  # Convert to ms
    
    def get_resilience_statistics(self) -> Dict[str, Any]:
        """Get comprehensive resilience statistics."""
        if not self.enable_resilience:
            return {'resilience_enabled': False}
        
        return {
            'resilience_enabled': True,
            'audio_validation': {
                'total_chunks_processed': self.audio_chunks_sent,
                'validation_errors': self.performance_metrics['error_counts']['validation']
            },
            'chunk_recovery': self.chunk_recovery.get_recovery_statistics(),
            'circuit_breakers': {
                'openai': self.openai_circuit_breaker.get_statistics(),
                'platform': self.platform_circuit_breaker.get_statistics()
            },
            'quality_management': self.quality_manager.get_statistics(),
            'message_delivery': self.message_sender.get_delivery_statistics(),
            'performance_metrics': {
                'avg_processing_time_ms': sum(self.performance_metrics['audio_processing_times']) / len(self.performance_metrics['audio_processing_times']) if self.performance_metrics['audio_processing_times'] else 0,
                'recovery_events': self.performance_metrics['recovery_events'],
                'error_counts': self.performance_metrics['error_counts']
            }
        }
    
    async def close(self) -> None:
        """Close the enhanced audio stream handler."""
        if self.enable_resilience:
            # Log final statistics
            stats = self.get_resilience_statistics()
            logger.info(f"Enhanced audio stream handler closing. Final stats: {stats}")
        
        await super().close() 