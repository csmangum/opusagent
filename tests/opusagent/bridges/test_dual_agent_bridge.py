import asyncio
import json
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Dict, Any

from opusagent.bridges.dual_agent_bridge import DualAgentBridge
from opusagent.callers import CallerType
from opusagent.utils.call_recorder import AudioChannel, TranscriptType


class AsyncIterator:
    """Helper class to create async iterators for testing."""
    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


class MockWebSocket:
    """Mock websocket that properly implements async iteration."""
    def __init__(self, messages):
        self.messages = messages
        self.index = 0
        self.send_calls = []
        
    def __aiter__(self):
        return self
        
    async def __anext__(self):
        if self.index >= len(self.messages):
            raise StopAsyncIteration
        message = self.messages[self.index]
        self.index += 1
        return message
        
    async def send(self, message):
        self.send_calls.append(message)


@pytest.fixture
def mock_websocket_manager():
    """Mock websocket manager for testing."""
    manager = AsyncMock()
    manager.get_connection = AsyncMock()
    manager._create_connection = AsyncMock()
    return manager


@pytest.fixture
def mock_caller_connection():
    """Mock caller connection for testing."""
    connection = AsyncMock()
    connection.connection_id = "caller-conn-123"
    connection.websocket = AsyncMock()
    connection.close = AsyncMock()
    connection.mark_used = AsyncMock()
    return connection


@pytest.fixture
def mock_cs_connection():
    """Mock CS connection for testing."""
    connection = AsyncMock()
    connection.connection_id = "cs-conn-456"
    connection.websocket = AsyncMock()
    connection.close = AsyncMock()
    connection.mark_used = AsyncMock()
    return connection


@pytest.fixture
def mock_call_recorder():
    """Mock call recorder for testing."""
    recorder = AsyncMock()
    recorder.start_recording = AsyncMock()
    recorder.stop_recording = AsyncMock(return_value=True)
    recorder.get_recording_summary = MagicMock(return_value="Test summary")
    recorder.record_caller_audio = AsyncMock()
    recorder.record_bot_audio = AsyncMock()
    recorder.add_transcript = AsyncMock()
    return recorder


@pytest.fixture
def mock_caller_session_config():
    """Mock caller session configuration."""
    config = MagicMock()
    config.voice = "alloy"
    config.temperature = 0.8
    config.max_response_output_tokens = 1000
    config.model_dump = MagicMock(return_value={"voice": "alloy", "temperature": 0.8})
    return config


@pytest.fixture
def mock_cs_session_config():
    """Mock CS session configuration."""
    config = MagicMock()
    config.voice = "verse"
    config.temperature = 0.7
    config.max_response_output_tokens = 1500
    config.model_dump = MagicMock(return_value={"voice": "verse", "temperature": 0.7})
    return config


@pytest.fixture
def mock_function_handler():
    """Mock function handler for testing."""
    handler = AsyncMock()
    handler.active_function_calls = {}
    handler.handle_function_call_arguments_delta = AsyncMock()
    handler.handle_function_call_arguments_done = AsyncMock()
    return handler


@pytest.fixture
def mock_transcript_manager():
    """Mock transcript manager for testing."""
    manager = AsyncMock()
    manager.handle_output_transcript_delta = AsyncMock()
    manager.handle_output_transcript_completed = AsyncMock()
    return manager


@pytest.fixture
async def dual_agent_bridge(mock_caller_session_config, mock_cs_session_config):
    """Create a DualAgentBridge instance for testing."""
    with patch('opusagent.bridges.dual_agent_bridge.get_caller_config', return_value=mock_caller_session_config), \
         patch('opusagent.bridges.dual_agent_bridge.cs_session_config', mock_cs_session_config), \
         patch('opusagent.bridges.dual_agent_bridge.register_caller_functions'), \
         patch('opusagent.bridges.dual_agent_bridge.register_customer_service_functions'):
        
        bridge = DualAgentBridge(
            caller_type=CallerType.TYPICAL,
            scenario="banking_card_replacement",
            agent_type="banking",
            conversation_id="test-conv-123"
        )
        return bridge


