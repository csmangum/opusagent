# OpusAgent Callback System Implementation

This directory contains a comprehensive callback system implementation for the OpusAgent codebase, providing enhanced modularity, error handling, and reactive programming capabilities.

## Overview

The callback systems address common pain points in asynchronous Python applications by providing:

- **Centralized Error Handling**: Reduces boilerplate try-except blocks
- **State Transition Callbacks**: Enables reactive UI updates and state management
- **Configurable Polling**: Replaces hardcoded loops with flexible monitoring
- **Resource Cleanup**: Ensures proper LIFO cleanup of resources
- **Enhanced Event Processing**: Supports multiple handlers per event with priority ordering
- **Health Monitoring**: Provides comprehensive system health tracking with alerting

## Components

### 1. Error Handler (`error_handler.py`)

Centralized error handling system with context-specific callbacks.

**Key Features:**
- Context-aware error categorization (WebSocket, Audio, Session, API, etc.)
- Priority-based handler execution
- Error statistics and tracking
- Async and sync callback support

**Usage:**
```python
from opusagent.handlers.error_handler import handle_error, ErrorContext, ErrorSeverity

# Handle an error with context
await handle_error(
    error=ConnectionError("WebSocket disconnected"),
    context=ErrorContext.WEBSOCKET,
    severity=ErrorSeverity.HIGH,
    operation="websocket_communication"
)

# Register custom error handler
def my_error_handler(error_info):
    print(f"Error: {error_info.error} in {error_info.context.value}")

register_error_handler(my_error_handler, ErrorContext.WEBSOCKET, priority=100)
```

### 2. Session State Callbacks (`models/session_state.py`)

Enhanced SessionState with callback support for status transitions.

**Key Features:**
- Reactive status change notifications
- Priority-based callback execution
- Automatic status transitions with callbacks

**Usage:**
```python
from opusagent.models.session_state import SessionState, SessionStatus

# Create session and register callback
session = SessionState(conversation_id="test_123")

def on_status_change(old_status, new_status, session):
    print(f"Session {session.conversation_id}: {old_status} → {new_status}")

session.register_status_callback(on_status_change)

# Status change triggers callbacks
session.update_status(SessionStatus.ACTIVE)
```

### 3. Polling Manager (`polling_manager.py`)

Configurable polling system for health checks and monitoring.

**Key Features:**
- Multiple concurrent polling tasks
- Conditional polling based on runtime conditions
- Error handling and retry logic
- Task lifecycle management

**Usage:**
```python
from opusagent.handlers.polling_manager import register_polling_task

# Register a health check
def check_database():
    # Perform database connectivity check
    return {"status": "healthy", "latency": 0.05}

register_polling_task(
    name="db_health",
    callback=check_database,
    interval=30.0,  # 30 seconds
    condition=lambda: config.monitoring_enabled
)
```

### 4. Resource Manager (`resource_manager.py`)

LIFO resource cleanup system with priority support.

**Key Features:**
- Automatic cleanup on shutdown and errors
- Priority-based cleanup ordering
- Resource categorization and tracking
- Context manager support

**Usage:**
```python
from opusagent.handlers.resource_manager import register_cleanup, ResourceType, CleanupPriority

# Register WebSocket cleanup
def cleanup_websocket():
    websocket.close()

cleanup_id = register_cleanup(
    callback=cleanup_websocket,
    resource_type=ResourceType.WEBSOCKET,
    priority=CleanupPriority.CRITICAL,
    description="Main WebSocket connection"
)

# Context manager for automatic cleanup
async with resource_manager.managed_resource(
    websocket, 
    lambda: websocket.close(),
    ResourceType.WEBSOCKET,
    CleanupPriority.HIGH
) as ws:
    # Use websocket
    await ws.send("Hello")
# Automatic cleanup happens here
```

### 5. Enhanced Event Router (`event_router.py`)

Extended EventRouter supporting multiple handlers per event with middleware.

**Key Features:**
- Multiple handlers per event type
- Priority-based handler execution
- Event middleware for transformation and filtering
- Enhanced error isolation

