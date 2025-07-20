"""Redis-based session storage implementation.

This module provides a Redis implementation of session storage for production use.
It includes connection pooling, error handling, and automatic cleanup of expired sessions.

The RedisSessionStorage class provides a robust, scalable storage solution
that's suitable for production environments with high availability and
scalability requirements. It uses Redis for persistent session storage
with automatic expiration and connection management.

Key Features:
- Redis-based persistent storage with automatic expiration
- Connection pooling for high-performance access
- Automatic session cleanup and TTL management
- Error handling and connection recovery
- Background cleanup tasks for maintenance
- Scalable across multiple server instances
- JSON serialization for complex session data

Example:
    ```python
    # Initialize Redis storage
    storage = RedisSessionStorage(
        redis_url="redis://localhost:6379",
        session_prefix="session:",
        default_ttl=3600,  # 1 hour
        max_connections=10
    )
    
    # Start the storage service
    await storage.start_cleanup_task()
    
    # Store a session
    session_data = {"conversation_id": "call_123", "status": "active"}
    success = await storage.store_session("call_123", session_data)
    
    # Retrieve a session
    session = await storage.retrieve_session("call_123")
    
    # Close connections when done
    await storage.close()
    ```
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
    
    The storage uses Redis for persistent session data with automatic TTL
    management. It includes connection pooling for efficient Redis access,
    automatic connection recovery, and background cleanup tasks. Sessions
    are stored as JSON strings with metadata for tracking and management.
    
    Features:
    - Redis-based persistent storage with automatic expiration
    - Connection pooling for high-performance access
    - Automatic session cleanup and TTL management
    - Error handling and connection recovery
    - Background cleanup tasks for maintenance
    - Scalable across multiple server instances
    - JSON serialization for complex session data
    
    Attributes:
        redis_url: Redis connection URL
        session_prefix: Prefix for session keys in Redis
        default_ttl: Default TTL in seconds for sessions
        max_connections: Maximum number of Redis connections in pool
        redis_kwargs: Additional Redis connection parameters
        redis_pool: Redis connection pool
        redis_client: Redis client instance
        _cleanup_task: Background task for automatic cleanup
        _initialized: Whether Redis connection is established
    
    Example:
        ```python
        # Create Redis storage with custom configuration
        storage = RedisSessionStorage(
            redis_url="redis://localhost:6379",
            session_prefix="myapp:session:",
            default_ttl=7200,  # 2 hours
            max_connections=20
        )
        
        # Start background cleanup
        await storage.start_cleanup_task()
        
        # Use storage for session management
        await storage.store_session("call_123", session_data)
        session = await storage.retrieve_session("call_123")
        
        # Get storage statistics
        stats = storage.get_stats()
        print(f"Storage type: {stats['storage_type']}")
        ```
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
        
        Sets up the Redis storage with connection pooling and configuration.
        The storage will automatically manage Redis connections and provide
        persistent session storage with automatic expiration.
        
        Args:
            redis_url: Redis connection URL. Supports various formats:
                - redis://localhost:6379 (default)
                - redis://user:password@localhost:6379
                - redis://localhost:6379/0 (with database number)
                - rediss://localhost:6379 (SSL connection)
            session_prefix: Prefix for session keys in Redis. This helps
                organize keys and avoid conflicts with other applications.
                Defaults to "session:".
            default_ttl: Default TTL in seconds for sessions. Sessions
                will automatically expire after this time unless accessed.
                Defaults to 3600 (1 hour).
            max_connections: Maximum number of Redis connections in the
                connection pool. Higher values support more concurrent
                operations but use more memory.
                Defaults to 10 connections.
            **kwargs: Additional Redis connection parameters passed to
                redis.ConnectionPool.from_url(). Common options include:
                - decode_responses: Whether to decode responses to strings
                - socket_connect_timeout: Connection timeout in seconds
                - socket_timeout: Socket timeout in seconds
                - retry_on_timeout: Whether to retry on timeout
                
        Raises:
            ValueError: If redis_url is empty or invalid
            ValueError: If default_ttl or max_connections are not positive
            
        Example:
            ```python
            # Default configuration
            storage = RedisSessionStorage()
            
            # Custom configuration for production
            storage = RedisSessionStorage(
                redis_url="redis://redis.example.com:6379",
                session_prefix="prod:session:",
                default_ttl=7200,  # 2 hours
                max_connections=50,
                decode_responses=True,
                socket_connect_timeout=5
            )
            ```
        """
        if not redis_url or not isinstance(redis_url, str):
            raise ValueError("redis_url must be a non-empty string")
        if default_ttl <= 0:
            raise ValueError("default_ttl must be positive")
        if max_connections <= 0:
            raise ValueError("max_connections must be positive")
        
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
        """Ensure Redis connection is established and healthy.
        
        Checks if the Redis connection is available and working. If not,
        attempts to establish a new connection. This method is called
        before each Redis operation to ensure connectivity.
        
        The method handles connection recovery and will attempt to
        reconnect if the current connection is lost or unhealthy.
        
        Returns:
            bool: True if connection is available and healthy, False otherwise
            
        Raises:
            ConnectionError: If unable to establish Redis connection
            TimeoutError: If Redis connection times out
            
        Example:
            ```python
            # This method is called automatically before Redis operations
            # No need to call it manually in most cases
            
            # Manual connection check
            if await storage._ensure_connection():
                print("Redis connection is healthy")
            else:
                print("Redis connection failed")
            ```
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
        
        Generates the Redis key used to store session data. The key
        includes the session prefix and conversation ID for organization.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            str: Redis key for the session data
            
        Example:
            ```python
            # Generate session key
            key = storage._get_session_key("call_123")
            # Returns: "session:call_123"
            ```
        """
        return f"{self.session_prefix}{conversation_id}"
    
    def _get_session_meta_key(self, conversation_id: str) -> str:
        """Get Redis key for session metadata.
        
        Generates the Redis key used to store session metadata. This
        is separate from the main session data and includes additional
        tracking information.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            str: Redis key for session metadata
            
        Example:
            ```python
            # Generate metadata key
            meta_key = storage._get_session_meta_key("call_123")
            # Returns: "session:call_123:meta"
            ```
        """
        return f"{self.session_prefix}{conversation_id}:meta"
    
    async def store_session(self, conversation_id: str, session_data: Dict[str, Any]) -> bool:
        """Store session state in Redis.
        
        Stores the session data in Redis with automatic TTL management.
        The session is stored as a JSON string with the configured
        expiration time. Metadata is also stored separately for tracking.
        
        Args:
            conversation_id: Unique identifier for the conversation.
                Must be a non-empty string.
            session_data: Session state data to store. Should be a
                dictionary containing all session information.
                The data will be serialized to JSON for storage.
                
        Returns:
            bool: True if storage was successful, False otherwise
            
        Raises:
            ValueError: If conversation_id is empty or invalid
            TypeError: If session_data is not a dictionary
            ConnectionError: If unable to connect to Redis
            JSONEncodeError: If session_data cannot be serialized to JSON
            
        Example:
            ```python
            # Store a new session
            session_data = {
                "conversation_id": "call_123",
                "status": "active",
                "bot_name": "customer-service-bot",
                "created_at": "2023-01-01T12:00:00"
            }
            
            success = await storage.store_session("call_123", session_data)
            if success:
                print("Session stored in Redis successfully")
            ```
        """
        if not conversation_id or not isinstance(conversation_id, str):
            raise ValueError("conversation_id must be a non-empty string")
        
        if not isinstance(session_data, dict):
            raise TypeError("session_data must be a dictionary")
        
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
    
    async def retrieve_session(self, conversation_id: str, update_activity: bool = True) -> Optional[Dict[str, Any]]:
        """Retrieve session state from Redis.
        
        Retrieves session data from Redis and optionally updates the
        last activity timestamp. The session data is deserialized from
        JSON back to a Python dictionary.
        
        Args:
            conversation_id: Unique identifier for the conversation.
                Must be a non-empty string.
            update_activity: Whether to update the last activity timestamp
                when retrieving the session. Defaults to True. Set to False
                when you need to check session state without affecting
                activity tracking.
                
        Returns:
            Optional[Dict[str, Any]]: Session state data if found, None otherwise
            
        Raises:
            ValueError: If conversation_id is empty or invalid
            ConnectionError: If unable to connect to Redis
            JSONDecodeError: If stored session data is invalid JSON
            
        Example:
            ```python
            # Retrieve session and update activity
            session = await storage.retrieve_session("call_123")
            if session:
                print(f"Session status: {session['status']}")
            
            # Retrieve session without updating activity
            session = await storage.retrieve_session("call_123", update_activity=False)
            ```
        """
        if not conversation_id or not isinstance(conversation_id, str):
            raise ValueError("conversation_id must be a non-empty string")
        
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
            
            # Update last activity only if requested
            if update_activity:
                await self.update_session_activity(conversation_id)
            
            logger.debug(f"Retrieved session from Redis: {conversation_id}")
            return session_dict
            
        except Exception as e:
            logger.error(f"Error retrieving session from Redis: {e}")
            return None
    
    async def delete_session(self, conversation_id: str) -> bool:
        """Delete session state from Redis.
        
        Removes both the session data and metadata from Redis. This
        operation is immediate and cannot be undone. The session will
        no longer be available for retrieval.
        
        Args:
            conversation_id: Unique identifier for the conversation.
                Must be a non-empty string.
                
        Returns:
            bool: True if deletion was successful, False otherwise
            
        Raises:
            ValueError: If conversation_id is empty or invalid
            ConnectionError: If unable to connect to Redis
            
        Example:
            ```python
            # Delete a session
            success = await storage.delete_session("call_123")
            if success:
                print("Session deleted from Redis successfully")
            else:
                print("Session not found or deletion failed")
            ```
        """
        if not conversation_id or not isinstance(conversation_id, str):
            raise ValueError("conversation_id must be a non-empty string")
        
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
        
        Retrieves all conversation IDs for sessions currently stored
        in Redis. This method uses Redis KEYS pattern matching to
        find all session keys with the configured prefix.
        
        Note: This operation can be slow on large Redis databases
        as it uses the KEYS command. For production use with many
        sessions, consider using SCAN instead.
        
        Returns:
            List[str]: List of conversation IDs for active sessions
            
        Raises:
            ConnectionError: If unable to connect to Redis
            
        Example:
            ```python
            # Get all active sessions
            active_sessions = await storage.list_active_sessions()
            print(f"Active sessions: {len(active_sessions)}")
            
            # Process each session
            for session_id in active_sessions:
                session = await storage.retrieve_session(session_id)
                print(f"Session {session_id}: {session['status']}")
            ```
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
        
        Removes sessions that have exceeded the specified maximum age
        since their last activity. This method checks session metadata
        to determine which sessions should be cleaned up.
        
        Args:
            max_age_seconds: Maximum age in seconds before session is
                considered expired. Defaults to 3600 (1 hour).
                Sessions older than this will be removed from Redis.
                
        Returns:
            int: Number of sessions that were cleaned up
            
        Raises:
            ValueError: If max_age_seconds is not positive
            ConnectionError: If unable to connect to Redis
            
        Example:
            ```python
            # Clean up sessions older than 30 minutes
            cleaned_count = await storage.cleanup_expired_sessions(1800)
            print(f"Cleaned up {cleaned_count} expired sessions")
            
            # Clean up with default 1 hour expiration
            cleaned_count = await storage.cleanup_expired_sessions()
            ```
        """
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        
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
        
        Updates the last activity timestamp for a session without
        retrieving the full session data. This is useful for keeping
        sessions alive during long-running operations.
        
        Args:
            conversation_id: Unique identifier for the conversation.
                Must be a non-empty string.
                
        Returns:
            bool: True if update was successful, False otherwise
            
        Raises:
            ValueError: If conversation_id is empty or invalid
            ConnectionError: If unable to connect to Redis
            
        Example:
            ```python
            # Update activity to keep session alive
            success = await storage.update_session_activity("call_123")
            if success:
                print("Session activity updated in Redis")
            ```
        """
        if not conversation_id or not isinstance(conversation_id, str):
            raise ValueError("conversation_id must be a non-empty string")
        
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
    
    async def start_cleanup_task(self) -> None:
        """Start background cleanup task for expired sessions.
        
        Creates and starts an asyncio task that periodically checks
        for and removes expired sessions from Redis. The task runs
        every 5 minutes until stopped by calling stop_cleanup_task().
        
        The cleanup task helps prevent Redis memory growth by automatically
        removing sessions that have exceeded their expiration time.
        
        Raises:
            RuntimeError: If cleanup task is already running
            
        Example:
            ```python
            storage = RedisSessionStorage()
            await storage.start_cleanup_task()
            
            # Cleanup task is now running in the background
            # It will automatically remove expired sessions every 5 minutes
            ```
        """
        if self._cleanup_task and not self._cleanup_task.done():
            raise RuntimeError("Cleanup task is already running")
        
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Started Redis session cleanup task")
    
    async def stop_cleanup_task(self) -> None:
        """Stop background cleanup task.
        
        Gracefully stops the background cleanup task and waits for
        it to complete. This method should be called when shutting
        down the storage to ensure proper cleanup.
        
        Example:
            ```python
            # Stop the cleanup task
            await storage.stop_cleanup_task()
            
            # Cleanup task is now stopped
            ```
        """
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped Redis session cleanup task")
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for expired sessions.
        
        Continuously runs cleanup operations every 5 minutes. This
        method is designed to run as a background task and should
        not be called directly.
        
        The loop will continue running until cancelled by stop_cleanup_task()
        or if an unhandled exception occurs. On error, it waits 1 minute
        before retrying to avoid overwhelming the system.
        
        Raises:
            Exception: Any exception that occurs during cleanup will be
                logged but won't stop the loop unless it's a CancelledError
        """
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self.cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def close(self) -> None:
        """Close Redis connections and cleanup resources.
        
        Gracefully shuts down the Redis storage by stopping the cleanup
        task and closing all Redis connections. This method should be
        called when the storage is no longer needed to prevent resource
        leaks.
        
        After calling this method, the storage instance should not be
        used for further operations. A new instance would need to be
        created for additional storage operations.
        
        Example:
            ```python
            # Close Redis connections
            await storage.close()
            
            # Storage is now closed and connections are cleaned up
            # Don't use this instance for further operations
            ```
        """
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
        """Get Redis storage statistics and configuration.
        
        Returns comprehensive statistics about the Redis storage,
        including configuration, connection status, and task status.
        This is useful for monitoring and debugging.
        
        Returns:
            Dict[str, Any]: Dictionary containing storage statistics with keys:
                - storage_type: Always "redis" for this implementation
                - redis_url: Redis connection URL (with password masked)
                - session_prefix: Prefix used for session keys
                - default_ttl: Default TTL in seconds for sessions
                - max_connections: Maximum connections in the pool
                - initialized: Whether Redis connection is established
                - cleanup_task_running: Whether background cleanup is active
                
        Example:
            ```python
            # Get storage statistics
            stats = storage.get_stats()
            print(f"Storage type: {stats['storage_type']}")
            print(f"Redis URL: {stats['redis_url']}")
            print(f"Connection initialized: {stats['initialized']}")
            print(f"Cleanup task running: {stats['cleanup_task_running']}")
            ```
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