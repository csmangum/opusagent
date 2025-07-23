"""
Centralized configuration settings for OpusAgent.

This module provides the main configuration interface for the entire application,
including singleton access to configuration and static data loading.
"""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .models import ApplicationConfig
from .env_loader import load_application_config, get_environment_info


# Global configuration instance
_config: Optional[ApplicationConfig] = None

# Cache for static data
_scenarios_cache: Optional[Dict[str, Any]] = None
_phrases_cache: Optional[Dict[str, Any]] = None
_cache_config_hash: Optional[int] = None


def get_config() -> ApplicationConfig:
    """Get the global application configuration instance."""
    global _config
    if _config is None:
        _config = load_application_config()
    return _config


def reload_config() -> ApplicationConfig:
    """Reload configuration from environment variables."""
    global _config, _scenarios_cache, _phrases_cache, _cache_config_hash
    _config = load_application_config()
    # Clear caches when configuration is reloaded
    _scenarios_cache = None
    _phrases_cache = None
    _cache_config_hash = None
    return _config


def set_config(config: ApplicationConfig) -> None:
    """Set a custom configuration instance (useful for testing)."""
    global _config, _scenarios_cache, _phrases_cache, _cache_config_hash
    _config = config
    # Clear caches when configuration is set
    _scenarios_cache = None
    _phrases_cache = None
    _cache_config_hash = None


def _get_config_hash() -> int:
    """Get a hash of the current configuration for cache invalidation."""
    config = get_config()
    # Create a hash based on the file paths that affect the cached data
    config_str = f"{config.static_data.scenarios_file}:{config.static_data.phrases_mapping_file}"
    return hash(config_str)


def _is_cache_valid() -> bool:
    """Check if the current cache is valid based on configuration."""
    global _cache_config_hash
    current_hash = _get_config_hash()
    return _cache_config_hash == current_hash


def _update_cache_hash():
    """Update the cache hash to mark cache as valid."""
    global _cache_config_hash
    _cache_config_hash = _get_config_hash()


def clear_static_data_cache():
    """Clear the static data cache (useful for testing or manual invalidation)."""
    global _scenarios_cache, _phrases_cache, _cache_config_hash
    _scenarios_cache = None
    _phrases_cache = None
    _cache_config_hash = None


def load_scenarios() -> Dict[str, Any]:
    """Load test scenarios from JSON file."""
    global _scenarios_cache
    
    # Check if cache is valid
    if _scenarios_cache is not None and _is_cache_valid():
        return _scenarios_cache
    
    config = get_config()
    scenarios_file = config.static_data.scenarios_file
    
    try:
        with open(scenarios_file, 'r', encoding='utf-8') as f:
            result = json.load(f)
            _scenarios_cache = result
            _update_cache_hash()
            return result
    except FileNotFoundError:
        result = {
            "description": "Default scenarios",
            "version": "1.0",
            "scenarios": [],
            "test_configurations": {}
        }
        _scenarios_cache = result
        _update_cache_hash()
        return result
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in scenarios file {scenarios_file}: {e}")


def load_phrases_mapping() -> Dict[str, Any]:
    """Load audio phrases mapping from YAML file."""
    global _phrases_cache
    
    # Check if cache is valid
    if _phrases_cache is not None and _is_cache_valid():
        return _phrases_cache
    
    config = get_config()
    phrases_file = config.static_data.phrases_mapping_file
    
    try:
        with open(phrases_file, 'r', encoding='utf-8') as f:
            result = yaml.safe_load(f)
            _phrases_cache = result
            _update_cache_hash()
            return result
    except FileNotFoundError:
        result = {
            "scenarios": {},
            "metadata": {
                "total_scenarios": 0,
                "total_phrases": 0,
                "generated_by": "manual",
            }
        }
        _phrases_cache = result
        _update_cache_hash()
        return result
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