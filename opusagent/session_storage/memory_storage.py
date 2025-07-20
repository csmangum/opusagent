"""Memory-based session storage implementation.

This module provides an in-memory implementation of session storage
for development and testing purposes. It includes automatic cleanup
of expired sessions and memory management.
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
    
    Features:
    - In-memory storage with automatic cleanup
    - Configurable session limits and cleanup intervals
    - Thread-safe operations
    - Background cleanup task
    """
    
    def __init__(self, max_sessions: int = 1000, cleanup_interval: int = 300):
        """Initialize memory session storage.
        
        Args:
            max_sessions: Maximum number of sessions to store
            cleanup_interval: Cleanup interval in seconds
        """
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._session_timestamps: Dict[str, float] = {}
        self._max_sessions = max_sessions
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        logger.info(f"Memory session storage initialized: max_sessions={max_sessions}, cleanup_interval={cleanup_interval}s")
    
    async def start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Background cleanup task started")
    
    async def stop_cleanup_task(self):
        """Stop background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Background cleanup task stopped")
    
    async def _cleanup_loop(self):
        """Background cleanup loop."""
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
        """Store session state in memory."""
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
        
        Args:
            conversation_id: Unique conversation identifier
            update_activity: Whether to update the last activity timestamp
            
        Returns:
            Session data if found, None otherwise
        """
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
        """Delete session state from memory."""
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
        """List all active session IDs."""
        async with self._lock:
            return list(self._sessions.keys())
    
    async def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> int:
        """Clean up expired sessions."""
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
        """Update session last activity timestamp."""
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
    
    async def _evict_oldest_session(self):
        """Evict the oldest session to make room for new ones."""
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
        """Get storage statistics."""
        return {
            "total_sessions": len(self._sessions),
            "max_sessions": self._max_sessions,
            "cleanup_interval": self._cleanup_interval,
            "cleanup_task_running": self._cleanup_task is not None and not self._cleanup_task.done()
        } 