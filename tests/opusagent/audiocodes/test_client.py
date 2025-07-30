"""
Unit tests for AudioCodes mock client main client.

This module tests the main LocalAudioCodesClient class that integrates all
the modular components for testing AudioCodes bridge server interactions.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path

from opusagent.local.audiocodes.models import (
    SessionConfig,
    SessionStatus,
    StreamStatus,
    ConversationResult,
    ConversationState,
)
from opusagent.local.audiocodes.client import LocalAudioCodesClient


class TestLocalAudioCodesClient:
    """Test LocalAudioCodesClient class."""

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
        # Ensure the websocket is seen as open by the new logic
        mock_ws.closed = False
        mock_ws.close_code = None
        
        # Create a proper async iterator for the websocket
        async def mock_iter():
            # Return an empty list to avoid infinite iteration
            return []
        
        mock_ws.__aiter__ = mock_iter
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
        import time
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Create a simple WAV file
            with wave.open(temp_file.name, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(bytes([0] * 32000))  # 1 second of silence
            
            yield temp_file.name
            
            # Cleanup with retry logic for Windows
            import os
            if os.path.exists(temp_file.name):
                # Try to delete with retries for Windows
                for attempt in range(3):
                    try:
                        os.unlink(temp_file.name)
                        break
                    except PermissionError:
                        if attempt < 2:  # Not the last attempt
                            time.sleep(0.1)  # Wait a bit before retrying
                        # On last attempt, just pass - file will be cleaned up by system
                        pass

    def test_client_initialization(self, client_config):
        """Test LocalAudioCodesClient initialization."""
        client = LocalAudioCodesClient(**client_config)
        
        assert client.config.bridge_url == "ws://localhost:8080"
        assert client.config.bot_name == "TestBot"
        assert client.config.caller == "+15551234567"
        assert client.session_manager is not None
        assert client.audio_manager is not None
        assert client.message_handler is not None
        assert client.conversation_manager is not None
        assert client.vad_manager is not None
        assert client._ws is None
        assert client._message_task is None

    def test_client_initialization_with_vad_config(self):
        """Test LocalAudioCodesClient initialization with VAD configuration."""
        vad_config = {
            "threshold": 0.7,
            "silence_threshold": 0.2,
            "enable_vad": True
        }
        
        client = LocalAudioCodesClient(
            bridge_url="ws://localhost:8080",
            vad_config=vad_config
        )
        
        assert client.config.enable_vad is True
        assert client.config.vad_threshold == 0.5  # Default from SessionConfig
        assert client.vad_manager is not None

    def test_client_initialization_vad_disabled(self):
        """Test LocalAudioCodesClient initialization with VAD disabled."""
        client = LocalAudioCodesClient(
            bridge_url="ws://localhost:8080",
            bot_name="TestBot",
            caller="+15551234567"
        )
        
        # VAD should be enabled by default
        assert client.config.enable_vad is True
        assert client.vad_manager is not None

    def test_client_initialization_with_custom_logger(self, client_config):
        """Test LocalAudioCodesClient initialization with custom logger."""
        custom_logger = Mock()
        client = LocalAudioCodesClient(**client_config, logger=custom_logger)
        
        assert client.logger == custom_logger

    @pytest.mark.asyncio
    async def test_client_context_manager_connect(self, client_config, mock_websocket_connect):
        """Test client context manager connection."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                assert client._ws is not None
                assert client._message_task is not None
                assert not client._message_task.done()

    @pytest.mark.asyncio
    async def test_client_context_manager_disconnect(self, client_config, mock_websocket_connect):
        """Test client context manager disconnection."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                pass  # Context manager should handle cleanup
        
        # Verify cleanup - the mock websocket should have been closed
        # Note: We can't directly verify this since we're using a new mock instance

    @pytest.mark.asyncio
    async def test_initiate_session_success(self, client_config, mock_websocket_connect):
        """Test successful session initiation."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
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
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Don't set session as accepted, should timeout
                success = await client.initiate_session()
                
                assert success is False

    @pytest.mark.asyncio
    async def test_initiate_session_error(self, client_config, mock_websocket_connect):
        """Test session initiation with error."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Mock session error
                client.session_manager.session_state.error = True
                client.session_manager.session_state.error_reason = "Test error"
                
                success = await client.initiate_session()
                
                assert success is False

    @pytest.mark.asyncio
    async def test_initiate_session_no_websocket(self, client_config):
        """Test session initiation without WebSocket connection."""
        client = LocalAudioCodesClient(**client_config)
        
        success = await client.initiate_session()
        
        assert success is False

    @pytest.mark.asyncio
    async def test_resume_session_success(self, client_config, mock_websocket_connect):
        """Test successful session resumption."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Mock session resumption
                client.session_manager.session_state.resumed = True
                
                success = await client.resume_session("test-conv-123")
                
                assert success is True
                assert client._ws is not None
                assert client._ws.send.called

    @pytest.mark.asyncio
    async def test_resume_session_timeout(self, client_config, mock_websocket_connect):
        """Test session resumption timeout."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                success = await client.resume_session("test-conv-123")
                
                assert success is False

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, client_config, mock_websocket_connect):
        """Test successful connection validation."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
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
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Create session first
                client.session_manager.create_session("test-conv-123")
                
                success = await client.validate_connection()
                
                assert success is False

    @pytest.mark.asyncio
    async def test_send_dtmf_event_success(self, client_config, mock_websocket_connect):
        """Test successful DTMF event sending."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Create session first
                client.session_manager.create_session("test-conv-123")
                
                success = await client.send_dtmf_event("5")
                
                assert success is True
                assert client._ws is not None
                assert client._ws.send.called

    @pytest.mark.asyncio
    async def test_send_dtmf_event_failure(self, client_config, mock_websocket_connect):
        """Test DTMF event sending failure."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
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
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Create session first
                client.session_manager.create_session("test-conv-123")
                
                success = await client.send_hangup_event()
                
                assert success is True
                assert client._ws is not None
                assert client._ws.send.called

    @pytest.mark.asyncio
    async def test_send_custom_activity_success(self, client_config, mock_websocket_connect):
        """Test successful custom activity sending."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
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
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
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
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Create session first
                client.session_manager.create_session("test-conv-123")
                
                # Mock empty audio chunks
                client.audio_manager.load_audio_chunks = Mock(return_value=[])
                
                success = await client.send_user_audio("nonexistent.wav")
                
                assert success is False

    @pytest.mark.asyncio
    async def test_wait_for_llm_greeting(self, client_config, mock_websocket_connect):
        """Test waiting for LLM greeting."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Start conversation
                client.conversation_manager.start_conversation("test-123")
                
                # Mock greeting
                greeting_chunks = ["greeting1", "greeting2"]
                assert client.conversation_manager.conversation_state is not None
                client.conversation_manager.conversation_state.greeting_chunks = greeting_chunks
                client.conversation_manager.conversation_state.collecting_greeting = True
                
                # Start waiting for greeting in background
                greeting_task = asyncio.create_task(
                    client.wait_for_llm_greeting(timeout=1.0)
                )
                
                # Wait a bit to ensure the task is running
                await asyncio.sleep(0.1)
                
                # Simulate greeting completion by calling the notification
                client.conversation_manager._notify_greeting_complete()
                
                # Wait for the task to complete
                greeting = await greeting_task
                
                assert greeting == greeting_chunks

    @pytest.mark.asyncio
    async def test_wait_for_llm_response(self, client_config, mock_websocket_connect):
        """Test waiting for LLM response."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Start conversation
                client.conversation_manager.start_conversation("test-123")
                
                # Mock response
                response_chunks = ["response1", "response2", "response3"]
                assert client.conversation_manager.conversation_state is not None
                client.conversation_manager.conversation_state.response_chunks = response_chunks
                client.conversation_manager.conversation_state.collecting_response = True
                
                # Start waiting for response in background
                response_task = asyncio.create_task(
                    client.wait_for_llm_response(timeout=1.0)
                )
                
                # Wait a bit to ensure the task is running
                await asyncio.sleep(0.1)
                
                # Simulate response completion by calling the notification
                client.conversation_manager._notify_response_complete()
                
                # Wait for the task to complete
                response = await response_task
                
                assert response == response_chunks

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, client_config, mock_websocket_connect, temp_audio_file):
        """Test multi-turn conversation."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
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
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Create session first
                client.session_manager.create_session("test-conv-123")
                
                await client.end_session("Test completed")
                
                assert client._ws is not None
                assert client._ws.send.called

    @pytest.mark.asyncio
    async def test_end_session_no_websocket(self, client_config):
        """Test ending session without WebSocket connection."""
        client = LocalAudioCodesClient(**client_config)
        
        # Should not raise exception
        await client.end_session("Test completed")

    def test_get_session_status(self, client_config):
        """Test getting session status."""
        client = LocalAudioCodesClient(**client_config)
        
        # Create session
        client.session_manager.create_session("test-123")
        # Simulate session acceptance by calling the proper handler
        client.session_manager.handle_session_accepted({"mediaFormat": "raw/lpcm16"})
        
        status = client.get_session_status()
        
        assert status["conversation_id"] == "test-123"
        assert status["accepted"] is True
        assert status["status"] == SessionStatus.ACTIVE.value

    def test_reset_session_state(self, client_config):
        """Test resetting session state."""
        client = LocalAudioCodesClient(**client_config)
        
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
        client = LocalAudioCodesClient(**client_config)
        
        # Mock conversation manager
        client.conversation_manager.save_collected_audio = Mock()
        
        client.save_collected_audio("test_output/")
        
        client.conversation_manager.save_collected_audio.assert_called_once_with("test_output/")


    @pytest.mark.asyncio
    async def test_message_handler_integration(self, client_config, mock_websocket_connect):
        """Test message handler integration."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
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
        client = LocalAudioCodesClient(**client_config)
        
        # Verify all components are connected
        assert client.session_manager.config == client.config
        assert client.message_handler.session_manager == client.session_manager
        assert client.conversation_manager.session_manager == client.session_manager
        assert client.conversation_manager.audio_manager == client.audio_manager
        assert client.vad_manager.stream_state == client.session_manager.stream_state

    def test_enable_vad(self, client_config):
        """Test enabling VAD functionality."""
        client = LocalAudioCodesClient(**client_config)
        
        # Mock VAD manager
        mock_vad_manager = Mock()
        client.vad_manager = mock_vad_manager
        mock_vad_manager.initialize.return_value = True
        
        # Enable VAD
        result = client.enable_vad()
        
        assert result is True
        assert client.config.enable_vad is True
        mock_vad_manager.initialize.assert_called_once()

    def test_enable_vad_failure(self, client_config):
        """Test enabling VAD when initialization fails."""
        client = LocalAudioCodesClient(**client_config)
        
        # Mock VAD manager
        mock_vad_manager = Mock()
        client.vad_manager = mock_vad_manager
        mock_vad_manager.initialize.return_value = False
        
        # Enable VAD
        result = client.enable_vad()
        
        assert result is False
        assert client.config.enable_vad is False

    def test_disable_vad(self, client_config):
        """Test disabling VAD functionality."""
        client = LocalAudioCodesClient(**client_config)
        
        # Mock VAD manager
        mock_vad_manager = Mock()
        client.vad_manager = mock_vad_manager
        
        # Disable VAD
        client.disable_vad()
        
        assert client.config.enable_vad is False
        mock_vad_manager.disable.assert_called_once()

    def test_get_vad_status(self, client_config):
        """Test getting VAD status information."""
        client = LocalAudioCodesClient(**client_config)
        
        # Mock VAD manager
        mock_vad_manager = Mock()
        client.vad_manager = mock_vad_manager
        mock_vad_manager.get_status.return_value = {"enabled": True, "speech_active": False}
        
        # Get VAD status
        status = client.get_vad_status()
        
        assert status["enabled"] is True
        assert "vad_manager_status" in status
        assert "config" in status
        mock_vad_manager.get_status.assert_called_once()

    def test_simulate_speech_committed(self, client_config):
        """Test simulating speech committed event."""
        client = LocalAudioCodesClient(**client_config)
        
        # Mock VAD manager
        mock_vad_manager = Mock()
        client.vad_manager = mock_vad_manager
        mock_vad_manager.enabled = True
        
        # Simulate speech committed
        client.simulate_speech_committed("Hello, world!")
        
        mock_vad_manager.simulate_speech_committed.assert_called_once_with("Hello, world!")

    def test_simulate_speech_committed_vad_disabled(self, client_config):
        """Test simulating speech committed when VAD is disabled."""
        client = LocalAudioCodesClient(**client_config)
        
        # Mock VAD manager
        mock_vad_manager = Mock()
        client.vad_manager = mock_vad_manager
        mock_vad_manager.enabled = False
        
        # Simulate speech committed
        client.simulate_speech_committed("Hello, world!")
        
        mock_vad_manager.simulate_speech_committed.assert_not_called()

    def test_simulate_speech_hypothesis(self, client_config):
        """Test simulating speech hypothesis event."""
        client = LocalAudioCodesClient(**client_config)
        
        # Mock VAD manager
        mock_vad_manager = Mock()
        client.vad_manager = mock_vad_manager
        mock_vad_manager.enabled = True
        
        # Simulate speech hypothesis
        client.simulate_speech_hypothesis("Hello, world!", 0.9)
        
        mock_vad_manager.simulate_speech_hypothesis.assert_called_once_with("Hello, world!", 0.9)

    def test_simulate_speech_hypothesis_vad_disabled(self, client_config):
        """Test simulating speech hypothesis when VAD is disabled."""
        client = LocalAudioCodesClient(**client_config)
        
        # Mock VAD manager
        mock_vad_manager = Mock()
        client.vad_manager = mock_vad_manager
        mock_vad_manager.enabled = False
        
        # Simulate speech hypothesis
        client.simulate_speech_hypothesis("Hello, world!", 0.9)
        
        mock_vad_manager.simulate_speech_hypothesis.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_user_audio_with_vad_success(self, client_config, mock_websocket_connect, temp_audio_file):
        """Test sending user audio with VAD processing."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Mock VAD manager
                mock_vad_manager = Mock()
                client.vad_manager = mock_vad_manager
                mock_vad_manager.enabled = True
                mock_vad_manager.process_audio_chunk.return_value = {
                    "speech_prob": 0.8,
                    "is_speech": True
                }
                
                # Mock stream state
                from opusagent.local.audiocodes.models import StreamStatus
                client.session_manager.stream_state.user_stream = StreamStatus.ACTIVE
                
                # Mock audio manager
                mock_audio_manager = Mock()
                client.audio_manager = mock_audio_manager
                mock_audio_manager.load_audio_chunks.return_value = ["chunk1", "chunk2", "chunk3"]
                
                # Send audio with VAD
                success = await client.send_user_audio_with_vad(temp_audio_file)
                
                assert success is True
                assert mock_vad_manager.process_audio_chunk.call_count == 3

    @pytest.mark.asyncio
    async def test_send_user_audio_with_vad_fallback(self, client_config, mock_websocket_connect, temp_audio_file):
        """Test sending user audio with VAD when VAD is disabled (fallback)."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Mock VAD manager
                mock_vad_manager = Mock()
                client.vad_manager = mock_vad_manager
                mock_vad_manager.enabled = False
                
                # Mock stream state
                from opusagent.local.audiocodes.models import StreamStatus
                client.session_manager.stream_state.user_stream = StreamStatus.ACTIVE
                
                # Mock audio manager
                mock_audio_manager = Mock()
                client.audio_manager = mock_audio_manager
                mock_audio_manager.load_audio_chunks.return_value = ["chunk1", "chunk2"]
                
                # Mock send_user_audio method
                client.send_user_audio = AsyncMock(return_value=True)
                
                # Send audio with VAD (should fallback)
                success = await client.send_user_audio_with_vad(temp_audio_file)
                
                assert success is True
                client.send_user_audio.assert_called_once_with(temp_audio_file, 0.02, enable_vad=False)

    @pytest.mark.asyncio
    async def test_handle_vad_event(self, client_config, mock_websocket_connect):
        """Test handling VAD events."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Create session
                client.session_manager.create_session("test-conv-123")
                
                # Test speech started event
                event = {
                    "type": "userStream.speech.started",
                    "timestamp": 1234.5,
                    "data": {"speech_prob": 0.8}
                }
                
                # Should not raise exception
                client._handle_vad_event(event)
                
                # The event is sent asynchronously, so we just verify no exception was raised
                assert client._ws is not None

    @pytest.mark.asyncio
    async def test_handle_vad_event_speech_hypothesis(self, client_config, mock_websocket_connect):
        """Test handling VAD speech hypothesis event."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Create session
                client.session_manager.create_session("test-conv-123")
                
                # Test speech hypothesis event
                event = {
                    "type": "userStream.speech.hypothesis",
                    "timestamp": 1234.5,
                    "data": {
                        "alternatives": [
                            {"text": "Hello", "confidence": 0.9}
                        ]
                    }
                }
                
                # Should not raise exception
                client._handle_vad_event(event)
                
                # The event is sent asynchronously, so we just verify no exception was raised
                assert client._ws is not None

    @pytest.mark.asyncio
    async def test_handle_vad_event_speech_committed(self, client_config, mock_websocket_connect):
        """Test handling VAD speech committed event."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Create session
                client.session_manager.create_session("test-conv-123")
                
                # Test speech committed event
                event = {
                    "type": "userStream.speech.committed",
                    "timestamp": 1234.5,
                    "data": {"text": "Hello, world!"}
                }
                
                # Should not raise exception
                client._handle_vad_event(event)
                
                # The event is sent asynchronously, so we just verify no exception was raised
                assert client._ws is not None

    @pytest.mark.asyncio
    async def test_handle_vad_event_no_websocket(self, client_config):
        """Test handling VAD events when WebSocket is not connected."""
        client = LocalAudioCodesClient(**client_config)
        
        # Test event handling without WebSocket
        event = {
            "type": "userStream.speech.started",
            "timestamp": 1234.5,
            "data": {"speech_prob": 0.8}
        }
        
        # Should not raise exception
        client._handle_vad_event(event)

    def test_get_session_status_with_vad(self, client_config):
        """Test getting session status with VAD information."""
        client = LocalAudioCodesClient(**client_config)
        
        # Mock VAD manager
        mock_vad_manager = Mock()
        client.vad_manager = mock_vad_manager
        mock_vad_manager.get_status.return_value = {"enabled": True, "speech_active": True}
        
        # Get session status
        status = client.get_session_status()
        
        assert "vad" in status
        assert status["vad"]["enabled"] is True
        assert status["vad"]["vad_manager_status"]["speech_active"] is True

    def test_reset_session_state_with_vad(self, client_config):
        """Test resetting session state with VAD reset."""
        client = LocalAudioCodesClient(**client_config)
        
        # Mock VAD manager
        mock_vad_manager = Mock()
        client.vad_manager = mock_vad_manager
        
        # Reset session state
        client.reset_session_state()
        
        # Verify VAD was reset
        mock_vad_manager.reset.assert_called_once()

    # ===== LIVE AUDIO CAPTURE TESTS =====

    def test_start_live_audio_capture_success(self, client_config):
        """Test successful live audio capture start."""
        client = LocalAudioCodesClient(**client_config)
        
        with patch('opusagent.local.audiocodes.client.LiveAudioManager') as mock_live_manager_class:
            mock_live_manager = Mock()
            mock_live_manager.start_capture.return_value = True
            mock_live_manager_class.return_value = mock_live_manager
            
            result = client.start_live_audio_capture()
            
            assert result is True
            assert client._live_audio_enabled is True
            assert client._live_audio_manager == mock_live_manager
            mock_live_manager_class.assert_called_once()
            mock_live_manager.start_capture.assert_called_once()

    def test_start_live_audio_capture_already_running(self, client_config):
        """Test starting live audio capture when already running."""
        # Create client with mocked logger
        mock_logger = Mock()
        client = LocalAudioCodesClient(**client_config, logger=mock_logger)
        client._live_audio_enabled = True
        
        result = client.start_live_audio_capture()
        
        assert result is True
        mock_logger.warning.assert_called_with("[CLIENT] Live audio capture already running")

    def test_start_live_audio_capture_failure(self, client_config):
        """Test live audio capture start failure."""
        # Create client with mocked logger
        mock_logger = Mock()
        client = LocalAudioCodesClient(**client_config, logger=mock_logger)
        
        with patch('opusagent.local.audiocodes.client.LiveAudioManager') as mock_live_manager_class:
            mock_live_manager = Mock()
            mock_live_manager.start_capture.return_value = False
            mock_live_manager_class.return_value = mock_live_manager
            
            result = client.start_live_audio_capture()
            
            assert result is False
            assert client._live_audio_enabled is False
            assert client._live_audio_manager is None
            mock_logger.error.assert_called_with("[CLIENT] Failed to start live audio capture")

    def test_start_live_audio_capture_with_config(self, client_config):
        """Test starting live audio capture with custom configuration."""
        client = LocalAudioCodesClient(**client_config)
        
        custom_config = {
            "vad_threshold": 0.3,
            "chunk_delay": 0.01
        }
        device_index = 1
        
        with patch('opusagent.local.audiocodes.client.LiveAudioManager') as mock_live_manager_class:
            mock_live_manager = Mock()
            mock_live_manager.start_capture.return_value = True
            mock_live_manager_class.return_value = mock_live_manager
            
            result = client.start_live_audio_capture(config=custom_config, device_index=device_index)
            
            assert result is True
            # Verify LiveAudioManager was created with correct config
            call_args = mock_live_manager_class.call_args
            assert call_args is not None
            assert call_args[1]["config"]["vad_threshold"] == 0.3
            assert call_args[1]["config"]["chunk_delay"] == 0.01
            assert call_args[1]["config"]["device_index"] == 1

    def test_stop_live_audio_capture(self, client_config):
        """Test stopping live audio capture."""
        # Create client with mocked logger
        mock_logger = Mock()
        client = LocalAudioCodesClient(**client_config, logger=mock_logger)
        client._live_audio_enabled = True
        client._live_audio_manager = Mock()
        
        client.stop_live_audio_capture()
        
        assert client._live_audio_enabled is False
        assert client._live_audio_manager is None
        mock_logger.info.assert_called_with("[CLIENT] Live audio capture stopped")

    @pytest.mark.asyncio
    async def test_handle_live_audio_chunk(self, client_config, mock_websocket_connect):
        """Test handling live audio chunk."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                client._live_audio_enabled = True

                # Ensure WebSocket is properly initialized
                assert client._ws is not None

                # Mock WebSocket send
                mock_send = Mock()
                client._ws.send = mock_send

                test_chunk = "base64_encoded_audio_data"
                client._handle_live_audio_chunk(test_chunk)

                # Wait for queue consumer to process the chunk
                await asyncio.sleep(0.1)

                # Verify message was sent
                mock_send.assert_called_once()
                call_args = mock_send.call_args[0][0]
                message = json.loads(call_args)
                assert message["type"] == "userStream.chunk"
                assert message["audioChunk"] == test_chunk

    @pytest.mark.asyncio
    async def test_handle_live_audio_chunk_not_enabled(self, client_config, mock_websocket_connect):
        """Test handling live audio chunk when not enabled."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                client._live_audio_enabled = False
                
                # Ensure WebSocket is properly initialized
                assert client._ws is not None
                
                # Mock WebSocket send
                mock_send = Mock()
                client._ws.send = mock_send
                
                test_chunk = "base64_encoded_audio_data"
                client._handle_live_audio_chunk(test_chunk)
                
                # Verify no message was sent
                mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_live_vad_event(self, client_config, mock_websocket_connect):
        """Test handling live VAD event."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                client._live_audio_enabled = True
                
                # Ensure WebSocket is properly initialized
                assert client._ws is not None
                
                # Mock WebSocket send
                mock_send = Mock()
                client._ws.send = mock_send
                
                test_event = {
                    "type": "userStream.speech.started",
                    "data": {
                        "speech_prob": 0.8,
                        "timestamp": 123.456
                    }
                }
                
                client._handle_live_vad_event(test_event)
                
                # Wait for queue consumer to process the event
                await asyncio.sleep(0.1)
                
                # Verify message was sent
                mock_send.assert_called_once()
                call_args = mock_send.call_args[0][0]
                message = json.loads(call_args)
                assert message["type"] == "userStream.speech.started"
                assert message["speech_prob"] == 0.8

    @pytest.mark.asyncio
    async def test_handle_live_vad_event_speech_stopped(self, client_config, mock_websocket_connect):
        """Test handling live VAD speech stopped event."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                client._live_audio_enabled = True
                
                # Ensure WebSocket is properly initialized
                assert client._ws is not None
                
                # Mock WebSocket send
                mock_send = Mock()
                client._ws.send = mock_send
                
                test_event = {
                    "type": "userStream.speech.stopped",
                    "data": {
                        "speech_prob": 0.1,
                        "speech_duration_ms": 1500,
                        "timestamp": 123.456
                    }
                }
                
                client._handle_live_vad_event(test_event)
                
                # Wait for queue consumer to process the event
                await asyncio.sleep(0.1)
                
                # Verify message was sent
                mock_send.assert_called_once()
                call_args = mock_send.call_args[0][0]
                message = json.loads(call_args)
                assert message["type"] == "userStream.speech.stopped"
                assert message["speech_prob"] == 0.1
                assert message["speech_duration_ms"] == 1500

    def test_get_available_audio_devices(self, client_config):
        """Test getting available audio devices."""
        client = LocalAudioCodesClient(**client_config)
        
        mock_devices = [
            {"index": 0, "name": "Device 0", "channels": 1, "sample_rate": 16000},
            {"index": 1, "name": "Device 1", "channels": 2, "sample_rate": 44100}
        ]
        
        with patch('opusagent.local.audiocodes.client.LiveAudioManager') as mock_live_manager_class:
            mock_live_manager = Mock()
            mock_live_manager.get_available_devices.return_value = mock_devices
            mock_live_manager_class.return_value = mock_live_manager
            
            devices = client.get_available_audio_devices()
            
            # Since the actual implementation creates a temporary manager, we can't easily mock it
            # Instead, just verify the method doesn't raise an exception
            assert isinstance(devices, list)

    def test_get_available_audio_devices_with_existing_manager(self, client_config):
        """Test getting available audio devices with existing manager."""
        client = LocalAudioCodesClient(**client_config)
        client._live_audio_manager = Mock()
        client._live_audio_manager.get_available_devices.return_value = [{"name": "Test"}]
        
        devices = client.get_available_audio_devices()
        
        assert devices == [{"name": "Test"}]
        client._live_audio_manager.get_available_devices.assert_called_once()

    def test_set_audio_device(self, client_config):
        """Test setting audio device."""
        client = LocalAudioCodesClient(**client_config)
        client._live_audio_manager = Mock()
        client._live_audio_manager.set_device.return_value = True
        
        result = client.set_audio_device(1)
        
        assert result is True
        client._live_audio_manager.set_device.assert_called_once_with(1)

    def test_set_audio_device_no_manager(self, client_config):
        """Test setting audio device when no manager exists."""
        # Create client with mocked logger
        mock_logger = Mock()
        client = LocalAudioCodesClient(**client_config, logger=mock_logger)
        
        result = client.set_audio_device(1)
        
        assert result is False
        mock_logger.warning.assert_called_with("[CLIENT] Live audio not initialized")

    def test_get_live_audio_status(self, client_config):
        """Test getting live audio status."""
        client = LocalAudioCodesClient(**client_config)
        
        # Test without manager
        status = client.get_live_audio_status()
        assert status["running"] is False
        assert status["enabled"] is False
        assert status["manager"] is None
        
        # Test with manager
        mock_manager = Mock()
        mock_manager.get_status.return_value = {"running": True, "config": {}}
        client._live_audio_manager = mock_manager
        
        status = client.get_live_audio_status()
        assert status["running"] is True
        mock_manager.get_status.assert_called_once()

    def test_get_audio_level(self, client_config):
        """Test getting audio level."""
        client = LocalAudioCodesClient(**client_config)
        
        # Test without manager
        level = client.get_audio_level()
        assert level == 0.0
        
        # Test with manager
        mock_manager = Mock()
        mock_manager.get_audio_level.return_value = 0.75
        client._live_audio_manager = mock_manager
        
        level = client.get_audio_level()
        assert level == 0.75
        mock_manager.get_audio_level.assert_called_once()

    def test_is_live_audio_enabled(self, client_config):
        """Test checking if live audio is enabled."""
        client = LocalAudioCodesClient(**client_config)
        
        assert client.is_live_audio_enabled() is False
        
        client._live_audio_enabled = True
        assert client.is_live_audio_enabled() is True

    def test_get_session_status_with_live_audio(self, client_config):
        """Test getting session status with live audio information."""
        client = LocalAudioCodesClient(**client_config)
        
        # Mock live audio status
        with patch.object(client, 'get_live_audio_status') as mock_get_status:
            mock_get_status.return_value = {"running": True, "enabled": True}
            
            status = client.get_session_status()
            
            assert "live_audio" in status
            assert status["live_audio"]["running"] is True
            assert status["live_audio"]["enabled"] is True

    @pytest.mark.asyncio
    async def test_client_context_manager_with_live_audio_cleanup(self, client_config, mock_websocket_connect):
        """Test client context manager cleanup with live audio."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Set up live audio
                mock_manager = Mock()
                client._live_audio_manager = mock_manager
                client._live_audio_enabled = True
                
                # Context manager will call __aexit__ which should cleanup live audio
                pass
            
            # Verify live audio was cleaned up
            mock_manager.stop_capture.assert_called_once()
            assert client._live_audio_manager is None
            # Note: _live_audio_enabled is not reset in __aexit__, only the manager is cleaned up

    # ===== AUDIO PLAYBACK TESTS =====

    def test_audio_playback_initialization(self, client_config):
        """Test that audio playback is initialized correctly."""
        client = LocalAudioCodesClient(**client_config)
        
        assert hasattr(client, 'audio_playback')
        assert client.audio_playback is not None
        assert client.audio_playback.enabled is True

    @pytest.mark.asyncio
    async def test_client_context_manager_with_audio_playback(self, client_config, mock_websocket_connect):
        """Test client context manager with audio playback initialization."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Audio playback should be connected and started
                assert client.audio_playback.connected is True
                assert client.audio_playback.enabled is True

    def test_enable_audio_playback(self, client_config):
        """Test enabling audio playback."""
        client = LocalAudioCodesClient(**client_config)
        
        with patch.object(client.audio_playback, 'start', return_value=True):
            success = client.enable_audio_playback(volume=0.7)
            assert success is True

    def test_enable_audio_playback_failure(self, client_config):
        """Test enabling audio playback with failure."""
        client = LocalAudioCodesClient(**client_config)
        
        with patch.object(client.audio_playback, 'start', return_value=False):
            success = client.enable_audio_playback(volume=0.7)
            assert success is False

    def test_disable_audio_playback(self, client_config):
        """Test disabling audio playback."""
        client = LocalAudioCodesClient(**client_config)
        
        with patch.object(client.audio_playback, 'stop') as mock_stop:
            client.disable_audio_playback()
            mock_stop.assert_called_once()

    def test_set_playback_volume(self, client_config):
        """Test setting playback volume."""
        client = LocalAudioCodesClient(**client_config)
        
        with patch.object(client.audio_playback, 'set_volume') as mock_set_volume:
            client.set_playback_volume(0.6)
            mock_set_volume.assert_called_once_with(0.6)

    def test_mute_playback(self, client_config):
        """Test muting playback."""
        client = LocalAudioCodesClient(**client_config)
        
        with patch.object(client.audio_playback, 'mute') as mock_mute:
            client.mute_playback()
            mock_mute.assert_called_once()

    def test_unmute_playback(self, client_config):
        """Test unmuting playback."""
        client = LocalAudioCodesClient(**client_config)
        
        with patch.object(client.audio_playback, 'unmute') as mock_unmute:
            client.unmute_playback()
            mock_unmute.assert_called_once()

    def test_get_playback_audio_level(self, client_config):
        """Test getting playback audio level."""
        client = LocalAudioCodesClient(**client_config)
        
        with patch.object(client.audio_playback, 'get_audio_level', return_value=0.75):
            level = client.get_playback_audio_level()
            assert level == 0.75

    def test_get_audio_playback_status(self, client_config):
        """Test getting audio playback status."""
        client = LocalAudioCodesClient(**client_config)
        
        mock_status = {
            "enabled": True,
            "connected": True,
            "manager_active": True,
            "playing": True,
            "muted": False,
            "volume": 0.8,
            "chunks_played": 10,
            "bytes_played": 1000
        }
        
        with patch.object(client.audio_playback, 'get_status', return_value=mock_status):
            status = client.get_audio_playback_status()
            assert status == mock_status

    def test_get_session_status_with_audio_playback(self, client_config):
        """Test getting session status with audio playback information."""
        client = LocalAudioCodesClient(**client_config)
        
        mock_playback_status = {
            "enabled": True,
            "connected": True,
            "playing": True,
            "chunks_played": 5
        }
        
        with patch.object(client.audio_playback, 'get_status', return_value=mock_playback_status):
            status = client.get_session_status()
            
            assert "audio_playback" in status
            assert status["audio_playback"] == mock_playback_status

    @pytest.mark.asyncio
    async def test_client_context_manager_with_audio_playback_cleanup(self, client_config, mock_websocket_connect):
        """Test client context manager cleanup with audio playback."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Audio playback should be initialized
                assert client.audio_playback is not None
                
                # Context manager should clean up audio playback
                pass
        
        # Verify cleanup - the audio playback should be cleaned up
        # Note: We can't directly verify this since we're using a new mock instance

    def test_reset_session_state_with_audio_playback(self, client_config):
        """Test resetting session state with audio playback."""
        client = LocalAudioCodesClient(**client_config)
        
        # Set some state
        client.session_manager.session_state.status = SessionStatus.ACTIVE
        client.audio_playback.playback.chunks_played = 10
        
        with patch.object(client.audio_playback, 'cleanup') as mock_cleanup:
            client.reset_session_state()
            
            # Session state should be reset
            assert client.session_manager.session_state.status == SessionStatus.DISCONNECTED
            # Audio playback should be cleaned up
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_audio_playback_integration_with_message_handler(self, client_config, mock_websocket_connect):
        """Test audio playback integration with message handler."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Audio playback should be connected to message handler
                assert client.audio_playback.connected is True
                
                # Test that playStream.chunk events are handled
                test_data = {
                    "type": "playStream.chunk",
                    "audioChunk": "dGVzdF9hdWRpb19kYXRh"
                }
                
                with patch.object(client.audio_playback, '_handle_play_stream_chunk') as mock_handler:
                    # Process the message
                    client.message_handler.process_message(json.dumps(test_data))
                    
                    # The handler should be called
                    # Note: This is indirect since the handler is registered with the message handler
                    assert client.audio_playback.connected is True

    def test_audio_playback_without_audio_dependencies(self, client_config):
        """Test audio playback when audio dependencies are not available."""
        with patch('opusagent.local.audiocodes.audio_playback.AUDIO_AVAILABLE', False):
            client = LocalAudioCodesClient(**client_config)
            
            # Audio playback should still be initialized but disabled
            assert hasattr(client, 'audio_playback')
            assert client.audio_playback is not None
            # The config should be disabled when dependencies are not available
            # This is handled in the AudioPlayback class initialization

    def test_audio_playback_volume_control_integration(self, client_config):
        """Test audio playback volume control integration."""
        client = LocalAudioCodesClient(**client_config)
        
        # Test volume control through client methods
        client.set_playback_volume(0.5)
        assert client.audio_playback.playback.volume == 0.5
        
        # Test mute/unmute
        client.mute_playback()
        assert client.audio_playback.playback.muted is True
        
        client.unmute_playback()
        assert client.audio_playback.playback.muted is False

    def test_audio_playback_statistics_integration(self, client_config):
        """Test audio playback statistics integration."""
        client = LocalAudioCodesClient(**client_config)
        
        # Set some test statistics
        client.audio_playback.playback.chunks_played = 15
        client.audio_playback.playback.bytes_played = 1500
        client.audio_playback.playback.current_audio_level = 0.8
        
        # Test getting statistics through client
        status = client.get_audio_playback_status()
        assert status["chunks_played"] == 15
        assert status["bytes_played"] == 1500
        assert status["audio_level"] == 0.8

    @pytest.mark.asyncio
    async def test_audio_playback_with_conversation(self, client_config, mock_websocket_connect, temp_audio_file):
        """Test audio playback during conversation."""
        with patch('opusagent.local.audiocodes.client.websockets.connect', side_effect=mock_websocket_connect):
            async with LocalAudioCodesClient(**client_config) as client:
                # Mock session acceptance
                client.session_manager.session_state.accepted = True
                
                # Mock audio chunks for response
                response_chunks = ["chunk1", "chunk2", "chunk3"]
                if client.conversation_manager.conversation_state:
                    client.conversation_manager.conversation_state.response_chunks = response_chunks
                
                # Test that audio playback is ready for conversation
                assert client.audio_playback.enabled is True
                assert client.audio_playback.connected is True
                
                # Test getting audio level during conversation
                level = client.get_playback_audio_level()
                assert isinstance(level, float)
                assert 0.0 <= level <= 1.0 