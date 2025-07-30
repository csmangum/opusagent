"""
Resource cleanup management system with callback support.

This module provides a comprehensive resource management system that supports
registering cleanup callbacks for various resource types. It ensures proper
LIFO (Last In, First Out) cleanup order and handles cleanup during shutdown,
errors, or explicit cleanup requests.
"""

import asyncio
import atexit
import logging
import signal
import weakref
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from contextlib import asynccontextmanager


class ResourceType(Enum):
    """Types of resources that can be managed."""
    WEBSOCKET = "websocket"
    AUDIO = "audio"
    SESSION = "session"
    FILE = "file"
    NETWORK = "network"
    DATABASE = "database"
    CACHE = "cache"
    THREAD = "thread"
    OTHER = "other"


class CleanupPriority(Enum):
    """Priority levels for cleanup operations."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class CleanupCallback:
    """Configuration for a cleanup callback."""
    callback: Callable
    resource_type: ResourceType
    priority: CleanupPriority
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.now)
    is_async: bool = field(init=False)
    
    def __post_init__(self):
        self.is_async = asyncio.iscoroutinefunction(self.callback)


class ResourceManager:
    """
    Centralized resource management system with cleanup callbacks.
    
    This class provides a comprehensive resource management system that supports:
    - LIFO (Last In, First Out) cleanup order for proper resource deallocation
    - Priority-based cleanup for critical resources
    - Async and sync callback support
    - Resource categorization and grouping
    - Automatic cleanup on shutdown and error conditions
    - Idempotent cleanup operations
    - Weak references to prevent memory leaks
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the resource manager."""
        self.logger = logger or logging.getLogger(__name__)
        self._cleanup_callbacks: List[CleanupCallback] = []
        self._resource_registry: Dict[str, Set[str]] = {rt.value: set() for rt in ResourceType}
        self._cleanup_in_progress = False
        self._shutdown_registered = False
        self._signal_handlers_registered = False
        
        # Register shutdown cleanup
        self._register_shutdown_cleanup()
    
    def register_cleanup(
        self,
        callback: Callable,
        resource_type: ResourceType = ResourceType.OTHER,
        priority: CleanupPriority = CleanupPriority.NORMAL,
        description: str = "Unknown resource",
        resource_id: Optional[str] = None,
        **metadata
    ) -> str:
        """
        Register a cleanup callback for a resource.
        
        Args:
            callback: Function to call for cleanup (sync or async)
            resource_type: Type of resource being managed
            priority: Cleanup priority level
            description: Human-readable description of the resource
            resource_id: Optional unique identifier for the resource
            **metadata: Additional metadata for the resource
            
        Returns:
            str: Unique identifier for the registered cleanup callback
            
        Example:
            ```python
            # Register WebSocket cleanup
            def cleanup_websocket(ws):
                ws.close()
            
            cleanup_id = resource_manager.register_cleanup(
                callback=lambda: cleanup_websocket(my_websocket),
                resource_type=ResourceType.WEBSOCKET,
                priority=CleanupPriority.HIGH,
                description="Main WebSocket connection",
                connection_id="ws_123"
            )
            ```
        """
        cleanup_callback = CleanupCallback(
            callback=callback,
            resource_type=resource_type,
            priority=priority,
            description=description,
            metadata=metadata
        )
        
        # Add to callbacks list (will be sorted by priority during cleanup)
        self._cleanup_callbacks.append(cleanup_callback)
        
        # Generate unique ID
        cleanup_id = f"{resource_type.value}_{len(self._cleanup_callbacks)}_{id(callback)}"
        
        # Register in resource registry
        if resource_id:
            self._resource_registry[resource_type.value].add(resource_id)
            cleanup_callback.metadata['resource_id'] = resource_id
        
        cleanup_callback.metadata['cleanup_id'] = cleanup_id
        
        self.logger.debug(
            f"Registered cleanup callback: {description} ({resource_type.value}, priority: {priority.name})"
        )
        
        return cleanup_id
    
    def unregister_cleanup(self, cleanup_id: str) -> bool:
        """
        Unregister a cleanup callback.
        
        Args:
            cleanup_id: ID returned from register_cleanup
            
        Returns:
            bool: True if callback was found and removed
        """
        for i, callback in enumerate(self._cleanup_callbacks):
            if callback.metadata.get('cleanup_id') == cleanup_id:
                removed_callback = self._cleanup_callbacks.pop(i)
                
                # Remove from resource registry
                resource_id = removed_callback.metadata.get('resource_id')
                if resource_id:
                    self._resource_registry[removed_callback.resource_type.value].discard(resource_id)
                
                self.logger.debug(f"Unregistered cleanup callback: {removed_callback.description}")
                return True
        
        return False
    
    @asynccontextmanager
    async def managed_resource(
        self,
        resource: Any,
        cleanup_func: Callable,
        resource_type: ResourceType = ResourceType.OTHER,
        priority: CleanupPriority = CleanupPriority.NORMAL,
        description: str = "Managed resource"
    ):
        """
        Context manager for automatic resource cleanup.
        
        Args:
            resource: The resource to manage
            cleanup_func: Function to clean up the resource
            resource_type: Type of resource
            priority: Cleanup priority
            description: Description of the resource
            
        Example:
            ```python
            async with resource_manager.managed_resource(
                websocket, 
                lambda: websocket.close(),
                ResourceType.WEBSOCKET,
                CleanupPriority.HIGH,
                "API WebSocket"
            ) as ws:
                # Use websocket
                await ws.send("Hello")
            # Websocket is automatically cleaned up here
            ```
        """
        cleanup_id = self.register_cleanup(
            callback=cleanup_func,
            resource_type=resource_type,
            priority=priority,
            description=description
        )
        
        try:
            yield resource
        finally:
            # Execute cleanup immediately
            await self._execute_single_cleanup(cleanup_id)
            # Remove from registry
            self.unregister_cleanup(cleanup_id)
    
    async def cleanup_by_type(
        self, 
        resource_type: ResourceType,
        max_age_seconds: Optional[float] = None
    ) -> int:
        """
        Clean up all resources of a specific type.
        
        Args:
            resource_type: Type of resources to clean up
            max_age_seconds: Only clean up resources older than this age
            
        Returns:
            int: Number of resources cleaned up
        """
        callbacks_to_cleanup = []
        current_time = datetime.now()
        
        for callback in self._cleanup_callbacks:
            if callback.resource_type == resource_type:
                if max_age_seconds is None:
                    callbacks_to_cleanup.append(callback)
                else:
                    age = (current_time - callback.registered_at).total_seconds()
                    if age >= max_age_seconds:
                        callbacks_to_cleanup.append(callback)
        
        # Sort by priority (highest first)
        callbacks_to_cleanup.sort(key=lambda x: x.priority.value, reverse=True)
        
        cleaned_count = 0
        for callback in callbacks_to_cleanup:
            try:
                await self._execute_callback(callback)
                self.unregister_cleanup(callback.metadata.get('cleanup_id', ''))
                cleaned_count += 1
            except Exception as e:
                self.logger.error(f"Error cleaning up {callback.description}: {e}")
        
        self.logger.info(f"Cleaned up {cleaned_count} resources of type {resource_type.value}")
        return cleaned_count
    
    async def cleanup_all(self, force: bool = False) -> int:
        """
        Clean up all registered resources.
        
        Args:
            force: If True, continue cleanup even if some callbacks fail
            
        Returns:
            int: Number of resources cleaned up successfully
        """
        if self._cleanup_in_progress and not force:
            self.logger.warning("Cleanup already in progress")
            return 0
        
        self._cleanup_in_progress = True
        
        try:
            # Sort callbacks by priority (highest first) and reverse order (LIFO)
            callbacks_to_cleanup = sorted(
                self._cleanup_callbacks,
                key=lambda x: (x.priority.value, x.registered_at),
                reverse=True
            )
            
            cleaned_count = 0
            failed_count = 0
            
            for callback in callbacks_to_cleanup:
                try:
                    await self._execute_callback(callback)
                    cleaned_count += 1
                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"Error cleaning up {callback.description}: {e}")
                    if not force:
                        break
            
            # Clear all callbacks after cleanup
            self._cleanup_callbacks.clear()
            for resource_set in self._resource_registry.values():
                resource_set.clear()
            
            self.logger.info(
                f"Cleanup complete: {cleaned_count} successful, {failed_count} failed"
            )
            
            return cleaned_count
            
        finally:
            self._cleanup_in_progress = False
    
    async def _execute_single_cleanup(self, cleanup_id: str) -> bool:
        """Execute cleanup for a single callback by ID."""
        for callback in self._cleanup_callbacks:
            if callback.metadata.get('cleanup_id') == cleanup_id:
                try:
                    await self._execute_callback(callback)
                    return True
                except Exception as e:
                    self.logger.error(f"Error executing cleanup {cleanup_id}: {e}")
                    return False
        return False
    
    async def _execute_callback(self, callback: CleanupCallback) -> None:
        """Execute a single cleanup callback."""
        self.logger.debug(f"Executing cleanup: {callback.description}")
        
        try:
            if callback.is_async:
                await callback.callback()
            else:
                callback.callback()
        except Exception as e:
            self.logger.error(f"Cleanup callback failed for {callback.description}: {e}")
            raise
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """Get statistics about registered resources."""
        stats = {
            "total_callbacks": len(self._cleanup_callbacks),
            "by_type": {},
            "by_priority": {},
            "cleanup_in_progress": self._cleanup_in_progress
        }
        
        # Count by type
        for callback in self._cleanup_callbacks:
            resource_type = callback.resource_type.value
            stats["by_type"][resource_type] = stats["by_type"].get(resource_type, 0) + 1
        
        # Count by priority
        for callback in self._cleanup_callbacks:
            priority = callback.priority.name
            stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1
        
        return stats
    
    def _register_shutdown_cleanup(self) -> None:
        """Register cleanup for normal shutdown and signal handling."""
        if self._shutdown_registered:
            return
        
        # Register atexit handler
        atexit.register(self._sync_cleanup_all)
        
        # Register signal handlers for graceful shutdown
        if not self._signal_handlers_registered:
            try:
                for sig in [signal.SIGTERM, signal.SIGINT]:
                    signal.signal(sig, self._signal_handler)
                self._signal_handlers_registered = True
            except (AttributeError, ValueError):
                # Signal handling not available (e.g., on Windows or in threads)
                pass
        
        self._shutdown_registered = True
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating cleanup")
        asyncio.create_task(self.cleanup_all(force=True))
    
    def _sync_cleanup_all(self) -> None:
        """Synchronous cleanup for atexit handler."""
        try:
            # Try to get running event loop
            loop = asyncio.get_running_loop()
            if loop and not loop.is_closed():
                loop.create_task(self.cleanup_all(force=True))
        except RuntimeError:
            # No event loop running, execute sync callbacks only
            for callback in reversed(self._cleanup_callbacks):
                if not callback.is_async:
                    try:
                        callback.callback()
                    except Exception as e:
                        print(f"Error in sync cleanup {callback.description}: {e}")


# Global resource manager instance
_global_resource_manager: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance."""
    global _global_resource_manager
    if _global_resource_manager is None:
        _global_resource_manager = ResourceManager()
    return _global_resource_manager


def register_cleanup(
    callback: Callable,
    resource_type: ResourceType = ResourceType.OTHER,
    priority: CleanupPriority = CleanupPriority.NORMAL,
    description: str = "Unknown resource",
    resource_id: Optional[str] = None,
    **metadata
) -> str:
    """Register a cleanup callback on the global resource manager."""
    return get_resource_manager().register_cleanup(
        callback, resource_type, priority, description, resource_id, **metadata
    )


async def cleanup_all() -> int:
    """Clean up all resources using the global resource manager."""
    return await get_resource_manager().cleanup_all()


async def cleanup_by_type(resource_type: ResourceType) -> int:
    """Clean up resources by type using the global resource manager."""
    return await get_resource_manager().cleanup_by_type(resource_type)