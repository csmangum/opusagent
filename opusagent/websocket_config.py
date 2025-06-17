"""
WebSocket Manager Configuration

This module provides configuration settings for the WebSocket manager,
allowing customization via environment variables.
"""

import os
from typing import Optional


class WebSocketConfig:
    """Configuration settings for the WebSocket manager."""
    
    # Connection pool settings
    MAX_CONNECTIONS = int(os.getenv("WEBSOCKET_MAX_CONNECTIONS", "10"))
    MAX_CONNECTION_AGE = float(os.getenv("WEBSOCKET_MAX_CONNECTION_AGE", "3600"))  # 1 hour
    MAX_IDLE_TIME = float(os.getenv("WEBSOCKET_MAX_IDLE_TIME", "300"))  # 5 minutes
    HEALTH_CHECK_INTERVAL = float(os.getenv("WEBSOCKET_HEALTH_CHECK_INTERVAL", "30"))  # 30 seconds
    
    # Connection settings per connection
    MAX_SESSIONS_PER_CONNECTION = int(os.getenv("WEBSOCKET_MAX_SESSIONS_PER_CONNECTION", "10"))
    
    # WebSocket connection parameters
    PING_INTERVAL = int(os.getenv("WEBSOCKET_PING_INTERVAL", "20"))
    PING_TIMEOUT = int(os.getenv("WEBSOCKET_PING_TIMEOUT", "30"))
    CLOSE_TIMEOUT = int(os.getenv("WEBSOCKET_CLOSE_TIMEOUT", "10"))
    
    # OpenAI API settings
    OPENAI_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview-2024-12-17")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    @classmethod
    def get_websocket_url(cls) -> str:
        """Get the OpenAI Realtime API WebSocket URL."""
        return f"wss://api.openai.com/v1/realtime?model={cls.OPENAI_MODEL}"
    
    @classmethod
    def get_headers(cls) -> dict:
        """Get the headers for OpenAI API authentication."""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        return {
            "Authorization": f"Bearer {cls.OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1",
        }
    
    @classmethod
    def validate(cls) -> None:
        """Validate the configuration settings."""
        errors = []
        
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY environment variable is required")
        
        if cls.MAX_CONNECTIONS <= 0:
            errors.append("WEBSOCKET_MAX_CONNECTIONS must be greater than 0")
        
        if cls.MAX_CONNECTION_AGE <= 0:
            errors.append("WEBSOCKET_MAX_CONNECTION_AGE must be greater than 0")
        
        if cls.MAX_IDLE_TIME <= 0:
            errors.append("WEBSOCKET_MAX_IDLE_TIME must be greater than 0")
        
        if cls.HEALTH_CHECK_INTERVAL <= 0:
            errors.append("WEBSOCKET_HEALTH_CHECK_INTERVAL must be greater than 0")
        
        if cls.MAX_SESSIONS_PER_CONNECTION <= 0:
            errors.append("WEBSOCKET_MAX_SESSIONS_PER_CONNECTION must be greater than 0")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    
    @classmethod
    def to_dict(cls) -> dict:
        """Get all configuration settings as a dictionary."""
        return {
            "max_connections": cls.MAX_CONNECTIONS,
            "max_connection_age": cls.MAX_CONNECTION_AGE,
            "max_idle_time": cls.MAX_IDLE_TIME,
            "health_check_interval": cls.HEALTH_CHECK_INTERVAL,
            "max_sessions_per_connection": cls.MAX_SESSIONS_PER_CONNECTION,
            "ping_interval": cls.PING_INTERVAL,
            "ping_timeout": cls.PING_TIMEOUT,
            "close_timeout": cls.CLOSE_TIMEOUT,
            "openai_model": cls.OPENAI_MODEL,
            "websocket_url": cls.get_websocket_url(),
        } 