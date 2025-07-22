"""
Configuration module for the real-time voice agent application.

This module provides centralized configuration management for the entire application,
including constants, logging setup, and environment-based configuration.

## New Centralized Configuration System

The new system provides:
- Type-safe configuration models organized by domain
- Environment variable loading with validation
- Singleton configuration access
- Static data loading (scenarios, phrases)
- Backward compatibility with legacy config

### Usage Examples:

```python
# Modern configuration access
from opusagent.config import get_config, server_config, openai_config
config = get_config()
print(f"Server: {config.server.host}:{config.server.port}")

# Domain-specific config access
server = server_config()
openai = openai_config()

# Legacy constants (backward compatibility)
from opusagent.config import audio_config
constants = {
    "LOGGER_NAME": "opusagent",
    "VOICE": "verse",
    "DEFAULT_SAMPLE_RATE": audio_config().sample_rate,
    "DEFAULT_CHANNELS": audio_config().channels,
    "DEFAULT_BITS_PER_SAMPLE": audio_config().bits_per_sample,
    "DEFAULT_AUDIO_CHUNK_SIZE": audio_config().chunk_size,
    "DEFAULT_AUDIO_CHUNK_SIZE_LARGE": audio_config().chunk_size_large,
}
sample_rate = constants["DEFAULT_SAMPLE_RATE"]

# Set up logging for your module
from opusagent.config.logging_config import configure_logging
logger = configure_logging()
logger.info("Application started")

# Static data access
from opusagent.config import load_scenarios, get_phrases_by_scenario
scenarios = load_scenarios()
phrases = get_phrases_by_scenario("customer_service")
```

## Legacy Support

For backward compatibility, you can still use:
```python
from opusagent.config.constants import DEFAULT_SAMPLE_RATE
from opusagent.config.websocket_config import WebSocketConfig
```
"""

# Import centralized configuration system
from .settings import (
    # Core configuration access
    get_config,
    reload_config,
    set_config,
    
    # Domain-specific config access
    server_config,
    openai_config,
    audio_config,
    vad_config,
    transcription_config,
    websocket_config,
    logging_config,
    tui_config,
    quality_config,
    mock_config,
    
    # Static data loading
    load_scenarios,
    load_phrases_mapping,
    get_scenarios_list,
    get_scenario_by_name,
    get_test_configurations,
    get_phrases_by_scenario,
    get_audio_file_path,
    
    # Utility functions
    validate_configuration,
    print_configuration_summary,
    is_mock_mode,
    is_development,
    is_production,
    

)

# Import configuration models for advanced usage
from .models import (
    ApplicationConfig,
    ServerConfig,
    OpenAIConfig,
    AudioConfig,
    VADConfig,
    TranscriptionConfig,
    WebSocketConfig,
    QualityMonitoringConfig,
    LoggingConfig,
    MockConfig,
    TUIConfig,
    StaticDataConfig,
    SecurityConfig,
    Environment,
    LogLevel,
)

# Keep legacy imports available for backward compatibility
from .constants import *
from .logging_config import configure_logging

# Export all public API
__all__ = [
    # Core configuration
    "get_config",
    "reload_config", 
    "set_config",
    
    # Domain configs
    "server_config",
    "openai_config",
    "audio_config",
    "vad_config",
    "transcription_config",
    "websocket_config",
    "logging_config",
    "tui_config", 
    "quality_config",
    "mock_config",
    
    # Static data
    "load_scenarios",
    "load_phrases_mapping",
    "get_scenarios_list",
    "get_scenario_by_name", 
    "get_test_configurations",
    "get_phrases_by_scenario",
    "get_audio_file_path",
    
    # Utilities
    "validate_configuration",
    "print_configuration_summary",
    "is_mock_mode",
    "is_development",
    "is_production",
    

    
    # Models
    "ApplicationConfig",
    "ServerConfig",
    "OpenAIConfig",
    "AudioConfig",
    "VADConfig", 
    "TranscriptionConfig",
    "WebSocketConfig",
    "QualityMonitoringConfig",
    "LoggingConfig",
    "MockConfig",
    "TUIConfig",
    "StaticDataConfig",
    "SecurityConfig",
    "Environment",
    "LogLevel",
    
    # Legacy
    "configure_logging",
] 