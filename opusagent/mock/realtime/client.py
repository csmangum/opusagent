"""
Main LocalRealtimeClient implementation.

This module contains the main LocalRealtimeClient class that orchestrates
all the components (audio management, event handling, response generation)
to provide a complete mock implementation of the OpenAI Realtime API.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import websockets
from websockets.asyncio.client import ClientConnection

from opusagent.models.openai_api import ResponseCreateOptions, SessionConfig, ServerEventType

from .audio import AudioManager
from .handlers import EventHandlerManager
from .generators import ResponseGenerator
from .models import LocalResponseConfig


class LocalRealtimeClient:
    """
    Enhanced mock client that simulates the OpenAI Realtime API.
    
    This client provides a complete simulation of the OpenAI Realtime API
    WebSocket connection, including all event types, response streaming,
    audio handling, and function calls. It's designed to be a drop-in
    replacement for the real API during testing and development.
    
    The LocalRealtimeClient supports:
    - Multiple response configurations for different scenarios
    - Saved audio phrases from actual audio files
    - Configurable timing for realistic streaming simulation
    - Function call simulation with custom arguments
    - Audio file caching for performance
    - Automatic fallback to silence for missing audio files
    - Complete WebSocket event handling
    
    Key Features:
        - **Response Configuration**: Define different responses for different
          scenarios using LocalResponseConfig objects
        - **Audio Support**: Load and stream actual audio files instead of silence
        - **Function Calls**: Simulate function calls with custom arguments
        - **Event Handling**: Handle all OpenAI Realtime API event types
        - **Caching**: Cache audio files for improved performance
        - **Fallbacks**: Graceful handling of missing files and errors
    
    Attributes:
        logger (logging.Logger): Logger instance for debugging and monitoring
        session_config (SessionConfig): OpenAI session configuration
        response_configs (Dict[str, LocalResponseConfig]): Available response configurations
        default_response_config (LocalResponseConfig): Default response when no specific config matches
        connected (bool): Connection status
        _ws (Optional[ClientConnection]): WebSocket connection
        _audio_manager (AudioManager): Audio file management
        _event_handler (EventHandlerManager): Event handling
        _response_generator (ResponseGenerator): Response generation
        _message_task (Optional[asyncio.Task]): Message handling task
    
    Example:
        ```python
        # Create a basic mock client
        mock_client = LocalRealtimeClient()
        
        # Add custom response configurations
        mock_client.add_response_config(
            "greeting",
            LocalResponseConfig(
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
        response_configs: Optional[Dict[str, LocalResponseConfig]] = None,
        default_response_config: Optional[LocalResponseConfig] = None,
    ):
        """
        Initialize the LocalRealtimeClient.
        
        Args:
            logger (Optional[logging.Logger]): Logger instance for debugging.
                                             If None, creates a default logger.
            session_config (Optional[SessionConfig]): OpenAI session configuration.
                                                    If None, uses default settings.
            response_configs (Optional[Dict[str, LocalResponseConfig]]): Pre-configured
                                                                      response configurations
                                                                      for different scenarios.
            default_response_config (Optional[LocalResponseConfig]): Default response
                                                                   configuration when no
                                                                   specific config matches.
        
        Example:
            ```python
            # Basic initialization
            mock_client = LocalRealtimeClient()
            
            # With custom configurations
            configs = {
                "greeting": LocalResponseConfig(text="Hello!"),
                "help": LocalResponseConfig(text="How can I help?")
            }
            mock_client = LocalRealtimeClient(response_configs=configs)
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
        self.default_response_config = default_response_config or LocalResponseConfig()
        
        # Connection state
        self.connected = False
        self._ws: Optional[ClientConnection] = None
        self._message_task: Optional[asyncio.Task] = None
        
        # Initialize components
        self._audio_manager = AudioManager(logger=self.logger)
        self._event_handler = EventHandlerManager(
            logger=self.logger,
            session_config=self.session_config
        )
        self._response_generator = ResponseGenerator(
            logger=self.logger,
            audio_manager=self._audio_manager
        )
        
        # Set up response generation callback
        self._event_handler.register_event_handler(
            "response.create",
            self._handle_response_create
        )

    def add_response_config(self, key: str, config: LocalResponseConfig) -> None:
        """
        Add a response configuration for a specific scenario.
        
        This method allows you to dynamically add response configurations
        at runtime. The configuration will be available for use in subsequent
        response generation.
        
        Args:
            key (str): Unique identifier for this response configuration.
                      Used to select the appropriate response during generation.
            config (LocalResponseConfig): Configuration defining how the response
                                       should be generated.
        
        Example:
            ```python
            mock_client.add_response_config(
                "greeting",
                LocalResponseConfig(
                    text="Hello! How can I help you?",
                    audio_file="audio/greeting.wav",
                    delay_seconds=0.03
                )
            )
            ```
        """
        self.response_configs[key] = config
        self.logger.debug(f"Added response config for key: {key}")

    def get_response_config(self, key: Optional[str] = None) -> LocalResponseConfig:
        """
        Get a response configuration by key, or return the default configuration.
        
        This method implements the response selection logic. If a specific key
        is provided and exists in the response configurations, it returns that
        configuration. Otherwise, it returns the default configuration.
        
        Args:
            key (Optional[str]): Key to look up in response configurations.
                                If None or not found, returns default config.
        
        Returns:
            LocalResponseConfig: The selected response configuration.
        
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
            
            # Set up components with WebSocket connection
            self._event_handler.set_websocket_connection(self._ws)
            self._response_generator.set_websocket_connection(self._ws)
            
            # Start message handler
            self._message_task = asyncio.create_task(self._message_handler())
            
            # Send session created event
            await self._event_handler.send_session_created()
            
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
        if self._message_task:
            self._message_task.cancel()
            try:
                await self._message_task
            except asyncio.CancelledError:
                pass
        
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
        connection and processes them using the event handler manager.
        It handles connection closure gracefully.
        
        The message handler:
        - Listens for incoming WebSocket messages
        - Routes messages to the event handler manager
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
                # Decode message if it's bytes or bytearray
                if isinstance(message, (bytes, bytearray)):
                    message = message.decode('utf-8')
                elif isinstance(message, memoryview):
                    message = message.tobytes().decode('utf-8')
                await self._event_handler.handle_message(message)
                    
        except websockets.ConnectionClosed:
            self.logger.info("[MOCK REALTIME] Connection closed")
        except Exception as e:
            self.logger.error(f"[MOCK REALTIME] Message handler error: {e}")

    async def _handle_response_create(self, data: Dict[str, Any]) -> None:
        """
        Handle response.create events and generate responses.
        
        This method is called when a response.create event is received.
        It determines the appropriate response configuration and generates
        the response using the response generator.
        
        Args:
            data (Dict[str, Any]): Response creation data containing options.
        """
        try:
            # Get response options
            options = ResponseCreateOptions(**data.get("response", {}))
            
            # Get session state
            session_state = self._event_handler.get_session_state()
            active_response_id = session_state.get("active_response_id")
            
            # If no active response ID, create one (for direct calls from tests)
            if not active_response_id:
                active_response_id = str(uuid.uuid4())
                self._event_handler.update_session_state({"active_response_id": active_response_id})
                
                # Send response.created event
                event = {
                    "type": ServerEventType.RESPONSE_CREATED,
                    "response": {
                        "id": active_response_id,
                        "created_at": int(datetime.now().timestamp() * 1000)
                    }
                }
                await self._event_handler._send_event(event)
            
            # Set active response ID in generator
            self._response_generator.set_active_response_id(active_response_id)
            
            # Simulate response generation delay
            await asyncio.sleep(0.1)
            
            # Determine which response config to use
            response_key = self._determine_response_key(options)
            config = self.get_response_config(response_key)
            
            self.logger.info(f"[MOCK REALTIME] Generating response with config: {response_key or 'default'}")
            
            # Handle function calls if tools are enabled
            if options.tools and options.tool_choice != "none":
                await self._response_generator.generate_function_call(options, config)
                await self._response_generator.generate_response_done()
                return
            
            # Generate text response
            if "text" in options.modalities:
                await self._response_generator.generate_text_response(options, config)
            
            # Generate audio response
            if "audio" in options.modalities:
                await self._response_generator.generate_audio_response(options, config)
            
            # Send response done
            await self._response_generator.generate_response_done()
            
            self.logger.info(f"[MOCK REALTIME] Response generation completed: {active_response_id}")
            
        except Exception as e:
            self.logger.error(f"[MOCK REALTIME] Error generating response: {e}")
            # Send error event
            await self._response_generator.send_error("response_generation_failed", str(e))
            
        finally:
            # Clear active response ID
            self._event_handler.update_session_state({"active_response_id": None})

    # Additional utility methods for advanced usage

    async def load_audio_file(self, file_path: str) -> bytes:
        """
        Load an audio file using the audio manager.
        
        Args:
            file_path (str): Path to the audio file to load.
        
        Returns:
            bytes: Audio data as bytes.
        """
        return await self._audio_manager.load_audio_file(file_path)

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """
        Register a custom event handler.
        
        Args:
            event_type (str): The type of event to handle.
            handler (Callable): Async function to handle the event.
        """
        self._event_handler.register_event_handler(event_type, handler)

    async def send_error(self, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Send an error event.
        
        Args:
            code (str): Error code.
            message (str): Error message.
            details (Optional[Dict[str, Any]]): Additional error details.
        """
        await self._response_generator.send_error(code, message, details)

    async def send_transcript_delta(self, text: str, final: bool = False) -> None:
        """
        Send a transcript delta event for generated audio.
        
        Args:
            text (str): Transcript text to send.
            final (bool): Whether this is the final transcript chunk.
        """
        await self._response_generator.send_transcript_delta(text, final)

    async def send_input_transcript_delta(self, item_id: str, text: str, final: bool = False) -> None:
        """
        Send an input audio transcription delta event.
        
        Args:
            item_id (str): ID of the conversation item.
            text (str): Transcript text to send.
            final (bool): Whether this is the final transcript chunk.
        """
        await self._response_generator.send_input_transcript_delta(item_id, text, final)

    async def send_input_transcript_failed(self, item_id: str, error: Dict[str, Any]) -> None:
        """
        Send an input audio transcription failed event.
        
        Args:
            item_id (str): ID of the conversation item.
            error (Dict[str, Any]): Error details.
        """
        await self._response_generator.send_input_transcript_failed(item_id, error)

    # Audio management utilities

    def clear_audio_cache(self) -> None:
        """Clear the audio file cache."""
        self._audio_manager.clear_cache()

    def get_audio_cache_info(self) -> Dict[str, int]:
        """Get information about the audio cache."""
        return self._audio_manager.get_cache_info()

    def is_audio_cached(self, file_path: str) -> bool:
        """Check if an audio file is currently cached."""
        return self._audio_manager.is_cached(file_path)

    def remove_audio_from_cache(self, file_path: str) -> bool:
        """
        Remove a specific audio file from the cache.
        
        Args:
            file_path (str): Path of the audio file to remove from cache.
        
        Returns:
            bool: True if the file was removed, False if it wasn't cached.
        """
        return self._audio_manager.remove_from_cache(file_path)

    # Properties for backward compatibility with tests
    @property
    def session_id(self) -> str:
        """Get the current session ID."""
        return self._event_handler._session_state["session_id"]
    
    @property
    def conversation_id(self) -> str:
        """Get the current conversation ID."""
        return self._event_handler._session_state["conversation_id"]
    
    @property
    def _audio_buffer(self) -> List[bytes]:
        """Get the current audio buffer."""
        return self._event_handler._session_state["audio_buffer"]
    
    @_audio_buffer.setter
    def _audio_buffer(self, value: List[bytes]) -> None:
        """Set the audio buffer."""
        self._event_handler._session_state["audio_buffer"] = value
    
    @property
    def _active_response_id(self) -> Optional[str]:
        """Get the active response ID."""
        return self._response_generator._active_response_id
    
    @_active_response_id.setter
    def _active_response_id(self, value: Optional[str]) -> None:
        """Set the active response ID."""
        self._response_generator._active_response_id = value
        # Also update the session state for consistency
        self._event_handler._session_state["active_response_id"] = value

    # Methods for backward compatibility with tests
    async def _handle_session_update(self, data: Dict[str, Any]) -> None:
        """Handle session update events."""
        await self._event_handler._handle_session_update(data)
    
    async def _handle_audio_append(self, data: Dict[str, Any]) -> None:
        """Handle audio append events."""
        await self._event_handler._handle_audio_append(data)
    
    async def _handle_audio_commit(self, data: Dict[str, Any]) -> None:
        """Handle audio commit events."""
        await self._event_handler._handle_audio_commit(data)
    
    async def _handle_response_cancel(self, data: Dict[str, Any]) -> None:
        """Handle response cancel events."""
        # For direct calls from tests, ensure the response ID is set in session state
        response_id = data.get("response_id")
        if response_id and not self._event_handler._session_state.get("active_response_id"):
            self._event_handler._session_state["active_response_id"] = response_id
        
        await self._event_handler._handle_response_cancel(data)
        
        # Ensure the response generator's active response ID is also cleared
        # since the test checks self.client._active_response_id which returns
        # self._response_generator._active_response_id
        if self._event_handler._session_state.get("active_response_id") is None:
            self._response_generator._active_response_id = None
    
    async def send_rate_limits(self, limits: List[Dict[str, Any]]) -> None:
        """Send rate limits update."""
        await self._event_handler._send_event({
            "type": ServerEventType.RATE_LIMITS_UPDATED,
            "rate_limits": limits
        })
    
    async def send_content_part_added(self, part: Dict[str, Any]) -> None:
        """Send content part added event."""
        await self._response_generator._send_event({
            "type": ServerEventType.RESPONSE_CONTENT_PART_ADDED,
            "part": part
        })
    
    async def send_content_part_done(self, part: Dict[str, Any]) -> None:
        """Send content part done event."""
        await self._response_generator._send_event({
            "type": ServerEventType.RESPONSE_CONTENT_PART_DONE,
            "part": part,
            "status": "completed"
        }) 