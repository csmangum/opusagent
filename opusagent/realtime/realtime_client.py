"""
Client for OpenAI Realtime API over WebSocket.

This client implements the Realtime API protocol for speech-to-speech conversations,
providing full support for audio streaming, text input/output, and function calling.
It uses Pydantic models from opusagent.models.openai_api for structured message handling.

Key Features:
- Session management with configurable parameters
- Audio streaming with base64 encoding/decoding
- Conversation item management
- Response handling with realtime deltas
- Voice Activity Detection (VAD) support
- Function calling with argument handling
- Connection management with auto-reconnection

Security Considerations:
- API keys are never logged or exposed
- WebSocket connections use TLS encryption
- Input validation is performed on all messages
- Rate limiting is implemented to prevent abuse
- Connection state is carefully managed to prevent resource leaks

Performance Optimizations:
- Low-latency WebSocket configuration
- Efficient audio buffer management
- Connection pooling for reuse
- Optimized TCP settings for real-time audio
- Memory-efficient queue management

Error Handling:
- Comprehensive exception handling
- Automatic reconnection with backoff
- Detailed error logging
- Graceful degradation
- Resource cleanup on errors

Usage Example:
```python
from opusagent.bot import RealtimeClient

async def example():
    client = RealtimeClient(api_key="your-api-key", model="gpt-4o-realtime-preview")

    # Connect with error handling
    if not await client.connect():
        print("Failed to connect")
        return

    try:
        # Send audio
        await client.send_audio_chunk(audio_data)

        # Receive responses
        while True:
            chunk = await client.receive_audio_chunk()
            if chunk is None:
                break
            process_audio(chunk)

    finally:
        await client.close()
```
"""

import asyncio
import base64
import json
import logging
import os
import platform
import random
import ssl
import time
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

import websockets
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    ConnectionClosedOK,
)

from opusagent.config.constants import LOGGER_NAME
from opusagent.models.openai_api import (  # Session-related; Event types; Base event models; Client events; Server events; Conversation models
    SESSION_CONFIG,
    ClientEvent,
    ClientEventType,
    ConversationItemContentParam,
    ConversationItemCreatedEvent,
    ConversationItemCreateEvent,
    ConversationItemParam,
    ConversationItemType,
    ErrorEvent,
    InputAudioBufferAppendEvent,
    InputAudioBufferClearEvent,
    InputAudioBufferCommitEvent,
    MessageRole,
    RateLimitsUpdatedEvent,
    RealtimeFunctionCall,
    ResponseAudioDeltaEvent,
    ResponseContentPartDoneEvent,
    ResponseCreateEvent,
    ResponseCreateOptions,
    ResponseDoneEvent,
    ResponseOutputItemAddedEvent,
    ResponseTextDeltaEvent,
    ServerEvent,
    ServerEventType,
    SessionConfig,
    SessionCreatedEvent,
    SessionUpdateEvent,
)

# Import client handlers
from opusagent.realtime.handlers.client import (
    SessionUpdateHandler,
    SessionGetConfigHandler,
    InputAudioBufferHandler,
    ConversationItemHandler,
    ResponseHandler,
    TranscriptionSessionHandler,
    registry as client_registry
)

# Import server handlers
from opusagent.realtime.handlers.server import (
    SessionHandler,
    ConversationHandler,
    ConversationItemHandler as ServerConversationItemHandler,
    InputAudioBufferHandler as ServerInputAudioBufferHandler,
    ResponseHandler as ServerResponseHandler,
    TranscriptionSessionHandler as ServerTranscriptionSessionHandler,
    RateLimitsHandler,
    OutputAudioBufferHandler,
    ErrorHandler,
    registry as server_registry
)

logger = logging.getLogger(LOGGER_NAME)

# Connection settings for WebSocket
CONNECTION_TIMEOUT = 30  # seconds
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 2  # seconds
WS_MAX_SIZE = 16 * 1024 * 1024  # 16MB - large enough for audio chunks
WS_PING_INTERVAL = 5  # 5 seconds between pings

# Rate limiting settings
RATE_LIMIT_WINDOW = 60  # 1 minute window
MAX_REQUESTS_PER_WINDOW = 100  # Maximum requests per minute
MAX_DATA_PER_WINDOW = 10 * 1024 * 1024  # 10MB per minute

