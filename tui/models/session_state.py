"""
Session state management for the TUI application.

This module provides classes for managing session state, audio streams,
and conversation data during real-time communication sessions.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from opusagent.config.constants import DEFAULT_SAMPLE_RATE

logger = logging.getLogger(__name__)

class SessionStatus(Enum):
    """Session status enumeration."""
    IDLE = "idle"
    INITIATING = "initiating"
    ACTIVE = "active"
    ENDING = "ending"
    ENDED = "ended"
    ERROR = "error"

class StreamStatus(Enum):
    """Audio stream status enumeration."""
    IDLE = "idle"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    STOPPED = "stopped"

@dataclass
class SessionMetrics:
    """Session performance metrics."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    messages_sent: int = 0
    messages_received: int = 0
    audio_chunks_sent: int = 0
    audio_chunks_received: int = 0
    errors_count: int = 0
    latency_ms: Optional[float] = None
    
    def get_duration(self) -> float:
        """Get session duration in seconds."""
        if self.start_time:
            end = self.end_time or datetime.now()
            return (end - self.start_time).total_seconds()
        return 0.0

@dataclass
class AudioStreamState:
    """Audio stream state information."""
    status: StreamStatus = StreamStatus.IDLE
    media_format: str = "raw/lpcm16"
    sample_rate: int = DEFAULT_SAMPLE_RATE
    channels: int = 1
    chunk_count: int = 0
    total_bytes: int = 0
    start_time: Optional[datetime] = None
    
    def reset(self) -> None:
        """Reset stream state."""
        self.status = StreamStatus.IDLE
        self.chunk_count = 0
        self.total_bytes = 0
        self.start_time = None

