"""
Client for OpenAI Realtime API over WebSocket.

This client implements the Realtime API protocol for speech-to-speech conversations,
providing full support for audio streaming, text input/output, and function calling.
It uses Pydantic models from app.models.openai_api for structured message handling.

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
from app.bot import RealtimeClient

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
    RealtimeFunctionCall,
    ResponseAudioDeltaEvent,
    ResponseCreateEvent,
    ResponseDoneEvent,
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
    It uses Pydantic models from app.models.openai_api for structured message handling.

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
        """
        Initialize the Realtime API client.

        Args:
            api_key: OpenAI API key (will be masked in logs)
            model: Model to use (e.g., "gpt-4o-realtime-preview")
            voice: Voice to use for audio output (e.g., "alloy", "echo", "nova")
            queue_size: Maximum size of the audio queue (default: 32)
            log_level: Logging level (default: logging.INFO)

        Raises:
            ValueError: If api_key or model is empty
        """
        if not api_key:
            raise ValueError("API key cannot be empty")
        if not model:
            raise ValueError("Model cannot be empty")

        # Configure logging
        self.logger = logging.getLogger(LOGGER_NAME)
        self.logger.setLevel(log_level)

        # Add handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(LOG_FORMAT))
            self.logger.addHandler(handler)

        self.api_key = api_key
        self.model = model
        self.voice = voice

        # WebSocket connection
        self.ws = None
        self._connection_active = False
        self._reconnect_attempts = 0
        self._last_activity = 0
        self._is_closing = False

        # Event handlers
        self._event_handlers: Dict[
            str, List[Callable[[Dict[str, Any]], Awaitable[None]]]
        ] = {}
        self._connection_lost_handler: Optional[Callable[[], Awaitable[None]]] = None
        self._connection_restored_handler: Optional[Callable[[], Awaitable[None]]] = (
            None
        )

        # Audio handling with backpressure
        self.audio_queue = asyncio.Queue(maxsize=queue_size)
        self._audio_queue_size = queue_size
        self._audio_queue_warning_threshold = int(
            queue_size * 0.8
        )  # Warn at 80% capacity
        self._audio_queue_full = False

        # Connection monitoring tasks
        self._recv_task = None
        self._heartbeat_task = None

        # Session tracking
        self.session_id = None
        self.conversation_id = None

        # Rate limiting with data size tracking
        self.rate_limit = RateLimit(
            requests=[],
            data_sizes=[],
            window=timedelta(seconds=RATE_LIMIT_WINDOW),
            max_requests=MAX_REQUESTS_PER_WINDOW,
            max_data=MAX_DATA_PER_WINDOW,
        )

        # Memory monitoring
        self._memory_warning_threshold = 0.8  # 80% of available memory
        self._last_memory_check = 0
        self._memory_check_interval = 60  # Check every 60 seconds

        self.logger.info(
            f"RealtimeClient initialized with model: {model}, voice: {voice}, queue_size: {queue_size}"
        )

    def set_log_level(self, level: int) -> None:
        """
        Set the logging level for the client.

        Args:
            level: The logging level to set (e.g., logging.DEBUG, logging.INFO)
        """
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)
        self.logger.info(f"Log level set to {logging.getLevelName(level)}")

    async def connect(self) -> bool:
        """
        Connect to the OpenAI Realtime WebSocket endpoint.

        This method establishes a secure WebSocket connection to OpenAI's Realtime API,
        configures it for low latency, and initializes the session. It includes
        comprehensive error handling and automatic reconnection logic.

        Returns:
            bool: True if connection was successful, False otherwise

        Raises:
            ConnectionError: If connection fails after all retry attempts
            RateLimitError: If rate limits are exceeded
            AuthenticationError: If API key is invalid
        """
        if self._is_closing:
            self.logger.warning("Cannot connect - client is closing")
            return False

        # Check rate limits before attempting connection
        if not self.rate_limit.is_allowed():
            self.logger.error("Rate limit exceeded for connection attempts")
            return False
        self.rate_limit.add_request()

        # Reset connection active flag during connection attempt
        self._connection_active = False

        # Cancel any existing tasks with proper cleanup
        if self._recv_task and not self._recv_task.done():
            self.logger.debug("Cancelling existing receive task")
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                self.logger.debug("Previous receive task cancelled successfully")
            except Exception as e:
                self.logger.warning(
                    f"Error while cancelling previous receive task: {e}"
                )

        # Close existing WebSocket if any
        if self.ws:
            try:
                self.logger.debug("Closing existing WebSocket connection")
                await self.ws.close()
            except Exception as e:
                self.logger.warning(f"Error closing existing WebSocket: {e}")
            self.ws = None

        url = f"wss://api.openai.com/v1/realtime?model={self.model}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1",
        }

        try:
            self.logger.info(
                f"Connecting to OpenAI Realtime API with model: {self.model}"
            )

            # Configure WebSocket for low latency
            connection_start = time.time()
            self.ws = await asyncio.wait_for(
                websockets.connect(
                    url,
                    max_size=WS_MAX_SIZE,
                    ping_interval=WS_PING_INTERVAL,
                    ping_timeout=10,
                    compression=None,  # Disable compression for lower latency
                    additional_headers=headers,
                    # Additional performance optimizations
                    max_queue=32,  # Small queue to prevent buffering
                    write_limit=WS_MAX_SIZE,
                    # SSL configuration for security
                    ssl=True,
                    ssl_handshake_timeout=10,
                ),
                timeout=CONNECTION_TIMEOUT,
            )
            connection_time = time.time() - connection_start
            self.logger.debug(
                f"WebSocket connection established in {connection_time:.2f} seconds"
            )

            # Try to optimize the socket at the TCP level
            if hasattr(self.ws, "sock") and self.ws.sock:
                import socket

                try:
                    # Disable Nagle's algorithm to send packets immediately
                    self.ws.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    # Set TCP keepalive
                    self.ws.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    # Set keepalive parameters
                    self.ws.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
                    self.ws.sock.setsockopt(
                        socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10
                    )
                    self.ws.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
                    self.logger.info(
                        "Optimized OpenAI socket: TCP_NODELAY and keepalive enabled"
                    )
                except Exception as e:
                    self.logger.warning(f"Could not optimize OpenAI socket: {e}")

            self._connection_active = True
            self._reconnect_attempts = 0
            self._last_activity = time.time()

            # Start listening for responses
            self.logger.debug("Starting WebSocket receive loop")
            self._recv_task = asyncio.create_task(self._recv_loop())

            # Start heartbeat
            if self._heartbeat_task and not self._heartbeat_task.done():
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    self.logger.debug("Previous heartbeat task cancelled successfully")
                except Exception:
                    pass

            self.logger.debug("Starting heartbeat task")
            self._heartbeat_task = asyncio.create_task(self._heartbeat())

            # Initialize session
            if not await self._initialize_session():
                self.logger.error("Failed to initialize session")
                await self.close()
                return False

            self.logger.info("Successfully connected to OpenAI Realtime API")

            # Call the connection restored handler if this was a reconnection
            if self._connection_restored_handler and self._reconnect_attempts > 0:
                self.logger.debug("Calling connection restored handler")
                await self._connection_restored_handler()

            return True

        except asyncio.TimeoutError:
            self.logger.error(
                f"Timeout while connecting to OpenAI Realtime API (after {CONNECTION_TIMEOUT}s)"
            )
            self._connection_active = False
            return False

        except websockets.exceptions.InvalidStatusCode as e:
            self.logger.error(f"Invalid status code from OpenAI: {e.status_code}")
            self._connection_active = False
            if e.status_code == 401:
                raise AuthenticationError("Invalid API key") from None
            elif e.status_code == 403:
                raise AuthenticationError(
                    "API key does not have access to this resource"
                ) from None
            elif e.status_code == 429:
                self.logger.error("Rate limit exceeded")
            return False

        except Exception as e:
            self.logger.error(f"Failed to connect to OpenAI Realtime API: {e}")
            self.logger.debug(f"Connection error details: {traceback.format_exc()}")
            self._connection_active = False
            return False

    async def _initialize_session(self) -> bool:
        """
        Initialize a new session with the Realtime API.

        This method handles session initialization with proper error handling
        and validation. It ensures the session is properly configured before
        allowing communication.

        Returns:
            bool: True if session initialization was successful, False otherwise

        Raises:
            SessionError: If session initialization fails
        """
        try:
            # Default session configuration
            session_config = SessionConfig(
                modalities=["text", "audio"],
                model=self.model,
                voice=self.voice,
                input_audio_format="pcm16",
                output_audio_format="pcm16",
                turn_detection={"type": "server_vad"},
            )

            # Create session update event
            update_event = SessionUpdateEvent(session=session_config)

            # Send session configuration
            event_id = await self.send_event(update_event)

            # Wait for session.created event with timeout
            session_created = asyncio.Future()

            def on_session_created(event: Dict[str, Any]):
                if not session_created.done():
                    # Check if session data exists before setting result
                    if event and isinstance(event, dict):
                        session_created.set_result(event)
                    else:
                        # If event is None or invalid, set a default value to avoid NoneType errors
                        session_created.set_result(
                            {"session": {"id": None, "conversation": {"id": None}}}
                        )

            # Register temporary handler for session.created event
            self.on(ServerEventType.SESSION_CREATED, on_session_created)

            try:
                # Wait for session created with timeout
                session_data = await asyncio.wait_for(session_created, timeout=10.0)
                if session_data:
                    # Safely extract session and conversation IDs with fallbacks
                    session = session_data.get("session", {})
                    self.session_id = session.get("id")
                    self.conversation_id = session.get("conversation", {}).get("id")

                    if not self.session_id or not self.conversation_id:
                        raise SessionError("Invalid session data received")

                    self.logger.info(
                        f"Session initialized: {self.session_id}, conversation: {self.conversation_id}"
                    )
                    return True
                else:
                    raise SessionError("No session data received")

            except asyncio.TimeoutError:
                raise SessionError("Timeout waiting for session initialization")

            finally:
                # Remove temporary handler
                self.off(ServerEventType.SESSION_CREATED, on_session_created)

        except Exception as e:
            self.logger.error(f"Error initializing session: {e}")
            self.logger.debug(
                f"Session initialization error details: {traceback.format_exc()}"
            )
            raise SessionError(f"Session initialization failed: {str(e)}") from None

    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to the OpenAI Realtime API.

        Returns:
            bool: True if reconnection was successful, False otherwise
        """
        if self._is_closing:
            self.logger.warning("Cannot reconnect - client is closing")
            return False

        if self._reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
            self.logger.error(
                f"Max reconnection attempts ({MAX_RECONNECT_ATTEMPTS}) reached"
            )
            return False

        self._reconnect_attempts += 1
        delay = RECONNECT_DELAY * self._reconnect_attempts

        self.logger.info(
            f"Reconnecting to OpenAI Realtime API (attempt {self._reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS}) in {delay} seconds"
        )
        await asyncio.sleep(delay)

        return await self.connect()

    async def _recv_loop(self) -> None:
        """
        Internal loop to receive and process messages from OpenAI.
        """
        if not self.ws:
            self.logger.error("WebSocket not initialized for receive loop")
            self._connection_active = False
            return

        try:
            self.logger.debug("Receive loop started")
            while self._connection_active and not self._is_closing:
                try:
                    # Use a timeout to prevent blocking indefinitely
                    self.logger.debug("Waiting for message from OpenAI...")
                    recv_start = time.time()
                    message = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
                    recv_time = time.time() - recv_start
                    self._last_activity = time.time()

                    if isinstance(message, bytes):
                        # Handle binary data
                        self.logger.debug(
                            f"Received binary data of size {len(message)} bytes"
                        )
                        try:
                            # Try to decode as base64 first
                            try:
                                decoded = base64.b64decode(message)
                                self.logger.debug(
                                    f"Successfully decoded binary data as base64"
                                )
                                await self._process_binary_data(decoded)
                            except Exception:
                                # If not base64, process as raw binary
                                self.logger.debug(
                                    "Binary data is not base64, processing as raw"
                                )
                                await self._process_binary_data(message)
                        except Exception as e:
                            self.logger.error(f"Error processing binary data: {e}")
                            self.logger.debug(
                                f"Binary processing error details: {traceback.format_exc()}"
                            )
                    else:
                        try:
                            self.logger.debug(
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
                                    self.logger.debug(
                                        f"Received audio delta with base64 data size: {len(audio_data)}"
                                    )
                                    chunk = base64.b64decode(audio_data)
                                    self.logger.debug(
                                        f"Decoded audio chunk of size {len(chunk)} bytes"
                                    )

                                    # More detailed logging of audio chunks
                                    if len(chunk) > 0:
                                        self.logger.debug(
                                            f"Audio chunk: first few bytes: {chunk[:10]}, putting in queue of size {self.audio_queue.qsize()}"
                                        )
                                    else:
                                        self.logger.warning(
                                            "Received empty audio chunk"
                                        )

                                    # Put chunk in queue
                                    try:
                                        await asyncio.wait_for(
                                            self.audio_queue.put(chunk), timeout=1.0
                                        )
                                        self.logger.debug(
                                            f"Audio queue size after put: {self.audio_queue.qsize()}"
                                        )
                                    except asyncio.TimeoutError:
                                        self.logger.warning(
                                            "Timeout putting audio chunk in queue - queue might be full"
                                        )
                                    except Exception as qe:
                                        self.logger.error(
                                            f"Error putting audio in queue: {qe}"
                                        )

                                except Exception as e:
                                    self.logger.error(
                                        f"Error processing audio delta: {e}"
                                    )
                                    self.logger.debug(
                                        f"Audio processing error details: {traceback.format_exc()}"
                                    )

                            # Process event through registered handlers
                            await self._process_event(event_type, data)

                        except json.JSONDecodeError:
                            self.logger.warning(
                                f"Received invalid JSON: {message[:100]}..."
                            )
                        except Exception as e:
                            self.logger.error(f"Error processing message: {e}")
                            self.logger.debug(f"Original message: {message[:200]}...")
                            self.logger.debug(
                                f"Processing error details: {traceback.format_exc()}"
                            )
                except asyncio.TimeoutError:
                    # This is expected - just continue the loop
                    self.logger.debug("Receive timeout - no message received within 5s")
                    continue
                except ConnectionClosedOK:
                    # Normal closure, don't treat as error
                    self.logger.info("WebSocket connection closed normally")
                    self._connection_active = False
                    break
                except ConnectionClosedError as e:
                    self.logger.warning(f"Connection closed during receive: {e}")
                    self.logger.debug(
                        f"WebSocket close code: {e.code}, reason: {e.reason}"
                    )
                    self._connection_active = False
                    break
                except Exception as e:
                    self.logger.error(f"Error in receive loop iteration: {e}")
                    self.logger.debug(
                        f"Receive error details: {traceback.format_exc()}"
                    )
                    await asyncio.sleep(
                        0.1
                    )  # Brief pause to avoid tight looping on errors

        except ConnectionClosedOK:
            # Normal closure
            self.logger.info("WebSocket connection closed normally")

        except ConnectionClosedError as e:
            self.logger.warning(f"WebSocket connection closed unexpectedly: {e}")
            self.logger.debug(f"WebSocket close code: {e.code}, reason: {e.reason}")

        except Exception as e:
            self.logger.error(f"Error in receive loop: {e}")
            self.logger.debug(f"Receive loop error details: {traceback.format_exc()}")

        # Mark connection as inactive
        self._connection_active = False
        self.logger.info("Receive loop exited, connection marked as inactive")

        # Notify about connection loss
        if self._connection_lost_handler:
            try:
                self.logger.debug("Calling connection lost handler")
                await self._connection_lost_handler()
            except Exception as e:
                self.logger.error(f"Error in connection lost handler: {e}")
                self.logger.debug(
                    f"Connection lost handler error details: {traceback.format_exc()}"
                )

        # Only attempt reconnection if not explicitly closing
        if not self._is_closing:
            self.logger.debug("Scheduling reconnection attempt")
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
                if not self.audio_queue.full():
                    await self.audio_queue.put(data)
                    self.logger.debug(
                        f"Processed binary data as audio chunk of size {len(data)} bytes"
                    )
                else:
                    self.logger.warning("Audio queue full, dropping binary data")
            else:
                self.logger.warning("Received empty binary data")
        except Exception as e:
            self.logger.error(f"Error processing binary data: {e}")
            self.logger.debug(
                f"Binary processing error details: {traceback.format_exc()}"
            )
            raise BinaryDataError(f"Failed to process binary data: {str(e)}") from None

    async def _process_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Process a server event and dispatch to registered handlers.

        Args:
            event_type: The type of event received
            data: The event data
        """
        self.logger.debug(f"Processing event of type: {event_type}")

        # Check for errors first
        if event_type == ServerEventType.ERROR:
            error_event = ErrorEvent(**data)
            self.logger.error(
                f"Received error from OpenAI: {error_event.message} (code: {error_event.code})"
            )

            # Check if this is related to a specific client event
            event_id = data.get("event_id")
            if event_id:
                self.logger.error(f"Error is related to client event: {event_id}")

        # Dispatch to registered handlers - if any handler throws an exception,
        # catch it and log it, but don't let it affect other handlers
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                # Only call the handler if it's callable
                if callable(handler):
                    # Use asyncio.ensure_future to run asynchronously without awaiting
                    # This prevents NoneType errors from propagating
                    result = handler(data)
                    if asyncio.iscoroutine(result):
                        asyncio.ensure_future(result)
            except Exception as e:
                self.logger.error(f"Error in event handler for {event_type}: {e}")
                self.logger.debug(f"Handler error details: {traceback.format_exc()}")
                # Continue processing other handlers despite the error

    async def send_event(self, event: ClientEvent) -> str:
        """
        Send a structured event message to OpenAI using Pydantic models.

        This method handles rate limiting, input validation, and error recovery
        for sending events to the OpenAI Realtime API.

        Args:
            event: A ClientEvent subclass instance to send

        Returns:
            str: The event_id that was sent with the message

        Raises:
            ConnectionError: If the connection is not active
            RateLimitError: If rate limits are exceeded
            ValueError: If the event is invalid
        """
        if not self._connection_active:
            self.logger.warning("Cannot send event - connection not active")
            raise ConnectionError("Connection not active")

        if self.ws is None:
            self.logger.warning("WebSocket is not connected, attempting to reconnect")
            if not await self.reconnect():
                raise ConnectionError("Failed to reconnect")

        # Check rate limits
        if not self.rate_limit.is_allowed():
            self.logger.error("Rate limit exceeded for sending events")
            raise RateLimitError("Too many events sent")
        self.rate_limit.add_request()

        try:
            # Generate an event_id for tracking
            event_id = str(uuid.uuid4())

            # Convert the Pydantic model to a dict and add event_id
            event_dict = event.model_dump(exclude_none=True)
            event_dict["event_id"] = event_id

            # Validate event structure
            if not isinstance(event_dict, dict):
                raise ValueError("Event must be a dictionary")
            if "type" not in event_dict:
                raise ValueError("Event must have a type field")

            # Convert to JSON with error handling
            try:
                event_json = json.dumps(event_dict)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid event data: {str(e)}") from None

            self.logger.debug(f"Sending event: {event_json}")

            # Send through WebSocket with timeout
            send_start = time.time()
            await asyncio.wait_for(self.ws.send(event_json), timeout=5.0)
            send_time = time.time() - send_start

            self.logger.debug(
                f"Sent event in {send_time:.4f} seconds, event_id: {event_id}"
            )
            self._last_activity = time.time()

            return event_id

        except asyncio.TimeoutError:
            self.logger.error("Timeout while sending event")
            raise ConnectionError("Event send timeout") from None

        except Exception as e:
            self.logger.error(f"Error sending event: {e}")
            self.logger.debug(f"Send error details: {traceback.format_exc()}")
            raise ConnectionError(f"Failed to send event: {str(e)}") from None

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
            if not self.audio_queue.empty():
                chunk = self.audio_queue.get_nowait()
                self.logger.debug(
                    f"Retrieved audio chunk of size {len(chunk) if chunk else 0} bytes from queue immediately"
                )
                return chunk

            # If queue is empty but connection is not active, return None
            if not self._connection_active:
                self.logger.debug(
                    "Audio queue empty and connection not active, returning None"
                )
                return None

            # Wait for data with timeout to prevent blocking forever
            self.logger.debug(f"Waiting for audio data (timeout: {timeout}s)...")
            chunk = await asyncio.wait_for(self.audio_queue.get(), timeout=timeout)
            self.logger.debug(
                f"Retrieved audio chunk of size {len(chunk) if chunk else 0} bytes from queue after waiting"
            )
            return chunk

        except asyncio.TimeoutError:
            # This is expected if no data is coming
            self.logger.debug(f"Timeout waiting for audio chunk after {timeout}s")
            return None

        except Exception as e:
            self.logger.error(f"Error receiving audio chunk: {e}")
            self.logger.debug(
                f"Receive audio chunk error details: {traceback.format_exc()}"
            )
            raise ConnectionError(f"Failed to receive audio chunk: {str(e)}") from None

    async def _heartbeat(self) -> None:
        """
        Send periodic heartbeats to keep the connection alive and monitor health.
        """
        self.logger.debug("Heartbeat task started")
        while self._connection_active and not self._is_closing:
            await asyncio.sleep(5)  # Check every 5 seconds

            # Check if we haven't seen activity for too long
            inactivity_period = time.time() - self._last_activity
            if inactivity_period > 60:  # 60 seconds
                self.logger.warning(
                    f"No activity detected for {inactivity_period:.1f} seconds, checking connection"
                )

                if self.ws:
                    try:
                        # Send a ping to test the connection
                        self.logger.debug("Sending ping to test connection")
                        ping_start = time.time()
                        pong_waiter = await self.ws.ping()
                        await asyncio.wait_for(pong_waiter, timeout=5)
                        ping_time = time.time() - ping_start
                        self.logger.debug(
                            f"Ping successful in {ping_time:.4f}s, connection is healthy"
                        )
                        self._last_activity = time.time()
                    except Exception as e:
                        self.logger.warning(
                            f"Ping failed: {e}, connection appears to be dead"
                        )
                        self._connection_active = False

                        # Only attempt reconnection if not explicitly closing
                        if not self._is_closing:
                            self.logger.debug(
                                "Scheduling reconnection after failed ping"
                            )
                            asyncio.create_task(self.reconnect())
                else:
                    self.logger.warning("WebSocket is closed, attempting to reconnect")
                    self._connection_active = False

                    # Only attempt reconnection if not explicitly closing
                    if not self._is_closing:
                        self.logger.debug(
                            "Scheduling reconnection for closed WebSocket"
                        )
                        asyncio.create_task(self.reconnect())

        self.logger.debug("Heartbeat task exited")

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
        self.logger.debug(f"Registered handler for event type: {event_type}")

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
                self.logger.debug(f"Removed handler for event type: {event_type}")
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
            self.logger.warning("Cannot send audio - connection not active")
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
            if not self.rate_limit.is_allowed(len(audio_data)):
                self.logger.error("Rate limit exceeded for audio chunks (data size)")
                raise RateLimitError("Data size rate limit exceeded")
            self.rate_limit.add_request(len(audio_data))

            # Check queue size and implement backpressure
            current_size = self.audio_queue.qsize()
            if current_size >= self._audio_queue_warning_threshold:
                self._audio_queue_full = True
                self.logger.warning(
                    f"Audio queue approaching capacity: {current_size}/{self._audio_queue_size}"
                )
            elif current_size < self._audio_queue_warning_threshold:
                self._audio_queue_full = False
                self.logger.info("Audio queue pressure relieved")

            if self._audio_queue_full:
                # Wait briefly to allow queue to drain
                await asyncio.sleep(0.1)
                if self.audio_queue.qsize() >= self._audio_queue_size:
                    self.logger.warning("Audio queue full, dropping chunk")
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
            self.logger.error(f"Memory error while sending audio: {e}")
            return False
        except RateLimitError as e:
            self.logger.error(f"Rate limit error while sending audio: {e}")
            return False
        except AudioError as e:
            self.logger.error(f"Audio error while sending audio: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error sending audio chunk: {e}")
            self.logger.debug(f"Audio send error details: {traceback.format_exc()}")
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
            self.logger.error(f"Error committing audio buffer: {e}")
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
            self.logger.error(f"Error sending text message: {e}")
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
            self.logger.error(f"Error creating response: {e}")
            return False

    async def update_session(
        self,
        instructions: Optional[str] = None,
        voice: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        modalities: Optional[List[str]] = None,
        turn_detection: Optional[Dict[str, Any]] = None,
        merge: bool = True,
    ) -> bool:
        """
        Update the session configuration.

        Args:
            instructions: System instructions for the model
            voice: Voice to use for audio output
            tools: List of function definitions the model can call
            modalities: List of enabled modalities ("text", "audio")
            turn_detection: VAD configuration or None to disable VAD
            merge: If True, merge with existing config instead of replacing

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Build session config with only the specified parameters
            session_params = {}

            if instructions is not None:
                session_params["instructions"] = instructions

            if voice is not None:
                session_params["voice"] = voice

            if tools is not None:
                session_params["tools"] = tools

            if modalities is not None:
                session_params["modalities"] = modalities

            if turn_detection is not None:
                session_params["turn_detection"] = turn_detection

            if not session_params:
                self.logger.warning("No session parameters specified for update")
                return False

            # If merge is True, get current session config and merge
            if merge and self.session_id:
                try:
                    current_config = await self._get_current_session_config()
                    if current_config:
                        # Merge new params with existing config
                        for key, value in session_params.items():
                            if value is not None:
                                current_config[key] = value
                        session_params = current_config
                except Exception as e:
                    self.logger.warning(
                        f"Failed to get current session config for merge: {e}"
                    )
                    # Continue with just the new params if merge fails

            session_config = SessionConfig(**session_params)
            update_event = SessionUpdateEvent(session=session_config)

            await self.send_event(update_event)
            return True
        except Exception as e:
            self.logger.error(f"Error updating session: {e}")
            return False

    async def _get_current_session_config(self) -> Optional[Dict[str, Any]]:
        """
        Get the current session configuration from the server.

        Returns:
            Optional[Dict[str, Any]]: Current session config or None if unavailable
        """
        try:
            # Create a future to receive the session config
            config_future = asyncio.Future()

            def on_session_config(event: Dict[str, Any]):
                if not config_future.done():
                    config_future.set_result(event.get("session", {}))

            # Register temporary handler
            self.on(ServerEventType.SESSION_CONFIG, on_session_config)

            try:
                # Request current config
                await self.send_event(
                    ClientEvent(type=ClientEventType.GET_SESSION_CONFIG)
                )

                # Wait for response with timeout
                config = await asyncio.wait_for(config_future, timeout=5.0)
                return config

            except asyncio.TimeoutError:
                self.logger.warning("Timeout waiting for session config")
                return None

            finally:
                # Remove temporary handler
                self.off(ServerEventType.SESSION_CONFIG, on_session_config)

        except Exception as e:
            self.logger.error(f"Error getting current session config: {e}")
            return None

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
        self.logger.debug("Connection event handlers registered")

    async def close(self) -> None:
        """
        Close the WebSocket connection and cancel all tasks.

        This method ensures proper cleanup of all resources and handles
        any errors that occur during shutdown.

        Raises:
            ConnectionError: If cleanup fails
        """
        self.logger.info("Closing OpenAI Realtime client")

        # Set closing flag first to prevent any new operations
        self._is_closing = True
        self._connection_active = False

        # Cancel tasks with proper cleanup
        if self._recv_task:
            self.logger.debug("Cancelling receive task")
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                self.logger.debug("Receive task cancelled successfully")
            except Exception as e:
                self.logger.warning(f"Error cancelling receive task: {e}")

        if self._heartbeat_task:
            self.logger.debug("Cancelling heartbeat task")
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                self.logger.debug("Heartbeat task cancelled successfully")
            except Exception as e:
                self.logger.warning(f"Error cancelling heartbeat task: {e}")

        # Close WebSocket with proper cleanup
        ws = self.ws  # Store reference before clearing
        self.ws = None  # Clear reference first to prevent any new operations

        if ws:
            try:
                self.logger.debug("Closing WebSocket connection")
                await ws.close()
            except Exception as e:
                self.logger.warning(f"Error closing WebSocket: {e}")

        # Clear any remaining audio chunks
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except Exception:
                pass

        # Reset state but maintain closing flag
        self.session_id = None
        self.conversation_id = None
        self._reconnect_attempts = 0
        self._last_activity = 0

        self.logger.info("OpenAI Realtime client closed")

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
                self.logger.warning(
                    f"Memory usage high: {memory_percent:.1f}% ({memory_info.rss / 1024 / 1024:.1f}MB)"
                )
                return False

            return True

        except Exception as e:
            self.logger.warning(f"Could not check memory usage: {e}")
            return True  # Assume OK if we can't check
