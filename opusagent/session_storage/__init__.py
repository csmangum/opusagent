"""Session storage package for persistent session state management.

This package provides interfaces and implementations for storing and retrieving
session state data, enabling session resume functionality across different
storage backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


class SessionStorage(ABC):
    """Abstract interface for session state storage.
    
    This interface defines the contract for storing and retrieving
    session state data. Implementations can use different storage
    backends (memory, Redis, database) while maintaining the same
    interface.
    """
    
    @abstractmethod
    async def store_session(self, conversation_id: str, session_data: Dict[str, Any]) -> bool:
        """Store session state.
        
        Args:
            conversation_id: Unique identifier for the conversation
            session_data: Session state data to store
            
        Returns:
            True if storage was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def retrieve_session(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session state.
        
        Args:
            conversation_id: Unique identifier for the conversation
            
        Returns:
            Session state data if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def delete_session(self, conversation_id: str) -> bool:
        """Delete session state.
        
        Args:
            conversation_id: Unique identifier for the conversation
            
        Returns:
            True if deletion was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def list_active_sessions(self) -> List[str]:
        """List all active session IDs.
        
        Returns:
            List of conversation IDs for active sessions
        """
        pass
    
    @abstractmethod
    async def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> int:
        """Clean up expired sessions.
        
        Args:
            max_age_seconds: Maximum age in seconds before session is considered expired
            
        Returns:
            Number of sessions cleaned up
        """
        pass
    
    @abstractmethod
    async def update_session_activity(self, conversation_id: str) -> bool:
        """Update session last activity timestamp.
        
        Args:
            conversation_id: Unique identifier for the conversation
            
        Returns:
            True if update was successful, False otherwise
        """
        pass
    
    async def start_cleanup_task(self):
        """Start background cleanup task (optional)."""
        pass
    
    async def stop_cleanup_task(self):
        """Stop background cleanup task (optional)."""
        pass


# Import implementations after defining the base class
from .memory_storage import MemorySessionStorage
from .redis_storage import RedisSessionStorage

__all__ = ["SessionStorage", "MemorySessionStorage", "RedisSessionStorage"] 