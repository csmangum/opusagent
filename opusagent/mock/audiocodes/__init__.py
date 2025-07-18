"""
AudioCodes Mock Client Module

This module provides a comprehensive mock implementation of the AudioCodes VAIC client
that connects to the bridge server. It simulates the behavior of a real AudioCodes
device for testing and development purposes.

The module is designed with a modular architecture that separates concerns into
specialized components:

Core Components:
- MockAudioCodesClient: Main client class that orchestrates all components
- SessionManager: Handles session lifecycle, state tracking, and WebSocket communication
- MessageHandler: Processes incoming WebSocket messages and manages event handlers
- AudioManager: Manages audio file operations, caching, and format conversion
- ConversationManager: Handles multi-turn conversations and audio collection
- VADManager: Provides Voice Activity Detection for realistic speech simulation
- LiveAudioManager: Enables real-time microphone input and processing

Data Models:
- SessionConfig: Configuration settings for AudioCodes sessions
- SessionState: Current session state and status tracking
- StreamState: Audio stream state management
- ConversationState: Multi-turn conversation state and history
- AudioChunk: Audio data structure for streaming
- MessageEvent: WebSocket message event representation

Key Features:
- Real-time WebSocket communication with bridge server
- Audio file handling with automatic format conversion and caching
- Multi-turn conversation testing with detailed result analysis
- Voice Activity Detection (VAD) with configurable thresholds
- Live microphone input for realistic testing scenarios
- Comprehensive session management (initiate, resume, validate, end)
- DTMF event simulation and custom activity support
- Detailed logging and error handling throughout

Architecture Overview:
The mock client follows a layered architecture where each component has a specific
responsibility:

1. MockAudioCodesClient (Orchestrator Layer)
   - Coordinates all components and provides high-level interface
   - Manages WebSocket connection and message routing
   - Handles client lifecycle and resource management

2. SessionManager (Session Layer)
   - Manages session state and lifecycle operations
   - Prepares WebSocket messages for session operations
   - Tracks conversation state and session metadata

3. MessageHandler (Communication Layer)
   - Processes incoming WebSocket messages
   - Routes messages to appropriate handlers
   - Maintains message history and event registration

4. AudioManager (Audio Processing Layer)
   - Handles audio file loading and format conversion
   - Manages audio chunking and caching
   - Provides audio utilities and silence generation

5. ConversationManager (Conversation Layer)
   - Orchestrates multi-turn conversations
   - Collects and manages audio responses
   - Provides conversation analysis and result tracking

6. VADManager (Speech Detection Layer)
   - Integrates with VAD system for speech detection
   - Simulates realistic speech events
   - Manages speech state and event emission

Usage Examples:

Basic Session Management:
    from opusagent.mock.audiocodes import MockAudioCodesClient
    
    async with MockAudioCodesClient("ws://localhost:8080") as client:
        # Initiate session
        success = await client.initiate_session()
        if success:
            # Send user audio
            await client.send_user_audio("audio/user_input.wav")
            # Wait for AI response
            response = await client.wait_for_llm_response()
            # End session
            await client.end_session("Test completed")

Multi-turn Conversation Testing:
    audio_files = ["audio/turn1.wav", "audio/turn2.wav", "audio/turn3.wav"]
    async with MockAudioCodesClient("ws://localhost:8080") as client:
        result = await client.multi_turn_conversation(audio_files)
        print(f"Success rate: {result.success_rate:.1f}%")
        client.save_collected_audio("output/")

Live Audio Capture:
    async with MockAudioCodesClient("ws://localhost:8080") as client:
        # Start live audio capture
        client.start_live_audio_capture()
        # Enable VAD for speech detection
        client.enable_vad({"threshold": 0.6})
        # ... perform testing ...
        client.stop_live_audio_capture()

Advanced Configuration:
    client = MockAudioCodesClient(
        bridge_url="ws://localhost:8080",
        bot_name="MyTestBot",
        caller="+15551234567"
    )
    
    # Configure VAD with custom parameters
    client.enable_vad({
        "threshold": 0.5,
        "silence_threshold": 0.3,
        "min_speech_duration_ms": 500,
        "min_silence_duration_ms": 300
    })
    
    # Configure session parameters
    client.configure_session({
        "media_format": "raw/lpcm16",
        "expect_audio_messages": True,
        "enable_speech_hypothesis": False
    })

Error Handling and Recovery:
    try:
        async with MockAudioCodesClient("ws://localhost:8080") as client:
            await client.initiate_session()
            # ... perform operations ...
    except ConnectionError as e:
        print(f"Connection failed: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

Performance Optimization:
    # Enable audio caching for repeated file access
    client.audio_manager.enable_caching()
    
    # Configure chunk sizes for optimal streaming
    client.configure_audio_chunking(chunk_size=32000)
    
    # Monitor performance metrics
    cache_info = client.audio_manager.get_cache_info()
    print(f"Cache hit rate: {cache_info['hit_rate']:.1f}%")

The module provides comprehensive error handling, detailed logging with structured
prefixes ([CLIENT], [SESSION], [AUDIO], etc.), and performance optimizations
including audio caching and efficient chunking for streaming scenarios.

Integration with Testing Frameworks:
The mock client is designed to integrate seamlessly with testing frameworks:

- pytest: Use async fixtures for session management
- unittest: Extend MockAudioCodesClient for custom test cases
- Custom frameworks: Register event handlers for specific test scenarios

Logging and Debugging:
The module uses structured logging with component prefixes for easy debugging:

- [CLIENT]: Main client operations and lifecycle
- [SESSION]: Session management and state changes
- [MESSAGE]: WebSocket message processing
- [AUDIO]: Audio file operations and streaming
- [VAD]: Voice activity detection events
- [CONVERSATION]: Multi-turn conversation management
"""

from .client import MockAudioCodesClient
from .audio_manager import AudioManager
from .session_manager import SessionManager
from .message_handler import MessageHandler
from .conversation_manager import ConversationManager
from .models import (
    SessionState,
    ConversationState,
    AudioChunk,
    MessageEvent,
    SessionConfig
)

__all__ = [
    "MockAudioCodesClient",
    "AudioManager", 
    "SessionManager",
    "MessageHandler",
    "ConversationManager",
    "SessionState",
    "ConversationState", 
    "AudioChunk",
    "MessageEvent",
    "SessionConfig"
]

__version__ = "1.0.0"
