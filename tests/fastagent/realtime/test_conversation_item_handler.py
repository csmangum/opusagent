import pytest
from unittest.mock import AsyncMock, MagicMock
import time

from fastagent.realtime.handlers.client.conversation_item_handler import (
    ConversationItemHandler,
)


@pytest.fixture
def send_event_mock():
    return AsyncMock()


@pytest.fixture
def handler(send_event_mock):
    return ConversationItemHandler(send_event_mock)


def test_init(handler, send_event_mock):
    """Test that the handler initializes properly."""
    assert handler.conversation_items == {}
    assert handler.conversation_order == []
    assert handler.send_event == send_event_mock


@pytest.mark.asyncio
async def test_handle_create_auto_id(handler, send_event_mock):
    """Test creating a conversation item with auto-generated ID."""
    event = {
        "event_id": "test_event_1",
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [{"type": "text", "text": "Hello world"}],
        },
    }

    await handler.handle_create(event)

    # Check that the item was created with auto-generated ID
    assert len(handler.conversation_items) == 1
    item_id = list(handler.conversation_items.keys())[0]
    assert item_id.startswith("item_")

    # Check that the order was updated
    assert handler.conversation_order == [item_id]

    # Check that the event was sent
    send_event_mock.assert_called_once()
    call_args = send_event_mock.call_args[0][0]
    assert call_args["type"] == "conversation.item.created"
    assert call_args["event_id"] == "test_event_1"
    assert call_args["item"]["role"] == "user"
    assert call_args["item"]["type"] == "message"


@pytest.mark.asyncio
async def test_handle_create_client_id(handler, send_event_mock):
    """Test creating a conversation item with client-provided ID."""
    event = {
        "event_id": "test_event_2",
        "type": "conversation.item.create",
        "item": {
            "id": "msg_custom_id",
            "type": "message",
            "role": "user",
            "content": [{"type": "text", "text": "Hello with custom ID"}],
        },
    }

    await handler.handle_create(event)

    # Check that the item was created with the provided ID
    assert "msg_custom_id" in handler.conversation_items
    assert handler.conversation_items["msg_custom_id"]["role"] == "user"

    # Check that the order was updated
    assert handler.conversation_order == ["msg_custom_id"]


@pytest.mark.asyncio
async def test_handle_create_at_beginning(handler, send_event_mock):
    """Test creating a conversation item at the beginning (root)."""
    # First create a regular item
    await handler.handle_create(
        {
            "event_id": "test_event_3",
            "type": "conversation.item.create",
            "item": {
                "id": "msg_first",
                "type": "message",
                "role": "user",
                "content": [{"type": "text", "text": "First message"}],
            },
        }
    )

    # Reset mock to clear previous calls
    send_event_mock.reset_mock()

    # Now create an item at the beginning
    await handler.handle_create(
        {
            "event_id": "test_event_4",
            "type": "conversation.item.create",
            "previous_item_id": "root",
            "item": {
                "id": "msg_root",
                "type": "message",
                "role": "system",
                "content": [{"type": "text", "text": "System prompt"}],
            },
        }
    )

    # Check the order
    assert handler.conversation_order == ["msg_root", "msg_first"]


@pytest.mark.asyncio
async def test_handle_create_in_middle(handler, send_event_mock):
    """Test creating a conversation item in the middle."""
    # Create two items
    await handler.handle_create(
        {"item": {"id": "msg_1", "type": "message", "role": "user", "content": []}}
    )
    await handler.handle_create(
        {"item": {"id": "msg_3", "type": "message", "role": "user", "content": []}}
    )

    # Reset mock to clear previous calls
    send_event_mock.reset_mock()

    # Insert between them
    await handler.handle_create(
        {
            "previous_item_id": "msg_1",
            "item": {
                "id": "msg_2",
                "type": "message",
                "role": "assistant",
                "content": [],
            },
        }
    )

    # Check the order
    assert handler.conversation_order == ["msg_1", "msg_2", "msg_3"]


@pytest.mark.asyncio
async def test_handle_create_invalid_previous_item(handler, send_event_mock):
    """Test creating an item with invalid previous_item_id."""
    await handler.handle_create(
        {
            "event_id": "test_event_5",
            "previous_item_id": "non_existent_id",
            "item": {
                "id": "msg_error",
                "type": "message",
                "role": "user",
                "content": [],
            },
        }
    )

    # Check that the error was sent
    send_event_mock.assert_called_with(
        {
            "type": "error",
            "event_id": "test_event_5",
            "code": "invalid_request_error",
            "message": "Previous item non_existent_id not found",
        }
    )

    # Check that the item was not added
    assert "msg_error" not in handler.conversation_items


@pytest.mark.asyncio
async def test_handle_retrieve_existing(handler, send_event_mock):
    """Test retrieving an existing conversation item."""
    # Create an item first
    await handler.handle_create(
        {
            "item": {
                "id": "msg_to_retrieve",
                "type": "message",
                "role": "user",
                "content": [],
            }
        }
    )

    # Reset the mock to clear previous calls
    send_event_mock.reset_mock()

    # Retrieve the item
    await handler.handle_retrieve(
        {
            "event_id": "retrieve_event",
            "type": "conversation.item.retrieve",
            "item_id": "msg_to_retrieve",
        }
    )

    # Check that the correct event was sent
    send_event_mock.assert_called_once()
    call_args = send_event_mock.call_args[0][0]
    assert call_args["type"] == "conversation.item.retrieved"
    assert call_args["event_id"] == "retrieve_event"
    assert call_args["item"]["id"] == "msg_to_retrieve"


