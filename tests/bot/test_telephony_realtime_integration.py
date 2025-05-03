import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastagent.telephony_realtime_bridge import TelephonyRealtimeBridge, initialize_session, send_initial_conversation_item


class MockWebSocket:
    """Mock WebSocket that simulates real client behavior with predefined messages."""
    
    def __init__(self, incoming_messages=None):
        self.incoming_messages = incoming_messages or []
        self.outgoing_messages = []
        self.closed = False
        self.accept_called = False
    
    async def accept(self):
        self.accept_called = True
    
    async def close(self):
        self.closed = True
    
    async def send_json(self, data):
        self.outgoing_messages.append(data)
    
    async def iter_text(self):
        for message in self.incoming_messages:
            yield json.dumps(message) if isinstance(message, dict) else message
    
    def get_received_audio_payloads(self):
        """Extract audio payloads from received messages."""
        return [
            msg["media"]["payload"] 
            for msg in self.outgoing_messages 
            if isinstance(msg, dict) and msg.get("event") == "media"
        ]


class MockOpenAIWebSocket:
    """Mock OpenAI WebSocket that simulates the OpenAI API with predefined responses."""
    
    def __init__(self, responses=None):
        self.responses = responses or []
        self.sent_messages = []
        self.close_code = None
        self.closed = False
    
    async def send(self, message):
        self.sent_messages.append(json.loads(message) if isinstance(message, str) else message)
    
    async def close(self):
        self.closed = True
        self.close_code = 1000
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if not self.responses:
            raise StopAsyncIteration
        
        response = self.responses.pop(0)
        return json.dumps(response) if isinstance(response, dict) else response
    
    def get_audio_inputs(self):
        """Extract audio inputs from sent messages."""
        return [
            msg["audio"] 
            for msg in self.sent_messages 
            if isinstance(msg, dict) and msg.get("type") == "input_audio_buffer.append"
        ]


@pytest.mark.asyncio
async def test_bridge_full_flow():
    """Test the full flow of audio from client to OpenAI and back."""
    # Setup mock client messages
    client_messages = [
        {"event": "start", "start": {"streamSid": "test-stream-id"}},
        {"event": "media", "media": {"payload": "client-audio-1"}},
        {"event": "media", "media": {"payload": "client-audio-2"}},
        {"event": "stop"}
    ]
    
    # Setup mock OpenAI responses
    openai_responses = [
        {"type": "session.created", "session": {"id": "session-123"}},
        {"type": "response.audio.delta", "delta": "ai-audio-1"},
        {"type": "response.audio.delta", "delta": "ai-audio-2"},
        {"type": "response.content.done", "content": "Done speaking"}
    ]
    
    # Create mock objects
    mock_client = MockWebSocket(client_messages)
    mock_openai = MockOpenAIWebSocket(openai_responses)
    
    # Create the bridge
    bridge = TelephonyRealtimeBridge(mock_client, mock_openai)
    
    # Run both tasks
    await asyncio.gather(
        bridge.receive_from_telephony(),
        bridge.send_to_telephony()
    )
    
    # Verify the bridge closed connections
    assert bridge._closed
    assert mock_client.closed
    assert mock_openai.closed
    
    # Verify audio was sent to OpenAI
    audio_inputs = mock_openai.get_audio_inputs()
    assert len(audio_inputs) == 2
    assert "client-audio-1" in audio_inputs
    assert "client-audio-2" in audio_inputs
    
    # Verify audio responses were sent to client
    audio_outputs = mock_client.get_received_audio_payloads()
    assert len(audio_outputs) == 2
    assert "ai-audio-1" in audio_outputs
    assert "ai-audio-2" in audio_outputs


@pytest.mark.asyncio
@patch("websockets.connect")
async def test_integration_with_mocked_connection(mock_connect):
    """Test integration of the bridge with handle_media_stream handler."""
    from fastagent.telephony_realtime_bridge import handle_media_stream
    
    # Setup mock client messages
    client_messages = [
        {"event": "start", "start": {"streamSid": "test-stream-id"}},
        {"event": "media", "media": {"payload": "client-audio-1"}},
        {"event": "stop"}
    ]
    
    # Setup mock OpenAI responses
    openai_responses = [
        {"type": "session.created", "session": {"id": "session-123"}},
        {"type": "response.audio.delta", "delta": "ai-audio-1"},
        {"type": "response.content.done", "content": "Done speaking"}
    ]
    
    # Create mocks
    mock_client = MockWebSocket(client_messages)
    mock_openai = MockOpenAIWebSocket(openai_responses)
    
    # Configure the websocket connection mock
    mock_connect.return_value.__aenter__.return_value = mock_openai
    
    # Run the handler with our mock client
    with patch("fastagent.bot.telephony_realtime_bridge.asyncio.gather") as mock_gather:
        # Make gather actually run the tasks
        async def mock_gather_impl(*args, **kwargs):
            results = []
            for task in args:
                results.append(await task)
            return results
            
        mock_gather.side_effect = mock_gather_impl
        
        # Call the handler
        await handle_media_stream(mock_client)
    
    # Verify client accepted and closed
    assert mock_client.accept_called
    assert mock_client.closed
    
    # Verify connection established with correct parameters
    mock_connect.assert_called_once()
    call_args = mock_connect.call_args
    assert "wss://api.openai.com/v1/realtime" in call_args[0][0]
    
    # Verify session initialization messages were sent
    session_updates = [
        msg for msg in mock_openai.sent_messages 
        if isinstance(msg, dict) and msg.get("type") == "session.update"
    ]
    assert len(session_updates) == 1
    
    # Verify initial conversation was sent
    conversation_items = [
        msg for msg in mock_openai.sent_messages 
        if isinstance(msg, dict) and msg.get("type") == "conversation.item.create"
    ]
    assert len(conversation_items) == 1
    
    # Verify audio was processed in both directions
    assert len(mock_openai.get_audio_inputs()) > 0
    assert len(mock_client.get_received_audio_payloads()) > 0 