class TestDualAgentBridgeInitialization:
    """Test DualAgentBridge initialization and setup."""

    @pytest.mark.asyncio
    async def test_bridge_initialization_defaults(self, mock_caller_session_config, mock_cs_session_config):
        """Test bridge initialization with default parameters."""
        with patch('opusagent.bridges.dual_agent_bridge.get_caller_config', return_value=mock_caller_session_config), \
             patch('opusagent.bridges.dual_agent_bridge.cs_session_config', mock_cs_session_config), \
             patch('opusagent.bridges.dual_agent_bridge.register_caller_functions'), \
             patch('opusagent.bridges.dual_agent_bridge.register_customer_service_functions'):
            
            bridge = DualAgentBridge()
            
            assert bridge.caller_type == CallerType.TYPICAL
            assert bridge.scenario == "banking_card_replacement"
            assert bridge.agent_type == "banking"
            assert bridge.conversation_id is not None
            assert isinstance(bridge.conversation_id, str)
            assert bridge.caller_connection is None
            assert bridge.cs_connection is None
            assert bridge._closed is False
            assert bridge._caller_ready is False
            assert bridge._cs_ready is False
            assert bridge._current_speaker is None
            assert bridge._waiting_for_response is False
            assert bridge.caller_audio_buffer == []
            assert bridge.cs_audio_buffer == []

    @pytest.mark.asyncio
    async def test_bridge_initialization_custom_params(self, mock_caller_session_config, mock_cs_session_config):
        """Test bridge initialization with custom parameters."""
        with patch('opusagent.bridges.dual_agent_bridge.get_caller_config', return_value=mock_caller_session_config), \
             patch('opusagent.bridges.dual_agent_bridge.get_insurance_session_config', return_value=mock_cs_session_config), \
             patch('opusagent.bridges.dual_agent_bridge.register_caller_functions'), \
             patch('opusagent.bridges.dual_agent_bridge.register_insurance_functions'):
            
            bridge = DualAgentBridge(
                caller_type=CallerType.FRUSTRATED,
                scenario="insurance_file_claim",
                agent_type="insurance",
                conversation_id="custom-conv-456"
            )
            
            assert bridge.caller_type == CallerType.FRUSTRATED
            assert bridge.scenario == "insurance_file_claim"
            assert bridge.agent_type == "insurance"
            assert bridge.conversation_id == "custom-conv-456"

    @pytest.mark.asyncio
    async def test_bridge_initialization_invalid_agent_type(self, mock_caller_session_config):
        """Test bridge initialization with invalid agent type."""
        with patch('opusagent.bridges.dual_agent_bridge.get_caller_config', return_value=mock_caller_session_config):
            with pytest.raises(ValueError, match="Unknown agent_type: invalid. Available: banking, insurance"):
                DualAgentBridge(agent_type="invalid")

    @pytest.mark.asyncio
    async def test_bridge_initialization_insurance_agent(self, mock_caller_session_config, mock_cs_session_config):
        """Test bridge initialization with insurance agent type."""
        with patch('opusagent.bridges.dual_agent_bridge.get_caller_config', return_value=mock_caller_session_config), \
             patch('opusagent.bridges.dual_agent_bridge.get_insurance_session_config', return_value=mock_cs_session_config), \
             patch('opusagent.bridges.dual_agent_bridge.register_caller_functions'), \
             patch('opusagent.bridges.dual_agent_bridge.register_insurance_functions'):
            
            bridge = DualAgentBridge(agent_type="insurance")
            assert bridge.agent_type == "insurance"


