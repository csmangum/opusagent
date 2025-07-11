"""
Reliable message sending with acknowledgment and retry logic.

This module provides reliable message delivery with acknowledgment tracking,
retry mechanisms, and delivery guarantees for WebSocket communications.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


class ReliableMessageSender:
    """Handles reliable message delivery with acknowledgment and retry logic."""
    
    def __init__(
        self,
        max_retries: int = 3,
        ack_timeout: float = 5.0,
        retry_delay: float = 0.1,
        enable_acks: bool = True
    ):
        """
        Initialize reliable message sender.
        
        Args:
            max_retries: Maximum retry attempts per message
            ack_timeout: Timeout for acknowledgment in seconds
            retry_delay: Base delay between retries in seconds
            enable_acks: Whether to use acknowledgment system
        """
        self.max_retries = max_retries
        self.ack_timeout = ack_timeout
        self.retry_delay = retry_delay
        self.enable_acks = enable_acks
        
        # Message tracking
        self.pending_messages = {}
        self.message_counter = 0
        
        # Statistics
        self.total_messages_sent = 0
        self.successful_deliveries = 0
        self.failed_deliveries = 0
        self.ack_timeouts = 0
        self.retry_attempts = 0
        
        # Callbacks
        self.on_delivery_success = None
        self.on_delivery_failure = None
        self.on_ack_timeout = None
        
        logger.info("Reliable message sender initialized")
    
    async def send_with_ack(
        self, 
        websocket, 
        message: Dict[str, Any],
        message_type: str = "message"
    ) -> bool:
        """
        Send message with acknowledgment and retry logic.
        
        Args:
            websocket: WebSocket connection
            message: Message to send
            message_type: Type of message for logging
            
        Returns:
            True if message delivered successfully, False otherwise
        """
        if not self.enable_acks:
            # Simple send without acknowledgment
            return await self._simple_send(websocket, message)
        
        # Generate unique message ID
        message_id = str(uuid.uuid4())
        message['id'] = message_id
        message['timestamp'] = time.time()
        
        # Track pending message
        self.pending_messages[message_id] = {
            'message': message,
            'type': message_type,
            'sent_time': time.time(),
            'retry_count': 0,
            'status': 'pending'
        }
        
        self.total_messages_sent += 1
        
        # Attempt delivery with retries
        for attempt in range(self.max_retries):
            try:
                # Send message
                await websocket.send(json.dumps(message))
                logger.debug(f"Sent message {message_id} (attempt {attempt + 1})")
                
                # Wait for acknowledgment
                ack_received = await self._wait_for_ack(websocket, message_id)
                
                if ack_received:
                    # Message delivered successfully
                    self._mark_message_delivered(message_id)
                    self.successful_deliveries += 1
                    
                    if self.on_delivery_success:
                        try:
                            await self.on_delivery_success(message_id, message)
                        except Exception as e:
                            logger.error(f"Error in delivery success callback: {e}")
                    
                    logger.debug(f"Message {message_id} delivered successfully")
                    return True
                else:
                    # Acknowledgment timeout
                    self.ack_timeouts += 1
                    self.retry_attempts += 1
                    
                    if self.on_ack_timeout:
                        try:
                            await self.on_ack_timeout(message_id, message, attempt + 1)
                        except Exception as e:
                            logger.error(f"Error in ack timeout callback: {e}")
                    
                    logger.warning(f"Ack timeout for message {message_id}, attempt {attempt + 1}")
                    
            except Exception as e:
                self.retry_attempts += 1
                logger.error(f"Error sending message {message_id}, attempt {attempt + 1}: {e}")
                
                if attempt < self.max_retries - 1:
                    # Wait before retry
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        # All retries failed
        self._mark_message_failed(message_id)
        self.failed_deliveries += 1
        
        if self.on_delivery_failure:
            try:
                await self.on_delivery_failure(message_id, message)
            except Exception as e:
                logger.error(f"Error in delivery failure callback: {e}")
        
        logger.error(f"Failed to deliver message {message_id} after {self.max_retries} attempts")
        return False
    
    async def _simple_send(self, websocket, message: Dict[str, Any]) -> bool:
        """Simple send without acknowledgment."""
        try:
            await websocket.send(json.dumps(message))
            self.total_messages_sent += 1
            self.successful_deliveries += 1
            return True
        except Exception as e:
            logger.error(f"Simple send failed: {e}")
            self.total_messages_sent += 1
            self.failed_deliveries += 1
            return False
    
    async def _wait_for_ack(self, websocket, message_id: str) -> bool:
        """
        Wait for acknowledgment for a specific message.
        
        Args:
            websocket: WebSocket connection
            message_id: Message ID to wait for
            
        Returns:
            True if acknowledgment received, False if timeout
        """
        try:
            # Wait for acknowledgment with timeout
            ack = await asyncio.wait_for(
                websocket.recv(),
                timeout=self.ack_timeout
            )
            
            # Parse acknowledgment
            ack_data = json.loads(ack)
            
            # Check if this is the acknowledgment we're waiting for
            if (ack_data.get('type') == 'ack' and 
                ack_data.get('id') == message_id):
                return True
            
            # Not the acknowledgment we're waiting for
            logger.debug(f"Received ack for different message: {ack_data.get('id')}")
            return False
            
        except asyncio.TimeoutError:
            return False
        except Exception as e:
            logger.error(f"Error waiting for ack: {e}")
            return False
    
    def _mark_message_delivered(self, message_id: str) -> None:
        """Mark message as successfully delivered."""
        if message_id in self.pending_messages:
            self.pending_messages[message_id]['status'] = 'delivered'
            self.pending_messages[message_id]['delivered_time'] = time.time()
    
    def _mark_message_failed(self, message_id: str) -> None:
        """Mark message as failed."""
        if message_id in self.pending_messages:
            self.pending_messages[message_id]['status'] = 'failed'
            self.pending_messages[message_id]['failed_time'] = time.time()
    
    def get_pending_messages(self) -> Dict[str, Any]:
        """Get all pending messages."""
        return self.pending_messages.copy()
    
    def clear_pending_messages(self) -> None:
        """Clear all pending messages."""
        self.pending_messages.clear()
        logger.info("Cleared all pending messages")
    
    def get_delivery_statistics(self) -> Dict[str, Any]:
        """
        Get delivery statistics.
        
        Returns:
            Dictionary with delivery statistics
        """
        if self.total_messages_sent == 0:
            return {
                'total_messages': 0,
                'success_rate': 0.0,
                'failure_rate': 0.0,
                'ack_timeout_rate': 0.0,
                'average_retries': 0.0,
                'pending_messages': len(self.pending_messages)
            }
        
        return {
            'total_messages': self.total_messages_sent,
            'successful_deliveries': self.successful_deliveries,
            'failed_deliveries': self.failed_deliveries,
            'ack_timeouts': self.ack_timeouts,
            'retry_attempts': self.retry_attempts,
            'success_rate': self.successful_deliveries / self.total_messages_sent,
            'failure_rate': self.failed_deliveries / self.total_messages_sent,
            'ack_timeout_rate': self.ack_timeouts / self.total_messages_sent,
            'average_retries': self.retry_attempts / self.total_messages_sent,
            'pending_messages': len(self.pending_messages),
            'enable_acks': self.enable_acks
        }
    
    def set_callbacks(
        self,
        on_delivery_success: Optional[Callable] = None,
        on_delivery_failure: Optional[Callable] = None,
        on_ack_timeout: Optional[Callable] = None
    ) -> None:
        """
        Set callback functions for delivery events.
        
        Args:
            on_delivery_success: Called when message is delivered successfully
            on_delivery_failure: Called when message delivery fails
            on_ack_timeout: Called when acknowledgment times out
        """
        self.on_delivery_success = on_delivery_success
        self.on_delivery_failure = on_delivery_failure
        self.on_ack_timeout = on_ack_timeout
    
    def reset_statistics(self) -> None:
        """Reset all statistics."""
        self.total_messages_sent = 0
        self.successful_deliveries = 0
        self.failed_deliveries = 0
        self.ack_timeouts = 0
        self.retry_attempts = 0
        self.pending_messages.clear()
        
        logger.info("Message delivery statistics reset") 