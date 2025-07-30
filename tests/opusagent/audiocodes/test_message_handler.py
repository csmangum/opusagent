"""
Unit tests for AudioCodes mock client message handler.

This module tests the WebSocket message processing and event handling
for the AudioCodes mock client.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from opusagent.local.audiocodes.models import (
    SessionConfig,
    ConversationState,
    MessageEvent,
    MessageType,
    StreamStatus,
)
from opusagent.local.audiocodes.session_manager import SessionManager
from opusagent.local.audiocodes.message_handler import MessageHandler
from opusagent.local.audiocodes.conversation_manager import ConversationManager
from opusagent.local.audiocodes.audio_manager import AudioManager


class TestMessageHandler:
    """Test MessageHandler class."""

    @pytest.fixture
    def config(self):
        """Create a test session configuration."""
        return SessionConfig(
            bridge_url="ws://localhost:8080",
            bot_name="TestBot",
            caller="+15551234567"
        )

    @pytest.fixture
    def session_manager(self, config):
        """Create a test session manager."""
        return SessionManager(config)

    @pytest.fixture
    def audio_manager(self):
        """Create a test audio manager."""
        return AudioManager()

    @pytest.fixture
    def conversation_manager(self, session_manager, audio_manager):
        """Create a test conversation manager."""
        return ConversationManager(session_manager, audio_manager)

    @pytest.fixture
    def message_handler(self, session_manager):
        """Create a test message handler."""
        return MessageHandler(session_manager)

    @pytest.fixture
    def message_handler_with_conversation(self, session_manager, conversation_manager):
        """Create a test message handler with conversation manager."""
        # Set the conversation manager in session manager
        session_manager.set_conversation_manager(conversation_manager)
        return MessageHandler(session_manager)

    def test_message_handler_initialization(self, message_handler, session_manager):
        """Test MessageHandler initialization."""
        assert message_handler.session_manager == session_manager
        assert message_handler.received_messages == []
        # The event_handlers dictionary is populated with default handlers during initialization
        assert len(message_handler.event_handlers) > 0
        # Verify that default handlers are registered
        expected_handler_types = [
            "session.accepted", "session.resumed", "session.error", "connection.validated",
            "userStream.started", "userStream.stopped", "playStream.start", "playStream.chunk",
            "playStream.stop", "activities", "userStream.speech.started", "userStream.speech.stopped",
            "userStream.speech.committed", "userStream.speech.hypothesis"
        ]
        for handler_type in expected_handler_types:
            assert handler_type in message_handler.event_handlers

    def test_message_handler_with_custom_logger(self, session_manager):
        """Test MessageHandler initialization with custom logger."""
        custom_logger = Mock()
        message_handler = MessageHandler(session_manager, custom_logger)
        
        assert message_handler.logger == custom_logger

    def test_register_event_handler(self, message_handler):
        """Test registering custom event handler."""
        handler_called = False
        
        def test_handler(data):
            nonlocal handler_called
            handler_called = True
        
        message_handler.register_event_handler("test.event", test_handler)
        
        # Trigger the handler
        message_handler._trigger_handlers("test.event", {"test": "data"})
        
        assert handler_called is True

    def test_process_message_valid_json(self, message_handler):
        """Test processing valid JSON message."""
        message = json.dumps({
            "type": "session.accepted",  # Use a valid message type
            "data": {"test": "value"}
        })
        
        result = message_handler.process_message(message)
        
        assert result is not None
        assert result.type == MessageType.SESSION_ACCEPTED
        assert result.data == {"type": "session.accepted", "data": {"test": "value"}}

    def test_process_message_invalid_json(self, message_handler):
        """Test processing invalid JSON message."""
        message = "invalid json"
        
        result = message_handler.process_message(message)
        
        assert result is None

    def test_process_message_missing_type(self, message_handler):
        """Test processing message without type field."""
        message = json.dumps({
            "data": {"test": "value"}
        })
        
        result = message_handler.process_message(message)
        
        assert result is None

    def test_handle_play_stream_stop_greeting(self, message_handler_with_conversation):
        """Test handling play stream stop for greeting collection."""
        # Set up conversation state for greeting collection
        message_handler_with_conversation.session_manager.conversation_state = ConversationState(conversation_id="test-123")
        message_handler_with_conversation.session_manager.conversation_state.collecting_greeting = True
        message_handler_with_conversation.session_manager.conversation_state.greeting_chunks = ["chunk1", "chunk2"]
        
        # Mock the conversation manager notification method
        with patch.object(message_handler_with_conversation.session_manager.conversation_manager, '_notify_greeting_complete') as mock_notify:
            message_handler_with_conversation._handle_play_stream_stop({"streamId": "test-stream"})
            
            # Verify greeting collection was completed
            assert message_handler_with_conversation.session_manager.conversation_state.collecting_greeting is False
            assert message_handler_with_conversation.session_manager.stream_state.play_stream == StreamStatus.INACTIVE
            
            # Verify notification was called
            mock_notify.assert_called_once()

    def test_handle_play_stream_stop_response(self, message_handler_with_conversation):
        """Test handling play stream stop for response collection."""
        # Set up conversation state for response collection
        message_handler_with_conversation.session_manager.conversation_state = ConversationState(conversation_id="test-123")
        message_handler_with_conversation.session_manager.conversation_state.collecting_response = True
        message_handler_with_conversation.session_manager.conversation_state.response_chunks = ["resp1", "resp2"]
        message_handler_with_conversation.session_manager.stream_state.current_stream_id = "test-stream"
        
        # Mock the conversation manager notification method
        with patch.object(message_handler_with_conversation.session_manager.conversation_manager, '_notify_response_complete') as mock_notify:
            message_handler_with_conversation._handle_play_stream_stop({"streamId": "test-stream"})
            
            # Verify response collection was completed
            assert message_handler_with_conversation.session_manager.conversation_state.collecting_response is False
            assert message_handler_with_conversation.session_manager.stream_state.play_stream == StreamStatus.STOPPED
            assert message_handler_with_conversation.session_manager.stream_state.current_stream_id is None
            
            # Verify notification was called
            mock_notify.assert_called_once()

    def test_handle_play_stream_stop_no_collection(self, message_handler_with_conversation):
        """Test handling play stream stop when no collection is active."""
        # Set up conversation state without active collection
        message_handler_with_conversation.session_manager.conversation_state = ConversationState(conversation_id="test-123")
        message_handler_with_conversation.session_manager.conversation_state.collecting_greeting = False
        message_handler_with_conversation.session_manager.conversation_state.collecting_response = False
        
        # Mock the conversation manager notification methods
        with patch.object(message_handler_with_conversation.session_manager.conversation_manager, '_notify_greeting_complete') as mock_greeting_notify:
            with patch.object(message_handler_with_conversation.session_manager.conversation_manager, '_notify_response_complete') as mock_response_notify:
                message_handler_with_conversation._handle_play_stream_stop({"streamId": "test-stream"})
                
                # Verify no notifications were called
                mock_greeting_notify.assert_not_called()
                mock_response_notify.assert_not_called()

    def test_handle_play_stream_stop_no_conversation_state(self, message_handler_with_conversation):
        """Test handling play stream stop without conversation state."""
        # Ensure no conversation state
        message_handler_with_conversation.session_manager.conversation_state = None
        
        # Should not raise exception
        message_handler_with_conversation._handle_play_stream_stop({"streamId": "test-stream"})

    def test_handle_play_stream_stop_no_conversation_manager(self, message_handler):
        """Test handling play stream stop without conversation manager."""
        # Set up conversation state for greeting collection
        message_handler.session_manager.conversation_state = ConversationState(conversation_id="test-123")
        message_handler.session_manager.conversation_state.collecting_greeting = True
        
        # Should not raise exception even without conversation manager
        message_handler._handle_play_stream_stop({"streamId": "test-stream"})
        
        # Verify greeting collection was completed
        assert message_handler.session_manager.conversation_state.collecting_greeting is False

    def test_handle_play_stream_stop_greeting_notification_error(self, message_handler_with_conversation):
        """Test handling play stream stop when greeting notification raises exception."""
        # Set up conversation state for greeting collection
        message_handler_with_conversation.session_manager.conversation_state = ConversationState(conversation_id="test-123")
        message_handler_with_conversation.session_manager.conversation_state.collecting_greeting = True
        
        # Mock the conversation manager notification method to raise exception
        def failing_notify():
            raise ValueError("Test exception")
        
        message_handler_with_conversation.session_manager.conversation_manager._notify_greeting_complete = failing_notify
        
        # Should not raise exception, just log error
        message_handler_with_conversation._handle_play_stream_stop({"streamId": "test-stream"})
        
        # Verify greeting collection was still completed
        assert message_handler_with_conversation.session_manager.conversation_state.collecting_greeting is False

    def test_handle_play_stream_stop_response_notification_error(self, message_handler_with_conversation):
        """Test handling play stream stop when response notification raises exception."""
        # Set up conversation state for response collection
        message_handler_with_conversation.session_manager.conversation_state = ConversationState(conversation_id="test-123")
        message_handler_with_conversation.session_manager.conversation_state.collecting_response = True
        
        # Mock the conversation manager notification method to raise exception
        def failing_notify():
            raise ValueError("Test exception")
        
        message_handler_with_conversation.session_manager.conversation_manager._notify_response_complete = failing_notify
        
        # Should not raise exception, just log error
        message_handler_with_conversation._handle_play_stream_stop({"streamId": "test-stream"})
        
        # Verify response collection was still completed
        assert message_handler_with_conversation.session_manager.conversation_state.collecting_response is False 