class TestDualAgentBridgeConnectionInitialization:
    """Test DualAgentBridge connection initialization."""

    @pytest.mark.asyncio
    async def test_initialize_connections_success(self, dual_agent_bridge, mock_websocket_manager, 
                                                mock_caller_connection, mock_cs_connection, mock_call_recorder, mock_function_handler, mock_transcript_manager):
        """Test successful connection initialization."""
        with patch('opusagent.bridges.dual_agent_bridge.get_websocket_manager', return_value=mock_websocket_manager), \
             patch('opusagent.bridges.dual_agent_bridge.CallRecorder', return_value=mock_call_recorder), \
             patch('opusagent.bridges.dual_agent_bridge.FunctionHandler', return_value=mock_function_handler), \
             patch('opusagent.bridges.dual_agent_bridge.TranscriptManager', return_value=mock_transcript_manager), \
             patch.object(dual_agent_bridge, '_initialize_caller_session', new_callable=AsyncMock) as mock_caller_init, \
             patch.object(dual_agent_bridge, '_initialize_cs_session', new_callable=AsyncMock) as mock_cs_init, \
             patch.object(dual_agent_bridge, '_handle_caller_messages', new_callable=AsyncMock) as mock_caller_handle, \
             patch.object(dual_agent_bridge, '_handle_cs_messages', new_callable=AsyncMock) as mock_cs_handle, \
             patch.object(dual_agent_bridge, '_manage_conversation_flow', new_callable=AsyncMock) as mock_manage:
            
            mock_websocket_manager.get_connection.side_effect = [mock_caller_connection, mock_cs_connection]
            
            # This will run until the asyncio.gather, which we'll mock to avoid infinite loop
            with patch('asyncio.gather', new_callable=AsyncMock) as mock_gather:
                await dual_agent_bridge.initialize_connections()
                
                # Verify connections were obtained
                assert mock_websocket_manager.get_connection.call_count == 2
                
                # Verify call recording was initialized
                mock_call_recorder.start_recording.assert_called_once()
                
                # Verify sessions were initialized
                mock_caller_init.assert_called_once()
                mock_cs_init.assert_called_once()
                
                # Verify message handling was started
                mock_gather.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_connections_same_connection_ids(self, dual_agent_bridge, mock_websocket_manager, 
                                                            mock_caller_connection, mock_call_recorder, mock_function_handler, mock_transcript_manager):
        """Test connection initialization when both connections have same ID."""
        # Create two connections with same ID
        mock_cs_connection = AsyncMock()
        mock_cs_connection.connection_id = mock_caller_connection.connection_id
        mock_cs_connection.websocket = AsyncMock()
        mock_cs_connection.close = AsyncMock()
        
        with patch('opusagent.bridges.dual_agent_bridge.get_websocket_manager', return_value=mock_websocket_manager), \
             patch('opusagent.bridges.dual_agent_bridge.CallRecorder', return_value=mock_call_recorder), \
             patch('opusagent.bridges.dual_agent_bridge.FunctionHandler', return_value=mock_function_handler), \
             patch('opusagent.bridges.dual_agent_bridge.TranscriptManager', return_value=mock_transcript_manager), \
             patch.object(dual_agent_bridge, '_initialize_caller_session', new_callable=AsyncMock), \
             patch.object(dual_agent_bridge, '_initialize_cs_session', new_callable=AsyncMock), \
             patch.object(dual_agent_bridge, '_handle_caller_messages', new_callable=AsyncMock), \
             patch.object(dual_agent_bridge, '_handle_cs_messages', new_callable=AsyncMock), \
             patch.object(dual_agent_bridge, '_manage_conversation_flow', new_callable=AsyncMock), \
             patch('asyncio.gather', new_callable=AsyncMock):
            
            mock_websocket_manager.get_connection.side_effect = [mock_caller_connection, mock_cs_connection]
            mock_websocket_manager._create_connection.return_value = mock_cs_connection
            
            await dual_agent_bridge.initialize_connections()
            
            # Verify a new connection was created for CS agent
            mock_websocket_manager._create_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_connections_error_handling(self, dual_agent_bridge, mock_websocket_manager):
        """Test connection initialization error handling."""
        with patch('opusagent.bridges.dual_agent_bridge.get_websocket_manager', return_value=mock_websocket_manager), \
             patch.object(dual_agent_bridge, 'close', new_callable=AsyncMock) as mock_close:
            
            mock_websocket_manager.get_connection.side_effect = Exception("Connection error")
            
            with pytest.raises(Exception, match="Connection error"):
                await dual_agent_bridge.initialize_connections()
            
            mock_close.assert_called_once()


class TestDualAgentBridgeCallRecording:
    """Test DualAgentBridge call recording functionality."""

    @pytest.mark.asyncio
    async def test_initialize_call_recording_success(self, dual_agent_bridge, mock_call_recorder, mock_transcript_manager):
        """Test successful call recording initialization."""
        with patch('opusagent.bridges.dual_agent_bridge.CallRecorder', return_value=mock_call_recorder), \
             patch('opusagent.bridges.dual_agent_bridge.TranscriptManager', return_value=mock_transcript_manager):
            
            result = await dual_agent_bridge._initialize_call_recording()
            
            assert result is True
            assert dual_agent_bridge.call_recorder == mock_call_recorder
            assert dual_agent_bridge.caller_transcript_manager is not None
            assert dual_agent_bridge.cs_transcript_manager is not None
            mock_call_recorder.start_recording.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_call_recording_failure(self, dual_agent_bridge):
        """Test call recording initialization failure."""
        with patch('opusagent.bridges.dual_agent_bridge.CallRecorder', side_effect=Exception("Recording error")):
            
            result = await dual_agent_bridge._initialize_call_recording()
            
            assert result is True  # Should continue without recording
            assert dual_agent_bridge.call_recorder is None
            assert dual_agent_bridge.caller_transcript_manager is None
            assert dual_agent_bridge.cs_transcript_manager is None


