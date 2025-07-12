# Environment Variables for LocalRealtimeClient

This document explains how to use environment variables to configure the LocalRealtimeClient for testing and development.

## Overview

The LocalRealtimeClient can be configured via environment variables to enable mock mode globally across your application. This allows you to switch between real OpenAI API and mock mode without changing your code.

## Environment Variables

### `OPUSAGENT_USE_MOCK`

**Purpose**: Enable or disable mock mode globally

**Values**:
- `true`, `TRUE`, `True` - Enable mock mode
- `false`, `FALSE`, `False` - Disable mock mode (default)
- Not set - Disable mock mode (default)

**Example**:
```bash
export OPUSAGENT_USE_MOCK=true
```

### `OPUSAGENT_MOCK_SERVER_URL`

**Purpose**: Set the URL for the mock WebSocket server

**Default**: `ws://localhost:8080`

**Example**:
```bash
export OPUSAGENT_MOCK_SERVER_URL=ws://localhost:9000
```

## Usage Methods

### Method 1: Shell Environment Variables (Recommended)

Set environment variables in your shell before running your application:

```bash
# Linux/macOS
export OPUSAGENT_USE_MOCK=true
export OPUSAGENT_MOCK_SERVER_URL=ws://localhost:9000
python your_script.py

# Windows Command Prompt
set OPUSAGENT_USE_MOCK=true
set OPUSAGENT_MOCK_SERVER_URL=ws://localhost:9000
python your_script.py

# Windows PowerShell
$env:OPUSAGENT_USE_MOCK="true"
$env:OPUSAGENT_MOCK_SERVER_URL="ws://localhost:9000"
python your_script.py
```

### Method 2: Python Environment Variables

Set environment variables in your Python code before importing the WebSocket manager:

```python
import os

# Set environment variables
os.environ['OPUSAGENT_USE_MOCK'] = 'true'
os.environ['OPUSAGENT_MOCK_SERVER_URL'] = 'ws://localhost:9000'

# Import after setting environment variables
from opusagent.websocket_manager import get_websocket_manager

# Get manager (will use mock mode)
manager = get_websocket_manager()
print(f"Mock mode: {manager.use_mock}")
```

### Method 3: .env File

Create a `.env` file in your project root:

```env
OPUSAGENT_USE_MOCK=true
OPUSAGENT_MOCK_SERVER_URL=ws://localhost:9000
```

The environment variables will be loaded automatically by the `dotenv` package.

## Integration with WebSocket Manager

The environment variables are automatically read by the global WebSocket manager:

```python
from opusagent.websocket_manager import get_websocket_manager

# This will use environment variables to determine mock mode
manager = get_websocket_manager()

if manager.use_mock:
    print("Using mock mode")
else:
    print("Using real OpenAI API")
```

## Factory Functions

You can also create WebSocket managers explicitly:

```python
from opusagent.websocket_manager import (
    create_websocket_manager,
    create_mock_websocket_manager
)

# Create mock manager explicitly
mock_manager = create_mock_websocket_manager()

# Create manager with custom settings
custom_manager = create_websocket_manager(
    use_mock=True,
    mock_server_url="ws://localhost:9000"
)
```

## Testing Environment Variables

Use the provided test script to verify environment variable functionality:

```bash
# Test with default settings
python scripts/test_mock_env.py

# Test with mock mode enabled
OPUSAGENT_USE_MOCK=true python scripts/test_mock_env.py

# Test with custom mock server
OPUSAGENT_USE_MOCK=true OPUSAGENT_MOCK_SERVER_URL=ws://localhost:9000 python scripts/test_mock_env.py
```

## Demo Script

Run the demo script to see environment variables in action:

```bash
# Demo with real API (default)
python scripts/demo_mock_env.py

# Demo with mock API
OPUSAGENT_USE_MOCK=true python scripts/demo_mock_env.py
```

## Configuration Validation

The WebSocket manager validates configuration on initialization:

```python
from opusagent.config.websocket_config import WebSocketConfig

# This will raise an error if required configuration is missing
WebSocketConfig.validate()
```

## Best Practices

1. **Use Environment Variables for Testing**: Set `OPUSAGENT_USE_MOCK=true` in your test environment
2. **Use .env Files for Development**: Create a `.env` file for local development
3. **Check Mock Mode in Code**: Always check `manager.use_mock` to handle different modes
4. **Use Factory Functions for Explicit Control**: Use factory functions when you need explicit control
5. **Test Both Modes**: Ensure your code works with both real and mock APIs

## Troubleshooting

### Environment Variable Not Read

**Problem**: Environment variable is not being read correctly

**Solution**: Ensure the environment variable is set before importing the WebSocket manager:

```python
import os
os.environ['OPUSAGENT_USE_MOCK'] = 'true'
# Import after setting environment variable
from opusagent.websocket_manager import get_websocket_manager
```

### Mock Mode Not Enabled

**Problem**: `manager.use_mock` returns `False` even when environment variable is set

**Solution**: Check the environment variable value:

```python
import os
print(f"OPUSAGENT_USE_MOCK: {os.getenv('OPUSAGENT_USE_MOCK')}")
print(f"Parsed value: {os.getenv('OPUSAGENT_USE_MOCK', 'false').lower() == 'true'}")
```

### Import Errors

**Problem**: Import errors when using mock mode

**Solution**: Ensure all mock dependencies are installed:

```bash
pip install -r requirements.txt
```

## Examples

### Complete Example

```python
import os
import asyncio
from opusagent.websocket_manager import get_websocket_manager

async def main():
    # Set environment variables
    os.environ['OPUSAGENT_USE_MOCK'] = 'true'
    os.environ['OPUSAGENT_MOCK_SERVER_URL'] = 'ws://localhost:9000'
    
    # Get WebSocket manager
    manager = get_websocket_manager()
    
    print(f"Mock mode: {manager.use_mock}")
    print(f"Mock server: {manager.mock_server_url}")
    
    # Use the manager
    connection = await manager.get_connection()
    print(f"Connection created: {connection.connection_id}")
    
    # Clean up
    await manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

### Testing Example

```python
import os
import pytest
from opusagent.websocket_manager import get_websocket_manager

@pytest.fixture
def mock_websocket_manager():
    """Fixture to enable mock mode for tests."""
    os.environ['OPUSAGENT_USE_MOCK'] = 'true'
    manager = get_websocket_manager()
    yield manager
    # Clean up
    asyncio.run(manager.shutdown())

def test_mock_mode(mock_websocket_manager):
    """Test that mock mode is enabled."""
    assert mock_websocket_manager.use_mock is True
```

## Related Documentation

- [LocalRealtimeClient Documentation](README.md)
- [Audio Generation Guide](../scripts/README_audio_generation.md)
- [Factory Functions](mock_factory.py)
- [Test Scripts](../scripts/test_mock_env.py) 