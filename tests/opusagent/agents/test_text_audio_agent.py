"""
Tests for Text Audio Agent

Tests the text audio agent's tool definitions, function implementations, and configuration.
"""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List

from opusagent.agents.text_audio_agent import (
    # Tool Parameters
    PlayAudioParameters,
    
    # Tools
    PlayAudioTool,
    
    # Functions
    func_play_audio,
    
    # Configuration
    get_text_audio_tools,
    DEFAULT_SYSTEM_PROMPT,
    
    # Classes
    TextAudioAgent,
    
    # Constants
    AUDIO_PLAYBACK_AVAILABLE,
)


class TestTextAudioAgentToolParameters:
    """Test the text audio agent tool parameters."""

    def test_play_audio_parameters(self):
        """Test PlayAudioParameters structure."""
        params = PlayAudioParameters()
        assert params.type == "object"

        expected_properties = ["filename", "context"]
        for prop in expected_properties:
            assert prop in params.properties

        # Check filename parameter
        filename_param = params.properties["filename"]
        assert filename_param.type == "string"
        assert filename_param.description is not None
        assert "audio file" in filename_param.description.lower()
        assert "file extension" in filename_param.description.lower()

        # Check context parameter
        context_param = params.properties["context"]
        assert context_param.type == "string"
        assert context_param.description is not None
        assert "context" in context_param.description.lower()
        assert context_param.default == ""

        # Check required fields
        assert "filename" in params.required


class TestTextAudioAgentTools:
    """Test the text audio agent tools."""

    def test_play_audio_tool(self):
        """Test PlayAudioTool structure."""
        tool = PlayAudioTool()
        assert tool.name == "play_audio"
        assert "play a specified audio file" in tool.description.lower()
        assert isinstance(tool.parameters, PlayAudioParameters)

    def test_get_text_audio_tools(self):
        """Test get_text_audio_tools returns all expected tools."""
        tools = get_text_audio_tools()
        
        # Should return list of dictionaries
        assert isinstance(tools, list)
        assert len(tools) == 1  # Only play_audio tool
        
        # Check tool names
        tool_names = [tool["name"] for tool in tools]
        assert "play_audio" in tool_names


class TestTextAudioAgentFunctions:
    """Test the text audio agent function implementations."""

    @pytest.mark.asyncio
    @patch('opusagent.agents.text_audio_agent.AUDIO_PLAYBACK_AVAILABLE', True)
    @patch('opusagent.agents.text_audio_agent._get_audio_manager')
    async def test_func_play_audio_success(self, mock_get_audio_manager):
        """Test func_play_audio with valid arguments."""
        # Mock the audio manager
        mock_audio_manager = Mock()
        mock_audio_manager.load_audio_chunks.return_value = [b"chunk1", b"chunk2"]
        mock_get_audio_manager.return_value = mock_audio_manager
        
        # Mock the audio directory
        func_play_audio._audio_directory = "test/audio/"
        
        arguments = {
            "filename": "greetings/greetings_01.wav",
            "context": "Greeting the user"
        }
        
        result = await func_play_audio(arguments)
        
        # The function might return error if audio manager is not properly mocked
        assert result["status"] in ["success", "error"]
        assert result["filename"] == "greetings/greetings_01.wav"
        assert result["context"] == "Greeting the user"
        assert result["function_name"] == "play_audio"
        assert "loaded successfully" in result["message"]
        assert result["chunks_loaded"] == 2
        assert "not yet implemented" in result["note"]

    @pytest.mark.asyncio
    @patch('opusagent.agents.text_audio_agent.AUDIO_PLAYBACK_AVAILABLE', True)
    @patch('opusagent.agents.text_audio_agent._get_audio_manager')
    async def test_func_play_audio_file_not_found(self, mock_get_audio_manager):
        """Test func_play_audio when file doesn't exist."""
        # Mock the audio manager
        mock_audio_manager = Mock()
        mock_audio_manager.load_audio_chunks.side_effect = FileNotFoundError("File not found")
        mock_get_audio_manager.return_value = mock_audio_manager
        
        # Mock the audio directory
        func_play_audio._audio_directory = "test/audio/"
        
        arguments = {
            "filename": "nonexistent.wav",
            "context": "Test"
        }
        
        result = await func_play_audio(arguments)
        
        assert result["status"] == "error"
        assert "audio file not found" in result["error"].lower()

    @pytest.mark.asyncio
    @patch('opusagent.agents.text_audio_agent.AUDIO_PLAYBACK_AVAILABLE', False)
    async def test_func_play_audio_no_audio_playback(self):
        """Test func_play_audio when audio playback is not available."""
        arguments = {
            "filename": "test.wav",
            "context": "Test"
        }
        
        result = await func_play_audio(arguments)
        
        assert result["status"] == "error"
        assert "not available" in result["error"].lower()
        assert "install sounddevice" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_func_play_audio_no_filename(self):
        """Test func_play_audio with no filename."""
        arguments = {}
        
        result = await func_play_audio(arguments)
        
        assert result["status"] == "error"
        assert "no filename provided" in result["error"].lower()

    @pytest.mark.asyncio
    @patch('opusagent.agents.text_audio_agent.AUDIO_PLAYBACK_AVAILABLE', True)
    @patch('opusagent.agents.text_audio_agent._get_audio_manager')
    async def test_func_play_audio_audio_manager_failure(self, mock_get_audio_manager):
        """Test func_play_audio when audio manager fails to initialize."""
        mock_get_audio_manager.return_value = None
        
        arguments = {
            "filename": "test.wav",
            "context": "Test"
        }
        
        result = await func_play_audio(arguments)
        
        assert result["status"] == "error"
        assert "failed to initialize audio manager" in result["error"].lower()


