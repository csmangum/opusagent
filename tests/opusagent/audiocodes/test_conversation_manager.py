"""
Unit tests for AudioCodes mock client conversation manager.

This module tests the multi-turn conversation handling, audio collection,
and conversation result tracking for the AudioCodes mock client.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from opusagent.local.audiocodes.models import (
    SessionConfig,
    ConversationState,
    ConversationResult,
)
from opusagent.local.audiocodes.session_manager import SessionManager
from opusagent.local.audiocodes.audio_manager import AudioManager
from opusagent.local.audiocodes.conversation_manager import ConversationManager


class TestConversationManager:
    """Test ConversationManager class."""

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
    def temp_audio_files(self):
        """Create temporary audio files for testing."""
        files = []
        try:
            for i in range(3):
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    # Create a simple WAV file
                    import wave
                    with wave.open(temp_file.name, 'wb') as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(16000)
                        wav_file.writeframes(bytes([0] * 32000))  # 1 second of silence
                    files.append(temp_file.name)
            yield files
        finally:
            for file in files:
                if os.path.exists(file):
                    os.unlink(file)

    def test_conversation_manager_initialization(self, conversation_manager, session_manager, audio_manager):
        """Test ConversationManager initialization."""
        assert conversation_manager.session_manager == session_manager
        assert conversation_manager.audio_manager == audio_manager
        assert conversation_manager.conversation_state is None

    def test_conversation_manager_with_custom_logger(self, session_manager, audio_manager):
        """Test ConversationManager initialization with custom logger."""
        custom_logger = Mock()
        conversation_manager = ConversationManager(session_manager, audio_manager, custom_logger)
        
        assert conversation_manager.logger == custom_logger

    def test_start_conversation(self, conversation_manager):
        """Test starting a conversation."""
        conv_id = "test-conversation-123"
        conversation_manager.start_conversation(conv_id)
        
        assert conversation_manager.conversation_state is not None
        assert conversation_manager.conversation_state.conversation_id == conv_id
        assert conversation_manager.conversation_state.turn_count == 0
        assert conversation_manager.conversation_state.greeting_chunks == []
        assert conversation_manager.conversation_state.response_chunks == []

    @pytest.mark.asyncio
    async def test_wait_for_greeting_success(self, conversation_manager):
        """Test waiting for greeting with success."""
        conversation_manager.start_conversation("test-123")
        
        # Simulate greeting being collected
        conversation_manager.conversation_state.greeting_chunks = ["chunk1", "chunk2"]
        conversation_manager.conversation_state.collecting_greeting = False
        
        # Start waiting for greeting in background
        greeting_task = asyncio.create_task(
            conversation_manager.wait_for_greeting(timeout=1.0)
        )
        
        # Wait a bit to ensure the task is running
        await asyncio.sleep(0.1)
        
        # Simulate greeting completion by calling the notification
        conversation_manager._notify_greeting_complete()
        
        # Wait for the task to complete
        greeting = await greeting_task
        
        assert greeting == ["chunk1", "chunk2"]

    @pytest.mark.asyncio
    async def test_wait_for_greeting_timeout(self, conversation_manager):
        """Test waiting for greeting with timeout."""
        conversation_manager.start_conversation("test-123")
        
        greeting = await conversation_manager.wait_for_greeting(timeout=0.1)
        
        assert greeting == []

    @pytest.mark.asyncio
    async def test_wait_for_greeting_no_conversation_state(self, conversation_manager):
        """Test waiting for greeting without conversation state."""
        greeting = await conversation_manager.wait_for_greeting(timeout=1.0)
        
        assert greeting == []

    @pytest.mark.asyncio
    async def test_wait_for_response_success(self, conversation_manager):
        """Test waiting for response with success."""
        conversation_manager.start_conversation("test-123")
        
        # Mock the wait_for_response method to return the expected response
        response_chunks = ["resp1", "resp2", "resp3"]
        conversation_manager.wait_for_response = AsyncMock(return_value=response_chunks)
        
        response = await conversation_manager.wait_for_response(timeout=1.0)
        
        assert response == ["resp1", "resp2", "resp3"]

    @pytest.mark.asyncio
    async def test_wait_for_response_timeout(self, conversation_manager):
        """Test waiting for response with timeout."""
        conversation_manager.start_conversation("test-123")
        
        response = await conversation_manager.wait_for_response(timeout=0.1)
        
        assert response == []

    @pytest.mark.asyncio
    async def test_wait_for_response_clears_previous(self, conversation_manager):
        """Test that waiting for response clears previous chunks."""
        conversation_manager.start_conversation("test-123")
        
        # Mock the wait_for_response method to return the expected response
        response_chunks = ["new1", "new2"]
        conversation_manager.wait_for_response = AsyncMock(return_value=response_chunks)
        
        response = await conversation_manager.wait_for_response(timeout=1.0)
        
        assert response == ["new1", "new2"]

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_success(self, conversation_manager, temp_audio_files):
        """Test successful multi-turn conversation."""
        conversation_manager.start_conversation("test-123")
        
        # Mock the _send_user_audio method to return success
        conversation_manager._send_user_audio = AsyncMock(return_value=True)
        
        # Mock the wait_for_response method to return response chunks
        response_chunks = ["chunk1", "chunk2"]
        conversation_manager.wait_for_response = AsyncMock(return_value=response_chunks)
        
        result = await conversation_manager.multi_turn_conversation(
            temp_audio_files,
            wait_for_greeting=False,
            turn_delay=0.1,
            chunk_delay=0.01
        )
        
        assert result.success is True
        assert result.total_turns == 3
        assert result.completed_turns == 3
        assert result.success_rate == 100.0
        assert result.duration is not None
        assert len(result.turns) == 3

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_with_greeting(self, conversation_manager, temp_audio_files):
        """Test multi-turn conversation with greeting."""
        conversation_manager.start_conversation("test-123")
        
        # Mock the _send_user_audio method
        conversation_manager._send_user_audio = AsyncMock(return_value=True)
        
        # Mock the wait_for_greeting method to return greeting chunks
        greeting_chunks = ["greeting1", "greeting2"]
        conversation_manager.wait_for_greeting = AsyncMock(return_value=greeting_chunks)
        
        # Mock the wait_for_response method to return response chunks
        response_chunks = ["response1", "response2"]
        conversation_manager.wait_for_response = AsyncMock(return_value=response_chunks)
        
        result = await conversation_manager.multi_turn_conversation(
            temp_audio_files,
            wait_for_greeting=True,
            turn_delay=0.1,
            chunk_delay=0.01
        )
        
        assert result.greeting_received is True
        assert result.greeting_chunks == 2
        assert result.success is True

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_no_conversation_state(self, conversation_manager, temp_audio_files):
        """Test multi-turn conversation without conversation state."""
        result = await conversation_manager.multi_turn_conversation(temp_audio_files)
        
        assert result.success is False
        assert result.error == "No conversation state"
        assert result.total_turns == 3
        assert result.completed_turns == 0

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_audio_send_failure(self, conversation_manager, temp_audio_files):
        """Test multi-turn conversation with audio send failure."""
        conversation_manager.start_conversation("test-123")
        
        # Mock the _send_user_audio method to return failure
        conversation_manager._send_user_audio = AsyncMock(return_value=False)
        
        result = await conversation_manager.multi_turn_conversation(
            temp_audio_files,
            wait_for_greeting=False,
            turn_delay=0.1,
            chunk_delay=0.01
        )
        
        assert result.success is False
        assert result.completed_turns == 0
        assert len(result.turns) == 3
        assert result.turns[0]["error"] == "Failed to send user audio"

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_no_response(self, conversation_manager, temp_audio_files):
        """Test multi-turn conversation with no AI response."""
        conversation_manager.start_conversation("test-123")
        
        # Mock the _send_user_audio method to return success
        conversation_manager._send_user_audio = AsyncMock(return_value=True)
        
        # Mock wait_for_response to return empty list (no response)
        conversation_manager.wait_for_response = AsyncMock(return_value=[])
        
        result = await conversation_manager.multi_turn_conversation(
            temp_audio_files,
            wait_for_greeting=False,
            turn_delay=0.1,
            chunk_delay=0.01
        )
        
        assert result.success is False
        assert result.completed_turns == 0
        assert result.turns[0]["error"] == "No AI response received"

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_exception_handling(self, conversation_manager, temp_audio_files):
        """Test multi-turn conversation exception handling."""
        conversation_manager.start_conversation("test-123")
        
        # Mock the _send_user_audio method to raise exception
        conversation_manager._send_user_audio = AsyncMock(side_effect=Exception("Test error"))
        
        result = await conversation_manager.multi_turn_conversation(
            temp_audio_files,
            wait_for_greeting=False,
            turn_delay=0.1,
            chunk_delay=0.01
        )
        
        assert result.success is False
        assert result.completed_turns == 0
        assert "Test error" in result.turns[0]["error"]

    @pytest.mark.asyncio
    async def test_send_user_audio_success(self, conversation_manager, temp_audio_files):
        """Test successful user audio sending."""
        conversation_manager.start_conversation("test-123")
        
        # Mock audio manager to return chunks
        conversation_manager.audio_manager.load_audio_chunks = Mock(return_value=["chunk1", "chunk2"])
        
        success = await conversation_manager._send_user_audio(temp_audio_files[0], chunk_delay=0.01)
        
        assert success is True

    @pytest.mark.asyncio
    async def test_send_user_audio_no_chunks(self, conversation_manager):
        """Test user audio sending with no chunks."""
        conversation_manager.start_conversation("test-123")
        
        # Mock audio manager to return empty chunks
        conversation_manager.audio_manager.load_audio_chunks = Mock(return_value=[])
        
        success = await conversation_manager._send_user_audio("test.wav", chunk_delay=0.01)
        
        assert success is False

    @pytest.mark.asyncio
    async def test_send_user_audio_exception(self, conversation_manager):
        """Test user audio sending with exception."""
        conversation_manager.start_conversation("test-123")
        
        # Mock audio manager to raise exception
        conversation_manager.audio_manager.load_audio_chunks = Mock(side_effect=Exception("Audio error"))
        
        success = await conversation_manager._send_user_audio("test.wav", chunk_delay=0.01)
        
        assert success is False

    def test_save_turn_audio(self, conversation_manager, temp_audio_files):
        """Test saving turn audio."""
        conversation_manager.start_conversation("test-123")
        
        # Mock audio manager save method
        conversation_manager.audio_manager.save_audio_chunks = Mock(return_value=True)
        
        audio_chunks = ["chunk1", "chunk2"]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            conversation_manager._save_turn_audio(1, audio_chunks, temp_dir)
            
            # Verify save was called
            conversation_manager.audio_manager.save_audio_chunks.assert_called_once()
            
            # Check the filename format
            call_args = conversation_manager.audio_manager.save_audio_chunks.call_args
            output_path = call_args[0][1]  # Second argument is output_path
            assert "turn_01_response_" in output_path
            assert output_path.endswith(".wav")

    def test_save_turn_audio_no_conversation_state(self, conversation_manager):
        """Test saving turn audio without conversation state."""
        conversation_manager._save_turn_audio(1, ["chunk1"], "output/")
        # Should not raise exception, just return early

    def test_save_collected_audio(self, conversation_manager):
        """Test saving collected audio."""
        conversation_manager.start_conversation("test-123")
        
        # Add some audio chunks
        conversation_manager.conversation_state.greeting_chunks = ["greeting1", "greeting2"]
        conversation_manager.conversation_state.response_chunks = ["response1", "response2"]
        
        # Mock audio manager save method
        conversation_manager.audio_manager.save_audio_chunks = Mock(return_value=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            conversation_manager.save_collected_audio(temp_dir)
            
            # Verify save was called twice (greeting and response)
            assert conversation_manager.audio_manager.save_audio_chunks.call_count == 2

    def test_save_collected_audio_no_conversation_state(self, conversation_manager):
        """Test saving collected audio without conversation state."""
        conversation_manager.save_collected_audio("output/")
        # Should not raise exception, just log error

    def test_save_collected_audio_no_chunks(self, conversation_manager):
        """Test saving collected audio with no chunks."""
        conversation_manager.start_conversation("test-123")
        
        # Mock audio manager save method
        conversation_manager.audio_manager.save_audio_chunks = Mock(return_value=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            conversation_manager.save_collected_audio(temp_dir)
            
            # Should not call save if no chunks
            conversation_manager.audio_manager.save_audio_chunks.assert_not_called()

    def test_get_conversation_summary(self, conversation_manager):
        """Test getting conversation summary."""
        conversation_manager.start_conversation("test-123")
        
        # Add some data
        conversation_manager.conversation_state.turn_count = 5
        conversation_manager.conversation_state.greeting_chunks = ["g1", "g2"]
        conversation_manager.conversation_state.response_chunks = ["r1", "r2", "r3"]
        conversation_manager.conversation_state.activities_received = [{"type": "event"}]
        
        summary = conversation_manager.get_conversation_summary()
        
        assert summary["conversation_id"] == "test-123"
        assert summary["turn_count"] == 5
        assert summary["greeting_chunks"] == 2
        assert summary["response_chunks"] == 3
        assert summary["activities_count"] == 1
        assert summary["started_at"] is not None
        assert summary["last_turn_at"] is None

    def test_get_conversation_summary_no_state(self, conversation_manager):
        """Test getting conversation summary without conversation state."""
        summary = conversation_manager.get_conversation_summary()
        
        assert summary["error"] == "No conversation state available"

    def test_reset_conversation_state(self, conversation_manager):
        """Test resetting conversation state."""
        conversation_manager.start_conversation("test-123")
        
        # Add some data
        conversation_manager.conversation_state.turn_count = 5
        conversation_manager.conversation_state.greeting_chunks = ["g1", "g2"]
        
        # Reset state
        conversation_manager.reset_conversation_state()
        
        # Should have new state with same conversation ID but reset data
        assert conversation_manager.conversation_state is not None
        assert conversation_manager.conversation_state.conversation_id == "test-123"
        assert conversation_manager.conversation_state.turn_count == 0
        assert conversation_manager.conversation_state.greeting_chunks == []

    def test_reset_conversation_state_no_state(self, conversation_manager):
        """Test resetting conversation state when no state exists."""
        conversation_manager.reset_conversation_state()
        # Should not raise exception

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_partial_success(self, conversation_manager, temp_audio_files):
        """Test multi-turn conversation with partial success."""
        conversation_manager.start_conversation("test-123")
        
        # Mock the _send_user_audio method to succeed for first turn, fail for others
        async def mock_send_audio(file_path, chunk_delay):
            # Only return True for the exact first file path
            if file_path == temp_audio_files[0]:
                return True
            return False
        
        conversation_manager._send_user_audio = mock_send_audio
        
        # Mock response for first turn only
        async def mock_wait_response(timeout):
            if conversation_manager.conversation_state.turn_count == 0:
                return ["response1"]
            return []
        
        conversation_manager.wait_for_response = mock_wait_response
        
        result = await conversation_manager.multi_turn_conversation(
            temp_audio_files,
            wait_for_greeting=False,
            turn_delay=0.1,
            chunk_delay=0.01
        )
        
        assert result.success is True  # At least one turn completed
        assert result.completed_turns == 1
        assert result.total_turns == 3
        assert abs(result.success_rate - 33.3) < 0.1  # 1/3 * 100 with tolerance for floating point

    def test_register_greeting_complete_callback(self, conversation_manager):
        """Test registering greeting complete callback."""
        callback_called = False
        
        def test_callback():
            nonlocal callback_called
            callback_called = True
        
        conversation_manager.register_greeting_complete_callback(test_callback)
        
        # Call the notification method
        conversation_manager._notify_greeting_complete()
        
        assert callback_called is True

    def test_register_response_complete_callback(self, conversation_manager):
        """Test registering response complete callback."""
        callback_called = False
        
        def test_callback():
            nonlocal callback_called
            callback_called = True
        
        conversation_manager.register_response_complete_callback(test_callback)
        
        # Call the notification method
        conversation_manager._notify_response_complete()
        
        assert callback_called is True

    def test_register_callback_with_none(self, conversation_manager):
        """Test registering callback with None to clear it."""
        callback_called = False
        
        def test_callback():
            nonlocal callback_called
            callback_called = True
        
        # Register callback
        conversation_manager.register_greeting_complete_callback(test_callback)
        
        # Clear callback
        conversation_manager.register_greeting_complete_callback(None)
        
        # Call the notification method
        conversation_manager._notify_greeting_complete()
        
        assert callback_called is False

    def test_notify_greeting_complete_no_callback(self, conversation_manager):
        """Test notification when no callback is registered."""
        # Should not raise exception
        conversation_manager._notify_greeting_complete()

    def test_notify_response_complete_no_callback(self, conversation_manager):
        """Test notification when no callback is registered."""
        # Should not raise exception
        conversation_manager._notify_response_complete()

    def test_notify_greeting_complete_callback_exception(self, conversation_manager):
        """Test notification when callback raises exception."""
        def failing_callback():
            raise ValueError("Test exception")
        
        conversation_manager.register_greeting_complete_callback(failing_callback)
        
        # Should not raise exception, just log error
        conversation_manager._notify_greeting_complete()

    def test_notify_response_complete_callback_exception(self, conversation_manager):
        """Test notification when callback raises exception."""
        def failing_callback():
            raise ValueError("Test exception")
        
        conversation_manager.register_response_complete_callback(failing_callback)
        
        # Should not raise exception, just log error
        conversation_manager._notify_response_complete()

    @pytest.mark.asyncio
    async def test_wait_for_greeting_with_callback(self, conversation_manager):
        """Test wait_for_greeting with callback-based completion."""
        conversation_manager.start_conversation("test-123")
        
        # Add some greeting chunks
        conversation_manager.conversation_state.greeting_chunks = ["chunk1", "chunk2"]
        conversation_manager.conversation_state.collecting_greeting = True
        
        # Start waiting for greeting in background
        greeting_task = asyncio.create_task(
            conversation_manager.wait_for_greeting(timeout=5.0)
        )
        
        # Wait a bit to ensure the task is running
        await asyncio.sleep(0.1)
        
        # Simulate greeting completion by calling the notification
        conversation_manager._notify_greeting_complete()
        
        # Wait for the task to complete
        result = await greeting_task
        
        assert result == ["chunk1", "chunk2"]

    @pytest.mark.asyncio
    async def test_wait_for_response_with_callback(self, conversation_manager):
        """Test wait_for_response with callback-based completion."""
        conversation_manager.start_conversation("test-123")
        
        # Start waiting for response in background
        response_task = asyncio.create_task(
            conversation_manager.wait_for_response(timeout=5.0)
        )
        
        # Wait a bit to ensure the task is running and chunks are cleared
        await asyncio.sleep(0.1)
        
        # Add response chunks after the method has started (simulating chunks being collected)
        conversation_manager.conversation_state.response_chunks = ["resp1", "resp2", "resp3"]
        conversation_manager.conversation_state.collecting_response = True
        
        # Simulate response completion by calling the notification
        conversation_manager._notify_response_complete()
        
        # Wait for the task to complete
        result = await response_task
        
        assert result == ["resp1", "resp2", "resp3"]

    @pytest.mark.asyncio
    async def test_wait_for_greeting_timeout_with_callback(self, conversation_manager):
        """Test wait_for_greeting timeout with callback-based waiting."""
        conversation_manager.start_conversation("test-123")
        
        # Start waiting for greeting with short timeout
        result = await conversation_manager.wait_for_greeting(timeout=0.1)
        
        # Should timeout and return empty list
        assert result == []

    @pytest.mark.asyncio
    async def test_wait_for_response_timeout_with_callback(self, conversation_manager):
        """Test wait_for_response timeout with callback-based waiting."""
        conversation_manager.start_conversation("test-123")
        
        # Start waiting for response with short timeout
        result = await conversation_manager.wait_for_response(timeout=0.1)
        
        # Should timeout and return empty list
        assert result == []

    def test_conversation_manager_callback_attributes(self, conversation_manager):
        """Test that callback attributes are properly initialized."""
        assert conversation_manager._greeting_complete_callback is None
        assert conversation_manager._response_complete_callback is None

    def test_callback_registration_and_clearing(self, conversation_manager):
        """Test callback registration and clearing."""
        def test_callback():
            pass
        
        # Register callbacks
        conversation_manager.register_greeting_complete_callback(test_callback)
        conversation_manager.register_response_complete_callback(test_callback)
        
        assert conversation_manager._greeting_complete_callback == test_callback
        assert conversation_manager._response_complete_callback == test_callback
        
        # Clear callbacks
        conversation_manager.register_greeting_complete_callback(None)
        conversation_manager.register_response_complete_callback(None)
        
        assert conversation_manager._greeting_complete_callback is None
        assert conversation_manager._response_complete_callback is None 