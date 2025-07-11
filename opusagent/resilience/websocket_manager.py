"""
Resilient WebSocket connection management.

This module provides robust WebSocket connection handling with retry logic,
exponential backoff, and connection health monitoring.
"""

import asyncio
import logging
import time
from typing import Optional, Callable, Dict, Any

import websockets

logger = logging.getLogger(__name__)


class ResilientWebSocketManager:
    """Manages WebSocket connections with resilience and retry logic."""
    
    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        timeout: float = 30.0,
        health_check_interval: float = 30.0,
        name: str = "websocket"
    ):
        """
        Initialize resilient WebSocket manager.
        
        Args:
            max_retries: Maximum connection attempts
            backoff_factor: Exponential backoff multiplier
            timeout: Connection timeout in seconds
            health_check_interval: Health check interval in seconds
            name: Name for logging and monitoring
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self.health_check_interval = health_check_interval
        self.name = name
        
        # Connection state
        self.websocket = None
        self.connected = False
        self.connection_attempts = 0
        self.last_failure_time = None
        self.last_success_time = None
        
        # Health monitoring
        self.last_health_check = None
        self.health_check_task = None
        
        # Statistics
        self.total_connections = 0
        self.successful_connections = 0
        self.failed_connections = 0
        self.connection_duration = 0.0
        
        # Callbacks
        self.on_connect_callback = None
        self.on_disconnect_callback = None
        self.on_error_callback = None
        
        logger.info(f"Resilient WebSocket manager '{name}' initialized")
    
    async def connect_with_retry(self, uri: str):
        """
        Connect to WebSocket with retry logic and exponential backoff.
        
        Args:
            uri: WebSocket URI to connect to
            
        Returns:
            WebSocket connection
            
        Raises:
            ConnectionError: If connection fails after all retries
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"{self.name}: Connection attempt {attempt + 1}/{self.max_retries} to {uri}")
                
                # Attempt connection with timeout
                websocket = await asyncio.wait_for(
                    websockets.connect(uri),
                    timeout=self.timeout
                )
                
                # Connection successful
                self.websocket = websocket
                self.connected = True
                self.connection_attempts = 0
                self.last_failure_time = None
                self.last_success_time = time.time()
                self.total_connections += 1
                self.successful_connections += 1
                
                # Start health monitoring
                self._start_health_monitoring()
                
                # Call connection callback
                if self.on_connect_callback:
                    try:
                        await self.on_connect_callback(websocket)
                    except Exception as e:
                        logger.error(f"Error in connect callback: {e}")
                
                logger.info(f"{self.name}: Successfully connected to {uri}")
                return websocket
                
            except Exception as e:
                self.connection_attempts += 1
                self.failed_connections += 1
                self.last_failure_time = time.time()
                
                logger.warning(f"{self.name}: Connection attempt {attempt + 1} failed: {e}")
                
                # Call error callback
                if self.on_error_callback:
                    try:
                        await self.on_error_callback(e, attempt + 1)
                    except Exception as callback_error:
                        logger.error(f"Error in error callback: {callback_error}")
                
                if attempt < self.max_retries - 1:
                    # Calculate backoff delay
                    wait_time = self.backoff_factor ** attempt
                    logger.info(f"{self.name}: Retrying in {wait_time:.1f} seconds")
                    await asyncio.sleep(wait_time)
        
        # All retries failed
        error_msg = f"Failed to connect to {uri} after {self.max_retries} attempts"
        logger.error(f"{self.name}: {error_msg}")
        raise ConnectionError(error_msg)
    
    async def disconnect(self) -> None:
        """Disconnect WebSocket connection."""
        if self.websocket and self.connected:
            try:
                await self.websocket.close()
                logger.info(f"{self.name}: WebSocket disconnected")
            except Exception as e:
                logger.warning(f"{self.name}: Error during disconnect: {e}")
            finally:
                self.connected = False
                self.websocket = None
                self._stop_health_monitoring()
                
                # Call disconnect callback
                if self.on_disconnect_callback:
                    try:
                        await self.on_disconnect_callback()
                    except Exception as e:
                        logger.error(f"Error in disconnect callback: {e}")
    
    async def send_message(self, message: str) -> bool:
        """
        Send message with error handling.
        
        Args:
            message: Message to send
            
        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.connected or not self.websocket:
            logger.warning(f"{self.name}: Cannot send message - not connected")
            return False
        
        try:
            await self.websocket.send(message)
            return True
        except Exception as e:
            logger.error(f"{self.name}: Error sending message: {e}")
            await self._handle_connection_error(e)
            return False
    
    async def receive_message(self) -> Optional[str]:
        """
        Receive message with error handling.
        
        Args:
            Message received, or None if error
            
        Returns:
            Received message or None
        """
        if not self.connected or not self.websocket:
            logger.warning(f"{self.name}: Cannot receive message - not connected")
            return None
        
        try:
            message = await self.websocket.recv()
            return message
        except Exception as e:
            logger.error(f"{self.name}: Error receiving message: {e}")
            await self._handle_connection_error(e)
            return None
    
    async def _handle_connection_error(self, error: Exception) -> None:
        """Handle connection errors and attempt recovery."""
        logger.warning(f"{self.name}: Connection error detected: {error}")
        
        # Mark as disconnected
        self.connected = False
        self.websocket = None
        self._stop_health_monitoring()
        
        # Call error callback
        if self.on_error_callback:
            try:
                await self.on_error_callback(error, 0)
            except Exception as callback_error:
                logger.error(f"Error in error callback: {callback_error}")
    
    def _start_health_monitoring(self) -> None:
        """Start health monitoring task."""
        if self.health_check_task is None:
            self.health_check_task = asyncio.create_task(self._health_monitor_loop())
            logger.debug(f"{self.name}: Health monitoring started")
    
    def _stop_health_monitoring(self) -> None:
        """Stop health monitoring task."""
        if self.health_check_task:
            self.health_check_task.cancel()
            self.health_check_task = None
            logger.debug(f"{self.name}: Health monitoring stopped")
    
    async def _health_monitor_loop(self) -> None:
        """Health monitoring loop."""
        while self.connected and self.websocket:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                if self.connected and self.websocket:
                    # Send ping to check connection health
                    pong_waiter = await self.websocket.ping()
                    await asyncio.wait_for(pong_waiter, timeout=5.0)
                    self.last_health_check = time.time()
                    logger.debug(f"{self.name}: Health check passed")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"{self.name}: Health check failed: {e}")
                await self._handle_connection_error(e)
                break
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self.connected and self.websocket is not None
    
    def get_connection_statistics(self) -> Dict[str, Any]:
        """
        Get connection statistics.
        
        Returns:
            Dictionary with connection statistics
        """
        return {
            'name': self.name,
            'connected': self.connected,
            'total_connections': self.total_connections,
            'successful_connections': self.successful_connections,
            'failed_connections': self.failed_connections,
            'success_rate': self.successful_connections / self.total_connections if self.total_connections > 0 else 0.0,
            'last_success_time': self.last_success_time,
            'last_failure_time': self.last_failure_time,
            'connection_attempts': self.connection_attempts,
            'last_health_check': self.last_health_check
        }
    
    def set_callbacks(
        self,
        on_connect: Optional[Callable] = None,
        on_disconnect: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ) -> None:
        """
        Set callback functions for connection events.
        
        Args:
            on_connect: Called when connection is established
            on_disconnect: Called when connection is lost
            on_error: Called when connection error occurs
        """
        self.on_connect_callback = on_connect
        self.on_disconnect_callback = on_disconnect
        self.on_error_callback = on_error
    
    async def reconnect(self, uri: str) -> bool:
        """
        Attempt to reconnect to WebSocket.
        
        Args:
            uri: WebSocket URI to connect to
            
        Returns:
            True if reconnection successful, False otherwise
        """
        logger.info(f"{self.name}: Attempting reconnection to {uri}")
        
        try:
            await self.disconnect()
            await self.connect_with_retry(uri)
            return True
        except Exception as e:
            logger.error(f"{self.name}: Reconnection failed: {e}")
            return False 