class TestDualAgentBridgeSessionInitialization:
    """Test DualAgentBridge session initialization."""

    @pytest.mark.asyncio
    async def test_initialize_caller_session_success(self, dual_agent_bridge, mock_caller_connection, mock_caller_session_config):
        """Test successful caller session initialization."""
        dual_agent_bridge.caller_connection = mock_caller_connection
        dual_agent_bridge.caller_session_config = mock_caller_session_config
        
        await dual_agent_bridge._initialize_caller_session()
        
        # Verify session update was sent
        mock_caller_connection.websocket.send.assert_called()
        calls = mock_caller_connection.websocket.send.call_args_list
        
        # Check session update message
        session_update = json.loads(calls[0][0][0])
        assert session_update["type"] == "session.update"
        
        # Check initial message
        initial_message = json.loads(calls[1][0][0])
        assert initial_message["type"] == "conversation.item.create"
        assert initial_message["item"]["role"] == "user"
        
        assert dual_agent_bridge._caller_ready is True

    @pytest.mark.asyncio
    async def test_initialize_caller_session_no_connection(self, dual_agent_bridge):
        """Test caller session initialization without connection."""
        dual_agent_bridge.caller_connection = None
        
        with pytest.raises(RuntimeError, match="Caller connection not available"):
            await dual_agent_bridge._initialize_caller_session()

    @pytest.mark.asyncio
    async def test_initialize_cs_session_success(self, dual_agent_bridge, mock_cs_connection, mock_cs_session_config):
        """Test successful CS session initialization."""
        dual_agent_bridge.cs_connection = mock_cs_connection
        dual_agent_bridge.cs_session_config = mock_cs_session_config
        
        await dual_agent_bridge._initialize_cs_session()
        
        # Verify session update was sent
        mock_cs_connection.websocket.send.assert_called()
        calls = mock_cs_connection.websocket.send.call_args_list
        
        # Check session update message
        session_update = json.loads(calls[0][0][0])
        assert session_update["type"] == "session.update"
        
        # Check initial message
        initial_message = json.loads(calls[1][0][0])
        assert initial_message["type"] == "conversation.item.create"
        assert initial_message["item"]["role"] == "user"
        
        assert dual_agent_bridge._cs_ready is True

    @pytest.mark.asyncio
    async def test_initialize_cs_session_no_connection(self, dual_agent_bridge):
        """Test CS session initialization without connection."""
        dual_agent_bridge.cs_connection = None
        
        with pytest.raises(RuntimeError, match="CS connection not available"):
            await dual_agent_bridge._initialize_cs_session()


class TestDualAgentBridgeResponseCreation:
    """Test DualAgentBridge response creation."""

    @pytest.mark.asyncio
    async def test_create_response_caller(self, dual_agent_bridge, mock_caller_connection, mock_caller_session_config):
        """Test response creation for caller agent."""
        dual_agent_bridge.caller_session_config = mock_caller_session_config
        
        await dual_agent_bridge._create_response(mock_caller_connection.websocket, "caller")
        
        mock_caller_connection.websocket.send.assert_called_once()
        message = json.loads(mock_caller_connection.websocket.send.call_args[0][0])
        
        assert message["type"] == "response.create"
        assert message["response"]["voice"] == "alloy"
        assert message["response"]["temperature"] == 0.8
        assert message["response"]["max_output_tokens"] == 1000

    @pytest.mark.asyncio
    async def test_create_response_cs(self, dual_agent_bridge, mock_cs_connection, mock_cs_session_config):
        """Test response creation for CS agent."""
        dual_agent_bridge.cs_session_config = mock_cs_session_config
        
        await dual_agent_bridge._create_response(mock_cs_connection.websocket, "cs")
        
        mock_cs_connection.websocket.send.assert_called_once()
        message = json.loads(mock_cs_connection.websocket.send.call_args[0][0])
        
        assert message["type"] == "response.create"
        assert message["response"]["voice"] == "verse"
        assert message["response"]["temperature"] == 0.7
        assert message["response"]["max_output_tokens"] == 1500


