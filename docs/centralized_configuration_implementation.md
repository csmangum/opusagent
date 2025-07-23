# Centralized Configuration Implementation

This document describes the new centralized configuration system for OpusAgent, which consolidates all configuration data that was previously scattered across multiple files and modules.

## Overview

The centralized configuration system provides:

- **Type-safe configuration models** organized by functional domain
- **Automatic environment variable loading** with type conversion and validation
- **Singleton configuration access** for consistent behavior across the application
- **Static data loading** for JSON/YAML configuration files
- **Backward compatibility** with legacy configuration patterns
- **Configuration validation** and error reporting

## Architecture

### Core Components

1. **`opusagent/config/models.py`** - Configuration dataclasses organized by domain
2. **`opusagent/config/env_loader.py`** - Environment variable loading with type safety
3. **`opusagent/config/settings.py`** - Main configuration interface with singleton pattern
4. **`opusagent/config/__init__.py`** - Public API exports and legacy compatibility

### Configuration Domains

The configuration is organized into logical domains:

- **ServerConfig** - Server host, port, environment settings
- **OpenAIConfig** - OpenAI API key, model, base URL
- **AudioConfig** - Sample rate, channels, formats, chunk sizes
- **VADConfig** - Voice Activity Detection settings
- **TranscriptionConfig** - Speech-to-text configuration
- **WebSocketConfig** - WebSocket connection parameters
- **QualityMonitoringConfig** - Audio quality monitoring
- **LoggingConfig** - Logging levels, formats, file settings
- **MockConfig** - Testing and mock mode settings
- **TUIConfig** - Terminal UI application settings
- **StaticDataConfig** - Paths to JSON/YAML config files
- **SecurityConfig** - Security and rate limiting settings

## Usage Examples

### Basic Configuration Access

```python
from opusagent.config import get_config

# Get the complete application configuration
config = get_config()

# Access domain-specific settings
print(f"Server: {config.server.host}:{config.server.port}")
print(f"OpenAI Model: {config.openai.model}")
print(f"VAD Enabled: {config.vad.enabled}")
```

### Domain-Specific Configuration

```python
from opusagent.config import server_config, openai_config, vad_config

# Get specific domain configurations
server = server_config()
openai = openai_config()
vad = vad_config()

print(f"Server environment: {server.environment}")
print(f"OpenAI API URL: {openai.get_websocket_url()}")
print(f"VAD backend: {vad.backend}")
```

### Environment Variable Loading

All environment variables are automatically loaded and converted to appropriate types:

```bash
# Set environment variables
export OPENAI_API_KEY="sk-..."
export HOST="localhost"
export PORT="9000"
export VAD_ENABLED="true"
export LOG_LEVEL="DEBUG"
```

```python
from opusagent.config import get_config

config = get_config()
# All values are automatically loaded and type-converted
assert config.server.host == "localhost"
assert config.server.port == 9000  # Converted to int
assert config.vad.enabled == True   # Converted to bool
assert config.logging.level == LogLevel.DEBUG  # Converted to enum
```

### Configuration Validation

```python
from opusagent.config import validate_configuration, print_configuration_summary

# Validate configuration and get errors
errors = validate_configuration()
if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("✅ Configuration is valid")

# Print complete configuration summary
print_configuration_summary()
```

### Static Data Loading

```python
from opusagent.config import (
    load_scenarios, 
    load_phrases_mapping,
    get_scenarios_list,
    get_phrases_by_scenario
)

# Load static configuration files
scenarios = load_scenarios()  # From scenarios.json
phrases = load_phrases_mapping()  # From phrases_mapping.yml

# Convenience methods
scenario_list = get_scenarios_list()
customer_phrases = get_phrases_by_scenario("customer_service")
```

## Environment Variables