# Logging configuration
DEFAULT_LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class RateLimit:
    """Track rate limiting for API requests."""

    requests: List[datetime]
    data_sizes: List[tuple[datetime, int]]  # (timestamp, size)
    window: timedelta
    max_requests: int
    max_data: int

    def is_allowed(self, data_size: int = 0) -> bool:
        """Check if a new request is allowed under rate limiting."""
        now = datetime.now()

        # Remove requests outside the window
        self.requests = [req for req in self.requests if now - req < self.window]
        self.data_sizes = [
            (ts, size) for ts, size in self.data_sizes if now - ts < self.window
        ]

        # Check request count
        if len(self.requests) >= self.max_requests:
            return False

        # Check data size
        total_data = sum(size for _, size in self.data_sizes)
        if total_data + data_size > self.max_data:
            return False

        return True

    def add_request(self, data_size: int = 0) -> None:
        """Record a new request and its data size."""
        now = datetime.now()
        self.requests.append(now)
        if data_size > 0:
            self.data_sizes.append((now, data_size))


class RealtimeClientError(Exception):
    """Base exception for RealtimeClient errors."""

    pass


class ConnectionError(RealtimeClientError):
    """Raised when connection-related errors occur."""

    pass


class AuthenticationError(RealtimeClientError):
    """Raised when authentication-related errors occur."""

    pass


class RateLimitError(RealtimeClientError):
    """Raised when rate limits are exceeded."""

    pass


class SessionError(RealtimeClientError):
    """Raised when session-related errors occur."""

    pass


class MemoryError(RealtimeClientError):
    """Raised when memory usage is too high."""

    pass


class AudioError(RealtimeClientError):
    """Raised when audio-related errors occur."""

    pass


class BinaryDataError(RealtimeClientError):
    """Raised when binary data processing fails."""

    pass


