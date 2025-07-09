# MockRealtimeClient Changelog

## Version 2.0.0 - Enhanced Mock Client with Audio Support

### 🎉 Major Features

#### Environment Variable Support
- **NEW**: Mock mode can now be enabled via environment variables
- **NEW**: `OPUSAGENT_USE_MOCK=true` enables mock mode globally
- **NEW**: `OPUSAGENT_MOCK_SERVER_URL=ws://localhost:8080` sets custom mock server URL
- **NEW**: Dynamic WebSocket manager creation that reads environment variables at runtime

#### Audio File Support
- **NEW**: Support for real audio files instead of silence
- **NEW**: Audio file caching for improved performance
- **NEW**: Automatic fallback to silence for missing files
- **NEW**: Configurable audio chunk delays for realistic streaming

#### Response Configuration System
- **NEW**: `MockResponseConfig` class for customizable responses
- **NEW**: Multiple response configurations for different scenarios
- **NEW**: Configurable text and audio timing
- **NEW**: Function call simulation support

#### Factory Functions
- **NEW**: `create_customer_service_mock()` for customer service scenarios
- **NEW**: `create_sales_mock()` for sales scenarios
- **NEW**: `create_function_test_mock()` for function call testing
- **NEW**: `create_audio_test_mock()` for audio testing

### 🔧 Usage Examples

#### Environment Variable Usage
```bash
# Enable mock mode globally
export OPUSAGENT_USE_MOCK=true
python your_script.py

# Set custom mock server
export OPUSAGENT_USE_MOCK=true
export OPUSAGENT_MOCK_SERVER_URL=ws://localhost:9000
python your_script.py
```

#### Python Code Usage
```python
# Method 1: Environment variable (recommended)
import os
os.environ['OPUSAGENT_USE_MOCK'] = 'true'
from opusagent.websocket_manager import get_websocket_manager
manager = get_websocket_manager()  # Will use mock mode

# Method 2: Explicit creation
from opusagent.websocket_manager import create_mock_websocket_manager
manager = create_mock_websocket_manager()

# Method 3: Factory functions
from opusagent.mock.mock_factory import create_customer_service_mock
mock_client = create_customer_service_mock(audio_dir="demo/audio/mock")
```

#### Basic MockRealtimeClient Usage
```python
from opusagent.mock.mock_realtime_client import MockRealtimeClient, MockResponseConfig

# Create mock client
mock_client = MockRealtimeClient()

# Add response configuration with audio
mock_client.add_response_config(
    "greeting",
    MockResponseConfig(
        text="Hello! Welcome to our service.",
        audio_file="demo/audio/mock/greetings/greetings_01.wav",
        delay_seconds=0.03,
        audio_chunk_delay=0.15
    )
)

# Use with WebSocket manager
from opusagent.websocket_manager import create_mock_websocket_manager
websocket_manager = create_mock_websocket_manager()
```

### 📁 File Structure

```
opusagent/mock/
├── __init__.py
├── mock_realtime_client.py      # Main mock client implementation
├── mock_factory.py              # Factory functions for common scenarios
├── mock_twilio_client.py        # Twilio mock client
├── mock_audiocodes_client.py    # AudioCodes mock client
├── example_usage.py             # Usage examples
├── test_mock_client.py          # Test script
├── README.md                    # Detailed documentation
└── CHANGELOG.md                 # This file

scripts/
├── generate_mock_audio.py       # Audio file generation script
├── example_mock_audio_usage.py  # Audio usage examples
├── test_mock_env.py             # Environment variable testing
├── demo_mock_env.py             # Environment variable demo
└── README_audio_generation.md   # Audio generation documentation
```

### 🎵 Audio Generation

#### Generate Audio Files
```bash
# Generate all scenarios
python scripts/generate_mock_audio.py

# Generate specific scenario
python scripts/generate_mock_audio.py --scenario customer_service

# Use specific voice
python scripts/generate_mock_audio.py --voice alloy

# Custom output directory
python scripts/generate_mock_audio.py --output-dir demo/audio/mock
```

#### Available Audio Scenarios
- `customer_service` - Customer service representative responses
- `card_replacement` - Card replacement specific responses
- `technical_support` - Technical support responses
- `sales` - Sales representative responses
- `greetings` - General greeting and introduction responses
- `farewells` - Farewell and closing responses
- `confirmations` - Confirmation and verification responses
- `errors` - Error and problem resolution responses

### 🔧 Configuration

#### Environment Variables
- `OPUSAGENT_USE_MOCK` - Enable mock mode (true/false)
- `OPUSAGENT_MOCK_SERVER_URL` - Mock server URL (default: ws://localhost:8080)

#### MockResponseConfig Parameters
- `text` - Response text content
- `audio_file` - Path to audio file
- `audio_data` - Raw audio bytes (takes precedence over audio_file)
- `delay_seconds` - Delay between text characters (default: 0.05s)
- `audio_chunk_delay` - Delay between audio chunks (default: 0.2s)
- `function_call` - Function call to simulate

### 🧪 Testing

#### Test Environment Variables
```bash
python scripts/test_mock_env.py
```

#### Test with Mock Mode Enabled
```bash
OPUSAGENT_USE_MOCK=true python scripts/test_mock_env.py
```

#### Demo Environment Variable Usage
```bash
python scripts/demo_mock_env.py
```

### 🔄 Migration from v1.0

#### Old Usage (v1.0)
```python
from opusagent.mock.mock_realtime_client import MockRealtimeClient

mock_client = MockRealtimeClient()
# Limited functionality, only silence audio
```

#### New Usage (v2.0)
```python
from opusagent.mock.mock_realtime_client import MockRealtimeClient, MockResponseConfig

mock_client = MockRealtimeClient()
mock_client.add_response_config(
    "greeting",
    MockResponseConfig(
        text="Hello!",
        audio_file="audio/greeting.wav"
    )
)
```

### 🚀 Performance Improvements

- **Audio Caching**: Files loaded once and cached in memory
- **Lazy Loading**: Global WebSocket manager created on first use
- **Environment Variable Reading**: Dynamic configuration at runtime
- **Connection Pooling**: Efficient connection management

### 🐛 Bug Fixes

- Fixed environment variable parsing for case-insensitive values
- Fixed global WebSocket manager initialization timing
- Fixed audio file loading error handling
- Fixed WebSocket wrapper compatibility issues

### 📚 Documentation

- Comprehensive docstrings for all classes and methods
- Usage examples for all major features
- Audio generation guide with examples
- Environment variable configuration guide
- Migration guide from v1.0 to v2.0

### 🔮 Future Plans

- [ ] Support for more audio formats (MP3, OGG, etc.)
- [ ] Dynamic response generation based on conversation context
- [ ] Integration with external TTS services
- [ ] WebSocket server mode for standalone testing
- [ ] Performance benchmarking tools
- [ ] More factory functions for specific use cases

---

## Version 1.0.0 - Initial Release

### Features
- Basic MockRealtimeClient implementation
- WebSocket connection simulation
- Hardcoded text responses
- Silence audio generation
- Basic event handling

### Limitations
- No audio file support
- Limited response customization
- No environment variable support
- Basic functionality only 