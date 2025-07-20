"""Memory-based session storage implementation.

This module provides an in-memory implementation of session storage
for development and testing purposes. It includes automatic cleanup
of expired sessions and memory management.

The MemorySessionStorage class provides a fast, in-memory storage
solution that's ideal for development, testing, and single-instance
deployments. It features automatic session expiration, memory limits,
and background cleanup tasks to prevent memory leaks.

Key Features:
- In-memory storage with O(1) access times
- Automatic cleanup of expired sessions
- Configurable session limits and cleanup intervals
- Thread-safe operations using asyncio locks
- Background cleanup task for maintenance
- Memory management with oldest session eviction

Example:
    ```python
    # Initialize memory storage
    storage = MemorySessionStorage(
        max_sessions=1000,
        cleanup_interval=300  # 5 minutes
    )
    
    # Start the storage service
    await storage.start_cleanup_task()
    
    # Store a session
    session_data = {"conversation_id": "call_123", "status": "active"}
    success = await storage.store_session("call_123", session_data)
    
    # Retrieve a session
    session = await storage.retrieve_session("call_123")
    
    # Stop the storage service
    await storage.stop_cleanup_task()
    ```
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from . import SessionStorage
from opusagent.config.logging_config import configure_logging

logger = configure_logging("memory_session_storage")


class MemorySessionStorage(SessionStorage):
    """In-memory session storage implementation.
    
    This implementation stores session data in memory with automatic
    cleanup of expired sessions. It's suitable for development and
    testing, but not for production use with multiple server instances.
    
    The storage uses a dictionary-based approach with O(1) access times
    and includes automatic memory management to prevent unbounded growth.
    Sessions are automatically cleaned up based on their last activity
    timestamp, and the storage enforces a maximum session limit.
    
    Features:
    - In-memory storage with automatic cleanup
    - Configurable session limits and cleanup intervals
    - Thread-safe operations using asyncio locks
    - Background cleanup task for maintenance
    - Memory management with oldest session eviction
    - Automatic timestamp management
    
    Attributes:
        _sessions: Dictionary storing session data by conversation ID
        _session_timestamps: Dictionary storing last activity timestamps
        _max_sessions: Maximum number of sessions allowed in storage
        _cleanup_interval: Interval in seconds between cleanup runs
        _cleanup_task: Background task for automatic cleanup
        _lock: Asyncio lock for thread-safe operations
    
    Example:
        ```python
        # Create storage with custom limits
        storage = MemorySessionStorage(
            max_sessions=500,
            cleanup_interval=180  # 3 minutes
        )
        
        # Start background cleanup
        await storage.start_cleanup_task()
        
        # Use storage for session management
        await storage.store_session("call_123", session_data)
        session = await storage.retrieve_session("call_123")
        
        # Get storage statistics
        stats = storage.get_stats()
        print(f"Active sessions: {stats['total_sessions']}")
        ```
    """
    
    def __init__(self, max_sessions: int = 1000, cleanup_interval: int = 300):
        """Initialize memory session storage.
        
        Sets up the in-memory storage with configurable limits and
        cleanup intervals. The storage will automatically manage memory
        usage and clean up expired sessions in the background.
        
        Args:
            max_sessions: Maximum number of sessions to store in memory.
                When this limit is reached, the oldest session will be
                automatically evicted to make room for new ones.
                Defaults to 1000 sessions.
            cleanup_interval: Interval in seconds between automatic
                cleanup runs. The background task will check for and
                remove expired sessions at this interval.
                Defaults to 300 seconds (5 minutes).
                
        Raises:
            ValueError: If max_sessions or cleanup_interval are not positive
            
        Example:
            ```python
            # Default configuration
            storage = MemorySessionStorage()
            
            # Custom configuration for testing
            storage = MemorySessionStorage(
                max_sessions=100,    # Small limit for testing
                cleanup_interval=60  # Frequent cleanup
            )
            ```
        """
        if max_sessions <= 0:
            raise ValueError("max_sessions must be positive")
        if cleanup_interval <= 0:
            raise ValueError("cleanup_interval must be positive")
        
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._session_timestamps: Dict[str, float] = {}
        self._max_sessions = max_sessions
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        logger.info(f"Memory session storage initialized: max_sessions={max_sessions}, cleanup_interval={cleanup_interval}s")
    
    async def start_cleanup_task(self) -> None:
        """Start background cleanup task for expired sessions.
        
        Creates and starts an asyncio task that periodically checks
        for and removes expired sessions. The task runs continuously
        until stopped by calling stop_cleanup_task().
        
        The cleanup task helps prevent memory leaks by automatically
        removing sessions that have exceeded their expiration time.
        
        Raises:
            RuntimeError: If cleanup task is already running
            
        Example:
            ```python
            storage = MemorySessionStorage()
            await storage.start_cleanup_task()
            
            # Cleanup task is now running in the background
            # It will automatically remove expired sessions
            ```
        """
        if self._cleanup_task is not None and not self._cleanup_task.done():
            raise RuntimeError("Cleanup task is already running")
        
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Background cleanup task started")
    
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
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Background cleanup task stopped")
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for expired sessions.
        
        Continuously runs cleanup operations at the configured interval.
        This method is designed to run as a background task and should
        not be called directly.
        
        The loop will continue running until cancelled by stop_cleanup_task()
        or if an unhandled exception occurs.
        
        Raises:
            Exception: Any exception that occurs during cleanup will be
                logged but won't stop the loop unless it's a CancelledError
        """
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                cleaned_count = await self.cleanup_expired_sessions()
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} expired sessions")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def store_session(self, conversation_id: str, session_data: Dict[str, Any]) -> bool:
        """Store session state in memory.
        
        Stores the session data in memory with automatic timestamp
        management. If the storage is at capacity, the oldest session
        will be automatically evicted to make room for the new session.
        
        Args:
            conversation_id: Unique identifier for the conversation session.
                Must be a non-empty string.
            session_data: Dictionary containing session state data.
                Should include all necessary session information.
                If 'last_activity' is not present, it will be automatically
                added with the current timestamp.
                
        Returns:
            bool: True if session was stored successfully, False otherwise
            
        Raises:
            ValueError: If conversation_id is empty or invalid
            TypeError: If session_data is not a dictionary
            
        Example:
            ```python
            # Store a new session
            session_data = {
                "conversation_id": "call_123",
                "status": "active",
                "bot_name": "customer-service-bot"
            }
            
            success = await storage.store_session("call_123", session_data)
            if success:
                print("Session stored successfully")
            ```
        """
        if not conversation_id or not isinstance(conversation_id, str):
            raise ValueError("conversation_id must be a non-empty string")
        
        if not isinstance(session_data, dict):
            raise TypeError("session_data must be a dictionary")
        
        async with self._lock:
            try:
                # Add timestamp if not present
                if "last_activity" not in session_data:
                    session_data["last_activity"] = datetime.now().isoformat()
                
                # Check if we need to make room
                if len(self._sessions) >= self._max_sessions:
                    await self._evict_oldest_session()
                
                self._sessions[conversation_id] = session_data
                self._session_timestamps[conversation_id] = time.time()
                
                logger.debug(f"Stored session: {conversation_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error storing session {conversation_id}: {e}")
                return False
    
    async def retrieve_session(self, conversation_id: str, update_activity: bool = True) -> Optional[Dict[str, Any]]:
        """Retrieve session state from memory.
        
        Retrieves session data from memory and optionally updates the
        last activity timestamp. This method is thread-safe and provides
        O(1) access time for session retrieval.
        
        Args:
            conversation_id: Unique conversation identifier to retrieve.
                Must be a non-empty string.
            update_activity: Whether to update the last activity timestamp
                when retrieving the session. Defaults to True. Set to False
                when you need to check session state without affecting
                activity tracking.
                
        Returns:
            Optional[Dict[str, Any]]: Session data if found, None otherwise
            
        Raises:
            ValueError: If conversation_id is empty or invalid
            
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
        
        async with self._lock:
            try:
                session_data = self._sessions.get(conversation_id)
                if session_data:
                    # Update last activity only if requested
                    if update_activity:
                        session_data["last_activity"] = datetime.now().isoformat()
                        self._session_timestamps[conversation_id] = time.time()
                    logger.debug(f"Retrieved session: {conversation_id}")
                    return session_data
                return None
                
            except Exception as e:
                logger.error(f"Error retrieving session {conversation_id}: {e}")
                return None
    
    async def delete_session(self, conversation_id: str) -> bool:
        """Delete session state from memory.
        
        Removes the session data and timestamp from memory. This operation
        is immediate and cannot be undone. The session will no longer be
        available for retrieval.
        
        Args:
            conversation_id: Unique conversation identifier to delete.
                Must be a non-empty string.
                
        Returns:
            bool: True if session was deleted successfully, False if session
                not found or error occurred
                
        Raises:
            ValueError: If conversation_id is empty or invalid
            
        Example:
            ```python
            # Delete a session
            success = await storage.delete_session("call_123")
            if success:
                print("Session deleted successfully")
            else:
                print("Session not found or deletion failed")
            ```
        """
        if not conversation_id or not isinstance(conversation_id, str):
            raise ValueError("conversation_id must be a non-empty string")
        
        async with self._lock:
            try:
                if conversation_id in self._sessions:
                    del self._sessions[conversation_id]
                    del self._session_timestamps[conversation_id]
                    logger.debug(f"Deleted session: {conversation_id}")
                    return True
                return False
                
            except Exception as e:
                logger.error(f"Error deleting session {conversation_id}: {e}")
                return False
    
    async def list_active_sessions(self) -> List[str]:
        """List all active session IDs in memory.
        
        Returns a list of all conversation IDs currently stored in memory.
        This method is useful for monitoring and debugging purposes.
        
        Returns:
            List[str]: List of all active conversation IDs
            
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
        async with self._lock:
            return list(self._sessions.keys())
    
    async def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> int:
        """Clean up expired sessions from memory.
        
        Removes sessions that have exceeded the specified maximum age
        since their last activity. This method is called automatically
        by the background cleanup task, but can also be called manually
        for immediate cleanup.
        
        Args:
            max_age_seconds: Maximum age in seconds before session is
                considered expired. Defaults to 3600 (1 hour).
                Sessions older than this will be removed from memory.
                
        Returns:
            int: Number of sessions that were cleaned up
            
        Raises:
            ValueError: If max_age_seconds is not positive
            
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
        
        async with self._lock:
            current_time = time.time()
            expired_sessions = []
            
            for conv_id, timestamp in self._session_timestamps.items():
                if current_time - timestamp > max_age_seconds:
                    expired_sessions.append(conv_id)
            
            # Remove expired sessions
            for conv_id in expired_sessions:
                del self._sessions[conv_id]
                del self._session_timestamps[conv_id]
            
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            
            return len(expired_sessions)
    
    async def update_session_activity(self, conversation_id: str) -> bool:
        """Update session last activity timestamp.
        
        Updates the last activity timestamp for a session without
        retrieving the full session data. This is useful for keeping
        sessions alive during long-running operations.
        
        Args:
            conversation_id: Unique conversation identifier to update.
                Must be a non-empty string.
                
        Returns:
            bool: True if activity was updated successfully, False if
                session not found or error occurred
                
        Raises:
            ValueError: If conversation_id is empty or invalid
            
        Example:
            ```python
            # Update activity to keep session alive
            success = await storage.update_session_activity("call_123")
            if success:
                print("Session activity updated")
            ```
        """
        if not conversation_id or not isinstance(conversation_id, str):
            raise ValueError("conversation_id must be a non-empty string")
        
        async with self._lock:
            try:
                if conversation_id in self._sessions:
                    self._sessions[conversation_id]["last_activity"] = datetime.now().isoformat()
                    self._session_timestamps[conversation_id] = time.time()
                    return True
                return False
                
            except Exception as e:
                logger.error(f"Error updating session activity {conversation_id}: {e}")
                return False
    
    async def _evict_oldest_session(self) -> None:
        """Evict the oldest session to make room for new ones.
        
        Removes the session with the oldest last activity timestamp
        to maintain the maximum session limit. This method is called
        automatically when the storage reaches capacity.
        
        The eviction is based on the last activity timestamp, ensuring
        that the least recently used session is removed first.
        
        Example:
            ```python
            # This method is called automatically when storage is full
            # No need to call it manually
            ```
        """
        if not self._session_timestamps:
            return
        
        oldest_conv_id = min(
            self._session_timestamps.keys(),
            key=lambda k: self._session_timestamps[k]
        )
        
        del self._sessions[oldest_conv_id]
        del self._session_timestamps[oldest_conv_id]
        logger.debug(f"Evicted oldest session: {oldest_conv_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics and health information.
        
        Returns comprehensive statistics about the memory storage,
        including session counts, configuration, and task status.
        This is useful for monitoring and debugging.
        
        Returns:
            Dict[str, Any]: Dictionary containing storage statistics with keys:
                - total_sessions: Current number of sessions in storage
                - max_sessions: Maximum number of sessions allowed
                - cleanup_interval: Interval between cleanup runs in seconds
                - cleanup_task_running: Whether background cleanup is active
                
        Example:
            ```python
            # Get storage statistics
            stats = storage.get_stats()
            print(f"Active sessions: {stats['total_sessions']}/{stats['max_sessions']}")
            print(f"Cleanup task running: {stats['cleanup_task_running']}")
            ```
        """
        return {
            "total_sessions": len(self._sessions),
            "max_sessions": self._max_sessions,
            "cleanup_interval": self._cleanup_interval,
            "cleanup_task_running": self._cleanup_task is not None and not self._cleanup_task.done()
        } 