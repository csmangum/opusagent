# WebSocket Manager

The WebSocket Manager provides centralized management of WebSocket connections to the OpenAI Realtime API, offering connection pooling, health monitoring, and automatic cleanup.

## Features

- **Connection Pooling**: Reuses WebSocket connections across multiple sessions
- **Health Monitoring**: Automatically monitors and cleans up unhealthy connections
- **Configurable Limits**: Set maximum connections, connection age, and idle time
- **Graceful Shutdown**: Properly closes all connections on application shutdown
- **Real-time Statistics**: Monitor connection pool health and usage
- **Automatic Reconnection**: Creates new connections as needed

## Benefits

### Before WebSocket Manager
- Each call created a new WebSocket connection
- No connection reuse
- Manual connection cleanup
- No centralized monitoring
- Potential resource leaks

### After WebSocket Manager
- Connections are pooled and reused
- Automatic health monitoring and cleanup
- Centralized connection management
- Real-time statistics and monitoring
- Graceful resource management

## Configuration

The WebSocket Manager is configured using environment variables:

### Required Configuration

```env
# OpenAI API key (required)
OPENAI_API_KEY=your_openai_api_key_here
```

### Optional Configuration

```env
# Connection Pool Settings
WEBSOCKET_MAX_CONNECTIONS=10                    # Maximum number of connections in pool
WEBSOCKET_MAX_CONNECTION_AGE=3600               # Maximum connection age in seconds (1 hour)
WEBSOCKET_MAX_IDLE_TIME=300                     # Maximum idle time in seconds (5 minutes)
WEBSOCKET_HEALTH_CHECK_INTERVAL=30              # Health check interval in seconds
WEBSOCKET_MAX_SESSIONS_PER_CONNECTION=10        # Maximum sessions per connection

# WebSocket Connection Parameters
WEBSOCKET_PING_INTERVAL=20                      # Ping interval in seconds
WEBSOCKET_PING_TIMEOUT=30                       # Ping timeout in seconds
WEBSOCKET_CLOSE_TIMEOUT=10                      # Close timeout in seconds

# OpenAI Model
OPENAI_REALTIME_MODEL=gpt-4o-realtime-preview-2024-12-17
```

## Usage

### Basic Usage

The WebSocket Manager is automatically initialized and used by the main application:

```python
from opusagent.websocket_manager import websocket_manager

# Get a connection from the pool
async with websocket_manager.connection_context() as connection:
    # Use connection.websocket for communication
    await connection.websocket.send(message)
    response = await connection.websocket.recv()
```

### Integration with Bridges

The manager is integrated with both AudioCodes and Twilio bridges:

```python
# In main.py
async with websocket_manager.connection_context() as connection:
    bridge = AudioCodesBridge(websocket, connection.websocket)
    # ... use bridge
```

### Monitoring

Access real-time statistics via HTTP endpoints:

#### Health Check
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "websocket_manager": {
    "healthy_connections": 3,
    "total_connections": 3,
    "max_connections": 10
  },
  "message": "Service is operational"
}
```

#### Detailed Statistics
```bash
curl http://localhost:8000/stats
```

Response:
```json
{
  "total_connections": 3,
  "healthy_connections": 3,
  "active_sessions": 0,
  "total_sessions_handled": 15,
  "max_connections": 10
}
```

#### Configuration
```bash
curl http://localhost:8000/config
```

Response:
```json
{
  "websocket_manager": {
    "max_connections": 10,
    "max_connection_age": 3600,
    "max_idle_time": 300,
    "health_check_interval": 30,
    "max_sessions_per_connection": 10,
    "ping_interval": 20,
    "ping_timeout": 30,
    "close_timeout": 10,
    "openai_model": "gpt-4o-realtime-preview-2024-12-17",
    "websocket_url": "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
  },
  "note": "Configuration is read from environment variables at startup"
}
```

## Architecture

### Components

1. **RealtimeConnection**: Wrapper for individual WebSocket connections
   - Tracks connection health, age, and usage
   - Manages session limits per connection
   - Handles graceful connection closure

2. **WebSocketManager**: Main management class
   - Maintains connection pool
   - Implements health monitoring
   - Provides connection context manager
   - Handles configuration and cleanup

3. **WebSocketConfig**: Configuration management
   - Reads environment variables
   - Validates configuration
   - Provides default values

### Connection Lifecycle

1. **Creation**: New connections are created on demand
2. **Pooling**: Healthy connections are kept in the pool for reuse
3. **Health Monitoring**: Background task monitors connection health
4. **Cleanup**: Unhealthy, old, or idle connections are automatically removed
5. **Shutdown**: All connections are gracefully closed on application shutdown

### Health Monitoring

The health monitor runs every 30 seconds (configurable) and removes connections that are:
- Marked as unhealthy
- Closed by the remote server
- Older than the maximum age
- Idle longer than the maximum idle time

## Best Practices

### Production Configuration

For production environments, consider these settings:

```env
# Higher connection limits for production
WEBSOCKET_MAX_CONNECTIONS=50
WEBSOCKET_MAX_CONNECTION_AGE=7200          # 2 hours
WEBSOCKET_MAX_IDLE_TIME=600               # 10 minutes
WEBSOCKET_HEALTH_CHECK_INTERVAL=60        # 1 minute
WEBSOCKET_MAX_SESSIONS_PER_CONNECTION=20
```

### Monitoring

- Monitor the `/health` endpoint for service health
- Track connection pool statistics via `/stats`
- Set up alerts for unhealthy connections
- Monitor total sessions handled for usage patterns

### Troubleshooting

1. **No healthy connections**: Check OpenAI API key and network connectivity
2. **High connection turnover**: Increase connection age or investigate connection stability
3. **Pool exhaustion**: Increase max connections or reduce session limits

## Migration Guide

### From Direct WebSocket Connections

**Before:**
```python
realtime_websocket = await websockets.connect(url, headers=headers)
bridge = AudioCodesBridge(websocket, realtime_websocket)
```

**After:**
```python
async with websocket_manager.connection_context() as connection:
    bridge = AudioCodesBridge(websocket, connection.websocket)
```

### Configuration Migration

Move connection parameters to environment variables:
- `WEBSOCKET_MAX_CONNECTIONS` for pool size
- `WEBSOCKET_PING_INTERVAL` for ping settings
- `OPENAI_REALTIME_MODEL` for model selection

The WebSocket Manager provides robust, scalable connection management for your OpenAI Realtime API integration. 