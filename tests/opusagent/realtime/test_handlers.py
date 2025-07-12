"""
Unit tests for opusagent.mock.realtime.handlers module.
"""

import pytest
import asyncio
import json
import base64
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from opusagent.mock.realtime.handlers import EventHandlerManager
from opusagent.models.openai_api import (
    ClientEventType,
    ServerEventType,
    SessionConfig
)


class TestEventHandlerManager:
    """Test EventHandlerManager class."""

    def test_event_handler_manager_creation(self):
        """Test basic EventHandlerManager creation."""
        logger = Mock()
        session_config = SessionConfig()
        
        handler = EventHandlerManager(logger, session_config)
        
        assert handler.logger == logger
        assert handler._session_config == session_config
        # Default handlers are registered automatically
        assert len(handler._event_handlers) > 0
        assert handler._ws is None
        assert "session_id" in handler._session_state
        assert "conversation_id" in handler._session_state

    def test_event_handler_manager_creation_without_params(self):
        """Test EventHandlerManager creation without parameters."""
        handler = EventHandlerManager()
        
        assert handler.logger is not None
        assert handler._session_config is None
        # Default handlers are registered automatically
        assert len(handler._event_handlers) > 0
        assert handler._ws is None
        assert "session_id" in handler._session_state

    def test_register_event_handler(self):
        """Test event handler registration."""
        handler = EventHandlerManager()
        
        async def test_handler(data):
            pass
        
        handler.register_event_handler("test.event", test_handler)
        
        assert "test.event" in handler._event_handlers
        assert len(handler._event_handlers["test.event"]) == 1
        assert handler._event_handlers["test.event"][0] == test_handler

    def test_register_multiple_handlers(self):
        """Test registering multiple handlers for the same event."""
        handler = EventHandlerManager()
        
        async def handler1(data):
            pass
        
        async def handler2(data):
            pass
        
        handler.register_event_handler("test.event", handler1)
        handler.register_event_handler("test.event", handler2)
        
        assert len(handler._event_handlers["test.event"]) == 2
        assert handler._event_handlers["test.event"][0] == handler1
        assert handler._event_handlers["test.event"][1] == handler2

    def test_set_websocket_connection(self):
        """Test setting WebSocket connection."""
        handler = EventHandlerManager()
        ws_connection = Mock()
        
        handler.set_websocket_connection(ws_connection)
        
        assert handler._ws == ws_connection

    def test_get_session_state(self):
        """Test getting session state."""
        handler = EventHandlerManager()
        
        state = handler.get_session_state()
        
        assert isinstance(state, dict)
        assert "session_id" in state
        assert "conversation_id" in state
        assert "connected" in state
        assert "active_response_id" in state
        assert "speech_detected" in state
        assert "audio_buffer" in state

    def test_update_session_state(self):
        """Test updating session state."""
        handler = EventHandlerManager()
        
        updates = {"test_key": "test_value", "another_key": 123}
        handler.update_session_state(updates)
        
        state = handler.get_session_state()
        assert state["test_key"] == "test_value"
        assert state["another_key"] == 123

    @pytest.mark.asyncio
    async def test_handle_message_valid_json(self):
        """Test handling valid JSON message."""
        handler = EventHandlerManager()
        
        # Register a test handler
        handler_called = False
        handler_data = None
        
        async def test_handler(data):
            nonlocal handler_called, handler_data
            handler_called = True
            handler_data = data
        
        handler.register_event_handler("test.event", test_handler)
        
        message = json.dumps({"type": "test.event", "data": "test_value"})
        await handler.handle_message(message)
        
        assert handler_called
        assert handler_data is not None
        assert handler_data["type"] == "test.event"
        assert handler_data["data"] == "test_value"

    @pytest.mark.asyncio
    async def test_handle_message_invalid_json(self):
        """Test handling invalid JSON message."""
        handler = EventHandlerManager()
        logger = Mock()
        handler.logger = logger
        
        message = "invalid json message"
        await handler.handle_message(message)
        
        logger.warning.assert_called_with("[MOCK REALTIME] Received non-JSON message: invalid json message")

    @pytest.mark.asyncio
    async def test_handle_message_no_handler(self):
        """Test handling message with no registered handler."""
        handler = EventHandlerManager()
        logger = Mock()
        handler.logger = logger
        
        message = json.dumps({"type": "unknown.event", "data": "test"})
        await handler.handle_message(message)
        
        logger.warning.assert_called_with("[MOCK REALTIME] No handler for event type: unknown.event")

    @pytest.mark.asyncio
    async def test_handle_message_exception(self):
        """Test handling message with handler exception."""
        handler = EventHandlerManager()
        logger = Mock()
        handler.logger = logger
        
        async def failing_handler(data):
            raise Exception("Handler error")
        
        handler.register_event_handler("test.event", failing_handler)
        
        message = json.dumps({"type": "test.event", "data": "test"})
        await handler.handle_message(message)
        
        logger.error.assert_called_with("[MOCK REALTIME] Error processing message: Handler error")

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_send_event_success(self, mock_websocket_utils):
        """Test successful event sending."""
        handler = EventHandlerManager()
        handler._ws = Mock()
        
        mock_websocket_utils.safe_send_event.return_value = asyncio.Future()
        mock_websocket_utils.safe_send_event.return_value.set_result(True)
        
        event = {"type": "test.event", "data": "test"}
        await handler._send_event(event)
        
        mock_websocket_utils.safe_send_event.assert_called_once_with(
            handler._ws, event, handler.logger
        )

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_send_event_failure(self, mock_websocket_utils):
        """Test event sending failure."""
        handler = EventHandlerManager()
        handler._ws = Mock()
        
        mock_websocket_utils.safe_send_event.return_value = asyncio.Future()
        mock_websocket_utils.safe_send_event.return_value.set_result(False)
        
        event = {"type": "test.event", "data": "test"}
        
        with pytest.raises(Exception, match="Failed to send event to WebSocket"):
            await handler._send_event(event)

    def test_register_default_handlers(self):
        """Test that default handlers are registered."""
        handler = EventHandlerManager()
        
        # Check that default handlers are registered
        expected_events = [
            ClientEventType.SESSION_UPDATE,
            ClientEventType.INPUT_AUDIO_BUFFER_APPEND,
            ClientEventType.INPUT_AUDIO_BUFFER_COMMIT,
            ClientEventType.INPUT_AUDIO_BUFFER_CLEAR,
            ClientEventType.RESPONSE_CREATE,
            ClientEventType.RESPONSE_CANCEL
        ]
        
        for event_type in expected_events:
            assert event_type in handler._event_handlers
            assert len(handler._event_handlers[event_type]) > 0

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_handle_session_update(self, mock_websocket_utils):
        """Test session update handling."""
        handler = EventHandlerManager()
        handler._ws = Mock()
        handler._session_config = SessionConfig()
        
        mock_websocket_utils.safe_send_event.return_value = asyncio.Future()
        mock_websocket_utils.safe_send_event.return_value.set_result(True)
        
        session_data = {
            "model": "gpt-4o-realtime-preview-2025-06-03",
            "voice": "nova",
            "temperature": 0.7
        }
        
        data = {"session": session_data}
        await handler._handle_session_update(data)
        
        # Check that session config was updated
        assert handler._session_config.model == "gpt-4o-realtime-preview-2025-06-03"
        assert handler._session_config.voice == "nova"
        assert handler._session_config.temperature == 0.7
        
        # Check that session.updated event was sent
        mock_websocket_utils.safe_send_event.assert_called_once()
        sent_event = mock_websocket_utils.safe_send_event.call_args[0][1]
        assert sent_event["type"] == ServerEventType.SESSION_UPDATED
        assert sent_event["session"] == session_data

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_handle_session_update_no_config(self, mock_websocket_utils):
        """Test session update handling without session config."""
        handler = EventHandlerManager()
        handler._ws = Mock()
        handler._session_config = None
        
        mock_websocket_utils.safe_send_event.return_value = asyncio.Future()
        mock_websocket_utils.safe_send_event.return_value.set_result(True)
        
        data = {"session": {"model": "test-model"}}
        await handler._handle_session_update(data)
        
        # Should still send session.updated event
        mock_websocket_utils.safe_send_event.assert_called_once()
        sent_event = mock_websocket_utils.safe_send_event.call_args[0][1]
        assert sent_event["type"] == ServerEventType.SESSION_UPDATED

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_handle_audio_append(self, mock_websocket_utils):
        """Test audio append handling."""
        handler = EventHandlerManager()
        handler._ws = Mock()
        
        mock_websocket_utils.safe_send_event.return_value = asyncio.Future()
        mock_websocket_utils.safe_send_event.return_value.set_result(True)
        
        # Test with valid audio data
        audio_data = base64.b64encode(b"test_audio_data").decode("utf-8")
        data = {"audio": audio_data}
        
        await handler._handle_audio_append(data)
        
        # Check that audio was added to buffer
        assert len(handler._session_state["audio_buffer"]) == 1
        assert handler._session_state["audio_buffer"][0] == b"test_audio_data"

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_handle_audio_append_speech_detection(self, mock_websocket_utils):
        """Test audio append with speech detection."""
        handler = EventHandlerManager()
        handler._ws = Mock()
        
        mock_websocket_utils.safe_send_event.return_value = asyncio.Future()
        mock_websocket_utils.safe_send_event.return_value.set_result(True)
        
        # Add enough audio chunks to trigger speech detection
        audio_data = base64.b64encode(b"test_audio_data").decode("utf-8")
        data = {"audio": audio_data}
        
        # Add 11 chunks (more than 10 to trigger speech detection)
        for _ in range(11):
            await handler._handle_audio_append(data)
        
        # Check that speech detection was triggered
        assert handler._session_state["speech_detected"] is True
        
        # Check that speech started event was sent
        mock_websocket_utils.safe_send_event.assert_called()
        sent_events = [call[0][1] for call in mock_websocket_utils.safe_send_event.call_args_list]
        speech_events = [event for event in sent_events if event["type"] == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED]
        assert len(speech_events) == 1

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_handle_audio_append_invalid_data(self, mock_websocket_utils):
        """Test audio append with invalid data."""
        handler = EventHandlerManager()
        handler._ws = Mock()
        logger = Mock()
        handler.logger = logger
        
        mock_websocket_utils.safe_send_event.return_value = asyncio.Future()
        mock_websocket_utils.safe_send_event.return_value.set_result(True)
        
        # Test with invalid base64 data
        data = {"audio": "invalid_base64_data"}
        
        await handler._handle_audio_append(data)
        
        # The actual error message includes the specific base64 error details
        logger.error.assert_called_with("[MOCK REALTIME] Error processing audio data: Invalid base64-encoded string: number of data characters (17) cannot be 1 more than a multiple of 4")

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_handle_audio_commit(self, mock_websocket_utils):
        """Test audio commit handling."""
        handler = EventHandlerManager()
        handler._ws = Mock()
        
        mock_websocket_utils.safe_send_event.return_value = asyncio.Future()
        mock_websocket_utils.safe_send_event.return_value.set_result(True)
        
        # Add some audio to buffer
        handler._session_state["audio_buffer"] = [b"chunk1", b"chunk2"]
        handler._session_state["speech_detected"] = True
        
        data = {}
        await handler._handle_audio_commit(data)
        
        # Check that buffer was cleared
        assert len(handler._session_state["audio_buffer"]) == 0
        assert handler._session_state["speech_detected"] is False
        
        # Check that committed event was sent
        mock_websocket_utils.safe_send_event.assert_called_once()
        sent_event = mock_websocket_utils.safe_send_event.call_args[0][1]
        assert sent_event["type"] == ServerEventType.INPUT_AUDIO_BUFFER_COMMITTED
        assert "item_id" in sent_event

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_handle_audio_commit_empty_buffer(self, mock_websocket_utils):
        """Test audio commit with empty buffer."""
        handler = EventHandlerManager()
        handler._ws = Mock()
        logger = Mock()
        handler.logger = logger
        
        mock_websocket_utils.safe_send_event.return_value = asyncio.Future()
        mock_websocket_utils.safe_send_event.return_value.set_result(True)
        
        # Ensure buffer is empty
        handler._session_state["audio_buffer"] = []
        
        data = {}
        await handler._handle_audio_commit(data)
        
        logger.warning.assert_called_with("[MOCK REALTIME] Attempted to commit empty audio buffer")

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_handle_audio_clear(self, mock_websocket_utils):
        """Test audio clear handling."""
        handler = EventHandlerManager()
        handler._ws = Mock()
        
        mock_websocket_utils.safe_send_event.return_value = asyncio.Future()
        mock_websocket_utils.safe_send_event.return_value.set_result(True)
        
        # Add some audio to buffer
        handler._session_state["audio_buffer"] = [b"chunk1", b"chunk2"]
        handler._session_state["speech_detected"] = True
        
        data = {}
        await handler._handle_audio_clear(data)
        
        # Check that buffer was cleared
        assert len(handler._session_state["audio_buffer"]) == 0
        assert handler._session_state["speech_detected"] is False
        
        # Check that cleared event was sent
        mock_websocket_utils.safe_send_event.assert_called_once()
        sent_event = mock_websocket_utils.safe_send_event.call_args[0][1]
        assert sent_event["type"] == ServerEventType.INPUT_AUDIO_BUFFER_CLEARED

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_handle_response_create(self, mock_websocket_utils):
        """Test response create handling."""
        handler = EventHandlerManager()
        handler._ws = Mock()
        
        mock_websocket_utils.safe_send_event.return_value = asyncio.Future()
        mock_websocket_utils.safe_send_event.return_value.set_result(True)
        
        response_data = {"model": "gpt-4o-realtime-preview-2025-06-03"}
        data = {"response": response_data}
        
        await handler._handle_response_create(data)
        
        # Check that active response ID was set
        assert handler._session_state["active_response_id"] is not None
        
        # Check that response.created event was sent
        mock_websocket_utils.safe_send_event.assert_called_once()
        sent_event = mock_websocket_utils.safe_send_event.call_args[0][1]
        assert sent_event["type"] == ServerEventType.RESPONSE_CREATED
        assert "response" in sent_event
        assert "id" in sent_event["response"]
        assert "created_at" in sent_event["response"]

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_handle_response_cancel(self, mock_websocket_utils):
        """Test response cancel handling."""
        handler = EventHandlerManager()
        handler._ws = Mock()
        
        mock_websocket_utils.safe_send_event.return_value = asyncio.Future()
        mock_websocket_utils.safe_send_event.return_value.set_result(True)
        
        # Set active response ID
        response_id = "test_response_123"
        handler._session_state["active_response_id"] = response_id
        
        data = {"response_id": response_id}
        await handler._handle_response_cancel(data)
        
        # Check that active response ID was cleared
        assert handler._session_state["active_response_id"] is None
        
        # Check that response.cancelled event was sent
        mock_websocket_utils.safe_send_event.assert_called_once()
        sent_event = mock_websocket_utils.safe_send_event.call_args[0][1]
        assert sent_event["type"] == ServerEventType.RESPONSE_CANCELLED
        assert sent_event["response_id"] == response_id

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_handle_response_cancel_wrong_id(self, mock_websocket_utils):
        """Test response cancel with wrong response ID."""
        handler = EventHandlerManager()
        handler._ws = Mock()
        logger = Mock()
        handler.logger = logger
        
        mock_websocket_utils.safe_send_event.return_value = asyncio.Future()
        mock_websocket_utils.safe_send_event.return_value.set_result(True)
        
        # Set active response ID
        handler._session_state["active_response_id"] = "active_response_123"
        
        data = {"response_id": "wrong_response_456"}
        await handler._handle_response_cancel(data)
        
        # Check that active response ID was not cleared
        assert handler._session_state["active_response_id"] == "active_response_123"
        
        # Check that no event was sent
        mock_websocket_utils.safe_send_event.assert_not_called()
        
        logger.warning.assert_called_with("[MOCK REALTIME] Attempted to cancel non-active response: wrong_response_456")

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_send_session_created(self, mock_websocket_utils):
        """Test sending session created event."""
        handler = EventHandlerManager()
        handler._ws = Mock()
        handler._session_config = SessionConfig(
            model="gpt-4o-realtime-preview-2025-06-03",
            modalities=["text", "audio"],
            voice="alloy"
        )
        
        mock_websocket_utils.safe_send_event.return_value = asyncio.Future()
        mock_websocket_utils.safe_send_event.return_value.set_result(True)
        
        await handler.send_session_created()
        
        # Check that session.created event was sent
        mock_websocket_utils.safe_send_event.assert_called_once()
        sent_event = mock_websocket_utils.safe_send_event.call_args[0][1]
        assert sent_event["type"] == ServerEventType.SESSION_CREATED
        assert "session" in sent_event
        assert sent_event["session"]["model"] == "gpt-4o-realtime-preview-2025-06-03"
        assert sent_event["session"]["voice"] == "alloy"
        assert "id" in sent_event["session"]
        assert "created_at" in sent_event["session"]

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_send_session_created_no_config(self, mock_websocket_utils):
        """Test sending session created event without session config."""
        handler = EventHandlerManager()
        handler._ws = Mock()
        handler._session_config = None
        logger = Mock()
        handler.logger = logger
        
        mock_websocket_utils.safe_send_event.return_value = asyncio.Future()
        mock_websocket_utils.safe_send_event.return_value.set_result(True)
        
        await handler.send_session_created()
        
        logger.error.assert_called_with("[MOCK REALTIME] No session config available for session.created")
        mock_websocket_utils.safe_send_event.assert_not_called()

    def test_session_state_initialization(self):
        """Test session state initialization."""
        handler = EventHandlerManager()
        
        state = handler._session_state
        
        # Check required fields
        assert "session_id" in state
        assert "conversation_id" in state
        assert "connected" in state
        assert "active_response_id" in state
        assert "speech_detected" in state
        assert "audio_buffer" in state
        assert "response_audio" in state
        assert "response_text" in state
        
        # Check default values
        assert state["connected"] is False
        assert state["active_response_id"] is None
        assert state["speech_detected"] is False
        assert state["audio_buffer"] == []
        assert state["response_audio"] == []
        assert state["response_text"] == ""
        
        # Check that IDs are UUIDs
        import uuid
        try:
            uuid.UUID(state["session_id"])
            uuid.UUID(state["conversation_id"])
        except ValueError:
            pytest.fail("Session and conversation IDs should be valid UUIDs")

    @pytest.mark.asyncio
    async def test_custom_event_handler_integration(self):
        """Test integration with custom event handlers."""
        handler = EventHandlerManager()
        
        # Register custom handler
        custom_handler_called = False
        custom_handler_data = None
        
        async def custom_handler(data):
            nonlocal custom_handler_called, custom_handler_data
            custom_handler_called = True
            custom_handler_data = data
        
        handler.register_event_handler("custom.event", custom_handler)
        
        # Send message that should trigger custom handler
        message = json.dumps({"type": "custom.event", "data": "custom_value"})
        await handler.handle_message(message)
        
        assert custom_handler_called
        assert custom_handler_data is not None
        assert custom_handler_data["type"] == "custom.event"
        assert custom_handler_data["data"] == "custom_value" 