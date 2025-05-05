import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from fastagent.telephony_realtime_bridge import (
    initialize_session,
    send_initial_conversation_item,
)


def test_index_page(test_client):
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Telephony Bridge is running!"}


@pytest.mark.asyncio
async def test_send_initial_conversation_item():
    # Create mock websocket
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()

    # Call the function
    await send_initial_conversation_item(mock_ws)

    # Verify two calls - one for conversation item, one for response creation
    assert mock_ws.send.call_count == 2

    # Get first call args - conversation item
    call_args_1 = mock_ws.send.call_args_list[0].args[0]
    conversation_data = json.loads(call_args_1)

    # Verify the conversation item structure
    assert conversation_data["type"] == "conversation.item.create"
    assert "item" in conversation_data
    assert conversation_data["item"]["role"] == "user"
    assert "content" in conversation_data["item"]

    # Get second call args - response creation
    call_args_2 = mock_ws.send.call_args_list[1].args[0]
    response_data = json.loads(call_args_2)

    # Verify response creation
    assert response_data["type"] == "response.create"