class TestDualAgentBridgeMessageHandling:
    """Test DualAgentBridge message handling."""

    @pytest.mark.asyncio
    async def test_handle_caller_messages_success(self, dual_agent_bridge, mock_caller_connection):
        """Test successful caller message handling."""
        dual_agent_bridge.caller_connection = mock_caller_connection
        dual_agent_bridge._closed = False
        
        test_message = json.dumps({"type": "response.created"})
        mock_websocket = MockWebSocket([test_message])
        mock_caller_connection.websocket = mock_websocket
        
        with patch.object(dual_agent_bridge, '_process_caller_message', new_callable=AsyncMock) as mock_process:
            # Mock the process method to set closed flag after processing
            async def mock_process_impl(data):
                dual_agent_bridge._closed = True
                mock_process.return_value = None
                
            mock_process.side_effect = mock_process_impl
            
            await dual_agent_bridge._handle_caller_messages()
            
            mock_process.assert_called_once_with({"type": "response.created"})

    @pytest.mark.asyncio
    async def test_handle_caller_messages_no_connection(self, dual_agent_bridge):
        """Test caller message handling without connection."""
        dual_agent_bridge.caller_connection = None
        
        # Should return without doing anything
        await dual_agent_bridge._handle_caller_messages()

    @pytest.mark.asyncio
    async def test_handle_cs_messages_success(self, dual_agent_bridge, mock_cs_connection):
        """Test successful CS message handling."""
        dual_agent_bridge.cs_connection = mock_cs_connection
        dual_agent_bridge._closed = False
        
        test_message = json.dumps({"type": "response.created"})
        mock_websocket = MockWebSocket([test_message])
        mock_cs_connection.websocket = mock_websocket
        
        with patch.object(dual_agent_bridge, '_process_cs_message', new_callable=AsyncMock) as mock_process:
            # Mock the process method to set closed flag after processing
            async def mock_process_impl(data):
                dual_agent_bridge._closed = True
                mock_process.return_value = None
                
            mock_process.side_effect = mock_process_impl
            
            await dual_agent_bridge._handle_cs_messages()
            
            mock_process.assert_called_once_with({"type": "response.created"})

    @pytest.mark.asyncio
    async def test_handle_cs_messages_no_connection(self, dual_agent_bridge):
        """Test CS message handling without connection."""
        dual_agent_bridge.cs_connection = None
        
        # Should return without doing anything
        await dual_agent_bridge._handle_cs_messages()


class TestDualAgentBridgeMessageProcessing:
    """Test DualAgentBridge message processing."""

    @pytest.mark.asyncio
    async def test_process_caller_message_response_created(self, dual_agent_bridge, mock_cs_connection):
        """Test processing caller response.created message."""
        dual_agent_bridge.cs_connection = mock_cs_connection
        
        data = {"type": "response.created"}
        
        await dual_agent_bridge._process_caller_message(data)
        
        assert dual_agent_bridge._current_speaker == "caller"
        assert dual_agent_bridge._waiting_for_response is False

    @pytest.mark.asyncio
    async def test_process_caller_message_audio_delta(self, dual_agent_bridge, mock_cs_connection, mock_call_recorder):
        """Test processing caller audio delta message."""
        dual_agent_bridge.cs_connection = mock_cs_connection
        dual_agent_bridge.call_recorder = mock_call_recorder
        
        with patch.object(dual_agent_bridge, '_route_audio_to_cs', new_callable=AsyncMock) as mock_route:
            data = {"type": "response.audio.delta", "delta": "test_audio"}
            
            await dual_agent_bridge._process_caller_message(data)
            
            mock_route.assert_called_once_with("test_audio")
            mock_call_recorder.record_caller_audio.assert_called_once_with("test_audio")

    @pytest.mark.asyncio
    async def test_process_caller_message_audio_done(self, dual_agent_bridge, mock_cs_connection):
        """Test processing caller audio done message."""
        dual_agent_bridge.cs_connection = mock_cs_connection
        dual_agent_bridge._current_speaker = "caller"
        dual_agent_bridge._waiting_for_response = False
        
        with patch.object(dual_agent_bridge, '_create_response', new_callable=AsyncMock) as mock_create:
            data = {"type": "response.audio.done"}
            
            await dual_agent_bridge._process_caller_message(data)
            
            mock_create.assert_called_once_with(mock_cs_connection.websocket, "cs")
            assert dual_agent_bridge._current_speaker is None
            assert dual_agent_bridge._waiting_for_response is True

    @pytest.mark.asyncio
    async def test_process_cs_message_response_created(self, dual_agent_bridge, mock_caller_connection):
        """Test processing CS response.created message."""
        dual_agent_bridge.caller_connection = mock_caller_connection
        
        data = {"type": "response.created"}
        
        await dual_agent_bridge._process_cs_message(data)
        
        assert dual_agent_bridge._current_speaker == "cs"
        assert dual_agent_bridge._waiting_for_response is False

    @pytest.mark.asyncio
    async def test_process_cs_message_audio_delta(self, dual_agent_bridge, mock_caller_connection, mock_call_recorder):
        """Test processing CS audio delta message."""
        dual_agent_bridge.caller_connection = mock_caller_connection
        dual_agent_bridge.call_recorder = mock_call_recorder
        
        with patch.object(dual_agent_bridge, '_route_audio_to_caller', new_callable=AsyncMock) as mock_route:
            data = {"type": "response.audio.delta", "delta": "test_audio"}
            
            await dual_agent_bridge._process_cs_message(data)
            
            mock_route.assert_called_once_with("test_audio")
            mock_call_recorder.record_bot_audio.assert_called_once_with("test_audio")

    @pytest.mark.asyncio
    async def test_process_cs_message_audio_done(self, dual_agent_bridge, mock_caller_connection):
        """Test processing CS audio done message."""
        dual_agent_bridge.caller_connection = mock_caller_connection
        dual_agent_bridge._current_speaker = "cs"
        dual_agent_bridge._waiting_for_response = False
        
        with patch.object(dual_agent_bridge, '_create_response', new_callable=AsyncMock) as mock_create:
            data = {"type": "response.audio.done"}
            
            await dual_agent_bridge._process_cs_message(data)
            
            mock_create.assert_called_once_with(mock_caller_connection.websocket, "caller")
            assert dual_agent_bridge._current_speaker is None
            assert dual_agent_bridge._waiting_for_response is True


