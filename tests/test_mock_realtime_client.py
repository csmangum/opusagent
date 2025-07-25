#!/usr/bin/env python3
"""
Unit tests for LocalRealtimeClient.
"""

import asyncio
import base64
import json
import logging
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import websockets

from opusagent.local.realtime.client import LocalRealtimeClient
from opusagent.models.openai_api import (
    ClientEventType,
    ResponseCreateOptions,
    ServerEventType,
    SessionConfig,
)


class TestLocalRealtimeClient(unittest.TestCase):
    """Test cases for LocalRealtimeClient."""

    def assert_sent_event(self, mock_ws, event_type):
        """Helper function to find and assert a specific event was sent.

        Args:
            mock_ws: The mock WebSocket object
            event_type: The event type to look for

        Returns:
            The found event data

        Raises:
            AssertionError: If the event is not found
        """
        for call_args in mock_ws.send.call_args_list:
            event = json.loads(call_args[0][0])
            if event["type"] == event_type:
                return event

        self.fail(f"{event_type} event not found in sent messages")

    def setUp(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger("test")
        self.logger.setLevel(logging.DEBUG)

        # Create a mock WebSocket
        self.mock_ws = AsyncMock()
        self.mock_ws.__aiter__.return_value = []
        # Ensure the websocket is seen as open by the new logic
        self.mock_ws.closed = False
        self.mock_ws.close_code = None

        # Create an async mock for websockets.connect that returns our mock WebSocket
        self.mock_connect = AsyncMock(return_value=self.mock_ws)

        # Create client with mock WebSocket
        with patch("websockets.connect", self.mock_connect):
            self.client = LocalRealtimeClient(logger=self.logger)
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.client.connect())

    def tearDown(self):
        """Tear down test fixtures."""
        self.loop.run_until_complete(self.client.disconnect())
        self.loop.close()

    def test_initialization(self):
        """Test client initialization."""
        session_state = self.client.get_session_state()
        self.assertIsNotNone(session_state["session_id"])
        self.assertIsNotNone(session_state["conversation_id"])
        self.assertTrue(self.client.connected)
        self.assertIsNotNone(self.client._ws)

    def test_session_created_event(self):
        """Test session.created event is sent on connect."""
        # Get the first message sent to WebSocket
        call_args = self.mock_ws.send.call_args_list[0][0][0]
        event = json.loads(call_args)

        self.assertEqual(event["type"], ServerEventType.SESSION_CREATED)
        self.assertIn("session", event)
        session_state = self.client.get_session_state()
        self.assertEqual(event["session"]["id"], session_state["session_id"])

    def test_session_update(self):
        """Test session update handling."""
        # Create test session config
        config = SessionConfig(
            modalities=["text", "audio"], model="gpt-4", voice="alloy"
        )

        # Send session update
        update_event = {
            "type": ClientEventType.SESSION_UPDATE,
            "session": config.model_dump(),
        }

        self.loop.run_until_complete(self.client.handle_session_update(update_event))

        # Verify session.updated event was sent
        call_args = self.mock_ws.send.call_args_list[-1][0][0]
        event = json.loads(call_args)

        self.assertEqual(event["type"], ServerEventType.SESSION_UPDATED)
        self.assertEqual(event["session"]["model"], "gpt-4")
        self.assertEqual(event["session"]["voice"], "alloy")

    def test_audio_buffer_append(self):
        """Test audio buffer append handling."""
        # Create test audio data
        audio_data = b"\x00" * 1000
        audio_b64 = base64.b64encode(audio_data).decode("utf-8")

        # Send audio append event
        append_event = {
            "type": ClientEventType.INPUT_AUDIO_BUFFER_APPEND,
            "audio": audio_b64,
        }

        self.loop.run_until_complete(self.client.handle_audio_append(append_event))

        # Verify audio was added to buffer
        audio_buffer = self.client.get_audio_buffer()
        self.assertEqual(len(audio_buffer), 1)
        self.assertEqual(audio_buffer[0], audio_data)

    def test_audio_buffer_commit(self):
        """Test audio buffer commit handling."""
        # Add some audio to buffer
        self.client.set_audio_buffer([b"\x00" * 1000])

        # Send commit event
        commit_event = {"type": ClientEventType.INPUT_AUDIO_BUFFER_COMMIT}

        self.loop.run_until_complete(self.client.handle_audio_commit(commit_event))

        # Verify committed event was sent
        call_args = self.mock_ws.send.call_args_list[-1][0][0]
        event = json.loads(call_args)

        self.assertEqual(event["type"], ServerEventType.INPUT_AUDIO_BUFFER_COMMITTED)
        self.assertIn("item_id", event)

        # Verify buffer was cleared
        audio_buffer = self.client.get_audio_buffer()
        self.assertEqual(len(audio_buffer), 0)

    def test_response_create_text(self):
        """Test text response creation."""
        # Create response options
        options = ResponseCreateOptions(modalities=["text"], temperature=0.7)

        # Send response create event
        create_event = {
            "type": ClientEventType.RESPONSE_CREATE,
            "response": options.model_dump(),
        }

        self.loop.run_until_complete(self.client._handle_response_create(create_event))

        # Verify response.created event was sent
        response_created_event = self.assert_sent_event(
            self.mock_ws, ServerEventType.RESPONSE_CREATED
        )
        self.assertIn("response", response_created_event)  # type: ignore
        self.assertIn("id", response_created_event["response"])  # type: ignore

    def test_response_create_audio(self):
        """Test audio response creation."""
        # Create response options
        options = ResponseCreateOptions(modalities=["audio"], voice="alloy")

        # Send response create event
        create_event = {
            "type": ClientEventType.RESPONSE_CREATE,
            "response": options.model_dump(),
        }

        self.loop.run_until_complete(self.client._handle_response_create(create_event))

        # Verify response.created event was sent
        response_created_event = self.assert_sent_event(
            self.mock_ws, ServerEventType.RESPONSE_CREATED
        )
        self.assertIn("response", response_created_event)  # type: ignore
        self.assertIn("id", response_created_event["response"])  # type: ignore

    def test_response_cancel(self):
        """Test response cancellation."""
        # Set up active response
        self.client.set_active_response_id("test_response_id")

        # Send cancel event
        cancel_event = {
            "type": ClientEventType.RESPONSE_CANCEL,
            "response_id": "test_response_id",
        }

        self.loop.run_until_complete(self.client.handle_response_cancel(cancel_event))

        # Verify response.cancelled event was sent
        response_cancelled_event = self.assert_sent_event(
            self.mock_ws, ServerEventType.RESPONSE_CANCELLED
        )
        self.assertEqual(response_cancelled_event["response_id"], "test_response_id")  # type: ignore

        # Verify active response was cleared
        self.assertIsNone(self.client.get_active_response_id())

    def test_error_sending(self):
        """Test error event sending."""
        # Send error
        self.loop.run_until_complete(
            self.client.send_error(
                code="test_error",
                message="Test error message",
                details={"key": "value"},
            )
        )

        # Verify error event was sent
        call_args = self.mock_ws.send.call_args_list[-1][0][0]
        event = json.loads(call_args)

        self.assertEqual(event["type"], ServerEventType.ERROR)
        self.assertEqual(event["code"], "test_error")
        self.assertEqual(event["message"], "Test error message")
        self.assertEqual(event["details"], {"key": "value"})

    def test_rate_limits(self):
        """Test rate limits update."""
        # Create test limits
        limits = [{"type": "tokens", "limit": 1000, "remaining": 500}]

        # Send rate limits
        self.loop.run_until_complete(self.client.send_rate_limits(limits))

        # Verify rate_limits.updated event was sent
        call_args = self.mock_ws.send.call_args_list[-1][0][0]
        event = json.loads(call_args)

        self.assertEqual(event["type"], ServerEventType.RATE_LIMITS_UPDATED)
        self.assertEqual(event["rate_limits"], limits)

    def test_transcript_delta(self):
        """Test transcript delta sending."""
        # Set up active response
        self.client.set_active_response_id("test_response_id")

        # Send transcript delta
        self.loop.run_until_complete(
            self.client.send_transcript_delta("Test transcript", final=True)
        )

        # Verify transcript events were sent
        call_args = self.mock_ws.send.call_args_list[-1][0][0]
        event = json.loads(call_args)

        self.assertEqual(event["type"], ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DONE)
        self.assertEqual(event["transcript"], "Test transcript")

    def test_input_transcript(self):
        """Test input transcript handling."""
        # Send input transcript
        self.loop.run_until_complete(
            self.client.send_input_transcript_delta(
                item_id="test_item", text="Test input transcript", final=True
            )
        )

        # Verify transcript events were sent
        call_args = self.mock_ws.send.call_args_list[-1][0][0]
        event = json.loads(call_args)

        self.assertEqual(
            event["type"],
            ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED,
        )
        self.assertEqual(event["transcript"], "Test input transcript")

    def test_content_part_handling(self):
        """Test content part handling."""
        # Set up active response
        self.client.set_active_response_id("test_response_id")

        # Create test part
        part = {"type": "text", "text": "Test content"}

        # Send content part added
        self.loop.run_until_complete(self.client.send_content_part_added(part))

        # Verify content part added event was sent
        call_args = self.mock_ws.send.call_args_list[-1][0][0]
        event = json.loads(call_args)

        self.assertEqual(event["type"], ServerEventType.RESPONSE_CONTENT_PART_ADDED)
        self.assertEqual(event["part"], part)

        # Send content part done
        self.loop.run_until_complete(self.client.send_content_part_done(part))

        # Verify content part done event was sent
        call_args = self.mock_ws.send.call_args_list[-1][0][0]
        event = json.loads(call_args)

        self.assertEqual(event["type"], ServerEventType.RESPONSE_CONTENT_PART_DONE)
        self.assertEqual(event["part"], part)
        self.assertEqual(event["status"], "completed")


if __name__ == "__main__":
    unittest.main()
