"""
Unit tests for AudioCodes mock client message handler.

This module tests the WebSocket message processing and event handling
for the AudioCodes mock client.
"""

import pytest
from unittest.mock import Mock, patch
import json

from opusagent.local.audiocodes.models import (
    SessionConfig,
    SessionStatus,
    StreamStatus,
    MessageType,
    ConversationState,
)
from opusagent.local.audiocodes.session_manager import SessionManager
from opusagent.local.audiocodes.message_handler import MessageHandler


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
    def message_handler(self, session_manager):
        """Create a test message handler."""
        return MessageHandler(session_manager)

    def test_message_handler_initialization(self, message_handler, session_manager):
        """Test MessageHandler initialization."""
        assert message_handler.session_manager == session_manager
        assert message_handler.received_messages == []
        assert len(message_handler.event_handlers) > 0

    def test_register_event_handler(self, message_handler):
        """Test registering custom event handlers."""
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
            "type": "session.accepted",
            "conversationId": "test-123",
            "mediaFormat": "raw/lpcm16"
        })
        
        event = message_handler.process_message(message)
        
        assert event is not None
        assert event.type == MessageType.SESSION_ACCEPTED
        assert event.conversation_id == "test-123"
        assert len(message_handler.received_messages) == 1
        assert message_handler.received_messages[0]["type"] == "session.accepted"

    def test_process_message_bytes(self, message_handler):
        """Test processing message as bytes."""
        message = json.dumps({
            "type": "session.accepted",
            "conversationId": "test-123"
        }).encode('utf-8')
        
        event = message_handler.process_message(message)
        
        assert event is not None
        assert event.type == MessageType.SESSION_ACCEPTED

    def test_process_message_bytearray(self, message_handler):
        """Test processing message as bytearray."""
        message = bytearray(json.dumps({
            "type": "session.accepted",
            "conversationId": "test-123"
        }).encode('utf-8'))
        
        event = message_handler.process_message(message)
        
        assert event is not None
        assert event.type == MessageType.SESSION_ACCEPTED

    def test_process_message_invalid_json(self, message_handler):
        """Test processing invalid JSON message."""
        message = "invalid json message"
        
        event = message_handler.process_message(message)
        
        assert event is None
        assert len(message_handler.received_messages) == 0

    def test_process_message_no_type(self, message_handler):
        """Test processing message without type field."""
        message = json.dumps({
            "conversationId": "test-123",
            "data": "some data"
        })
        
        event = message_handler.process_message(message)
        
        assert event is None
        assert len(message_handler.received_messages) == 0

    def test_process_message_exception_handling(self, message_handler):
        """Test exception handling during message processing."""
        # Mock a handler that raises an exception
        def failing_handler(data):
            raise ValueError("Handler error")
        
        message_handler.register_event_handler("session.accepted", failing_handler)
        
        message = json.dumps({
            "type": "session.accepted",
            "conversationId": "test-123"
        })
        
        # Should not raise exception, should log error
        event = message_handler.process_message(message)
        
        assert event is not None
        assert event.type.value == "session.accepted"

    def test_handle_user_stream_started(self, message_handler, session_manager):
        """Test handling userStream.started message."""
        session_manager.create_session("test-123")
        
        data = {"conversationId": "test-123"}
        message_handler._handle_user_stream_started(data)
        
        assert session_manager.stream_state.user_stream == StreamStatus.ACTIVE

    def test_handle_user_stream_stopped(self, message_handler, session_manager):
        """Test handling userStream.stopped message."""
        session_manager.create_session("test-123")
        session_manager.stream_state.user_stream = StreamStatus.ACTIVE
        
        data = {"conversationId": "test-123"}
        message_handler._handle_user_stream_stopped(data)
        
        assert session_manager.stream_state.user_stream == StreamStatus.STOPPED

    def test_handle_play_stream_start_greeting(self, message_handler, session_manager):
        """Test handling playStream.start for greeting."""
        session_manager.create_session("test-123")
        
        data = {
            "conversationId": "test-123",
            "streamId": "stream-456"
        }
        message_handler._handle_play_stream_start(data)
        
        assert session_manager.stream_state.play_stream == StreamStatus.ACTIVE
        assert session_manager.stream_state.current_stream_id == "stream-456"
        assert session_manager.conversation_state.collecting_greeting is True
        assert session_manager.conversation_state.collecting_response is False

    def test_handle_play_stream_start_response(self, message_handler, session_manager):
        """Test handling playStream.start for response."""
        session_manager.create_session("test-123")
        # Simulate greeting already collected
        session_manager.conversation_state.greeting_chunks = ["chunk1"]
        
        data = {
            "conversationId": "test-123",
            "streamId": "stream-789"
        }
        message_handler._handle_play_stream_start(data)
        
        assert session_manager.stream_state.play_stream == StreamStatus.ACTIVE
        assert session_manager.stream_state.current_stream_id == "stream-789"
        assert session_manager.conversation_state.collecting_greeting is False
        assert session_manager.conversation_state.collecting_response is True

    def test_handle_play_stream_chunk_greeting(self, message_handler, session_manager):
        """Test handling playStream.chunk for greeting."""
        session_manager.create_session("test-123")
        session_manager.conversation_state.collecting_greeting = True
        
        data = {
            "conversationId": "test-123",
            "audioChunk": "base64_audio_data"
        }
        message_handler._handle_play_stream_chunk(data)
        
        assert len(session_manager.conversation_state.greeting_chunks) == 1
        assert session_manager.conversation_state.greeting_chunks[0] == "base64_audio_data"

    def test_handle_play_stream_chunk_response(self, message_handler, session_manager):
        """Test handling playStream.chunk for response."""
        session_manager.create_session("test-123")
        session_manager.conversation_state.collecting_response = True
        
        data = {
            "conversationId": "test-123",
            "audioChunk": "base64_response_data"
        }
        message_handler._handle_play_stream_chunk(data)
        
        assert len(session_manager.conversation_state.response_chunks) == 1
        assert session_manager.conversation_state.response_chunks[0] == "base64_response_data"

    def test_handle_play_stream_chunk_no_audio(self, message_handler, session_manager):
        """Test handling playStream.chunk without audio data."""
        session_manager.create_session("test-123")
        session_manager.conversation_state.collecting_response = True
        
        data = {
            "conversationId": "test-123"
            # No audioChunk field
        }
        message_handler._handle_play_stream_chunk(data)
        
        assert len(session_manager.conversation_state.response_chunks) == 0

    def test_handle_play_stream_stop_greeting(self, message_handler, session_manager):
        """Test handling playStream.stop for greeting."""
        session_manager.create_session("test-123")
        session_manager.conversation_state.collecting_greeting = True
        session_manager.conversation_state.greeting_chunks = ["chunk1", "chunk2"]
        
        data = {"conversationId": "test-123"}
        message_handler._handle_play_stream_stop(data)
        
        assert session_manager.conversation_state.collecting_greeting is False
        assert session_manager.stream_state.play_stream == StreamStatus.INACTIVE

    def test_handle_play_stream_stop_response(self, message_handler, session_manager):
        """Test handling playStream.stop for response."""
        session_manager.create_session("test-123")
        session_manager.conversation_state.collecting_response = True
        session_manager.conversation_state.response_chunks = ["chunk1", "chunk2", "chunk3"]
        
        data = {"conversationId": "test-123"}
        message_handler._handle_play_stream_stop(data)
        
        assert session_manager.conversation_state.collecting_response is False
        assert session_manager.stream_state.play_stream == StreamStatus.STOPPED
        assert session_manager.stream_state.current_stream_id is None

    def test_handle_activities(self, message_handler, session_manager):
        """Test handling activities message."""
        session_manager.create_session("test-123")
        
        activities = [
            {"type": "event", "name": "test_event1"},
            {"type": "event", "name": "test_event2"}
        ]
        data = {
            "conversationId": "test-123",
            "activities": activities
        }
        message_handler._handle_activities(data)
        
        assert len(session_manager.conversation_state.activities_received) == 2
        assert session_manager.conversation_state.last_activity == activities[1]

    def test_handle_activities_empty(self, message_handler, session_manager):
        """Test handling activities message with empty activities."""
        session_manager.create_session("test-123")
        
        data = {
            "conversationId": "test-123",
            "activities": []
        }
        message_handler._handle_activities(data)
        
        assert len(session_manager.conversation_state.activities_received) == 0
        assert session_manager.conversation_state.last_activity is None

    def test_handle_speech_started(self, message_handler, session_manager):
        """Test handling userStream.speech.started message."""
        session_manager.create_session("test-123")
        
        data = {"conversationId": "test-123"}
        message_handler._handle_speech_started(data)
        
        assert session_manager.stream_state.speech_active is True

    def test_handle_speech_stopped(self, message_handler, session_manager):
        """Test handling userStream.speech.stopped message."""
        session_manager.create_session("test-123")
        session_manager.stream_state.speech_active = True
        
        data = {"conversationId": "test-123"}
        message_handler._handle_speech_stopped(data)
        
        assert session_manager.stream_state.speech_active is False

    def test_handle_speech_committed(self, message_handler, session_manager):
        """Test handling userStream.speech.committed message."""
        session_manager.create_session("test-123")
        
        data = {"conversationId": "test-123"}
        message_handler._handle_speech_committed(data)
        
        assert session_manager.stream_state.speech_committed is True

    def test_handle_speech_hypothesis(self, message_handler, session_manager):
        """Test handling userStream.speech.hypothesis message."""
        session_manager.create_session("test-123")
        
        alternatives = [
            {"text": "hello world", "confidence": 0.9},
            {"text": "hello word", "confidence": 0.7}
        ]
        data = {
            "conversationId": "test-123",
            "alternatives": alternatives
        }
        message_handler._handle_speech_hypothesis(data)
        
        assert session_manager.stream_state.current_hypothesis == alternatives

    def test_get_received_messages(self, message_handler):
        """Test getting received messages."""
        # Process some messages
        messages = [
            {"type": "session.accepted", "conversationId": "test-1"},
            {"type": "session.error", "conversationId": "test-2"}
        ]
        
        for msg in messages:
            message_handler.process_message(json.dumps(msg))
        
        received = message_handler.get_received_messages()
        
        assert len(received) == 2
        assert received[0]["type"] == "session.accepted"
        assert received[1]["type"] == "session.error"

    def test_get_message_count(self, message_handler):
        """Test getting message count."""
        assert message_handler.get_message_count() == 0
        
        message_handler.process_message(json.dumps({
            "type": "session.accepted",
            "conversationId": "test-123"
        }))
        
        assert message_handler.get_message_count() == 1

    def test_clear_message_history(self, message_handler):
        """Test clearing message history."""
        # Add some messages
        message_handler.process_message(json.dumps({
            "type": "session.accepted",
            "conversationId": "test-123"
        }))
        
        assert message_handler.get_message_count() == 1
        
        message_handler.clear_message_history()
        
        assert message_handler.get_message_count() == 0
        assert message_handler.received_messages == []

    def test_get_last_message(self, message_handler):
        """Test getting last message."""
        # Initially no messages
        assert message_handler.get_last_message() is None
        
        # Add a message
        message = {"type": "session.accepted", "conversationId": "test-123"}
        message_handler.process_message(json.dumps(message))
        
        last_message = message_handler.get_last_message()
        assert last_message["type"] == "session.accepted"
        assert last_message["conversationId"] == "test-123"

    def test_get_messages_by_type(self, message_handler):
        """Test getting messages by type."""
        # Add messages of different types
        messages = [
            {"type": "session.accepted", "conversationId": "test-1"},
            {"type": "session.error", "conversationId": "test-2"},
            {"type": "session.accepted", "conversationId": "test-3"}
        ]
        
        for msg in messages:
            message_handler.process_message(json.dumps(msg))
        
        accepted_messages = message_handler.get_messages_by_type("session.accepted")
        assert len(accepted_messages) == 2
        
        error_messages = message_handler.get_messages_by_type("session.error")
        assert len(error_messages) == 1
        
        # Non-existent type
        none_messages = message_handler.get_messages_by_type("nonexistent.type")
        assert len(none_messages) == 0

    # ===== AUDIO PLAYBACK INTEGRATION TESTS =====

    def test_play_stream_chunk_with_audio_playback_handler(self, message_handler, session_manager):
        """Test playStream.chunk handling with audio playback integration."""
        session_manager.create_session("test-123")
        session_manager.conversation_state.collecting_response = True
        
        # Mock audio playback handler
        audio_handler_called = False
        audio_chunk_received = None
        
        def mock_audio_handler(data):
            nonlocal audio_handler_called, audio_chunk_received
            audio_handler_called = True
            audio_chunk_received = data.get("audioChunk")
        
        # Register the audio playback handler
        message_handler.register_event_handler("playStream.chunk", mock_audio_handler)
        
        # Process playStream.chunk message using process_message
        data = {
            "type": "playStream.chunk",
            "conversationId": "test-123",
            "audioChunk": "dGVzdF9hdWRpb19kYXRh"
        }
        message_handler.process_message(json.dumps(data))
        
        # Verify audio handler was called
        assert audio_handler_called is True
        assert audio_chunk_received == "dGVzdF9hdWRpb19kYXRh"
        
        # Verify conversation state was updated
        assert len(session_manager.conversation_state.response_chunks) == 1
        assert session_manager.conversation_state.response_chunks[0] == "dGVzdF9hdWRpb19kYXRh"

    def test_play_stream_chunk_multiple_handlers(self, message_handler, session_manager):
        """Test playStream.chunk handling with multiple handlers."""
        session_manager.create_session("test-123")
        session_manager.conversation_state.collecting_response = True
        
        # Mock multiple handlers
        handler1_called = False
        handler2_called = False
        
        def handler1(data):
            nonlocal handler1_called
            handler1_called = True
        
        def handler2(data):
            nonlocal handler2_called
            handler2_called = True
        
        # Register multiple handlers
        message_handler.register_event_handler("playStream.chunk", handler1)
        message_handler.register_event_handler("playStream.chunk", handler2)
        
        # Process playStream.chunk message using process_message
        data = {
            "type": "playStream.chunk",
            "conversationId": "test-123",
            "audioChunk": "dGVzdF9hdWRpb19kYXRh"
        }
        message_handler.process_message(json.dumps(data))
        
        # Verify both handlers were called
        assert handler1_called is True
        assert handler2_called is True

    def test_play_stream_chunk_handler_exception(self, message_handler, session_manager):
        """Test playStream.chunk handling when handler raises exception."""
        session_manager.create_session("test-123")
        session_manager.conversation_state.collecting_response = True
        
        # Mock handler that raises exception
        def failing_handler(data):
            raise ValueError("Audio handler error")
        
        # Register the failing handler
        message_handler.register_event_handler("playStream.chunk", failing_handler)
        
        # Process playStream.chunk message - should not raise exception
        data = {
            "type": "playStream.chunk",
            "conversationId": "test-123",
            "audioChunk": "dGVzdF9hdWRpb19kYXRh"
        }
        
        # Should not raise exception, should log error
        message_handler.process_message(json.dumps(data))
        
        # Verify conversation state was still updated despite handler error
        assert len(session_manager.conversation_state.response_chunks) == 1

    def test_play_stream_chunk_no_audio_playback_handler(self, message_handler, session_manager):
        """Test playStream.chunk handling without audio playback handler."""
        session_manager.create_session("test-123")
        session_manager.conversation_state.collecting_response = True
        
        # Process playStream.chunk message without any custom handlers
        data = {
            "type": "playStream.chunk",
            "conversationId": "test-123",
            "audioChunk": "dGVzdF9hdWRpb19kYXRh"
        }
        message_handler.process_message(json.dumps(data))
        
        # Verify conversation state was updated (default behavior)
        assert len(session_manager.conversation_state.response_chunks) == 1
        assert session_manager.conversation_state.response_chunks[0] == "dGVzdF9hdWRpb19kYXRh"

    def test_play_stream_chunk_with_metadata(self, message_handler, session_manager):
        """Test playStream.chunk handling with additional metadata."""
        session_manager.create_session("test-123")
        session_manager.conversation_state.collecting_response = True
        
        # Mock audio playback handler
        handler_called = False
        received_data = None
        
        def mock_audio_handler(data):
            nonlocal handler_called, received_data
            handler_called = True
            received_data = data
        
        # Register the audio playback handler
        message_handler.register_event_handler("playStream.chunk", mock_audio_handler)
        
        # Process playStream.chunk message with metadata
        data = {
            "type": "playStream.chunk",
            "conversationId": "test-123",
            "audioChunk": "dGVzdF9hdWRpb19kYXRh",
            "timestamp": 1234567890,
            "sequenceNumber": 42,
            "metadata": {"quality": "high", "format": "pcm16"}
        }
        message_handler.process_message(json.dumps(data))
        
        # Verify handler was called with full data
        assert handler_called is True
        assert received_data is not None
        assert received_data["audioChunk"] == "dGVzdF9hdWRpb19kYXRh"
        assert received_data["timestamp"] == 1234567890
        assert received_data["sequenceNumber"] == 42
        assert received_data["metadata"]["quality"] == "high"

    def test_play_stream_chunk_handler_chain(self, message_handler, session_manager):
        """Test playStream.chunk handling with handler chain."""
        session_manager.create_session("test-123")
        session_manager.conversation_state.collecting_response = True
        
        # Mock handler chain
        handler_chain = []
        
        def handler1(data):
            handler_chain.append("handler1")
            data["processed_by_handler1"] = True
        
        def handler2(data):
            handler_chain.append("handler2")
            data["processed_by_handler2"] = True
        
        def handler3(data):
            handler_chain.append("handler3")
            data["processed_by_handler3"] = True
        
        # Register handlers in order
        message_handler.register_event_handler("playStream.chunk", handler1)
        message_handler.register_event_handler("playStream.chunk", handler2)
        message_handler.register_event_handler("playStream.chunk", handler3)
        
        # Process playStream.chunk message
        data = {
            "type": "playStream.chunk",
            "conversationId": "test-123",
            "audioChunk": "dGVzdF9hdWRpb19kYXRh"
        }
        message_handler.process_message(json.dumps(data))
        
        # Verify handlers were called in order
        assert handler_chain == ["handler1", "handler2", "handler3"]
        
        # Verify data was modified by handlers by checking the processed message
        processed_messages = message_handler.get_received_messages()
        assert len(processed_messages) == 1
        
        processed_data = processed_messages[0]
        assert processed_data["processed_by_handler1"] is True
        assert processed_data["processed_by_handler2"] is True
        assert processed_data["processed_by_handler3"] is True 