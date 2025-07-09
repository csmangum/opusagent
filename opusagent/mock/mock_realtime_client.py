#!/usr/bin/env python3
"""
MockRealtimeClient - Enhanced OpenAI Realtime API Simulator

This module provides a comprehensive mock implementation of the OpenAI Realtime API
WebSocket connection, designed for testing and development without requiring an
actual OpenAI API connection.

Key Features:
- Simulates the complete OpenAI Realtime API WebSocket protocol
- Supports saved audio phrases and configurable responses
- Provides factory functions for common testing scenarios
- Includes audio file caching and fallback mechanisms
- Supports function call simulation
- Configurable timing and streaming behavior

The MockRealtimeClient is designed to be a drop-in replacement for the real
OpenAI Realtime API during testing, allowing developers to:
- Test their applications without API costs
- Use predictable, hardcoded responses
- Test with actual audio files instead of silence
- Simulate various scenarios and edge cases
- Test function call handling
- Validate WebSocket event handling

Example Usage:
    ```python
    from opusagent.mock.mock_factory import create_customer_service_mock
    
    # Create a mock client with saved audio phrases
    mock_client = create_customer_service_mock(audio_dir="demo/audio")
    
    # Use with your existing WebSocket manager
    websocket_manager = create_mock_websocket_manager()
    ```
"""

import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable

import websockets
from websockets.asyncio.client import ClientConnection
from pydantic import BaseModel, Field

from opusagent.models.openai_api import (
    ClientEventType,
    MessageRole,
    RealtimeBaseMessage,
    RealtimeMessage,
    RealtimeMessageContent,
    RealtimeStreamMessage,
    ResponseCreateOptions,
    ServerEventType,
    SessionConfig,
)


class MockResponseConfig(BaseModel):
    """
    Configuration for a mock response in the MockRealtimeClient.
    
    This class defines how a specific response should be generated, including
    text content, audio files, timing, and function calls. It allows for
    highly customizable mock responses that can simulate various real-world
    scenarios.
    
    Attributes:
        text (str): The text content to be streamed as the response.
                   Defaults to a generic mock response message.
        audio_file (Optional[str]): Path to an audio file to be streamed.
                                   Supports WAV, MP3, and other audio formats.
                                   If None, silence will be generated.
        audio_data (Optional[bytes]): Raw audio data as bytes. If provided,
                                     this takes precedence over audio_file.
                                     Useful for dynamic audio generation.
        delay_seconds (float): Delay between text characters during streaming.
                              Simulates realistic typing speed. Default: 0.05s
        audio_chunk_delay (float): Delay between audio chunks during streaming.
                                  Controls audio streaming speed. Default: 0.2s
        function_call (Optional[Dict[str, Any]]): Function call to simulate.
                                                  Should contain 'name' and 'arguments'
                                                  keys for the function call.
    
    Example:
        ```python
        config = MockResponseConfig(
            text="Hello! How can I help you today?",
            audio_file="audio/greeting.wav",
            delay_seconds=0.03,
            audio_chunk_delay=0.15,
            function_call={
                "name": "get_user_info",
                "arguments": {"user_id": "12345"}
            }
        )
        ```
    """
    
    text: str = Field(
        default="This is a mock text response from the OpenAI Realtime API.",
        description="Text content to be streamed as the response"
    )
    audio_file: Optional[str] = Field(
        default=None,
        description="Path to audio file (WAV, MP3, etc.) to be streamed"
    )
    audio_data: Optional[bytes] = Field(
        default=None,
        description="Raw audio data as bytes (takes precedence over audio_file)"
    )
    delay_seconds: float = Field(
        default=0.05,
        description="Delay between text characters during streaming",
        ge=0.0
    )
    audio_chunk_delay: float = Field(
        default=0.2,
        description="Delay between audio chunks during streaming",
        ge=0.0
    )
    function_call: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Function call to simulate with 'name' and 'arguments' keys"
    )


