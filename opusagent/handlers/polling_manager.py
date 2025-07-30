"""
Configurable polling system with callback support.

This module provides a centralized polling management system that supports
registering multiple polling tasks with configurable intervals and conditions.
It enables reactive monitoring and health checking across the OpusAgent system.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor


class PollingStatus(Enum):
    """Status of a polling task."""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class PollingTask:
    """Configuration for a polling task."""
    name: str
    callback: Callable
    interval: float
    condition: Optional[Callable[[], bool]] = None
    max_errors: int = 3
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Runtime state
    status: PollingStatus = field(default=PollingStatus.STOPPED, init=False)
    error_count: int = field(default=0, init=False)
    last_run: Optional[datetime] = field(default=None, init=False)
    last_error: Optional[str] = field(default=None, init=False)
    task: Optional[asyncio.Task] = field(default=None, init=False, repr=False)


class PollingManager:
    """
    Centralized polling management system with callback support.
    
    This class provides a comprehensive polling system that supports:
    - Multiple concurrent polling tasks with different intervals
    - Conditional polling based on runtime conditions
    - Error handling and automatic retry logic
    - Task lifecycle management (start, stop, pause, resume)
    - Performance monitoring and statistics
    - Thread pool support for CPU-intensive callbacks
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None, max_workers: int = 4):
        """Initialize the polling manager."""
        self.logger = logger or logging.getLogger(__name__)
        self._tasks: Dict[str, PollingTask] = {}
        self._shutdown = False
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="polling")
        
    def register_polling_task(
        self,
        name: str,
        callback: Callable,
        interval: float,
        condition: Optional[Callable[[], bool]] = None,
        max_errors: int = 3,
        timeout: Optional[float] = None,
        auto_start: bool = True,
        **metadata
    ) -> PollingTask:
        """
        Register a new polling task.
        
        Args:
            name: Unique name for the polling task
            callback: Function to call on each poll (sync or async)
            interval: Polling interval in seconds
            condition: Optional condition function that must return True for polling to continue
            max_errors: Maximum consecutive errors before stopping the task
            timeout: Optional timeout for each callback execution
            auto_start: Whether to start the task immediately
            **metadata: Additional metadata for the task
            
        Returns:
            PollingTask: The created polling task
            
        Example:
            ```python
            # Register a health check
            def check_database():
                # Check database connectivity
                return {"status": "healthy", "latency": 0.1}
            
            polling_manager.register_polling_task(
                name="db_health_check",
                callback=check_database,
                interval=30.0,  # 30 seconds
                condition=lambda: config.monitoring_enabled,
                service="database"
            )
            ```
        """
        if name in self._tasks:
            raise ValueError(f"Polling task '{name}' already exists")
        
        task = PollingTask(
            name=name,
            callback=callback,
            interval=interval,
            condition=condition,
            max_errors=max_errors,
            timeout=timeout,
            metadata=metadata
        )
        
        self._tasks[name] = task
        self.logger.debug(f"Registered polling task: {name} (interval: {interval}s)")
        
        if auto_start:
            self.start_task(name)
            
        return task
    
    def start_task(self, name: str) -> bool:
        """
        Start a polling task.
        
        Args:
            name: Name of the task to start
            
        Returns:
            bool: True if task was started successfully
        """
        if name not in self._tasks:
            self.logger.error(f"Polling task '{name}' not found")
            return False
        
        task = self._tasks[name]
        if task.status == PollingStatus.RUNNING:
            self.logger.warning(f"Polling task '{name}' is already running")
            return True
        
        # Cancel existing task if any
        if task.task and not task.task.done():
            task.task.cancel()
        
        # Start new task
        task.task = asyncio.create_task(self._polling_loop(task))
        task.status = PollingStatus.RUNNING
        task.error_count = 0
        
        self.logger.info(f"Started polling task: {name}")
        return True
    
    def stop_task(self, name: str) -> bool:
        """
        Stop a polling task.
        
        Args:
            name: Name of the task to stop
            
        Returns:
            bool: True if task was stopped successfully
        """
        if name not in self._tasks:
            self.logger.error(f"Polling task '{name}' not found")
            return False
        
        task = self._tasks[name]
        if task.task and not task.task.done():
            task.task.cancel()
        
        task.status = PollingStatus.STOPPED
        self.logger.info(f"Stopped polling task: {name}")
        return True
    
    def pause_task(self, name: str) -> bool:
        """
        Pause a polling task.
        
        Args:
            name: Name of the task to pause
            
        Returns:
            bool: True if task was paused successfully
        """
        if name not in self._tasks:
            self.logger.error(f"Polling task '{name}' not found")
            return False
        
        task = self._tasks[name]
        if task.status == PollingStatus.RUNNING:
            task.status = PollingStatus.PAUSED
            self.logger.info(f"Paused polling task: {name}")
            return True
        
        return False
    
    def resume_task(self, name: str) -> bool:
        """
        Resume a paused polling task.
        
        Args:
            name: Name of the task to resume
            
        Returns:
            bool: True if task was resumed successfully
        """
        if name not in self._tasks:
            self.logger.error(f"Polling task '{name}' not found")
            return False
        
        task = self._tasks[name]
        if task.status == PollingStatus.PAUSED:
            task.status = PollingStatus.RUNNING
            self.logger.info(f"Resumed polling task: {name}")
            return True
        
        return False
    
    def update_interval(self, name: str, new_interval: float) -> bool:
        """
        Update the interval of a polling task.
        
        Args:
            name: Name of the task to update
            new_interval: New polling interval in seconds
            
        Returns:
            bool: True if interval was updated successfully
        """
        if name not in self._tasks:
            self.logger.error(f"Polling task '{name}' not found")
            return False
        
        task = self._tasks[name]
        old_interval = task.interval
        task.interval = new_interval
        
        self.logger.info(f"Updated polling interval for '{name}': {old_interval}s -> {new_interval}s")
        return True
    
    def unregister_task(self, name: str) -> bool:
        """
        Unregister and stop a polling task.
        
        Args:
            name: Name of the task to unregister
            
        Returns:
            bool: True if task was unregistered successfully
        """
        if name not in self._tasks:
            return False
        
        self.stop_task(name)
        del self._tasks[name]
        self.logger.info(f"Unregistered polling task: {name}")
        return True
    
    async def _polling_loop(self, task: PollingTask) -> None:
        """Main polling loop for a task."""
        while not self._shutdown and task.status in [PollingStatus.RUNNING, PollingStatus.PAUSED]:
            try:
                # Check if task is paused
                if task.status == PollingStatus.PAUSED:
                    await asyncio.sleep(1.0)  # Short sleep when paused
                    continue
                
                # Check condition if provided
                if task.condition and not task.condition():
                    await asyncio.sleep(task.interval)
                    continue
                
                # Execute callback
                start_time = time.time()
                
                try:
                    if asyncio.iscoroutinefunction(task.callback):
                        if task.timeout:
                            await asyncio.wait_for(task.callback(), timeout=task.timeout)
                        else:
                            await task.callback()
                    else:
                        # Run sync callback in thread pool
                        if task.timeout:
                            await asyncio.wait_for(
                                asyncio.get_event_loop().run_in_executor(
                                    self._executor, task.callback
                                ),
                                timeout=task.timeout
                            )
                        else:
                            await asyncio.get_event_loop().run_in_executor(
                                self._executor, task.callback
                            )
                    
                    # Reset error count on success
                    task.error_count = 0
                    task.last_error = None
                    
                except Exception as e:
                    task.error_count += 1
                    task.last_error = str(e)
                    
                    self.logger.error(
                        f"Error in polling task '{task.name}' (attempt {task.error_count}/{task.max_errors}): {e}"
                    )
                    
                    if task.error_count >= task.max_errors:
                        task.status = PollingStatus.ERROR
                        self.logger.error(f"Polling task '{task.name}' stopped due to too many errors")
                        break
                
                task.last_run = datetime.now()
                
                # Calculate actual sleep time accounting for execution time
                execution_time = time.time() - start_time
                sleep_time = max(0, task.interval - execution_time)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in polling loop for '{task.name}': {e}")
                await asyncio.sleep(task.interval)
    
    def get_task_status(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get status information for a polling task.
        
        Args:
            name: Name of the task
            
        Returns:
            Optional[Dict]: Task status information or None if not found
        """
        if name not in self._tasks:
            return None
        
        task = self._tasks[name]
        return {
            "name": task.name,
            "status": task.status.value,
            "interval": task.interval,
            "error_count": task.error_count,
            "max_errors": task.max_errors,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "last_error": task.last_error,
            "has_condition": task.condition is not None,
            "timeout": task.timeout,
            "metadata": task.metadata
        }
    
    def get_all_tasks_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status information for all registered tasks."""
        return {name: self.get_task_status(name) for name in self._tasks.keys()}
    
    def start_all_tasks(self) -> None:
        """Start all registered tasks."""
        for name in self._tasks.keys():
            self.start_task(name)
    
    def stop_all_tasks(self) -> None:
        """Stop all running tasks."""
        for name in self._tasks.keys():
            self.stop_task(name)
    
    async def shutdown(self) -> None:
        """Shutdown the polling manager and clean up resources."""
        self.logger.info("Shutting down polling manager")
        self._shutdown = True
        
        # Cancel all tasks
        for task in self._tasks.values():
            if task.task and not task.task.done():
                task.task.cancel()
        
        # Wait for all tasks to complete
        running_tasks = [task.task for task in self._tasks.values() if task.task and not task.task.done()]
        if running_tasks:
            await asyncio.gather(*running_tasks, return_exceptions=True)
        
        # Shutdown thread pool
        self._executor.shutdown(wait=True)
        
        self.logger.info("Polling manager shutdown complete")


# Global polling manager instance
_global_polling_manager: Optional[PollingManager] = None


def get_polling_manager() -> PollingManager:
    """Get the global polling manager instance."""
    global _global_polling_manager
    if _global_polling_manager is None:
        _global_polling_manager = PollingManager()
    return _global_polling_manager


def register_polling_task(
    name: str,
    callback: Callable,
    interval: float,
    condition: Optional[Callable[[], bool]] = None,
    max_errors: int = 3,
    timeout: Optional[float] = None,
    auto_start: bool = True,
    **metadata
) -> PollingTask:
    """Register a polling task on the global polling manager."""
    return get_polling_manager().register_polling_task(
        name, callback, interval, condition, max_errors, timeout, auto_start, **metadata
    )


def start_polling_task(name: str) -> bool:
    """Start a polling task on the global polling manager."""
    return get_polling_manager().start_task(name)


def stop_polling_task(name: str) -> bool:
    """Stop a polling task on the global polling manager."""
    return get_polling_manager().stop_task(name)