"""Unit tests for the EventRouter class.

This module contains tests for the event routing functionality, including
telephony and realtime event handling, error cases, and edge cases.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from opusagent.event_router import EventRouter
from opusagent.models.audiocodes_api import TelephonyEventType
from opusagent.models.openai_api import LogEventType, ServerEventType

@pytest.fixture
def event_router():
    """Create an EventRouter instance for testing."""
    return EventRouter()

@pytest.fixture
def mock_telephony_handler():
    """Create a mock telephony event handler."""
    return AsyncMock()

@pytest.fixture
def mock_realtime_handler():
    """Create a mock realtime event handler."""
    return AsyncMock()

@pytest.fixture
def mock_log_handler():
    """Create a mock log event handler."""
    return AsyncMock()

class TestEventRouter:
    """Test suite for the EventRouter class."""

    def test_init(self, event_router):
        """Test EventRouter initialization."""
        assert isinstance(event_router.telephony_handlers, dict)
        assert isinstance(event_router.realtime_handlers, dict)
        assert isinstance(event_router.log_event_types, list)
        assert len(event_router.log_event_types) > 0
        assert LogEventType.ERROR in event_router.log_event_types

    def test_register_platform_handler(self, event_router, mock_telephony_handler):
        """Test registering a telephony event handler."""
        event_router.register_platform_handler(
            TelephonyEventType.SESSION_INITIATE, mock_telephony_handler
        )
        assert event_router.telephony_handlers[TelephonyEventType.SESSION_INITIATE] == mock_telephony_handler

    def test_register_realtime_handler(self, event_router, mock_realtime_handler):
        """Test registering a realtime event handler."""
        event_router.register_realtime_handler(
            ServerEventType.SESSION_CREATED, mock_realtime_handler
        )
        assert event_router.realtime_handlers[ServerEventType.SESSION_CREATED] == mock_realtime_handler

    def test_get_platform_event_type_valid(self, event_router):
        """Test converting a valid telephony event type string."""
        event_type = event_router._get_platform_event_type("session.initiate")
        assert event_type == TelephonyEventType.SESSION_INITIATE

    def test_get_platform_event_type_invalid(self, event_router):
        """Test converting an invalid telephony event type string."""
        event_type = event_router._get_platform_event_type("invalid.event")
        assert event_type is None

    @pytest.mark.asyncio
    async def test_handle_platform_event_valid(self, event_router, mock_telephony_handler):
        """Test handling a valid telephony event."""
        event_router.register_platform_handler(
            TelephonyEventType.SESSION_INITIATE, mock_telephony_handler
        )
        data = {"type": "session.initiate", "conversationId": "test-123"}
        await event_router.handle_platform_event(data)
        mock_telephony_handler.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_handle_platform_event_invalid(self, event_router):
        """Test handling an invalid telephony event."""
        data = {"type": "invalid.event"}
        await event_router.handle_platform_event(data)
        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_handle_platform_event_no_handler(self, event_router):
        """Test handling a telephony event with no registered handler."""
        data = {"type": "session.initiate"}
        await event_router.handle_platform_event(data)
        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_handle_realtime_event_valid(self, event_router, mock_realtime_handler):
        """Test handling a valid realtime event."""
        event_router.register_realtime_handler(
            ServerEventType.SESSION_CREATED, mock_realtime_handler
        )
        data = {"type": ServerEventType.SESSION_CREATED, "session": {"id": "test-123"}}
        await event_router.handle_realtime_event(data)
        mock_realtime_handler.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_handle_realtime_event_invalid(self, event_router):
        """Test handling an invalid realtime event."""
        data = {"type": "invalid.event"}
        await event_router.handle_realtime_event(data)
        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_handle_realtime_event_no_handler(self, event_router):
        """Test handling a realtime event with no registered handler."""
        data = {"type": ServerEventType.SESSION_CREATED}
        await event_router.handle_realtime_event(data)
        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_handle_log_event_error(self, event_router):
        """Test handling an error log event."""
        data = {
            "type": "error",
            "code": "test_error",
            "message": "Test error message",
            "details": {"key": "value"}
        }
        await event_router.handle_log_event(data)
        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_handle_log_event_response_done_success(self, event_router):
        """Test handling a successful response.done log event."""
        data = {
            "type": "response.done",
            "response": {
                "status": "success",
                "id": "test-123"
            }
        }
        await event_router.handle_log_event(data)
        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_handle_log_event_response_done_quota_error(self, event_router):
        """Test handling a response.done log event with quota error."""
        data = {
            "type": "response.done",
            "response": {
                "status": "failed",
                "status_details": {
                    "error": {
                        "type": "insufficient_quota",
                        "code": "insufficient_quota",
                        "message": "Quota exceeded"
                    }
                },
                "usage": {
                    "total_tokens": 1000,
                    "input_tokens": 400,
                    "output_tokens": 600
                }
            }
        }
        await event_router.handle_log_event(data)
        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_handle_log_event_response_done_other_error(self, event_router):
        """Test handling a response.done log event with other error."""
        data = {
            "type": "response.done",
            "response": {
                "status": "failed",
                "status_details": {
                    "error": {
                        "type": "other_error",
                        "code": "other_error",
                        "message": "Other error"
                    }
                }
            }
        }
        await event_router.handle_log_event(data)
        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_handle_telephony_event_with_audio_chunk(self, event_router, mock_telephony_handler):
        """Test handling a telephony event with audio chunk."""
        event_router.register_platform_handler(
            TelephonyEventType.USER_STREAM_CHUNK, mock_telephony_handler
        )
        data = {
            "type": "userStream.chunk",
            "audioChunk": "base64_encoded_audio_data"
        }
        await event_router.handle_platform_event(data)
        mock_telephony_handler.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_handle_realtime_event_with_detailed_logging(self, event_router, mock_realtime_handler):
        """Test handling a realtime event that triggers detailed logging."""
        event_router.register_realtime_handler(
            ServerEventType.RESPONSE_CREATED, mock_realtime_handler
        )
        data = {
            "type": ServerEventType.RESPONSE_CREATED,
            "response": {
                "id": "test-123",
                "status": "in_progress"
            }
        }
        await event_router.handle_realtime_event(data)
        mock_realtime_handler.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_handle_realtime_event_function_call(self, event_router, mock_realtime_handler):
        """Test handling a realtime event for function calls."""
        event_router.register_realtime_handler(
            ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA, mock_realtime_handler
        )
        data = {
            "type": ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA,
            "delta": "function argument data"
        }
        await event_router.handle_realtime_event(data)
        mock_realtime_handler.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_handle_realtime_event_handler_error(self, event_router, mock_realtime_handler):
        """Test handling an error in a realtime event handler."""
        event_router.register_realtime_handler(
            ServerEventType.SESSION_CREATED, mock_realtime_handler
        )
        mock_realtime_handler.side_effect = Exception("Test error")
        data = {"type": ServerEventType.SESSION_CREATED}
        await event_router.handle_realtime_event(data)
        # Should not raise any exceptions, error should be logged

    @pytest.mark.asyncio
    async def test_handle_platform_event_handler_error(self, event_router, mock_telephony_handler):
        """Test handling an error in a telephony event handler."""
        event_router.register_platform_handler(
            TelephonyEventType.SESSION_INITIATE, mock_telephony_handler
        )
        mock_telephony_handler.side_effect = Exception("Test error")
        data = {"type": "session.initiate"}
        await event_router.handle_platform_event(data)
        # Should not raise any exceptions, error should be logged 