# MockRealtimeClient Refactoring Migration Guide

## Overview

The `MockRealtimeClient` has been refactored from a single large file (`mock_realtime_client.py`) into a modular structure under the `mock_realtime/` directory. This refactoring improves maintainability, testability, and separation of concerns.

## What Changed

### Before (Monolithic Structure)
```
opusagent/mock/
├── mock_realtime_client.py    # 1,213 lines - everything in one file
├── mock_factory.py
├── mock_twilio_client.py
├── mock_audiocodes_client.py
└── ...
```

### After (Modular Structure)
```
opusagent/mock/
├── mock_realtime/             # New modular structure
│   ├── __init__.py           # Main exports
│   ├── models.py             # Data models (MockResponseConfig, etc.)
│   ├── audio.py              # Audio management and caching
│   ├── handlers.py           # WebSocket event handlers
│   ├── generators.py         # Response generation logic
│   ├── client.py             # Main MockRealtimeClient
│   └── utils.py              # Utility functions and constants
├── mock_realtime_client.py   # Backward compatibility wrapper
├── mock_factory.py
├── mock_twilio_client.py
├── mock_audiocodes_client.py
└── ...
```

## Migration Steps

### 1. Update Imports (Recommended)

**Old way:**
```python
from opusagent.mock.mock_realtime_client import MockRealtimeClient, MockResponseConfig
```

**New way:**
```python
from opusagent.mock.mock_realtime import MockRealtimeClient, MockResponseConfig
```

### 2. Backward Compatibility

The old import path still works for backward compatibility:
```python
# This still works
from opusagent.mock.mock_realtime_client import MockRealtimeClient, MockResponseConfig
```

However, it's recommended to update to the new import path for better maintainability.

## Module Breakdown

### `models.py`
- **Purpose**: Data models and configuration classes
- **Contains**: `MockResponseConfig`, `MockSessionState`
- **Benefits**: Clear data structure definitions, validation

### `audio.py`
- **Purpose**: Audio file management and processing
- **Contains**: `AudioManager` class
- **Benefits**: Centralized audio handling, caching, fallback logic

### `handlers.py`
- **Purpose**: WebSocket event processing
- **Contains**: `EventHandlerManager` class
- **Benefits**: Extensible event handling, clean separation of concerns

### `generators.py`
- **Purpose**: Response generation logic
- **Contains**: `ResponseGenerator` class
- **Benefits**: Focused response generation, easier testing

### `client.py`
- **Purpose**: Main client orchestration
- **Contains**: `MockRealtimeClient` class
- **Benefits**: Clean main interface, delegates to specialized components

### `utils.py`
- **Purpose**: Helper functions and constants
- **Contains**: Utility functions, constants, helper methods
- **Benefits**: Reusable utilities, centralized constants

## Benefits of the Refactoring

### 1. **Maintainability**
- Smaller, focused files are easier to understand and modify
- Clear separation of concerns
- Reduced cognitive load when working on specific features

### 2. **Testability**
- Each module can be tested independently
- Easier to mock specific components
- Better unit test coverage

### 3. **Extensibility**
- Easy to add new event handlers
- Simple to extend audio processing
- Modular response generation

### 4. **Code Reuse**
- Utilities can be shared across modules
- Audio management can be used independently
- Event handling can be extended

## Example Usage (No Changes Required)

Your existing code will continue to work without any changes:

```python
# This still works exactly the same
from opusagent.mock.mock_realtime_client import MockRealtimeClient, MockResponseConfig

# Create mock client
mock_client = MockRealtimeClient()

# Add response configuration
mock_client.add_response_config(
    "greeting",
    MockResponseConfig(
        text="Hello! How can I help you?",
        audio_file="audio/greeting.wav"
    )
)

# Use with WebSocket manager
from opusagent.websocket_manager import create_mock_websocket_manager
websocket_manager = create_mock_websocket_manager()
```

## Advanced Usage with New Structure

If you want to use the new modular structure directly:

```python
from opusagent.mock.mock_realtime import MockRealtimeClient, MockResponseConfig
from opusagent.mock.mock_realtime.audio import AudioManager
from opusagent.mock.mock_realtime.handlers import EventHandlerManager
from opusagent.mock.mock_realtime.generators import ResponseGenerator

# Create components individually
audio_manager = AudioManager()
event_handler = EventHandlerManager()
response_generator = ResponseGenerator(audio_manager=audio_manager)

# Create mock client with custom components
mock_client = MockRealtimeClient(
    logger=logger,
    session_config=session_config,
    response_configs=response_configs
)
```

## Testing

The refactoring makes testing much easier:

```python
# Test audio management independently
from opusagent.mock.mock_realtime.audio import AudioManager

async def test_audio_manager():
    audio_manager = AudioManager()
    audio_data = await audio_manager.load_audio_file("test.wav")
    assert len(audio_data) > 0

# Test event handlers independently
from opusagent.mock.mock_realtime.handlers import EventHandlerManager

async def test_event_handlers():
    handler = EventHandlerManager()
    # Test specific event handling logic
```

## Migration Checklist

- [ ] Update imports to use `from opusagent.mock.mock_realtime import ...`
- [ ] Test existing functionality to ensure nothing broke
- [ ] Update any custom event handlers to use the new structure
- [ ] Consider using the new modular components for advanced use cases
- [ ] Update documentation to reference the new structure

## Breaking Changes

**None!** This refactoring is fully backward compatible. All existing code will continue to work without any changes.

## Future Enhancements

The new modular structure enables several future enhancements:

1. **Custom Audio Processors**: Easy to add new audio processing plugins
2. **Advanced Event Handling**: Extensible event processing pipeline
3. **Response Templates**: Reusable response generation patterns
4. **Performance Optimizations**: Targeted optimizations per module
5. **Plugin System**: Third-party extensions for specific use cases

## Support

If you encounter any issues during migration:

1. Check that you're using the correct import path
2. Verify that all dependencies are installed
3. Test with a simple example first
4. Review the module documentation for specific usage patterns

The refactoring maintains 100% backward compatibility while providing a much more maintainable and extensible codebase. 