**Usage:**
```python
from opusagent.handlers.event_router import EventRouter

router = EventRouter()

# Register multiple handlers for same event
def primary_handler(data):
    print("Primary processing")

def secondary_handler(data):
    print("Secondary processing")

router.register_realtime_handler("session.created", primary_handler, priority=100)
router.register_realtime_handler("session.created", secondary_handler, priority=50)

# Register middleware
def logging_middleware(event_type, data):
    print(f"Processing {event_type}")
    return data

router.register_middleware(logging_middleware, priority=100)
```

### 6. Health Monitor (`health_monitor.py`)

Comprehensive health monitoring with aggregation and alerting.

**Key Features:**
- Multiple health checks with configurable intervals
- Alert generation on status changes
- Health status aggregation
- Historical data tracking with automatic cleanup

**Usage:**
```python
from opusagent.handlers.health_monitor import register_health_check, get_health_monitor

# Register health check
def check_api_health():
    try:
        response = api_client.ping()
        return {
            "status": "healthy",
            "message": "API is responsive",
            "latency": response.latency
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"API error: {e}"
        }

register_health_check(
    component="api",
    check_function=check_api_health,
    interval=60.0,
    critical=True
)

# Register alert callback
def handle_alert(alert):
    if alert.severity.value == "critical":
        send_notification(f"Critical: {alert.message}")

get_health_monitor().register_alert_callback(handle_alert)
```

## Integration Example

See `examples/callback_integration_example.py` for a complete demonstration of how all callback systems work together.

```python
# Run the integration example
python -m opusagent.examples.callback_integration_example
```

## Best Practices

### 1. Error Handling
- Use appropriate error contexts for better categorization
- Set severity levels correctly to trigger appropriate responses
- Include relevant metadata for debugging

### 2. State Transitions
- Register callbacks before triggering state changes
- Use priority ordering for dependent operations
- Keep callbacks lightweight to avoid blocking

### 3. Polling Tasks
- Use conditions to enable/disable polling dynamically
- Set appropriate intervals to balance responsiveness and resource usage
- Handle errors gracefully with retry logic

### 4. Resource Cleanup
- Register cleanup callbacks immediately after resource creation
- Use appropriate priority levels (CRITICAL for essential resources)
- Test cleanup logic thoroughly

### 5. Event Processing
- Use middleware for cross-cutting concerns (logging, security)
- Register handlers with appropriate priorities
- Isolate handler failures to prevent cascading issues

### 6. Health Monitoring
- Mark critical components appropriately
- Set reasonable check intervals
- Implement proper alert handling to avoid spam

## Configuration

All callback systems support configuration through their respective constructors:

```python
# Custom error handler with different logger
error_handler = ErrorHandler(logger=custom_logger)

# Health monitor with custom retention
health_monitor = HealthMonitor(
    alert_debounce_seconds=30.0,
    history_retention_hours=48
)

# Resource manager with custom thread pool
resource_manager = ResourceManager(max_workers=8)
```

## Performance Considerations

- **Callback Execution**: All callbacks are executed with error isolation
- **Memory Usage**: Automatic cleanup of historical data prevents memory leaks
- **Thread Safety**: All systems are designed for async/concurrent usage
- **Resource Cleanup**: LIFO ordering ensures proper dependency resolution

## Monitoring and Debugging

Each system provides statistics and status information:

```python
# Error statistics
error_stats = get_error_handler().get_error_stats()

# Polling task status
polling_status = get_polling_manager().get_all_tasks_status()

# Resource cleanup statistics
resource_stats = get_resource_manager().get_resource_stats()

# Health status
health_status = get_health_monitor().get_health_status()

# Event handler statistics
handler_stats = event_router.get_handler_stats()
```

## Testing

The callback systems include comprehensive error handling and graceful degradation:

- Callback failures are isolated and logged
- Systems continue operating even if individual callbacks fail
- Proper cleanup ensures no resource leaks during testing

## Migration Guide

To integrate these systems into existing code:

1. **Replace try-except blocks** with centralized error handling
2. **Add state transition callbacks** instead of manual notifications
3. **Convert polling loops** to configurable polling tasks
4. **Register cleanup callbacks** for all resources
5. **Enhance event handlers** with multiple handler support
6. **Add health checks** for critical components

This provides a foundation for building more maintainable, scalable, and robust async applications with proper error handling, resource management, and monitoring capabilities.