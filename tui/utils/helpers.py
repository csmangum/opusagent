"""
Helper utility functions for the Interactive TUI Validator.

This module provides common utility functions for formatting,
data processing, and other shared operations.
"""

import time
from datetime import datetime
from typing import Any, Dict, Optional


def format_timestamp(timestamp: Optional[float] = None, format_str: str = "%H:%M:%S.%f") -> str:
    """
    Format a timestamp for display.
    
    Args:
        timestamp: Unix timestamp (defaults to current time)
        format_str: Format string for datetime formatting
        
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = time.time()
    
    dt = datetime.fromtimestamp(timestamp)
    formatted = dt.strftime(format_str)
    
    # Truncate microseconds to 3 digits (milliseconds)
    if ".%f" in format_str:
        formatted = formatted[:-3]
    
    return formatted


def format_latency(latency_ms: float) -> str:
    """
    Format latency for display.
    
    Args:
        latency_ms: Latency in milliseconds
        
    Returns:
        Formatted latency string with appropriate unit
    """
    if latency_ms < 1:
        return f"{latency_ms * 1000:.0f}μs"
    elif latency_ms < 1000:
        return f"{latency_ms:.0f}ms"
    else:
        return f"{latency_ms / 1000:.1f}s"


def format_bytes(num_bytes: int) -> str:
    """
    Format byte count for display.
    
    Args:
        num_bytes: Number of bytes
        
    Returns:
        Formatted byte string with appropriate unit
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if num_bytes < 1024.0:
            if unit == 'B':
                return f"{num_bytes:.0f} {unit}"
            else:
                return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def format_duration(seconds: float) -> str:
    """
    Format duration for display.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string (e.g., "1m 30s", "45s")
    """
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.
    
    Args:
        text: String to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def sanitize_message_for_display(message: Dict[str, Any], max_length: int = 100) -> str:
    """
    Sanitize and format a message dictionary for safe display.
    
    Args:
        message: Message dictionary
        max_length: Maximum length for the formatted message
        
    Returns:
        Sanitized message string
    """
    try:
        # Remove sensitive or large data fields
        display_msg = message.copy()
        
        # Remove or truncate large fields
        if "audioChunk" in display_msg:
            chunk_size = len(display_msg["audioChunk"])
            display_msg["audioChunk"] = f"<{chunk_size} bytes>"
        
        # Format for display
        if "type" in display_msg:
            msg_type = display_msg["type"]
            if "conversationId" in display_msg:
                conv_id = display_msg["conversationId"][:8] + "..."
                return f"{msg_type} (conv: {conv_id})"
            else:
                return msg_type
        
        # Fallback to string representation
        msg_str = str(display_msg)
        return truncate_string(msg_str, max_length)
        
    except Exception:
        return truncate_string(str(message), max_length)


def get_message_icon(message_type: str) -> str:
    """
    Get an icon for a message type.
    
    Args:
        message_type: Type of the message
        
    Returns:
        Icon string for the message type
    """
    icons = {
        # Session events
        "session.initiate": "🚀",
        "session.accepted": "✅",
        "session.end": "🛑",
        
        # Audio stream events
        "userStream.start": "🎤",
        "userStream.started": "▶️",
        "userStream.chunk": "📊",
        "userStream.stop": "⏹️",
        "userStream.stopped": "⏸️",
        
        # Bot response events
        "playStream.start": "🔊",
        "playStream.chunk": "🎵",
        "playStream.stop": "🔇",
        
        # Error events
        "error": "❌",
        "warning": "⚠️",
        
        # Status events
        "connected": "🔗",
        "disconnected": "💔",
        "reconnecting": "🔄",
    }
    
    return icons.get(message_type, "📄")


def get_status_color(status: str) -> str:
    """
    Get a color for a status.
    
    Args:
        status: Status string
        
    Returns:
        Color name for the status
    """
    status_colors = {
        "connected": "green",
        "connecting": "yellow", 
        "disconnected": "red",
        "reconnecting": "orange",
        "error": "red",
        "success": "green",
        "warning": "yellow",
        "info": "blue",
        "active": "green",
        "inactive": "grey",
        "playing": "cyan",
        "recording": "magenta",
        "stopped": "grey",
    }
    
    return status_colors.get(status.lower(), "white")


def validate_conversation_id(conv_id: str) -> bool:
    """
    Validate a conversation ID format.
    
    Args:
        conv_id: Conversation ID to validate
        
    Returns:
        True if valid format
    """
    if not conv_id or not isinstance(conv_id, str):
        return False
    
    # Basic validation - should be non-empty string
    return len(conv_id.strip()) > 0


def create_session_summary(session_data: Dict[str, Any]) -> str:
    """
    Create a summary string for a session.
    
    Args:
        session_data: Session information dictionary
        
    Returns:
        Formatted session summary
    """
    try:
        summary_parts = []
        
        if "conversationId" in session_data:
            conv_id = session_data["conversationId"][:8] + "..."
            summary_parts.append(f"Conv: {conv_id}")
        
        if "mediaFormat" in session_data:
            summary_parts.append(f"Format: {session_data['mediaFormat']}")
        
        if "duration" in session_data:
            duration = format_duration(session_data["duration"])
            summary_parts.append(f"Duration: {duration}")
        
        return " | ".join(summary_parts)
        
    except Exception:
        return "Session summary unavailable" 