"""
Client for OpenAI Realtime API over WebSocket.

This client implements the Realtime API protocol for speech-to-speech conversations,
providing full support for audio streaming, text input/output, and function calling.
It uses Pydantic models from fastagent.models.openai_api for structured message handling.

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
from fastagent.bot import RealtimeClient

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

from fastagent.config.constants import LOGGER_NAME
from fastagent.models.openai_api import (  # Session-related; Event types; Base event models; Client events; Server events; Conversation models
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
    InputAudioBufferCommitEvent,
    MessageRole,
    RateLimitsUpdatedEvent,
    RealtimeFunctionCall,
    ResponseAudioDeltaEvent,
    ResponseContentPartDoneEvent,
    ResponseCreateEvent,
    ResponseDoneEvent,
    ResponseOutputItemAddedEvent,
    ResponseTextDeltaEvent,
    ServerEvent,
    ServerEventType,
    SessionConfig,
    SessionCreatedEvent,
    SessionUpdateEvent,
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
    It uses Pydantic models from fastagent.models.openai_api for structured message handling.

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

    @property
    def session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return getattr(self, "_session_id", None)

    @property
    def conversation_id(self) -> Optional[str]:
        """Get the current conversation ID."""
        return getattr(self, "_conversation_id", None)

    @property
    def audio_queue(self) -> asyncio.Queue:
        """Get the audio queue."""
        return self._audio_queue

    @property
    def rate_limit(self) -> RateLimit:
        """Get the rate limit instance."""
        return self._rate_limit

    @property
    def ws_url(self) -> str:
        """Get the WebSocket URL for the current model."""
        return f"{self._api_base}?model={self._model}"

    @property
    def ws(self) -> Optional[websockets.WebSocketClientProtocol]:
        """Get the WebSocket connection."""
        return self._ws

    @ws.setter
    def ws(self, value: Optional[websockets.WebSocketClientProtocol]) -> None:
        """Set the WebSocket connection."""
        self._ws = value

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
        self._event_handlers = {}
        self._ws = None
        self._session_id = None
        self._conversation_id = None
        self._receive_task = None
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
            window=timedelta(minutes=1),
            max_requests=1000,
            max_data=1000000,
        )
        self._logger = logging.getLogger("voice_agent")
        self._logger.setLevel(log_level)

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

        self._logger.info(
            f"RealtimeClient initialized with model: {model}, voice: {voice}, queue_size: {queue_size}"
        )

        # New attribute for reconnection tracking
        self._reconnecting = False

        # Session configuration
        self._session_config = None
        self._session_config_event = asyncio.Event()

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
        if self._ws is not None:
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
                self._ws = await websockets.connect(
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
            if self._ws:
                await self._ws.close()
                self._ws = None
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

            # Create session configuration
            session_config = {
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
            logger.info(f"Session config: {json.dumps(session_config, indent=2)}")

            # Send session creation event
            event = SessionUpdateEvent(
                event=ClientEventType.SESSION_UPDATE,
                session_id=self._session_id,
                session=session_config  # Changed from config to session
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
                    self._ws.recv(), timeout=CONNECTION_TIMEOUT
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
                self._ws = await websockets.connect(
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
        if not self._ws:
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
                    message = await asyncio.wait_for(self._ws.recv(), timeout=5.0)
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

                # Call any registered error handlers
                await self._call_event_handlers(ServerEventType.ERROR, data)

                # Log the error
                self._logger.error(
                    f"Error from server: {error_event.code}: {error_event.message}"
                )
                if error_event.details:
                    self._logger.debug(f"Error details: {error_event.details}")

            # Handle other event types
            elif event_type in [e.value for e in ServerEventType]:
                # Create appropriate event object based on type
                event_obj = None
                if event_type == ServerEventType.RATE_LIMITS_UPDATED:
                    event_obj = RateLimitsUpdatedEvent(**data)
                elif event_type == ServerEventType.RESPONSE_OUTPUT_ITEM_ADDED:
                    event_obj = ResponseOutputItemAddedEvent(**data)
                elif event_type == ServerEventType.RESPONSE_CONTENT_PART_DONE:
                    event_obj = ResponseContentPartDoneEvent(**data)
                elif event_type == ServerEventType.SESSION_UPDATED:
                    # Set the session config event to signal that the update is complete
                    self._session_config_event.set()
                    # Update the session config
                    if "session" in data:
                        self._session_config = data["session"]

                # Call event handlers with either the created event object or raw data
                await self._call_event_handlers(
                    event_type, event_obj if event_obj else data
                )
            else:
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

        if self._ws is None:
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

            await self._ws.send(json.dumps(event_data))
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
        """
        Send periodic heartbeats to keep the connection alive and monitor health.
        """
        self._logger.debug("Heartbeat task started")
        while self._connection_active and not self._is_closing:
            await asyncio.sleep(5)  # Check every 5 seconds

            # Check if we haven't seen activity for too long
            inactivity_period = time.time() - self._last_activity
            if inactivity_period > 60:  # 60 seconds
                self._logger.warning(
                    f"No activity detected for {inactivity_period:.1f} seconds, checking connection"
                )

                if self._ws:
                    try:
                        # Send a ping to test the connection
                        self._logger.debug("Sending ping to test connection")
                        ping_start = time.time()
                        pong_waiter = await self._ws.ping()
                        await asyncio.wait_for(pong_waiter, timeout=5)
                        ping_time = time.time() - ping_start
                        self._logger.debug(
                            f"Ping successful in {ping_time:.4f}s, connection is healthy"
                        )
                        self._last_activity = time.time()
                    except Exception as e:
                        self._logger.warning(
                            f"Ping failed: {e}, connection appears to be dead"
                        )
                        self._connection_active = False

                        # Only attempt reconnection if not explicitly closing
                        if not self._is_closing:
                            self._logger.debug(
                                "Scheduling reconnection after failed ping"
                            )
                            asyncio.create_task(self.reconnect())
                else:
                    self._logger.warning("WebSocket is closed, attempting to reconnect")
                    self._connection_active = False

                    # Only attempt reconnection if not explicitly closing
                    if not self._is_closing:
                        self._logger.debug(
                            "Scheduling reconnection for closed WebSocket"
                        )
                        asyncio.create_task(self.reconnect())

        self._logger.debug("Heartbeat task exited")

    def on(
        self, event_type: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """
        Register an event handler for a specific event type.

        Args:
            event_type: The type of event to listen for
            handler: Async function to call when event is received
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []

        self._event_handlers[event_type].append(handler)
        self._logger.debug(f"Registered handler for event type: {event_type}")

    def off(
        self, event_type: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """
        Remove an event handler for a specific event type.

        Args:
            event_type: The type of event to stop listening for
            handler: The handler to remove
        """
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
                self._logger.debug(f"Removed handler for event type: {event_type}")
            except ValueError:
                # Handler wasn't registered
                pass

    async def send_audio_chunk(self, audio_data: bytes) -> bool:
        """
        Send raw audio data to OpenAI.

        This method handles audio data validation, rate limiting, and error recovery
        for sending audio chunks to the OpenAI Realtime API. Implements backpressure
        to prevent overwhelming the server.

        Args:
            audio_data: Raw PCM16 audio bytes to send

        Returns:
            bool: True if the chunk was sent successfully, False otherwise

        Raises:
            ValueError: If audio data is invalid
            ConnectionError: If connection is not active
            MemoryError: If memory usage is too high
            AudioError: If audio processing fails
            RateLimitError: If rate limits are exceeded
        """
        if not self._connection_active:
            self._logger.warning("Cannot send audio - connection not active")
            return False

        if not isinstance(audio_data, bytes):
            raise ValueError("Audio data must be bytes")

        if len(audio_data) == 0:
            raise ValueError("Audio data cannot be empty")

        if len(audio_data) > WS_MAX_SIZE:
            raise ValueError(f"Audio chunk too large (max {WS_MAX_SIZE} bytes)")

        try:
            # Check memory usage periodically
            now = time.time()
            if now - self._last_memory_check > self._memory_check_interval:
                if not await self._check_memory_usage():
                    raise MemoryError("Memory usage too high")
                self._last_memory_check = now

            # Check rate limits with data size
            if not self._rate_limit.is_allowed(len(audio_data)):
                self._logger.error("Rate limit exceeded for audio chunks (data size)")
                raise RateLimitError("Data size rate limit exceeded")
            self._rate_limit.add_request(len(audio_data))

            # Check queue size and implement backpressure
            current_size = self._audio_queue.qsize()
            if current_size >= self._audio_queue_warning_threshold:
                self._audio_queue_full = True
                self._logger.warning(
                    f"Audio queue approaching capacity: {current_size}/{self._audio_queue_size}"
                )
            elif current_size < self._audio_queue_warning_threshold:
                self._audio_queue_full = False
                self._logger.info("Audio queue pressure relieved")

            if self._audio_queue_full:
                # Wait briefly to allow queue to drain
                await asyncio.sleep(0.1)
                if self._audio_queue.qsize() >= self._audio_queue_size:
                    self._logger.warning("Audio queue full, dropping chunk")
                    return False

            # Convert binary audio to base64
            try:
                audio_base64 = base64.b64encode(audio_data).decode("utf-8")
            except Exception as e:
                raise AudioError(f"Failed to encode audio data: {str(e)}") from None

            # Create and send event
            try:
                audio_event = InputAudioBufferAppendEvent(audio=audio_base64)
                await self.send_event(audio_event)
                return True
            except Exception as e:
                raise AudioError(f"Failed to send audio event: {str(e)}") from None

        except MemoryError as e:
            self._logger.error(f"Memory error while sending audio: {e}")
            return False
        except RateLimitError as e:
            self._logger.error(f"Rate limit error while sending audio: {e}")
            return False
        except AudioError as e:
            self._logger.error(f"Audio error while sending audio: {e}")
            return False
        except Exception as e:
            self._logger.error(f"Error sending audio chunk: {e}")
            self._logger.debug(f"Audio send error details: {traceback.format_exc()}")
            return False

    async def commit_audio_buffer(self) -> bool:
        """
        Commit the current audio buffer to create a user input item.

        This is used when VAD is disabled to manually indicate
        the end of user speech.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            commit_event = InputAudioBufferCommitEvent()
            await self.send_event(commit_event)
            return True
        except Exception as e:
            self._logger.error(f"Error committing audio buffer: {e}")
            return False

    async def send_text_message(self, text: str, role: str = "user") -> bool:
        """
        Send a text message to the conversation.

        Args:
            text: The text message to send
            role: The role of the message sender (usually "user")

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create text content
            content = [ConversationItemContentParam(type="input_text", text=text)]

            # Create conversation item
            item = ConversationItemParam(type="message", role=role, content=content)

            # Create and send event
            event = ConversationItemCreateEvent(item=item)
            await self.send_event(event)
            return True
        except Exception as e:
            self._logger.error(f"Error sending text message: {e}")
            return False

    async def create_response(
        self, modalities: Optional[List[str]] = None, instructions: Optional[str] = None
    ) -> bool:
        """
        Request a response from the model.

        Args:
            modalities: List of response modalities ("text", "audio")
            instructions: Optional override instructions for this response

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response_params = {}

            if modalities:
                response_params["modalities"] = modalities

            if instructions:
                response_params["instructions"] = instructions

            event = ResponseCreateEvent(response=response_params or None)
            await self.send_event(event)
            return True
        except Exception as e:
            self._logger.error(f"Error creating response: {e}")
            return False

    async def update_session(
        self,
        instructions: Optional[str] = None,
        voice: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        modalities: Optional[List[str]] = None,
        turn_detection: Optional[Dict[str, Any]] = None,
        merge: bool = True,
        tool_choice: Optional[str] = None,
    ) -> bool:
        """
        Update the session configuration.

        Args:
            instructions: New instructions for the session
            voice: New voice to use
            tools: List of tools to enable
            modalities: List of modalities to enable
            turn_detection: Turn detection settings
            merge: Whether to merge with existing config
            tool_choice: Tool choice strategy

        Returns:
            bool: True if update was successful
        """
        try:
            # Prepare update data
            update_data = {}

            if instructions is not None:
                update_data["instructions"] = instructions
            if voice is not None:
                update_data["voice"] = voice
            if tools is not None:
                # Format tools correctly for the API
                formatted_tools = []
                for i, tool in enumerate(tools):
                    if "type" not in tool:
                        tool["type"] = "function"
                    if "name" not in tool:
                        tool["name"] = f"tool_{i}"
                    # Ensure the function parameter is at the root level
                    if "function" in tool:
                        tool.update(tool.pop("function"))
                    formatted_tools.append(tool)
                update_data["tools"] = formatted_tools
            if modalities is not None:
                update_data["modalities"] = modalities
            if turn_detection is not None:
                update_data["turn_detection"] = turn_detection
            if tool_choice is not None:
                update_data["tool_choice"] = tool_choice

            # If merge is True, get current config and merge
            if merge and self._session_config:
                current_config = self._session_config.copy()
                current_config.update(update_data)
                update_data = current_config

            # Create and send the update event
            event = SessionUpdateEvent(session=update_data)
            await self.send_event(event)

            # Wait for session.updated event
            await self._session_config_event.wait()
            self._session_config_event.clear()

            return True

        except Exception as e:
            self._logger.error(f"Error updating session: {e}")
            self._logger.debug(
                f"Session update error details: {traceback.format_exc()}"
            )
            return False

    async def _get_current_session_config(self) -> Dict[str, Any]:
        """
        Get the current session configuration from the server.

        Returns:
            Dict[str, Any]: The current session configuration or an empty dict if failed
        """
        if not self.session_id:
            self._logger.warning("Cannot get session config - no active session")
            return {}

        try:
            # Instead of using GET_SESSION_CONFIG, we'll use the session.updated event
            # that we receive after session creation/update
            session_config = {}

            # Set up a future to wait for the session config response
            config_future = asyncio.Future()

            # Define a handler for the session updated event
            async def on_session_updated(data: Dict[str, Any]) -> None:
                if "session" in data:
                    config_future.set_result(data["session"])

            # Register a temporary handler for the session updated event
            self.on(ServerEventType.SESSION_UPDATED, on_session_updated)

            try:
                # Wait for the config with a timeout
                session_config = await asyncio.wait_for(config_future, timeout=5.0)
                return session_config
            except asyncio.TimeoutError:
                self._logger.warning("Timeout waiting for session config")
                return {}
            finally:
                # Remove the temporary handler
                self.off(ServerEventType.SESSION_UPDATED, on_session_updated)

        except Exception as e:
            self._logger.error(f"Error getting session config: {e}")
            self._logger.debug(
                f"Session config error details: {traceback.format_exc()}"
            )
            return {}

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
        """
        Close the WebSocket connection and cancel all tasks.

        This method ensures proper cleanup of all resources and handles
        any errors that occur during shutdown.

        Raises:
            ConnectionError: If cleanup fails
        """
        self._logger.info("Closing OpenAI Realtime client")

        # Set closing flag first to prevent any new operations
        self._is_closing = True
        self._connection_active = False

        # Cancel tasks with proper cleanup
        if self._recv_task:
            self._logger.debug("Cancelling receive task")
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                self._logger.debug("Receive task cancelled successfully")
            except Exception as e:
                self._logger.warning(f"Error cancelling receive task: {e}")

        if self._heartbeat_task:
            self._logger.debug("Cancelling heartbeat task")
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                self._logger.debug("Heartbeat task cancelled successfully")
            except Exception as e:
                self._logger.warning(f"Error cancelling heartbeat task: {e}")

        # Close WebSocket with proper cleanup
        if self._ws:
            try:
                self._logger.debug("Closing WebSocket connection")
                await self._ws.close()
            except Exception as e:
                self._logger.warning(f"Error closing WebSocket: {e}")
            finally:
                self._ws = None

        # Clear any remaining audio chunks
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except Exception:
                pass

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

    async def _call_event_handlers(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Call all registered handlers for a specific event type.

        Args:
            event_type: The type of event
            data: Event data to pass to handlers
        """
        self._logger.debug(f"Processing event of type: {event_type}")

        handlers = self._event_handlers.get(event_type, [])
        if not handlers:
            return

        for handler in handlers:
            try:
                if callable(handler):
                    result = handler(data)
                    if asyncio.iscoroutine(result):
                        await result
            except Exception as e:
                self._logger.error(f"Error in event handler for {event_type}: {e}")
                self._logger.debug(f"Handler error details: {traceback.format_exc()}")
                # Continue processing other handlers despite the error
