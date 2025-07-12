"""
Utility functions and constants for the LocalRealtime module.

This module contains helper functions, constants, and utilities used
by the LocalRealtimeClient and its components. Mock-specific utilities only.
"""

import json
import logging
import time
import uuid
from typing import Any, Dict, Optional

from opusagent.utils.audio_utils import AudioUtils
from opusagent.utils.websocket_utils import WebSocketUtils
from opusagent.utils.retry_utils import RetryUtils


# Constants
DEFAULT_AUDIO_CHUNK_SIZE = 3200  # 200ms at 16kHz 16-bit
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_BITS_PER_SAMPLE = 16

# Event types for easy reference
EVENT_TYPES = {
    "SESSION_CREATED": "session.created",
    "SESSION_UPDATED": "session.updated",
    "INPUT_AUDIO_BUFFER_APPEND": "input_audio_buffer.append",
    "INPUT_AUDIO_BUFFER_COMMIT": "input_audio_buffer.commit",
    "INPUT_AUDIO_BUFFER_CLEAR": "input_audio_buffer.clear",
    "RESPONSE_CREATE": "response.create",
    "RESPONSE_CANCEL": "response.cancel",
    "RESPONSE_CREATED": "response.created",
    "RESPONSE_CANCELLED": "response.cancelled",
    "RESPONSE_DONE": "response.done",
    "RESPONSE_TEXT_DELTA": "response.text.delta",
    "RESPONSE_TEXT_DONE": "response.text.done",
    "RESPONSE_AUDIO_DELTA": "response.audio.delta",
    "RESPONSE_AUDIO_DONE": "response.audio.done",
    "RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA": "response.function_call_arguments.delta",
    "RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE": "response.function_call_arguments.done",
    "ERROR": "error"
}


def validate_response_config(config: Dict[str, Any]) -> bool:
    """
    Validate a response configuration dictionary.
    
    Args:
        config (Dict[str, Any]): Configuration to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = ["text"]
    optional_fields = ["audio_file", "audio_data", "delay_seconds", "audio_chunk_delay", "function_call"]
    
    # Check required fields
    for field in required_fields:
        if field not in config:
            return False
    
    # Check field types
    if not isinstance(config["text"], str):
        return False
    
    if "delay_seconds" in config and not isinstance(config["delay_seconds"], (int, float)):
        return False
    
    if "audio_chunk_delay" in config and not isinstance(config["audio_chunk_delay"], (int, float)):
        return False
    
    if "function_call" in config and not isinstance(config["function_call"], dict):
        return False
    
    return True


def create_default_response_config() -> Dict[str, Any]:
    """
    Create a default response configuration.
    
    Returns:
        Dict[str, Any]: Default response configuration
    """
    return {
        "text": "This is a mock text response from the OpenAI Realtime API.",
        "delay_seconds": 0.05,
        "audio_chunk_delay": 0.2
    }


def create_error_event(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create an error event.
    
    Args:
        code (str): Error code
        message (str): Error message
        details (Optional[Dict[str, Any]]): Additional error details
    
    Returns:
        Dict[str, Any]: Error event
    """
    event: Dict[str, Any] = {
        "type": EVENT_TYPES["ERROR"],
        "code": code,
        "message": message
    }
    
    if details:
        event["details"] = details
    
    return event


def create_session_event(session_id: str, session_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a session.created event.
    
    Args:
        session_id (str): Session ID
        session_config (Dict[str, Any]): Session configuration
    
    Returns:
        Dict[str, Any]: Session event
    """
    session_data = {
        "id": session_id,
        "created_at": int(time.time() * 1000),
    }
    session_data.update(session_config)
    
    return {
        "type": EVENT_TYPES["SESSION_CREATED"],
        "session": session_data
    }


def create_response_event(response_id: str, event_type: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Create a response event.
    
    Args:
        response_id (str): Response ID
        event_type (str): Type of response event
        **kwargs: Additional event data
    
    Returns:
        Dict[str, Any]: Response event
    """
    event = {
        "type": event_type,
        "response_id": response_id,
        "item_id": str(uuid.uuid4()),
        "output_index": 0,
        "content_index": 0,
    }
    event.update(kwargs)
    
    return event


# Re-export shared utilities for convenience
create_simple_wav_data = AudioUtils.create_simple_wav_data
chunk_audio_data = AudioUtils.chunk_audio_data
calculate_audio_duration = AudioUtils.calculate_audio_duration
safe_send_event = WebSocketUtils.safe_send_event
format_event_log = WebSocketUtils.format_event_log
retry_operation = RetryUtils.retry_operation 