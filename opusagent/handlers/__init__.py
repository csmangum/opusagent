"""
OpenAI Realtime API Handlers Module

This module contains all the core components for integrating with OpenAI's Realtime API,
including audio streaming, event routing, function handling, session management,
and WebSocket connection management.

Components:
- AudioStreamHandler: Manages bidirectional audio streaming
- EventRouter: Routes events between telephony and OpenAI Realtime API
- FunctionHandler: Handles function calls and execution
- RealtimeHandler: Main orchestrator for realtime communication
- SessionManager: Manages OpenAI Realtime API sessions
- TranscriptManager: Handles real-time transcript processing
- WebSocketManager: Manages WebSocket connections and pooling
"""

from .audio_stream_handler import AudioStreamHandler
from .event_router import EventRouter
from .function_handler import FunctionHandler
from .realtime_handler import RealtimeHandler
from .session_manager import SessionManager
from .transcript_manager import TranscriptManager
from .websocket_manager import (
    WebSocketManager,
    create_websocket_manager,
    create_mock_websocket_manager,
    get_websocket_manager,
)

__all__ = [
    "AudioStreamHandler",
    "EventRouter", 
    "FunctionHandler",
    "RealtimeHandler",
    "SessionManager",
    "TranscriptManager",
    "WebSocketManager",
    "create_websocket_manager",
    "create_mock_websocket_manager", 
    "get_websocket_manager",
] 