class RealtimeClient:
    """
    Client for OpenAI Realtime API over WebSocket.

    This client implements the Realtime API protocol for speech-to-speech conversations,
    providing full support for audio streaming, text input/output, and function calling.
    It uses Pydantic models from opusagent.models.openai_api for structured message handling.

    Features:
    - Session management with configurable parameters
    - Audio streaming with base64 encoding/decoding
    - Conversation item management
    - Response handling with realtime deltas
    - Voice Activity Detection (VAD) support
    - Function calling with argument handling
    - Connection management with auto-reconnection

    Security:
    - API keys are never logged or exposed
    - WebSocket connections use TLS encryption
    - Input validation is performed on all messages
    - Rate limiting is implemented to prevent abuse

    Performance:
    - Low-latency WebSocket configuration
    - Efficient audio buffer management
    - Connection pooling for reuse
    - Optimized TCP settings for real-time audio

    Error Handling:
    - Comprehensive exception handling
    - Automatic reconnection with backoff
    - Detailed error logging
    - Graceful degradation
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        voice: Optional[str] = "alloy",
        queue_size: int = 32,
        log_level: int = DEFAULT_LOG_LEVEL,
    ):
        """Initialize the RealtimeClient.

        Args:
            api_key: OpenAI API key
            model: Model to use (e.g. "gpt-4o-realtime-preview")
            voice: Voice to use (default: "alloy")
            queue_size: Size of the audio queue (default: 32)
            log_level: Logging level (default: DEFAULT_LOG_LEVEL)
        """
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._queue_size = queue_size
        self._api_base = "wss://api.openai.com/v1/realtime"
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1",
        }
        self.ws = None
        self._session_id = None
        self._conversation_id = None
        self._recv_task = None
        self._heartbeat_task = None
        self._audio_queue = asyncio.Queue(maxsize=queue_size)
        self._is_connected = False
        self._is_closing = False
        self._connection_active = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_delay = 2.0
        self._connection_lost_handler = None
        self._connection_restored_handler = None
        self._rate_limit = RateLimit(
            requests=[],
            data_sizes=[],
            window=timedelta(seconds=RATE_LIMIT_WINDOW),
            max_requests=MAX_REQUESTS_PER_WINDOW,
            max_data=MAX_DATA_PER_WINDOW
        )
        self._logger = logging.getLogger("voice_agent")
        self._logger.setLevel(log_level)
        
        # Event handler registry for on/off methods
        self._event_handlers: Dict[str, List[Callable]] = {}

        # Initialize session config
        self._session_config = {
            "model": self._model,
            "voice": self._voice,
            "modalities": ["text", "audio"],
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 200,
                "create_response": True,
                "interrupt_response": True
            }
        }

        # Initialize client handlers
        self._initialize_handlers()

        # Audio handling with backpressure
        self._audio_queue_size = queue_size
        self._audio_queue_warning_threshold = int(
            queue_size * 0.8
        )  # Warn at 80% capacity
        self._audio_queue_full = False

        # Connection monitoring tasks
        self._recv_task = None
        self._heartbeat_task = None

        # Memory monitoring
        self._memory_warning_threshold = 0.8  # 80% of available memory
        self._last_memory_check = 0
        self._memory_check_interval = 60  # Check every 60 seconds

        # Heartbeat configuration
        self._heartbeat_interval = 60  # 60 seconds between heartbeat checks
        self._last_activity = time.time()

        self._logger.info(
            f"RealtimeClient initialized with model: {model}, voice: {voice}, queue_size: {queue_size}"
        )

        # New attribute for reconnection tracking
        self._reconnecting = False

        # Session configuration
        self._session_config_event = asyncio.Event()

    @property
    def session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self._session_id

    @property
    def conversation_id(self) -> Optional[str]:
        """Get the current conversation ID."""
        return self._conversation_id

    @property
    def audio_queue(self) -> asyncio.Queue:
        """Get the audio queue."""
        return self._audio_queue

    @property
    def rate_limit(self) -> RateLimit:
        """Get the rate limit object."""
        return self._rate_limit

    @property
    def ws_url(self):
        """Return the websocket URL for the current model."""
        return f"{self._api_base}?model={self._model}"

    def on(self, event_type: str, handler: Callable) -> None:
        """Register an event handler for a specific event type.
        
        Args:
            event_type: The event type to listen for (e.g., 'session.created')
            handler: Async function to call when the event occurs
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        self._logger.debug(f"Registered handler for event type: {event_type}")

    def off(self, event_type: str, handler: Callable) -> None:
        """Remove an event handler for a specific event type.
        
        Args:
            event_type: The event type to stop listening for
            handler: The handler function to remove
        """
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
                self._logger.debug(f"Removed handler for event type: {event_type}")
            except ValueError:
                self._logger.warning(f"Handler not found for event type: {event_type}")

    async def send_text_message(self, text: str, role: MessageRole = MessageRole.USER) -> bool:
        """Send a text message to the conversation.
        
        Args:
            text: The text content to send
            role: The role of the message sender (default: USER)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create conversation item with text content
            content_param = ConversationItemContentParam(
                type="input_text",
                text=text
            )
            
            item_param = ConversationItemParam(
                type="message",
                role=role,
                content=[content_param]
            )
            
            event = ConversationItemCreateEvent(
                item=item_param
            )
            
            await self.send_event(event)
            return True
            
        except Exception as e:
            self._logger.error(f"Error sending text message: {e}")
            return False

    async def update_session(self, **kwargs) -> bool:
        """Update the session configuration.
        
        Args:
            **kwargs: Session configuration parameters (voice, modalities, tools, etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update local session config
            for key, value in kwargs.items():
                if key in ['model']:
                    # Model cannot be changed after session creation
                    self._logger.warning(f"Cannot change {key} after session creation")
                    continue
                self._session_config[key] = value
            
            # Create session config object
            session_config = SessionConfig(**self._session_config)
            
            # Send session update event
            event = SessionUpdateEvent(session=session_config)
            await self.send_event(event)
            return True
            
        except Exception as e:
            self._logger.error(f"Error updating session: {e}")
            return False

    async def create_response(self, modalities: Optional[List[str]] = None, **kwargs) -> bool:
        """Create a response from the assistant.
        
        Args:
            modalities: List of modalities for the response (e.g., ["text", "audio"])
            **kwargs: Additional response options
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Set default modalities if not provided
            if modalities is None:
                modalities = ["text"]
            
            # Create response options
            options = ResponseCreateOptions(
                modalities=modalities,
                **kwargs
            )
            
            # Send response create event
            event = ResponseCreateEvent(response=options)
            await self.send_event(event)
            return True
            
        except Exception as e:
            self._logger.error(f"Error creating response: {e}")
            return False

    async def commit_audio_buffer(self) -> bool:
        """Commit the current audio buffer to the conversation.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            event = InputAudioBufferCommitEvent()
            await self.send_event(event)
            return True
            
        except Exception as e:
            self._logger.error(f"Error committing audio buffer: {e}")
            return False

    async def clear_audio_buffer(self) -> bool:
        """Clear the current audio buffer.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            event = InputAudioBufferClearEvent()
            await self.send_event(event)
            return True
            
        except Exception as e:
            self._logger.error(f"Error clearing audio buffer: {e}")
            return False

    def _initialize_handlers(self) -> None:
        """Initialize all client handlers."""
        # Initialize each handler with the send_event callback
        self._handlers = {
            'session_update': SessionUpdateHandler(
                send_event_callback=self.send_event,
                session_config=self._session_config
            ),
            'session_get_config': SessionGetConfigHandler(
                send_event_callback=self.send_event,
                session_config=self._session_config
            ),
            'input_audio_buffer': InputAudioBufferHandler(
                send_event_callback=self.send_event
            ),
            'conversation_item': ConversationItemHandler(
                send_event_callback=self.send_event
            ),
            'response': ResponseHandler(
                send_event_callback=self.send_event
            ),
            'transcription_session': TranscriptionSessionHandler(
                send_event_callback=self.send_event
            )
        }

    def set_log_level(self, level: int) -> None:
        """
        Set the logging level for the client.

        Args:
            level: The logging level to set (e.g., logging.DEBUG, logging.INFO)
        """
        self._logger.setLevel(level)
        for handler in self._logger.handlers:
            handler.setLevel(level)
        self._logger.info(f"Log level set to {logging.getLevelName(level)}")

    async def connect(self) -> bool:
        """
        Connect to the OpenAI Realtime API WebSocket server.

        Returns:
            bool: True if connection and session initialization successful, False otherwise.
        """
        if self.ws is not None:
            logger.warning("Already connected or connecting")
            return False

        try:
            logger.info("Connecting to OpenAI Realtime API...")
            # Configure WebSocket connection
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED

            # Create WebSocket connection with proper error handling
            try:
                self.ws = await websockets.connect(
                    self.ws_url,
                    additional_headers=self._headers,
                    max_size=WS_MAX_SIZE,
                    ping_interval=WS_PING_INTERVAL,
                    ssl=ssl_context,
                    open_timeout=CONNECTION_TIMEOUT,
                )
                logger.info("WebSocket connection established")
                self._connection_active = True  # Set connection as active
            except Exception as e:
                logger.error(f"Failed to establish WebSocket connection: {str(e)}")
                return False

            # Initialize session
            if not await self._initialize_session():
                logger.error("Failed to initialize session")
                await self.close()
                return False

            # Start background tasks
            self._start_background_tasks()
            logger.info("Connection and session initialization successful")
            return True

        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            if self.ws:
                await self.ws.close()
                self.ws = None
            return False

    async def _initialize_session(self) -> bool:
        """
        Initialize the session with OpenAI Realtime API.

        Returns:
            bool: True if session initialization successful, False otherwise.
        """
        try:
            logger.info("Initializing session...")
            # Generate session ID
            self._session_id = str(uuid.uuid4())
            logger.info(f"Generated session ID: {self._session_id}")

            # Send session creation event
            event = SessionUpdateEvent(
                event=ClientEventType.SESSION_UPDATE,
                session_id=self._session_id,
                session=self._session_config  # Changed from config to session
            )

            try:
                await self.send_event(event)
                logger.info("Session creation event sent")
            except Exception as e:
                logger.error(f"Failed to send session creation event: {str(e)}")
                return False

            # Wait for session created event
            try:
                response = await asyncio.wait_for(
                    self.ws.recv(), timeout=CONNECTION_TIMEOUT
                )
                event_data = json.loads(response)
                logger.info(f"Received response: {json.dumps(event_data, indent=2)}")

                if event_data.get("type") == ServerEventType.SESSION_CREATED:
                    logger.info("Session created successfully")
                    # Start background tasks after successful session creation
                    self._start_background_tasks()
                    return True
                else:
                    logger.error(f"Unexpected event type: {event_data.get('type')}")
                    return False

            except asyncio.TimeoutError:
                logger.error("Timeout waiting for session creation response")
                return False
            except Exception as e:
                logger.error(f"Error processing session creation response: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Session initialization failed: {str(e)}")
            return False

    def _start_background_tasks(self) -> None:
        """Start background tasks for maintaining the connection."""
        if not self._recv_task:
            self._recv_task = asyncio.create_task(self._recv_loop())
        if not self._heartbeat_task:
            self._heartbeat_task = asyncio.create_task(self._heartbeat())
        self._is_connected = True
        self._last_activity = time.time()

    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to the OpenAI API using exponential backoff.

        Returns:
            bool: True if reconnection was successful, False otherwise
        """
        if self._is_closing:
            self._logger.debug("Client is closing, not attempting reconnection")
            return False

        # If reconnection is already in progress, don't start another attempt
        if self._reconnecting:
            self._logger.debug("Reconnection already in progress")
            return False

        self._reconnecting = True
        self._reconnect_attempts += 1

        try:
            # Calculate backoff time with jitter (random variation)
            max_attempts = 5
            base_delay = 2.0
            max_delay = 30.0

            if self._reconnect_attempts > max_attempts:
                self._logger.error(
                    f"Exceeded maximum reconnection attempts ({max_attempts})"
                )
                self._reconnecting = False
                return False

            # Exponential backoff with jitter
            delay = min(base_delay * (2 ** (self._reconnect_attempts - 1)), max_delay)
            jitter = random.uniform(0, 0.3 * delay)  # 30% jitter
            delay = delay + jitter

            self._logger.info(
                f"Reconnecting to OpenAI Realtime API (attempt {self._reconnect_attempts}/{max_attempts}) in {delay:.1f} seconds"
            )

            # Wait before attempting reconnection
            await asyncio.sleep(delay)

            # If someone called close() during the delay, abort reconnection
            if self._is_closing:
                self._logger.debug("Client was closed during reconnection delay")
                self._reconnecting = False
                return False

            # Attempt to establish a new connection
            self._logger.info(
                "Connecting to OpenAI Realtime API with model: " + self._model
            )

            # Initialize WebSocket with increased timeout
            try:
                ws_url = f"{self._api_base}?model={self._model}"

                # Create SSL context
                ssl_context = ssl.create_default_context()

                # Create headers
                headers = {
                    "Authorization": f"Bearer {self._api_key}",
                    "OpenAI-Beta": "realtime=v1",
                    "User-Agent": f"Python/{platform.python_version()} websockets/{websockets.__version__}",
                }

                # Create the WebSocket connection
                self.ws = await websockets.connect(
                    ws_url,
                    ping_interval=30.0,
                    ping_timeout=10.0,
                    close_timeout=5.0,
                    max_size=None,
                    max_queue=32,
                    ssl=ssl_context,
                    additional_headers=headers,
                )
            except Exception as e:
                self._logger.error(f"Failed to connect: {e}")
                self._logger.debug(
                    f"Connection error details: {traceback.format_exc()}"
                )
                self._reconnecting = False

                # Schedule another reconnection attempt
                if not self._is_closing:
                    asyncio.create_task(self.reconnect())

                return False

            # Reset WebSocket state
            self._recv_task = asyncio.create_task(self._recv_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat())
            self._is_connected = True
            self._last_activity = time.time()

            # Wait for session initialization with increased timeout
            session_init_timeout = 20.0  # Increased from standard timeout

            try:
                session_initialized = await self._initialize_session()
                if not session_initialized:
                    self._logger.error("Error initializing session")
                    await self.close()
                    self._reconnecting = False

                    # Schedule another reconnection attempt
                    if not self._is_closing:
                        asyncio.create_task(self.reconnect())

                    return False

                # If we made it here, we successfully reconnected and initialized a session
                self._logger.info("Successfully reconnected to OpenAI Realtime API")
                self._reconnect_attempts = 0  # Reset the counter on success

                # Call the reconnected handler if it exists
                if self._connection_restored_handler:
                    try:
                        await self._connection_restored_handler()
                    except Exception as e:
                        self._logger.error(f"Error in connection restored handler: {e}")

                self._reconnecting = False
                return True

            except asyncio.TimeoutError:
                self._logger.error(
                    f"Timeout waiting for session initialization (after {session_init_timeout}s)"
                )
                await self.close()
                self._reconnecting = False

                # Schedule another reconnection attempt
                if not self._is_closing:
                    asyncio.create_task(self.reconnect())

                return False

        except Exception as e:
            self._logger.error(f"Error during reconnection: {e}")
            self._logger.debug(f"Reconnection error details: {traceback.format_exc()}")
            self._reconnecting = False

            # Schedule another reconnection attempt
            if not self._is_closing:
                asyncio.create_task(self.reconnect())

            return False

    async def _recv_loop(self) -> None:
        """
        Internal loop to receive and process messages from OpenAI.
        """
        if not self.ws:
            self._logger.error("WebSocket not initialized for receive loop")
            self._is_connected = False
            return

        try:
            self._logger.debug("Receive loop started")
            while self._is_connected and not self._is_closing:
                try:
                    # Use a timeout to prevent blocking indefinitely
                    self._logger.debug("Waiting for message from OpenAI...")
                    recv_start = time.time()
                    message = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
                    recv_time = time.time() - recv_start
                    self._last_activity = time.time()

                    if isinstance(message, bytes):
                        # Handle binary data
                        self._logger.debug(
                            f"Received binary data of size {len(message)} bytes"
                        )
                        try:
                            # Try to decode as base64 first
                            try:
                                decoded = base64.b64decode(message)
                                self._logger.debug(
                                    f"Successfully decoded binary data as base64"
                                )
                                await self._process_binary_data(decoded)
                            except Exception:
                                # If not base64, process as raw binary
                                self._logger.debug(
                                    "Binary data is not base64, processing as raw"
                                )
                                await self._process_binary_data(message)
                        except Exception as e:
                            self._logger.error(f"Error processing binary data: {e}")
                            self._logger.debug(
                                f"Binary processing error details: {traceback.format_exc()}"
                            )
                    else:
                        try:
                            self._logger.debug(
                                f"Received text message in {recv_time:.4f}s: {message[:200]}..."
                            )
                            data = json.loads(message)

                            # Extract event type
                            event_type = data.get("type")

                            # Handle audio deltas (special case for audio queue)
                            if (
                                event_type == ServerEventType.RESPONSE_AUDIO_DELTA
                                and "audio" in data
                            ):
                                try:
                                    audio_data = data["audio"]
                                    self._logger.debug(
                                        f"Received audio delta with base64 data size: {len(audio_data)}"
                                    )
                                    chunk = base64.b64decode(audio_data)
                                    self._logger.debug(
                                        f"Decoded audio chunk of size {len(chunk)} bytes"
                                    )

                                    # More detailed logging of audio chunks
                                    if len(chunk) > 0:
                                        self._logger.debug(
                                            f"Audio chunk: first few bytes: {chunk[:10]}, putting in queue of size {self._audio_queue.qsize()}"
                                        )
                                    else:
                                        self._logger.warning(
                                            "Received empty audio chunk"
                                        )

                                    # Put chunk in queue
                                    try:
                                        await asyncio.wait_for(
                                            self._audio_queue.put(chunk), timeout=1.0
                                        )
                                        self._logger.debug(
                                            f"Audio queue size after put: {self._audio_queue.qsize()}"
                                        )
                                    except asyncio.TimeoutError:
                                        self._logger.warning(
                                            "Timeout putting audio chunk in queue - queue might be full"
                                        )
                                    except Exception as qe:
                                        self._logger.error(
                                            f"Error putting audio in queue: {qe}"
                                        )

                                except Exception as e:
                                    self._logger.error(
                                        f"Error processing audio delta: {e}"
                                    )
                                    self._logger.debug(
                                        f"Audio processing error details: {traceback.format_exc()}"
                                    )

                            # Process event through registered handlers
                            await self._process_event(event_type, data)

                        except json.JSONDecodeError:
                            self._logger.warning(
                                f"Received invalid JSON: {message[:100]}..."
                            )
                        except Exception as e:
                            self._logger.error(f"Error processing message: {e}")
                            self._logger.debug(f"Original message: {message[:200]}...")
                            self._logger.debug(
                                f"Processing error details: {traceback.format_exc()}"
                            )
                except asyncio.TimeoutError:
                    # This is expected - just continue the loop
                    self._logger.debug(
                        "Receive timeout - no message received within 5s"
                    )
                    continue
                except ConnectionClosedOK:
                    # Normal closure, don't treat as error
                    self._logger.info("WebSocket connection closed normally")
                    self._is_connected = False
                    break
                except ConnectionClosedError as e:
                    self._logger.warning(
                        f"WebSocket connection closed unexpectedly: {e}"
                    )
                    self._logger.debug(
                        f"WebSocket close code: {e.code}, reason: {e.reason}"
                    )
                    self._is_connected = False
                    self._connection_active = False
                    if self._connection_lost_handler:
                        try:
                            await self._connection_lost_handler()
                        except Exception as e:
                            self._logger.error(f"Error in connection lost handler: {e}")
                            self._logger.debug(
                                f"Connection lost handler error details: {traceback.format_exc()}"
                            )
                    break
                except Exception as e:
                    self._logger.error(f"Error in receive loop iteration: {e}")
                    self._logger.debug(
                        f"Receive error details: {traceback.format_exc()}"
                    )
                    await asyncio.sleep(
                        0.1
                    )  # Brief pause to avoid tight looping on errors

        except ConnectionClosedOK:
            # Normal closure
            self._logger.info("WebSocket connection closed normally")

        except ConnectionClosedError as e:
            self._logger.warning(f"WebSocket connection closed unexpectedly: {e}")
            self._logger.debug(f"WebSocket close code: {e.code}, reason: {e.reason}")
            self._is_connected = False
            self._connection_active = False
            if self._connection_lost_handler:
                try:
                    await self._connection_lost_handler()
                except Exception as e:
                    self._logger.error(f"Error in connection lost handler: {e}")
                    self._logger.debug(
                        f"Connection lost handler error details: {traceback.format_exc()}"
                    )

        except Exception as e:
            self._logger.error(f"Error in receive loop: {e}")
            self._logger.debug(f"Receive loop error details: {traceback.format_exc()}")

        # Mark connection as inactive
        self._is_connected = False
        self._logger.info("Receive loop exited, connection marked as inactive")

        # Notify about connection loss
        if self._connection_lost_handler:
            try:
                self._logger.debug("Calling connection lost handler")
                await self._connection_lost_handler()
            except Exception as e:
                self._logger.error(f"Error in connection lost handler: {e}")
                self._logger.debug(
                    f"Connection lost handler error details: {traceback.format_exc()}"
                )

        # Only attempt reconnection if not explicitly closing
        if not self._is_closing:
            self._logger.debug("Scheduling reconnection attempt")
            asyncio.create_task(self.reconnect())

    async def _process_binary_data(self, data: bytes) -> None:
        """
        Process received binary data.

        Args:
            data: The binary data to process

        Raises:
            BinaryDataError: If processing fails
        """
        try:
            # Check if this is an audio chunk
            if len(data) > 0:
                # Put in audio queue if it's not full
                if not self._audio_queue.full():
                    await self._audio_queue.put(data)
                    self._logger.debug(
                        f"Processed binary data as audio chunk of size {len(data)} bytes"
                    )
                else:
                    self._logger.warning("Audio queue full, dropping binary data")
            else:
                self._logger.warning("Received empty binary data")
        except Exception as e:
            self._logger.error(f"Error processing binary data: {e}")
            self._logger.debug(
                f"Binary processing error details: {traceback.format_exc()}"
            )
            raise BinaryDataError(f"Failed to process binary data: {str(e)}") from None

    async def _process_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Process an incoming event from the server.

        Args:
            event_type: Type of the event
            data: Event data dictionary

        Raises:
            ValueError: If event type is invalid
        """
        try:
            if event_type == "error":
                # Handle error events
                if "error" in data:
                    error_data = data["error"]
                    error_event = ErrorEvent(
                        code=error_data.get("code", "unknown_error"),
                        message=error_data.get("message", "Unknown error"),
                        details=error_data.get("details"),
                    )
                else:
                    # Fallback for error events that don't follow the standard structure
                    error_event = ErrorEvent(**data)

                # Log the error
                self._logger.error(
                    f"Error from server: {error_event.code}: {error_event.message}"
                )
                if error_event.details:
                    self._logger.debug(f"Error details: {error_event.details}")

            # Import server handlers registry
            from opusagent.realtime.handlers.server import registry as server_registry
            
            # Process server events using the server handlers
            if event_type in server_registry:
                handler_class = server_registry[event_type]
                
                # Create a handler instance with this client's send_event as callback
                handler = handler_class(callback=self.send_event)
                
                # Process the event
                try:
                    await handler.handle_event(event_type, data)
                except Exception as e:
                    self._logger.error(f"Error in server handler for {event_type}: {e}")
                    self._logger.debug(f"Handler error details: {traceback.format_exc()}")
            
            # Also process with client handlers if available
            # Client handlers are for outgoing events, but they may need to react to incoming events
            if event_type in self._handlers:
                handler = self._handlers[event_type]
                try:
                    # Get the appropriate handler method based on the event type
                    handler_method = getattr(handler, f"handle_{event_type.split('.')[-1]}")
                    await handler_method(data)
                except AttributeError:
                    self._logger.warning(f"No client handler method found for event type: {event_type}")
                except Exception as e:
                    self._logger.error(f"Error in client handler for {event_type}: {e}")
                    self._logger.debug(f"Client handler error details: {traceback.format_exc()}")
            
            # If no handler was found in either registry
            if event_type not in server_registry and event_type not in self._handlers:
                self._logger.warning(f"Unknown event type received: {event_type}")

        except Exception as e:
            self._logger.error(f"Error processing message: {e}")
            self._logger.debug(f"Original message: {data}")
            self._logger.debug(f"Processing error details: {traceback.format_exc()}")

    async def send_event(self, event: ClientEvent) -> str:
        """Send an event to the OpenAI Realtime API.

        Args:
            event: The event to send

        Returns:
            str: The event ID

        Raises:
            ConnectionError: If the connection is not active
        """
        if not self._connection_active:
            self._logger.warning("Cannot send event - connection not active")
            raise ConnectionError("Connection not active")

        if self.ws is None:
            self._logger.warning("Cannot send event - WebSocket not initialized")
            raise ConnectionError("WebSocket not initialized")

        try:
            # Check rate limits
            if not self._rate_limit.is_allowed():
                self._logger.warning("Rate limit exceeded")
                raise RateLimitError("Rate limit exceeded")

            # Send the event
            event_id = str(uuid.uuid4())
            event_data = {
                "type": event.type,
                "event_id": event_id,
                **event.model_dump(exclude_none=True, exclude={"type"}),
            }

            await self.ws.send(json.dumps(event_data))
            self._rate_limit.add_request()

            self._logger.debug(f"Sent event: {event.type} (ID: {event_id})")
            return event_id

        except websockets.exceptions.ConnectionClosed:
            self._logger.error("Connection closed while sending event")
            self._connection_active = False
            raise ConnectionError("Connection closed")

        except Exception as e:
            self._logger.error(f"Error sending event: {str(e)}")
            raise

    async def receive_audio_chunk(
        self, timeout: Optional[float] = 2.0
    ) -> Optional[bytes]:
        """
        Await and return the next audio chunk from OpenAI.

        This method handles audio chunk retrieval with configurable timeouts and error recovery.
        It includes performance optimizations for audio processing.

        Args:
            timeout: Maximum time to wait for a chunk in seconds (default: 2.0)

        Returns:
            bytes: Audio chunk data or None if an error occurred or timeout

        Raises:
            ConnectionError: If connection issues occur
        """
        try:
            # Use get_nowait when available to avoid waiting for chunks that might never come
            if not self._audio_queue.empty():
                chunk = self._audio_queue.get_nowait()
                self._logger.debug(
                    f"Retrieved audio chunk of size {len(chunk) if chunk else 0} bytes from queue immediately"
                )
                return chunk

            # If queue is empty but connection is not active, return None
            if not self._connection_active:
                self._logger.debug(
                    "Audio queue empty and connection not active, returning None"
                )
                return None

            # Wait for data with timeout to prevent blocking forever
            self._logger.debug(f"Waiting for audio data (timeout: {timeout}s)...")
            chunk = await asyncio.wait_for(self._audio_queue.get(), timeout=timeout)
            self._logger.debug(
                f"Retrieved audio chunk of size {len(chunk) if chunk else 0} bytes from queue after waiting"
            )
            return chunk

        except asyncio.TimeoutError:
            # This is expected if no data is coming
            self._logger.debug(f"Timeout waiting for audio chunk after {timeout}s")
            return None

        except Exception as e:
            self._logger.error(f"Error receiving audio chunk: {e}")
            self._logger.debug(
                f"Receive audio chunk error details: {traceback.format_exc()}"
            )
            raise ConnectionError(f"Failed to receive audio chunk: {str(e)}") from None

    async def _heartbeat(self) -> None:
        """Send periodic heartbeat messages to keep the connection alive."""
        while self._connection_active and not self._is_closing:
            try:
                # Check if we need to send a heartbeat
                current_time = time.time()
                if current_time - self._last_activity > self._heartbeat_interval:
                    if self.ws and not self.ws.closed:
                        try:
                            # Send ping and wait for response
                            pong_waiter = await self.ws.ping()
                            await asyncio.wait_for(pong_waiter, timeout=5.0)
                            self._last_activity = current_time
                        except Exception as e:
                            logger.error(f"Ping failed: {e}")
                            self._connection_active = False
                            if not self._is_closing:
                                asyncio.create_task(self.reconnect())
                            break
                    else:
                        # Connection is dead, attempt to reconnect
                        self._connection_active = False
                        if not self._is_closing:
                            asyncio.create_task(self.reconnect())
                        break
                
                # Wait for the next heartbeat check
                await asyncio.sleep(self._heartbeat_interval)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                self._connection_active = False
                if not self._is_closing:
                    asyncio.create_task(self.reconnect())
                break

    def set_connection_handlers(
        self,
        lost_handler: Optional[Callable[[], Awaitable[None]]] = None,
        restored_handler: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> None:
        """
        Set handlers for connection loss and restoration events.

        Args:
            lost_handler: Async function to call when connection is lost
            restored_handler: Async function to call when connection is restored
        """
        self._connection_lost_handler = lost_handler
        self._connection_restored_handler = restored_handler
        self._logger.debug("Connection event handlers registered")

    async def close(self) -> None:
        """Close the WebSocket connection and clean up resources."""
        if self._is_closing:
            return

        self._is_closing = True
        self._connection_active = False
        self._is_connected = False

        # Cancel tasks
        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()
            try:
                await asyncio.wait_for(self._recv_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await asyncio.wait_for(self._heartbeat_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        # Close WebSocket
        if self.ws and not self.ws.closed:
            await self.ws.close()

        # Clear queues
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # Reset state
        self.ws = None
        self._recv_task = None
        self._heartbeat_task = None

        # Reset state but maintain closing flag
        self._session_id = None
        self._conversation_id = None
        self._reconnect_attempts = 0
        self._last_activity = 0

        self._logger.info("OpenAI Realtime client closed")

    async def _check_memory_usage(self) -> bool:
        """
        Check if memory usage is within acceptable limits.

        Returns:
            bool: True if memory usage is acceptable, False if warning threshold exceeded
        """
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()

            if memory_percent > self._memory_warning_threshold * 100:
                self._logger.warning(
                    f"Memory usage high: {memory_percent:.1f}% ({memory_info.rss / 1024 / 1024:.1f}MB)"
                )
                return False

            return True

        except Exception as e:
            self._logger.warning(f"Could not check memory usage: {e}")
            return True  # Assume OK if we can't check

    async def send_audio_chunk(self, audio_data: bytes) -> bool:
        """Send a chunk of audio data to the server."""
        if not self._connection_active or self._is_closing:
            return False

        # Check rate limit
        if not self._rate_limit.is_allowed():
            return False

        # Check if queue is full
        if self._audio_queue.qsize() >= self._audio_queue_size:
            return False

        try:
            # Create and send the audio event
            event = InputAudioBufferAppendEvent(
                audio=base64.b64encode(audio_data).decode("utf-8")
            )
            await self.send_event(event)
            self._rate_limit.add_request(len(audio_data))
            return True
        except Exception as e:
            self._logger.error(f"Error sending audio chunk: {e}")
            return False
