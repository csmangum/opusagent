"""
Data models for the MockRealtime module.

This module contains Pydantic models and data structures used by the
LocalRealtimeClient for configuration and response handling.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class MockResponseConfig(BaseModel):
    """
    Configuration for a mock response in the LocalRealtimeClient.
    
    This class defines how a specific response should be generated, including
    text content, audio files, timing, and function calls. It allows for
    highly customizable mock responses that can simulate various real-world
    scenarios.
    
    Attributes:
        text (str): The text content to be streamed as the response.
                   Defaults to a generic mock response message.
        audio_file (Optional[str]): Path to an audio file to be streamed.
                                   Supports WAV, MP3, and other audio formats.
                                   If None, silence will be generated.
        audio_data (Optional[bytes]): Raw audio data as bytes. If provided,
                                     this takes precedence over audio_file.
                                     Useful for dynamic audio generation.
        delay_seconds (float): Delay between text characters during streaming.
                              Simulates realistic typing speed. Default: 0.05s
        audio_chunk_delay (float): Delay between audio chunks during streaming.
                                  Controls audio streaming speed. Default: 0.2s
        function_call (Optional[Dict[str, Any]]): Function call to simulate.
                                                  Should contain 'name' and 'arguments'
                                                  keys for the function call.
    
    Example:
        ```python
        config = MockResponseConfig(
            text="Hello! How can I help you today?",
            audio_file="audio/greeting.wav",
            delay_seconds=0.03,
            audio_chunk_delay=0.15,
            function_call={
                "name": "get_user_info",
                "arguments": {"user_id": "12345"}
            }
        )
        ```
    """
    
    text: str = Field(
        default="This is a mock text response from the OpenAI Realtime API.",
        description="Text content to be streamed as the response"
    )
    audio_file: Optional[str] = Field(
        default=None,
        description="Path to audio file (WAV, MP3, etc.) to be streamed"
    )
    audio_data: Optional[bytes] = Field(
        default=None,
        description="Raw audio data as bytes (takes precedence over audio_file)"
    )
    delay_seconds: float = Field(
        default=0.05,
        description="Delay between text characters during streaming",
        ge=0.0
    )
    audio_chunk_delay: float = Field(
        default=0.2,
        description="Delay between audio chunks during streaming",
        ge=0.0
    )
    function_call: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Function call to simulate with 'name' and 'arguments' keys"
    )


class MockSessionState(BaseModel):
    """
    Session state for the LocalRealtimeClient.
    
    This class tracks the current state of a mock session, including
    connection status, active responses, and audio buffers.
    """
    
    session_id: str
    conversation_id: str
    connected: bool = False
    active_response_id: Optional[str] = None
    speech_detected: bool = False
    
    # Audio buffer state
    audio_buffer: list = Field(default_factory=list)
    response_audio: list = Field(default_factory=list)
    
    # Response state
    response_text: str = ""
    
    class Config:
        arbitrary_types_allowed = True 