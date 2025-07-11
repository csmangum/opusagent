"""
Audio chunk recovery and timing management.

This module provides utilities for handling network jitter, chunk timing issues,
and recovery mechanisms for audio processing in real-time systems.
"""

import asyncio
import logging
import time
from collections import deque
from typing import Optional, List, Dict, Any

from .audio_validator import AudioDataValidator

logger = logging.getLogger(__name__)


class AudioChunkRecovery:
    """Handles audio chunk recovery and timing management for network jitter."""
    
    def __init__(
        self, 
        max_chunk_delay_ms: int = 500,
        silence_threshold: float = 0.01,
        buffer_size: int = 10,
        sample_rate: int = 16000
    ):
        """
        Initialize audio chunk recovery system.
        
        Args:
            max_chunk_delay_ms: Maximum acceptable chunk delay before recovery
            silence_threshold: Threshold for detecting silence
            buffer_size: Number of chunks to buffer for timing recovery
            sample_rate: Audio sample rate for calculations
        """
        self.max_chunk_delay_ms = max_chunk_delay_ms
        self.silence_threshold = silence_threshold
        self.buffer_size = buffer_size
        self.sample_rate = sample_rate
        
        # Timing state
        self.last_chunk_time = None
        self.expected_chunk_interval_ms = 100  # 100ms chunks
        self.chunk_buffer = deque(maxlen=buffer_size)
        
        # Recovery statistics
        self.total_chunks_processed = 0
        self.chunks_with_delay = 0
        self.silence_insertions = 0
        self.recovery_events = 0
        self.successful_recoveries = 0  # Track successful recoveries
        
    async def process_chunk_with_recovery(
        self, 
        audio_chunk_b64: str, 
        timestamp: Optional[float] = None,
        chunk_sequence: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process audio chunk with network jitter recovery.
        
        Args:
            audio_chunk_b64: Base64 encoded audio chunk
            timestamp: Optional timestamp for the chunk
            chunk_sequence: Optional sequence number for ordering
            
        Returns:
            Dictionary with processed audio and recovery information
        """
        try:
            current_time = timestamp or time.time()
            self.total_chunks_processed += 1
            
            # Validate and decode audio
            audio_bytes = AudioDataValidator.validate_and_decode_audio(audio_chunk_b64)
            
            # Handle timing recovery
            recovery_info = await self._handle_timing_recovery(current_time, audio_bytes)
            
            # Track successful recoveries
            if recovery_info['recovery_applied']:
                self.successful_recoveries += 1
            
            # Store chunk in buffer
            chunk_info = {
                'timestamp': current_time,
                'sequence': chunk_sequence,
                'audio_bytes': audio_bytes,
                'size': len(audio_bytes),
                'recovery_info': recovery_info
            }
            self.chunk_buffer.append(chunk_info)
            
            # Update timing state
            self.last_chunk_time = current_time
            
            return {
                'audio_bytes': audio_bytes,
                'processed': True,
                'recovery_applied': recovery_info['recovery_applied'],
                'delay_ms': recovery_info['delay_ms'],
                'silence_inserted': recovery_info['silence_inserted'],
                'chunk_sequence': chunk_sequence,
                'timestamp': current_time
            }
            
        except Exception as e:
            logger.error(f"Chunk recovery failed: {e}")
            self.recovery_events += 1
            
            # Return silence as fallback
            fallback_silence = b"\x00" * 3200  # 100ms at 16kHz
            return {
                'audio_bytes': fallback_silence,
                'processed': False,
                'error': str(e),
                'recovery_applied': True,
                'delay_ms': 0,
                'silence_inserted': len(fallback_silence),
                'chunk_sequence': chunk_sequence,
                'timestamp': current_time
            }
    
    async def _handle_timing_recovery(self, current_time: float, audio_bytes: bytes) -> Dict[str, Any]:
        """
        Handle timing recovery for network jitter.
        
        Args:
            current_time: Current timestamp
            audio_bytes: Decoded audio bytes
            
        Returns:
            Recovery information dictionary
        """
        recovery_info = {
            'recovery_applied': False,
            'delay_ms': 0,
            'silence_inserted': 0,
            'recovery_type': None
        }
        
        if self.last_chunk_time is None:
            # First chunk, no timing to recover
            return recovery_info
        
        # Calculate delay
        delay_ms = (current_time - self.last_chunk_time) * 1000
        recovery_info['delay_ms'] = delay_ms
        
        if delay_ms > self.max_chunk_delay_ms:
            # Large delay detected - insert silence to maintain timing
            self.chunks_with_delay += 1
            recovery_info['recovery_applied'] = True
            recovery_info['recovery_type'] = 'delay_compensation'
            
            # Calculate how much silence to insert
            expected_chunks = int(delay_ms / self.expected_chunk_interval_ms)
            silence_duration_ms = expected_chunks * self.expected_chunk_interval_ms
            silence_bytes = self._generate_silence(silence_duration_ms)
            
            recovery_info['silence_inserted'] = len(silence_bytes)
            self.silence_insertions += 1
            
            logger.warning(
                f"Large chunk delay detected: {delay_ms:.1f}ms. "
                f"Inserting {silence_duration_ms:.1f}ms of silence ({len(silence_bytes)} bytes)"
            )
            
            # Insert silence into buffer
            silence_chunk = {
                'timestamp': self.last_chunk_time + (self.expected_chunk_interval_ms / 1000),
                'sequence': None,
                'audio_bytes': silence_bytes,
                'size': len(silence_bytes),
                'recovery_info': {'recovery_type': 'silence_insertion'}
            }
            self.chunk_buffer.append(silence_chunk)
            
        elif delay_ms < self.expected_chunk_interval_ms * 0.5:
            # Chunks arriving too quickly - potential buffer overflow
            logger.debug(f"Chunks arriving quickly: {delay_ms:.1f}ms delay")
            recovery_info['recovery_type'] = 'rate_limiting'
            
        return recovery_info
    
    def _generate_silence(self, duration_ms: float) -> bytes:
        """
        Generate silence bytes for specified duration.
        
        Args:
            duration_ms: Duration in milliseconds
            
        Returns:
            Silence bytes
        """
        samples_needed = int(duration_ms * self.sample_rate / 1000)
        bytes_needed = samples_needed * 2  # 16-bit samples
        return b"\x00" * bytes_needed
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """
        Get recovery statistics and performance metrics.
        
        Returns:
            Dictionary with recovery statistics
        """
        if self.total_chunks_processed == 0:
            return {
                'total_chunks': 0,
                'delay_rate': 0.0,
                'silence_insertion_rate': 0.0,
                'recovery_rate': 0.0,
                'average_delay_ms': 0.0
            }
        
        return {
            'total_chunks': self.total_chunks_processed,
            'chunks_with_delay': self.chunks_with_delay,
            'silence_insertions': self.silence_insertions,
            'recovery_events': self.recovery_events,
            'successful_recoveries': self.successful_recoveries,
            'delay_rate': self.chunks_with_delay / self.total_chunks_processed,
            'silence_insertion_rate': self.silence_insertions / self.total_chunks_processed,
            'recovery_rate': self.successful_recoveries / self.total_chunks_processed if self.total_chunks_processed > 0 else 0.0,
            'buffer_utilization': len(self.chunk_buffer) / self.buffer_size,
            'average_delay_ms': self._calculate_average_delay()
        }
    
    def _calculate_average_delay(self) -> float:
        """Calculate average delay from recent chunks."""
        if not self.chunk_buffer:
            return 0.0
        
        delays = []
        prev_time = None
        
        for chunk in self.chunk_buffer:
            if prev_time is not None:
                delay_ms = (chunk['timestamp'] - prev_time) * 1000
                delays.append(delay_ms)
            prev_time = chunk['timestamp']
        
        return sum(delays) / len(delays) if delays else 0.0
    
    def reset_statistics(self) -> None:
        """Reset recovery statistics."""
        self.total_chunks_processed = 0
        self.chunks_with_delay = 0
        self.silence_insertions = 0
        self.recovery_events = 0
        self.successful_recoveries = 0
        self.chunk_buffer.clear()
        self.last_chunk_time = None
    
    def adjust_parameters(
        self, 
        max_chunk_delay_ms: Optional[int] = None,
        silence_threshold: Optional[float] = None,
        buffer_size: Optional[int] = None
    ) -> None:
        """
        Dynamically adjust recovery parameters based on performance.
        
        Args:
            max_chunk_delay_ms: New maximum delay threshold
            silence_threshold: New silence threshold
            buffer_size: New buffer size
        """
        if max_chunk_delay_ms is not None:
            self.max_chunk_delay_ms = max_chunk_delay_ms
            logger.info(f"Adjusted max chunk delay to {max_chunk_delay_ms}ms")
        
        if silence_threshold is not None:
            self.silence_threshold = silence_threshold
            logger.info(f"Adjusted silence threshold to {silence_threshold}")
        
        if buffer_size is not None:
            old_buffer_size = self.buffer_size
            self.buffer_size = buffer_size
            # Create new buffer with new size
            old_buffer = list(self.chunk_buffer)
            self.chunk_buffer = deque(maxlen=buffer_size)
            # Copy recent chunks to new buffer
            for chunk in old_buffer[-buffer_size:]:
                self.chunk_buffer.append(chunk)
            logger.info(f"Adjusted buffer size from {old_buffer_size} to {buffer_size}") 