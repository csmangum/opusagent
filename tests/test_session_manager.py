"""Unit tests for the SessionManager class.

This module contains tests for the SessionManager class, which handles
OpenAI Realtime API session management and conversation initialization.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from opusagent.session_manager import SessionManager
from opusagent.models.openai_api import SessionConfig, SessionUpdateEvent

# Test constants
TEST_CONVERSATION_ID = "test-conversation-123"
TEST_VOICE = "verse"
TEST_MODEL = "gpt-4o-realtime-preview-2025-06-03"

@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection for testing."""
    mock = AsyncMock()
    return mock

@pytest.fixture
def test_session_config():
    """Create a test session configuration."""
    return SessionConfig(
        input_audio_format="pcm16",
        output_audio_format="pcm16",
        voice=TEST_VOICE,
        instructions="You are a test customer service agent.",
        modalities=["text", "audio"],
        temperature=0.8,
        model=TEST_MODEL,
        tools=[
            {
                "type": "function",
                "name": "get_balance",
                "description": "Get the user's account balance.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "type": "function",
                "name": "transfer_funds",
                "description": "Transfer funds to another account.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "number"},
                        "to_account": {"type": "string"},
                    },
                },
            },
            {
                "type": "function",
                "name": "call_intent",
                "description": "Get the user's intent.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "enum": ["card_replacement", "account_inquiry", "other"],
                        },
                    },
                    "required": ["intent"],
                },
            },
        ],
        input_audio_noise_reduction={"type": "near_field"},
        input_audio_transcription={"model": "whisper-1"},
        max_response_output_tokens=4096,
        tool_choice="auto",
    )

@pytest.fixture
def session_manager(mock_websocket, test_session_config):
    """Create a SessionManager instance with a mock WebSocket and session config."""
    return SessionManager(mock_websocket, test_session_config)

@pytest.mark.asyncio
async def test_initialize_session(session_manager, mock_websocket):
    """Test session initialization."""
    # Call the method
    await session_manager.initialize_session()

    # Verify the session was initialized
    assert session_manager.session_initialized is True

    # Verify the WebSocket send was called with correct data
    mock_websocket.send.assert_called_once()
    sent_data = json.loads(mock_websocket.send.call_args[0][0])
    
    # Verify the session update event structure
    assert sent_data["type"] == "session.update"
    assert "session" in sent_data
    
    # Verify session configuration
    session_config = sent_data["session"]
    assert session_config["input_audio_format"] == "pcm16"
    assert session_config["output_audio_format"] == "pcm16"
    assert session_config["voice"] == TEST_VOICE
    assert session_config["modalities"] == ["text", "audio"]
    assert session_config["temperature"] == 0.8
    assert session_config["model"] == TEST_MODEL
    assert "tools" in session_config
    assert len(session_config["tools"]) > 0

@pytest.mark.asyncio
async def test_send_initial_conversation_item(session_manager, mock_websocket):
    """Test sending initial conversation item."""
    # Call the method
    await session_manager.send_initial_conversation_item()

    # Verify WebSocket send was called twice (conversation item and response create)
    assert mock_websocket.send.call_count == 2

    # Get the first call (conversation item)
    first_call = json.loads(mock_websocket.send.call_args_list[0][0][0])
    assert first_call["type"] == "conversation.item.create"
    assert first_call["item"]["type"] == "message"
    assert first_call["item"]["role"] == "user"
    assert len(first_call["item"]["content"]) == 1
    assert first_call["item"]["content"][0]["type"] == "input_text"
    assert "customer service agent" in first_call["item"]["content"][0]["text"]
    assert "How can I help you today" in first_call["item"]["content"][0]["text"]
    assert "call_intent function" in first_call["item"]["content"][0]["text"]

    # Get the second call (response create)
    second_call = json.loads(mock_websocket.send.call_args_list[1][0][0])
    assert second_call["type"] == "response.create"
    assert second_call["response"]["modalities"] == ["text", "audio"]
    assert second_call["response"]["output_audio_format"] == "pcm16"
    assert second_call["response"]["temperature"] == 0.6
    assert second_call["response"]["max_output_tokens"] == 4096
    assert second_call["response"]["voice"] == TEST_VOICE

