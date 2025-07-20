"""Session manager service for centralized session management.

This module provides a centralized service for managing session state,
including creation, retrieval, updates, and cleanup operations. The service
acts as a high-level interface that coordinates with underlying storage
backends to maintain session state persistence across the application.

The SessionManagerService handles the complete lifecycle of sessions:
- Session creation and initialization
- Session retrieval and validation
- Session updates and state management
- Session resumption with expiration checks
- Session termination and cleanup
- Session statistics and monitoring

Example:
    ```python
    # Initialize with Redis storage
    storage = RedisSessionStorage(redis_client)
    session_service = SessionManagerService(storage)
    
    # Start the service
    await session_service.start()
    
    # Create a new session
    session = await session_service.create_session("conv_123")
    
    # Resume an existing session
    resumed_session = await session_service.resume_session("conv_123")
    
    # End the session
    await session_service.end_session("conv_123", "Call completed")
    ```
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
    
    The service handles session lifecycle operations and provides methods
    for session validation, resumption, and monitoring. It also manages
    automatic cleanup of expired sessions and provides statistics for
    monitoring session health.
    
    Attributes:
        storage: The underlying session storage backend implementation
        _cleanup_task: Optional asyncio task for background cleanup operations
    
    Example:
        ```python
        # Initialize with memory storage
        storage = MemorySessionStorage()
        service = SessionManagerService(storage)
        
        # Start the service
        await service.start()
        
        # Create and manage sessions
        session = await service.create_session("call_123")
        await service.update_session("call_123", status=SessionStatus.ACTIVE)
        await service.end_session("call_123", "Call completed")
        ```
    """
    
    def __init__(self, storage: SessionStorage):
        """Initialize session manager service.
        
        Args:
            storage: Session storage backend implementation that conforms to
                the SessionStorage interface. Must support async operations
                for storing, retrieving, and managing session data.
        
        Raises:
            TypeError: If storage is None or doesn't implement required methods
            ValueError: If storage configuration is invalid
        
        Example:
            ```python
            # Initialize with Redis storage
            redis_storage = RedisSessionStorage(redis_client)
            service = SessionManagerService(redis_storage)
            ```
        """
        if storage is None:
            raise TypeError("Storage backend cannot be None")
        
        self.storage = storage
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("Session manager service initialized")
    
    async def start(self) -> None:
        """Start the session manager service.
        
        Initializes the service and starts any background tasks such as
        cleanup operations. This method should be called before using
        the service for session management operations.
        
        Raises:
            RuntimeError: If the service is already running
            ConnectionError: If unable to connect to the storage backend
        
        Example:
            ```python
            service = SessionManagerService(storage)
            await service.start()
            # Service is now ready for session operations
            ```
        """
        if hasattr(self.storage, 'start_cleanup_task'):
            await self.storage.start_cleanup_task()
        logger.info("Session manager service started")
    
    async def stop(self) -> None:
        """Stop the session manager service.
        
        Gracefully shuts down the service, cancelling any background tasks
        and cleaning up resources. This method should be called when the
        service is no longer needed.
        
        Raises:
            RuntimeError: If the service is already stopped
        
        Example:
            ```python
            await service.stop()
            # Service is now stopped and resources are cleaned up
            ```
        """
        if hasattr(self.storage, 'stop_cleanup_task'):
            await self.storage.stop_cleanup_task()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("Session manager service stopped")
    
    async def create_session(self, conversation_id: str, **kwargs) -> SessionState:
        """Create a new session with the specified conversation ID.
        
        Creates a new SessionState instance and stores it in the underlying
        storage backend. The session is initialized with default values and
        any additional parameters provided in kwargs.
        
        Args:
            conversation_id: Unique conversation identifier. Must be a non-empty
                string that uniquely identifies the conversation session.
            **kwargs: Additional session parameters to set during creation.
                Common parameters include:
                - status: Initial session status (default: SessionStatus.ACTIVE)
                - metadata: Dictionary of session metadata
                - created_by: Identifier of who created the session
                - max_age_seconds: Session expiration time in seconds
        
        Returns:
            SessionState: The newly created session state object
            
        Raises:
            ValueError: If conversation_id is empty or invalid
            StorageError: If unable to store the session in the backend
            DuplicateSessionError: If a session with the same ID already exists
        
        Example:
            ```python
            # Create a basic session
            session = await service.create_session("call_123")
            
            # Create session with custom parameters
            session = await service.create_session(
                "call_456",
                status=SessionStatus.ACTIVE,
                metadata={"caller_id": "user123", "priority": "high"},
                max_age_seconds=7200
            )
            ```
        """
        if not conversation_id or not isinstance(conversation_id, str):
            raise ValueError("conversation_id must be a non-empty string")
        
        session_state = SessionState(conversation_id=conversation_id, **kwargs)
        await self.storage.store_session(conversation_id, session_state.to_dict())
        logger.info(f"Created session: {conversation_id}")
        return session_state
    
    async def get_session(self, conversation_id: str, update_activity: bool = True) -> Optional[SessionState]:
        """Retrieve a session by conversation ID.
        
        Fetches the session state from the storage backend and optionally
        updates the last activity timestamp. If the session is not found,
        returns None.
        
        Args:
            conversation_id: Unique conversation identifier to retrieve
            update_activity: Whether to update the last activity timestamp
                when retrieving the session. Defaults to True. Set to False
                when you need to check session state without affecting
                activity tracking.
        
        Returns:
            Optional[SessionState]: The session state if found, None otherwise
            
        Raises:
            ValueError: If conversation_id is empty or invalid
            StorageError: If unable to retrieve from the storage backend
        
        Example:
            ```python
            # Get session and update activity
            session = await service.get_session("call_123")
            if session:
                print(f"Session status: {session.status}")
            
            # Get session without updating activity (for validation)
            session = await service.get_session("call_123", update_activity=False)
            ```
        """
        if not conversation_id or not isinstance(conversation_id, str):
            raise ValueError("conversation_id must be a non-empty string")
        
        session_data = await self.storage.retrieve_session(conversation_id, update_activity=update_activity)
        if session_data:
            session_state = SessionState.from_dict(session_data)
            return session_state
        return None
    
    async def update_session(self, conversation_id: str, **updates) -> bool:
        """Update session state with the provided changes.
        
        Retrieves the current session state, applies the specified updates,
        and stores the updated state back to the storage backend. Only
        attributes that exist on the SessionState object will be updated.
        
        Args:
            conversation_id: Unique conversation identifier to update
            **updates: Session state updates as keyword arguments.
                Common updates include:
                - status: New session status
                - metadata: Updated metadata dictionary
                - resumed_count: Increment resume counter
                - last_activity: Manual activity timestamp update
        
        Returns:
            bool: True if update was successful, False if session not found
            
        Raises:
            ValueError: If conversation_id is empty or invalid
            StorageError: If unable to store the updated session
        
        Example:
            ```python
            # Update session status
            success = await service.update_session("call_123", status=SessionStatus.PAUSED)
            
            # Update metadata
            success = await service.update_session(
                "call_123",
                metadata={"current_step": "payment", "attempts": 3}
            )
            
            # Multiple updates
            success = await service.update_session(
                "call_123",
                status=SessionStatus.ACTIVE,
                resumed_count=session.resumed_count + 1
            )
            ```
        """
        if not conversation_id or not isinstance(conversation_id, str):
            raise ValueError("conversation_id must be a non-empty string")
        
        session_state = await self.get_session(conversation_id, update_activity=False)
        if not session_state:
            return False
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(session_state, key):
                setattr(session_state, key, value)
        
        session_state.update_activity()
        await self.storage.store_session(conversation_id, session_state.to_dict())
        return True
    
    async def resume_session(self, conversation_id: str, max_age_seconds: int = 3600) -> Optional[SessionState]:
        """Resume an existing session with expiration validation.
        
        Attempts to resume a session by validating its current state and
        expiration. The session must be in a resumable state and not expired
        according to the specified maximum age. If successful, increments
        the resume count and updates the session state.
        
        Args:
            conversation_id: Unique conversation identifier to resume
            max_age_seconds: Maximum age in seconds before session is considered
                expired. Defaults to 3600 (1 hour). Sessions older than this
                will not be resumable.
        
        Returns:
            Optional[SessionState]: Resumed session state if successful, None otherwise
            
        Raises:
            ValueError: If conversation_id is empty or invalid
            StorageError: If unable to retrieve or store the session
        
        Example:
            ```python
            # Resume session with default expiration (1 hour)
            session = await service.resume_session("call_123")
            if session:
                print(f"Resumed session, count: {session.resumed_count}")
            
            # Resume session with custom expiration (30 minutes)
            session = await service.resume_session("call_123", max_age_seconds=1800)
            ```
        """
        if not conversation_id or not isinstance(conversation_id, str):
            raise ValueError("conversation_id must be a non-empty string")
        
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        
        # Get session without updating activity to check expiration
        session_state = await self.get_session(conversation_id, update_activity=False)
        if not session_state:
            return None
        
        # Validate session can be resumed (includes expiration check)
        if not session_state.can_resume(max_age_seconds):
            logger.warning(f"Cannot resume session {conversation_id}: status={session_state.status}")
            return None
        
        # Update resume count and status
        session_state.increment_resume_count()
        
        await self.storage.store_session(conversation_id, session_state.to_dict())
        logger.info(f"Resumed session: {conversation_id} (resume #{session_state.resumed_count})")
        return session_state
    
    async def end_session(self, conversation_id: str, reason: str = "Session ended") -> bool:
        """End a session and mark it as terminated.
        
        Changes the session status to ENDED and stores the reason for
        termination in the session metadata. The session will no longer
        be considered active and cannot be resumed.
        
        Args:
            conversation_id: Unique conversation identifier to end
            reason: Human-readable reason for ending the session.
                This is stored in the session metadata for audit purposes.
                Defaults to "Session ended".
        
        Returns:
            bool: True if session was ended successfully, False if session not found
            
        Raises:
            ValueError: If conversation_id is empty or invalid
            StorageError: If unable to store the updated session
        
        Example:
            ```python
            # End session with default reason
            success = await service.end_session("call_123")
            
            # End session with custom reason
            success = await service.end_session(
                "call_123",
                reason="Caller hung up unexpectedly"
            )
            ```
        """
        if not conversation_id or not isinstance(conversation_id, str):
            raise ValueError("conversation_id must be a non-empty string")
        
        session_state = await self.get_session(conversation_id, update_activity=False)
        if not session_state:
            return False
        
        session_state.status = SessionStatus.ENDED
        session_state.metadata["end_reason"] = reason
        session_state.update_activity()
        
        await self.storage.store_session(conversation_id, session_state.to_dict())
        logger.info(f"Ended session: {conversation_id} - {reason}")
        return True
    
    async def delete_session(self, conversation_id: str) -> bool:
        """Delete a session completely from storage.
        
        Permanently removes the session from the storage backend. This
        operation cannot be undone and all session data will be lost.
        Use with caution, especially for sessions that may need to be
        audited or analyzed later.
        
        Args:
            conversation_id: Unique conversation identifier to delete
        
        Returns:
            bool: True if session was deleted successfully, False if session not found
            
        Raises:
            ValueError: If conversation_id is empty or invalid
            StorageError: If unable to delete from the storage backend
        
        Example:
            ```python
            # Delete a session
            success = await service.delete_session("call_123")
            if success:
                print("Session deleted successfully")
            ```
        """
        if not conversation_id or not isinstance(conversation_id, str):
            raise ValueError("conversation_id must be a non-empty string")
        
        success = await self.storage.delete_session(conversation_id)
        if success:
            logger.info(f"Deleted session: {conversation_id}")
        return success
    
    async def list_active_sessions(self) -> List[str]:
        """List all active session IDs.
        
        Retrieves all session IDs from the storage backend and filters
        them to return only those that are not in ENDED status. This
        provides a list of sessions that are currently active and
        potentially resumable.
        
        Returns:
            List[str]: List of active conversation IDs (excluding ended sessions)
            
        Raises:
            StorageError: If unable to retrieve sessions from the backend
        
        Example:
            ```python
            # Get all active sessions
            active_sessions = await service.list_active_sessions()
            print(f"Active sessions: {len(active_sessions)}")
            
            # Process each active session
            for session_id in active_sessions:
                session = await service.get_session(session_id)
                print(f"Session {session_id}: {session.status}")
            ```
        """
        all_sessions = await self.storage.list_active_sessions()
        active_sessions = []
        
        for conversation_id in all_sessions:
            # Get session without updating activity to check status
            session_state = await self.get_session(conversation_id, update_activity=False)
            if session_state and session_state.status != SessionStatus.ENDED:
                active_sessions.append(conversation_id)
        
        return active_sessions
    
    async def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> int:
        """Clean up expired sessions from storage.
        
        Removes sessions that have exceeded the specified maximum age
        from the storage backend. This helps maintain storage efficiency
        and prevents accumulation of stale session data.
        
        Args:
            max_age_seconds: Maximum age in seconds before session is considered
                expired. Defaults to 3600 (1 hour). Sessions older than this
                will be removed from storage.
        
        Returns:
            int: Number of sessions that were cleaned up
            
        Raises:
            ValueError: If max_age_seconds is not positive
            StorageError: If unable to perform cleanup operations
        
        Example:
            ```python
            # Clean up sessions older than 1 hour (default)
            cleaned_count = await service.cleanup_expired_sessions()
            print(f"Cleaned up {cleaned_count} expired sessions")
            
            # Clean up sessions older than 30 minutes
            cleaned_count = await service.cleanup_expired_sessions(1800)
            ```
        """
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        
        return await self.storage.cleanup_expired_sessions(max_age_seconds)
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get session management statistics and service health information.
        
        Provides comprehensive statistics about the session management
        service, including active session count, storage backend statistics,
        and service status. This is useful for monitoring and debugging.
        
        Returns:
            Dict[str, Any]: Dictionary containing session statistics with keys:
                - active_sessions_count: Number of currently active sessions
                - storage_stats: Statistics from the storage backend
                - service_status: Current service status ("running" or "stopped")
                
        Raises:
            StorageError: If unable to retrieve statistics from the backend
        
        Example:
            ```python
            # Get service statistics
            stats = await service.get_session_stats()
            print(f"Active sessions: {stats['active_sessions_count']}")
            print(f"Service status: {stats['service_status']}")
            print(f"Storage stats: {stats['storage_stats']}")
            ```
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
        
        Performs comprehensive validation of a session to determine if it
        can be resumed. Checks for session existence, status validity,
        and expiration. Returns detailed validation results including
        the reason for any validation failures.
        
        Args:
            conversation_id: Unique conversation identifier to validate
        
        Returns:
            Dict[str, Any]: Validation result dictionary with keys:
                - valid: Boolean indicating if session is valid for resumption
                - reason: Human-readable reason for validation result
                - can_resume: Boolean indicating if session can be resumed
                - resume_count: Number of times session has been resumed (if valid)
                - last_activity: ISO format timestamp of last activity (if valid)
                
        Raises:
            ValueError: If conversation_id is empty or invalid
            StorageError: If unable to retrieve session for validation
        
        Example:
            ```python
            # Validate a session
            validation = await service.validate_session("call_123")
            
            if validation["valid"]:
                print(f"Session can be resumed (count: {validation['resume_count']})")
                print(f"Last activity: {validation['last_activity']}")
            else:
                print(f"Session cannot be resumed: {validation['reason']}")
            ```
        """
        if not conversation_id or not isinstance(conversation_id, str):
            raise ValueError("conversation_id must be a non-empty string")
        
        session_state = await self.get_session(conversation_id, update_activity=False)
        
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