class TestDualAgentBridgeAudioRouting:
    """Test DualAgentBridge audio routing functionality."""

    @pytest.mark.asyncio
    async def test_route_audio_to_caller(self, dual_agent_bridge, mock_caller_connection):
        """Test routing audio to caller agent."""
        dual_agent_bridge.caller_connection = mock_caller_connection
        dual_agent_bridge.cs_audio_buffer = []
        
        with patch.object(dual_agent_bridge, '_commit_caller_audio_buffer', new_callable=AsyncMock) as mock_commit:
            await dual_agent_bridge._route_audio_to_caller("test_audio")
            
            # Verify audio was sent
            mock_caller_connection.websocket.send.assert_called_once()
            message = json.loads(mock_caller_connection.websocket.send.call_args[0][0])
            assert message["type"] == "input_audio_buffer.append"
            assert message["audio"] == "test_audio"
            
            # Verify audio was buffered
            assert "test_audio" in dual_agent_bridge.cs_audio_buffer
            
            # Verify commit was called after buffer threshold
            assert mock_commit.call_count == 0  # Not called yet since buffer < 5

    @pytest.mark.asyncio
    async def test_route_audio_to_caller_buffer_threshold(self, dual_agent_bridge, mock_caller_connection):
        """Test routing audio to caller with buffer threshold."""
        dual_agent_bridge.caller_connection = mock_caller_connection
        dual_agent_bridge.cs_audio_buffer = ["audio1", "audio2", "audio3", "audio4"]
        
        with patch.object(dual_agent_bridge, '_commit_caller_audio_buffer', new_callable=AsyncMock) as mock_commit:
            await dual_agent_bridge._route_audio_to_caller("audio5")
            
            # Verify commit was called after reaching threshold
            mock_commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_audio_to_cs(self, dual_agent_bridge, mock_cs_connection):
        """Test routing audio to CS agent."""
        dual_agent_bridge.cs_connection = mock_cs_connection
        dual_agent_bridge.caller_audio_buffer = []
        
        with patch.object(dual_agent_bridge, '_commit_cs_audio_buffer', new_callable=AsyncMock) as mock_commit:
            await dual_agent_bridge._route_audio_to_cs("test_audio")
            
            # Verify audio was sent
            mock_cs_connection.websocket.send.assert_called_once()
            message = json.loads(mock_cs_connection.websocket.send.call_args[0][0])
            assert message["type"] == "input_audio_buffer.append"
            assert message["audio"] == "test_audio"
            
            # Verify audio was buffered
            assert "test_audio" in dual_agent_bridge.caller_audio_buffer

    @pytest.mark.asyncio
    async def test_commit_caller_audio_buffer(self, dual_agent_bridge, mock_caller_connection):
        """Test committing caller audio buffer."""
        dual_agent_bridge.caller_connection = mock_caller_connection
        dual_agent_bridge.cs_audio_buffer = ["audio1", "audio2"]
        
        await dual_agent_bridge._commit_caller_audio_buffer()
        
        # Verify commit message was sent
        mock_caller_connection.websocket.send.assert_called_once()
        message = json.loads(mock_caller_connection.websocket.send.call_args[0][0])
        assert message["type"] == "input_audio_buffer.commit"
        
        # Verify buffer was cleared
        assert dual_agent_bridge.cs_audio_buffer == []

    @pytest.mark.asyncio
    async def test_commit_cs_audio_buffer(self, dual_agent_bridge, mock_cs_connection):
        """Test committing CS audio buffer."""
        dual_agent_bridge.cs_connection = mock_cs_connection
        dual_agent_bridge.caller_audio_buffer = ["audio1", "audio2"]
        
        await dual_agent_bridge._commit_cs_audio_buffer()
        
        # Verify commit message was sent
        mock_cs_connection.websocket.send.assert_called_once()
        message = json.loads(mock_cs_connection.websocket.send.call_args[0][0])
        assert message["type"] == "input_audio_buffer.commit"
        
        # Verify buffer was cleared
        assert dual_agent_bridge.caller_audio_buffer == []


