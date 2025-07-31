import asyncio
import json
import logging
import time
from typing import Optional, Callable, AsyncGenerator, Dict, Any
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK, ConnectionClosedError
from opusagent.utils.websocket_utils import WebSocketUtils
from opusagent.handlers.error_handler import handle_error, ErrorContext, ErrorSeverity

logger = logging.getLogger(__name__)

class WebSocketClient:
    """Enhanced WebSocket client with error handling and reconnection."""
    
    def __init__(self, 
                 max_reconnect_attempts: int = 5,
                 reconnect_delay: float = 2.0,
                 ping_interval: float = 20.0,
                 ping_timeout: float = 10.0,
                 connection_timeout: float = 15.0):
        self.websocket: Optional[Any] = None
        self.connected = False
        self.connecting = False
        self.url: Optional[str] = None
        
        # Reconnection settings
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.reconnect_attempts = 0
        self.auto_reconnect = True
        
        # Connection settings
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.connection_timeout = connection_timeout
        
        # Event handlers
        self.on_message: Optional[Callable] = None
        self.on_connect: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # Background tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._should_stop = False

    async def connect(self, url: str) -> bool:
        """Connect to WebSocket server with retry logic."""
        if self.connecting or self.connected:
            logger.warning("Already connected or connecting")
            return self.connected
            
        self.connecting = True
        self.url = url
        self._should_stop = False
        
        try:
            logger.info(f"Connecting to {url}")
            
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    url,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout,
                    max_size=None,
                    compression=None
                ),
                timeout=self.connection_timeout
            )
            
            self.connected = True
            self.connecting = False
            self.reconnect_attempts = 0
            
            # Start background tasks
            self._start_background_tasks()
            
            logger.info("WebSocket connection established")
            
            if self.on_connect:
                try:
                    await self._safe_call_handler(self.on_connect)
                except Exception as e:
                    logger.error(f"Error in connect handler: {e}")
            
            return True
            
        except asyncio.TimeoutError:
            await handle_error(
                error=TimeoutError("Connection timeout"),
                context=ErrorContext.WEBSOCKET,
                severity=ErrorSeverity.HIGH,
                operation="websocket_connect",
                url=url,
                timeout=self.connection_timeout
            )
            self.connecting = False
            if self.on_error:
                await self._safe_call_handler(self.on_error, TimeoutError("Connection timeout"))
            return False
            
        except Exception as e:
            await handle_error(
                error=e,
                context=ErrorContext.WEBSOCKET,
                severity=ErrorSeverity.HIGH,
                operation="websocket_connect",
                url=url
            )
            self.connecting = False
            if self.on_error:
                await self._safe_call_handler(self.on_error, e)
            return False

    async def disconnect(self) -> None:
        """Gracefully disconnect from WebSocket server."""
        self._should_stop = True
        self.auto_reconnect = False
        
        # Cancel background tasks
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
                
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Close WebSocket connection
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                await handle_error(
                    error=e,
                    context=ErrorContext.WEBSOCKET,
                    severity=ErrorSeverity.MEDIUM,
                    operation="websocket_close"
                )
        
        self.connected = False
        self.connecting = False
        self.websocket = None
        
        logger.info("WebSocket disconnected")
        
        if self.on_disconnect:
            await self._safe_call_handler(self.on_disconnect)

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send a message to the WebSocket server."""
        if not self.websocket:
            logger.error("Cannot send message: Not connected")
            return False
        
        try:
            message_str = json.dumps(message)
            await self.websocket.send(message_str)
            logger.debug(f"Sent message: {message.get('type', 'unknown')}")
            return True
        except Exception as e:
            await handle_error(
                error=e,
                context=ErrorContext.WEBSOCKET,
                severity=ErrorSeverity.HIGH,
                operation="websocket_send",
                message_type=message.get('type', 'unknown')
            )
            return False

    async def _receive_loop(self) -> None:
        """Background task to receive and process messages."""
        logger.info("Receive loop started")
        
        try:
            while self.connected and not self._should_stop:
                try:
                    # Receive message with timeout
                    if not self.websocket:
                        break
                    message_str = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=5.0
                    )
                    
                    try:
                        message = json.loads(message_str)
                        logger.debug(f"Received message: {message.get('type', 'unknown')}")
                        
                        if self.on_message:
                            await self._safe_call_handler(self.on_message, message)
                            
                    except json.JSONDecodeError as e:
                        await handle_error(
                            error=e,
                            context=ErrorContext.WEBSOCKET,
                            severity=ErrorSeverity.MEDIUM,
                            operation="message_parse",
                            message_str=message_str[:100]  # First 100 chars for debugging
                        )
                        
                except asyncio.TimeoutError:
                    # Timeout is expected, continue loop
                    continue
                    
                except ConnectionClosedOK:
                    logger.info("WebSocket connection closed normally")
                    break
                    
                except ConnectionClosedError as e:
                    await handle_error(
                        error=e,
                        context=ErrorContext.WEBSOCKET,
                        severity=ErrorSeverity.MEDIUM,
                        operation="connection_closed"
                    )
                    break
                    
                except Exception as e:
                    await handle_error(
                        error=e,
                        context=ErrorContext.WEBSOCKET,
                        severity=ErrorSeverity.HIGH,
                        operation="receive_loop"
                    )
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            await handle_error(
                error=e,
                context=ErrorContext.WEBSOCKET,
                severity=ErrorSeverity.CRITICAL,
                operation="receive_loop_fatal"
            )
            
        finally:
            self.connected = False
            logger.info("Receive loop exited")
            
            # Attempt reconnection if enabled
            if self.auto_reconnect and not self._should_stop:
                await self._attempt_reconnect()

    async def _heartbeat_loop(self) -> None:
        """Background task to monitor connection health."""
        logger.debug("Heartbeat loop started")
        
        try:
            while self.connected and not self._should_stop:
                await asyncio.sleep(self.ping_interval)
                
                if self.websocket and self.connected:
                    try:
                        await self.websocket.ping()
                        logger.debug("Ping sent")
                    except Exception as e:
                        await handle_error(
                            error=e,
                            context=ErrorContext.WEBSOCKET,
                            severity=ErrorSeverity.MEDIUM,
                            operation="heartbeat_ping"
                        )
                        break
                        
        except Exception as e:
            await handle_error(
                error=e,
                context=ErrorContext.WEBSOCKET,
                severity=ErrorSeverity.HIGH,
                operation="heartbeat_loop"
            )
        finally:
            logger.debug("Heartbeat loop exited")

    async def _attempt_reconnect(self) -> None:
        """Attempt to reconnect to the WebSocket server."""
        if not self.auto_reconnect or self._should_stop:
            return
            
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached")
            return
        
        from opusagent.utils.retry_utils import RetryUtils
        
        # Calculate delay using shared utility
        delay = RetryUtils.calculate_backoff_delay(
            self.reconnect_attempts - 1, 
            self.reconnect_delay, 
            max_delay=60.0
        )
        logger.info(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts} in {delay}s")
        
        await asyncio.sleep(delay)
        
        if not self._should_stop and self.url:
            success = await self.connect(self.url)
            if not success:
                await self._attempt_reconnect()

    def _start_background_tasks(self) -> None:
        """Start background tasks for receiving messages and heartbeat."""
        self._receive_task = asyncio.create_task(self._receive_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _safe_call_handler(self, handler: Callable, *args) -> None:
        """Safely call an event handler, catching exceptions."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(*args)
            else:
                handler(*args)
        except Exception as e:
            logger.error(f"Error in event handler: {e}")

    def is_connected(self) -> bool:
        """Check if the WebSocket is currently connected."""
        return self.connected and self.websocket is not None

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "connected": self.connected,
            "connecting": self.connecting,
            "reconnect_attempts": self.reconnect_attempts,
            "max_reconnect_attempts": self.max_reconnect_attempts,
            "url": self.url,
            "auto_reconnect": self.auto_reconnect
        } 