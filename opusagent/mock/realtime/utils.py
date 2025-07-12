"""
Utility functions and constants for the LocalRealtime module.

This module contains helper functions, constants, and utilities used
by the LocalRealtimeClient and its components.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional


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


def create_simple_wav_data(duration: float = 2.0, sample_rate: int = 16000) -> bytes:
    """
    Create simple WAV audio data with silence.
    
    Args:
        duration (float): Duration in seconds. Default: 2.0s
        sample_rate (int): Sample rate in Hz. Default: 16000Hz
    
    Returns:
        bytes: Raw WAV audio data
    """
    import struct
    
    # Calculate audio parameters
    num_samples = int(sample_rate * duration)
    data_size = num_samples * 2  # 16-bit samples
    
    # Create WAV file structure
    wav_data = bytearray()
    
    # RIFF header
    wav_data.extend(b'RIFF')
    wav_data.extend(struct.pack('<I', 36 + data_size))  # File size
    wav_data.extend(b'WAVE')
    
    # fmt chunk
    wav_data.extend(b'fmt ')
    wav_data.extend(struct.pack('<I', 16))  # Chunk size
    wav_data.extend(struct.pack('<H', 1))   # Audio format (PCM)
    wav_data.extend(struct.pack('<H', 1))   # Number of channels
    wav_data.extend(struct.pack('<I', sample_rate))  # Sample rate
    wav_data.extend(struct.pack('<I', sample_rate * 2))  # Byte rate
    wav_data.extend(struct.pack('<H', 2))   # Block align
    wav_data.extend(struct.pack('<H', 16))  # Bits per sample
    
    # data chunk
    wav_data.extend(b'data')
    wav_data.extend(struct.pack('<I', data_size))
    
    # Audio data (silence)
    wav_data.extend(b'\x00\x00' * num_samples)
    
    return bytes(wav_data)


def chunk_audio_data(audio_data: bytes, chunk_size: int = DEFAULT_AUDIO_CHUNK_SIZE) -> List[bytes]:
    """
    Split audio data into chunks of specified size.
    
    Args:
        audio_data (bytes): Raw audio data to chunk
        chunk_size (int): Size of each chunk in bytes
    
    Returns:
        List[bytes]: List of audio chunks
    """
    return [audio_data[i:i + chunk_size] for i in range(0, len(audio_data), chunk_size)]


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


def format_event_log(event_type: str, data: Dict[str, Any]) -> str:
    """
    Format an event for logging.
    
    Args:
        event_type (str): Type of event
        data (Dict[str, Any]): Event data
    
    Returns:
        str: Formatted log message
    """
    # Truncate large data for logging
    if len(str(data)) > 200:
        data_str = str(data)[:200] + "..."
    else:
        data_str = str(data)
    
    return f"Event[{event_type}]: {data_str}"


async def safe_send_event(websocket, event: Dict[str, Any], logger: Optional[logging.Logger] = None) -> bool:
    """
    Safely send an event to a WebSocket connection.
    
    Args:
        websocket: WebSocket connection
        event (Dict[str, Any]): Event to send
        logger (Optional[logging.Logger]): Logger for error reporting
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    if not websocket:
        if logger:
            logger.error("[MOCK REALTIME] No WebSocket connection available")
        return False
    
    try:
        await websocket.send(json.dumps(event))
        if logger:
            logger.debug(f"[MOCK REALTIME] Sent event: {event.get('type', 'unknown')}")
        return True
    except Exception as e:
        if logger:
            logger.error(f"[MOCK REALTIME] Error sending event: {e}")
        return False


def calculate_audio_duration(audio_data: bytes, sample_rate: int = 16000, channels: int = 1, bits_per_sample: int = 16) -> float:
    """
    Calculate the duration of audio data.
    
    Args:
        audio_data (bytes): Raw audio data
        sample_rate (int): Sample rate in Hz
        channels (int): Number of channels
        bits_per_sample (int): Bits per sample
    
    Returns:
        float: Duration in seconds
    """
    bytes_per_sample = bits_per_sample // 8
    total_samples = len(audio_data) // (channels * bytes_per_sample)
    return total_samples / sample_rate


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
    import time
    
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
    import uuid
    
    event = {
        "type": event_type,
        "response_id": response_id,
        "item_id": str(uuid.uuid4()),
        "output_index": 0,
        "content_index": 0,
    }
    event.update(kwargs)
    
    return event


async def retry_operation(operation, max_retries: int = 3, delay: float = 1.0, logger: Optional[logging.Logger] = None):
    """
    Retry an async operation with exponential backoff.
    
    Args:
        operation: Async function to retry
        max_retries (int): Maximum number of retries
        delay (float): Initial delay between retries
        logger (Optional[logging.Logger]): Logger for retry messages
    
    Returns:
        Result of the operation
    
    Raises:
        Exception: If all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                if logger:
                    logger.warning(f"[MOCK REALTIME] Operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
            else:
                if logger:
                    logger.error(f"[MOCK REALTIME] Operation failed after {max_retries + 1} attempts: {e}")
    
    if last_exception:
        raise last_exception
    else:
        raise Exception("Operation failed but no exception was captured") 