class TestDualAgentBridgeConversationFlow:
    """Test DualAgentBridge conversation flow management."""

    @pytest.mark.asyncio
    async def test_manage_conversation_flow_success(self, dual_agent_bridge, mock_cs_connection, mock_call_recorder):
        """Test successful conversation flow management."""
        dual_agent_bridge._caller_ready = True
        dual_agent_bridge._cs_ready = True
        dual_agent_bridge._closed = False
        dual_agent_bridge.cs_connection = mock_cs_connection
        dual_agent_bridge.call_recorder = mock_call_recorder
        
        with patch.object(dual_agent_bridge, '_create_response', new_callable=AsyncMock) as mock_create, \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            
            # Mock sleep to immediately set closed flag
            async def mock_sleep_impl(duration):
                dual_agent_bridge._closed = True
                
            mock_sleep.side_effect = mock_sleep_impl
            
            await dual_agent_bridge._manage_conversation_flow()
            
            # Verify CS greeting was triggered
            mock_create.assert_called_once_with(mock_cs_connection.websocket, "cs")

    @pytest.mark.asyncio
    async def test_manage_conversation_flow_max_duration(self, dual_agent_bridge, mock_cs_connection):
        """Test conversation flow with maximum duration reached."""
        dual_agent_bridge._caller_ready = True
        dual_agent_bridge._cs_ready = True
        dual_agent_bridge._closed = False
        dual_agent_bridge.cs_connection = mock_cs_connection
        
        with patch.object(dual_agent_bridge, '_create_response', new_callable=AsyncMock), \
             patch.object(dual_agent_bridge, 'close', new_callable=AsyncMock) as mock_close, \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            
            # Mock the conversation duration logic
            conversation_duration = 0
            max_duration = 300
            
            async def mock_sleep_impl(duration):
                nonlocal conversation_duration
                conversation_duration += 1
                if conversation_duration >= max_duration:
                    # This will trigger the close() call in the actual method
                    pass
                    
            mock_sleep.side_effect = mock_sleep_impl
            
            await dual_agent_bridge._manage_conversation_flow()
            
            mock_close.assert_called_once()


class TestDualAgentBridgeCleanup:
    """Test DualAgentBridge cleanup and closing."""

    @pytest.mark.asyncio
    async def test_close_success(self, dual_agent_bridge, mock_caller_connection, mock_cs_connection, mock_call_recorder):
        """Test successful bridge closure."""
        dual_agent_bridge._closed = False
        dual_agent_bridge.caller_connection = mock_caller_connection
        dual_agent_bridge.cs_connection = mock_cs_connection
        dual_agent_bridge.call_recorder = mock_call_recorder
        
        await dual_agent_bridge.close()
        
        assert dual_agent_bridge._closed is True
        mock_call_recorder.stop_recording.assert_called_once()
        mock_call_recorder.get_recording_summary.assert_called_once()
        mock_caller_connection.close.assert_called_once()
        mock_cs_connection.close.assert_called_once()
        assert dual_agent_bridge.caller_connection is None
        assert dual_agent_bridge.cs_connection is None

    @pytest.mark.asyncio
    async def test_close_already_closed(self, dual_agent_bridge):
        """Test closing an already closed bridge."""
        dual_agent_bridge._closed = True
        
        # Should not raise any exceptions
        await dual_agent_bridge.close()
        assert dual_agent_bridge._closed is True

    @pytest.mark.asyncio
    async def test_close_with_recording_error(self, dual_agent_bridge, mock_caller_connection, mock_cs_connection):
        """Test bridge closure with recording error."""
        dual_agent_bridge._closed = False
        dual_agent_bridge.caller_connection = mock_caller_connection
        dual_agent_bridge.cs_connection = mock_cs_connection
        
        # Mock call recorder that raises an error
        mock_recorder = AsyncMock()
        mock_recorder.stop_recording.side_effect = Exception("Recording error")
        dual_agent_bridge.call_recorder = mock_recorder
        
        # Should not raise an exception
        await dual_agent_bridge.close()
        
        assert dual_agent_bridge._closed is True
        mock_caller_connection.close.assert_called_once()
        mock_cs_connection.close.assert_called_once()


