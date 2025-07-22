"""
Centralized configuration settings for OpusAgent.

This module provides the main configuration interface for the entire application,
including singleton access to configuration and static data loading.
"""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from functools import lru_cache

from .models import ApplicationConfig
from .env_loader import load_application_config, get_environment_info


# Global configuration instance
_config: Optional[ApplicationConfig] = None


def get_config() -> ApplicationConfig:
    """Get the global application configuration instance."""
    global _config
    if _config is None:
        _config = load_application_config()
    return _config


def reload_config() -> ApplicationConfig:
    """Reload configuration from environment variables."""
    global _config
    _config = load_application_config()
    return _config


def set_config(config: ApplicationConfig) -> None:
    """Set a custom configuration instance (useful for testing)."""
    global _config
    _config = config


@lru_cache(maxsize=1)
def load_scenarios() -> Dict[str, Any]:
    """Load test scenarios from JSON file."""
    config = get_config()
    scenarios_file = config.static_data.scenarios_file
    
    try:
        with open(scenarios_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "description": "Default scenarios",
            "version": "1.0",
            "scenarios": [],
            "test_configurations": {}
        }
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in scenarios file {scenarios_file}: {e}")


@lru_cache(maxsize=1)
def load_phrases_mapping() -> Dict[str, Any]:
    """Load audio phrases mapping from YAML file."""
    config = get_config()
    phrases_file = config.static_data.phrases_mapping_file
    
    try:
        with open(phrases_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {
            "scenarios": {},
            "metadata": {
                "total_scenarios": 0,
                "total_phrases": 0,
                "generated_by": "manual",
            }
        }
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in phrases file {phrases_file}: {e}")


def get_scenarios_list() -> List[Dict[str, Any]]:
    """Get list of available test scenarios."""
    scenarios_data = load_scenarios()
    return scenarios_data.get("scenarios", [])


def get_scenario_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get a specific scenario by name."""
    scenarios = get_scenarios_list()
    for scenario in scenarios:
        if scenario.get("name") == name:
            return scenario
    return None


def get_test_configurations() -> Dict[str, Any]:
    """Get available test configurations."""
    scenarios_data = load_scenarios()
    return scenarios_data.get("test_configurations", {})


def get_phrases_by_scenario(scenario: str) -> List[Dict[str, Any]]:
    """Get audio phrases for a specific scenario."""
    phrases_data = load_phrases_mapping()
    scenarios = phrases_data.get("scenarios", {})
    scenario_data = scenarios.get(scenario, {})
    return scenario_data.get("phrases", [])


def get_audio_file_path(scenario: str, filename: str) -> Path:
    """Get full path to an audio file."""
    config = get_config()
    audio_dir = config.static_data.audio_directory
    return audio_dir / scenario / filename


def validate_configuration() -> List[str]:
    """Validate the current configuration and return any errors."""
    config = get_config()
    errors = config.validate()
    
    # Check static data files
    if not config.static_data.scenarios_file.exists():
        errors.append(f"Scenarios file not found: {config.static_data.scenarios_file}")
    
    if not config.static_data.phrases_mapping_file.exists():
        errors.append(f"Phrases mapping file not found: {config.static_data.phrases_mapping_file}")
    
    if not config.static_data.audio_directory.exists():
        errors.append(f"Audio directory not found: {config.static_data.audio_directory}")
    
    return errors


def print_configuration_summary() -> None:
    """Print a summary of the current configuration."""
    config = get_config()
    env_info = get_environment_info()
    
    print("=== OpusAgent Configuration Summary ===")
    print(f"Environment: {config.server.environment.value}")
    print(f"Server: {config.server.host}:{config.server.port}")
    print(f"Mock mode: {config.mock.enabled}")
    print(f"OpenAI model: {config.openai.model}")
    print(f"VAD enabled: {config.vad.enabled} ({config.vad.backend})")
    print(f"Transcription: {config.transcription.enabled} ({config.transcription.backend})")
    print(f"Log level: {config.logging.level.value}")
    print(f"Audio format: {config.audio.format} @ {config.audio.sample_rate}Hz")
    print(f"Environment variables loaded: {env_info['environment_variables_loaded']}")
    print(f".env file present: {env_info['dotenv_loaded']}")
    
    # Validation
    errors = validate_configuration()
    if errors:
        print("\n⚠️  Configuration Issues:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✅ Configuration is valid")


def get_legacy_constants() -> Dict[str, Any]:
    """Get legacy constants for backward compatibility."""
    config = get_config()
    
    return {
        # From constants.py
        "LOGGER_NAME": "opusagent",
        "VOICE": "verse",
        "DEFAULT_SAMPLE_RATE": config.audio.sample_rate,
        "DEFAULT_CHANNELS": config.audio.channels,
        "DEFAULT_BITS_PER_SAMPLE": config.audio.bits_per_sample,
        "DEFAULT_AUDIO_CHUNK_SIZE": config.audio.chunk_size,
        "DEFAULT_AUDIO_CHUNK_SIZE_LARGE": config.audio.chunk_size_large,
        "DEFAULT_VAD_CHUNK_SIZE": config.vad.chunk_size,
        "DEFAULT_TRANSCRIPTION_BACKEND": config.transcription.backend,
        "DEFAULT_TRANSCRIPTION_LANGUAGE": config.transcription.language,
        "DEFAULT_WHISPER_MODEL_SIZE": config.transcription.model_size,
        "DEFAULT_TRANSCRIPTION_CONFIDENCE_THRESHOLD": config.transcription.confidence_threshold,
        "DEFAULT_TRANSCRIPTION_CHUNK_DURATION": config.transcription.chunk_duration,
        "SPEECH_START_THRESHOLD": config.vad.speech_start_threshold,
        "SPEECH_STOP_THRESHOLD": config.vad.speech_stop_threshold,
    }


def get_legacy_vad_config() -> Dict[str, Any]:
    """Get VAD configuration in legacy format for backward compatibility."""
    config = get_config()
    
    return {
        'backend': config.vad.backend,
        'sample_rate': config.vad.sample_rate,
        'threshold': config.vad.confidence_threshold,
        'silence_threshold': config.vad.silence_threshold,
        'min_speech_duration_ms': config.vad.min_speech_duration_ms,
        'speech_start_threshold': config.vad.speech_start_threshold,
        'speech_stop_threshold': config.vad.speech_stop_threshold,
        'device': config.vad.device,
        'chunk_size': config.vad.chunk_size,
        'confidence_history_size': config.vad.confidence_history_size,
        'force_stop_timeout_ms': config.vad.force_stop_timeout_ms,
    }


def get_legacy_websocket_config() -> object:
    """Get WebSocket configuration in legacy format for backward compatibility."""
    config = get_config()
    
    class LegacyWebSocketConfig:
        def __init__(self, ws_config):
            self.MAX_CONNECTIONS = ws_config.max_connections
            self.MAX_CONNECTION_AGE = ws_config.max_connection_age
            self.MAX_IDLE_TIME = ws_config.max_idle_time
            self.HEALTH_CHECK_INTERVAL = ws_config.health_check_interval
            self.MAX_SESSIONS_PER_CONNECTION = ws_config.max_sessions_per_connection
            self.PING_INTERVAL = ws_config.ping_interval
            self.PING_TIMEOUT = ws_config.ping_timeout
            self.CLOSE_TIMEOUT = ws_config.close_timeout
            self.OPENAI_MODEL = config.openai.model
            self.OPENAI_API_KEY = config.openai.api_key
            self.OPENAI_API_BASE_URL = config.openai.base_url
        
        def get_websocket_url(self) -> str:
            return config.openai.get_websocket_url()
        
        def get_headers(self) -> Dict[str, str]:
            return config.openai.get_headers()
        
        def validate(self) -> None:
            errors = config.validate()
            if errors:
                raise ValueError("Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))
        
        def to_dict(self) -> Dict[str, Any]:
            return {
                "max_connections": self.MAX_CONNECTIONS,
                "max_connection_age": self.MAX_CONNECTION_AGE,
                "max_idle_time": self.MAX_IDLE_TIME,
                "health_check_interval": self.HEALTH_CHECK_INTERVAL,
                "max_sessions_per_connection": self.MAX_SESSIONS_PER_CONNECTION,
                "ping_interval": self.PING_INTERVAL,
                "ping_timeout": self.PING_TIMEOUT,
                "close_timeout": self.CLOSE_TIMEOUT,
                "openai_model": self.OPENAI_MODEL,
                "openai_api_base_url": self.OPENAI_API_BASE_URL,
                "websocket_url": self.get_websocket_url(),
            }
    
    return LegacyWebSocketConfig(config.websocket)


# Convenience aliases for common configurations
def server_config():
    """Get server configuration."""
    return get_config().server


def openai_config():
    """Get OpenAI configuration."""
    return get_config().openai


def audio_config():
    """Get audio configuration."""
    return get_config().audio


def vad_config():
    """Get VAD configuration."""
    return get_config().vad


def transcription_config():
    """Get transcription configuration."""
    return get_config().transcription


def websocket_config():
    """Get WebSocket configuration."""
    return get_config().websocket


def logging_config():
    """Get logging configuration."""
    return get_config().logging


def tui_config():
    """Get TUI configuration."""
    return get_config().tui


def quality_config():
    """Get quality monitoring configuration."""
    return get_config().quality


def mock_config():
    """Get mock configuration."""
    return get_config().mock


def is_mock_mode() -> bool:
    """Check if running in mock mode."""
    return get_config().mock.enabled


def is_development() -> bool:
    """Check if running in development mode."""
    return get_config().is_development()


def is_production() -> bool:
    """Check if running in production mode."""
    return get_config().is_production()