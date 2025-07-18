# Enhanced LocalRealtimeClient

This directory contains an enhanced version of the LocalRealtimeClient that supports **saved audio phrases** and **configurable responses**, making it perfect for testing scenarios without requiring an actual OpenAI API connection.

## What's New

The enhanced LocalRealtimeClient now supports:

✅ **Saved Audio Phrases** - Load and play actual audio files instead of silence  
✅ **Configurable Responses** - Different responses for different scenarios  
✅ **Factory Functions** - Easy-to-use functions for common use cases  
✅ **Audio File Caching** - Efficient loading and caching of audio files  
✅ **Function Call Simulation** - Mock function calls with custom responses  
✅ **Customizable Timing** - Control text and audio streaming speeds  

## Key Components

### 1. LocalResponseConfig
A configuration class that defines how a response should be generated:

```python
class LocalResponseConfig(BaseModel):
    text: str = "Default response text"
    audio_file: Optional[str] = None  # Path to audio file
    audio_data: Optional[bytes] = None  # Raw audio data
    delay_seconds: float = 0.05  # Delay between text characters
    audio_chunk_delay: float = 0.2  # Delay between audio chunks
    function_call: Optional[Dict[str, Any]] = None  # Function call to simulate
```

### 2. Enhanced LocalRealtimeClient
The main mock client with support for multiple response configurations:

```python
mock_client = LocalRealtimeClient(
    response_configs={
        "greeting": LocalResponseConfig(
            text="Hello! How can I help you?",
            audio_file="demo/audio/greeting.wav"
        ),
        "help": LocalResponseConfig(
            text="I'd be happy to help you with that.",
            audio_file="demo/audio/help.wav"
        )
    }
)
```

### 3. Factory Functions
Easy-to-use functions for common scenarios:

- `create_customer_service_mock()` - Customer service scenarios
- `create_sales_mock()` - Sales scenarios  
- `create_simple_mock()` - Custom text responses
- `create_function_testing_mock()` - Function call testing
- `create_audio_testing_mock()` - Audio response testing

## Usage Examples

### Basic Usage

```python
from opusagent.mock.mock_factory import create_customer_service_mock

# Create a customer service mock with saved audio files
mock_client = create_customer_service_mock(audio_dir="demo/audio")

# The mock client will now return different responses based on scenarios
# and play actual audio files instead of silence
```

### Custom Responses

```python
from opusagent.mock.mock_realtime_client import LocalRealtimeClient, LocalResponseConfig

# Create a custom mock client
mock_client = LocalRealtimeClient()

# Add response configurations
mock_client.add_response_config(
    "greeting",
    LocalResponseConfig(
        text="Welcome to our service!",
        audio_file="audio/greeting.wav",
        delay_seconds=0.03
    )
)

mock_client.add_response_config(
    "help",
    LocalResponseConfig(
        text="I'm here to help you.",
        audio_file="audio/help.wav",
        delay_seconds=0.04
    )
)
```

### Function Call Testing

```python
from opusagent.mock.mock_factory import create_function_testing_mock

# Create a mock client for testing function calls
mock_client = create_function_testing_mock()

# This mock client will simulate function calls like:
# - get_weather(location="New York", unit="fahrenheit")
# - get_account_balance(account_id="12345", include_transactions=True)
```

### Audio Testing

```python
from opusagent.mock.mock_factory import create_audio_testing_mock

# Create a mock client specifically for audio testing
audio_files = {
    "test1": "audio/test1.wav",
    "test2": "audio/test2.wav",
    "test3": "audio/test3.wav"
}

mock_client = create_audio_testing_mock(audio_files)
```

## Audio File Support

The enhanced mock client supports various audio file formats:

- **WAV files** (recommended for testing)
- **Raw audio data** (bytes)
- **Automatic fallback** to silence if file not found

### Creating Test Audio Files

Use the factory function to create test audio files:

```python
from opusagent.mock.mock_factory import create_test_audio_files

# Create test audio files in demo/audio directory
create_test_audio_files("demo/audio")
```

This will create WAV files with silence for testing purposes.

## Integration with WebSocket Manager

The enhanced mock client integrates seamlessly with your existing WebSocket manager:

```python
from opusagent.websocket_manager import create_mock_websocket_manager

# Create a WebSocket manager that uses the enhanced mock client
websocket_manager = create_mock_websocket_manager(
    mock_server_url="ws://localhost:8080"
)
```

## Testing

Run the test script to see all features in action:

```bash
# Set PYTHONPATH and run tests
set PYTHONPATH=. && python opusagent/mock/test_mock_client.py
```

This will:
1. Create test audio files
2. Test all factory functions
3. Demonstrate response selection
4. Test audio file loading
5. Show function call simulation

## Configuration Options

### Response Selection Logic

The mock client uses a simple response selection strategy:

1. If response configs exist, use the first available key
2. Otherwise, use the default configuration
3. You can customize this logic in `_determine_response_key()`

### Audio File Caching

Audio files are automatically cached to improve performance:

- Files are loaded once and cached in memory
- Subsequent requests use cached data
- Cache is shared across all response configurations

### Timing Control

Control the streaming behavior:

- `delay_seconds`: Time between text characters (simulates typing)
- `audio_chunk_delay`: Time between audio chunks (simulates streaming)

## File Structure

```
opusagent/mock/
├── mock_realtime_client.py    # Enhanced mock client
├── mock_factory.py            # Factory functions
├── example_usage.py           # Usage examples
├── test_mock_client.py        # Test script
└── README.md                  # This file
```

## Benefits

1. **No API Costs** - Test without using OpenAI API credits
2. **Predictable Responses** - Hardcoded responses for consistent testing
3. **Real Audio** - Use actual audio files instead of silence
4. **Fast Testing** - No network latency or API rate limits
5. **Customizable** - Easy to configure for different scenarios
6. **Function Testing** - Test function call handling
7. **Audio Testing** - Test audio streaming and playback

## Next Steps

1. **Add Real Audio Files** - Replace the generated silence with actual audio recordings
2. **Customize Response Logic** - Implement more sophisticated response selection based on conversation context
3. **Add More Scenarios** - Create additional factory functions for your specific use cases
4. **Integration Testing** - Use the mock client in your integration tests

The enhanced LocalRealtimeClient now provides a complete solution for testing your realtime audio applications with saved audio phrases and configurable responses! 