"""
Configuration management for the Interactive TUI Validator.

This module provides configuration settings and environment variable handling
for the TUI application.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class TUIConfig:
    """Configuration settings for the TUI application."""
    
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
    
    # Audio settings
    audio_chunk_size: int = 32000  # 2 seconds of 16kHz 16-bit audio
    sample_rate: int = 16000  # 16kHz
    audio_format: str = "raw/lpcm16"
    supported_formats: List[str] = None
    
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
    
    # Appearance
    theme: str = "dark"
    show_timestamps: bool = True
    show_latency: bool = True
    
    def __post_init__(self):
        """Initialize configuration from environment variables."""
        # WebSocket settings
        self.host = os.getenv("TUI_HOST", self.host)
        self.port = int(os.getenv("TUI_PORT", str(self.port)))
        self.ws_path = os.getenv("TUI_WS_PATH", self.ws_path)
        
        # Connection settings
        self.timeout_seconds = int(os.getenv("TUI_TIMEOUT", str(self.timeout_seconds)))
        self.reconnect_attempts = int(os.getenv("TUI_RECONNECT_ATTEMPTS", str(self.reconnect_attempts)))
        
        # Audio settings
        self.sample_rate = int(os.getenv("TUI_SAMPLE_RATE", str(self.sample_rate)))
        self.audio_format = os.getenv("TUI_AUDIO_FORMAT", self.audio_format)
        
        # Default supported formats
        if self.supported_formats is None:
            self.supported_formats = ["raw/lpcm16", "g711/ulaw", "g711/alaw"]
        
        # Recording settings
        self.enable_audio_recording = os.getenv("TUI_ENABLE_RECORDING", "true").lower() == "true"
        self.recordings_dir = os.getenv("TUI_RECORDINGS_DIR", self.recordings_dir)
        
        # UI settings
        self.refresh_rate = int(os.getenv("TUI_REFRESH_RATE", str(self.refresh_rate)))
        self.theme = os.getenv("TUI_THEME", self.theme)
        
        # Message filtering
        self.show_audio_chunks = os.getenv("TUI_SHOW_AUDIO_CHUNKS", "false").lower() == "true"
        self.show_debug_messages = os.getenv("TUI_SHOW_DEBUG", "true").lower() == "true"
        
        # Create recordings directory if it doesn't exist
        Path(self.recordings_dir).mkdir(parents=True, exist_ok=True)
    
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
    
    def is_valid(self) -> bool:
        """Validate the configuration."""
        try:
            # Check required settings
            if not self.host or self.port <= 0:
                return False
            
            # Check audio settings
            if self.sample_rate <= 0 or self.audio_chunk_size <= 0:
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
            "sample_rate": self.sample_rate,
            "audio_format": self.audio_format,
            "recordings_dir": self.recordings_dir,
            "theme": self.theme,
        }


# Global configuration instance
config = TUIConfig() 