class MockRealtimeClient:
    """
    Enhanced mock client that simulates the OpenAI Realtime API.
    
    This client provides a complete simulation of the OpenAI Realtime API
    WebSocket connection, including all event types, response streaming,
    audio handling, and function calls. It's designed to be a drop-in
    replacement for the real API during testing and development.
    
    The MockRealtimeClient supports:
    - Multiple response configurations for different scenarios
    - Saved audio phrases from actual audio files
    - Configurable timing for realistic streaming simulation
    - Function call simulation with custom arguments
    - Audio file caching for performance
    - Automatic fallback to silence for missing audio files
    - Complete WebSocket event handling
    
    Key Features:
        - **Response Configuration**: Define different responses for different
          scenarios using MockResponseConfig objects
        - **Audio Support**: Load and stream actual audio files instead of silence
        - **Function Calls**: Simulate function calls with custom arguments
        - **Event Handling**: Handle all OpenAI Realtime API event types
        - **Caching**: Cache audio files for improved performance
        - **Fallbacks**: Graceful handling of missing files and errors
    
    Attributes:
        logger (logging.Logger): Logger instance for debugging and monitoring
        session_config (SessionConfig): OpenAI session configuration
        response_configs (Dict[str, MockResponseConfig]): Available response configurations
        default_response_config (MockResponseConfig): Default response when no specific config matches
        session_id (str): Unique session identifier
        conversation_id (str): Unique conversation identifier
        connected (bool): Connection status
        _ws (Optional[ClientConnection]): WebSocket connection
        _audio_cache (Dict[str, bytes]): Cache for loaded audio files
    
    Example:
        ```python
        # Create a basic mock client
        mock_client = MockRealtimeClient()
        
        # Add custom response configurations
        mock_client.add_response_config(
            "greeting",
            MockResponseConfig(
                text="Hello! Welcome to our service.",
                audio_file="audio/greeting.wav"
            )
        )
        
        # Use with WebSocket manager
        websocket_manager = create_mock_websocket_manager()
        ```
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        session_config: Optional[SessionConfig] = None,
        response_configs: Optional[Dict[str, MockResponseConfig]] = None,
        default_response_config: Optional[MockResponseConfig] = None,
    ):
        """
        Initialize the MockRealtimeClient.
        
        Args:
            logger (Optional[logging.Logger]): Logger instance for debugging.
                                             If None, creates a default logger.
            session_config (Optional[SessionConfig]): OpenAI session configuration.
                                                    If None, uses default settings.
            response_configs (Optional[Dict[str, MockResponseConfig]]): Pre-configured
                                                                      response configurations
                                                                      for different scenarios.
            default_response_config (Optional[MockResponseConfig]): Default response
                                                                   configuration when no
                                                                   specific config matches.
        
        Example:
            ```python
            # Basic initialization
            mock_client = MockRealtimeClient()
            
            # With custom configurations
            configs = {
                "greeting": MockResponseConfig(text="Hello!"),
                "help": MockResponseConfig(text="How can I help?")
            }
            mock_client = MockRealtimeClient(response_configs=configs)
            ```
        """
        self.logger = logger or logging.getLogger(__name__)
        self.session_config = session_config or SessionConfig(
            model="gpt-4o-realtime-preview-2025-06-03",
            modalities=["text", "audio"],
            voice="alloy"
        )
        
        # Response configuration
        self.response_configs = response_configs or {}
        self.default_response_config = default_response_config or MockResponseConfig()
        
        # Session state
        self.session_id = str(uuid.uuid4())
        self.conversation_id = str(uuid.uuid4())
        self.connected = False
        self._ws: Optional[ClientConnection] = None
        
        # Event handling
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._response_queue: asyncio.Queue = asyncio.Queue()
        
        # Audio handling
        self._audio_buffer: List[bytes] = []
        self._speech_detected = False
        
        # Response state
        self._active_response_id: Optional[str] = None
        self._response_text = ""
        self._response_audio: List[bytes] = []
        
        # Audio cache for loaded files
        self._audio_cache: Dict[str, bytes] = {}
        
        # Register default event handlers
        self._register_default_handlers()

    def add_response_config(self, key: str, config: MockResponseConfig) -> None:
        """
        Add a response configuration for a specific scenario.
        
        This method allows you to dynamically add response configurations
        at runtime. The configuration will be available for use in subsequent
        response generation.
        
        Args:
            key (str): Unique identifier for this response configuration.
                      Used to select the appropriate response during generation.
            config (MockResponseConfig): Configuration defining how the response
                                       should be generated.
        
        Example:
            ```python
            mock_client.add_response_config(
                "greeting",
                MockResponseConfig(
                    text="Hello! How can I help you?",
                    audio_file="audio/greeting.wav",
                    delay_seconds=0.03
                )
            )
            ```
        """
        self.response_configs[key] = config
        self.logger.debug(f"Added response config for key: {key}")

    def get_response_config(self, key: Optional[str] = None) -> MockResponseConfig:
        """
        Get a response configuration by key, or return the default configuration.
        
        This method implements the response selection logic. If a specific key
        is provided and exists in the response configurations, it returns that
        configuration. Otherwise, it returns the default configuration.
        
        Args:
            key (Optional[str]): Key to look up in response configurations.
                                If None or not found, returns default config.
        
        Returns:
            MockResponseConfig: The selected response configuration.
        
        Example:
            ```python
            # Get specific configuration
            config = mock_client.get_response_config("greeting")
            
            # Get default configuration
            default_config = mock_client.get_response_config()
            ```
        """
        if key and key in self.response_configs:
            return self.response_configs[key]
        return self.default_response_config

    async def load_audio_file(self, file_path: str) -> bytes:
        """
        Load an audio file and cache it for future use.
        
        This method loads audio files from disk and caches them in memory
        for improved performance. If the file doesn't exist or can't be loaded,
        it falls back to generating silence.
        
        Args:
            file_path (str): Path to the audio file to load.
        
        Returns:
            bytes: Audio data as bytes. If file loading fails, returns silence.
        
        Example:
            ```python
            # Load an audio file
            audio_data = await mock_client.load_audio_file("audio/greeting.wav")
            print(f"Loaded {len(audio_data)} bytes of audio data")
            ```
        
        Note:
            - Files are cached after first load for improved performance
            - Supports WAV, MP3, and other audio formats
            - Falls back to silence if file not found or loading fails
            - Logs warnings and errors for debugging
        """
        if file_path in self._audio_cache:
            self.logger.debug(f"Using cached audio file: {file_path}")
            return self._audio_cache[file_path]
        
        try:
            path = Path(file_path)
            if not path.exists():
                self.logger.warning(f"[MOCK REALTIME] Audio file not found: {file_path}")
                return self._generate_silence()
            
            with open(path, 'rb') as f:
                audio_data = f.read()
                self._audio_cache[file_path] = audio_data
                self.logger.info(f"[MOCK REALTIME] Loaded audio file: {file_path} ({len(audio_data)} bytes)")
                return audio_data
                
        except Exception as e:
            self.logger.error(f"[MOCK REALTIME] Error loading audio file {file_path}: {e}")
            return self._generate_silence()

    def _generate_silence(self, duration: float = 2.0, sample_rate: int = 16000) -> bytes:
        """
        Generate silence audio data for fallback scenarios.
        
        This method creates audio data consisting of silence, which is used
        as a fallback when audio files are not available or fail to load.
        
        Args:
            duration (float): Duration of silence in seconds. Default: 2.0s
            sample_rate (int): Audio sample rate in Hz. Default: 16000Hz
        
        Returns:
            bytes: Raw audio data representing silence.
        
        Note:
            - Generates 16-bit PCM audio data
            - Uses the specified sample rate and duration
            - All samples are set to 0 (silence)
        """
        num_samples = int(sample_rate * duration)
        return bytes([0] * num_samples * 2)  # 16-bit PCM

    def _register_default_handlers(self) -> None:
        """
        Register default event handlers for common OpenAI Realtime API events.
        
        This method sets up the default event handlers that process incoming
        WebSocket messages. It registers handlers for session management,
        audio buffer operations, and response creation/cancellation.
        
        Registered Events:
            - session.update: Handle session configuration updates
            - input_audio_buffer.append: Handle incoming audio data
            - input_audio_buffer.commit: Commit audio buffer to conversation
            - input_audio_buffer.clear: Clear the audio buffer
            - response.create: Start response generation
            - response.cancel: Cancel active response generation
        """
        self.register_event_handler(ClientEventType.SESSION_UPDATE, self._handle_session_update)
        self.register_event_handler(ClientEventType.INPUT_AUDIO_BUFFER_APPEND, self._handle_audio_append)
        self.register_event_handler(ClientEventType.INPUT_AUDIO_BUFFER_COMMIT, self._handle_audio_commit)
        self.register_event_handler(ClientEventType.INPUT_AUDIO_BUFFER_CLEAR, self._handle_audio_clear)
        self.register_event_handler(ClientEventType.RESPONSE_CREATE, self._handle_response_create)
        self.register_event_handler(ClientEventType.RESPONSE_CANCEL, self._handle_response_cancel)

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """
        Register an event handler for a specific event type.
        
        This method allows you to register custom event handlers for processing
        specific types of WebSocket events. Multiple handlers can be registered
        for the same event type.
        
        Args:
            event_type (str): The type of event to handle (e.g., "session.update")
            handler (Callable): Async function to handle the event.
                               Should accept a single dict parameter.
        
        Example:
            ```python
            async def custom_handler(data):
                print(f"Handling event: {data}")
            
            mock_client.register_event_handler("custom.event", custom_handler)
            ```
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        self.logger.debug(f"Registered handler for event type: {event_type}")

    async def connect(self, url: str = "ws://localhost:8080") -> None:
        """
        Connect to a mock WebSocket server.
        
        This method establishes a WebSocket connection to the specified URL.
        After connecting, it starts the message handler and sends an initial
        session.created event to simulate the OpenAI Realtime API behavior.
        
        Args:
            url (str): WebSocket server URL to connect to.
                      Default: "ws://localhost:8080"
        
        Raises:
            websockets.exceptions.ConnectionError: If connection fails
            Exception: For other connection-related errors
        
        Example:
            ```python
            # Connect to default mock server
            await mock_client.connect()
            
            # Connect to custom server
            await mock_client.connect("ws://localhost:9000")
            ```
        """
        self.logger.info(f"[MOCK REALTIME] Connecting to {url}...")
        try:
            self._ws = await websockets.connect(url)
            self.connected = True
            self.logger.info("[MOCK REALTIME] Connected successfully")
            
            # Start message handler
            asyncio.create_task(self._message_handler())
            
            # Send session created event
            await self._send_session_created()
            
        except Exception as e:
            self.logger.error(f"[MOCK REALTIME] Connection failed: {e}")
            self.connected = False
            raise

    async def disconnect(self) -> None:
        """
        Disconnect from the WebSocket server.
        
        This method gracefully closes the WebSocket connection and updates
        the connection status. It's safe to call even if not connected.
        
        Example:
            ```python
            await mock_client.disconnect()
            ```
        """
        if self._ws:
            try:
                await self._ws.close()
                self.logger.info("[MOCK REALTIME] Disconnected successfully")
            except Exception as e:
                self.logger.warning(f"[MOCK REALTIME] Error during disconnect: {e}")
            finally:
                self.connected = False
                self._ws = None

    async def _message_handler(self) -> None:
        """
        Handle incoming WebSocket messages.
        
        This method continuously listens for messages from the WebSocket
        connection and processes them using registered event handlers.
        It handles JSON parsing, error conditions, and connection closure.
        
        The message handler:
        - Parses incoming JSON messages
        - Routes messages to appropriate event handlers
        - Handles connection closure gracefully
        - Logs errors and warnings for debugging
        
        Note:
            This method runs as a background task after connection
            and continues until the connection is closed.
        """
        if not self._ws:
            return
            
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    event_type = data.get("type")
                    
                    if event_type in self._event_handlers:
                        for handler in self._event_handlers[event_type]:
                            await handler(data)
                    else:
                        self.logger.warning(f"[MOCK REALTIME] No handler for event type: {event_type}")
                        
                except json.JSONDecodeError:
                    self.logger.warning(f"[MOCK REALTIME] Received non-JSON message: {message}")
                except Exception as e:
                    self.logger.error(f"[MOCK REALTIME] Error processing message: {e}")
                    
        except websockets.ConnectionClosed:
            self.logger.info("[MOCK REALTIME] Connection closed")
        except Exception as e:
            self.logger.error(f"[MOCK REALTIME] Message handler error: {e}")

    async def _send_session_created(self) -> None:
        """
        Send a session.created event to simulate session initialization.
        
        This method sends the initial session.created event that the
        OpenAI Realtime API sends when a connection is established.
        It includes the current session configuration and metadata.
        
        The event contains:
        - Session ID and creation timestamp
        - Model configuration and modalities
        - Voice settings and audio formats
        - Tool configurations and other settings
        """
        event = {
            "type": ServerEventType.SESSION_CREATED,
            "session": {
                "id": self.session_id,
                "created_at": int(datetime.now().timestamp() * 1000),
                "modalities": self.session_config.modalities,
                "model": self.session_config.model,
                "instructions": self.session_config.instructions,
                "voice": self.session_config.voice,
                "input_audio_format": self.session_config.input_audio_format,
                "output_audio_format": self.session_config.output_audio_format,
                "turn_detection": self.session_config.turn_detection,
                "tools": self.session_config.tools,
                "tool_choice": self.session_config.tool_choice,
                "temperature": self.session_config.temperature,
                "max_response_output_tokens": self.session_config.max_response_output_tokens,
                "input_audio_transcription": self.session_config.input_audio_transcription,
                "input_audio_noise_reduction": self.session_config.input_audio_noise_reduction,
            }
        }
        await self._send_event(event)

    async def _send_event(self, event: Dict[str, Any]) -> None:
        """
        Send an event to the connected WebSocket client.
        
        This method serializes and sends an event to the WebSocket connection.
        It handles the JSON serialization and error conditions.
        
        Args:
            event (Dict[str, Any]): Event data to send. Must be JSON serializable.
        
        Raises:
            Exception: If sending fails (e.g., connection closed)
        """
        if self._ws:
            try:
                await self._ws.send(json.dumps(event))
                self.logger.debug(f"[MOCK REALTIME] Sent event: {event.get('type', 'unknown')}")
            except Exception as e:
                self.logger.error(f"[MOCK REALTIME] Error sending event: {e}")
                raise

    async def _handle_session_update(self, data: Dict[str, Any]) -> None:
        """
        Handle session.update events from the client.
        
        This method processes session configuration updates sent by the client.
        It updates the internal session configuration and sends a confirmation
        event back to the client.
        
        Args:
            data (Dict[str, Any]): Session update data containing new configuration.
        """
        session = data.get("session", {})
        self.session_config = SessionConfig(**session)
        
        # Send session.updated event
        event = {
            "type": ServerEventType.SESSION_UPDATED,
            "session": session
        }
        await self._send_event(event)
        self.logger.info("[MOCK REALTIME] Session updated successfully")

    async def _handle_audio_append(self, data: Dict[str, Any]) -> None:
        """
        Handle input_audio_buffer.append events from the client.
        
        This method processes incoming audio data and adds it to the audio buffer.
        It also simulates speech detection by monitoring buffer size and sending
        speech detection events when appropriate.
        
        Args:
            data (Dict[str, Any]): Audio data containing base64-encoded audio.
        """
        audio = data.get("audio")
        if audio:
            try:
                audio_bytes = base64.b64decode(audio)
                self._audio_buffer.append(audio_bytes)
                
                # Simulate speech detection
                if not self._speech_detected and len(self._audio_buffer) > 10:
                    self._speech_detected = True
                    event = {
                        "type": ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED,
                        "audio_start_ms": 0,
                        "item_id": str(uuid.uuid4())
                    }
                    await self._send_event(event)
                    self.logger.debug("[MOCK REALTIME] Speech detection started")
                    
            except Exception as e:
                self.logger.error(f"[MOCK REALTIME] Error processing audio data: {e}")

    async def _handle_audio_commit(self, data: Dict[str, Any]) -> None:
        """
        Handle input_audio_buffer.commit events from the client.
        
        This method commits the current audio buffer to the conversation,
        creating a new conversation item. It sends a confirmation event
        and clears the buffer for future use.
        
        Args:
            data (Dict[str, Any]): Commit event data (usually empty).
        """
        if self._audio_buffer:
            # Create a new conversation item
            item_id = str(uuid.uuid4())
            
            # Send committed event
            event = {
                "type": ServerEventType.INPUT_AUDIO_BUFFER_COMMITTED,
                "item_id": item_id
            }
            await self._send_event(event)
            
            # Clear buffer
            self._audio_buffer.clear()
            self._speech_detected = False
            self.logger.info(f"[MOCK REALTIME] Audio buffer committed, item_id: {item_id}")
        else:
            self.logger.warning("[MOCK REALTIME] Attempted to commit empty audio buffer")

    async def _handle_audio_clear(self, data: Dict[str, Any]) -> None:
        """
        Handle input_audio_buffer.clear events from the client.
        
        This method clears the current audio buffer and resets speech detection.
        It sends a confirmation event back to the client.
        
        Args:
            data (Dict[str, Any]): Clear event data (usually empty).
        """
        self._audio_buffer.clear()
        self._speech_detected = False
        
        event = {
            "type": ServerEventType.INPUT_AUDIO_BUFFER_CLEARED
        }
        await self._send_event(event)
        self.logger.info("[MOCK REALTIME] Audio buffer cleared")

    async def _handle_response_create(self, data: Dict[str, Any]) -> None:
        """
        Handle response.create events from the client.
        
        This method initiates response generation based on the client's request.
        It creates a new response ID, sends a response.created event, and
        starts the response generation process in the background.
        
        Args:
            data (Dict[str, Any]): Response creation data containing options.
        """
        response = data.get("response", {})
        self._active_response_id = str(uuid.uuid4())
        
        # Send response.created event
        event = {
            "type": ServerEventType.RESPONSE_CREATED,
            "response": {
                "id": self._active_response_id,
                "created_at": int(datetime.now().timestamp() * 1000)
            }
        }
        await self._send_event(event)
        
        # Start response generation
        asyncio.create_task(self._generate_response(response))
        self.logger.info(f"[MOCK REALTIME] Response generation started: {self._active_response_id}")

    async def _handle_response_cancel(self, data: Dict[str, Any]) -> None:
        """
        Handle response.cancel events from the client.
        
        This method cancels an active response generation. It checks if the
        specified response ID matches the active response and sends a
        cancellation confirmation event.
        
        Args:
            data (Dict[str, Any]): Cancel event data containing response_id.
        """
        response_id = data.get("response_id")
        if response_id == self._active_response_id:
            self._active_response_id = None
            
            event = {
                "type": ServerEventType.RESPONSE_CANCELLED,
                "response_id": response_id
            }
            await self._send_event(event)
            self.logger.info(f"[MOCK REALTIME] Response cancelled: {response_id}")
        else:
            self.logger.warning(f"[MOCK REALTIME] Attempted to cancel non-active response: {response_id}")

    async def _generate_response(self, response: Dict[str, Any]) -> None:
        """
        Generate a complete mock response based on the request.
        
        This method orchestrates the response generation process. It determines
        which response configuration to use, handles function calls, and generates
        text and audio responses according to the configuration.
        
        The response generation process:
        1. Determines the appropriate response configuration
        2. Handles function calls if tools are enabled
        3. Generates text responses with streaming
        4. Generates audio responses with streaming
        5. Sends completion events
        
        Args:
            response (Dict[str, Any]): Response creation options from the client.
        
        Note:
            This method runs as a background task and handles all aspects
            of response generation including timing and error handling.
        """
        try:
            # Simulate response generation delay
            await asyncio.sleep(0.5)
            
            # Get response options
            options = ResponseCreateOptions(**response)
            
            # Determine which response config to use
            response_key = self._determine_response_key(options)
            config = self.get_response_config(response_key)
            
            self.logger.info(f"[MOCK REALTIME] Generating response with config: {response_key or 'default'}")
            
            # Handle function calls if tools are enabled
            if options.tools and options.tool_choice != "none":
                await self._generate_function_call(options, config)
                return
            
            # Generate text response
            if "text" in options.modalities:
                await self._generate_text_response(options, config)
            
            # Generate audio response
            if "audio" in options.modalities:
                await self._generate_audio_response(options, config)
            
            # Send response done
            event = {
                "type": ServerEventType.RESPONSE_DONE,
                "response": {
                    "id": self._active_response_id,
                    "created_at": int(datetime.now().timestamp() * 1000)
                }
            }
            await self._send_event(event)
            
            self.logger.info(f"[MOCK REALTIME] Response generation completed: {self._active_response_id}")
            
        except Exception as e:
            self.logger.error(f"[MOCK REALTIME] Error generating response: {e}")
            # Send error event
            await self.send_error("response_generation_failed", str(e))
            
        finally:
            self._active_response_id = None

    def _determine_response_key(self, options: ResponseCreateOptions) -> Optional[str]:
        """
        Determine which response configuration to use based on the request.
        
        This method implements the response selection logic. Currently, it uses
        a simple strategy of returning the first available response configuration
        key. This can be customized to implement more sophisticated selection
        logic based on conversation context, user input, or other factors.
        
        Args:
            options (ResponseCreateOptions): Response creation options from the client.
        
        Returns:
            Optional[str]: Key for the response configuration to use, or None for default.
        
        Note:
            This is a simple implementation that can be extended for more
            sophisticated response selection based on:
            - Conversation history
            - User input content
            - Requested modalities
            - Tool configurations
            - Session context
        """
        # Check if there are any specific keys in the response configs
        if self.response_configs:
            # For now, just return the first key - you can customize this logic
            return list(self.response_configs.keys())[0]
        
        return None

    async def _generate_text_response(self, options: ResponseCreateOptions, config: MockResponseConfig) -> None:
        """
        Generate a text response with streaming simulation.
        
        This method generates a text response by streaming individual characters
        with configurable delays to simulate realistic typing behavior. It sends
        text delta events for each character and a final text done event.
        
        Args:
            options (ResponseCreateOptions): Response creation options.
            config (MockResponseConfig): Configuration for this response.
        
        The streaming process:
        1. Sends text.delta events for each character
        2. Applies configurable delays between characters
        3. Sends text.done event with complete text
        """
        # Send text deltas
        text = config.text
        for char in text:
            event = {
                "type": ServerEventType.RESPONSE_TEXT_DELTA,
                "response_id": self._active_response_id,
                "item_id": str(uuid.uuid4()),
                "output_index": 0,
                "content_index": 0,
                "delta": char
            }
            await self._send_event(event)
            await asyncio.sleep(config.delay_seconds)
        
        # Send text done
        event = {
            "type": ServerEventType.RESPONSE_TEXT_DONE,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "content_index": 0,
            "text": text
        }
        await self._send_event(event)
        
        self.logger.debug(f"[MOCK REALTIME] Text response completed: {len(text)} characters")

    async def _generate_audio_response(self, options: ResponseCreateOptions, config: MockResponseConfig) -> None:
        """
        Generate an audio response with streaming simulation.
        
        This method generates an audio response by streaming audio data in chunks
        with configurable delays. It can use saved audio files, raw audio data,
        or generate silence as a fallback.
        
        Args:
            options (ResponseCreateOptions): Response creation options.
            config (MockResponseConfig): Configuration for this response.
        
        Audio sources (in order of precedence):
        1. config.audio_data (raw bytes)
        2. config.audio_file (file path)
        3. Generated silence (fallback)
        
        The streaming process:
        1. Loads or generates audio data
        2. Splits data into chunks (3200 bytes = 200ms at 16kHz 16-bit)
        3. Sends audio.delta events for each chunk
        4. Applies configurable delays between chunks
        5. Sends audio.done event
        """
        # Get audio data
        if config.audio_data:
            audio_data = config.audio_data
            self.logger.debug("[MOCK REALTIME] Using raw audio data")
        elif config.audio_file:
            audio_data = await self.load_audio_file(config.audio_file)
            self.logger.debug(f"[MOCK REALTIME] Using audio file: {config.audio_file}")
        else:
            # Generate silence as fallback
            audio_data = self._generate_silence()
            self.logger.debug("[MOCK REALTIME] Using generated silence")
        
        # Split into chunks (3200 bytes = 200ms at 16kHz 16-bit)
        chunk_size = 3200
        chunks = [audio_data[i:i + chunk_size] for i in range(0, len(audio_data), chunk_size)]
        
        self.logger.debug(f"[MOCK REALTIME] Streaming {len(chunks)} audio chunks")
        
        # Send audio deltas
        for i, chunk in enumerate(chunks):
            event = {
                "type": ServerEventType.RESPONSE_AUDIO_DELTA,
                "response_id": self._active_response_id,
                "item_id": str(uuid.uuid4()),
                "output_index": 0,
                "content_index": 0,
                "delta": base64.b64encode(chunk).decode("utf-8")
            }
            await self._send_event(event)
            await asyncio.sleep(config.audio_chunk_delay)
        
        # Send audio done
        event = {
            "type": ServerEventType.RESPONSE_AUDIO_DONE,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "content_index": 0
        }
        await self._send_event(event)
        
        self.logger.debug(f"[MOCK REALTIME] Audio response completed: {len(audio_data)} bytes")

    async def _generate_function_call(self, options: ResponseCreateOptions, config: MockResponseConfig) -> None:
        """
        Generate a function call response.
        
        This method generates a function call response by streaming function
        call arguments and sending appropriate events. It can use a configured
        function call or generate a default one.
        
        Args:
            options (ResponseCreateOptions): Response creation options.
            config (MockResponseConfig): Configuration for this response.
        
        The function call process:
        1. Determines function call to simulate
        2. Sends function_call_arguments.delta events
        3. Sends function_call_arguments.done event
        4. Includes function name and arguments
        """
        # Use config function call if available, otherwise use default
        if config.function_call:
            function_call = config.function_call
            self.logger.debug(f"[MOCK REALTIME] Using configured function call: {function_call.get('name')}")
        else:
            # Default function call
            function_call = {
                "name": "mock_function",
                "arguments": {"param1": "value1", "param2": "value2"}
            }
            self.logger.debug("[MOCK REALTIME] Using default function call")
        
        # Send function call arguments delta
        event = {
            "type": ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "call_id": str(uuid.uuid4()),
            "delta": json.dumps(function_call["arguments"])
        }
        await self._send_event(event)
        
        # Send function call arguments done
        event = {
            "type": ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "call_id": str(uuid.uuid4()),
            "arguments": json.dumps(function_call["arguments"])
        }
        await self._send_event(event)
        
        self.logger.info(f"[MOCK REALTIME] Function call completed: {function_call.get('name')}")

    # Additional utility methods for advanced usage

    async def send_transcript_delta(self, text: str, final: bool = False) -> None:
        """
        Send a transcript delta event for generated audio.
        
        This method sends transcript events that correspond to generated audio.
        It's useful for testing audio transcription features.
        
        Args:
            text (str): Transcript text to send.
            final (bool): Whether this is the final transcript chunk.
        """
        event = {
            "type": ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "content_index": 0,
            "delta": text
        }
        await self._send_event(event)
        
        if final:
            event = {
                "type": ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DONE,
                "response_id": self._active_response_id,
                "item_id": str(uuid.uuid4()),
                "output_index": 0,
                "content_index": 0,
                "transcript": text
            }
            await self._send_event(event)

    async def send_input_transcript_delta(self, item_id: str, text: str, final: bool = False) -> None:
        """
        Send an input audio transcription delta event.
        
        This method sends transcript events for user input audio.
        It's useful for testing input audio transcription features.
        
        Args:
            item_id (str): ID of the conversation item.
            text (str): Transcript text to send.
            final (bool): Whether this is the final transcript chunk.
        """
        event = {
            "type": ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_DELTA,
            "item_id": item_id,
            "content_index": 0,
            "delta": text
        }
        await self._send_event(event)
        
        if final:
            event = {
                "type": ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED,
                "item_id": item_id,
                "content_index": 0,
                "transcript": text
            }
            await self._send_event(event)

    async def send_input_transcript_failed(self, item_id: str, error: Dict[str, Any]) -> None:
        """
        Send an input audio transcription failed event.
        
        This method sends a failure event for input audio transcription.
        It's useful for testing error handling scenarios.
        
        Args:
            item_id (str): ID of the conversation item.
            error (Dict[str, Any]): Error details.
        """
        event = {
            "type": ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_FAILED,
            "item_id": item_id,
            "content_index": 0,
            "error": error
        }
        await self._send_event(event)

    async def send_output_item_added(self, item: Dict[str, Any]) -> None:
        """
        Send an output item added event.
        
        This method sends an event indicating a new output item has been added
        to the response. It's useful for testing complex response structures.
        
        Args:
            item (Dict[str, Any]): Item data to include in the event.
        """
        event = {
            "type": ServerEventType.RESPONSE_OUTPUT_ITEM_ADDED,
            "response_id": self._active_response_id,
            "output_index": 0,
            "item": item
        }
        await self._send_event(event)

    async def send_output_item_done(self, item: Dict[str, Any]) -> None:
        """
        Send an output item done event.
        
        This method sends an event indicating an output item is complete.
        It's useful for testing response completion scenarios.
        
        Args:
            item (Dict[str, Any]): Item data to include in the event.
        """
        event = {
            "type": ServerEventType.RESPONSE_OUTPUT_ITEM_DONE,
            "response_id": self._active_response_id,
            "output_index": 0,
            "item": item
        }
        await self._send_event(event)

    async def send_content_part_added(self, part: Dict[str, Any]) -> None:
        """
        Send a content part added event.
        
        This method sends an event indicating a new content part has been added
        to a response. It's useful for testing complex content structures.
        
        Args:
            part (Dict[str, Any]): Part data to include in the event.
        """
        event = {
            "type": ServerEventType.RESPONSE_CONTENT_PART_ADDED,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "content_index": 0,
            "part": part
        }
        await self._send_event(event)

    async def send_content_part_done(self, part: Dict[str, Any], status: str = "completed") -> None:
        """
        Send a content part done event.
        
        This method sends an event indicating a content part is complete.
        It's useful for testing content completion scenarios.
        
        Args:
            part (Dict[str, Any]): Part data to include in the event.
            status (str): Status of the completed part. Default: "completed"
        """
        event = {
            "type": ServerEventType.RESPONSE_CONTENT_PART_DONE,
            "response_id": self._active_response_id,
            "item_id": str(uuid.uuid4()),
            "output_index": 0,
            "content_index": 0,
            "part_id": str(uuid.uuid4()),
            "status": status,
            "part": part
        }
        await self._send_event(event)

    async def send_error(self, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Send an error event.
        
        This method sends an error event to the client. It's useful for
        testing error handling and edge cases.
        
        Args:
            code (str): Error code.
            message (str): Error message.
            details (Optional[Dict[str, Any]]): Additional error details.
        """
        event = {
            "type": ServerEventType.ERROR,
            "code": code,
            "message": message,
            "details": details
        }
        await self._send_event(event)

    async def send_rate_limits(self, limits: List[Dict[str, Any]]) -> None:
        """
        Send rate limits update event.
        
        This method sends a rate limits update event to the client.
        It's useful for testing rate limiting scenarios.
        
        Args:
            limits (List[Dict[str, Any]]): List of rate limit updates.
        """
        event = {
            "type": ServerEventType.RATE_LIMITS_UPDATED,
            "rate_limits": limits
        }
        await self._send_event(event) 