import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from fastagent.telephony_realtime_bridge import app, initialize_session, send_initial_conversation_item


@pytest.fixture
def test_client():
    return TestClient(app)


def test_index_page(test_client):
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Telephony Bridge is running!"}


@pytest.mark.asyncio
async def test_initialize_session():
    # Create mock websocket
    mock_ws = AsyncMock()
    
    # Call the function
    await initialize_session(mock_ws)
    
    # Verify the session update was sent with correct format
    assert mock_ws.send.call_count == 3
    
    # Get the first call args - session update
    call_args_1 = mock_ws.send.call_args_list[0].args[0]
    session_data = json.loads(call_args_1)
    
    # Verify the session update structure
    assert session_data["type"] == "session.update"
    assert "session" in session_data
    assert session_data["session"]["input_audio_format"] == "g711_ulaw"
    assert session_data["session"]["output_audio_format"] == "g711_ulaw"
    assert "voice" in session_data["session"]
    assert "instructions" in session_data["session"]
    assert "modalities" in session_data["session"]
    assert "temperature" in session_data["session"]
    
    # Get the second call args - conversation item
    call_args_2 = mock_ws.send.call_args_list[1].args[0]
    conversation_data = json.loads(call_args_2)
    
    # Verify the conversation item structure
    assert conversation_data["type"] == "conversation.item.create"
    assert "item" in conversation_data
    assert conversation_data["item"]["role"] == "user"
    assert "content" in conversation_data["item"]
    
    # Get the third call args - response creation
    call_args_3 = mock_ws.send.call_args_list[2].args[0]
    response_data = json.loads(call_args_3)
    
    # Verify response creation
    assert response_data["type"] == "response.create"


@pytest.mark.asyncio
async def test_send_initial_conversation_item():
    # Create mock websocket
    mock_ws = AsyncMock()
    
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


@pytest.mark.asyncio
@patch("fastagent.bot.telephony_realtime_bridge.websockets.connect")
@patch("fastagent.bot.telephony_realtime_bridge.initialize_session")
@patch("fastagent.bot.telephony_realtime_bridge.TelephonyRealtimeBridge")
async def test_handle_media_stream(mock_bridge_class, mock_initialize, mock_connect, test_client):
    # Setup mocks
    mock_ws_client = AsyncMock()
    mock_openai_ws = AsyncMock()
    mock_connect.return_value.__aenter__.return_value = mock_openai_ws
    
    mock_bridge = AsyncMock()
    mock_bridge_class.return_value = mock_bridge
    
    # Setup gather to run once and then complete
    mock_gather_result = AsyncMock()
    
    async def mock_gather(*args, **kwargs):
        # Just return a completed future
        return mock_gather_result
    
    with patch("fastagent.bot.telephony_realtime_bridge.asyncio.gather", mock_gather):
        # We can't easily test the websocket endpoint with TestClient
        # This is a simplified test of the handler's logic
        from fastagent.telephony_realtime_bridge import handle_media_stream
        
        # Create a mock WebSocket
        mock_websocket = AsyncMock()
        
        # Execute the handler (with patched dependencies)
        await handle_media_stream(mock_websocket)
        
        # Verify the websocket was accepted
        mock_websocket.accept.assert_called_once()
        
        # Verify OpenAI connection was established with correct parameters
        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        assert call_args[0][0] == "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        assert call_args[1]["subprotocols"] == ["realtime"]
        assert "Authorization" in call_args[1]["additional_headers"]
        assert "OpenAI-Beta" in call_args[1]["additional_headers"]
        
        # Verify session was initialized
        mock_initialize.assert_called_once_with(mock_openai_ws)
        
        # Verify bridge was created and used
        mock_bridge_class.assert_called_once_with(mock_websocket, mock_openai_ws)
        # Verify bridge was closed
        mock_bridge.close.assert_called_once()


@pytest.mark.asyncio
@patch("fastagent.bot.telephony_realtime_bridge.websockets.connect")
async def test_handle_media_stream_connection_error(mock_connect, test_client):
    # Setup mock to raise an exception
    mock_connect.side_effect = Exception("Connection failed")
    
    # We can't easily test the websocket endpoint with TestClient
    # This is a simplified test of the handler's error handling
    from fastagent.telephony_realtime_bridge import handle_media_stream
    
    # Create a mock WebSocket
    mock_websocket = AsyncMock()
    
    # Execute the handler (with patched dependencies)
    await handle_media_stream(mock_websocket)
    
    # Verify the websocket was accepted and then closed on error
    mock_websocket.accept.assert_called_once()
    mock_websocket.close.assert_called_once() 