"""
Unit tests for the Twilio Realtime Bridge module.

These tests validate the TwilioRealtimeBridge class functionality including
WebSocket communication, event handling, audio processing, and session management.
"""

import asyncio
import base64
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from opusagent.models.openai_api import ServerEventType
from opusagent.models.twilio_api import TwilioEventType, ConnectedMessage, StartMessage, MediaMessage, StopMessage, DTMFMessage, MarkMessage
from opusagent.twilio_realtime_bridge import TwilioRealtimeBridge

# Test SIDs - Using clearly fake test values
TEST_ACCOUNT_SID = "ACtest1234567890abcdef1234567890abcdef"
TEST_CALL_SID = "CAtest1234567890abcdef1234567890abcdef"
TEST_STREAM_SID = "MStest1234567890abcdef1234567890abcdef"

class TestTwilioRealtimeBridge:
    """Tests for the TwilioRealtimeBridge class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Use MagicMock without spec to allow __bool__ override
        self.twilio_websocket = MagicMock()
        # Make async methods return AsyncMocks
        self.twilio_websocket.send_json = AsyncMock()
        self.twilio_websocket.iter_text = AsyncMock()
        self.twilio_websocket.close = AsyncMock()
        # Make the mock truthy
        self.twilio_websocket.__bool__ = MagicMock(return_value=True)

        self.realtime_websocket = AsyncMock()
        self.realtime_websocket.close_code = None

        # Create bridge instance
        self.bridge = TwilioRealtimeBridge(
            twilio_websocket=self.twilio_websocket,
            realtime_websocket=self.realtime_websocket,
        )

    def test_initialization(self):
        """Test that the bridge initializes correctly."""
        assert self.bridge.twilio_websocket == self.twilio_websocket
        assert self.bridge.realtime_websocket == self.realtime_websocket
        assert self.bridge.stream_sid is None
        assert self.bridge.account_sid is None
        assert self.bridge.call_sid is None
        assert self.bridge.media_format is None
        assert self.bridge.session_initialized is False
        assert self.bridge.speech_detected is False
        assert self.bridge._closed is False
        assert self.bridge.audio_chunks_sent == 0
        assert self.bridge.total_audio_bytes_sent == 0
        assert self.bridge.audio_buffer == []
        assert self.bridge.input_transcript_buffer == []
        assert self.bridge.output_transcript_buffer == []
        assert self.bridge.mark_counter == 0
        assert self.bridge.function_handler is not None

    def test_event_handler_mappings(self):
        """Test that event handler mappings are properly configured."""
        # Test Twilio event handler mappings
        assert TwilioEventType.CONNECTED in self.bridge.twilio_event_handlers
        assert TwilioEventType.START in self.bridge.twilio_event_handlers
        assert TwilioEventType.MEDIA in self.bridge.twilio_event_handlers
        assert TwilioEventType.STOP in self.bridge.twilio_event_handlers
        assert TwilioEventType.DTMF in self.bridge.twilio_event_handlers
        assert TwilioEventType.MARK in self.bridge.twilio_event_handlers

        # Test OpenAI event handler mappings
        assert ServerEventType.SESSION_UPDATED in self.bridge.realtime_event_handlers
        assert ServerEventType.SESSION_CREATED in self.bridge.realtime_event_handlers
        assert (
            ServerEventType.RESPONSE_AUDIO_DELTA in self.bridge.realtime_event_handlers
        )
        assert ServerEventType.RESPONSE_DONE in self.bridge.realtime_event_handlers

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Test that the close method properly closes both WebSocket connections."""
        # Mock the WebSocketState to properly test the close method
        with patch("starlette.websockets.WebSocketState") as mock_state:
            # Set up the mock so that DISCONNECTED comparison returns False
            mock_state.DISCONNECTED = "disconnected"
            self.twilio_websocket.client_state = "connected"  # Not DISCONNECTED

            # Test normal close
            await self.bridge.close()

            assert self.bridge._closed is True
            self.realtime_websocket.close.assert_called_once()
            self.twilio_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_with_exceptions(self):
        """Test that close method handles exceptions gracefully."""
        # Mock exceptions during close
        self.realtime_websocket.close.side_effect = Exception("OpenAI close error")
        self.twilio_websocket.close.side_effect = Exception("Twilio close error")

        # Mock the WebSocketState to properly test the close method
        with patch("starlette.websockets.WebSocketState") as mock_state:
            mock_state.DISCONNECTED = "disconnected"
            self.twilio_websocket.client_state = "connected"

            # Should not raise exceptions
            await self.bridge.close()

            assert self.bridge._closed is True

    def test_is_websocket_closed(self):
        """Test WebSocket closed state detection."""
        # Test with mock WebSocket state
        with patch("starlette.websockets.WebSocketState") as mock_state:
            mock_state.DISCONNECTED = "disconnected"
            self.twilio_websocket.client_state = "disconnected"

            result = self.bridge._is_websocket_closed()
            assert result is True

        # Test fallback without WebSocketState
        with patch("starlette.websockets.WebSocketState", side_effect=ImportError):
            self.bridge.twilio_websocket = None
            result = self.bridge._is_websocket_closed()
            assert result is True

    @pytest.mark.asyncio
    async def test_handle_connected(self):
        """Test handling of Twilio connected message."""
        data = {"event": "connected", "protocol": "Call", "version": "1.0.0"}

        await self.bridge.handle_connected(data)
        # Should not raise exceptions and log the connection info

    @pytest.mark.asyncio
    async def test_handle_start(self):
        """Test handling of Twilio start message."""
        data = {
            "event": "start",
            "sequenceNumber": "1",
            "streamSid": TEST_STREAM_SID,
            "start": {
                "streamSid": TEST_STREAM_SID,
                "accountSid": TEST_ACCOUNT_SID,
                "callSid": TEST_CALL_SID,
                "tracks": ["inbound", "outbound"],
                "customParameters": {},
                "mediaFormat": {
                    "encoding": "audio/x-mulaw",
                    "sampleRate": 8000,
                    "channels": 1,
                },
            },
        }

        with patch.object(self.bridge, "initialize_openai_session") as mock_init:
            await self.bridge.handle_start(data)

        assert self.bridge.stream_sid == TEST_STREAM_SID
        assert self.bridge.account_sid == TEST_ACCOUNT_SID
        assert self.bridge.call_sid == TEST_CALL_SID
        assert self.bridge.media_format == "audio/x-mulaw"
        mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_media(self):
        """Test handling of Twilio media message with audio data."""
        # Create test audio data
        test_audio = b"test audio data"
        audio_b64 = base64.b64encode(test_audio).decode("utf-8")

        data = {
            "event": "media",
            "sequenceNumber": "2",
            "streamSid": TEST_STREAM_SID,
            "media": {
                "track": "inbound",
                "chunk": "1",
                "timestamp": "1000",
                "payload": audio_b64,
            },
        }

        with patch.object(self.bridge, "_convert_mulaw_to_pcm16") as mock_convert:
            mock_convert.return_value = b"converted pcm16 data"

            await self.bridge.handle_media(data)

            # Should buffer the audio
            assert len(self.bridge.audio_buffer) == 1
            assert self.bridge.audio_buffer[0] == test_audio

    @pytest.mark.asyncio
    async def test_handle_media_with_buffering(self):
        """Test media handling with audio buffering and processing."""
        # Fill buffer to trigger processing
        test_audio = b"test"
        audio_b64 = base64.b64encode(test_audio).decode("utf-8")

        data = {
            "event": "media",
            "sequenceNumber": "2",
            "streamSid": TEST_STREAM_SID,
            "media": {
                "track": "inbound",
                "chunk": "1",
                "timestamp": "1000",
                "payload": audio_b64,
            },
        }

        # Pre-fill buffer to reach processing threshold
        self.bridge.audio_buffer = [test_audio] * 9  # 9 + 1 = 10, triggers processing

        with patch.object(self.bridge, "_convert_mulaw_to_pcm16") as mock_convert:
            mock_convert.return_value = b"converted pcm16 data"

            await self.bridge.handle_media(data)

            # Buffer should be cleared after processing
            assert len(self.bridge.audio_buffer) == 0
            assert self.bridge.audio_chunks_sent == 1

            # Should send to OpenAI
            self.realtime_websocket.send.assert_called()

    @pytest.mark.asyncio
    async def test_handle_stop(self):
        """Test handling of Twilio stop message."""
        data = {
            "event": "stop",
            "sequenceNumber": "5",
            "streamSid": TEST_STREAM_SID,
            "stop": {
                "accountSid": TEST_ACCOUNT_SID,
                "callSid": TEST_CALL_SID,
            },
        }

        # Add some audio to buffer
        self.bridge.audio_buffer = [b"test"]

        with patch.object(self.bridge, "_commit_audio_buffer") as mock_commit:
            with patch.object(self.bridge, "close") as mock_close:
                await self.bridge.handle_stop(data)

                mock_commit.assert_called_once()
                mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_dtmf(self):
        """Test handling of Twilio DTMF message."""
        data = {
            "event": "dtmf",
            "streamSid": TEST_STREAM_SID,
            "sequenceNumber": "3",
            "dtmf": {"track": "inbound_track", "digit": "5"},
        }

        await self.bridge.handle_dtmf(data)
        # Should not raise exceptions and log the DTMF digit

    @pytest.mark.asyncio
    async def test_handle_mark(self):
        """Test handling of Twilio mark message."""
        data = {
            "event": "mark",
            "sequenceNumber": "4",
            "streamSid": TEST_STREAM_SID,
            "mark": {"name": "test_mark"},
        }

        await self.bridge.handle_mark(data)
        # Should not raise exceptions and log the mark completion

    def test_convert_mulaw_to_pcm16_with_audioop(self):
        """Test mulaw to PCM16 conversion with audioop."""
        test_mulaw = b"\x7f\x80\x00\xff"

        with patch("audioop.ulaw2lin") as mock_ulaw2lin:
            mock_ulaw2lin.return_value = b"converted pcm16"

            result = self.bridge._convert_mulaw_to_pcm16(test_mulaw)

            mock_ulaw2lin.assert_called_once_with(test_mulaw, 2)
            assert result == b"converted pcm16"

    def test_convert_mulaw_to_pcm16_fallback(self):
        """Test mulaw to PCM16 conversion fallback without audioop."""
        test_mulaw = b"\x7f\x80"

        with patch("audioop.ulaw2lin", side_effect=ImportError):
            result = self.bridge._convert_mulaw_to_pcm16(test_mulaw)

            # Fallback should repeat each byte twice
            expected = b"\x7f\x7f\x80\x80"
            assert result == expected

    def test_convert_pcm16_to_mulaw_with_audioop(self):
        """Test PCM16 to mulaw conversion with audioop."""
        test_pcm16 = b"\x00\x7f\x80\x00"

        with patch("audioop.lin2ulaw") as mock_lin2ulaw:
            mock_lin2ulaw.return_value = b"converted mulaw"

            result = self.bridge._convert_pcm16_to_mulaw(test_pcm16)

            mock_lin2ulaw.assert_called_once_with(test_pcm16, 2)
            assert result == b"converted mulaw"

    def test_convert_pcm16_to_mulaw_fallback(self):
        """Test PCM16 to mulaw conversion fallback without audioop."""
        test_pcm16 = b"\x00\x7f\x80\x00"

        with patch("audioop.lin2ulaw", side_effect=ImportError):
            result = self.bridge._convert_pcm16_to_mulaw(test_pcm16)

            # Fallback should take every other byte
            expected = b"\x00\x80"
            assert result == expected

    @pytest.mark.asyncio
    async def test_commit_audio_buffer(self):
        """Test committing audio buffer to OpenAI."""
        self.bridge.audio_buffer = [b"test1", b"test2"]

        with patch.object(self.bridge, "_convert_mulaw_to_pcm16") as mock_convert:
            with patch.object(self.bridge, "_trigger_response") as mock_trigger:
                mock_convert.return_value = b"converted audio"

                await self.bridge._commit_audio_buffer()

                # Should send audio and commit to OpenAI
                assert self.realtime_websocket.send.call_count == 2  # append + commit
                mock_trigger.assert_called_once()
                assert len(self.bridge.audio_buffer) == 0

    @pytest.mark.asyncio
    async def test_trigger_response(self):
        """Test triggering response from OpenAI."""
        await self.bridge._trigger_response()

        # Should send response creation request
        self.realtime_websocket.send.assert_called_once()
        call_args = self.realtime_websocket.send.call_args[0][0]
        response_data = json.loads(call_args)

        assert response_data["type"] == "response.create"
        assert "audio" in response_data["response"]["modalities"]
        assert response_data["response"]["voice"] == "alloy"

    @pytest.mark.asyncio
    async def test_handle_session_update(self):
        """Test handling of OpenAI session update events."""
        # Test session updated
        response_dict = {"type": "session.updated"}
        await self.bridge.handle_session_update(response_dict)

        # Test session created
        response_dict = {"type": "session.created"}
        with patch.object(self.bridge, "send_initial_conversation_item") as mock_send:
            await self.bridge.handle_session_update(response_dict)

            assert self.bridge.session_initialized is True
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_speech_detection(self):
        """Test handling of speech detection events."""
        # Test speech started
        response_dict = {"type": "input_audio_buffer.speech_started"}
        await self.bridge.handle_speech_detection(response_dict)
        assert self.bridge.speech_detected is True

        # Test speech stopped
        response_dict = {"type": "input_audio_buffer.speech_stopped"}
        await self.bridge.handle_speech_detection(response_dict)
        assert self.bridge.speech_detected is False

        # Test buffer committed
        response_dict = {"type": "input_audio_buffer.committed"}
        await self.bridge.handle_speech_detection(response_dict)

    @pytest.mark.asyncio
    async def test_handle_audio_response_delta(self):
        """Test handling of audio response delta from OpenAI."""
        self.bridge.stream_sid = TEST_STREAM_SID

        # Ensure bridge is not closed
        self.bridge._closed = False

        # Create test PCM16 audio data
        test_pcm16 = b"test pcm16 audio"
        pcm16_b64 = base64.b64encode(test_pcm16).decode("utf-8")

        response_dict = {
            "type": "response.audio.delta",
            "response_id": "resp_123",
            "item_id": "item_123",
            "output_index": 0,
            "content_index": 0,
            "delta": pcm16_b64,
        }

        # Mock both the websocket closed check and the conversion methods
        with patch.object(self.bridge, "_is_websocket_closed", return_value=False):
            with patch.object(self.bridge, "_resample_pcm16") as mock_resample:
                with patch.object(self.bridge, "_convert_pcm16_to_mulaw") as mock_convert:
                    # Mock resampling to return the same data
                    mock_resample.return_value = test_pcm16
                    mock_convert.return_value = b"converted mulaw"

                    await self.bridge.handle_audio_response_delta(response_dict)

                    # Verify resampling was called with correct parameters
                    mock_resample.assert_called_once_with(test_pcm16, 24000, 8000)
                    # Verify conversion was called with resampled data
                    mock_convert.assert_called_once_with(test_pcm16)
                    self.twilio_websocket.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_audio_response_delta_no_stream_sid(self):
        """Test audio response delta handling when no stream SID is available."""
        response_dict = {
            "type": "response.audio.delta",
            "response_id": "resp_123",
            "item_id": "item_123",
            "output_index": 0,
            "content_index": 0,
            "delta": base64.b64encode(b"test").decode("utf-8"),
        }

        # No stream SID set
        await self.bridge.handle_audio_response_delta(response_dict)

        # Should not send to Twilio
        self.twilio_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_audio_response_completion(self):
        """Test handling of audio response completion."""
        self.bridge.stream_sid = TEST_STREAM_SID

        response_dict = {"type": "response.audio.done"}

        await self.bridge.handle_audio_response_completion(response_dict)

        # Should send mark to Twilio
        self.twilio_websocket.send_json.assert_called_once()
        assert self.bridge.mark_counter == 1

    @pytest.mark.asyncio
    async def test_handle_transcript_events(self):
        """Test handling of transcript events."""
        # Test audio transcript delta
        response_dict = {"type": "response.audio_transcript.delta", "delta": "Hello"}
        await self.bridge.handle_audio_transcript_delta(response_dict)
        assert "Hello" in self.bridge.output_transcript_buffer

        # Test audio transcript done
        await self.bridge.handle_audio_transcript_done(response_dict)
        assert len(self.bridge.output_transcript_buffer) == 0

        # Test input audio transcription delta
        response_dict = {
            "type": "conversation.item.input_audio_transcription.delta",
            "delta": "Hi",
        }
        await self.bridge.handle_input_audio_transcription_delta(response_dict)
        assert "Hi" in self.bridge.input_transcript_buffer

        # Test input audio transcription completed
        await self.bridge.handle_input_audio_transcription_completed(response_dict)
        assert len(self.bridge.input_transcript_buffer) == 0

    @pytest.mark.asyncio
    async def test_handle_output_item_added_function_call(self):
        """Test handling of output item added events for function calls."""
        response_dict = {
            "type": "response.output_item.added",
            "response_id": "resp_123",
            "output_index": 0,
            "item": {
                "id": "item_123",
                "type": "function_call",
                "call_id": "call_123",
                "name": "test_function",
            },
        }

        await self.bridge.handle_output_item_added(response_dict)

        # Should track function call
        assert "call_123" in self.bridge.function_handler.active_function_calls
        func_call = self.bridge.function_handler.active_function_calls["call_123"]
        assert func_call["function_name"] == "test_function"

    def test_get_twilio_event_type(self):
        """Test conversion of string event types to TwilioEventType enum."""
        # Valid event type
        event_type = self.bridge._get_twilio_event_type("connected")
        assert event_type == TwilioEventType.CONNECTED

        # Invalid event type
        event_type = self.bridge._get_twilio_event_type("invalid")
        assert event_type is None

    @pytest.mark.asyncio
    async def test_receive_from_twilio(self):
        """Test receiving and processing messages from Twilio."""
        messages = [
            json.dumps({"event": "connected", "protocol": "Call", "version": "1.0.0"}),
            json.dumps(
                {
                    "event": "start",
                    "sequenceNumber": "1",
                    "streamSid": TEST_STREAM_SID,
                    "start": {
                        "streamSid": TEST_STREAM_SID,
                        "accountSid": TEST_ACCOUNT_SID,
                        "callSid": TEST_CALL_SID,
                        "tracks": ["inbound"],
                        "customParameters": {},
                        "mediaFormat": {
                            "encoding": "audio/x-mulaw",
                            "sampleRate": 8000,
                            "channels": 1,
                        },
                    },
                }
            ),
            json.dumps(
                {
                    "event": "stop",
                    "sequenceNumber": "2",
                    "streamSid": TEST_STREAM_SID,
                    "stop": {
                        "accountSid": TEST_ACCOUNT_SID,
                        "callSid": TEST_CALL_SID,
                    },
                }
            ),
        ]

        # Mock the async iterator directly
        async def async_iterator():
            for msg in messages:
                yield msg

        self.twilio_websocket.iter_text.return_value = async_iterator()

        # Since we can't easily mock the handlers without interfering with the actual execution,
        # let's just test that it processes without error and calls close on stop
        with patch.object(self.bridge, "close") as mock_close:
            await self.bridge.receive_from_twilio()
            # Should be called when processing stop event
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_receive_from_twilio_disconnect(self):
        """Test handling of Twilio WebSocket disconnect."""
        self.twilio_websocket.iter_text.side_effect = WebSocketDisconnect

        with patch.object(self.bridge, "close") as mock_close:
            await self.bridge.receive_from_twilio()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_receive_from_realtime(self):
        """Test receiving and processing events from OpenAI Realtime API."""
        messages = [
            json.dumps({"type": "session.created", "session": {"id": "sess_123"}}),
            json.dumps(
                {
                    "type": "response.audio.delta",
                    "response_id": "resp_123",
                    "item_id": "item_123",
                    "output_index": 0,
                    "content_index": 0,
                    "delta": "dGVzdA==",
                }
            ),
            json.dumps(
                {"type": "error", "code": "invalid_request", "message": "Test error"}
            ),
        ]

        # Create an async iterator that properly handles the websocket protocol
        async def async_iter(self):
            for msg in messages:
                yield msg

        # Mock the async iterator method
        self.realtime_websocket.__aiter__ = async_iter

        # Create mock handlers to track calls
        mock_session = AsyncMock()
        mock_audio = AsyncMock()
        mock_log = AsyncMock()

        # Update the handler mappings to use our mocks
        self.bridge.realtime_event_handlers[ServerEventType.SESSION_CREATED] = mock_session
        self.bridge.realtime_event_handlers[ServerEventType.RESPONSE_AUDIO_DELTA] = mock_audio

        # Mock the individual handler methods that will be called
        with patch.object(self.bridge, "handle_log_event", mock_log):
            await self.bridge.receive_from_realtime()

            # Check that handlers were called
            mock_session.assert_called_once()
            mock_audio.assert_called_once()
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_receive_from_realtime_connection_closed(self):
        """Test handling of OpenAI WebSocket connection closed."""
        import websockets

        async def async_iter():
            raise websockets.exceptions.ConnectionClosed(None, None)

        self.realtime_websocket.__aiter__ = async_iter

        with patch.object(self.bridge, "close") as mock_close:
            await self.bridge.receive_from_realtime()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_log_event(self):
        """Test handling of log events from OpenAI."""
        error_event = {
            "type": "error",
            "code": "invalid_request",
            "message": "Test error message",
        }

        await self.bridge.handle_log_event(error_event)
        # Should log error without raising exceptions

    @pytest.mark.asyncio
    async def test_initialize_openai_session(self):
        """Test initialization of OpenAI session."""
        await self.bridge.initialize_openai_session()

        # Should send session update to OpenAI
        self.realtime_websocket.send.assert_called_once()
        call_args = self.realtime_websocket.send.call_args[0][0]
        session_data = json.loads(call_args)

        assert session_data["type"] == "session.update"
        assert session_data["session"]["input_audio_format"] == "pcm16"
        assert session_data["session"]["output_audio_format"] == "pcm16"
        assert "tools" in session_data["session"]

    @pytest.mark.asyncio
    async def test_send_initial_conversation_item(self):
        """Test sending initial conversation item."""
        with patch.object(self.bridge, "_trigger_response") as mock_trigger:
            await self.bridge.send_initial_conversation_item()

            # Should send conversation item and trigger response
            assert self.realtime_websocket.send.call_count >= 1
            mock_trigger.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_in_media_processing(self):
        """Test error handling during media message processing."""
        # Invalid base64 payload that should trigger error handling
        data = {
            "event": "media",
            "sequenceNumber": "2",
            "streamSid": TEST_STREAM_SID,
            "media": {
                "track": "inbound",
                "chunk": "1",
                "timestamp": "1000",
                "payload": "invalid base64!",
            },
        }

        # The handle_media method should catch this exception and handle it gracefully
        # Since we don't want to modify the actual implementation, let's test that
        # invalid data doesn't crash the method
        try:
            await self.bridge.handle_media(data)
            # If we get here without exception, the error was handled
            assert True
        except Exception:
            # If an exception propagates up, the error handling is not working
            pytest.fail("handle_media should handle validation errors gracefully")

    @pytest.mark.asyncio
    async def test_audio_response_delta_with_closed_connection(self):
        """Test audio response delta handling when connection is closed."""
        self.bridge._closed = True

        response_dict = {
            "type": "response.audio.delta",
            "response_id": "resp_123",
            "item_id": "item_123",
            "output_index": 0,
            "content_index": 0,
            "delta": base64.b64encode(b"test").decode("utf-8"),
        }

        await self.bridge.handle_audio_response_delta(response_dict)

        # Should not send to Twilio when closed
        self.twilio_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_mark_generation(self):
        """Test that multiple marks generate unique identifiers."""
        self.bridge.stream_sid = TEST_STREAM_SID

        # Generate multiple marks
        for i in range(3):
            await self.bridge.handle_audio_response_completion({})

        assert self.bridge.mark_counter == 3
        assert self.twilio_websocket.send_json.call_count == 3

    def test_function_handler_integration(self):
        """Test that function handler is properly integrated."""
        assert self.bridge.function_handler is not None
        assert (
            self.bridge.function_handler.realtime_websocket == self.realtime_websocket
        )

        # Test that function call handlers are mapped
        assert (
            ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA
            in self.bridge.realtime_event_handlers
        )
        assert (
            ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE
            in self.bridge.realtime_event_handlers
        )


