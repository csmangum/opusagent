"""
Tests for WebSocket configuration module.
"""

import os
import pytest
from unittest.mock import patch

from opusagent.config.websocket_config import WebSocketConfig


class TestWebSocketConfig:
    """Test cases for WebSocketConfig class."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Store original environment variables
        self.original_env = {}
        env_vars = [
            "WEBSOCKET_MAX_CONNECTIONS",
            "WEBSOCKET_MAX_CONNECTION_AGE", 
            "WEBSOCKET_MAX_IDLE_TIME",
            "WEBSOCKET_HEALTH_CHECK_INTERVAL",
            "WEBSOCKET_MAX_SESSIONS_PER_CONNECTION",
            "WEBSOCKET_PING_INTERVAL",
            "WEBSOCKET_PING_TIMEOUT",
            "WEBSOCKET_CLOSE_TIMEOUT",
            "OPENAI_API_KEY",
            "OPENAI_MODEL",
            "OPENAI_API_BASE_URL"
        ]
        
        for var in env_vars:
            self.original_env[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]

    def teardown_method(self):
        """Clean up test environment after each test."""
        # Restore original environment variables
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]

    def test_default_values(self):
        """Test that default configuration values are set correctly."""
        assert WebSocketConfig.MAX_CONNECTIONS == 10
        assert WebSocketConfig.MAX_CONNECTION_AGE == 3600
        assert WebSocketConfig.MAX_IDLE_TIME == 300
        assert WebSocketConfig.HEALTH_CHECK_INTERVAL == 30
        assert WebSocketConfig.MAX_SESSIONS_PER_CONNECTION == 10
        assert WebSocketConfig.PING_INTERVAL == 20
        assert WebSocketConfig.PING_TIMEOUT == 30
        assert WebSocketConfig.CLOSE_TIMEOUT == 10
        assert WebSocketConfig.OPENAI_MODEL == "gpt-4o-realtime-preview-2024-12-17"
        assert WebSocketConfig.OPENAI_API_BASE_URL == "wss://api.openai.com"

    def test_environment_variable_override_integers(self):
        """Test that environment variables override default integer values."""
        os.environ["WEBSOCKET_MAX_CONNECTIONS"] = "5"
        os.environ["WEBSOCKET_MAX_CONNECTION_AGE"] = "1800"
        os.environ["WEBSOCKET_MAX_IDLE_TIME"] = "150"
        os.environ["WEBSOCKET_HEALTH_CHECK_INTERVAL"] = "15"
        os.environ["WEBSOCKET_MAX_SESSIONS_PER_CONNECTION"] = "20"
        os.environ["WEBSOCKET_PING_INTERVAL"] = "10"
        os.environ["WEBSOCKET_PING_TIMEOUT"] = "15"
        os.environ["WEBSOCKET_CLOSE_TIMEOUT"] = "5"
        
        # Reload the module to pick up environment variables
        import importlib
        import opusagent.config.websocket_config
        importlib.reload(opusagent.config.websocket_config)
        from opusagent.config.websocket_config import WebSocketConfig
        
        assert WebSocketConfig.MAX_CONNECTIONS == 5
        assert WebSocketConfig.MAX_CONNECTION_AGE == 1800
        assert WebSocketConfig.MAX_IDLE_TIME == 150
        assert WebSocketConfig.HEALTH_CHECK_INTERVAL == 15
        assert WebSocketConfig.MAX_SESSIONS_PER_CONNECTION == 20
        assert WebSocketConfig.PING_INTERVAL == 10
        assert WebSocketConfig.PING_TIMEOUT == 15
        assert WebSocketConfig.CLOSE_TIMEOUT == 5

    def test_environment_variable_override_strings(self):
        """Test that environment variables override default string values."""
        os.environ["OPENAI_MODEL"] = "gpt-4o-realtime-custom"
        os.environ["OPENAI_API_BASE_URL"] = "wss://custom.openai.com"
        os.environ["OPENAI_API_KEY"] = "sk-test123"
        
        # Reload the module to pick up environment variables
        import importlib
        import opusagent.config.websocket_config
        importlib.reload(opusagent.config.websocket_config)
        from opusagent.config.websocket_config import WebSocketConfig
        
        assert WebSocketConfig.OPENAI_MODEL == "gpt-4o-realtime-custom"
        assert WebSocketConfig.OPENAI_API_BASE_URL == "wss://custom.openai.com"
        assert WebSocketConfig.OPENAI_API_KEY == "sk-test123"

    def test_invalid_integer_environment_variable(self):
        """Test that invalid integer environment variables use defaults."""
        os.environ["WEBSOCKET_MAX_CONNECTIONS"] = "invalid"
        
        # Reload the module to pick up environment variables
        import importlib
        import opusagent.config.websocket_config
        importlib.reload(opusagent.config.websocket_config)
        from opusagent.config.websocket_config import WebSocketConfig
        
        # Should use default value when conversion fails
        assert WebSocketConfig.MAX_CONNECTIONS == 10

    def test_validate_with_api_key(self):
        """Test validate method when API key is present."""
        WebSocketConfig.OPENAI_API_KEY = "sk-test123"
        
        # Should not raise any exception
        WebSocketConfig.validate()

    def test_validate_without_api_key(self):
        """Test validate method when API key is missing."""
        WebSocketConfig.OPENAI_API_KEY = None
        
        with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is required"):
            WebSocketConfig.validate()

    def test_validate_with_empty_api_key(self):
        """Test validate method when API key is empty."""
        WebSocketConfig.OPENAI_API_KEY = ""
        
        with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is required"):
            WebSocketConfig.validate()

    def test_get_websocket_url(self):
        """Test get_websocket_url method."""
        WebSocketConfig.OPENAI_API_BASE_URL = "wss://api.openai.com"
        WebSocketConfig.OPENAI_MODEL = "gpt-4o-realtime-preview-2024-12-17"
        
        url = WebSocketConfig.get_websocket_url()
        expected = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
        
        assert url == expected

    def test_get_websocket_url_with_custom_values(self):
        """Test get_websocket_url method with custom values."""
        WebSocketConfig.OPENAI_API_BASE_URL = "wss://custom.openai.com"
        WebSocketConfig.OPENAI_MODEL = "custom-model"
        
        url = WebSocketConfig.get_websocket_url()
        expected = "wss://custom.openai.com/v1/realtime?model=custom-model"
        
        assert url == expected

    def test_get_headers_with_api_key(self):
        """Test get_headers method with API key."""
        WebSocketConfig.OPENAI_API_KEY = "sk-test123"
        
        headers = WebSocketConfig.get_headers()
        
        assert headers == {
            "Authorization": "Bearer sk-test123",
            "OpenAI-Beta": "realtime=v1"
        }

    def test_get_headers_without_api_key(self):
        """Test get_headers method without API key."""
        WebSocketConfig.OPENAI_API_KEY = None
        
        headers = WebSocketConfig.get_headers()
        
        assert headers == {
            "Authorization": "Bearer None",
            "OpenAI-Beta": "realtime=v1"
        }

    def test_to_dict(self):
        """Test to_dict method returns all configuration as dictionary."""
        WebSocketConfig.OPENAI_API_KEY = "sk-test123"
        WebSocketConfig.OPENAI_MODEL = "gpt-4o-realtime-preview-2024-12-17"
        WebSocketConfig.OPENAI_API_BASE_URL = "wss://api.openai.com"
        WebSocketConfig.MAX_CONNECTIONS = 10
        WebSocketConfig.MAX_CONNECTION_AGE = 3600
        WebSocketConfig.MAX_IDLE_TIME = 300
        WebSocketConfig.HEALTH_CHECK_INTERVAL = 30
        WebSocketConfig.MAX_SESSIONS_PER_CONNECTION = 10
        WebSocketConfig.PING_INTERVAL = 20
        WebSocketConfig.PING_TIMEOUT = 30
        WebSocketConfig.CLOSE_TIMEOUT = 10
        
        config_dict = WebSocketConfig.to_dict()
        
        expected_keys = [
            "max_connections",
            "max_connection_age",
            "max_idle_time", 
            "health_check_interval",
            "max_sessions_per_connection",
            "ping_interval",
            "ping_timeout",
            "close_timeout",
            "openai_model",
            "openai_api_base_url",
            "websocket_url"
        ]
        
        for key in expected_keys:
            assert key in config_dict
        
        assert config_dict["max_connections"] == 10
        assert config_dict["max_connection_age"] == 3600
        assert config_dict["max_idle_time"] == 300
        assert config_dict["health_check_interval"] == 30
        assert config_dict["max_sessions_per_connection"] == 10
        assert config_dict["ping_interval"] == 20
        assert config_dict["ping_timeout"] == 30
        assert config_dict["close_timeout"] == 10
        assert config_dict["openai_model"] == "gpt-4o-realtime-preview-2024-12-17"
        assert config_dict["openai_api_base_url"] == "wss://api.openai.com"
        assert config_dict["websocket_url"] == "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"

    def test_to_dict_excludes_api_key(self):
        """Test that to_dict method does not include the API key for security."""
        WebSocketConfig.OPENAI_API_KEY = "sk-secret123"
        
        config_dict = WebSocketConfig.to_dict()
        
        # API key should not be included in the dictionary
        assert "openai_api_key" not in config_dict
        assert "api_key" not in config_dict
        assert "sk-secret123" not in str(config_dict)

    def test_environment_variable_types(self):
        """Test that environment variables are properly converted to correct types."""
        # Test with valid values
        os.environ["WEBSOCKET_MAX_CONNECTIONS"] = "15"
        os.environ["WEBSOCKET_PING_INTERVAL"] = "25"
        os.environ["OPENAI_MODEL"] = "custom-model"
        
        # Reload the module to pick up environment variables
        import importlib
        import opusagent.config.websocket_config
        importlib.reload(opusagent.config.websocket_config)
        from opusagent.config.websocket_config import WebSocketConfig
        
        # Check types
        assert isinstance(WebSocketConfig.MAX_CONNECTIONS, int)
        assert isinstance(WebSocketConfig.PING_INTERVAL, int)
        assert isinstance(WebSocketConfig.OPENAI_MODEL, str)
        
        # Check values
        assert WebSocketConfig.MAX_CONNECTIONS == 15
        assert WebSocketConfig.PING_INTERVAL == 25
        assert WebSocketConfig.OPENAI_MODEL == "custom-model"

    def test_zero_and_negative_values(self):
        """Test handling of zero and negative values in environment variables."""
        os.environ["WEBSOCKET_MAX_CONNECTIONS"] = "0"
        os.environ["WEBSOCKET_PING_INTERVAL"] = "-5"
        
        # Reload the module to pick up environment variables
        import importlib
        import opusagent.config.websocket_config
        importlib.reload(opusagent.config.websocket_config)
        from opusagent.config.websocket_config import WebSocketConfig
        
        # Should accept zero and negative values (validation is separate)
        assert WebSocketConfig.MAX_CONNECTIONS == 0
        assert WebSocketConfig.PING_INTERVAL == -5

    def test_very_large_values(self):
        """Test handling of very large values in environment variables."""
        os.environ["WEBSOCKET_MAX_CONNECTION_AGE"] = "999999999"
        
        # Reload the module to pick up environment variables
        import importlib
        import opusagent.config.websocket_config
        importlib.reload(opusagent.config.websocket_config)
        from opusagent.config.websocket_config import WebSocketConfig
        
        assert WebSocketConfig.MAX_CONNECTION_AGE == 999999999

    def test_whitespace_in_string_values(self):
        """Test handling of whitespace in string environment variables."""
        os.environ["OPENAI_MODEL"] = "  gpt-4o-realtime-preview-2024-12-17  "
        os.environ["OPENAI_API_KEY"] = "  sk-test123  "
        
        # Reload the module to pick up environment variables
        import importlib
        import opusagent.config.websocket_config
        importlib.reload(opusagent.config.websocket_config)
        from opusagent.config.websocket_config import WebSocketConfig
        
        # Should preserve whitespace (trimming is application-specific)
        assert WebSocketConfig.OPENAI_MODEL == "  gpt-4o-realtime-preview-2024-12-17  "
        assert WebSocketConfig.OPENAI_API_KEY == "  sk-test123  "

    def test_boolean_like_string_values(self):
        """Test handling of boolean-like string values."""
        os.environ["OPENAI_MODEL"] = "true"
        
        # Reload the module to pick up environment variables
        import importlib
        import opusagent.config.websocket_config
        importlib.reload(opusagent.config.websocket_config)
        from opusagent.config.websocket_config import WebSocketConfig
        
        # Should be treated as string, not boolean
        assert WebSocketConfig.OPENAI_MODEL == "true"
        assert isinstance(WebSocketConfig.OPENAI_MODEL, str)

    def test_class_methods_are_classmethods(self):
        """Test that configuration methods work as class methods."""
        # Set up test values
        WebSocketConfig.OPENAI_API_KEY = "sk-test123"
        WebSocketConfig.OPENAI_MODEL = "test-model"
        WebSocketConfig.OPENAI_API_BASE_URL = "wss://test.openai.com"
        
        # Test that methods can be called on the class directly
        url = WebSocketConfig.get_websocket_url()
        headers = WebSocketConfig.get_headers()
        config_dict = WebSocketConfig.to_dict()
        
        assert isinstance(url, str)
        assert isinstance(headers, dict)
        assert isinstance(config_dict, dict)
        
        # Test validation as class method
        WebSocketConfig.validate()  # Should not raise

    def test_immutable_defaults(self):
        """Test that default values are not accidentally modified."""
        original_max_connections = WebSocketConfig.MAX_CONNECTIONS
        original_model = WebSocketConfig.OPENAI_MODEL
        
        # Simulate some operations
        WebSocketConfig.to_dict()
        WebSocketConfig.get_websocket_url()
        
        # Values should remain unchanged
        assert WebSocketConfig.MAX_CONNECTIONS == original_max_connections
        assert WebSocketConfig.OPENAI_MODEL == original_model