### Core Server Settings
- `ENV` - Environment: development, production, testing (default: production)
- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 8000)
- `LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)

### OpenAI Configuration
- `OPENAI_API_KEY` - OpenAI API key (required for production)
- `OPENAI_MODEL` - OpenAI model name (default: gpt-4o-realtime-preview-2024-12-17)
- `OPENAI_API_BASE_URL` - OpenAI API base URL (default: wss://api.openai.com)

### Audio Configuration
- `AUDIO_SAMPLE_RATE` - Audio sample rate in Hz (default: 16000)
- `AUDIO_CHANNELS` - Number of audio channels (default: 1)
- `AUDIO_FORMAT` - Audio format (default: raw/lpcm16)
- `AUDIO_CHUNK_SIZE` - Audio chunk size in bytes (default: 3200)

### VAD Configuration
- `VAD_ENABLED` - Enable Voice Activity Detection (default: true)
- `VAD_BACKEND` - VAD backend: silero, webrtc (default: silero)
- `VAD_CONFIDENCE_THRESHOLD` - VAD confidence threshold (default: 0.5)
- `VAD_DEVICE` - Processing device: cpu, cuda (default: cpu)

### Transcription Configuration
- `TRANSCRIPTION_ENABLED` - Enable transcription (default: true)
- `TRANSCRIPTION_BACKEND` - Backend: pocketsphinx, whisper (default: pocketsphinx)
- `TRANSCRIPTION_LANGUAGE` - Language code (default: en)
- `WHISPER_MODEL_SIZE` - Whisper model size (default: base)

### WebSocket Configuration
- `WEBSOCKET_MAX_CONNECTIONS` - Max concurrent connections (default: 10)
- `WEBSOCKET_PING_INTERVAL` - Ping interval in seconds (default: 20)
- `WEBSOCKET_PING_TIMEOUT` - Ping timeout in seconds (default: 30)

### Mock/Testing Configuration
- `OPUSAGENT_USE_MOCK` - Enable mock mode (default: false)
- `OPUSAGENT_MOCK_SERVER_URL` - Mock server URL (default: ws://localhost:8080)
- `USE_LOCAL_REALTIME` - Use local realtime client (default: false)

### TUI Configuration
- `TUI_HOST` - TUI server host (default: localhost)
- `TUI_PORT` - TUI server port (default: 8000)
- `TUI_VAD_ENABLED` - Enable VAD in TUI (default: true)
- `TUI_THEME` - TUI theme (default: dark)

### Quality Monitoring
- `QUALITY_MONITORING_ENABLED` - Enable quality monitoring (default: true)
- `QUALITY_MIN_SNR_DB` - Minimum SNR in dB (default: 15.0)
- `QUALITY_MAX_THD_PERCENT` - Maximum THD percentage (default: 1.0)

### Static Data Files
- `SCENARIOS_FILE` - Path to scenarios JSON file (default: scenarios.json)
- `PHRASES_MAPPING_FILE` - Path to phrases YAML file (default: opusagent/local/audio/phrases_mapping.yml)
- `AUDIO_DIRECTORY` - Audio files directory (default: opusagent/local/audio)

## Legacy Compatibility

The new system maintains backward compatibility with existing code:

### Legacy Constants
```python
from opusagent.config import get_legacy_constants

constants = get_legacy_constants()
DEFAULT_SAMPLE_RATE = constants["DEFAULT_SAMPLE_RATE"]
VOICE = constants["VOICE"]
```

### Legacy VAD Config
```python
from opusagent.config import get_legacy_vad_config

vad_config = get_legacy_vad_config()
# Returns dict in old format
```

### Legacy WebSocket Config
```python
from opusagent.config import get_legacy_websocket_config

WebSocketConfig = get_legacy_websocket_config()
# Returns object with same interface as old WebSocketConfig class
```

### Direct Legacy Imports (still work)
```python
# These still work for backward compatibility
from opusagent.config.constants import DEFAULT_SAMPLE_RATE, VOICE
from opusagent.config.logging_config import configure_logging
```

## Migration Guide

### Before (scattered configuration)
```python
# Multiple imports and manual environment variable handling
from opusagent.config.constants import DEFAULT_SAMPLE_RATE, VOICE
from opusagent.config.websocket_config import WebSocketConfig
from opusagent.vad.vad_config import load_vad_config
import os

sample_rate = DEFAULT_SAMPLE_RATE
voice = VOICE
websocket_config = WebSocketConfig()
vad_config = load_vad_config()
openai_key = os.getenv("OPENAI_API_KEY")
port = int(os.getenv("PORT", "8000"))
```

### After (centralized configuration)
```python
# Single import, type-safe access
from opusagent.config import get_config

config = get_config()
sample_rate = config.audio.sample_rate
openai_key = config.openai.api_key
websocket_settings = config.websocket
vad_settings = config.vad
port = config.server.port  # Already type-converted
```

## Testing and Development

### Setting Custom Configuration
```python
from opusagent.config import set_config
from opusagent.config.models import ApplicationConfig, ServerConfig

# Create custom config for testing
test_config = ApplicationConfig(
    server=ServerConfig(host="localhost", port=9999, debug=True)
)
set_config(test_config)
```

### Configuration Debugging
```python
from opusagent.config import print_configuration_summary, get_environment_info

# Print complete configuration overview
print_configuration_summary()

# Get environment variable information
env_info = get_environment_info()
print(f"Environment variables loaded: {env_info['environment_variables_loaded']}")
```

### Development Mode
```bash
# Enable development mode
export ENV=development
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run with development configuration
python -m opusagent.main
```

## Configuration Validation

The system automatically validates configuration on load:

- **OpenAI API key** required when not in mock mode
- **Port numbers** must be valid (1-65535)
- **Sample rates** must be positive
- **Confidence thresholds** must be between 0 and 1
- **File paths** must exist for static data files

## Benefits

1. **Type Safety** - Configuration values are properly typed and validated
2. **Single Source of Truth** - All configuration in one place
3. **Environment Flexibility** - Easy to override any setting with environment variables
4. **Developer Experience** - IDE autocomplete and type checking
5. **Backward Compatibility** - Existing code continues to work
6. **Validation** - Automatic configuration validation with clear error messages
7. **Documentation** - Self-documenting configuration with dataclasses
8. **Testing** - Easy to inject custom configuration for tests

## Performance

- **Singleton Pattern** - Configuration loaded once and cached
- **Lazy Loading** - Static data files loaded only when needed
- **LRU Cache** - Static data cached after first load
- **Type Conversion** - Environment variables converted once at startup

This centralized configuration system provides a robust, type-safe, and maintainable foundation for managing all OpusAgent configuration needs.