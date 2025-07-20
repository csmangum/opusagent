"""Redis-based session storage implementation.

This module provides a Redis implementation of session storage for production use.
It includes connection pooling, error handling, and automatic cleanup of expired sessions.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List

import redis.asyncio as redis
from . import SessionStorage
from opusagent.config.logging_config import configure_logging

logger = configure_logging("redis_session_storage")


class RedisSessionStorage(SessionStorage):
    """Redis-based session storage implementation.
    
    This implementation stores session data in Redis with automatic expiration
    and cleanup. It's suitable for production environments with high availability
    and scalability requirements.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        session_prefix: str = "session:",
        default_ttl: int = 3600,  # 1 hour default TTL
        max_connections: int = 10,
        **kwargs
    ):
        """Initialize Redis session storage.
        
        Args:
            redis_url: Redis connection URL
            session_prefix: Prefix for session keys in Redis
            default_ttl: Default TTL in seconds for sessions
            max_connections: Maximum number of Redis connections
            **kwargs: Additional Redis connection parameters
        """
        self.redis_url = redis_url
        self.session_prefix = session_prefix
        self.default_ttl = default_ttl
        self.max_connections = max_connections
        self.redis_kwargs = kwargs
        
        # Initialize Redis connection pool
        self.redis_pool: Optional[redis.ConnectionPool] = None
        self.redis_client: Optional[redis.Redis] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._initialized = False
        
        logger.info(f"Redis session storage initialized with URL: {redis_url}")
    
    async def _ensure_connection(self) -> bool:
        """Ensure Redis connection is established.
        
        Returns:
            True if connection is available, False otherwise
        """
        if self._initialized and self.redis_client:
            try:
                # Test connection
                await self.redis_client.ping()
                return True
            except Exception as e:
                logger.warning(f"Redis connection test failed: {e}")
                self._initialized = False
        
        try:
            # Create connection pool if not exists
            if not self.redis_pool:
                self.redis_pool = redis.ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=self.max_connections,
                    **self.redis_kwargs
                )
            
            # Create Redis client
            self.redis_client = redis.Redis(connection_pool=self.redis_pool)
            
            # Test connection
            await self.redis_client.ping()
            self._initialized = True
            
            logger.info("Redis connection established successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to establish Redis connection: {e}")
            self._initialized = False
            return False
    
    def _get_session_key(self, conversation_id: str) -> str:
        """Get Redis key for session data.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            Redis key for the session
        """
        return f"{self.session_prefix}{conversation_id}"
    
    def _get_session_meta_key(self, conversation_id: str) -> str:
        """Get Redis key for session metadata.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            Redis key for session metadata
        """
        return f"{self.session_prefix}{conversation_id}:meta"
    
    async def store_session(self, conversation_id: str, session_data: Dict[str, Any]) -> bool:
        """Store session state in Redis.
        
        Args:
            conversation_id: Unique identifier for the conversation
            session_data: Session state data to store
            
        Returns:
            True if storage was successful, False otherwise
        """
        if not await self._ensure_connection():
            return False
        
        try:
            if not self.redis_client:
                return False
                
            session_key = self._get_session_key(conversation_id)
            meta_key = self._get_session_meta_key(conversation_id)
            
            # Store session data
            await self.redis_client.set(
                session_key,
                json.dumps(session_data),
                ex=self.default_ttl
            )
            
            # Store metadata for tracking
            metadata = {
                "conversation_id": conversation_id,
                "created_at": time.time(),
                "last_activity": time.time(),
                "ttl": self.default_ttl
            }
            await self.redis_client.set(
                meta_key,
                json.dumps(metadata),
                ex=self.default_ttl
            )
            
            logger.debug(f"Stored session in Redis: {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing session in Redis: {e}")
            return False
    
    async def retrieve_session(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session state from Redis.
        
        Args:
            conversation_id: Unique identifier for the conversation
            
        Returns:
            Session state data if found, None otherwise
        """
        if not await self._ensure_connection():
            return None
        
        try:
            if not self.redis_client:
                return None
                
            session_key = self._get_session_key(conversation_id)
            
            # Retrieve session data
            session_data = await self.redis_client.get(session_key)
            if not session_data:
                return None
            
            # Parse JSON data
            session_dict = json.loads(session_data)
            
            # Update last activity
            await self.update_session_activity(conversation_id)
            
            logger.debug(f"Retrieved session from Redis: {conversation_id}")
            return session_dict
            
        except Exception as e:
            logger.error(f"Error retrieving session from Redis: {e}")
            return None
    
    async def delete_session(self, conversation_id: str) -> bool:
        """Delete session state from Redis.
        
        Args:
            conversation_id: Unique identifier for the conversation
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not await self._ensure_connection():
            return False
        
        try:
            if not self.redis_client:
                return False
                
            session_key = self._get_session_key(conversation_id)
            meta_key = self._get_session_meta_key(conversation_id)
            
            # Delete both session data and metadata
            await self.redis_client.delete(session_key, meta_key)
            
            logger.debug(f"Deleted session from Redis: {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting session from Redis: {e}")
            return False
    
    async def list_active_sessions(self) -> List[str]:
        """List all active session IDs from Redis.
        
        Returns:
            List of conversation IDs for active sessions
        """
        if not await self._ensure_connection():
            return []
        
        try:
            if not self.redis_client:
                return []
                
            # Get all session keys with the prefix
            pattern = f"{self.session_prefix}*"
            keys = await self.redis_client.keys(pattern)
            
            # Extract conversation IDs from keys
            conversation_ids = []
            for key in keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                if not key_str.endswith(':meta'):  # Skip metadata keys
                    conversation_id = key_str[len(self.session_prefix):]
                    conversation_ids.append(conversation_id)
            
            logger.debug(f"Found {len(conversation_ids)} active sessions in Redis")
            return conversation_ids
            
        except Exception as e:
            logger.error(f"Error listing active sessions from Redis: {e}")
            return []
    
    async def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> int:
        """Clean up expired sessions from Redis.
        
        Args:
            max_age_seconds: Maximum age in seconds before session is considered expired
            
        Returns:
            Number of sessions cleaned up
        """
        if not await self._ensure_connection():
            return 0
        
        try:
            if not self.redis_client:
                return 0
                
            # Get all session metadata
            pattern = f"{self.session_prefix}*:meta"
            meta_keys = await self.redis_client.keys(pattern)
            
            current_time = time.time()
            cleaned_count = 0
            
            for meta_key in meta_keys:
                try:
                    # Get metadata
                    meta_data = await self.redis_client.get(meta_key)
                    if not meta_data:
                        continue
                    
                    metadata = json.loads(meta_data)
                    last_activity = metadata.get("last_activity", 0)
                    
                    # Check if session is expired
                    if current_time - last_activity > max_age_seconds:
                        conversation_id = metadata.get("conversation_id")
                        if conversation_id:
                            # Delete session
                            await self.delete_session(conversation_id)
                            cleaned_count += 1
                            
                except Exception as e:
                    logger.warning(f"Error processing session metadata: {e}")
                    continue
            
            logger.info(f"Cleaned up {cleaned_count} expired sessions from Redis")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions from Redis: {e}")
            return 0
    
    async def update_session_activity(self, conversation_id: str) -> bool:
        """Update session last activity timestamp in Redis.
        
        Args:
            conversation_id: Unique identifier for the conversation
            
        Returns:
            True if update was successful, False otherwise
        """
        if not await self._ensure_connection():
            return False
        
        try:
            if not self.redis_client:
                return False
                
            meta_key = self._get_session_meta_key(conversation_id)
            
            # Get existing metadata
            meta_data = await self.redis_client.get(meta_key)
            if meta_data:
                metadata = json.loads(meta_data)
                metadata["last_activity"] = time.time()
                
                # Update metadata with new TTL
                await self.redis_client.set(
                    meta_key,
                    json.dumps(metadata),
                    ex=self.default_ttl
                )
                
                # Also extend TTL for session data
                session_key = self._get_session_key(conversation_id)
                await self.redis_client.expire(session_key, self.default_ttl)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating session activity in Redis: {e}")
            return False
    
    async def start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            return
        
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Started Redis session cleanup task")
    
    async def stop_cleanup_task(self):
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped Redis session cleanup task")
    
    async def _cleanup_loop(self):
        """Background cleanup loop."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self.cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def close(self):
        """Close Redis connections."""
        await self.stop_cleanup_task()
        
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
        
        if self.redis_pool:
            await self.redis_pool.disconnect()
            self.redis_pool = None
        
        self._initialized = False
        logger.info("Redis session storage connections closed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Redis storage statistics.
        
        Returns:
            Dictionary containing storage statistics
        """
        return {
            "storage_type": "redis",
            "redis_url": self.redis_url,
            "session_prefix": self.session_prefix,
            "default_ttl": self.default_ttl,
            "max_connections": self.max_connections,
            "initialized": self._initialized,
            "cleanup_task_running": self._cleanup_task is not None and not self._cleanup_task.done()
        } 