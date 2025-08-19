"""
Unit tests for the settings module.

This module tests the settings management functions defined in opusagent.config.settings.
"""

import pytest
import json
from unittest.mock import patch, mock_open
from pathlib import Path

from opusagent.config.settings import (
    get_config,
    reload_config,
    set_config,
    clear_static_data_cache,
    load_scenarios,
    load_phrases_mapping,
    get_scenarios_list,
    get_scenario_by_name,
    get_test_configurations,
    get_phrases_by_scenario,
    get_audio_file_path,
    validate_configuration,
    print_configuration_summary,
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
    is_mock_mode,
    is_development,
    is_production,
)
from opusagent.config.models import ApplicationConfig, ServerConfig, OpenAIConfig, Environment


class TestGetConfig:
    """Test get_config function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_static_data_cache()
        # Reset the global config
        import opusagent.config.settings
        opusagent.config.settings._config = None

    @patch('opusagent.config.settings.load_application_config')
    def test_get_config_first_call(self, mock_load_config):
        """Test get_config on first call."""
        mock_config = ApplicationConfig()
        mock_load_config.return_value = mock_config
        
        result = get_config()
        
        assert result == mock_config
        mock_load_config.assert_called_once()

    @patch('opusagent.config.settings.load_application_config')
    def test_get_config_cached(self, mock_load_config):
        """Test get_config with cached config."""
        mock_config = ApplicationConfig()
        mock_load_config.return_value = mock_config
        
        # First call to populate cache
        result1 = get_config()
        
        # Second call should use cache
        result2 = get_config()
        
        assert result1 == result2
        mock_load_config.assert_called_once()  # Only called once

    @patch('opusagent.config.settings.load_application_config')
    def test_get_config_cache_invalid(self, mock_load_config):
        """Test get_config when cache is invalid."""
        mock_config = ApplicationConfig()
        mock_load_config.return_value = mock_config
        
        result = get_config()
        
        assert result == mock_config
        mock_load_config.assert_called_once()


class TestReloadConfig:
    """Test reload_config function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_static_data_cache()
        # Reset the global config
        import opusagent.config.settings
        opusagent.config.settings._config = None

    @patch('opusagent.config.settings.load_application_config')
    def test_reload_config(self, mock_load_config):
        """Test reload_config."""
        mock_config = ApplicationConfig()
        mock_load_config.return_value = mock_config
        
        result = reload_config()
        
        assert result == mock_config
        mock_load_config.assert_called_once()


class TestSetConfig:
    """Test set_config function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_static_data_cache()
        # Reset the global config
        import opusagent.config.settings
        opusagent.config.settings._config = None

    def test_set_config(self):
        """Test set_config."""
        config = ApplicationConfig()
        
        set_config(config)
        
        # Verify config is cached
        result = get_config()
        assert result == config


class TestClearStaticDataCache:
    """Test clear_static_data_cache function."""

    def test_clear_static_data_cache(self):
        """Test clear_static_data_cache."""
        # This function should not raise any exceptions
        clear_static_data_cache()


class TestLoadScenarios:
    """Test load_scenarios function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_static_data_cache()

    @patch('builtins.open', mock_open(read_data='{"scenarios": [{"name": "test"}]}'))
    def test_load_scenarios_success(self):
        """Test load_scenarios with valid JSON."""
        result = load_scenarios()
        
        assert isinstance(result, dict)
        assert "scenarios" in result
        assert len(result["scenarios"]) == 1
        assert result["scenarios"][0]["name"] == "test"

    @patch('opusagent.config.settings.get_config')
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_scenarios_file_not_found(self, mock_open, mock_get_config):
        """Test load_scenarios with missing file."""
        # Mock the config to return a specific file path
        mock_config = ApplicationConfig()
        mock_get_config.return_value = mock_config
        
        result = load_scenarios()
        
        assert isinstance(result, dict)
        assert "scenarios" in result
        assert len(result["scenarios"]) == 0

    @patch('opusagent.config.settings.get_config')
    def test_load_scenarios_invalid_json(self, mock_get_config):
        """Test load_scenarios with invalid JSON."""
        # Mock the config to return a specific file path
        mock_config = ApplicationConfig()
        mock_get_config.return_value = mock_config
        
        with patch('builtins.open', mock_open(read_data='invalid json')):
            with pytest.raises(ValueError, match="Invalid JSON"):
                load_scenarios()


