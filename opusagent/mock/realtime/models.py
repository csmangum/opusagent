"""
Data models for the LocalRealtime module.

This module provides comprehensive data models and structures for the LocalRealtimeClient,
which simulates the OpenAI Realtime API. It defines the configuration, state management,
and response selection logic using Pydantic for validation and type safety.

Key Components:
- ConversationContext: Tracks conversation state and provides context for intelligent response selection
- ResponseSelectionCriteria: Defines conditions for selecting responses based on conversation context
- LocalResponseConfig: Configuration for mock responses with text, audio, timing, and function calls
- MockSessionState: Session state tracking including connection status and audio buffers

Core Features:
- Context-Aware Response Selection: Intelligent response selection based on conversation history
- Flexible Response Configuration: Support for text, audio, function calls, and timing control
- Session State Management: Comprehensive tracking of session and conversation state
- Validation and Type Safety: Pydantic models ensure data integrity and provide clear interfaces

Data Models:
- ConversationContext: Tracks conversation history, intents, modalities, and function call context
- ResponseSelectionCriteria: Keyword matching, intent detection, turn count conditions, and priority
- LocalResponseConfig: Text content, audio files/data, timing delays, function calls, and selection criteria
- MockSessionState: Session IDs, connection status, audio buffers, and conversation context

The models are designed to support sophisticated mock conversations with realistic
response selection, state management, and configuration options that closely mirror
the behavior of the actual OpenAI Realtime API.

Usage:
    context = ConversationContext(session_id="123", conversation_id="456")
    criteria = ResponseSelectionCriteria(required_keywords=["hello"], priority=10)
    config = LocalResponseConfig(text="Hello!", audio_file="greeting.wav", delay_seconds=0.05)
    state = MockSessionState(session_id="123", conversation_id="456", connected=True)
"""

from typing import Any, Dict, List, Optional, Set, Union
from pydantic import BaseModel, Field


class ConversationContext(BaseModel):
    """
    Context information for conversation-aware response selection.
    
    This class tracks conversation state and provides context for
    intelligent response selection.
    """
    
    # Conversation history
    conversation_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of conversation turns with user input and responses"
    )
    
    # Current session state
    session_id: str = Field(description="Current session ID")
    conversation_id: str = Field(description="Current conversation ID")
    
    # User input analysis
    last_user_input: Optional[str] = Field(
        default=None,
        description="Most recent user input text"
    )
    
    # Conversation metadata
    turn_count: int = Field(
        default=0,
        description="Number of conversation turns"
    )
    
    # Detected intents and entities
    detected_intents: List[str] = Field(
        default_factory=list,
        description="List of detected conversation intents"
    )
    
    # Modality preferences
    preferred_modalities: List[str] = Field(
        default_factory=lambda: ["text", "audio"],
        description="User's preferred response modalities"
    )
    
    # Function call context
    function_call_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Context for function calls"
    )

    class Config:
        # Allow field assignment for mutable updates
        validate_assignment = False


class ResponseSelectionCriteria(BaseModel):
    """
    Criteria for selecting responses based on conversation context.
    
    This class defines the conditions that must be met for a response
    configuration to be selected.
    """
    
    # Keyword matching
    required_keywords: Optional[List[str]] = Field(
        default=None,
        description="Keywords that must be present in user input"
    )
    
    excluded_keywords: Optional[List[str]] = Field(
        default=None,
        description="Keywords that must NOT be present in user input"
    )
    
    # Intent matching
    required_intents: Optional[List[str]] = Field(
        default=None,
        description="Intents that must be detected"
    )
    
    # Turn count conditions
    min_turn_count: Optional[int] = Field(
        default=None,
        description="Minimum conversation turn count"
    )
    
    max_turn_count: Optional[int] = Field(
        default=None,
        description="Maximum conversation turn count"
    )
    
    # Modality preferences
    required_modalities: Optional[List[str]] = Field(
        default=None,
        description="Required response modalities"
    )
    
    # Function call conditions
    requires_function_call: Optional[bool] = Field(
        default=None,
        description="Whether function call is required"
    )
    
    # Priority and weight
    priority: int = Field(
        default=0,
        description="Selection priority (higher = more preferred)"
    )
    
    # Context patterns
    context_patterns: Optional[List[str]] = Field(
        default=None,
        description="Regex patterns to match in conversation context"
    )


class LocalResponseConfig(BaseModel):
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
        selection_criteria (Optional[ResponseSelectionCriteria]): Criteria for
                                                                  selecting this response
                                                                  based on conversation context.
    
    Example:
        ```python
        config = LocalResponseConfig(
            text="Hello! How can I help you today?",
            audio_file="audio/greeting.wav",
            delay_seconds=0.03,
            audio_chunk_delay=0.15,
            function_call={
                "name": "get_user_info",
                "arguments": {"user_id": "12345"}
            },
            selection_criteria=ResponseSelectionCriteria(
                required_keywords=["hello", "hi", "greeting"],
                max_turn_count=1,
                priority=10
            )
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
    selection_criteria: Optional[ResponseSelectionCriteria] = Field(
        default=None,
        description="Criteria for selecting this response based on conversation context"
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
    
    # Conversation context
    conversation_context: Optional[ConversationContext] = Field(
        default=None,
        description="Current conversation context for response selection"
    )
    
    class Config:
        arbitrary_types_allowed = True 