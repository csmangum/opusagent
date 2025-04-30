"""
Concurrent Execution Service for FastAgent.

This module provides functionality for executing FSM agent tasks concurrently with
the main conversation flow, allowing tasks to be processed in parallel without
interrupting the natural conversation experience.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, Coroutine

from fastagent.config.constants import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)

# Type variable for task results
T = TypeVar('T')

class ConcurrentExecutor:
    """
    Manages concurrent execution of FSM agent tasks alongside the main conversation flow.
    
    This class provides the infrastructure to:
    - Submit background tasks that run concurrently with the main conversation
    - Track task status and completion
    - Handle results and errors from concurrent tasks
    - Ensure proper cleanup of abandoned tasks
    """
    
    def __init__(self):
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.task_results: Dict[str, Any] = {}
        self.task_errors: Dict[str, Exception] = {}
    
    async def execute_task(self, 
                          task_id: str, 
                          coro: Coroutine,
                          timeout: Optional[float] = None) -> None:
        """
        Execute a coroutine as a background task with proper error handling.
        
        Args:
            task_id: Unique identifier for the task
            coro: Coroutine to be executed
            timeout: Optional timeout in seconds
        """
        try:
            if timeout:
                result = await asyncio.wait_for(coro, timeout=timeout)
            else:
                result = await coro
            
            self.task_results[task_id] = result
            logger.info(f"Task {task_id} completed successfully")
        except asyncio.TimeoutError:
            logger.warning(f"Task {task_id} timed out after {timeout} seconds")
            self.task_errors[task_id] = asyncio.TimeoutError(f"Task timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"Error in task {task_id}: {str(e)}", exc_info=True)
            self.task_errors[task_id] = e
        finally:
            # Remove the task from active_tasks when done
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    def submit_task(self, 
                   task_id: str, 
                   coro: Coroutine, 
                   timeout: Optional[float] = None) -> asyncio.Task:
        """
        Submit a task for concurrent execution.
        
        Args:
            task_id: Unique identifier for the task
            coro: Coroutine to be executed
            timeout: Optional timeout in seconds
            
        Returns:
            asyncio.Task: The created task
        """
        # Create and store the task
        task = asyncio.create_task(self.execute_task(task_id, coro, timeout))
        self.active_tasks[task_id] = task
        logger.info(f"Submitted task {task_id} for concurrent execution")
        return task
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the current status of a task.
        
        Args:
            task_id: Unique identifier for the task
            
        Returns:
            Dict with task status information
        """
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            return {
                "task_id": task_id,
                "status": "running",
                "done": task.done(),
                "cancelled": task.cancelled()
            }
        elif task_id in self.task_results:
            return {
                "task_id": task_id,
                "status": "completed",
                "result": "available"
            }
        elif task_id in self.task_errors:
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(self.task_errors[task_id])
            }
        else:
            return {
                "task_id": task_id,
                "status": "not_found"
            }
    
    def get_task_result(self, task_id: str) -> Any:
        """
        Get the result of a completed task.
        
        Args:
            task_id: Unique identifier for the task
            
        Returns:
            Result of the task
            
        Raises:
            KeyError: If task result doesn't exist
            Exception: If task failed with an error
        """
        if task_id in self.task_errors:
            raise self.task_errors[task_id]
        
        if task_id in self.task_results:
            return self.task_results[task_id]
        
        raise KeyError(f"No result found for task {task_id}")
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: Unique identifier for the task
            
        Returns:
            bool: True if task was cancelled, False otherwise
        """
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            if not task.done():
                task.cancel()
                logger.info(f"Task {task_id} cancelled")
                return True
        
        logger.warning(f"Could not cancel task {task_id}: not found or already completed")
        return False
    
    def cleanup(self, conversation_id: str = None) -> List[str]:
        """
        Clean up all tasks or tasks for a specific conversation.
        
        Args:
            conversation_id: Optional conversation ID to clean up tasks for
            
        Returns:
            List of task IDs that were cleaned up
        """
        cleaned_tasks = []
        
        # If conversation_id is provided, clean up tasks for that conversation only
        if conversation_id:
            task_ids_to_clean = [
                task_id for task_id in self.active_tasks.keys() 
                if task_id.startswith(f"{conversation_id}:")
            ]
        else:
            task_ids_to_clean = list(self.active_tasks.keys())
        
        # Cancel all active tasks
        for task_id in task_ids_to_clean:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                if not task.done():
                    task.cancel()
                
                del self.active_tasks[task_id]
                cleaned_tasks.append(task_id)
                logger.info(f"Cleaned up task {task_id}")
        
        # Clean up results and errors
        for task_id in list(self.task_results.keys()):
            if conversation_id and task_id.startswith(f"{conversation_id}:"):
                del self.task_results[task_id]
                cleaned_tasks.append(task_id)
        
        for task_id in list(self.task_errors.keys()):
            if conversation_id and task_id.startswith(f"{conversation_id}:"):
                del self.task_errors[task_id]
                cleaned_tasks.append(task_id)
        
        return cleaned_tasks

# Create a singleton instance
executor = ConcurrentExecutor() 