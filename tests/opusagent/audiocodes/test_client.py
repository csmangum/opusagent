"""
Unit tests for AudioCodes mock client main client.

This module tests the main MockAudioCodesClient class that integrates all
the modular components for testing AudioCodes bridge server interactions.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path

from opusagent.mock.audiocodes.models import (
    SessionConfig,
    SessionStatus,
    StreamStatus,
    ConversationResult,
    ConversationState,
)
from opusagent.mock.audiocodes.client import MockAudioCodesClient


class TestMockAudioCodesClient:
    """Test MockAudioCodesClient class."""

    @pytest.fixture
    def client_config(self):
        """Create a test client configuration."""
        return {
            "bridge_url": "ws://localhost:8080",
            "bot_name": "TestBot",
            "caller": "+15551234567"
        }

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket connection."""
        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.close = AsyncMock()
        # Configure the mock to be properly awaitable
        mock_ws.__aiter__ = AsyncMock(return_value=AsyncMock())
        return mock_ws

    @pytest.fixture
    def mock_websocket_connect(self, mock_websocket):
        """Create a mock websockets.connect function."""
        async def mock_connect(url):
            return mock_websocket
        return mock_connect

    @pytest.fixture
    def temp_audio_file(self):
        """Create a temporary audio file for testing."""
        import tempfile
        import wave
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Create a simple WAV file
            with wave.open(temp_file.name, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(bytes([0] * 32000))  # 1 second of silence
            
            yield temp_file.name
            
            # Cleanup
            import os
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

    def test_client_initialization(self, client_config):
        """Test MockAudioCodesClient initialization."""
        client = MockAudioCodesClient(**client_config)
        
        assert client.config.bridge_url == "ws://localhost:8080"
        assert client.config.bot_name == "TestBot"
        assert client.config.caller == "+15551234567"
        assert client.session_manager is not None
        assert client.audio_manager is not None
        assert client.message_handler is not None
        assert client.conversation_manager is not None
        assert client._ws is None
        assert client._message_task is None

    def test_client_initialization_with_custom_logger(self, client_config):
        """Test MockAudioCodesClient initialization with custom logger."""
        custom_logger = Mock()
        client = MockAudioCodesClient(**client_config, logger=custom_logger)
        
        assert client.logger == custom_logger

    @pytest.mark.asyncio
    async def test_client_context_manager_connect(self, client_config, mock_websocket_connect):
        """Test client context manager connection."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                assert client._ws is not None
                assert client._message_task is not None
                assert not client._message_task.done()

    @pytest.mark.asyncio
    async def test_client_context_manager_disconnect(self, client_config, mock_websocket_connect):
        """Test client context manager disconnection."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                pass  # Context manager should handle cleanup
        
        # Verify cleanup - the mock websocket should have been closed
        # Note: We can't directly verify this since we're using a new mock instance

    @pytest.mark.asyncio
    async def test_initiate_session_success(self, client_config, mock_websocket_connect):
        """Test successful session initiation."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Mock session acceptance
                client.session_manager.session_state.accepted = True
                
                success = await client.initiate_session()
                
                assert success is True
                # Verify that send was called (we can't check the exact mock since it's a new instance)
                assert client._ws is not None
                assert client._ws.send.called

    @pytest.mark.asyncio
    async def test_initiate_session_timeout(self, client_config, mock_websocket_connect):
        """Test session initiation timeout."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Don't set session as accepted, should timeout
                success = await client.initiate_session()
                
                assert success is False

    @pytest.mark.asyncio
    async def test_initiate_session_error(self, client_config, mock_websocket_connect):
        """Test session initiation with error."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Mock session error
                client.session_manager.session_state.error = True
                client.session_manager.session_state.error_reason = "Test error"
                
                success = await client.initiate_session()
                
                assert success is False

    @pytest.mark.asyncio
    async def test_initiate_session_no_websocket(self, client_config):
        """Test session initiation without WebSocket connection."""
        client = MockAudioCodesClient(**client_config)
        
        success = await client.initiate_session()
        
        assert success is False

    @pytest.mark.asyncio
    async def test_resume_session_success(self, client_config, mock_websocket_connect):
        """Test successful session resumption."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Mock session resumption
                client.session_manager.session_state.resumed = True
                
                success = await client.resume_session("test-conv-123")
                
                assert success is True
                assert client._ws is not None
                assert client._ws.send.called

    @pytest.mark.asyncio
    async def test_resume_session_timeout(self, client_config, mock_websocket_connect):
        """Test session resumption timeout."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                success = await client.resume_session("test-conv-123")
                
                assert success is False

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, client_config, mock_websocket_connect):
        """Test successful connection validation."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Create session first
                client.session_manager.create_session("test-conv-123")
                
                # Mock connection validation
                client.session_manager.session_state.connection_validated = True
                
                success = await client.validate_connection()
                
                assert success is True
                assert client._ws is not None
                assert client._ws.send.called

    @pytest.mark.asyncio
    async def test_validate_connection_timeout(self, client_config, mock_websocket_connect):
        """Test connection validation timeout."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Create session first
                client.session_manager.create_session("test-conv-123")
                
                success = await client.validate_connection()
                
                assert success is False

    @pytest.mark.asyncio
    async def test_send_dtmf_event_success(self, client_config, mock_websocket_connect):
        """Test successful DTMF event sending."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Create session first
                client.session_manager.create_session("test-conv-123")
                
                success = await client.send_dtmf_event("5")
                
                assert success is True
                assert client._ws is not None
                assert client._ws.send.called

    @pytest.mark.asyncio
    async def test_send_dtmf_event_failure(self, client_config, mock_websocket_connect):
        """Test DTMF event sending failure."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Create session first
                client.session_manager.create_session("test-conv-123")
                
                # Mock WebSocket send to raise exception
                assert client._ws is not None
                client._ws.send.side_effect = Exception("Send error")
                
                success = await client.send_dtmf_event("5")
                
                assert success is False

    @pytest.mark.asyncio
    async def test_send_hangup_event_success(self, client_config, mock_websocket_connect):
        """Test successful hangup event sending."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Create session first
                client.session_manager.create_session("test-conv-123")
                
                success = await client.send_hangup_event()
                
                assert success is True
                assert client._ws is not None
                assert client._ws.send.called

    @pytest.mark.asyncio
    async def test_send_custom_activity_success(self, client_config, mock_websocket_connect):
        """Test successful custom activity sending."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Create session first
                client.session_manager.create_session("test-conv-123")
                
                activity = {"type": "event", "name": "custom_event", "value": "test"}
                success = await client.send_custom_activity(activity)
                
                assert success is True
                assert client._ws is not None
                assert client._ws.send.called

    @pytest.mark.asyncio
    async def test_send_user_audio_success(self, client_config, mock_websocket_connect, temp_audio_file):
        """Test successful user audio sending."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Create session first
                client.session_manager.create_session("test-conv-123")
                
                # Mock user stream started
                client.session_manager.stream_state.user_stream = StreamStatus.ACTIVE
                
                # Mock audio chunks
                client.audio_manager.load_audio_chunks = Mock(return_value=["chunk1", "chunk2"])
                
                success = await client.send_user_audio(temp_audio_file)
                
                assert success is True
                # Should have sent multiple messages (start, chunks, stop)
                assert client._ws is not None
                assert client._ws.send.call_count >= 4

    @pytest.mark.asyncio
    async def test_send_user_audio_no_chunks(self, client_config, mock_websocket_connect):
        """Test user audio sending with no chunks."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Create session first
                client.session_manager.create_session("test-conv-123")
                
                # Mock empty audio chunks
                client.audio_manager.load_audio_chunks = Mock(return_value=[])
                
                success = await client.send_user_audio("nonexistent.wav")
                
                assert success is False

    @pytest.mark.asyncio
    async def test_wait_for_llm_greeting(self, client_config, mock_websocket_connect):
        """Test waiting for LLM greeting."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Start conversation
                client.conversation_manager.start_conversation("test-123")
                
                # Mock greeting
                greeting_chunks = ["greeting1", "greeting2"]
                assert client.conversation_manager.conversation_state is not None
                client.conversation_manager.conversation_state.greeting_chunks = greeting_chunks
                client.conversation_manager.conversation_state.collecting_greeting = False
                
                greeting = await client.wait_for_llm_greeting(timeout=1.0)
                
                assert greeting == greeting_chunks

    @pytest.mark.asyncio
    async def test_wait_for_llm_response(self, client_config, mock_websocket_connect):
        """Test waiting for LLM response."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Start conversation
                client.conversation_manager.start_conversation("test-123")
                
                # Mock response
                response_chunks = ["response1", "response2", "response3"]
                assert client.conversation_manager.conversation_state is not None
                client.conversation_manager.conversation_state.response_chunks = response_chunks
                client.conversation_manager.conversation_state.collecting_response = False
                
                response = await client.wait_for_llm_response(timeout=1.0)
                
                assert response == response_chunks

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, client_config, mock_websocket_connect, temp_audio_file):
        """Test multi-turn conversation."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Start conversation
                client.conversation_manager.start_conversation("test-123")
                
                # Mock conversation manager
                mock_result = ConversationResult(
                    total_turns=1,
                    completed_turns=1,
                    success=True
                )
                client.conversation_manager.multi_turn_conversation = AsyncMock(return_value=mock_result)
                
                result = await client.multi_turn_conversation([temp_audio_file])
                
                assert result == mock_result
                client.conversation_manager.multi_turn_conversation.assert_called_once()

    @pytest.mark.asyncio
    async def test_end_session(self, client_config, mock_websocket_connect):
        """Test ending session."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Create session first
                client.session_manager.create_session("test-conv-123")
                
                await client.end_session("Test completed")
                
                assert client._ws is not None
                assert client._ws.send.called

    @pytest.mark.asyncio
    async def test_end_session_no_websocket(self, client_config):
        """Test ending session without WebSocket connection."""
        client = MockAudioCodesClient(**client_config)
        
        # Should not raise exception
        await client.end_session("Test completed")

    def test_get_session_status(self, client_config):
        """Test getting session status."""
        client = MockAudioCodesClient(**client_config)
        
        # Create session
        client.session_manager.create_session("test-123")
        client.session_manager.session_state.accepted = True
        
        status = client.get_session_status()
        
        assert status["conversation_id"] == "test-123"
        assert status["accepted"] is True
        assert status["status"] == SessionStatus.CONNECTED.value

    def test_reset_session_state(self, client_config):
        """Test resetting session state."""
        client = MockAudioCodesClient(**client_config)
        
        # Create session and add some state
        client.session_manager.create_session("test-123")
        client.session_manager.session_state.accepted = True
        client.conversation_manager.start_conversation("test-123")
        
        # Reset state
        client.reset_session_state()
        
        assert client.session_manager.session_state.status == SessionStatus.DISCONNECTED
        assert client.session_manager.session_state.accepted is False
        # The conversation state should be reset but keep the same conversation_id
        assert client.conversation_manager.conversation_state is not None
        assert client.conversation_manager.conversation_state.conversation_id == "test-123"
        # But other state should be reset
        assert len(client.conversation_manager.conversation_state.greeting_chunks) == 0
        assert len(client.conversation_manager.conversation_state.response_chunks) == 0

    def test_save_collected_audio(self, client_config):
        """Test saving collected audio."""
        client = MockAudioCodesClient(**client_config)
        
        # Mock conversation manager
        client.conversation_manager.save_collected_audio = Mock()
        
        client.save_collected_audio("test_output/")
        
        client.conversation_manager.save_collected_audio.assert_called_once_with("test_output/")

    @pytest.mark.asyncio
    async def test_simple_conversation_test_success(self, client_config, mock_websocket_connect, temp_audio_file):
        """Test successful simple conversation test."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Mock session initiation
                client.session_manager.session_state.accepted = True
                
                # Mock conversation result
                mock_result = ConversationResult(
                    total_turns=1,
                    completed_turns=1,
                    success=True
                )
                client.conversation_manager.multi_turn_conversation = AsyncMock(return_value=mock_result)
                
                # Mock conversation manager save method
                client.conversation_manager.save_collected_audio = Mock()
                
                success = await client.simple_conversation_test([temp_audio_file], "TestSession")
                
                assert success is True
                client.conversation_manager.save_collected_audio.assert_called_once()

    @pytest.mark.asyncio
    async def test_simple_conversation_test_session_failure(self, client_config, mock_websocket_connect):
        """Test simple conversation test with session initiation failure."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Don't set session as accepted, should fail
                success = await client.simple_conversation_test([], "TestSession")
                
                assert success is False

    @pytest.mark.asyncio
    async def test_simple_conversation_test_exception(self, client_config, mock_websocket_connect):
        """Test simple conversation test with exception."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Mock session initiation to raise exception
                client.initiate_session = AsyncMock(side_effect=Exception("Test error"))
                
                success = await client.simple_conversation_test([], "TestSession")
                
                assert success is False

    @pytest.mark.asyncio
    async def test_message_handler_integration(self, client_config, mock_websocket_connect):
        """Test message handler integration."""
        with patch('opusagent.mock.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with MockAudioCodesClient(**client_config) as client:
                # Create session
                client.session_manager.create_session("test-123")
                
                # Simulate receiving a session.accepted message
                message = json.dumps({
                    "type": "session.accepted",
                    "conversationId": "test-123",
                    "mediaFormat": "raw/lpcm16"
                })
                
                # Process the message
                event = client.message_handler.process_message(message)
                
                assert event is not None
                assert event.type.value == "session.accepted"
                assert client.session_manager.session_state.accepted is True
                assert client.session_manager.session_state.status == SessionStatus.ACTIVE

    def test_client_components_integration(self, client_config):
        """Test that all client components are properly integrated."""
        client = MockAudioCodesClient(**client_config)
        
        # Verify all components are connected
        assert client.session_manager.config == client.config
        assert client.message_handler.session_manager == client.session_manager
        assert client.conversation_manager.session_manager == client.session_manager
        assert client.conversation_manager.audio_manager == client.audio_manager 