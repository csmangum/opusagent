"""
Example demonstrating concurrent execution of FSA task agents alongside conversation flow.

This example shows how to:
1. Define states for a structured task (in this case, a simple account balance check)
2. Execute the task concurrently with the main conversation
3. Retrieve results from the task while continuing the conversation
"""

import asyncio
import logging
import uuid
from typing import Dict, Any

from opusagent.fsa.executor import fsm_executor
from opusagent.fsa.states import FSAState
from opusagent.config.constants import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)

# Define some example states for a banking task
class BalanceCheckInitialState(FSAState):
    """Initial state for balance check task."""
    
    def __init__(self):
        super().__init__(
            name="balance_check_initial",
            description="Initiates the balance check process"
        )
    
    async def process(self, input_text: str, context: Dict[str, Any]):
        """Process the state and transition to authentication."""
        response = "Starting account balance check process."
        
        # Update context with task info
        context["task_type"] = "balance_check"
        context["started_at"] = asyncio.get_event_loop().time()
        
        # Simulate some processing time
        await asyncio.sleep(0.5)
        
        return response, "balance_check_auth", context

class BalanceCheckAuthState(FSAState):
    """Authentication state for balance check task."""
    
    def __init__(self):
        super().__init__(
            name="balance_check_auth",
            description="Authenticates the user for balance check"
        )
    
    async def process(self, input_text: str, context: Dict[str, Any]):
        """Process the state and perform authentication."""
        response = "Authenticating user for account balance check."
        
        # Simulate authentication process
        await asyncio.sleep(1.5)
        
        # Update context with auth status
        context["authenticated"] = True
        context["auth_method"] = "voice_biometrics"
        
        return response, "balance_check_query", context

class BalanceCheckQueryState(FSAState):
    """Query state for balance check task."""
    
    def __init__(self):
        super().__init__(
            name="balance_check_query",
            description="Queries the account balance"
        )
    
    async def process(self, input_text: str, context: Dict[str, Any]):
        """Process the state and query account balance."""
        response = "Querying account balance from banking system."
        
        # Simulate API call to banking system
        await asyncio.sleep(2.0)
        
        # Update context with balance info
        context["account_balance"] = 1250.75
        context["currency"] = "USD"
        context["query_timestamp"] = asyncio.get_event_loop().time()
        
        return response, "balance_check_result", context

class BalanceCheckResultState(FSAState):
    """Result state for balance check task."""
    
    def __init__(self):
        super().__init__(
            name="balance_check_result",
            description="Returns the account balance result"
        )
    
    async def process(self, input_text: str, context: Dict[str, Any]):
        """Process the state and format the balance result."""
        # Format the balance result
        balance = context.get("account_balance")
        currency = context.get("currency", "USD")
        
        response = f"The current balance is {currency} {balance:.2f}."
        
        # Calculate task duration
        start_time = context.get("started_at", 0)
        end_time = asyncio.get_event_loop().time()
        context["task_duration"] = end_time - start_time
        
        # This is a terminal state, so return the same state name
        return response, "balance_check_result", context


async def demonstrate_concurrent_execution():
    """Demonstrate concurrent execution of an FSA task while conversation continues."""
    
    # Create a unique conversation ID
    conversation_id = f"demo_{uuid.uuid4().hex[:8]}"
    
    print(f"Starting demonstration with conversation ID: {conversation_id}")
    
    # Create a state map for the balance check task
    balance_check_states = {
        "balance_check_initial": BalanceCheckInitialState(),
        "balance_check_auth": BalanceCheckAuthState(),
        "balance_check_query": BalanceCheckQueryState(),
        "balance_check_result": BalanceCheckResultState()
    }
    
    # Initial context for the task
    task_context = {
        "user_id": "demo_user_123",
        "account_number": "********5678",  # Masked for security
        "task_initiated_by": "voice_command"
    }
    
    # Submit the balance check task for concurrent execution
    print("\n[Main conversation] User: Can you check my account balance?")
    print("[Main conversation] Bot: I'll check your account balance right away. What else can I help you with?")
    
    # Start the task in the background
    task_id = fsm_executor.submit_fsm_task(
        conversation_id=conversation_id,
        initial_state="balance_check_initial",
        state_map=balance_check_states,
        context=task_context,
        task_name="balance_check"
    )
    
    print(f"\n[Background] Started balance check task with ID: {task_id}")
    
    # Continue the conversation while the task is running
    print("\n[Main conversation] User: I also need to know about upcoming payments.")
    print("[Main conversation] Bot: Sure, you have a payment of $250 scheduled for next Tuesday.")
    
    # Check task status
    await asyncio.sleep(1.0)  # Give the task time to progress
    status = fsm_executor.get_task_status(task_id)
    print(f"\n[Background] Task status after 1 second: {status['status']}")
    
    # Continue conversation
    print("\n[Main conversation] User: Thanks. Do I have enough to cover that?")
    print("[Main conversation] Bot: Let me check if the balance check is complete...")
    
    # Wait for task completion (in a real system, you'd poll or use callbacks)
    retries = 0
    max_retries = 10
    while retries < max_retries:
        status = fsm_executor.get_task_status(task_id)
        if status['status'] == 'completed' or status['status'] == 'failed':
            break
        await asyncio.sleep(0.5)
        retries += 1
    
    # Get task result if available
    try:
        result = fsm_executor.get_task_result(task_id)
        print(f"\n[Background] Task completed with result: {result}")
        
        # Use the task result in the conversation
        balance = result.get('context', {}).get('account_balance', 0)
        currency = result.get('context', {}).get('currency', 'USD')
        
        print(f"\n[Main conversation] Bot: Yes, your current balance is {currency} {balance:.2f}, which is sufficient to cover the $250 payment.")
        
        # Show task performance
        duration = result.get('context', {}).get('task_duration', 0)
        print(f"\n[Background] Task completed in {duration:.2f} seconds")
        
    except Exception as e:
        print(f"\n[Background] Could not retrieve task result: {e}")
        print("\n[Main conversation] Bot: I'm still working on retrieving your balance. I'll let you know once I have it.")
    
    # Clean up resources
    cleaned = fsm_executor.cleanup_conversation_tasks(conversation_id)
    print(f"\n[Background] Cleaned up {len(cleaned)} tasks for conversation {conversation_id}")


if __name__ == "__main__":
    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the demonstration
    asyncio.run(demonstrate_concurrent_execution()) 