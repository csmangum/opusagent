# Concurrent Execution Service

The Concurrent Execution Service enables FastAgent to run structured tasks in parallel with the main conversation flow, allowing for seamless multitasking without interrupting the user experience.

## Key Features

- **Parallel Processing**: Execute AFSM task agents in the background while the conversation continues
- **Task Management**: Track task progress, status, and results
- **Resource Cleanup**: Automatically clean up resources when conversations end
- **Error Handling**: Robust error handling and timeout management for background tasks

## Core Components

### ConcurrentExecutor

The `ConcurrentExecutor` class provides the foundation for running concurrent tasks:

- Submit tasks for background execution
- Monitor task status and completion
- Retrieve results from completed tasks
- Handle errors and timeouts gracefully
- Clean up tasks when conversations end

### AFSMExecutor

The `AFSMExecutor` class integrates the concurrent execution service with AFSM state machines:

- Execute complete FSM workflows in the background
- Track state transitions during execution
- Maintain proper context throughout the FSM execution
- Return final state and context when complete
- Clean up related resources automatically

## Usage Examples

### Basic Background Task

```python
from fastagent.services.concurrent_executor import executor

# Submit a simple task
async def my_task():
    # Perform some work
    return {"status": "complete", "data": "processed"}

task_id = executor.submit_task(
    task_id="conversation123:my_task",
    coro=my_task()
)

# Later, check the result
result = executor.get_task_result(task_id)
```

### AFSM Task Execution

```python
from fastagent.services.afsm_executor import fsm_executor

# Define states for a structured task
state_map = {
    "initial_state": MyInitialState(),
    "processing_state": MyProcessingState(),
    "final_state": MyFinalState()
}

# Submit an FSM workflow as a background task
task_id = fsm_executor.submit_fsm_task(
    conversation_id="conversation123",
    initial_state="initial_state",
    state_map=state_map,
    context={"user_data": "example"},
    task_name="user_verification"
)

# Later, retrieve the result
result = fsm_executor.get_task_result(task_id)
```

## Integration with Conversation Flow

The concurrent execution service is integrated with the conversation manager to ensure proper resource cleanup:

1. When a task requires background processing, submit it via `fsm_executor`
2. Continue the conversation while the task executes
3. Periodically check for task completion or use appropriate conversational strategies
4. When the conversation ends, all associated tasks are automatically cleaned up

## Best Practices

1. **Task Design**: Keep background tasks focused and optimized
2. **Error Handling**: Include proper error handling in concurrent tasks
3. **State Management**: Maintain clean state boundaries in AFSM tasks
4. **Resource Management**: Be mindful of resource usage in long-running tasks
5. **Conversation Integration**: Use natural prompts to inform users about background processing

## Example Workflow

1. User requests an account balance check
2. Agent acknowledges and starts a background task
3. User and agent continue discussing other topics
4. When balance check completes, agent naturally weaves result into conversation
5. Conversation ends, and all tasks are cleaned up automatically 