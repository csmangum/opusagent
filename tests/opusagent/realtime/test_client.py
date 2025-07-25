"""
Unit tests for opusagent.local.realtime.client module.
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any

from opusagent.local.realtime.client import LocalRealtimeClient
from opusagent.local.realtime.models import (
    LocalResponseConfig,
    ResponseSelectionCriteria,
    ConversationContext
)
from opusagent.models.openai_api import (
    ResponseCreateOptions,
    SessionConfig,
    ServerEventType
)


class TestLocalRealtimeClient:
    """Test LocalRealtimeClient class."""

    def test_client_creation_basic(self):
        """Test basic LocalRealtimeClient creation."""
        client = LocalRealtimeClient()
        
        assert client.logger is not None
        assert client.session_config is not None
        assert client.response_configs == {}
        assert client.default_response_config is not None
        assert client.connected is False
        assert client._ws is None
        assert client._message_task is None
        assert client._response_timings == []

    def test_client_creation_with_logger(self):
        """Test LocalRealtimeClient creation with custom logger."""
        logger = Mock()
        client = LocalRealtimeClient(logger=logger)
        
        assert client.logger == logger

    def test_client_creation_with_session_config(self):
        """Test LocalRealtimeClient creation with custom session config."""
        session_config = SessionConfig(
            model="gpt-4o-realtime-preview-2025-06-03",
            modalities=["text"],
            voice="nova"
        )
        client = LocalRealtimeClient(session_config=session_config)
        
        assert client.session_config == session_config
        assert client.session_config.model == "gpt-4o-realtime-preview-2025-06-03"
        assert client.session_config.voice == "nova"

    def test_client_creation_with_response_configs(self):
        """Test LocalRealtimeClient creation with response configs."""
        configs = {
            "greeting": LocalResponseConfig(text="Hello!"),
            "help": LocalResponseConfig(text="How can I help?")
        }
        client = LocalRealtimeClient(response_configs=configs)
        
        assert client.response_configs == configs
        assert "greeting" in client.response_configs
        assert "help" in client.response_configs

    def test_client_creation_with_default_response_config(self):
        """Test LocalRealtimeClient creation with default response config."""
        default_config = LocalResponseConfig(
            text="Default response",
            delay_seconds=0.1
        )
        client = LocalRealtimeClient(default_response_config=default_config)
        
        assert client.default_response_config == default_config
        assert client.default_response_config.text == "Default response"
        assert client.default_response_config.delay_seconds == 0.1

    def test_add_response_config(self):
        """Test adding response configuration."""
        client = LocalRealtimeClient()
        logger = Mock()
        client.logger = logger
        
        config = LocalResponseConfig(
            text="Test response",
            audio_file="test.wav",
            delay_seconds=0.05
        )
        
        client.add_response_config("test_key", config)
        
        assert "test_key" in client.response_configs
        assert client.response_configs["test_key"] == config
        logger.debug.assert_called_with("Added response config for key: test_key")

    def test_get_response_config_existing(self):
        """Test getting existing response configuration."""
        client = LocalRealtimeClient()
        config = LocalResponseConfig(text="Test response")
        client.response_configs["test_key"] = config
        
        result = client.get_response_config("test_key")
        
        assert result == config

    def test_get_response_config_nonexistent(self):
        """Test getting non-existent response configuration."""
        client = LocalRealtimeClient()
        default_config = LocalResponseConfig(text="Default")
        client.default_response_config = default_config
        
        result = client.get_response_config("nonexistent_key")
        
        assert result == default_config

    def test_get_response_config_none_key(self):
        """Test getting response configuration with None key."""
        client = LocalRealtimeClient()
        default_config = LocalResponseConfig(text="Default")
        client.default_response_config = default_config
        
        result = client.get_response_config(None)
        
        assert result == default_config

    def test_detect_intents_greeting(self):
        """Test intent detection for greeting."""
        client = LocalRealtimeClient()
        
        intents = client._detect_intents("Hello there!")
        assert "greeting" in intents
        
        intents = client._detect_intents("Hi, how are you?")
        assert "greeting" in intents
        
        intents = client._detect_intents("Hey, what's up?")
        assert "greeting" in intents

    def test_detect_intents_farewell(self):
        """Test intent detection for farewell."""
        client = LocalRealtimeClient()
        
        intents = client._detect_intents("Goodbye!")
        assert "farewell" in intents
        
        intents = client._detect_intents("See you later")
        assert "farewell" in intents

    def test_detect_intents_help_request(self):
        """Test intent detection for help request."""
        client = LocalRealtimeClient()
        
        intents = client._detect_intents("I need help")
        assert "help_request" in intents
        
        intents = client._detect_intents("Can you assist me?")
        assert "help_request" in intents
        
        intents = client._detect_intents("I have a problem")
        assert "help_request" in intents

    def test_detect_intents_question(self):
        """Test intent detection for questions."""
        client = LocalRealtimeClient()
        
        intents = client._detect_intents("What is this?")
        assert "question" in intents
        
        intents = client._detect_intents("How does it work?")
        assert "question" in intents
        
        intents = client._detect_intents("Why is this happening?")
        assert "question" in intents

    def test_detect_intents_complaint(self):
        """Test intent detection for complaints."""
        client = LocalRealtimeClient()
        
        intents = client._detect_intents("I have a complaint")
        assert "complaint" in intents
        
        intents = client._detect_intents("There's an issue")
        assert "complaint" in intents
        
        intents = client._detect_intents("This is broken")
        assert "complaint" in intents

    def test_detect_intents_gratitude(self):
        """Test intent detection for gratitude."""
        client = LocalRealtimeClient()
        
        intents = client._detect_intents("Thank you")
        assert "gratitude" in intents
        
        intents = client._detect_intents("Thanks for your help")
        assert "gratitude" in intents

    def test_detect_intents_confirmation(self):
        """Test intent detection for confirmation."""
        client = LocalRealtimeClient()
        
        intents = client._detect_intents("Yes, that's correct")
        assert "confirmation" in intents
        
        intents = client._detect_intents("Right, exactly")
        assert "confirmation" in intents

    def test_detect_intents_denial(self):
        """Test intent detection for denial."""
        client = LocalRealtimeClient()
        
        intents = client._detect_intents("No, that's wrong")
        assert "denial" in intents
        
        intents = client._detect_intents("Incorrect")
        assert "denial" in intents

    def test_detect_intents_multiple(self):
        """Test detection of multiple intents."""
        client = LocalRealtimeClient()
        
        intents = client._detect_intents("Hello, I need help with a problem")
        assert "greeting" in intents
        assert "help_request" in intents
        assert "complaint" in intents

    def test_check_keyword_match(self):
        """Test keyword matching."""
        client = LocalRealtimeClient()
        
        # Test with matching keywords
        assert client._check_keyword_match("Hello world", ["hello", "world"])
        assert client._check_keyword_match("HELLO WORLD", ["hello", "world"])  # Case insensitive
        
        # Test with non-matching keywords
        assert not client._check_keyword_match("Hello world", ["goodbye", "farewell"])
        
        # Test with None input
        assert not client._check_keyword_match(None, ["hello"])

    def test_check_intent_match(self):
        """Test intent matching."""
        client = LocalRealtimeClient()
        
        # Test with matching intents
        assert client._check_intent_match(["greeting", "help"], ["greeting"])
        assert client._check_intent_match(["greeting", "help"], ["help", "complaint"])
        
        # Test with non-matching intents
        assert not client._check_intent_match(["greeting"], ["help", "complaint"])

    def test_check_modality_match(self):
        """Test modality matching."""
        client = LocalRealtimeClient()
        
        # Test with matching modalities
        assert client._check_modality_match(["text", "audio"], ["text"])
        assert client._check_modality_match(["text", "audio"], ["text", "audio"])
        
        # Test with non-matching modalities
        assert not client._check_modality_match(["text"], ["audio"])
        assert not client._check_modality_match(["text", "audio"], ["video"])

    def test_check_context_patterns(self):
        """Test context pattern matching."""
        client = LocalRealtimeClient()
        
        context = ConversationContext(
            session_id="test",
            conversation_id="test",
            last_user_input="I have an error in my code"
        )
        
        # Test with matching pattern
        patterns = [r"error|bug|crash"]
        assert client._check_context_patterns(context, patterns)
        
        # Test with non-matching pattern
        patterns = [r"success|working"]
        assert not client._check_context_patterns(context, patterns)

    def test_update_conversation_context(self):
        """Test updating conversation context."""
        client = LocalRealtimeClient()
        
        # Update with user input
        client.update_conversation_context("Hello, I need help")
        
        # Get session state and check context
        session_state = client.get_session_state()
        context = session_state.get("conversation_context")
        
        assert context is not None
        assert context.last_user_input == "Hello, I need help"
        assert "greeting" in context.detected_intents
        assert "help_request" in context.detected_intents
        assert len(context.conversation_history) == 1

    def test_update_conversation_context_no_input(self):
        """Test updating conversation context without input."""
        client = LocalRealtimeClient()
        
        # Update without user input
        client.update_conversation_context()
        
        # Get session state and check context
        session_state = client.get_session_state()
        context = session_state.get("conversation_context")
        
        assert context is not None
        assert context.last_user_input is None
        assert len(context.conversation_history) == 0

    def test_setup_smart_response_examples(self):
        """Test setting up smart response examples."""
        client = LocalRealtimeClient()
        
        client.setup_smart_response_examples()
        
        # Check that examples were added
        expected_keys = [
            "greeting", "help_request", "complaint", "question",
            "gratitude", "farewell", "function_call", "audio_only",
            "technical_support", "fallback"
        ]
        
        for key in expected_keys:
            assert key in client.response_configs

    def test_setup_smart_response_examples_greeting(self):
        """Test greeting response example."""
        client = LocalRealtimeClient()
        client.setup_smart_response_examples()
        
        greeting_config = client.response_configs["greeting"]
        assert greeting_config.text == "Hello! Welcome to our service. How can I help you today?"
        assert greeting_config.audio_file == "audio/greetings/greeting_01.wav"
        assert greeting_config.delay_seconds == 0.03
        
        criteria = greeting_config.selection_criteria
        assert criteria is not None
        assert criteria.required_keywords == ["hello", "hi", "hey", "greetings"]
        assert criteria.max_turn_count == 1
        assert criteria.priority == 20

    def test_setup_smart_response_examples_help_request(self):
        """Test help request response example."""
        client = LocalRealtimeClient()
        client.setup_smart_response_examples()
        
        help_config = client.response_configs["help_request"]
        assert help_config.text == "I'd be happy to help! What specific issue are you experiencing?"
        assert help_config.audio_file == "audio/help/help_01.wav"
        
        criteria = help_config.selection_criteria
        assert criteria is not None
        assert criteria.required_intents == ["help_request"]
        assert criteria.priority == 15

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection."""
        client = LocalRealtimeClient()
        logger = Mock()
        client.logger = logger
        
        # Mock websockets.connect
        mock_ws = AsyncMock()
        mock_connect = AsyncMock(return_value=mock_ws)
        with patch('opusagent.local.realtime.client.websockets.connect', mock_connect), \
             patch('opusagent.utils.websocket_utils.WebSocketUtils.safe_send_event', new=AsyncMock(return_value=True)):
            await client.connect("ws://localhost:8080")
        
        assert client.connected is True
        assert client._ws == mock_ws
        assert client._message_task is not None
        logger.info.assert_called_with("[MOCK REALTIME] Connected successfully")

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure."""
        client = LocalRealtimeClient()
        logger = Mock()
        client.logger = logger
        
        # Mock websockets.connect to raise exception
        with patch('opusagent.local.realtime.client.websockets.connect', side_effect=Exception("Connection failed")):
            with pytest.raises(Exception, match="Connection failed"):
                await client.connect("ws://localhost:8080")
        
        assert client.connected is False
        logger.error.assert_called_with("[MOCK REALTIME] Connection failed: Connection failed")

    @pytest.mark.asyncio
    async def test_disconnect_success(self):
        """Test successful disconnection."""
        client = LocalRealtimeClient()
        logger = Mock()
        client.logger = logger
        
        # Set up connected state
        client.connected = True
        client._ws = AsyncMock()
        client._message_task = asyncio.create_task(asyncio.sleep(1))
        
        await client.disconnect()
        
        assert client.connected is False
        assert client._ws is None
        logger.info.assert_called_with("[MOCK REALTIME] Disconnected successfully")

    @pytest.mark.asyncio
    async def test_disconnect_not_connected(self):
        """Test disconnection when not connected."""
        client = LocalRealtimeClient()
        logger = Mock()
        client.logger = logger
        
        # Should not raise exception
        await client.disconnect()
        
        assert client.connected is False

    @pytest.mark.asyncio
    async def test_disconnect_with_exception(self):
        """Test disconnection with exception."""
        client = LocalRealtimeClient()
        logger = Mock()
        client.logger = logger
        
        # Set up connected state with problematic WebSocket
        client.connected = True
        mock_ws = AsyncMock()
        mock_ws.close.side_effect = Exception("Close failed")
        client._ws = mock_ws
        
        # Should not raise exception, should log warning
        await client.disconnect()
        
        assert client.connected is False
        logger.warning.assert_called_with("[MOCK REALTIME] Error during disconnect: Close failed")

    def test_get_session_state(self):
        """Test getting session state."""
        client = LocalRealtimeClient()
        
        state = client.get_session_state()
        
        assert isinstance(state, dict)
        assert "session_id" in state
        assert "conversation_id" in state
        assert "connected" in state
        assert "active_response_id" in state
        assert "speech_detected" in state
        assert "audio_buffer" in state

    def test_get_audio_buffer(self):
        """Test getting audio buffer."""
        client = LocalRealtimeClient()
        
        # Add some audio data
        client._event_handler._session_state["audio_buffer"] = [b"chunk1", b"chunk2"]
        
        buffer = client.get_audio_buffer()
        
        assert buffer == [b"chunk1", b"chunk2"]

    def test_set_audio_buffer(self):
        """Test setting audio buffer."""
        client = LocalRealtimeClient()
        
        audio_data = [b"new_chunk1", b"new_chunk2"]
        client.set_audio_buffer(audio_data)
        
        buffer = client.get_audio_buffer()
        assert buffer == audio_data

    def test_get_active_response_id(self):
        """Test getting active response ID."""
        client = LocalRealtimeClient()
        
        # Set active response ID
        client._response_generator._active_response_id = "test_response_123"
        
        response_id = client.get_active_response_id()
        assert response_id == "test_response_123"

    def test_set_active_response_id(self):
        """Test setting active response ID."""
        client = LocalRealtimeClient()
        
        client.set_active_response_id("new_response_456")
        
        assert client._response_generator._active_response_id == "new_response_456"
        assert client._event_handler._session_state["active_response_id"] == "new_response_456"

    def test_get_response_timings(self):
        """Test getting response timings."""
        client = LocalRealtimeClient()
        
        # Add some timing records
        client._response_timings = [
            {"response_id": "resp1", "duration": 0.1, "timestamp": "2023-01-01T00:00:00"},
            {"response_id": "resp2", "duration": 0.2, "timestamp": "2023-01-01T00:00:01"}
        ]
        
        timings = client.get_response_timings()
        
        assert len(timings) == 2
        assert timings[0]["response_id"] == "resp1"
        assert timings[1]["response_id"] == "resp2"

    def test_get_response_timings_limit(self):
        """Test that response timings are limited to last 100."""
        client = LocalRealtimeClient()
        
        # Add more than 100 timing records
        for i in range(150):
            client._response_timings.append({
                "response_id": f"resp{i}",
                "duration": 0.1,
                "timestamp": "2023-01-01T00:00:00"
            })
        
        timings = client.get_response_timings()
        
        assert len(timings) == 100
        assert timings[0]["response_id"] == "resp50"  # Last 100 records

    @pytest.mark.asyncio
    async def test_load_audio_file(self):
        """Test loading audio file."""
        client = LocalRealtimeClient()
        
        # Mock audio manager
        mock_audio_manager = AsyncMock()
        mock_audio_manager.load_audio_file.return_value = b"audio_data"
        client._audio_manager = mock_audio_manager
        
        result = await client.load_audio_file("test.wav")
        
        assert result == b"audio_data"
        mock_audio_manager.load_audio_file.assert_called_once_with("test.wav")

    def test_register_event_handler(self):
        """Test registering event handler."""
        client = LocalRealtimeClient()
        
        async def test_handler(data):
            pass
        
        client.register_event_handler("test.event", test_handler)
        
        # Check that handler was registered in event handler manager
        assert "test.event" in client._event_handler._event_handlers

    @pytest.mark.asyncio
    async def test_send_error(self):
        """Test sending error."""
        client = LocalRealtimeClient()
        
        # Mock response generator
        mock_generator = AsyncMock()
        client._response_generator = mock_generator
        
        await client.send_error("TEST_ERROR", "Test error message", {"detail": "test"})
        
        mock_generator.send_error.assert_called_once_with(
            "TEST_ERROR", "Test error message", {"detail": "test"}
        )

    @pytest.mark.asyncio
    async def test_send_transcript_delta(self):
        """Test sending transcript delta."""
        client = LocalRealtimeClient()
        
        # Mock response generator
        mock_generator = AsyncMock()
        client._response_generator = mock_generator
        
        await client.send_transcript_delta("Hello", final=True)
        
        mock_generator.send_transcript_delta.assert_called_once_with("Hello", True)

    @pytest.mark.asyncio
    async def test_send_input_transcript_delta(self):
        """Test sending input transcript delta."""
        client = LocalRealtimeClient()
        
        # Mock response generator
        mock_generator = AsyncMock()
        client._response_generator = mock_generator
        
        await client.send_input_transcript_delta("item_123", "User input", final=True)
        
        mock_generator.send_input_transcript_delta.assert_called_once_with(
            "item_123", "User input", True
        )

    @pytest.mark.asyncio
    async def test_send_input_transcript_failed(self):
        """Test sending input transcript failed."""
        client = LocalRealtimeClient()
        
        # Mock response generator
        mock_generator = AsyncMock()
        client._response_generator = mock_generator
        
        error = {"code": "transcription_failed"}
        await client.send_input_transcript_failed("item_123", error)
        
        mock_generator.send_input_transcript_failed.assert_called_once_with("item_123", error)

    @pytest.mark.asyncio
    async def test_handle_session_update(self):
        """Test handling session update."""
        client = LocalRealtimeClient()
        
        # Mock event handler
        mock_handler = AsyncMock()
        client._event_handler = mock_handler
        
        data = {"session": {"model": "test-model"}}
        await client.handle_session_update(data)
        
        mock_handler._handle_session_update.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_handle_audio_append(self):
        """Test handling audio append."""
        client = LocalRealtimeClient()
        
        # Mock event handler
        mock_handler = AsyncMock()
        client._event_handler = mock_handler
        
        data = {"audio": "base64_audio_data"}
        await client.handle_audio_append(data)
        
        mock_handler._handle_audio_append.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_handle_audio_commit(self):
        """Test handling audio commit."""
        client = LocalRealtimeClient()
        
        # Mock event handler
        mock_handler = AsyncMock()
        client._event_handler = mock_handler
        
        data = {}
        await client.handle_audio_commit(data)
        
        mock_handler._handle_audio_commit.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_handle_response_cancel(self):
        """Test handling response cancel."""
        client = LocalRealtimeClient()
        
        # Mock event handler
        mock_handler = AsyncMock()
        client._event_handler = mock_handler
        
        data = {"response_id": "test_response_123"}
        await client.handle_response_cancel(data)
        
        mock_handler._handle_response_cancel.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_send_rate_limits(self):
        """Test sending rate limits."""
        client = LocalRealtimeClient()
        
        # Mock event handler
        mock_handler = AsyncMock()
        client._event_handler = mock_handler
        
        limits = [{"type": "requests", "limit": 100}]
        await client.send_rate_limits(limits)
        
        mock_handler._send_event.assert_called_once()
        sent_event = mock_handler._send_event.call_args[0][0]
        assert sent_event["type"] == ServerEventType.RATE_LIMITS_UPDATED
        assert sent_event["rate_limits"] == limits

    @pytest.mark.asyncio
    async def test_send_content_part_added(self):
        """Test sending content part added."""
        client = LocalRealtimeClient()
        
        # Mock response generator
        mock_generator = AsyncMock()
        client._response_generator = mock_generator
        
        part = {"type": "text", "content": "Hello"}
        await client.send_content_part_added(part)
        
        mock_generator._send_event.assert_called_once()
        sent_event = mock_generator._send_event.call_args[0][0]
        assert sent_event["type"] == ServerEventType.RESPONSE_CONTENT_PART_ADDED
        assert sent_event["part"] == part

    @pytest.mark.asyncio
    async def test_send_content_part_done(self):
        """Test sending content part done event."""
        client = LocalRealtimeClient()
        client._response_generator.set_active_response_id("resp_123")
        client._response_generator._send_event = AsyncMock()
        
        part_data = {
            "type": "text",
            "content": "Complete text"
        }
        
        await client.send_content_part_done(part_data)
        
        client._response_generator._send_event.assert_called_once()
        call_args = client._response_generator._send_event.call_args[0][0]
        
        assert call_args["type"] == ServerEventType.RESPONSE_CONTENT_PART_DONE
        assert call_args["part"] == part_data
        assert call_args["status"] == "completed"


class TestVADIntegration:
    """Test VAD integration in LocalRealtimeClient."""

    def test_client_creation_with_vad_enabled_explicit(self):
        """Test client creation with VAD explicitly enabled."""
        vad_config = {
            "backend": "silero",
            "sample_rate": 16000,
            "threshold": 0.3
        }
        
        with patch('opusagent.local.realtime.client.VADFactory') as mock_vad_factory, \
             patch('opusagent.local.realtime.client.load_vad_config') as mock_load_config:
            
            mock_load_config.return_value = {"backend": "silero", "sample_rate": 16000}
            mock_vad = Mock()
            mock_vad_factory.create_vad.return_value = mock_vad
            
            client = LocalRealtimeClient(enable_vad=True, vad_config=vad_config)
            
            assert client.is_vad_enabled() is True
            assert client._vad is not None
            mock_vad_factory.create_vad.assert_called_once()

    def test_client_creation_with_vad_disabled_explicit(self):
        """Test client creation with VAD explicitly disabled."""
        client = LocalRealtimeClient(enable_vad=False)
        
        assert client.is_vad_enabled() is False
        assert client._vad is None

    def test_client_creation_with_vad_auto_enabled_by_session_config(self):
        """Test client creation with VAD auto-enabled by session configuration."""
        session_config = SessionConfig(
            model="gpt-4o-realtime-preview-2025-06-03",
            turn_detection={"type": "server_vad"}
        )
        
        with patch('opusagent.local.realtime.client.VADFactory') as mock_vad_factory, \
             patch('opusagent.local.realtime.client.load_vad_config') as mock_load_config:
            
            mock_load_config.return_value = {"backend": "silero", "sample_rate": 16000}
            mock_vad = Mock()
            mock_vad_factory.create_vad.return_value = mock_vad
            
            client = LocalRealtimeClient(session_config=session_config)
            
            assert client.is_vad_enabled() is True
            assert client._vad is not None
            mock_vad_factory.create_vad.assert_called_once()

    def test_client_creation_with_vad_disabled_by_default(self):
        """Test client creation with VAD disabled by default."""
        session_config = SessionConfig(
            model="gpt-4o-realtime-preview-2025-06-03",
            turn_detection={"type": "none"}
        )
        
        client = LocalRealtimeClient(session_config=session_config)
        
        assert client.is_vad_enabled() is False
        assert client._vad is None

    def test_vad_initialization_failure_fallback(self):
        """Test VAD initialization failure graceful fallback."""
        session_config = SessionConfig(
            model="gpt-4o-realtime-preview-2025-06-03",
            turn_detection={"type": "server_vad"}
        )
        
        with patch('opusagent.local.realtime.client.VADFactory') as mock_vad_factory, \
             patch('opusagent.local.realtime.client.load_vad_config') as mock_load_config:
            
            mock_load_config.return_value = {"backend": "silero", "sample_rate": 16000}
            mock_vad_factory.create_vad.side_effect = Exception("VAD initialization failed")
            
            client = LocalRealtimeClient(session_config=session_config, enable_vad=True)
            
            assert client.is_vad_enabled() is False
            assert client._vad is None

    def test_is_vad_enabled(self):
        """Test VAD enabled status check."""
        client = LocalRealtimeClient(enable_vad=False)
        assert client.is_vad_enabled() is False
        
        with patch('opusagent.local.realtime.client.VADFactory') as mock_vad_factory, \
             patch('opusagent.local.realtime.client.load_vad_config') as mock_load_config:
            
            mock_load_config.return_value = {"backend": "silero"}
            mock_vad = Mock()
            mock_vad_factory.create_vad.return_value = mock_vad
            
            client = LocalRealtimeClient(enable_vad=True)
            assert client.is_vad_enabled() is True

    def test_get_vad_config(self):
        """Test getting VAD configuration."""
        vad_config = {
            "backend": "silero",
            "sample_rate": 16000,
            "threshold": 0.3
        }
        
        client = LocalRealtimeClient(vad_config=vad_config)
        result_config = client.get_vad_config()
        
        assert result_config == vad_config
        # Ensure it's a copy, not the original
        assert result_config is not client._vad_config

    def test_enable_vad_runtime(self):
        """Test enabling VAD at runtime."""
        client = LocalRealtimeClient(enable_vad=False)
        assert client.is_vad_enabled() is False
        
        with patch('opusagent.local.realtime.client.VADFactory') as mock_vad_factory, \
             patch('opusagent.local.realtime.client.load_vad_config') as mock_load_config:
            
            mock_load_config.return_value = {"backend": "silero"}
            mock_vad = Mock()
            mock_vad_factory.create_vad.return_value = mock_vad
            
            client.enable_vad()
            
            assert client.is_vad_enabled() is True
            assert client._vad is not None
            assert client._event_handler._vad is not None
            mock_vad_factory.create_vad.assert_called_once()

    def test_enable_vad_with_custom_config(self):
        """Test enabling VAD with custom configuration."""
        client = LocalRealtimeClient(enable_vad=False)
        
        custom_config = {
            "backend": "silero",
            "threshold": 0.7,
            "sample_rate": 8000
        }
        
        with patch('opusagent.local.realtime.client.VADFactory') as mock_vad_factory, \
             patch('opusagent.local.realtime.client.load_vad_config') as mock_load_config:
            
            mock_load_config.return_value = {"backend": "silero", "sample_rate": 16000}
            mock_vad = Mock()
            mock_vad_factory.create_vad.return_value = mock_vad
            
            client.enable_vad(custom_config)
            
            assert client.is_vad_enabled() is True
            # Check that custom config was merged
            expected_config = {"backend": "silero", "sample_rate": 8000, "threshold": 0.7}
            mock_vad_factory.create_vad.assert_called_once()
            call_args = mock_vad_factory.create_vad.call_args[0][0]
            assert call_args["threshold"] == 0.7
            assert call_args["sample_rate"] == 8000

    def test_disable_vad_runtime(self):
        """Test disabling VAD at runtime."""
        with patch('opusagent.local.realtime.client.VADFactory') as mock_vad_factory, \
             patch('opusagent.local.realtime.client.load_vad_config') as mock_load_config:
            
            mock_load_config.return_value = {"backend": "silero"}
            mock_vad = Mock()
            mock_vad.cleanup = Mock()
            mock_vad_factory.create_vad.return_value = mock_vad
            
            client = LocalRealtimeClient(enable_vad=True)
            assert client.is_vad_enabled() is True
            
            client.disable_vad()
            
            assert client.is_vad_enabled() is False
            assert client._vad is None
            assert client._event_handler._vad is None
            mock_vad.cleanup.assert_called_once()

    def test_get_vad_state_disabled(self):
        """Test getting VAD state when disabled."""
        client = LocalRealtimeClient(enable_vad=False)
        
        state = client.get_vad_state()
        
        assert state["enabled"] is False
        assert state["initialized"] is False
        assert state["speech_active"] is False
        assert "configuration" in state

    def test_get_vad_state_enabled(self):
        """Test getting VAD state when enabled."""
        with patch('opusagent.local.realtime.client.VADFactory') as mock_vad_factory, \
             patch('opusagent.local.realtime.client.load_vad_config') as mock_load_config:
            
            mock_load_config.return_value = {"backend": "silero"}
            mock_vad = Mock()
            mock_vad_factory.create_vad.return_value = mock_vad
            
            client = LocalRealtimeClient(enable_vad=True)
            
            # Mock some VAD state in the event handler
            client._event_handler._vad_state = {
                "speech_active": True,
                "confidence_history": [0.8, 0.9, 0.7],
                "speech_counter": 3,
                "silence_counter": 0,
                "last_speech_time": 1234567890.0,
                "speech_start_time": 1234567885.0
            }
            client._event_handler._session_state["speech_detected"] = True
            
            state = client.get_vad_state()
            
            assert state["enabled"] is True
            assert state["initialized"] is True
            assert state["speech_active"] is True
            assert "state_details" in state
            assert state["state_details"]["speech_active"] is True
            assert state["state_details"]["confidence_history"] == [0.8, 0.9, 0.7]

    def test_reset_vad_state(self):
        """Test resetting VAD state."""
        with patch('opusagent.local.realtime.client.VADFactory') as mock_vad_factory, \
             patch('opusagent.local.realtime.client.load_vad_config') as mock_load_config:
            
            mock_load_config.return_value = {"backend": "silero"}
            mock_vad = Mock()
            mock_vad_factory.create_vad.return_value = mock_vad
            
            client = LocalRealtimeClient(enable_vad=True)
            client._event_handler._reset_vad_state = Mock()
            
            client.reset_vad_state()
            
            client._event_handler._reset_vad_state.assert_called_once()

    def test_update_vad_config(self):
        """Test updating VAD configuration."""
        with patch('opusagent.local.realtime.client.VADFactory') as mock_vad_factory, \
             patch('opusagent.local.realtime.client.load_vad_config') as mock_load_config:
            
            mock_load_config.return_value = {"backend": "silero", "threshold": 0.5}
            mock_vad = Mock()
            mock_vad.cleanup = Mock()
            mock_vad_factory.create_vad.return_value = mock_vad
            
            client = LocalRealtimeClient(enable_vad=True)
            original_threshold = client._vad_config.get("threshold", 0.5)
            
            config_updates = {"threshold": 0.8, "new_param": "value"}
            client.update_vad_config(config_updates)
            
            # Should have updated the config
            assert client._vad_config["threshold"] == 0.8
            assert client._vad_config["new_param"] == "value"
            
            # Should have reinitalized VAD
            assert mock_vad.cleanup.call_count == 1  # Called during reinitialization
            assert mock_vad_factory.create_vad.call_count == 2  # Initial + reinitialization

    @pytest.mark.asyncio
    async def test_handle_vad_session_update_enable(self):
        """Test VAD session update handling when enabling VAD."""
        client = LocalRealtimeClient(enable_vad=False)
        client.session_config.turn_detection = {"type": "server_vad"}
        
        # Mock VAD operations
        client.enable_vad = Mock()
        client.is_vad_enabled = Mock(return_value=False)
        
        await client._handle_vad_session_update()
        
        client.enable_vad.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_vad_session_update_disable(self):
        """Test VAD session update handling when disabling VAD."""
        with patch('opusagent.local.realtime.client.VADFactory') as mock_vad_factory, \
             patch('opusagent.local.realtime.client.load_vad_config') as mock_load_config:
            
            mock_load_config.return_value = {"backend": "silero"}
            mock_vad = Mock()
            mock_vad_factory.create_vad.return_value = mock_vad
            
            client = LocalRealtimeClient(enable_vad=True)
            client.session_config.turn_detection = {"type": "none"}
            client.disable_vad = Mock()
            
            await client._handle_vad_session_update()
            
            client.disable_vad.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_session_update_with_vad_changes(self):
        """Test session update handling with VAD configuration changes."""
        client = LocalRealtimeClient(enable_vad=False)
        client._event_handler._handle_session_update = AsyncMock()
        client._handle_vad_session_update = AsyncMock()
        
        # Simulate turn detection change
        data = {
            "session": {
                "turn_detection": {"type": "server_vad"}
            }
        }
        
        await client.handle_session_update(data)
        
        client._event_handler._handle_session_update.assert_called_once_with(data)
        client._handle_vad_session_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_session_update_no_vad_changes(self):
        """Test session update handling without VAD configuration changes."""
        client = LocalRealtimeClient(enable_vad=False)
        client._event_handler._handle_session_update = AsyncMock()
        client._handle_vad_session_update = AsyncMock()
        
        # Simulate non-turn-detection change
        data = {
            "session": {
                "voice": "nova"
            }
        }
        
        await client.handle_session_update(data)
        
        client._event_handler._handle_session_update.assert_called_once_with(data)
        client._handle_vad_session_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_disconnect_cleanup_vad(self):
        """Test that VAD resources are cleaned up on disconnect."""
        with patch('opusagent.local.realtime.client.VADFactory') as mock_vad_factory, \
             patch('opusagent.local.realtime.client.load_vad_config') as mock_load_config:
            
            mock_load_config.return_value = {"backend": "silero"}
            mock_vad = Mock()
            mock_vad.cleanup = Mock()
            mock_vad_factory.create_vad.return_value = mock_vad
            
            client = LocalRealtimeClient(enable_vad=True)
            client._ws = AsyncMock()
            client._message_task = None
            
            await client.disconnect()
            
            mock_vad.cleanup.assert_called_once()

    def test_vad_config_immutability(self):
        """Test that VAD config returned by get_vad_config is immutable."""
        original_config = {
            "backend": "silero",
            "threshold": 0.5
        }
        
        client = LocalRealtimeClient(vad_config=original_config)
        returned_config = client.get_vad_config()
        
        # Modify the returned config
        returned_config["threshold"] = 0.8
        returned_config["new_key"] = "new_value"
        
        # Original should be unchanged
        assert client._vad_config["threshold"] == 0.5
        assert "new_key" not in client._vad_config

    def test_vad_event_handler_integration(self):
        """Test that VAD instance is properly passed to event handler."""
        with patch('opusagent.local.realtime.client.VADFactory') as mock_vad_factory, \
             patch('opusagent.local.realtime.client.load_vad_config') as mock_load_config:
            
            mock_load_config.return_value = {"backend": "silero"}
            mock_vad = Mock()
            mock_vad_factory.create_vad.return_value = mock_vad
            
            client = LocalRealtimeClient(enable_vad=True)
            
            assert client._event_handler._vad is mock_vad

    def test_vad_enable_disable_event_handler_sync(self):
        """Test that enabling/disabling VAD keeps event handler in sync."""
        client = LocalRealtimeClient(enable_vad=False)
        assert client._event_handler._vad is None
        
        with patch('opusagent.local.realtime.client.VADFactory') as mock_vad_factory, \
             patch('opusagent.local.realtime.client.load_vad_config') as mock_load_config:
            
            mock_load_config.return_value = {"backend": "silero"}
            mock_vad = Mock()
            mock_vad.cleanup = Mock()
            mock_vad_factory.create_vad.return_value = mock_vad
            
            client.enable_vad()
            assert client._event_handler._vad is mock_vad
            
            client.disable_vad()
            assert client._event_handler._vad is None


class TestResponseSelection:
    """Test response selection logic."""

    def test_determine_response_key_no_configs(self):
        """Test response key determination with no configs."""
        client = LocalRealtimeClient()
        
        options = ResponseCreateOptions()
        result = client._determine_response_key(options)
        
        assert result is None

    def test_determine_response_key_with_configs(self):
        """Test response key determination with configs."""
        client = LocalRealtimeClient()
        
        # Add response configs
        config1 = LocalResponseConfig(
            text="Response 1",
            selection_criteria=ResponseSelectionCriteria(priority=10)
        )
        config2 = LocalResponseConfig(
            text="Response 2",
            selection_criteria=ResponseSelectionCriteria(priority=20)
        )
        
        client.response_configs["config1"] = config1
        client.response_configs["config2"] = config2
        
        options = ResponseCreateOptions()
        result = client._determine_response_key(options)
        
        # Should return the config with higher priority
        assert result == "config2"

    def test_calculate_response_score_basic(self):
        """Test basic response score calculation."""
        client = LocalRealtimeClient()
        
        config = LocalResponseConfig(
            text="Test response",
            selection_criteria=ResponseSelectionCriteria(priority=15)
        )
        
        context = ConversationContext(
            session_id="test",
            conversation_id="test",
            last_user_input="Hello world"
        )
        
        options = ResponseCreateOptions()
        
        score = client._calculate_response_score(config, context, options)
        
        assert score == 15.0  # Base priority

    def test_calculate_response_score_keyword_match(self):
        """Test response score calculation with keyword match."""
        client = LocalRealtimeClient()
        
        config = LocalResponseConfig(
            text="Test response",
            selection_criteria=ResponseSelectionCriteria(
                priority=10,
                required_keywords=["hello", "world"]
            )
        )
        
        context = ConversationContext(
            session_id="test",
            conversation_id="test",
            last_user_input="Hello world"
        )
        
        options = ResponseCreateOptions()
        
        score = client._calculate_response_score(config, context, options)
        
        assert score == 20.0  # Base priority + keyword bonus

    def test_calculate_response_score_keyword_mismatch(self):
        """Test response score calculation with keyword mismatch."""
        client = LocalRealtimeClient()
        
        config = LocalResponseConfig(
            text="Test response",
            selection_criteria=ResponseSelectionCriteria(
                priority=10,
                required_keywords=["goodbye", "farewell"]
            )
        )
        
        context = ConversationContext(
            session_id="test",
            conversation_id="test",
            last_user_input="Hello world"
        )
        
        options = ResponseCreateOptions()
        
        score = client._calculate_response_score(config, context, options)
        
        assert score == 0.0  # Required keywords not found

    def test_calculate_response_score_excluded_keywords(self):
        """Test response score calculation with excluded keywords."""
        client = LocalRealtimeClient()
        
        config = LocalResponseConfig(
            text="Test response",
            selection_criteria=ResponseSelectionCriteria(
                priority=10,
                excluded_keywords=["goodbye", "farewell"]
            )
        )
        
        context = ConversationContext(
            session_id="test",
            conversation_id="test",
            last_user_input="Hello world"
        )
        
        options = ResponseCreateOptions()
        
        score = client._calculate_response_score(config, context, options)
        
        assert score == 10.0  # Base priority (no excluded keywords found)

    def test_calculate_response_score_excluded_keywords_found(self):
        """Test response score calculation when excluded keywords are found."""
        client = LocalRealtimeClient()
        
        config = LocalResponseConfig(
            text="Test response",
            selection_criteria=ResponseSelectionCriteria(
                priority=10,
                excluded_keywords=["hello", "world"]
            )
        )
        
        context = ConversationContext(
            session_id="test",
            conversation_id="test",
            last_user_input="Hello world"
        )
        
        options = ResponseCreateOptions()
        
        score = client._calculate_response_score(config, context, options)
        
        assert score == 0.0  # Excluded keywords found

    def test_calculate_response_score_intent_match(self):
        """Test response score calculation with intent match."""
        client = LocalRealtimeClient()
        
        config = LocalResponseConfig(
            text="Test response",
            selection_criteria=ResponseSelectionCriteria(
                priority=10,
                required_intents=["greeting"]
            )
        )
        
        context = ConversationContext(
            session_id="test",
            conversation_id="test",
            last_user_input="Hello world",
            detected_intents=["greeting", "help_request"]
        )
        
        options = ResponseCreateOptions()
        
        score = client._calculate_response_score(config, context, options)
        
        assert score == 25.0  # Base priority + intent bonus

    def test_calculate_response_score_intent_mismatch(self):
        """Test response score calculation with intent mismatch."""
        client = LocalRealtimeClient()
        
        config = LocalResponseConfig(
            text="Test response",
            selection_criteria=ResponseSelectionCriteria(
                priority=10,
                required_intents=["complaint"]
            )
        )
        
        context = ConversationContext(
            session_id="test",
            conversation_id="test",
            last_user_input="Hello world",
            detected_intents=["greeting", "help_request"]
        )
        
        options = ResponseCreateOptions()
        
        score = client._calculate_response_score(config, context, options)
        
        assert score == 0.0  # Required intents not found

    def test_calculate_response_score_turn_count_conditions(self):
        """Test response score calculation with turn count conditions."""
        client = LocalRealtimeClient()
        
        config = LocalResponseConfig(
            text="Test response",
            selection_criteria=ResponseSelectionCriteria(
                priority=10,
                min_turn_count=2,
                max_turn_count=5
            )
        )
        
        # Test with turn count within range
        context = ConversationContext(
            session_id="test",
            conversation_id="test",
            turn_count=3
        )
        
        options = ResponseCreateOptions()
        
        score = client._calculate_response_score(config, context, options)
        assert score == 10.0  # Base priority
        
        # Test with turn count below minimum
        context.turn_count = 1
        score = client._calculate_response_score(config, context, options)
        assert score == 0.0
        
        # Test with turn count above maximum
        context.turn_count = 6
        score = client._calculate_response_score(config, context, options)
        assert score == 0.0

    def test_calculate_response_score_modality_match(self):
        """Test response score calculation with modality match."""
        client = LocalRealtimeClient()
        
        config = LocalResponseConfig(
            text="Test response",
            selection_criteria=ResponseSelectionCriteria(
                priority=10,
                required_modalities=["text", "audio"]
            )
        )
        
        context = ConversationContext(
            session_id="test",
            conversation_id="test"
        )
        
        options = ResponseCreateOptions(modalities=["text", "audio"])
        
        score = client._calculate_response_score(config, context, options)
        
        assert score == 15.0  # Base priority + modality bonus

    def test_calculate_response_score_modality_mismatch(self):
        """Test response score calculation with modality mismatch."""
        client = LocalRealtimeClient()
        
        config = LocalResponseConfig(
            text="Test response",
            selection_criteria=ResponseSelectionCriteria(
                priority=10,
                required_modalities=["video"]
            )
        )
        
        context = ConversationContext(
            session_id="test",
            conversation_id="test"
        )
        
        options = ResponseCreateOptions(modalities=["text", "audio"])
        
        score = client._calculate_response_score(config, context, options)
        
        assert score == 0.0  # Required modalities not available

    def test_calculate_response_score_function_call_required(self):
        """Test response score calculation with function call required."""
        client = LocalRealtimeClient()
        
        config = LocalResponseConfig(
            text="Test response",
            selection_criteria=ResponseSelectionCriteria(
                priority=10,
                requires_function_call=True
            )
        )
        
        context = ConversationContext(
            session_id="test",
            conversation_id="test"
        )
        
        # Test with function call available
        options = ResponseCreateOptions(tools=[{"name": "test_tool"}], tool_choice="auto")
        
        score = client._calculate_response_score(config, context, options)
        assert score == 18.0  # Base priority + function call bonus
        
        # Test without function call
        options = ResponseCreateOptions()
        
        score = client._calculate_response_score(config, context, options)
        assert score == 0.0  # Function call required but not available

    def test_calculate_response_score_function_call_not_required(self):
        """Test response score calculation with function call not required."""
        client = LocalRealtimeClient()
        
        config = LocalResponseConfig(
            text="Test response",
            selection_criteria=ResponseSelectionCriteria(
                priority=10,
                requires_function_call=False
            )
        )
        
        context = ConversationContext(
            session_id="test",
            conversation_id="test"
        )
        
        # Test without function call (as required)
        options = ResponseCreateOptions()
        
        score = client._calculate_response_score(config, context, options)
        assert score == 18.0  # Base priority + function call bonus
        
        # Test with function call (should not match)
        options = ResponseCreateOptions(tools=[{"name": "test_tool"}], tool_choice="auto")
        
        score = client._calculate_response_score(config, context, options)
        assert score == 0.0  # Function call not required but available

    def test_calculate_response_score_context_patterns(self):
        """Test response score calculation with context patterns."""
        client = LocalRealtimeClient()
        
        config = LocalResponseConfig(
            text="Test response",
            selection_criteria=ResponseSelectionCriteria(
                priority=10,
                context_patterns=[r"error|bug|crash"]
            )
        )
        
        context = ConversationContext(
            session_id="test",
            conversation_id="test",
            last_user_input="I have an error in my code"
        )
        
        options = ResponseCreateOptions()
        
        score = client._calculate_response_score(config, context, options)
        
        assert score == 22.0  # Base priority + context pattern bonus

    def test_calculate_response_score_text_match_bonus(self):
        """Test response score calculation with text match bonus."""
        client = LocalRealtimeClient()
        
        config = LocalResponseConfig(
            text="Hello world response",
            selection_criteria=ResponseSelectionCriteria(priority=10)
        )
        
        context = ConversationContext(
            session_id="test",
            conversation_id="test",
            last_user_input="Hello world"
        )
        
        options = ResponseCreateOptions()
        
        score = client._calculate_response_score(config, context, options)
        
        assert score == 13.0  # Base priority + text match bonus 