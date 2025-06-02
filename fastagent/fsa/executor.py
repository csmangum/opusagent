"""
FSA Executor for concurrent task processing.

This module integrates the ConcurrentExecutor service with the FSA architecture
to enable parallel execution of FSM-based task agents alongside the main conversation flow.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Type

from fastagent.fsa.states import FSAState, StateManager
from fastagent.config.constants import LOGGER_NAME
from fastagent.services.concurrent_executor import executor

logger = logging.getLogger(LOGGER_NAME)

class FSAExecutor:
    """
    Manages the concurrent execution of FSA-based agents for structured tasks.
    
    This class provides an interface for:
    - Starting FSM agents as background tasks
    - Monitoring task progress
    - Retrieving results from completed tasks
    - Managing the lifecycle of concurrent FSM agents
    """
    
    def __init__(self):
        self.executor = executor
        self.state_managers: Dict[str, StateManager] = {}
    
    async def execute_fsm(self, 
                         task_id: str, 
                         initial_state: str,
                         state_map: Dict[str, FSAState],
                         context: Dict[str, Any],
                         first_input: str = None,
                         timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Execute an FSM workflow from start to completion.
        
        Args:
            task_id: Unique identifier for the task
            initial_state: Name of the initial state
            state_map: Dictionary mapping state names to state objects
            context: Initial context for the FSM
            first_input: Optional first input to process
            timeout: Optional timeout in seconds
            
        Returns:
            Dictionary containing the final state and context
        """
        # Create a state manager for this task
        state_manager = StateManager(initial_state)
        state_manager.register_states(state_map)
        self.state_managers[task_id] = state_manager
        
        current_state = initial_state
        current_context = context.copy()
        current_input = first_input
        
        try:
            # Main FSM execution loop
            while True:
                # Process the current state
                if current_input:
                    response, next_state, updated_context = await state_manager.process_input(
                        current_state, current_input, current_context
                    )
                else:
                    # If no input, just run the state's process method with empty input
                    response, next_state, updated_context = await state_manager.process_input(
                        current_state, "", current_context
                    )
                
                # Update tracking variables
                current_context = updated_context
                
                # Log state transition
                logger.info(f"Task {task_id}: State transition {current_state} -> {next_state}")
                
                # Check if we've reached a terminal state
                if next_state == current_state or next_state is None:
                    logger.info(f"Task {task_id}: Reached terminal state {current_state}")
                    break
                
                current_state = next_state
                current_input = None  # Only use first_input for the first state
            
            # Return the final results
            return {
                "task_id": task_id,
                "final_state": current_state,
                "context": current_context,
                "response": response,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Error executing FSM task {task_id}: {str(e)}", exc_info=True)
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(e)
            }
        finally:
            # Clean up the state manager
            if task_id in self.state_managers:
                del self.state_managers[task_id]
    
    def submit_fsm_task(self,
                       conversation_id: str,
                       initial_state: str,
                       state_map: Dict[str, FSAState],
                       context: Dict[str, Any],
                       first_input: str = None,
                       task_name: str = None,
                       timeout: Optional[float] = None) -> str:
        """
        Submit an FSM workflow for concurrent execution.
        
        Args:
            conversation_id: ID of the conversation
            initial_state: Name of the initial state
            state_map: Dictionary mapping state names to state objects
            context: Initial context for the FSM
            first_input: Optional first input to process
            task_name: Optional descriptive name for the task
            timeout: Optional timeout in seconds
            
        Returns:
            task_id: Unique identifier for the submitted task
        """
        # Generate a unique task ID
        task_name_part = task_name or "fsm_task"
        task_id = f"{conversation_id}:{task_name_part}_{uuid.uuid4().hex[:8]}"
        
        # Submit the task for execution
        self.executor.submit_task(
            task_id=task_id,
            coro=self.execute_fsm(
                task_id=task_id,
                initial_state=initial_state,
                state_map=state_map,
                context=context,
                first_input=first_input,
                timeout=timeout
            ),
            timeout=timeout
        )
        
        logger.info(f"Submitted FSM task {task_id} for concurrent execution")
        return task_id
    
    def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """
        Get the result of a completed FSM task.
        
        Args:
            task_id: Unique identifier for the task
            
        Returns:
            Result of the FSM task execution
            
        Raises:
            KeyError: If task result doesn't exist
            Exception: If task failed with an error
        """
        return self.executor.get_task_result(task_id)
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the current status of an FSM task.
        
        Args:
            task_id: Unique identifier for the task
            
        Returns:
            Dict with task status information
        """
        return self.executor.get_task_status(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running FSM task.
        
        Args:
            task_id: Unique identifier for the task
            
        Returns:
            bool: True if task was cancelled, False otherwise
        """
        return self.executor.cancel_task(task_id)
    
    def cleanup_conversation_tasks(self, conversation_id: str) -> List[str]:
        """
        Clean up all FSM tasks for a specific conversation.
        
        Args:
            conversation_id: Conversation ID to clean up tasks for
            
        Returns:
            List of task IDs that were cleaned up
        """
        return self.executor.cleanup(conversation_id)

# Create a singleton instance
fsm_executor = FSAExecutor() 