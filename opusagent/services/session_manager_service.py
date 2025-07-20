"""Session manager service for centralized session management.

This module provides a centralized service for managing session state,
including creation, retrieval, updates, and cleanup operations.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from opusagent.session_storage import SessionStorage
from opusagent.models.session_state import SessionState, SessionStatus
from opusagent.config.logging_config import configure_logging

logger = configure_logging("session_manager_service")


class SessionManagerService:
    """Centralized session management service.
    
    This service provides a high-level interface for session management,
    including session creation, retrieval, updates, and cleanup. It
    coordinates with the underlying storage backend to maintain session
    state persistence.
    """
    
    def __init__(self, storage):
        """Initialize session manager service.
        
        Args:
            storage: Session storage backend implementation
        """
        self.storage = storage
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("Session manager service initialized")
    
    async def start(self):
        """Start the session manager service."""
        if hasattr(self.storage, 'start_cleanup_task'):
            await self.storage.start_cleanup_task()
        logger.info("Session manager service started")
    
    async def stop(self):
        """Stop the session manager service."""
        if hasattr(self.storage, 'stop_cleanup_task'):
            await self.storage.stop_cleanup_task()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("Session manager service stopped")
    
    async def create_session(self, conversation_id: str, **kwargs) -> SessionState:
        """Create a new session.
        
        Args:
            conversation_id: Unique conversation identifier
            **kwargs: Additional session parameters
            
        Returns:
            Created session state
        """
        session_state = SessionState(conversation_id=conversation_id, **kwargs)
        await self.storage.store_session(conversation_id, session_state.to_dict())
        logger.info(f"Created session: {conversation_id}")
        return session_state
    
    async def get_session(self, conversation_id: str) -> Optional[SessionState]:
        """Retrieve a session by conversation ID.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            Session state if found, None otherwise
        """
        session_data = await self.storage.retrieve_session(conversation_id)
        if session_data:
            session_state = SessionState.from_dict(session_data)
            # Update last activity
            session_state.update_activity()
            await self.storage.store_session(conversation_id, session_state.to_dict())
            return session_state
        return None
    
    async def update_session(self, conversation_id: str, **updates) -> bool:
        """Update session state.
        
        Args:
            conversation_id: Unique conversation identifier
            **updates: Session state updates
            
        Returns:
            True if update was successful, False otherwise
        """
        session_state = await self.get_session(conversation_id)
        if not session_state:
            return False
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(session_state, key):
                setattr(session_state, key, value)
        
        session_state.update_activity()
        await self.storage.store_session(conversation_id, session_state.to_dict())
        return True
    
    async def resume_session(self, conversation_id: str) -> Optional[SessionState]:
        """Resume an existing session.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            Resumed session state if successful, None otherwise
        """
        session_state = await self.get_session(conversation_id)
        if not session_state:
            return None
        
        # Validate session can be resumed
        if not session_state.can_resume():
            logger.warning(f"Cannot resume session {conversation_id}: status={session_state.status}")
            return None
        
        # Check if session is expired
        if session_state.is_expired():
            logger.warning(f"Session {conversation_id} is expired, cannot resume")
            return None
        
        # Update resume count and status
        session_state.increment_resume_count()
        
        await self.storage.store_session(conversation_id, session_state.to_dict())
        logger.info(f"Resumed session: {conversation_id} (resume #{session_state.resumed_count})")
        return session_state
    
    async def end_session(self, conversation_id: str, reason: str = "Session ended") -> bool:
        """End a session.
        
        Args:
            conversation_id: Unique conversation identifier
            reason: Reason for ending the session
            
        Returns:
            True if session was ended successfully, False otherwise
        """
        session_state = await self.get_session(conversation_id)
        if not session_state:
            return False
        
        session_state.status = SessionStatus.ENDED
        session_state.metadata["end_reason"] = reason
        session_state.update_activity()
        
        await self.storage.store_session(conversation_id, session_state.to_dict())
        logger.info(f"Ended session: {conversation_id} - {reason}")
        return True
    
    async def delete_session(self, conversation_id: str) -> bool:
        """Delete a session completely.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            True if session was deleted successfully, False otherwise
        """
        success = await self.storage.delete_session(conversation_id)
        if success:
            logger.info(f"Deleted session: {conversation_id}")
        return success
    
    async def list_active_sessions(self) -> List[str]:
        """List all active session IDs.
        
        Returns:
            List of active conversation IDs
        """
        return await self.storage.list_active_sessions()
    
    async def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> int:
        """Clean up expired sessions.
        
        Args:
            max_age_seconds: Maximum age in seconds before session is considered expired
            
        Returns:
            Number of sessions cleaned up
        """
        return await self.storage.cleanup_expired_sessions(max_age_seconds)
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get session management statistics.
        
        Returns:
            Dictionary containing session statistics
        """
        active_sessions = await self.list_active_sessions()
        storage_stats = getattr(self.storage, 'get_stats', lambda: {})()
        
        return {
            "active_sessions_count": len(active_sessions),
            "storage_stats": storage_stats,
            "service_status": "running" if not self._cleanup_task or not self._cleanup_task.done() else "stopped"
        }
    
    async def validate_session(self, conversation_id: str) -> Dict[str, Any]:
        """Validate a session for resume operations.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            Validation result dictionary
        """
        session_state = await self.get_session(conversation_id)
        
        if not session_state:
            return {
                "valid": False,
                "reason": "Session not found",
                "can_resume": False
            }
        
        if not session_state.can_resume():
            return {
                "valid": False,
                "reason": f"Session status: {session_state.status.value}",
                "can_resume": False
            }
        
        if session_state.is_expired():
            return {
                "valid": False,
                "reason": "Session expired",
                "can_resume": False
            }
        
        return {
            "valid": True,
            "reason": "Session is valid",
            "can_resume": True,
            "resume_count": session_state.resumed_count,
            "last_activity": session_state.last_activity.isoformat()
        } 