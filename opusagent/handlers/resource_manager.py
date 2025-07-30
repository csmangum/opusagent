"""
Simplified resource cleanup management system.

This module provides a lightweight resource management system that ensures
proper LIFO cleanup of resources like WebSocket connections and audio streams.
"""

import asyncio
import atexit
import logging
import signal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ResourceType(Enum):
    """Types of resources that can be managed."""
    WEBSOCKET = "websocket"
    AUDIO = "audio"
    SESSION = "session"
    FILE = "file"
    NETWORK = "network"
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
    registered_at: datetime = field(default_factory=datetime.now)


class ResourceManager:
    """
    Simplified resource management system with cleanup callbacks.
    
    Provides LIFO cleanup with priority support for proper resource deallocation.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the resource manager."""
        self.logger = logger or logging.getLogger(__name__)
        self._cleanup_callbacks: List[CleanupCallback] = []
        self._cleanup_in_progress = False
        self._shutdown_registered = False
        
        # Register shutdown cleanup
        self._register_shutdown_cleanup()
    
    def register_cleanup(
        self,
        callback: Callable,
        resource_type: ResourceType = ResourceType.OTHER,
        priority: CleanupPriority = CleanupPriority.NORMAL,
        description: str = "Unknown resource"
    ) -> str:
        """
        Register a cleanup callback for a resource.
        
        Args:
            callback: Function to call for cleanup (sync or async)
            resource_type: Type of resource being managed
            priority: Cleanup priority level
            description: Human-readable description of the resource
            
        Returns:
            str: Unique identifier for the registered cleanup callback
        """
        cleanup_callback = CleanupCallback(
            callback=callback,
            resource_type=resource_type,
            priority=priority,
            description=description
        )
        
        self._cleanup_callbacks.append(cleanup_callback)
        cleanup_id = f"{resource_type.value}_{len(self._cleanup_callbacks)}_{id(callback)}"
        
        self.logger.debug(f"Registered cleanup: {description} ({resource_type.value}, priority: {priority.name})")
        return cleanup_id
    
    async def cleanup_by_type(self, resource_type: ResourceType) -> int:
        """
        Clean up all resources of a specific type.
        
        Args:
            resource_type: Type of resources to clean up
            
        Returns:
            int: Number of resources cleaned up
        """
        callbacks_to_cleanup = [cb for cb in self._cleanup_callbacks if cb.resource_type == resource_type]
        
        # Sort by priority (highest first) and reverse order (LIFO)
        callbacks_to_cleanup.sort(key=lambda x: (x.priority.value, x.registered_at), reverse=True)
        
        cleaned_count = 0
        for callback in callbacks_to_cleanup:
            try:
                await self._execute_callback(callback)
                self._cleanup_callbacks.remove(callback)
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
            
            self.logger.info(f"Cleanup complete: {cleaned_count} successful, {failed_count} failed")
            return cleaned_count
            
        finally:
            self._cleanup_in_progress = False
    
    async def _execute_callback(self, callback: CleanupCallback) -> None:
        """Execute a single cleanup callback."""
        self.logger.debug(f"Executing cleanup: {callback.description}")
        
        if asyncio.iscoroutinefunction(callback.callback):
            await callback.callback()
        else:
            callback.callback()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about registered resources."""
        stats = {
            "total_callbacks": len(self._cleanup_callbacks),
            "by_type": {},
            "by_priority": {},
            "cleanup_in_progress": self._cleanup_in_progress
        }
        
        # Count by type and priority
        for callback in self._cleanup_callbacks:
            resource_type = callback.resource_type.value
            priority = callback.priority.name
            stats["by_type"][resource_type] = stats["by_type"].get(resource_type, 0) + 1
            stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1
        
        return stats
    
    def _register_shutdown_cleanup(self) -> None:
        """Register cleanup for normal shutdown and signal handling."""
        if self._shutdown_registered:
            return
        
        # Register atexit handler
        atexit.register(self._sync_cleanup_all)
        
        # Register signal handlers for graceful shutdown
        try:
            for sig in [signal.SIGTERM, signal.SIGINT]:
                signal.signal(sig, self._signal_handler)
        except (AttributeError, ValueError):
            # Signal handling not available (e.g., on Windows or in threads)
            pass
        
        self._shutdown_registered = True
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating cleanup")
        try:
            loop = asyncio.get_running_loop()
            
            # Use run_coroutine_threadsafe which properly handles cross-thread execution
            import concurrent.futures
            future = asyncio.run_coroutine_threadsafe(self.cleanup_all(force=True), loop)
            
            try:
                # Wait for completion with a reasonable timeout
                # This blocks the signal handler until cleanup is complete
                future.result(timeout=10.0)
                self.logger.info("Signal cleanup completed successfully")
            except concurrent.futures.TimeoutError:
                self.logger.warning("Cleanup task timed out during signal handling")
                future.cancel()
            except Exception as e:
                self.logger.error(f"Error during signal cleanup: {e}")
                
        except RuntimeError:
            # No event loop running
            self._sync_cleanup_all()
    
    def _sync_cleanup_all(self) -> None:
        """Synchronous cleanup for atexit handler."""
        try:
            # Try to use running event loop
            loop = asyncio.get_running_loop()
            if loop and not loop.is_closed():
                # Use run_coroutine_threadsafe to properly wait for completion
                import concurrent.futures
                future = asyncio.run_coroutine_threadsafe(self.cleanup_all(force=True), loop)
                try:
                    # Wait for completion with timeout
                    future.result(timeout=10.0)
                except concurrent.futures.TimeoutError:
                    self.logger.warning("Cleanup task timed out during atexit")
                    future.cancel()
                except Exception as e:
                    self.logger.error(f"Error during atexit cleanup: {e}")
        except RuntimeError:
            # No event loop running, execute sync callbacks only
            for callback in reversed(self._cleanup_callbacks):
                if not asyncio.iscoroutinefunction(callback.callback):
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
    description: str = "Unknown resource"
) -> str:
    """Register a cleanup callback on the global resource manager."""
    return get_resource_manager().register_cleanup(callback, resource_type, priority, description)


async def cleanup_all() -> int:
    """Clean up all resources using the global resource manager."""
    return await get_resource_manager().cleanup_all()


async def cleanup_by_type(resource_type: ResourceType) -> int:
    """Clean up resources by type using the global resource manager."""
    return await get_resource_manager().cleanup_by_type(resource_type)