# Integration test class
class TestTwilioRealtimeBridgeIntegration:
    """Integration tests for TwilioRealtimeBridge."""

    def setup_method(self):
        """Set up integration test fixtures."""
        self.twilio_websocket = MagicMock()
        # Make async methods return AsyncMocks
        self.twilio_websocket.send_json = AsyncMock()
        self.twilio_websocket.iter_text = AsyncMock()
        self.twilio_websocket.close = AsyncMock()
        # Make the mock truthy so it doesn't fail the boolean check in handle_audio_response_delta
        self.twilio_websocket.__bool__ = MagicMock(return_value=True)

        self.realtime_websocket = AsyncMock()
        self.realtime_websocket.close_code = None

        self.bridge = TwilioRealtimeBridge(
            twilio_websocket=self.twilio_websocket,
            realtime_websocket=self.realtime_websocket,
        )

    @pytest.mark.asyncio
    async def test_full_call_flow(self):
        """Test a complete call flow from start to finish."""
        # 1. Connected
        await self.bridge.handle_connected(
            {"event": "connected", "protocol": "Call", "version": "1.0.0"}
        )

        # 2. Start
        with patch.object(self.bridge, "initialize_openai_session"):
            await self.bridge.handle_start(
                {
                    "event": "start",
                    "sequenceNumber": "1",
                    "streamSid": TEST_STREAM_SID,
                    "start": {
                        "streamSid": TEST_STREAM_SID,
                        "accountSid": TEST_ACCOUNT_SID,
                        "callSid": TEST_CALL_SID,
                        "tracks": ["inbound"],
                        "customParameters": {},
                        "mediaFormat": {
                            "encoding": "audio/x-mulaw",
                            "sampleRate": 8000,
                            "channels": 1,
                        },
                    },
                }
            )

        assert self.bridge.stream_sid == TEST_STREAM_SID

        # 3. Media processing
        test_audio = b"test"
        await self.bridge.handle_media(
            {
                "event": "media",
                "sequenceNumber": "2",
                "streamSid": TEST_STREAM_SID,
                "media": {
                    "track": "inbound",
                    "chunk": "1",
                    "timestamp": "1000",
                    "payload": base64.b64encode(test_audio).decode("utf-8"),
                },
            }
        )

        assert len(self.bridge.audio_buffer) == 1

        # 4. Stop
        with patch.object(self.bridge, "close"):
            await self.bridge.handle_stop(
                {
                    "event": "stop",
                    "sequenceNumber": "3",
                    "streamSid": TEST_STREAM_SID,
                    "stop": {
                        "accountSid": TEST_ACCOUNT_SID,
                        "callSid": TEST_CALL_SID,
                    },
                }
            )

    @pytest.mark.asyncio
    async def test_bidirectional_audio_flow(self):
        """Test bidirectional audio flow between Twilio and OpenAI."""
        self.bridge.stream_sid = TEST_STREAM_SID

        # Simulate audio from Twilio
        test_audio = b"test_audio"
        with patch.object(self.bridge, "_convert_mulaw_to_pcm16") as mock_mulaw_convert:
            mock_mulaw_convert.return_value = b"pcm16_data"

            # Fill buffer to trigger processing
            self.bridge.audio_buffer = [test_audio] * 10

            await self.bridge.handle_media(
                {
                    "event": "media",
                    "sequenceNumber": "2",
                    "streamSid": TEST_STREAM_SID,
                    "media": {
                        "track": "inbound",
                        "chunk": "1",
                        "timestamp": "1000",
                        "payload": base64.b64encode(test_audio).decode("utf-8"),
                    },
                }
            )

        # Simulate audio response from OpenAI
        pcm16_data = b"response_audio"
        # Mock the _is_websocket_closed method to return False
        with patch.object(self.bridge, "_is_websocket_closed", return_value=False):
            with patch.object(
                self.bridge, "_convert_pcm16_to_mulaw"
            ) as mock_pcm_convert:
                mock_pcm_convert.return_value = b"mulaw_data"

                await self.bridge.handle_audio_response_delta(
                    {
                        "type": "response.audio.delta",
                        "response_id": "resp_123",
                        "item_id": "item_123",
                        "output_index": 0,
                        "content_index": 0,
                        "delta": base64.b64encode(pcm16_data).decode("utf-8"),
                    }
                )

        # Verify both directions worked
        self.realtime_websocket.send.assert_called()  # Sent to OpenAI
        self.twilio_websocket.send_json.assert_called()  # Sent to Twilio
