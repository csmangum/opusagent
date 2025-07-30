# OpusAgent Simplified Callback System

This directory contains a streamlined callback system implementation for the OpusAgent codebase, providing essential error handling, resource management, and health monitoring capabilities without over-engineering.

## Philosophy

After analyzing the codebase needs vs. complexity trade-offs, we implemented a simplified approach that provides **80% of the value with 10% of the complexity**. This focuses on the real problems in the codebase while avoiding enterprise-level features that aren't needed.

## Components (~450 lines total vs. 4,656 lines in the original implementation)

### 1. Error Handler (`error_handler.py`) - ~150 lines

**Problem Solved**: 380+ scattered try-except blocks throughout the codebase  
**Value**: High - Significant reduction in boilerplate code

```python
from opusagent.handlers.error_handler import handle_error, ErrorContext, ErrorSeverity

# Replace scattered try-except blocks with centralized handling
try:
    websocket.connect()
except Exception as e:
    await handle_error(
        error=e,
        context=ErrorContext.WEBSOCKET,
        severity=ErrorSeverity.HIGH,
        operation="websocket_connect"
    )

# Register custom handlers for specific contexts
def websocket_error_handler(error_info):
    if error_info.severity == ErrorSeverity.CRITICAL:
        trigger_reconnection()

register_error_handler(websocket_error_handler, ErrorContext.WEBSOCKET)
```

### 2. Resource Manager (`resource_manager.py`) - ~180 lines

**Problem Solved**: WebSocket connections, audio resources, and session cleanup  
**Value**: High - Prevents resource leaks in long-running services

```python
from opusagent.handlers.resource_manager import register_cleanup, ResourceType, CleanupPriority

# Register cleanup for WebSocket
def cleanup_websocket():
    websocket.close()

register_cleanup(
    callback=cleanup_websocket,
    resource_type=ResourceType.WEBSOCKET,
    priority=CleanupPriority.CRITICAL,
    description="Main WebSocket connection"
)

# Automatic cleanup on shutdown/errors
await cleanup_all()  # Executes in LIFO order with priority
```

### 3. Health Checker (`health_checker.py`) - ~120 lines

**Problem Solved**: Basic health monitoring without enterprise complexity  
**Value**: Medium - Useful for monitoring critical components

```python
from opusagent.handlers.health_checker import register_health_check

def check_database():
    try:
        db.ping()
        return {"status": "healthy", "message": "DB responsive"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"DB error: {e}"}

register_health_check(
    name="database",
    check_function=check_database,
    interval=60.0
)

# Get current status
status = get_health_status()  # Overall status + individual checks
```

## Removed Components (Over-engineered for this codebase)

### ❌ Complex Polling Manager
- **Why removed**: Only 6-8 polling loops in entire codebase
- **Replacement**: Simple utility functions in `utils/polling_utils.py`
- **Lines saved**: ~400 lines

```python
# Simple replacement for the few polling needs
from opusagent.utils.polling_utils import start_simple_poll

poll_task = start_simple_poll(
    check_function=lambda: check_websocket_health(),
    interval=30.0,
    condition=lambda: websocket_manager.is_running
)
```

### ❌ Session State Callbacks
- **Why removed**: UI concerns should be separate from data models
- **Replacement**: Return status changes from methods, let UI react
- **Lines saved**: ~200 lines

### ❌ Event Router Enhancements  
- **Why removed**: Multiple handlers per event rarely needed
- **Replacement**: Keep existing simple EventRouter
- **Lines saved**: ~300 lines

### ❌ Complex Health Monitor
- **Why removed**: Enterprise alerting, history, aggregation not needed
- **Replacement**: Basic health checker
- **Lines saved**: ~600 lines

## Usage Examples

### Complete Integration Example

```python
# See examples/simplified_callback_example.py
python -m opusagent.examples.simplified_callback_example
```

### Real-World Usage Patterns

```python
# 1. Replace try-except boilerplate
async def websocket_operation():
    try:
        await websocket.send(data)
    except Exception as e:
        await handle_error(e, ErrorContext.WEBSOCKET, ErrorSeverity.HIGH, "send_data")

# 2. Ensure resource cleanup
register_cleanup(
    lambda: audio_stream.close(),
    ResourceType.AUDIO,
    CleanupPriority.HIGH,
    "Audio stream"
)

# 3. Monitor critical components
register_health_check("openai_api", check_openai_health, 30.0)
```

## Migration from Complex Implementation

If you were using the original complex implementation:

1. **Error Handling**: Remove `priority` and `context manager` features, keep basic registration
2. **Resource Management**: Remove `managed_resource` context manager and complex metadata
3. **Health Monitoring**: Replace with basic health checker, remove alerting/history features
4. **Polling**: Use `simple_poll` utility functions instead of full polling manager
5. **Session State**: Remove callbacks, handle state changes in UI layer
6. **Event Router**: Use original simple router, remove middleware/multiple handlers

## Benefits of Simplified Approach

### ✅ Advantages
- **Much smaller codebase**: 450 lines vs 4,656 lines (90% reduction)
- **Easier to understand**: Simple, focused components
- **Addresses real problems**: 380+ try-except blocks, resource cleanup needs
- **Lower maintenance burden**: Less code to debug and maintain
- **Faster implementation**: Quick to integrate into existing code

### ⚠️ Trade-offs
- **Less flexible**: No priority ordering, middleware, complex alerting
- **No enterprise features**: No metrics aggregation, alert debouncing, etc.
- **Simpler APIs**: Fewer configuration options

## Performance

- **Error Handler**: Minimal overhead, simple list iteration
- **Resource Manager**: LIFO cleanup with basic priority support
- **Health Checker**: Basic polling loops, no history retention
- **Memory Usage**: Significantly lower than complex implementation

## When to Use This vs. Enterprise Solutions

**Use this simplified system when**:
- Building applications, not platforms
- Need basic error handling and resource cleanup
- Want to reduce try-except boilerplate
- Don't need complex monitoring features

**Consider enterprise solutions when**:
- Building multi-tenant platforms
- Need comprehensive monitoring/alerting
- Require complex event processing pipelines
- Have dedicated DevOps/monitoring team

## Summary

This simplified callback system provides the essential benefits of the original analysis (reducing duplication, improving resource management, adding basic monitoring) while avoiding the complexity overhead. It's specifically tailored to the actual needs of the OpusAgent codebase rather than implementing features that might be needed someday.