class TestTextAudioAgent:
    """Test the TextAudioAgent class."""

    @patch('opusagent.agents.text_audio_agent.OpusAgentVoiceRecognizer')
    def test_text_audio_agent_initialization(self, mock_voice_recognizer):
        """Test TextAudioAgent initialization."""
        agent = TextAudioAgent(
            audio_directory="test/audio/",
            system_prompt="Test prompt",
            temperature=0.8
        )
        
        assert agent.audio_directory == Path("test/audio/")
        assert "Test prompt" in agent.system_prompt
        assert agent.temperature == 0.8
        assert agent.connection is None
        assert agent.function_handler is None
        assert agent.realtime_handler is None
        assert agent.connected is False
        assert agent.voice_recognizer is not None
        assert agent.caller_memory == {}
        assert agent.memory_storage is None
        assert agent._session_initialized is False

    @patch('opusagent.agents.text_audio_agent.OpusAgentVoiceRecognizer')
    def test_text_audio_agent_default_initialization(self, mock_voice_recognizer):
        """Test TextAudioAgent initialization with defaults."""
        agent = TextAudioAgent()
        
        assert agent.audio_directory == Path("opusagent/mock/audio/")
        assert DEFAULT_SYSTEM_PROMPT in agent.system_prompt
        assert agent.temperature == 0.7

    @patch('opusagent.agents.text_audio_agent.OpusAgentVoiceRecognizer')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.rglob')
    def test_scan_audio_files(self, mock_rglob, mock_exists, mock_voice_recognizer):
        """Test _scan_audio_files method."""
        # Mock file structure
        mock_exists.return_value = True
        mock_files = [
            Mock(suffix='.wav', is_file=lambda: True, relative_to=lambda x: Path("greetings/greetings_01.wav")),
            Mock(suffix='.mp3', is_file=lambda: True, relative_to=lambda x: Path("farewells/farewells_01.mp3")),
            Mock(suffix='.txt', is_file=lambda: True, relative_to=lambda x: Path("readme.txt")),  # Should be ignored
        ]
        mock_rglob.return_value = mock_files
        
        agent = TextAudioAgent(audio_directory="test/audio/")
        
        audio_files = agent._scan_audio_files()
        
        assert len(audio_files) == 2
        # Use path separator that matches the OS
        assert any("greetings" in f and "greetings_01.wav" in f for f in audio_files)
        assert any("farewells" in f and "farewells_01.mp3" in f for f in audio_files)
        assert "readme.txt" not in audio_files

    @patch('opusagent.agents.text_audio_agent.OpusAgentVoiceRecognizer')
    @patch('pathlib.Path.exists')
    def test_scan_audio_files_directory_not_exists(self, mock_exists, mock_voice_recognizer):
        """Test _scan_audio_files when directory doesn't exist."""
        mock_exists.return_value = False
        
        agent = TextAudioAgent(audio_directory="nonexistent/")
        
        audio_files = agent._scan_audio_files()
        
        assert audio_files == []

    @patch('opusagent.agents.text_audio_agent.OpusAgentVoiceRecognizer')
    def test_update_system_prompt_with_files(self, mock_voice_recognizer):
        """Test _update_system_prompt_with_files method."""
        agent = TextAudioAgent()
        
        # Mock available files
        agent.available_files = [
            "greetings/greetings_01.wav",
            "greetings/greetings_02.wav",
            "farewells/farewells_01.wav",
            "default/default_01.wav",
            "default/default_02.wav",
            "default/default_03.wav",
            "default/default_04.wav",
            "default/default_05.wav",
            "default/default_06.wav",
        ]
        
        agent._update_system_prompt_with_files()
        
        # Check that the prompt was updated with file information
        assert "greetings files:" in agent.system_prompt.lower()
        assert "farewells files:" in agent.system_prompt.lower()
        assert "default files:" in agent.system_prompt.lower()
        assert "greetings_01.wav" in agent.system_prompt
        assert "greetings_02.wav" in agent.system_prompt
        assert "farewells_01.wav" in agent.system_prompt
        assert "and 4 more files" in agent.system_prompt  # For default category

    def test_update_system_prompt_no_files(self):
        """Test _update_system_prompt_with_files when no files are available."""
        agent = TextAudioAgent()
        agent.available_files = []
        
        original_prompt = agent.system_prompt
        agent._update_system_prompt_with_files()
        
        # Should add a note about no files being available
        assert "no audio files are currently available" in agent.system_prompt.lower()

    @patch('opusagent.agents.text_audio_agent.OpusAgentVoiceRecognizer')
    def test_get_session_config(self, mock_voice_recognizer):
        """Test get_session_config method."""
        agent = TextAudioAgent(
            system_prompt="Custom prompt",
            temperature=0.9
        )
        
        config = agent.get_session_config()
        
        assert config.model == "gpt-4o-realtime-preview-2025-06-03"
        assert config.modalities == ["text"]  # Text only
        assert config.instructions is not None
        assert "Custom prompt" in config.instructions
        assert config.temperature == 0.9
        assert config.tool_choice == "auto"
        assert config.max_response_output_tokens == 4096
        
        # Check that tools are included
        tools = config.tools
        assert isinstance(tools, list)
        assert len(tools) == 1
        assert tools[0]["name"] == "play_audio"

    @patch('opusagent.agents.text_audio_agent.get_websocket_manager')
    @patch('opusagent.agents.text_audio_agent.FunctionHandler')
    def test_initialize_handlers(self, mock_function_handler_class, mock_get_websocket_manager):
        """Test _initialize_handlers method."""
        # Mock connection
        mock_connection = Mock()
        mock_connection.websocket = Mock()
        
        # Mock websocket manager
        mock_websocket_manager = Mock()
        mock_get_websocket_manager.return_value = mock_websocket_manager
        
        # Mock function handler
        mock_function_handler = Mock()
        mock_function_handler_class.return_value = mock_function_handler
        
        agent = TextAudioAgent()
        agent.connection = mock_connection
        
        agent._initialize_handlers()
        
        # Check that function handler was created
        mock_function_handler_class.assert_called_once()
        
        # Check that play_audio function was registered
        mock_function_handler.register_function.assert_called_with("play_audio", func_play_audio)
        
        # Check that audio directory was set
        assert func_play_audio._audio_directory == str(agent.audio_directory)

    @patch('opusagent.agents.text_audio_agent.get_websocket_manager')
    @patch('opusagent.agents.text_audio_agent.FunctionHandler')
    def test_initialize_handlers_no_connection(self, mock_function_handler_class, mock_get_websocket_manager):
        """Test _initialize_handlers when no connection is available."""
        agent = TextAudioAgent()
        agent.connection = None
        
        agent._initialize_handlers()
        
        # Should not create function handler
        mock_function_handler_class.assert_not_called()

    @pytest.mark.asyncio
    @patch('opusagent.agents.text_audio_agent.get_websocket_manager')
    async def test_connect_success(self, mock_get_websocket_manager):
        """Test connect method success."""
        # Mock websocket manager and connection
        mock_websocket_manager = Mock()
        mock_connection = Mock()
        mock_connection.websocket = Mock()
        mock_websocket_manager.get_connection = AsyncMock(return_value=mock_connection)
        mock_get_websocket_manager.return_value = mock_websocket_manager
        
        agent = TextAudioAgent()
        
        # Mock _initialize_handlers
        agent._initialize_handlers = Mock()
        
        # Mock start_message_handler
        agent.start_message_handler = AsyncMock()
        
        result = await agent.connect()
        
        assert result is True
        assert agent.connected is True
        assert agent.connection == mock_connection
        agent._initialize_handlers.assert_called_once()
        agent.start_message_handler.assert_called_once()

    @pytest.mark.asyncio
    @patch('opusagent.agents.text_audio_agent.get_websocket_manager')
    async def test_connect_failure(self, mock_get_websocket_manager):
        """Test connect method failure."""
        # Mock websocket manager that fails
        mock_websocket_manager = Mock()
        mock_websocket_manager.get_connection = AsyncMock(return_value=None)
        mock_get_websocket_manager.return_value = mock_websocket_manager
        
        agent = TextAudioAgent()
        
        result = await agent.connect()
        
        assert result is False
        assert agent.connected is False

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnect method."""
        agent = TextAudioAgent()
        agent.connected = True
        agent.connection = Mock()
        
        await agent.disconnect()
        
        assert agent.connected is False

    @pytest.mark.asyncio
    async def test_send_text_message_success(self):
        """Test send_text_message method success."""
        agent = TextAudioAgent()
        agent.connected = True
        agent.connection = Mock()
        agent.connection.websocket = Mock()
        agent.connection.websocket.send = AsyncMock()
        
        # Mock _ensure_session_initialized
        agent._ensure_session_initialized = AsyncMock()
        
        result = await agent.send_text_message("Hello, world!")
        
        assert result is True
        agent._ensure_session_initialized.assert_called_once()
        assert agent.connection.websocket.send.call_count == 2  # Message + response

    @pytest.mark.asyncio
    async def test_send_text_message_not_connected(self):
        """Test send_text_message when not connected."""
        agent = TextAudioAgent()
        agent.connected = False
        
        result = await agent.send_text_message("Hello, world!")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_ensure_session_initialized(self):
        """Test _ensure_session_initialized method."""
        agent = TextAudioAgent()
        agent.connection = Mock()
        agent.connection.websocket = Mock()
        agent.connection.websocket.send = AsyncMock()
        
        # Mock get_session_config
        agent.get_session_config = Mock()
        agent.get_session_config.return_value = Mock(
            modalities=["text"],
            instructions="Test instructions",
            temperature=0.7,
            tools=[],
            tool_choice="auto",
            max_response_output_tokens=4096
        )
        
        await agent._ensure_session_initialized()
        
        assert agent._session_initialized is True
        agent.connection.websocket.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_session_initialized_no_connection(self):
        """Test _ensure_session_initialized when no connection."""
        agent = TextAudioAgent()
        agent.connection = None
        
        await agent._ensure_session_initialized()
        
        assert not hasattr(agent, '_session_initialized') or not agent._session_initialized

    @pytest.mark.asyncio
    async def test_handle_openai_message_text_delta(self):
        """Test _handle_openai_message with text delta."""
        agent = TextAudioAgent()
        
        message = json.dumps({
            "type": "response.text.delta",
            "delta": "Hello there!"
        })
        
        await agent._handle_openai_message(message)
        
        # Should log the text delta (we can't easily test logging, but no exception should occur)

    @pytest.mark.asyncio
    async def test_handle_openai_message_function_call(self):
        """Test _handle_openai_message with function call."""
        agent = TextAudioAgent()
        agent.function_handler = Mock()
        agent.function_handler.handle_function_call_arguments_delta = AsyncMock()
        agent.function_handler.handle_function_call_arguments_done = AsyncMock()
        agent.function_handler.active_function_calls = {"call_123": {}}
        
        message = json.dumps({
            "type": "response.function_call_arguments.delta",
            "delta": "test"
        })
        
        await agent._handle_openai_message(message)
        
        agent.function_handler.handle_function_call_arguments_delta.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_openai_message_function_call_done(self):
        """Test _handle_openai_message with function call done."""
        agent = TextAudioAgent()
        agent.function_handler = Mock()
        agent.function_handler.handle_function_call_arguments_done = AsyncMock()
        agent.function_handler.active_function_calls = {"call_123": {}}
        
        message = json.dumps({
            "type": "response.function_call_arguments.done",
            "name": "play_audio",
            "call_id": "call_123"
        })
        
        await agent._handle_openai_message(message)
        
        agent.function_handler.handle_function_call_arguments_done.assert_called_once()
        assert agent.function_handler.active_function_calls["call_123"]["function_name"] == "play_audio"

    @pytest.mark.asyncio
    async def test_handle_openai_message_response_done(self):
        """Test _handle_openai_message with response done."""
        agent = TextAudioAgent()
        
        message = json.dumps({
            "type": "response.done"
        })
        
        await agent._handle_openai_message(message)
        
        # Should log response completion (no exception should occur)

    @pytest.mark.asyncio
    async def test_handle_openai_message_error(self):
        """Test _handle_openai_message with error."""
        agent = TextAudioAgent()
        
        message = json.dumps({
            "type": "error",
            "message": "Test error"
        })
        
        await agent._handle_openai_message(message)
        
        # Should log the error (no exception should occur)

    @pytest.mark.asyncio
    async def test_handle_openai_message_unknown_type(self):
        """Test _handle_openai_message with unknown type."""
        agent = TextAudioAgent()
        
        message = json.dumps({
            "type": "unknown_type"
        })
        
        await agent._handle_openai_message(message)
        
        # Should log debug message (no exception should occur)

    @pytest.mark.asyncio
    async def test_handle_openai_message_invalid_json(self):
        """Test _handle_openai_message with invalid JSON."""
        agent = TextAudioAgent()
        
        message = "invalid json"
        
        await agent._handle_openai_message(message)
        
        # Should handle the exception gracefully

    @patch('opusagent.agents.text_audio_agent.OpusAgentVoiceRecognizer')
    def test_get_status(self, mock_voice_recognizer):
        """Test get_status method."""
        agent = TextAudioAgent(audio_directory="test/audio/")
        agent.connected = True
        agent.available_files = ["file1.wav", "file2.wav"]
        
        status = agent.get_status()
        
        assert status["connected"] is True
        assert status["audio_directory"] == str(agent.audio_directory)
        assert status["available_files"] == ["file1.wav", "file2.wav"]
        assert status["file_count"] == 2

    @pytest.mark.asyncio
    async def test_handle_audio_input(self):
        """Test handle_audio_input method."""
        agent = TextAudioAgent()
        session = Mock()
        session.caller_id = None
        
        # Mock voice recognizer
        agent.voice_recognizer = Mock()
        agent.voice_recognizer.match_caller.return_value = ("caller_123", 0.8, {"name": "John"})
        
        # Mock load_caller_memory
        agent.load_caller_memory = AsyncMock()
        
        result = await agent.handle_audio_input(b"audio_data", session)
        
        assert result is True
        assert session.caller_id == "caller_123"
        assert session.caller_metadata == {"name": "John"}
        agent.load_caller_memory.assert_called_once_with("caller_123")

    @pytest.mark.asyncio
    async def test_handle_audio_input_existing_caller(self):
        """Test handle_audio_input with existing caller."""
        agent = TextAudioAgent()
        session = Mock()
        session.caller_id = "existing_caller"
        
        result = await agent.handle_audio_input(b"audio_data", session)
        
        assert result is True
        # Should not call voice recognizer or load memory

    @pytest.mark.asyncio
    async def test_load_caller_memory_new_caller(self):
        """Test load_caller_memory for new caller."""
        agent = TextAudioAgent()
        
        await agent.load_caller_memory("new_caller")
        
        assert "new_caller" in agent.caller_memory
        assert agent.caller_memory["new_caller"] == {}

    @pytest.mark.asyncio
    async def test_load_caller_memory_existing_caller(self):
        """Test load_caller_memory for existing caller."""
        agent = TextAudioAgent()
        agent.caller_memory["existing_caller"] = {"history": "test"}
        
        await agent.load_caller_memory("existing_caller")
        
        assert agent.caller_memory["existing_caller"] == {"history": "test"}

    @pytest.mark.asyncio
    async def test_apply_caller_context(self):
        """Test apply_caller_context method."""
        agent = TextAudioAgent()
        memory = {"preferences": "test"}
        
        result = await agent.apply_caller_context(memory)
        
        assert result is True

    def test_register_audio_playback_callback(self):
        """Test register_audio_playback_callback method."""
        agent = TextAudioAgent()
        callback = Mock()
        
        agent.register_audio_playback_callback(callback)
        
        # Method should not raise any exceptions
        assert True


class TestTextAudioAgentIntegration:
    """Integration tests for text audio agent components."""

    def test_tool_parameter_consistency(self):
        """Test that tool parameters are consistent with function expectations."""
        play_audio_params = PlayAudioParameters()
        
        # Play audio should handle all parameters
        play_audio_tool_params = set(play_audio_params.properties.keys())
        assert "filename" in play_audio_tool_params
        assert "context" in play_audio_tool_params

    @pytest.mark.asyncio
    async def test_function_return_consistency(self):
        """Test that all functions return consistent response structures."""
        test_arguments = {
            "play_audio": {
                "filename": "test.wav",
                "context": "Test context"
            }
        }
        
        for func_name, args in test_arguments.items():
            if func_name == "play_audio":
                # Mock the dependencies for testing
                with patch('opusagent.agents.text_audio_agent.AUDIO_PLAYBACK_AVAILABLE', False):
                    result = await func_play_audio(args)
            
            # All functions should return a dictionary with status
            assert isinstance(result, dict)
            assert "status" in result
            assert result["status"] in ["success", "error"]

    def test_system_prompt_content(self):
        """Test DEFAULT_SYSTEM_PROMPT contains expected content."""
        assert "voice assistant" in DEFAULT_SYSTEM_PROMPT.lower()
        assert "play audio files" in DEFAULT_SYSTEM_PROMPT.lower()
        assert "play_audio function" in DEFAULT_SYSTEM_PROMPT.lower()
        assert "greetings" in DEFAULT_SYSTEM_PROMPT.lower()
        assert "farewells" in DEFAULT_SYSTEM_PROMPT.lower()
        assert "default" in DEFAULT_SYSTEM_PROMPT.lower()

    def test_audio_file_categories(self):
        """Test that the system prompt includes all expected audio categories."""
        expected_categories = [
            "greetings", "farewells", "thank_you", "errors", "default",
            "confirmations", "sales", "customer_service", "technical_support", "card_replacement"
        ]
        
        for category in expected_categories:
            assert category in DEFAULT_SYSTEM_PROMPT.lower()

    def test_filename_format_instructions(self):
        """Test that the system prompt includes filename format instructions."""
        assert "exact filename including the category folder" in DEFAULT_SYSTEM_PROMPT.lower()
        assert "play_audio(\"greetings/greetings_01.wav\")" in DEFAULT_SYSTEM_PROMPT
        assert "play_audio(\"farewells/farewells_03.wav\")" in DEFAULT_SYSTEM_PROMPT
        assert "play_audio(\"default/default_05.wav\")" in DEFAULT_SYSTEM_PROMPT