class SessionState:
    """
    Manages session state and conversation data for TelephonyRealtimeBridge.
    
    Tracks session lifecycle, conversation metadata, audio streams,
    and performance metrics throughout the call flow.
    """
    
    def __init__(self):
        # Session identification
        self.conversation_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.bot_name: str = "voice-bot"
        self.caller: str = "tui-validator"
        
        # Session state
        self.status: SessionStatus = SessionStatus.IDLE
        self.is_active: bool = False
        self.media_format: str = "raw/lpcm16"
        self.supported_formats: List[str] = ["raw/lpcm16"]
        
        # Audio streams
        self.user_stream: AudioStreamState = AudioStreamState()
        self.bot_stream: AudioStreamState = AudioStreamState()
        
        # Session metrics
        self.metrics: SessionMetrics = SessionMetrics()
        
        # Message history (limited)
        self.message_history: List[Dict[str, Any]] = []
        self.max_history_size: int = 100
        
        # Event callbacks
        self._status_change_callbacks: List[Callable] = []
        self._metrics_update_callbacks: List[Callable] = []
    
    def initiate_session(self, bot_name: str = None, caller: str = None) -> str:
        """
        Initiate a new session.
        
        Args:
            bot_name: Name of the bot (optional)
            caller: Caller identifier (optional)
            
        Returns:
            Generated conversation ID
        """
        if self.status != SessionStatus.IDLE:
            logger.warning(f"Cannot initiate session in status: {self.status}")
            return self.conversation_id
        
        # Generate new conversation ID
        self.conversation_id = str(uuid.uuid4())
        
        # Update session parameters
        if bot_name:
            self.bot_name = bot_name
        if caller:
            self.caller = caller
        
        # Reset state
        self.session_id = None
        self.is_active = False
        self.user_stream.reset()
        self.bot_stream.reset()
        self.message_history.clear()
        
        # Initialize metrics
        self.metrics = SessionMetrics(start_time=datetime.now())
        
        # Update status
        self._update_status(SessionStatus.INITIATING)
        
        logger.info(f"Session initiated: {self.conversation_id}")
        return self.conversation_id
    
    def accept_session(self, session_id: str = None) -> None:
        """
        Mark session as accepted.
        
        Args:
            session_id: Session ID from the server
        """
        if self.status != SessionStatus.INITIATING:
            logger.warning(f"Cannot accept session in status: {self.status}")
            return
        
        self.session_id = session_id
        self.is_active = True
        self._update_status(SessionStatus.ACTIVE)
        
        logger.info(f"Session accepted: {self.session_id}")
    
    def end_session(self) -> None:
        """End the current session."""
        if self.status not in [SessionStatus.ACTIVE, SessionStatus.INITIATING]:
            logger.warning(f"Cannot end session in status: {self.status}")
            return
        
        self._update_status(SessionStatus.ENDING)
        
        # Stop any active streams
        if self.user_stream.status == StreamStatus.ACTIVE:
            self.stop_user_stream()
        
        # Update metrics
        self.metrics.end_time = datetime.now()
        self.metrics.duration_seconds = self.metrics.get_duration()
        
        # Reset session state
        self.is_active = False
        self._update_status(SessionStatus.ENDED)
        
        logger.info(f"Session ended: {self.conversation_id}")
    
    def start_user_stream(self, media_format: str = None) -> None:
        """Start user audio stream."""
        if not self.is_active:
            logger.warning("Cannot start user stream: Session not active")
            return
        
        if media_format:
            self.user_stream.media_format = media_format
        
        self.user_stream.status = StreamStatus.STARTING
        self.user_stream.start_time = datetime.now()
        self.user_stream.chunk_count = 0
        self.user_stream.total_bytes = 0
        
        logger.debug("User stream starting")
    
    def user_stream_started(self) -> None:
        """Mark user stream as started."""
        if self.user_stream.status == StreamStatus.STARTING:
            self.user_stream.status = StreamStatus.ACTIVE
            logger.debug("User stream started")
    
    def stop_user_stream(self) -> None:
        """Stop user audio stream."""
        if self.user_stream.status == StreamStatus.ACTIVE:
            self.user_stream.status = StreamStatus.STOPPING
            logger.debug("User stream stopping")
    
    def user_stream_stopped(self) -> None:
        """Mark user stream as stopped."""
        if self.user_stream.status == StreamStatus.STOPPING:
            self.user_stream.status = StreamStatus.STOPPED
            logger.debug("User stream stopped")
    
    def handle_user_audio_chunk(self, chunk_data: str) -> None:
        """Handle incoming user audio chunk."""
        if self.user_stream.status == StreamStatus.ACTIVE:
            self.user_stream.chunk_count += 1
            # Estimate bytes from base64 (3/4 ratio)
            self.user_stream.total_bytes += len(chunk_data) * 3 // 4
            self.metrics.audio_chunks_sent += 1
    
    def handle_bot_audio_start(self, media_format: str = None) -> None:
        """Handle bot audio stream start."""
        if media_format:
            self.bot_stream.media_format = media_format
        
        self.bot_stream.status = StreamStatus.ACTIVE
        self.bot_stream.start_time = datetime.now()
        self.bot_stream.chunk_count = 0
        self.bot_stream.total_bytes = 0
        
        logger.debug("Bot stream started")
    
    def handle_bot_audio_chunk(self, chunk_data: str) -> None:
        """Handle incoming bot audio chunk."""
        if self.bot_stream.status == StreamStatus.ACTIVE:
            self.bot_stream.chunk_count += 1
            # Estimate bytes from base64 (3/4 ratio)
            self.bot_stream.total_bytes += len(chunk_data) * 3 // 4
            self.metrics.audio_chunks_received += 1
    
    def handle_bot_audio_stop(self) -> None:
        """Handle bot audio stream stop."""
        self.bot_stream.status = StreamStatus.STOPPED
        logger.debug("Bot stream stopped")
    
    def add_message(self, message: Dict[str, Any], direction: str = "in") -> None:
        """
        Add a message to the history.
        
        Args:
            message: Message data
            direction: "in" for incoming, "out" for outgoing
        """
        message_entry = {
            "timestamp": datetime.now().isoformat(),
            "direction": direction,
            "type": message.get("type", "unknown"),
            "data": message
        }
        
        self.message_history.append(message_entry)
        
        # Maintain history size limit
        if len(self.message_history) > self.max_history_size:
            self.message_history = self.message_history[-self.max_history_size:]
        
        # Update metrics
        if direction == "in":
            self.metrics.messages_received += 1
        else:
            self.metrics.messages_sent += 1
    
    def handle_error(self, error: Dict[str, Any]) -> None:
        """Handle error event."""
        self.metrics.errors_count += 1
        self._update_status(SessionStatus.ERROR)
        
        error_code = error.get("error", {}).get("code", "unknown")
        error_message = error.get("error", {}).get("message", "Unknown error")
        
        logger.error(f"Session error: {error_code} - {error_message}")
    
    def update_latency(self, latency_ms: float) -> None:
        """Update session latency metric."""
        self.metrics.latency_ms = latency_ms
        
        # Trigger metrics update callbacks
        for callback in self._metrics_update_callbacks:
            try:
                callback(self.metrics)
            except Exception as e:
                logger.error(f"Error in metrics callback: {e}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session."""
        return {
            "conversation_id": self.conversation_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "is_active": self.is_active,
            "bot_name": self.bot_name,
            "caller": self.caller,
            "media_format": self.media_format,
            "duration": self.metrics.get_duration(),
            "user_stream_status": self.user_stream.status.value,
            "bot_stream_status": self.bot_stream.status.value,
            "messages_sent": self.metrics.messages_sent,
            "messages_received": self.metrics.messages_received,
            "audio_chunks_sent": self.metrics.audio_chunks_sent,
            "audio_chunks_received": self.metrics.audio_chunks_received,
            "errors_count": self.metrics.errors_count,
            "latency_ms": self.metrics.latency_ms,
        }
    
    def reset(self) -> None:
        """Reset session state to initial state."""
        self.conversation_id = None
        self.session_id = None
        self.is_active = False
        self.user_stream.reset()
        self.bot_stream.reset()
        self.metrics = SessionMetrics()
        self.message_history.clear()
        self._update_status(SessionStatus.IDLE)
        
        logger.info("Session state reset")
    
    def add_status_change_callback(self, callback: Callable) -> None:
        """Add a callback for status changes."""
        self._status_change_callbacks.append(callback)
    
    def add_metrics_update_callback(self, callback: Callable) -> None:
        """Add a callback for metrics updates."""
        self._metrics_update_callbacks.append(callback)
    
    def _update_status(self, new_status: SessionStatus) -> None:
        """Update session status and trigger callbacks."""
        old_status = self.status
        self.status = new_status
        
        logger.debug(f"Session status: {old_status.value} -> {new_status.value}")
        
        # Trigger status change callbacks
        for callback in self._status_change_callbacks:
            try:
                callback(old_status, new_status)
            except Exception as e:
                logger.error(f"Error in status change callback: {e}")
    
    def is_stream_active(self) -> bool:
        """Check if any audio stream is active."""
        return (self.user_stream.status == StreamStatus.ACTIVE or 
                self.bot_stream.status == StreamStatus.ACTIVE)
    
    def get_connection_display_info(self) -> tuple:
        """Get information for connection display."""
        session_str = self.session_id[:8] + "..." if self.session_id else "Not established"
        conv_str = self.conversation_id[:8] + "..." if self.conversation_id else "N/A"
        return session_str, conv_str 