"""
Unit tests for opusagent.mock.realtime.generators module.
"""

import pytest
import asyncio
import json
import base64
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from opusagent.local.realtime.generators import ResponseGenerator
from opusagent.local.realtime.models import LocalResponseConfig
from opusagent.models.openai_api import ResponseCreateOptions, ServerEventType


class TestResponseGenerator:
    """Test ResponseGenerator class."""

    def test_response_generator_creation(self):
        """Test basic ResponseGenerator creation."""
        logger = Mock()
        audio_manager = Mock()
        ws_connection = Mock()
        
        generator = ResponseGenerator(logger, audio_manager, ws_connection)
        
        assert generator.logger == logger
        assert generator.audio_manager == audio_manager
        assert generator._ws == ws_connection
        assert generator._active_response_id is None

    def test_response_generator_creation_without_params(self):
        """Test ResponseGenerator creation without parameters."""
        generator = ResponseGenerator()
        
        assert generator.logger is not None
        assert generator.audio_manager is None
        assert generator._ws is None
        assert generator._active_response_id is None

    def test_set_websocket_connection(self):
        """Test setting WebSocket connection."""
        generator = ResponseGenerator()
        ws_connection = Mock()
        
        generator.set_websocket_connection(ws_connection)
        
        assert generator._ws == ws_connection

    def test_set_active_response_id(self):
        """Test setting active response ID."""
        generator = ResponseGenerator()
        response_id = "test_response_123"
        
        generator.set_active_response_id(response_id)
        
        assert generator._active_response_id == response_id

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_send_event_success(self, mock_websocket_utils):
        """Test successful event sending."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        event = {"type": "test.event", "data": "test"}
        await generator._send_event(event)
        
        mock_websocket_utils.safe_send_event.assert_called_once_with(
            generator._ws, event, generator.logger
        )

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_send_event_failure(self, mock_websocket_utils):
        """Test event sending failure."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=False)
        
        event = {"type": "test.event", "data": "test"}
        
        with pytest.raises(Exception, match="Failed to send event to WebSocket"):
            await generator._send_event(event)

    def test_determine_response_key(self):
        """Test response key determination."""
        generator = ResponseGenerator()
        options = ResponseCreateOptions()
        
        # This is a placeholder method that returns None
        result = generator._determine_response_key(options)
        assert result is None

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_generate_text_response(self, mock_websocket_utils):
        """Test text response generation."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        generator._active_response_id = "test_response_123"
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        options = ResponseCreateOptions()
        config = LocalResponseConfig(
            text="Hello world!",
            delay_seconds=0.01
        )
        
        await generator.generate_text_response(options, config)
        
        # Should send 12 text.delta events (one for each character)
        # plus one text.done event
        assert mock_websocket_utils.safe_send_event.call_count == 13
        
        # Check first delta event
        first_call = mock_websocket_utils.safe_send_event.call_args_list[0]
        first_event = first_call[0][1]
        assert first_event["type"] == ServerEventType.RESPONSE_TEXT_DELTA
        assert first_event["response_id"] == "test_response_123"
        assert first_event["delta"] == "H"
        
        # Check text.done event
        last_call = mock_websocket_utils.safe_send_event.call_args_list[-1]
        last_event = last_call[0][1]
        assert last_event["type"] == ServerEventType.RESPONSE_TEXT_DONE
        assert last_event["text"] == "Hello world!"

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_generate_text_response_empty_text(self, mock_websocket_utils):
        """Test text response generation with empty text."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        generator._active_response_id = "test_response_123"
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        options = ResponseCreateOptions()
        config = LocalResponseConfig(text="")
        
        await generator.generate_text_response(options, config)
        
        # Should only send text.done event
        assert mock_websocket_utils.safe_send_event.call_count == 1
        
        event = mock_websocket_utils.safe_send_event.call_args[0][1]
        assert event["type"] == ServerEventType.RESPONSE_TEXT_DONE
        assert event["text"] == ""

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_generate_audio_response_with_audio_data(self, mock_websocket_utils):
        """Test audio response generation with raw audio data."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        generator._active_response_id = "test_response_123"
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        options = ResponseCreateOptions()
        audio_data = b"audio_data_here" * 100  # 1400 bytes
        config = LocalResponseConfig(
            audio_data=audio_data,
            audio_chunk_delay=0.01
        )
        
        await generator.generate_audio_response(options, config)
        
        # Should send audio.delta events for each chunk plus audio.done
        # 1400 bytes / 3200 bytes per chunk = 1 chunk
        assert mock_websocket_utils.safe_send_event.call_count == 2
        
        # Check first delta event
        first_call = mock_websocket_utils.safe_send_event.call_args_list[0]
        first_event = first_call[0][1]
        assert first_event["type"] == ServerEventType.RESPONSE_AUDIO_DELTA
        assert first_event["response_id"] == "test_response_123"
        assert base64.b64decode(first_event["delta"]) == audio_data

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_generate_audio_response_with_audio_file(self, mock_websocket_utils):
        """Test audio response generation with audio file."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        generator._active_response_id = "test_response_123"
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        # Mock audio manager
        audio_manager = Mock()
        audio_data = b"file_audio_data" * 200  # 2800 bytes
        audio_manager.load_audio_file = AsyncMock(return_value=audio_data)
        generator.audio_manager = audio_manager
        
        options = ResponseCreateOptions()
        config = LocalResponseConfig(
            audio_file="test_audio.wav",
            audio_chunk_delay=0.01
        )
        
        await generator.generate_audio_response(options, config)
        
        # Verify audio manager was called
        audio_manager.load_audio_file.assert_called_once_with("test_audio.wav")
        
        # Should send audio.delta events for each chunk plus audio.done
        # 2800 bytes / 3200 bytes per chunk = 1 chunk
        assert mock_websocket_utils.safe_send_event.call_count == 2

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_generate_audio_response_fallback_silence(self, mock_websocket_utils):
        """Test audio response generation with fallback silence."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        generator._active_response_id = "test_response_123"
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        # Mock audio manager with silence generation
        audio_manager = Mock()
        silence_data = b"\x00" * 32000  # 2 seconds of silence
        audio_manager._generate_silence.return_value = silence_data
        generator.audio_manager = audio_manager
        
        options = ResponseCreateOptions()
        config = LocalResponseConfig(audio_chunk_delay=0.01)
        
        await generator.generate_audio_response(options, config)
        
        # Verify silence was generated
        audio_manager._generate_silence.assert_called_once()
        
        # Should send audio.delta events for each chunk plus audio.done
        # 32000 bytes / 3200 bytes per chunk = 10 chunks
        assert mock_websocket_utils.safe_send_event.call_count == 11

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_generate_audio_response_no_audio_manager(self, mock_websocket_utils):
        """Test audio response generation without audio manager."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        generator._active_response_id = "test_response_123"
        generator.audio_manager = None
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        options = ResponseCreateOptions()
        config = LocalResponseConfig(audio_chunk_delay=0.01)
        
        await generator.generate_audio_response(options, config)
        
        # Should use fallback silence (32000 bytes)
        # 32000 bytes / 3200 bytes per chunk = 10 chunks
        assert mock_websocket_utils.safe_send_event.call_count == 11

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_generate_function_call_with_config(self, mock_websocket_utils):
        """Test function call generation with configured function call."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        generator._active_response_id = "test_response_123"
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        options = ResponseCreateOptions()
        config = LocalResponseConfig(
            function_call={
                "name": "test_function",
                "arguments": {"param1": "value1", "param2": 123}
            }
        )
        
        await generator.generate_function_call(options, config)
        
        # Should send function_call_arguments.delta and function_call_arguments.done
        assert mock_websocket_utils.safe_send_event.call_count == 2
        
        # Check delta event
        delta_call = mock_websocket_utils.safe_send_event.call_args_list[0]
        delta_event = delta_call[0][1]
        assert delta_event["type"] == ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA
        assert delta_event["response_id"] == "test_response_123"
        
        # Check done event
        done_call = mock_websocket_utils.safe_send_event.call_args_list[1]
        done_event = done_call[0][1]
        assert done_event["type"] == ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE
        assert done_event["response_id"] == "test_response_123"

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_generate_function_call_default(self, mock_websocket_utils):
        """Test function call generation with default function call."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        generator._active_response_id = "test_response_123"
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        options = ResponseCreateOptions()
        config = LocalResponseConfig()  # No function_call configured
        
        await generator.generate_function_call(options, config)
        
        # Should send function_call_arguments.delta and function_call_arguments.done
        assert mock_websocket_utils.safe_send_event.call_count == 2
        
        # Check that default function call was used
        done_call = mock_websocket_utils.safe_send_event.call_args_list[1]
        done_event = done_call[0][1]
        arguments = json.loads(done_event["arguments"])
        assert arguments["param1"] == "value1"
        assert arguments["param2"] == "value2"

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_generate_response_done(self, mock_websocket_utils):
        """Test response done generation."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        generator._active_response_id = "test_response_123"
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        await generator.generate_response_done()
        
        # Should send response.done event
        assert mock_websocket_utils.safe_send_event.call_count == 1
        
        event = mock_websocket_utils.safe_send_event.call_args[0][1]
        assert event["type"] == ServerEventType.RESPONSE_DONE
        assert event["response"]["id"] == "test_response_123"
        assert "created_at" in event["response"]

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_send_error(self, mock_websocket_utils):
        """Test error event sending."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        await generator.send_error("test_error", "Test error message", {"detail": "test"})
        
        # Should send error event
        assert mock_websocket_utils.safe_send_event.call_count == 1
        
        event = mock_websocket_utils.safe_send_event.call_args[0][1]
        assert event["type"] == ServerEventType.ERROR
        assert event["code"] == "test_error"
        assert event["message"] == "Test error message"
        assert event["details"] == {"detail": "test"}

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_send_error_without_details(self, mock_websocket_utils):
        """Test error event sending without details."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        await generator.send_error("test_error", "Test error message")
        
        event = mock_websocket_utils.safe_send_event.call_args[0][1]
        assert event["type"] == ServerEventType.ERROR
        assert event["code"] == "test_error"
        assert event["message"] == "Test error message"
        assert "details" not in event

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_send_transcript_delta(self, mock_websocket_utils):
        """Test transcript delta sending."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        generator._active_response_id = "test_response_123"
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        await generator.send_transcript_delta("Hello", final=False)
        
        # Should send transcript delta event
        assert mock_websocket_utils.safe_send_event.call_count == 1
        
        event = mock_websocket_utils.safe_send_event.call_args[0][1]
        assert event["type"] == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA
        assert event["response_id"] == "test_response_123"
        assert event["delta"] == "Hello"

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_send_transcript_delta_final(self, mock_websocket_utils):
        """Test transcript delta sending with final flag."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        generator._active_response_id = "test_response_123"
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        await generator.send_transcript_delta("Hello world", final=True)
        
        # Should send both delta and done events
        assert mock_websocket_utils.safe_send_event.call_count == 2
        
        # Check done event
        done_event = mock_websocket_utils.safe_send_event.call_args_list[1][0][1]
        assert done_event["type"] == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DONE
        assert done_event["transcript"] == "Hello world"

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_send_input_transcript_delta(self, mock_websocket_utils):
        """Test input transcript delta sending."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        item_id = "test_item_123"
        await generator.send_input_transcript_delta(item_id, "User input", final=False)
        
        # Should send input transcript delta event
        assert mock_websocket_utils.safe_send_event.call_count == 1
        
        event = mock_websocket_utils.safe_send_event.call_args[0][1]
        assert event["type"] == ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_DELTA
        assert event["item_id"] == item_id
        assert event["delta"] == "User input"

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_send_input_transcript_delta_final(self, mock_websocket_utils):
        """Test input transcript delta sending with final flag."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        item_id = "test_item_123"
        await generator.send_input_transcript_delta(item_id, "Complete input", final=True)
        
        # Should send both delta and completed events
        assert mock_websocket_utils.safe_send_event.call_count == 2
        
        # Check completed event
        completed_event = mock_websocket_utils.safe_send_event.call_args_list[1][0][1]
        assert completed_event["type"] == ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED
        assert completed_event["transcript"] == "Complete input"

    @pytest.mark.asyncio
    @patch('opusagent.utils.websocket_utils.WebSocketUtils')
    async def test_send_input_transcript_failed(self, mock_websocket_utils):
        """Test input transcript failed sending."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        
        mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
        
        item_id = "test_item_123"
        error = {"code": "transcription_failed", "message": "Failed to transcribe"}
        
        await generator.send_input_transcript_failed(item_id, error)
        
        # Should send failed event
        assert mock_websocket_utils.safe_send_event.call_count == 1
        
        event = mock_websocket_utils.safe_send_event.call_args[0][1]
        assert event["type"] == ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_FAILED
        assert event["item_id"] == item_id
        assert event["error"] == error

    @pytest.mark.asyncio
    async def test_audio_chunking_large_file(self):
        """Test audio chunking with large audio data."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        generator._active_response_id = "test_response_123"
        
        # Create large audio data
        audio_data = b"audio_chunk" * 1000  # 11000 bytes
        
        with patch('opusagent.utils.websocket_utils.WebSocketUtils') as mock_websocket_utils:
            mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
            
            options = ResponseCreateOptions()
            config = LocalResponseConfig(audio_data=audio_data, audio_chunk_delay=0.01)
            
            await generator.generate_audio_response(options, config)
            
            # 11000 bytes / 3200 bytes per chunk = 4 chunks (rounded up)
            # Plus 1 audio.done event
            assert mock_websocket_utils.safe_send_event.call_count == 5

    @pytest.mark.asyncio
    async def test_text_streaming_timing(self):
        """Test text streaming timing with delays."""
        generator = ResponseGenerator()
        generator._ws = Mock()
        generator._active_response_id = "test_response_123"
        
        with patch('opusagent.utils.websocket_utils.WebSocketUtils') as mock_websocket_utils:
            mock_websocket_utils.safe_send_event = AsyncMock(return_value=True)
            
            options = ResponseCreateOptions()
            config = LocalResponseConfig(
                text="Hi",
                delay_seconds=0.1
            )
            
            start_time = asyncio.get_event_loop().time()
            await generator.generate_text_response(options, config)
            end_time = asyncio.get_event_loop().time()
            
            # Should take at least 0.2 seconds (2 characters * 0.1s delay)
            assert end_time - start_time >= 0.2 