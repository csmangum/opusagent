"""
Configuration management for the Interactive TUI Validator.

This module provides configuration settings using the centralized configuration system.
Legacy environment variable loading is maintained for backward compatibility.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import centralized configuration
try:
    from opusagent.config import tui_config as get_centralized_tui_config
    from opusagent.config.constants import DEFAULT_SAMPLE_RATE
    _has_centralized_config = True
except ImportError:
    _has_centralized_config = False
    # Fallback constant if centralized config is not available
    DEFAULT_SAMPLE_RATE = 16000


@dataclass
class TUIConfig:
    """Configuration settings for the TUI application.
    
    Now uses centralized configuration system with fallback to environment variables.
    """
    
    # WebSocket connection settings
    host: str = "localhost"
    port: int = 8000
    ws_path: str = "/voice-bot"
    
    # Connection settings
    timeout_seconds: int = 15
    ping_interval: int = 5
    ping_timeout: int = 20
    reconnect_attempts: int = 3
    reconnect_delay: int = 2
    
    # Session settings
    bot_name: str = "voice-bot"
    caller_id: str = "tui-validator"
    session_timeout: int = 300  # 5 minutes
    auto_reconnect: bool = True
    
    # VAD settings
    vad_enabled: bool = True  # Enable Voice Activity Detection by default
    show_vad_events: bool = True  # Show VAD events in the TUI
    
    # Audio settings
    audio_chunk_size: int = 32000  # 2 seconds of 16kHz 16-bit audio
    sample_rate: int = 16000  # 16kHz
    audio_format: str = "raw/lpcm16"
    supported_formats: Optional[List[str]] = None
    
    # Recording settings
    enable_audio_recording: bool = True
    recordings_dir: str = "test_logs"
    max_recording_duration: int = 300  # 5 minutes max
    
    # UI settings
    refresh_rate: int = 60  # FPS for UI updates
    log_max_lines: int = 1000
    transcript_max_lines: int = 500
    events_max_lines: int = 200
    
    # Message filtering
    show_audio_chunks: bool = False
    show_debug_messages: bool = True
    filter_heartbeat_messages: bool = True
    
    # Event logging
    max_events: int = 1000
    log_level: str = "INFO"
    export_format: str = "json"
    auto_export_on_session_end: bool = False
    
    # Appearance
    theme: str = "dark"
    show_timestamps: bool = True
    show_latency: bool = True
    
    def __post_init__(self):
        """Initialize configuration from centralized config or environment variables."""
        if _has_centralized_config:
            # Use centralized configuration system
            centralized_config = get_centralized_tui_config()
            
            # Map centralized config to TUI config fields
            self.host = centralized_config.host
            self.port = centralized_config.port
            self.ws_path = centralized_config.ws_path
            self.timeout_seconds = centralized_config.timeout_seconds
            self.ping_interval = centralized_config.ping_interval
            self.ping_timeout = centralized_config.ping_timeout
            self.reconnect_attempts = centralized_config.reconnect_attempts
            self.reconnect_delay = centralized_config.reconnect_delay
            self.bot_name = centralized_config.bot_name
            self.caller_id = centralized_config.caller_id
            self.session_timeout = centralized_config.session_timeout
            self.auto_reconnect = centralized_config.auto_reconnect
            self.vad_enabled = centralized_config.vad_enabled
            self.show_vad_events = centralized_config.show_vad_events
            self.sample_rate = getattr(centralized_config, "sample_rate", DEFAULT_SAMPLE_RATE)
            self.audio_format = getattr(centralized_config, "audio_format", "raw/lpcm16")
            self.enable_audio_recording = centralized_config.enable_audio_recording
            self.recordings_dir = centralized_config.recordings_dir
            self.max_recording_duration = centralized_config.max_recording_duration
            self.refresh_rate = centralized_config.refresh_rate
            self.log_max_lines = centralized_config.log_max_lines
            self.transcript_max_lines = centralized_config.transcript_max_lines
            self.events_max_lines = centralized_config.events_max_lines
            self.show_audio_chunks = centralized_config.show_audio_chunks
            self.show_debug_messages = centralized_config.show_debug_messages
            self.filter_heartbeat_messages = centralized_config.filter_heartbeat_messages
            self.max_events = centralized_config.max_events
            self.log_level = centralized_config.log_level
            self.export_format = centralized_config.export_format
            self.auto_export_on_session_end = centralized_config.auto_export_on_session_end
            self.theme = centralized_config.theme
            self.show_timestamps = centralized_config.show_timestamps
            self.show_latency = centralized_config.show_latency
        else:
            # Fallback to environment variables (legacy mode)
            self._load_from_environment()
        
        # Default supported formats
        if self.supported_formats is None:
            self.supported_formats = ["raw/lpcm16", "g711/ulaw", "g711/alaw"]
        
        # Create recordings directory if it doesn't exist
        Path(self.recordings_dir).mkdir(parents=True, exist_ok=True)
    
    def _load_from_environment(self):
        """Load configuration from environment variables (legacy fallback)."""
        # WebSocket settings
        self.host = os.getenv("TUI_HOST", self.host)
        self.port = int(os.getenv("TUI_PORT", str(self.port)))
        self.ws_path = os.getenv("TUI_WS_PATH", self.ws_path)
        
        # Connection settings
        self.timeout_seconds = int(os.getenv("TUI_TIMEOUT", str(self.timeout_seconds)))
        self.reconnect_attempts = int(os.getenv("TUI_RECONNECT_ATTEMPTS", str(self.reconnect_attempts)))
        self.auto_reconnect = os.getenv("TUI_AUTO_RECONNECT", "true").lower() == "true"
        
        # Session settings
        self.bot_name = os.getenv("TUI_BOT_NAME", self.bot_name)
        self.caller_id = os.getenv("TUI_CALLER_ID", self.caller_id)
        self.session_timeout = int(os.getenv("TUI_SESSION_TIMEOUT", str(self.session_timeout)))
        
        # VAD settings
        self.vad_enabled = os.getenv("TUI_VAD_ENABLED", "true").lower() == "true"
        self.show_vad_events = os.getenv("TUI_SHOW_VAD_EVENTS", "true").lower() == "true"
        
        # Audio settings
        self.sample_rate = int(os.getenv("TUI_SAMPLE_RATE", str(self.sample_rate)))
        self.audio_format = os.getenv("TUI_AUDIO_FORMAT", self.audio_format)
        
        # Recording settings
        self.enable_audio_recording = os.getenv("TUI_ENABLE_RECORDING", "true").lower() == "true"
        self.recordings_dir = os.getenv("TUI_RECORDINGS_DIR", self.recordings_dir)
        
        # UI settings
        self.refresh_rate = int(os.getenv("TUI_REFRESH_RATE", str(self.refresh_rate)))
        self.theme = os.getenv("TUI_THEME", self.theme)
        
        # Message filtering
        self.show_audio_chunks = os.getenv("TUI_SHOW_AUDIO_CHUNKS", "false").lower() == "true"
        self.show_debug_messages = os.getenv("TUI_SHOW_DEBUG", "true").lower() == "true"
        self.filter_heartbeat_messages = os.getenv("TUI_FILTER_HEARTBEAT", "true").lower() == "true"
        
        # Event logging
        self.max_events = int(os.getenv("TUI_MAX_EVENTS", str(self.max_events)))
        self.log_level = os.getenv("TUI_LOG_LEVEL", self.log_level)
        self.export_format = os.getenv("TUI_EXPORT_FORMAT", self.export_format)
        self.auto_export_on_session_end = os.getenv("TUI_AUTO_EXPORT", "false").lower() == "true"
    
    @property
    def ws_url(self) -> str:
        """Get the full WebSocket URL."""
        return f"ws://{self.host}:{self.port}{self.ws_path}"
    
    @property
    def server_url(self) -> str:
        """Get the server URL for display."""
        return f"{self.host}:{self.port}"
    
    def get_audio_file_path(self, filename: str) -> Path:
        """Get the full path for an audio file."""
        return Path(self.recordings_dir) / filename
    
    def get_export_file_path(self, filename: str) -> Path:
        """Get the full path for an export file."""
        return Path(self.recordings_dir) / filename
    
    def is_valid(self) -> bool:
        """Validate the configuration."""
        try:
            # Check required settings
            if not self.host or self.port <= 0:
                return False
            
            # Check audio settings
            if self.sample_rate <= 0 or self.audio_chunk_size <= 0:
                return False
            
            # Check session settings
            if self.session_timeout <= 0:
                return False
            
            # Check directory exists and is writable
            recordings_path = Path(self.recordings_dir)
            if not recordings_path.exists():
                recordings_path.mkdir(parents=True, exist_ok=True)
            
            return True
        except Exception:
            return False
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "host": self.host,
            "port": self.port,
            "ws_path": self.ws_path,
            "ws_url": self.ws_url,
            "timeout_seconds": self.timeout_seconds,
            "bot_name": self.bot_name,
            "caller_id": self.caller_id,
            "sample_rate": self.sample_rate,
            "audio_format": self.audio_format,
            "recordings_dir": self.recordings_dir,
            "theme": self.theme,
            "max_events": self.max_events,
            "log_level": self.log_level,
            "auto_reconnect": self.auto_reconnect,
            "vad_enabled": self.vad_enabled,
            "show_vad_events": self.show_vad_events,
        }


# Global configuration instance
config = TUIConfig() 