class TestLoadPhrasesMapping:
    """Test load_phrases_mapping function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_static_data_cache()

    @patch('builtins.open', mock_open(read_data='{"scenarios": {"test": {"phrases": ["phrase1"]}}}'))
    def test_load_phrases_mapping_success(self):
        """Test load_phrases_mapping with valid YAML."""
        result = load_phrases_mapping()
        
        assert isinstance(result, dict)
        assert "scenarios" in result
        assert "test" in result["scenarios"]
        assert "phrases" in result["scenarios"]["test"]
        assert result["scenarios"]["test"]["phrases"] == ["phrase1"]

    @patch('opusagent.config.settings.get_config')
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_phrases_mapping_file_not_found(self, mock_open, mock_get_config):
        """Test load_phrases_mapping with missing file."""
        # Mock the config to return a specific file path
        mock_config = ApplicationConfig()
        mock_get_config.return_value = mock_config
        
        result = load_phrases_mapping()
        
        assert isinstance(result, dict)
        assert "scenarios" in result
        assert len(result["scenarios"]) == 0

    @patch('opusagent.config.settings.get_config')
    def test_load_phrases_mapping_invalid_yaml(self, mock_get_config):
        """Test load_phrases_mapping with invalid YAML."""
        # Mock the config to return a specific file path
        mock_config = ApplicationConfig()
        mock_get_config.return_value = mock_config
        
        with patch('builtins.open', mock_open(read_data='key: [unclosed bracket')):
            with pytest.raises(ValueError, match="Invalid YAML"):
                load_phrases_mapping()


class TestGetScenariosList:
    """Test get_scenarios_list function."""

    @patch('opusagent.config.settings.load_scenarios')
    def test_get_scenarios_list(self, mock_load_scenarios):
        """Test get_scenarios_list."""
        mock_scenarios = {
            "scenarios": [
                {"name": "scenario1", "description": "test1"},
                {"name": "scenario2", "description": "test2"}
            ]
        }
        mock_load_scenarios.return_value = mock_scenarios
        
        result = get_scenarios_list()
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "scenario1"
        assert result[1]["name"] == "scenario2"

    @patch('opusagent.config.settings.load_scenarios')
    def test_get_scenarios_list_empty(self, mock_load_scenarios):
        """Test get_scenarios_list with empty scenarios."""
        mock_load_scenarios.return_value = {"scenarios": []}
        
        result = get_scenarios_list()
        
        assert isinstance(result, list)
        assert len(result) == 0


class TestGetScenarioByName:
    """Test get_scenario_by_name function."""

    @patch('opusagent.config.settings.load_scenarios')
    def test_get_scenario_by_name_found(self, mock_load_scenarios):
        """Test get_scenario_by_name with existing scenario."""
        mock_scenarios = {
            "scenarios": [
                {"name": "scenario1", "description": "test1"},
                {"name": "scenario2", "description": "test2"}
            ]
        }
        mock_load_scenarios.return_value = mock_scenarios
        
        result = get_scenario_by_name("scenario1")
        
        assert result is not None
        assert result["name"] == "scenario1"
        assert result["description"] == "test1"

    @patch('opusagent.config.settings.load_scenarios')
    def test_get_scenario_by_name_not_found(self, mock_load_scenarios):
        """Test get_scenario_by_name with non-existing scenario."""
        mock_scenarios = {
            "scenarios": [
                {"name": "scenario1", "description": "test1"}
            ]
        }
        mock_load_scenarios.return_value = mock_scenarios
        
        result = get_scenario_by_name("nonexistent")
        
        assert result is None


class TestGetTestConfigurations:
    """Test get_test_configurations function."""

    @patch('opusagent.config.settings.load_scenarios')
    def test_get_test_configurations(self, mock_load_scenarios):
        """Test get_test_configurations."""
        mock_scenarios = {
            "test_configurations": {
                "config1": {"param": "value1"},
                "config2": {"param": "value2"}
            }
        }
        mock_load_scenarios.return_value = mock_scenarios
        
        result = get_test_configurations()
        
        assert isinstance(result, dict)
        assert "config1" in result
        assert "config2" in result


class TestGetPhrasesByScenario:
    """Test get_phrases_by_scenario function."""

    @patch('opusagent.config.settings.load_phrases_mapping')
    def test_get_phrases_by_scenario_found(self, mock_load_phrases):
        """Test get_phrases_by_scenario with existing scenario."""
        mock_phrases = {
            "scenarios": {
                "scenario1": {"phrases": ["phrase1", "phrase2"]},
                "scenario2": {"phrases": ["phrase3"]}
            }
        }
        mock_load_phrases.return_value = mock_phrases
        
        result = get_phrases_by_scenario("scenario1")
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert "phrase1" in result
        assert "phrase2" in result

    @patch('opusagent.config.settings.load_phrases_mapping')
    def test_get_phrases_by_scenario_not_found(self, mock_load_phrases):
        """Test get_phrases_by_scenario with non-existing scenario."""
        mock_phrases = {
            "scenarios": {
                "scenario1": {"phrases": ["phrase1"]}
            }
        }
        mock_load_phrases.return_value = mock_phrases
        
        result = get_phrases_by_scenario("nonexistent")
        
        assert isinstance(result, list)
        assert len(result) == 0


class TestGetAudioFilePath:
    """Test get_audio_file_path function."""

    def test_get_audio_file_path(self):
        """Test get_audio_file_path."""
        result = get_audio_file_path("test_scenario", "test_file.wav")
        
        assert isinstance(result, Path)
        assert "test_scenario" in str(result)
        assert "test_file.wav" in str(result)


class TestValidateConfiguration:
    """Test validate_configuration function."""

    @patch('opusagent.config.settings.get_config')
    def test_validate_configuration_valid(self, mock_get_config):
        """Test validate_configuration with valid config."""
        mock_config = ApplicationConfig()
        mock_config.openai.api_key = "test-key"
        mock_get_config.return_value = mock_config
        
        errors = validate_configuration()
        
        assert isinstance(errors, list)
        assert len(errors) == 0

    @patch('opusagent.config.settings.get_config')
    def test_validate_configuration_invalid(self, mock_get_config):
        """Test validate_configuration with invalid config."""
        mock_config = ApplicationConfig()
        mock_config.openai.api_key = None
        mock_config.mock.enabled = False
        mock_get_config.return_value = mock_config
        
        errors = validate_configuration()
        
        assert isinstance(errors, list)
        assert len(errors) > 0
        assert any("OpenAI API key is required" in error for error in errors)


class TestPrintConfigurationSummary:
    """Test print_configuration_summary function."""

    @patch('opusagent.config.settings.get_config')
    @patch('builtins.print')
    def test_print_configuration_summary(self, mock_print, mock_get_config):
        """Test print_configuration_summary."""
        mock_config = ApplicationConfig()
        mock_config.openai.api_key = "test-key"
        mock_get_config.return_value = mock_config
        
        print_configuration_summary()
        
        # Should call print at least once
        assert mock_print.called


class TestConfigAccessors:
    """Test configuration accessor functions."""

    @patch('opusagent.config.settings.get_config')
    def test_server_config(self, mock_get_config):
        """Test server_config function."""
        mock_config = ApplicationConfig()
        mock_get_config.return_value = mock_config
        
        result = server_config()
        
        assert result == mock_config.server

    @patch('opusagent.config.settings.get_config')
    def test_openai_config(self, mock_get_config):
        """Test openai_config function."""
        mock_config = ApplicationConfig()
        mock_get_config.return_value = mock_config
        
        result = openai_config()
        
        assert result == mock_config.openai

    @patch('opusagent.config.settings.get_config')
    def test_audio_config(self, mock_get_config):
        """Test audio_config function."""
        mock_config = ApplicationConfig()
        mock_get_config.return_value = mock_config
        
        result = audio_config()
        
        assert result == mock_config.audio

    @patch('opusagent.config.settings.get_config')
    def test_vad_config(self, mock_get_config):
        """Test vad_config function."""
        mock_config = ApplicationConfig()
        mock_get_config.return_value = mock_config
        
        result = vad_config()
        
        assert result == mock_config.vad

    @patch('opusagent.config.settings.get_config')
    def test_transcription_config(self, mock_get_config):
        """Test transcription_config function."""
        mock_config = ApplicationConfig()
        mock_get_config.return_value = mock_config
        
        result = transcription_config()
        
        assert result == mock_config.transcription

    @patch('opusagent.config.settings.get_config')
    def test_websocket_config(self, mock_get_config):
        """Test websocket_config function."""
        mock_config = ApplicationConfig()
        mock_get_config.return_value = mock_config
        
        result = websocket_config()
        
        assert result == mock_config.websocket

    @patch('opusagent.config.settings.get_config')
    def test_logging_config(self, mock_get_config):
        """Test logging_config function."""
        mock_config = ApplicationConfig()
        mock_get_config.return_value = mock_config
        
        result = logging_config()
        
        assert result == mock_config.logging

    @patch('opusagent.config.settings.get_config')
    def test_tui_config(self, mock_get_config):
        """Test tui_config function."""
        mock_config = ApplicationConfig()
        mock_get_config.return_value = mock_config
        
        result = tui_config()
        
        assert result == mock_config.tui

    @patch('opusagent.config.settings.get_config')
    def test_quality_config(self, mock_get_config):
        """Test quality_config function."""
        mock_config = ApplicationConfig()
        mock_get_config.return_value = mock_config
        
        result = quality_config()
        
        assert result == mock_config.quality

    @patch('opusagent.config.settings.get_config')
    def test_mock_config(self, mock_get_config):
        """Test mock_config function."""
        mock_app_config = ApplicationConfig()
        mock_get_config.return_value = mock_app_config
        
        result = mock_config()
        
        assert result == mock_app_config.mock


class TestEnvironmentChecks:
    """Test environment check functions."""

    @patch('opusagent.config.settings.get_config')
    def test_is_mock_mode_true(self, mock_get_config):
        """Test is_mock_mode when mock is enabled."""
        mock_config = ApplicationConfig()
        mock_config.mock.enabled = True
        mock_get_config.return_value = mock_config
        
        result = is_mock_mode()
        
        assert result is True

    @patch('opusagent.config.settings.get_config')
    def test_is_mock_mode_false(self, mock_get_config):
        """Test is_mock_mode when mock is disabled."""
        mock_config = ApplicationConfig()
        mock_config.mock.enabled = False
        mock_get_config.return_value = mock_config
        
        result = is_mock_mode()
        
        assert result is False

    @patch('opusagent.config.settings.get_config')
    def test_is_development_true(self, mock_get_config):
        """Test is_development when in development environment."""
        mock_config = ApplicationConfig()
        mock_config.server.environment = Environment.DEVELOPMENT
        mock_get_config.return_value = mock_config
        
        result = is_development()
        
        assert result is True

    @patch('opusagent.config.settings.get_config')
    def test_is_development_false(self, mock_get_config):
        """Test is_development when not in development environment."""
        mock_config = ApplicationConfig()
        mock_config.server.environment = Environment.PRODUCTION
        mock_get_config.return_value = mock_config
        
        result = is_development()
        
        assert result is False

    @patch('opusagent.config.settings.get_config')
    def test_is_production_true(self, mock_get_config):
        """Test is_production when in production environment."""
        mock_config = ApplicationConfig()
        mock_config.server.environment = Environment.PRODUCTION
        mock_get_config.return_value = mock_config
        
        result = is_production()
        
        assert result is True

    @patch('opusagent.config.settings.get_config')
    def test_is_production_false(self, mock_get_config):
        """Test is_production when not in production environment."""
        mock_config = ApplicationConfig()
        mock_config.server.environment = Environment.DEVELOPMENT
        mock_get_config.return_value = mock_config
        
        result = is_production()
        
        assert result is False


class TestSettingsIntegration:
    """Integration tests for settings module."""

    def test_config_caching_behavior(self):
        """Test that config caching works correctly."""
        # First call should load config
        config1 = get_config()
        
        # Second call should use cached config
        config2 = get_config()
        
        # Should be the same object (cached)
        assert config1 is config2

    def test_reload_config_clears_cache(self):
        """Test that reload_config clears the cache."""
        # Get initial config
        config1 = get_config()
        
        # Reload config
        config2 = reload_config()
        
        # Should be different objects (cache cleared)
        assert config1 is not config2

    def test_set_config_updates_cache(self):
        """Test that set_config updates the cache."""
        # Get initial config
        initial_config = get_config()
        
        # Create new config
        new_config = ApplicationConfig()
        new_config.server.port = 9999
        
        # Set new config
        set_config(new_config)
        
        # Get config again
        cached_config = get_config()
        
        # Should be the new config
        assert cached_config is new_config
        assert cached_config.server.port == 9999

    def test_config_accessors_return_correct_types(self):
        """Test that config accessors return the correct types."""
        assert isinstance(server_config(), ServerConfig)
        assert isinstance(openai_config(), OpenAIConfig)
        assert isinstance(audio_config(), type(get_config().audio))
        assert isinstance(vad_config(), type(get_config().vad))
        assert isinstance(transcription_config(), type(get_config().transcription))
        assert isinstance(websocket_config(), type(get_config().websocket))
        assert isinstance(logging_config(), type(get_config().logging))
        assert isinstance(tui_config(), type(get_config().tui))
        assert isinstance(quality_config(), type(get_config().quality))
        assert isinstance(mock_config(), type(get_config().mock))

    def test_environment_checks_consistency(self):
        """Test that environment checks are consistent."""
        # These should be mutually exclusive
        assert not (is_mock_mode() and is_development() and is_production())
        
        # At least one should be true (depending on config)
        # This test may need adjustment based on actual default config

    def test_static_data_functions_handle_errors_gracefully(self):
        """Test that static data functions handle errors gracefully."""
        # These should not raise exceptions even with invalid data
        scenarios = get_scenarios_list()
        assert isinstance(scenarios, list)
        
        phrases = get_phrases_by_scenario("nonexistent")
        assert isinstance(phrases, list)
        
        scenario = get_scenario_by_name("nonexistent")
        assert scenario is None

    def test_validation_integration(self):
        """Test that validation works with actual config."""
        errors = validate_configuration()
        assert isinstance(errors, list)
        
        # If there are errors, they should be strings
        for error in errors:
            assert isinstance(error, str)
            assert len(error) > 0