@pytest.mark.asyncio
async def test_create_response(session_manager, mock_websocket):
    """Test creating a new response."""
    # Call the method
    await session_manager.create_response()

    # Verify WebSocket send was called once
    mock_websocket.send.assert_called_once()

    # Verify the response create event structure
    sent_data = json.loads(mock_websocket.send.call_args[0][0])
    assert sent_data["type"] == "response.create"
    assert sent_data["response"]["modalities"] == ["text", "audio"]
    assert sent_data["response"]["output_audio_format"] == "pcm16"
    assert sent_data["response"]["temperature"] == 0.6
    assert sent_data["response"]["max_output_tokens"] == 4096
    assert sent_data["response"]["voice"] == TEST_VOICE

@pytest.mark.asyncio
async def test_initialize_session_error_handling(session_manager, mock_websocket):
    """Test error handling during session initialization."""
    # Make the WebSocket send raise an exception
    mock_websocket.send.side_effect = Exception("WebSocket error")

    # Verify the exception is propagated
    with pytest.raises(Exception) as exc_info:
        await session_manager.initialize_session()
    assert str(exc_info.value) == "WebSocket error"

@pytest.mark.asyncio
async def test_send_initial_conversation_item_error_handling(session_manager, mock_websocket):
    """Test error handling during initial conversation item sending."""
    # Make the WebSocket send raise an exception
    mock_websocket.send.side_effect = Exception("WebSocket error")

    # Verify the exception is propagated
    with pytest.raises(Exception) as exc_info:
        await session_manager.send_initial_conversation_item()
    assert str(exc_info.value) == "WebSocket error"

@pytest.mark.asyncio
async def test_create_response_error_handling(session_manager, mock_websocket):
    """Test error handling during response creation."""
    # Make the WebSocket send raise an exception
    mock_websocket.send.side_effect = Exception("WebSocket error")

    # Verify the exception is propagated
    with pytest.raises(Exception) as exc_info:
        await session_manager.create_response()
    assert str(exc_info.value) == "WebSocket error"

@pytest.mark.asyncio
async def test_session_manager_initialization():
    """Test SessionManager initialization with different WebSocket instances."""
    # Create a mock WebSocket
    mock_websocket = AsyncMock()
    
    # Create a test session config
    test_config = SessionConfig(
        input_audio_format="pcm16",
        output_audio_format="pcm16",
        voice=TEST_VOICE,
        instructions="Test instructions",
        modalities=["text", "audio"],
        temperature=0.8,
        model=TEST_MODEL,
    )
    
    # Create SessionManager instance
    manager = SessionManager(mock_websocket, test_config)
    
    # Verify initial state
    assert manager.realtime_websocket == mock_websocket
    assert manager.session_config == test_config
    assert manager.session_initialized is False
    assert manager.conversation_id is None

@pytest.mark.asyncio
async def test_session_manager_tools_configuration(session_manager, mock_websocket):
    """Test that all required tools are configured in the session."""
    # Call the method
    await session_manager.initialize_session()

    # Get the sent session configuration
    sent_data = json.loads(mock_websocket.send.call_args[0][0])
    tools = sent_data["session"]["tools"]

    # Verify essential tools are present (based on the test session config)
    tool_names = {tool["name"] for tool in tools}
    required_tools = {
        "get_balance",
        "transfer_funds",
        "call_intent",
    }
    assert required_tools.issubset(tool_names)

    # Verify tool configurations
    for tool in tools:
        assert "type" in tool
        assert "name" in tool
        assert "description" in tool
        assert "parameters" in tool
        assert tool["type"] == "function" 