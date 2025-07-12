# Audio Generation Scripts for LocalRealtimeClient

This directory contains scripts for generating audio files to use with the `LocalRealtimeClient` for testing and development.

## Overview

The LocalRealtimeClient supports using real audio files instead of silence, making tests more realistic and comprehensive. These scripts help you generate audio files for various scenarios.

## Scripts

### 1. `generate_mock_audio.py`

The main script for generating audio files using OpenAI's TTS API.

**Features:**
- Generate audio for 8 different scenarios
- Support for all OpenAI TTS voices
- Organized directory structure
- Configurable output formats
- Error handling and progress tracking

**Usage:**
```bash
# Generate all scenarios
python scripts/generate_mock_audio.py

# Generate specific scenario
python scripts/generate_mock_audio.py --scenario customer_service

# Use specific voice
python scripts/generate_mock_audio.py --voice alloy

# Custom output directory
python scripts/generate_mock_audio.py --output-dir demo/audio/mock

# List available scenarios
python scripts/generate_mock_audio.py --list-scenarios
```

**Available Scenarios:**
- `customer_service` - Customer service representative responses
- `card_replacement` - Card replacement specific responses
- `technical_support` - Technical support responses
- `sales` - Sales representative responses
- `greetings` - General greeting and introduction responses
- `farewells` - Farewell and closing responses
- `confirmations` - Confirmation and verification responses
- `errors` - Error and problem resolution responses

**Available Voices:**
- `alloy` (default)
- `echo`
- `fable`
- `onyx`
- `nova`
- `shimmer`

### 2. `example_mock_audio_usage.py`

Example script demonstrating how to use generated audio files with the LocalRealtimeClient.

**Features:**
- Basic usage examples
- Factory function examples
- Audio file loading examples
- Function call examples
- WebSocket simulation examples
- Audio file validation

**Usage:**
```bash
python scripts/example_mock_audio_usage.py
```

### 3. `synthesize_phrases.py`

Original script for generating specific phrases (legacy).

**Usage:**
```bash
python scripts/synthesize_phrases.py
```

## Directory Structure

After running `generate_mock_audio.py`, you'll have this structure:

```
demo/audio/mock/
├── customer_service/
│   ├── customer_service_01.wav
│   ├── customer_service_02.wav
│   └── ...
├── card_replacement/
│   ├── card_replacement_01.wav
│   ├── card_replacement_02.wav
│   └── ...
├── technical_support/
├── sales/
├── greetings/
├── farewells/
├── confirmations/
└── errors/
```

## Integration with LocalRealtimeClient

### Basic Usage

```python
from opusagent.mock.mock_realtime_client import LocalRealtimeClient, MockResponseConfig

# Create mock client
mock_client = LocalRealtimeClient()

# Add response configuration with audio file
mock_client.add_response_config(
    "greeting",
    MockResponseConfig(
        text="Hello! Welcome to our service.",
        audio_file="demo/audio/mock/greetings/greetings_01.wav",
        delay_seconds=0.03,
        audio_chunk_delay=0.15
    )
)
```

### Using Factory Functions

```python
from opusagent.mock.mock_factory import create_customer_service_mock

# Create customer service mock with audio files
mock_client = create_customer_service_mock(
    audio_dir="demo/audio/mock"
)
```

### WebSocket Manager Integration

```python
from opusagent.websocket_manager import create_mock_websocket_manager

# Create WebSocket manager with mock client
websocket_manager = create_mock_websocket_manager(
    mock_server_url="ws://localhost:8080"
)
```

## Configuration

### Environment Variables

Set your OpenAI API key in a `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

### Custom Scenarios

You can add custom scenarios by modifying the `AUDIO_SCENARIOS` dictionary in `generate_mock_audio.py`:

```python
AUDIO_SCENARIOS["custom_scenario"] = {
    "description": "Custom scenario description",
    "voice_instructions": "Custom voice instructions",
    "phrases": [
        "Custom phrase 1",
        "Custom phrase 2",
        # ... more phrases
    ]
}
```

## Audio File Formats

- **Format**: WAV (16-bit PCM)
- **Sample Rate**: 16kHz (default)
- **Channels**: Mono
- **Duration**: Variable (based on text length)

## Performance Considerations

### Caching

The LocalRealtimeClient automatically caches loaded audio files in memory for improved performance. Files are loaded once and reused.

### File Sizes

Audio files are typically 50-200KB each, depending on the phrase length. A complete set of all scenarios (~80 files) will use approximately 5-10MB of disk space.

### Loading Time

- First load: ~100-500ms per file (depends on file size)
- Cached load: ~1-5ms per file

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   ```
   Error: OPENAI_API_KEY not found in environment
   ```
   **Solution**: Set your OpenAI API key in a `.env` file or environment variable.

2. **Audio Files Not Found**
   ```
   Warning: Audio file not found: demo/audio/mock/greetings/greetings_01.wav
   ```
   **Solution**: Run `generate_mock_audio.py` first to create the audio files.

3. **Import Errors**
   ```
   ModuleNotFoundError: No module named 'opusagent'
   ```
   **Solution**: Ensure you're running from the project root directory.

4. **Connection Errors**
   ```
   Connection failed: Connection refused
   ```
   **Solution**: This is normal if no mock server is running. The mock client can work without a server.

### Debug Mode

Enable debug logging to see detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Best Practices

1. **Generate Audio Files First**: Always run `generate_mock_audio.py` before using the mock client with audio files.

2. **Use Appropriate Scenarios**: Choose scenarios that match your testing needs.

3. **Test Different Voices**: Try different voices to ensure your application works with various speech patterns.

4. **Monitor File Sizes**: Keep track of audio file sizes to avoid excessive disk usage.

5. **Version Control**: Consider whether to include generated audio files in version control (usually not recommended due to size).

## Examples

See `example_mock_audio_usage.py` for comprehensive examples of:
- Basic LocalRealtimeClient usage
- Factory function usage
- Audio file loading and caching
- Function call simulation
- WebSocket integration

## Next Steps

1. Generate audio files: `python scripts/generate_mock_audio.py`
2. Test with examples: `python scripts/example_mock_audio_usage.py`
3. Integrate with your tests
4. Customize scenarios as needed
5. Use with your WebSocket manager

For more information about the LocalRealtimeClient, see the main documentation in `opusagent/mock/CHANGELOG.md`. 