@pytest.mark.asyncio
async def test_handle_retrieve_nonexistent(handler, send_event_mock):
    """Test retrieving a non-existent conversation item."""
    await handler.handle_retrieve(
        {
            "event_id": "retrieve_event_error",
            "type": "conversation.item.retrieve",
            "item_id": "non_existent_msg",
        }
    )

    # Check that the error was sent
    send_event_mock.assert_called_with(
        {
            "type": "error",
            "event_id": "retrieve_event_error",
            "code": "invalid_request_error",
            "message": "Conversation item non_existent_msg not found",
        }
    )


@pytest.mark.asyncio
async def test_handle_truncate_success(handler, send_event_mock):
    """Test truncating audio content successfully."""
    # Create an assistant message with audio content
    await handler.handle_create(
        {
            "item": {
                "id": "msg_with_audio",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "audio",
                        "audio": "base64data",
                        "audio_duration_ms": 5000,
                        "text": "This is the transcript",
                    }
                ],
            }
        }
    )

    send_event_mock.reset_mock()

    # Truncate the audio
    await handler.handle_truncate(
        {
            "event_id": "truncate_event",
            "type": "conversation.item.truncate",
            "item_id": "msg_with_audio",
            "content_index": 0,
            "audio_end_ms": 2000,
        }
    )

    # Check that the audio was truncated
    item = handler.conversation_items["msg_with_audio"]
    assert item["content"][0]["audio_truncated_ms"] == 2000
    assert "text" not in item["content"][0]

    # Check that the correct event was sent
    send_event_mock.assert_called_once()
    call_args = send_event_mock.call_args[0][0]
    assert call_args["type"] == "conversation.item.truncated"


@pytest.mark.asyncio
async def test_handle_truncate_non_assistant_message(handler, send_event_mock):
    """Test truncating a non-assistant message."""
    # Create a user message
    await handler.handle_create(
        {
            "item": {
                "id": "user_msg",
                "type": "message",
                "role": "user",
                "content": [{"type": "text", "text": "Hello"}],
            }
        }
    )

    send_event_mock.reset_mock()

    # Try to truncate it
    await handler.handle_truncate(
        {"event_id": "truncate_error", "item_id": "user_msg", "content_index": 0, "audio_end_ms": 1000}
    )

    # Check that the error was sent
    send_event_mock.assert_called_with(
        {
            "type": "error",
            "event_id": "truncate_error",
            "code": "invalid_request_error",
            "message": "Only assistant message items can be truncated",
        }
    )


@pytest.mark.asyncio
async def test_handle_truncate_invalid_content_index(handler, send_event_mock):
    """Test truncating with invalid content index."""
    # Create an assistant message
    await handler.handle_create(
        {
            "item": {
                "id": "assistant_msg",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "Hello"}],
            }
        }
    )

    send_event_mock.reset_mock()

    # Try to truncate with invalid index
    await handler.handle_truncate(
        {
            "event_id": "truncate_index_error",
            "item_id": "assistant_msg",
            "content_index": 999,
            "audio_end_ms": 1000
        }
    )

    # Check that the error was sent
    send_event_mock.assert_called_with(
        {
            "type": "error",
            "event_id": "truncate_index_error",
            "code": "invalid_request_error",
            "message": "Content index 999 is out of bounds",
        }
    )


@pytest.mark.asyncio
async def test_handle_truncate_exceeding_duration(handler, send_event_mock):
    """Test truncating with audio_end_ms exceeding duration."""
    # Create an assistant message with audio content
    await handler.handle_create(
        {
            "item": {
                "id": "msg_audio_short",
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "audio", "audio": "base64data", "audio_duration_ms": 1000}
                ],
            }
        }
    )

    send_event_mock.reset_mock()

    # Try to truncate with too large duration
    await handler.handle_truncate(
        {
            "event_id": "truncate_duration_error",
            "item_id": "msg_audio_short",
            "content_index": 0,
            "audio_end_ms": 2000,
        }
    )

    # Check that the error was sent
    send_event_mock.assert_called_with(
        {
            "type": "error",
            "event_id": "truncate_duration_error",
            "code": "invalid_request_error",
            "message": "audio_end_ms 2000 exceeds audio duration 1000",
        }
    )


@pytest.mark.asyncio
async def test_handle_delete_success(handler, send_event_mock):
    """Test deleting a conversation item successfully."""
    # Create an item
    await handler.handle_create(
        {
            "item": {
                "id": "msg_to_delete",
                "type": "message",
                "role": "user",
                "content": [],
            }
        }
    )

    send_event_mock.reset_mock()

    # Delete the item
    await handler.handle_delete(
        {
            "event_id": "delete_event",
            "type": "conversation.item.delete",
            "item_id": "msg_to_delete",
        }
    )

    # Check that the item was deleted
    assert "msg_to_delete" not in handler.conversation_items
    assert "msg_to_delete" not in handler.conversation_order

    # Check that the correct event was sent
    send_event_mock.assert_called_once()
    call_args = send_event_mock.call_args[0][0]
    assert call_args["type"] == "conversation.item.deleted"
    assert call_args["item_id"] == "msg_to_delete"


@pytest.mark.asyncio
async def test_handle_delete_nonexistent(handler, send_event_mock):
    """Test deleting a non-existent conversation item."""
    await handler.handle_delete(
        {
            "event_id": "delete_error",
            "type": "conversation.item.delete",
            "item_id": "non_existent_msg",
        }
    )

    # Check that the error was sent
    send_event_mock.assert_called_with(
        {
            "type": "error",
            "event_id": "delete_error",
            "code": "invalid_request_error",
            "message": "Conversation item non_existent_msg not found",
        }
    )