class TestDualAgentBridgeIntegration:
    """Integration tests for DualAgentBridge."""

    @pytest.mark.asyncio
    async def test_complete_conversation_flow(self, mock_caller_session_config, mock_cs_session_config, mock_call_recorder, mock_function_handler, mock_transcript_manager, mock_caller_connection, mock_cs_connection):
        """Test a complete conversation flow between agents."""
        with patch('opusagent.bridges.dual_agent_bridge.get_caller_config', return_value=mock_caller_session_config), \
             patch('opusagent.bridges.dual_agent_bridge.cs_session_config', mock_cs_session_config), \
             patch('opusagent.bridges.dual_agent_bridge.register_caller_functions'), \
             patch('opusagent.bridges.dual_agent_bridge.register_customer_service_functions'), \
             patch('opusagent.bridges.dual_agent_bridge.get_websocket_manager') as mock_ws_mgr, \
             patch('opusagent.bridges.dual_agent_bridge.CallRecorder', return_value=mock_call_recorder), \
             patch('opusagent.bridges.dual_agent_bridge.FunctionHandler', return_value=mock_function_handler), \
             patch('opusagent.bridges.dual_agent_bridge.TranscriptManager', return_value=mock_transcript_manager):
            
            # Set up mock connections
            caller_conn = mock_caller_connection
            cs_conn = mock_cs_connection
            
            # Create proper async mocks for the websocket manager methods
            async def mock_get_connection():
                return caller_conn if mock_get_connection.call_count == 0 else cs_conn
            mock_get_connection.call_count = 0
            mock_ws_mgr.return_value.get_connection = mock_get_connection
            
            async def mock_create_connection():
                return cs_conn
            mock_ws_mgr.return_value._create_connection = mock_create_connection
            
            bridge = DualAgentBridge(
                caller_type=CallerType.TYPICAL,
                scenario="banking_card_replacement",
                agent_type="banking",
                conversation_id="test-conv-123"
            )
            
            # Mock the async operations to avoid infinite loops
            with patch.object(bridge, '_initialize_caller_session', new_callable=AsyncMock), \
                 patch.object(bridge, '_initialize_cs_session', new_callable=AsyncMock), \
                 patch.object(bridge, '_handle_caller_messages', new_callable=AsyncMock), \
                 patch.object(bridge, '_handle_cs_messages', new_callable=AsyncMock), \
                 patch.object(bridge, '_manage_conversation_flow', new_callable=AsyncMock), \
                 patch('asyncio.gather', new_callable=AsyncMock):
                
                await bridge.initialize_connections()
                
                # Verify connections were established
                assert bridge.caller_connection == caller_conn
                assert bridge.cs_connection == cs_conn
                assert bridge.call_recorder is not None
                assert bridge.caller_transcript_manager is not None
                assert bridge.cs_transcript_manager is not None
                
                # Test audio routing
                with patch.object(bridge, '_commit_caller_audio_buffer', new_callable=AsyncMock) as mock_commit:
                    await bridge._route_audio_to_caller("test_audio")
                    caller_conn.websocket.send.assert_called()
                    
                    # Fill buffer to trigger commit
                    bridge.cs_audio_buffer = ["a1", "a2", "a3", "a4"]
                    await bridge._route_audio_to_caller("a5")
                    mock_commit.assert_called_once()
                
                # Test cleanup
                await bridge.close()
                assert bridge._closed is True
                caller_conn.close.assert_called_once()
                cs_conn.close.assert_called_once()
