import asyncio
import json
import base64
import logging
import time
import traceback
import uuid
from typing import Optional, Dict, Any, Callable, Awaitable, List, Union

import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK

from app.config.constants import LOGGER_NAME
from app.models.openai_api import (
    # Session-related
    SessionConfig, 
    # Event types
    ServerEventType, ClientEventType,
    # Base event models
    ServerEvent, ClientEvent,
    # Client events
    SessionUpdateEvent, InputAudioBufferAppendEvent, InputAudioBufferCommitEvent,
    ConversationItemCreateEvent, ResponseCreateEvent,
    # Server events
    ErrorEvent, SessionCreatedEvent, ConversationItemCreatedEvent,
    ResponseTextDeltaEvent, ResponseAudioDeltaEvent, ResponseDoneEvent,
    # Conversation models
    ConversationItemParam, ConversationItemContentParam, ConversationItemType,
    MessageRole, RealtimeFunctionCall
)

logger = logging.getLogger(LOGGER_NAME)

# Connection settings for WebSocket
CONNECTION_TIMEOUT = 30  # seconds
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 2  # seconds
WS_MAX_SIZE = 16 * 1024 * 1024  # 16MB - large enough for audio chunks
WS_PING_INTERVAL = 5  # 5 seconds between pings


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
    """
    def __init__(self, api_key: str, model: str, voice: Optional[str] = "alloy"):
        """
        Initialize the Realtime API client.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (e.g., "gpt-4o-realtime-preview")
            voice: Voice to use for audio output (e.g., "alloy", "echo", "nova")
        """
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
        self._event_handlers: Dict[str, List[Callable[[Dict[str, Any]], Awaitable[None]]]] = {}
        self._connection_lost_handler: Optional[Callable[[], Awaitable[None]]] = None
        self._connection_restored_handler: Optional[Callable[[], Awaitable[None]]] = None
        
        # Audio handling
        self.audio_queue = asyncio.Queue(maxsize=32)  # Buffer for received audio
        
        # Connection monitoring tasks
        self._recv_task = None
        self._heartbeat_task = None
        
        # Session tracking
        self.session_id = None
        self.conversation_id = None
        
        logger.info(f"RealtimeClient initialized with model: {model}, voice: {voice}")

    async def connect(self) -> bool:
        """
        Connect to the OpenAI Realtime WebSocket endpoint.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        if self._is_closing:
            logger.warning("Cannot connect - client is closing")
            return False
            
        # Reset connection active flag during connection attempt
        self._connection_active = False
        
        # Cancel any existing tasks
        if self._recv_task and not self._recv_task.done():
            logger.debug("Cancelling existing receive task")
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                logger.debug("Previous receive task cancelled successfully")
            except Exception as e:
                logger.warning(f"Error while cancelling previous receive task: {e}")
        
        # Close existing WebSocket if any
        if self.ws:
            try:
                logger.debug("Closing existing WebSocket connection")
                await self.ws.close()
            except Exception as e:
                logger.warning(f"Error closing existing WebSocket: {e}")
            self.ws = None
            
        url = f"wss://api.openai.com/v1/realtime?model={self.model}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1",
        }
        
        try:
            logger.info(f"Connecting to OpenAI Realtime API with model: {self.model}")
            
            # Configure WebSocket for low latency
            connection_start = time.time()
            self.ws = await asyncio.wait_for(
                websockets.connect(
                    url, 
                    max_size=WS_MAX_SIZE,
                    ping_interval=WS_PING_INTERVAL,
                    ping_timeout=10,
                    compression=None,  # Disable compression for lower latency
                    additional_headers=headers
                ),
                timeout=CONNECTION_TIMEOUT
            )
            connection_time = time.time() - connection_start
            logger.debug(f"WebSocket connection established in {connection_time:.2f} seconds")
            
            # Try to optimize the socket at the TCP level
            if hasattr(self.ws, "sock") and self.ws.sock:
                import socket
                try:
                    # Disable Nagle's algorithm to send packets immediately
                    self.ws.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    logger.info("Optimized OpenAI socket: TCP_NODELAY enabled for low latency")
                except Exception as e:
                    logger.warning(f"Could not optimize OpenAI socket: {e}")
            
            self._connection_active = True
            self._reconnect_attempts = 0
            self._last_activity = time.time()
            
            # Start listening for responses
            logger.debug("Starting WebSocket receive loop")
            self._recv_task = asyncio.create_task(self._recv_loop())
            
            # Start heartbeat
            if self._heartbeat_task and not self._heartbeat_task.done():
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    logger.debug("Previous heartbeat task cancelled successfully")
                except Exception:
                    pass
            
            logger.debug("Starting heartbeat task")
            self._heartbeat_task = asyncio.create_task(self._heartbeat())
            
            # Initialize session
            if not await self._initialize_session():
                logger.error("Failed to initialize session")
                await self.close()
                return False
                
            logger.info("Successfully connected to OpenAI Realtime API")
            
            # Call the connection restored handler if this was a reconnection
            if self._connection_restored_handler and self._reconnect_attempts > 0:
                logger.debug("Calling connection restored handler")
                await self._connection_restored_handler()
                
            return True
        except asyncio.TimeoutError:
            logger.error(f"Timeout while connecting to OpenAI Realtime API (after {CONNECTION_TIMEOUT}s)")
            self._connection_active = False
            return False
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI Realtime API: {e}")
            logger.debug(f"Connection error details: {traceback.format_exc()}")
            self._connection_active = False
            return False

    async def _initialize_session(self) -> bool:
        """
        Initialize a new session with the Realtime API.
        
        Returns:
            bool: True if session initialization was successful, False otherwise
        """
        try:
            # Default session configuration
            session_config = SessionConfig(
                modalities=["text", "audio"],
                model=self.model,
                voice=self.voice,
                input_audio_format="pcm16",
                output_audio_format="pcm16",
                turn_detection={"type": "server_vad"}
            )
            
            # Create session update event
            update_event = SessionUpdateEvent(session=session_config)
            
            # Send session configuration
            event_id = await self.send_event(update_event)
            
            # Wait for session.created event
            session_created = asyncio.Future()
            
            def on_session_created(event: Dict[str, Any]):
                if not session_created.done():
                    session_created.set_result(event)
            
            # Register temporary handler for session.created event
            self.on(ServerEventType.SESSION_CREATED, on_session_created)
            
            try:
                # Wait for session created with timeout
                session_data = await asyncio.wait_for(session_created, timeout=10.0)
                self.session_id = session_data.get("session", {}).get("id")
                self.conversation_id = session_data.get("session", {}).get("conversation", {}).get("id")
                
                logger.info(f"Session initialized: {self.session_id}, conversation: {self.conversation_id}")
                return True
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for session initialization")
                return False
            finally:
                # Remove temporary handler
                self.off(ServerEventType.SESSION_CREATED, on_session_created)
                
        except Exception as e:
            logger.error(f"Error initializing session: {e}")
            logger.debug(f"Session initialization error details: {traceback.format_exc()}")
            return False
    
    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to the OpenAI Realtime API.
        
        Returns:
            bool: True if reconnection was successful, False otherwise
        """
        if self._is_closing:
            logger.warning("Cannot reconnect - client is closing")
            return False
            
        if self._reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
            logger.error(f"Max reconnection attempts ({MAX_RECONNECT_ATTEMPTS}) reached")
            return False
            
        self._reconnect_attempts += 1
        delay = RECONNECT_DELAY * self._reconnect_attempts
        
        logger.info(f"Reconnecting to OpenAI Realtime API (attempt {self._reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS}) in {delay} seconds")
        await asyncio.sleep(delay)
        
        return await self.connect()

    async def _recv_loop(self) -> None:
        """
        Internal loop to receive and process messages from OpenAI.
        """
        if not self.ws:
            logger.error("WebSocket not initialized for receive loop")
            self._connection_active = False
            return
        
        try:
            logger.debug("Receive loop started")
            while self._connection_active and not self._is_closing:
                try:
                    # Use a timeout to prevent blocking indefinitely
                    logger.debug("Waiting for message from OpenAI...")
                    recv_start = time.time()
                    message = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
                    recv_time = time.time() - recv_start
                    self._last_activity = time.time()
                    
                    if isinstance(message, bytes):
                        # binary data - not expected in the Realtime API via WebSocket
                        logger.warning(f"Received unexpected binary data of size {len(message)} bytes")
                    else:
                        try:
                            logger.debug(f"Received text message in {recv_time:.4f}s: {message[:200]}...")
                            data = json.loads(message)
                            
                            # Extract event type
                            event_type = data.get("type")
                            
                            # Handle audio deltas (special case for audio queue)
                            if event_type == ServerEventType.RESPONSE_AUDIO_DELTA and "audio" in data:
                                try:
                                    chunk = base64.b64decode(data["audio"])
                                    logger.debug(f"Decoded audio chunk of size {len(chunk)} bytes")
                                    await self.audio_queue.put(chunk)
                                except Exception as e:
                                    logger.error(f"Error processing audio delta: {e}")
                            
                            # Process event through registered handlers
                            await self._process_event(event_type, data)
                            
                        except json.JSONDecodeError:
                            logger.warning(f"Received invalid JSON: {message[:100]}...")
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            logger.debug(f"Original message: {message[:200]}...")
                            logger.debug(f"Processing error details: {traceback.format_exc()}")
                except asyncio.TimeoutError:
                    # This is expected - just continue the loop
                    logger.debug("Receive timeout - no message received within 5s")
                    continue
                except ConnectionClosedOK:
                    # Normal closure, don't treat as error
                    logger.info("WebSocket connection closed normally")
                    self._connection_active = False
                    break
                except ConnectionClosedError as e:
                    logger.warning(f"Connection closed during receive: {e}")
                    logger.debug(f"WebSocket close code: {e.code}, reason: {e.reason}")
                    self._connection_active = False
                    break
                except Exception as e:
                    logger.error(f"Error in receive loop iteration: {e}")
                    logger.debug(f"Receive error details: {traceback.format_exc()}")
                    await asyncio.sleep(0.1)  # Brief pause to avoid tight looping on errors
                            
        except ConnectionClosedOK:
            # Normal closure
            logger.info("WebSocket connection closed normally")
            
        except ConnectionClosedError as e:
            logger.warning(f"WebSocket connection closed unexpectedly: {e}")
            logger.debug(f"WebSocket close code: {e.code}, reason: {e.reason}")
            
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
            logger.debug(f"Receive loop error details: {traceback.format_exc()}")
            
        # Mark connection as inactive
        self._connection_active = False
        logger.info("Receive loop exited, connection marked as inactive")
        
        # Notify about connection loss
        if self._connection_lost_handler:
            try:
                logger.debug("Calling connection lost handler")
                await self._connection_lost_handler()
            except Exception as e:
                logger.error(f"Error in connection lost handler: {e}")
                logger.debug(f"Connection lost handler error details: {traceback.format_exc()}")
            
        # Only attempt reconnection if not explicitly closing
        if not self._is_closing:
            logger.debug("Scheduling reconnection attempt")
            asyncio.create_task(self.reconnect())
    
    async def _process_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Process a server event and dispatch to registered handlers.
        
        Args:
            event_type: The type of event received
            data: The event data
        """
        logger.debug(f"Processing event of type: {event_type}")
        
        # Check for errors first
        if event_type == ServerEventType.ERROR:
            error_event = ErrorEvent(**data)
            logger.error(f"Received error from OpenAI: {error_event.message} (code: {error_event.code})")
            
            # Check if this is related to a specific client event
            event_id = data.get("event_id")
            if event_id:
                logger.error(f"Error is related to client event: {event_id}")
        
        # Dispatch to registered handlers
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
                logger.debug(f"Handler error details: {traceback.format_exc()}")

    async def send_event(self, event: ClientEvent) -> str:
        """
        Send a structured event message to OpenAI using Pydantic models.
        
        Args:
            event: A ClientEvent subclass instance to send
            
        Returns:
            str: The event_id that was sent with the message
        """
        if not self._connection_active:
            logger.warning("Cannot send event - connection not active")
            raise ConnectionError("Connection not active")
            
        if self.ws is None:
            logger.warning("WebSocket is not connected, attempting to reconnect")
            if not await self.reconnect():
                raise ConnectionError("Failed to reconnect")
        
        try:
            # Generate an event_id for tracking
            event_id = str(uuid.uuid4())
            
            # Convert the Pydantic model to a dict and add event_id
            event_dict = event.model_dump(exclude_none=True)
            event_dict["event_id"] = event_id
            
            # Convert to JSON
            event_json = json.dumps(event_dict)
            logger.debug(f"Sending event: {event_json}")
            
            # Send through WebSocket
            send_start = time.time()
            await asyncio.wait_for(self.ws.send(event_json), timeout=5.0)
            send_time = time.time() - send_start
            
            logger.debug(f"Sent event in {send_time:.4f} seconds, event_id: {event_id}")
            self._last_activity = time.time()
            
            return event_id
        except Exception as e:
            logger.error(f"Error sending event: {e}")
            logger.debug(f"Send error details: {traceback.format_exc()}")
            raise

    async def receive_audio_chunk(self) -> Optional[bytes]:
        """
        Await and return the next audio chunk from OpenAI.
        
        Returns:
            bytes: Audio chunk data or None if an error occurred or timeout
        """
        try:
            # Use get_nowait when available to avoid waiting for chunks that might never come
            if not self.audio_queue.empty():
                chunk = self.audio_queue.get_nowait()
                logger.debug(f"Retrieved audio chunk of size {len(chunk) if chunk else 0} bytes from queue immediately")
                return chunk
            
            # If queue is empty but connection is not active, return None
            if not self._connection_active:
                logger.debug("Audio queue empty and connection not active, returning None")
                return None
            
            # Wait for data with timeout to prevent blocking forever
            logger.debug("Waiting for audio data...")
            chunk = await asyncio.wait_for(self.audio_queue.get(), timeout=2.0)
            logger.debug(f"Retrieved audio chunk of size {len(chunk) if chunk else 0} bytes from queue after waiting")
            return chunk
        except asyncio.TimeoutError:
            # This is expected if no data is coming
            logger.debug("Timeout waiting for audio chunk")
            return None
        except Exception as e:
            logger.error(f"Error receiving audio chunk: {e}")
            logger.debug(f"Receive audio chunk error details: {traceback.format_exc()}")
            return None

    async def _heartbeat(self) -> None:
        """
        Send periodic heartbeats to keep the connection alive and monitor health.
        """
        logger.debug("Heartbeat task started")
        while self._connection_active and not self._is_closing:
            await asyncio.sleep(5)  # Check every 5 seconds
            
            # Check if we haven't seen activity for too long
            inactivity_period = time.time() - self._last_activity
            if inactivity_period > 60:  # 60 seconds
                logger.warning(f"No activity detected for {inactivity_period:.1f} seconds, checking connection")
                
                if self.ws:
                    try:
                        # Send a ping to test the connection
                        logger.debug("Sending ping to test connection")
                        ping_start = time.time()
                        pong_waiter = await self.ws.ping()
                        await asyncio.wait_for(pong_waiter, timeout=5)
                        ping_time = time.time() - ping_start
                        logger.debug(f"Ping successful in {ping_time:.4f}s, connection is healthy")
                        self._last_activity = time.time()
                    except Exception as e:
                        logger.warning(f"Ping failed: {e}, connection appears to be dead")
                        self._connection_active = False
                        
                        # Only attempt reconnection if not explicitly closing
                        if not self._is_closing:
                            logger.debug("Scheduling reconnection after failed ping")
                            asyncio.create_task(self.reconnect())
                else:
                    logger.warning("WebSocket is closed, attempting to reconnect")
                    self._connection_active = False
                    
                    # Only attempt reconnection if not explicitly closing 
                    if not self._is_closing:
                        logger.debug("Scheduling reconnection for closed WebSocket")
                        asyncio.create_task(self.reconnect())
        
        logger.debug("Heartbeat task exited")

    def on(self, event_type: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """
        Register an event handler for a specific event type.
        
        Args:
            event_type: The type of event to listen for
            handler: Async function to call when event is received
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        
        self._event_handlers[event_type].append(handler)
        logger.debug(f"Registered handler for event type: {event_type}")
    
    def off(self, event_type: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """
        Remove an event handler for a specific event type.
        
        Args:
            event_type: The type of event to stop listening for
            handler: The handler to remove
        """
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
                logger.debug(f"Removed handler for event type: {event_type}")
            except ValueError:
                # Handler wasn't registered
                pass

    async def send_audio_chunk(self, audio_data: bytes) -> bool:
        """
        Send raw audio data to OpenAI.
        
        This method converts the audio to base64 and sends it as an
        input_audio_buffer.append event.
        
        Args:
            audio_data: Raw PCM16 audio bytes to send
            
        Returns:
            bool: True if the chunk was sent successfully, False otherwise
        """
        try:
            # Convert binary audio to base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Create and send event
            audio_event = InputAudioBufferAppendEvent(audio=audio_base64)
            await self.send_event(audio_event)
            return True
        except Exception as e:
            logger.error(f"Error sending audio chunk: {e}")
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
            logger.error(f"Error committing audio buffer: {e}")
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
            item = ConversationItemParam(
                type="message",
                role=role,
                content=content
            )
            
            # Create and send event
            event = ConversationItemCreateEvent(item=item)
            await self.send_event(event)
            return True
        except Exception as e:
            logger.error(f"Error sending text message: {e}")
            return False

    async def create_response(self, 
                             modalities: Optional[List[str]] = None,
                             instructions: Optional[str] = None) -> bool:
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
            logger.error(f"Error creating response: {e}")
            return False

    async def update_session(self, 
                           instructions: Optional[str] = None,
                           voice: Optional[str] = None,
                           tools: Optional[List[Dict[str, Any]]] = None,
                           modalities: Optional[List[str]] = None,
                           turn_detection: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update the session configuration.
        
        Args:
            instructions: System instructions for the model
            voice: Voice to use for audio output
            tools: List of function definitions the model can call
            modalities: List of enabled modalities ("text", "audio")
            turn_detection: VAD configuration or None to disable VAD
            
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
                logger.warning("No session parameters specified for update")
                return False
                
            session_config = SessionConfig(**session_params)
            update_event = SessionUpdateEvent(session=session_config)
            
            await self.send_event(update_event)
            return True
        except Exception as e:
            logger.error(f"Error updating session: {e}")
            return False

    def set_connection_handlers(self, 
                               lost_handler: Optional[Callable[[], Awaitable[None]]] = None,
                               restored_handler: Optional[Callable[[], Awaitable[None]]] = None) -> None:
        """
        Set handlers for connection loss and restoration events.
        
        Args:
            lost_handler: Async function to call when connection is lost
            restored_handler: Async function to call when connection is restored
        """
        self._connection_lost_handler = lost_handler
        self._connection_restored_handler = restored_handler
        logger.debug("Connection event handlers registered")

    async def close(self) -> None:
        """
        Close the WebSocket connection and cancel all tasks.
        """
        logger.info("Closing OpenAI Realtime client")
        self._is_closing = True
        self._connection_active = False
        
        # Cancel tasks
        if self._recv_task:
            logger.debug("Cancelling receive task")
            self._recv_task.cancel()
            
        if self._heartbeat_task:
            logger.debug("Cancelling heartbeat task")
            self._heartbeat_task.cancel()
        
        # Close WebSocket
        if self.ws:
            logger.debug("Closing WebSocket connection")
            await self.ws.close()
            
        logger.info("OpenAI Realtime client closed") 