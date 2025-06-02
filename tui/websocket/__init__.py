"""
WebSocket client and message handling for the Interactive TUI Validator.

This package provides WebSocket connection management and message processing
for communicating with the TelephonyRealtimeBridge.
"""

from .client import WebSocketClient
from .message_handler import MessageHandler

__all__ = [
    "WebSocketClient",
    "MessageHandler",
] 