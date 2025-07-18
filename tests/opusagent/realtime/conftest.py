"""
Configuration and fixtures for opusagent.mock.realtime tests.
"""

import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_logger():
    """Provide a mock logger for testing."""
    return Mock()


@pytest.fixture
def sample_session_config():
    """Provide a sample session configuration for testing."""
    from opusagent.models.openai_api import SessionConfig
    
    return SessionConfig(
        model="gpt-4o-realtime-preview-2025-06-03",
        modalities=["text", "audio"],
        voice="alloy"
    )


@pytest.fixture
def sample_response_config():
    """Provide a sample response configuration for testing."""
    from opusagent.local.realtime.models import LocalResponseConfig
    
    return LocalResponseConfig(
        text="Hello! How can I help you?",
        audio_file="test_audio.wav",
        delay_seconds=0.05,
        audio_chunk_delay=0.2
    )


@pytest.fixture
def sample_selection_criteria():
    """Provide a sample selection criteria for testing."""
    from opusagent.local.realtime.models import ResponseSelectionCriteria
    
    return ResponseSelectionCriteria(
        required_keywords=["hello", "hi"],
        required_intents=["greeting"],
        priority=15,
        min_turn_count=1,
        max_turn_count=5
    )


@pytest.fixture
def sample_conversation_context():
    """Provide a sample conversation context for testing."""
    from opusagent.local.realtime.models import ConversationContext
    
    return ConversationContext(
        session_id="test_session_123",
        conversation_id="test_conversation_456",
        last_user_input="Hello there!",
        detected_intents=["greeting"],
        turn_count=2
    )


@pytest.fixture
def mock_websocket_connection():
    """Provide a mock WebSocket connection for testing."""
    return Mock()


@pytest.fixture
def mock_audio_manager():
    """Provide a mock audio manager for testing."""
    audio_manager = Mock()
    audio_manager.load_audio_file = Mock()
    audio_manager._generate_silence = Mock(return_value=b"\x00" * 32000)
    return audio_manager


@pytest.fixture
def sample_response_create_options():
    """Provide sample response creation options for testing."""
    from opusagent.models.openai_api import ResponseCreateOptions
    
    return ResponseCreateOptions(
        modalities=["text", "audio"],
        tools=[{"name": "test_function"}],
        tool_choice="auto"
    ) 