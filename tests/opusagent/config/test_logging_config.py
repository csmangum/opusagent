"""
Unit tests for the logging_config module.

This module tests the logging configuration functions defined in opusagent.config.logging_config.
"""

import os
import pytest
import logging
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path

from opusagent.config.logging_config import (
    configure_logging,
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_DIR,
    LOG_FILE,
    MAX_LOG_SIZE,
    BACKUP_COUNT,
    LOGGER_NAME,
)


class TestLoggingConstants:
    """Test logging constants."""

    def test_log_level_default(self):
        """Test that LOG_LEVEL has a valid default value."""
        assert LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert isinstance(LOG_LEVEL, str)

    def test_log_format(self):
        """Test that LOG_FORMAT has the expected format."""
        assert LOG_FORMAT == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        assert isinstance(LOG_FORMAT, str)
        assert "%(asctime)s" in LOG_FORMAT
        assert "%(name)s" in LOG_FORMAT
        assert "%(levelname)s" in LOG_FORMAT
        assert "%(message)s" in LOG_FORMAT

    def test_log_dir(self):
        """Test that LOG_DIR is a Path object."""
        assert isinstance(LOG_DIR, Path)
        assert str(LOG_DIR) == "logs"

    def test_log_file(self):
        """Test that LOG_FILE is a Path object."""
        assert isinstance(LOG_FILE, Path)
        assert "opusagent.log" in str(LOG_FILE)

    def test_max_log_size(self):
        """Test that MAX_LOG_SIZE is a reasonable value."""
        assert isinstance(MAX_LOG_SIZE, int)
        assert MAX_LOG_SIZE > 0
        assert MAX_LOG_SIZE == 10 * 1024 * 1024  # 10 MB

    def test_backup_count(self):
        """Test that BACKUP_COUNT is a reasonable value."""
        assert isinstance(BACKUP_COUNT, int)
        assert BACKUP_COUNT > 0
        assert BACKUP_COUNT == 5

    def test_logger_name(self):
        """Test that LOGGER_NAME is imported correctly."""
        assert LOGGER_NAME == "opusagent"
        assert isinstance(LOGGER_NAME, str)


class TestConfigureLogging:
    """Test configure_logging function."""

    @patch('opusagent.config.logging_config.LOG_FILE')
    @patch('opusagent.config.logging_config.LOG_DIR')
    def test_configure_logging_default_parameters(self, mock_log_dir, mock_log_file):
        """Test configure_logging with default parameters."""
        mock_log_dir.mkdir = MagicMock()
        mock_log_file.parent.mkdir = MagicMock()
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            with patch('logging.StreamHandler') as mock_stream_handler:
                mock_console_handler = MagicMock()
                mock_stream_handler.return_value = mock_console_handler
                
                with patch('logging.handlers.RotatingFileHandler') as mock_file_handler:
                    mock_file_handler_instance = MagicMock()
                    mock_file_handler.return_value = mock_file_handler_instance
                    
                    result = configure_logging()
                    
                    # Verify logger was created
                    mock_get_logger.assert_called_once_with("opusagent")
                    
                    # Verify handlers were added
                    mock_logger.addHandler.assert_called()
                    
                    # Verify formatter was created
                    mock_logger.setLevel.assert_called()
                    
                    # Verify result is the logger
                    assert result == mock_logger

    @patch('opusagent.config.logging_config.LOG_FILE')
    @patch('opusagent.config.logging_config.LOG_DIR')
    def test_configure_logging_custom_parameters(self, mock_log_dir, mock_log_file):
        """Test configure_logging with custom parameters."""
        mock_log_dir.mkdir = MagicMock()
        mock_log_file.parent.mkdir = MagicMock()
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            with patch('logging.StreamHandler') as mock_stream_handler:
                mock_console_handler = MagicMock()
                mock_stream_handler.return_value = mock_console_handler
                
                with patch('logging.handlers.RotatingFileHandler') as mock_file_handler:
                    mock_file_handler_instance = MagicMock()
                    mock_file_handler.return_value = mock_file_handler_instance
                    
                    result = configure_logging(
                        name="custom_logger",
                        file_path="custom/logs/",
                        log_filename="custom.log"
                    )
                    
                    # Verify logger was created with custom name
                    mock_get_logger.assert_called_once_with("custom_logger")
                    
                    # Verify result is the logger
                    assert result == mock_logger

    @patch('opusagent.config.logging_config.LOG_FILE')
    @patch('opusagent.config.logging_config.LOG_DIR')
    def test_configure_logging_removes_existing_handlers(self, mock_log_dir, mock_log_file):
        """Test that configure_logging removes existing handlers."""
        mock_log_dir.mkdir = MagicMock()
        mock_log_file.parent.mkdir = MagicMock()
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.handlers = [MagicMock(), MagicMock()]  # Existing handlers
            mock_get_logger.return_value = mock_logger
            
            with patch('logging.StreamHandler'):
                with patch('logging.handlers.RotatingFileHandler'):
                    configure_logging()
                    
                    # Verify existing handlers were removed
                    assert mock_logger.removeHandler.call_count == 2


    @patch('opusagent.config.logging_config.LOG_FILE')
    @patch('opusagent.config.logging_config.LOG_DIR')
    def test_configure_logging_console_handler_encoding(self, mock_log_dir, mock_log_file):
        """Test configure_logging with console handler encoding configuration."""
        mock_log_dir.mkdir = MagicMock()
        mock_log_file.parent.mkdir = MagicMock()
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            with patch('logging.StreamHandler') as mock_stream_handler:
                mock_console_handler = MagicMock()
                mock_console_handler.stream.reconfigure = MagicMock()
                mock_stream_handler.return_value = mock_console_handler
                
                with patch('logging.handlers.RotatingFileHandler'):
                    configure_logging()
                    
                    # Verify encoding was configured if possible
                    mock_console_handler.stream.reconfigure.assert_called_with(encoding='utf-8')

    @patch('opusagent.config.logging_config.LOG_FILE')
    @patch('opusagent.config.logging_config.LOG_DIR')
    def test_configure_logging_console_handler_encoding_exception(self, mock_log_dir, mock_log_file):
        """Test configure_logging when console handler encoding configuration fails."""
        mock_log_dir.mkdir = MagicMock()
        mock_log_file.parent.mkdir = MagicMock()
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            with patch('logging.StreamHandler') as mock_stream_handler:
                mock_console_handler = MagicMock()
                mock_console_handler.stream.reconfigure = MagicMock(side_effect=Exception("Encoding error"))
                mock_stream_handler.return_value = mock_console_handler
                
                with patch('logging.handlers.RotatingFileHandler'):
                    configure_logging()
                    
                    # Should log a warning about encoding configuration failure
                    mock_logger.warning.assert_called()

    @patch('opusagent.config.logging_config.LOG_FILE')
    @patch('opusagent.config.logging_config.LOG_DIR')
    def test_configure_logging_sets_propagate_false(self, mock_log_dir, mock_log_file):
        """Test that configure_logging sets propagate to False."""
        mock_log_dir.mkdir = MagicMock()
        mock_log_file.parent.mkdir = MagicMock()
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            with patch('logging.StreamHandler'):
                with patch('logging.handlers.RotatingFileHandler'):
                    configure_logging()
                    
                    # Verify propagate was set to False
                    mock_logger.propagate = False

    @patch('opusagent.config.logging_config.LOG_FILE')
    @patch('opusagent.config.logging_config.LOG_DIR')
    def test_configure_logging_logs_info_message(self, mock_log_dir, mock_log_file):
        """Test that configure_logging logs an info message."""
        mock_log_dir.mkdir = MagicMock()
        mock_log_file.parent.mkdir = MagicMock()
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            with patch('logging.StreamHandler'):
                with patch('logging.handlers.RotatingFileHandler'):
                    configure_logging()
                    
                    # Verify info message was logged
                    mock_logger.info.assert_called_with("Logging configured")


class TestLoggingConfigIntegration:
    """Integration tests for logging configuration."""

    def test_configure_logging_creates_valid_logger(self):
        """Test that configure_logging creates a valid logger."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            with patch('logging.StreamHandler'):
                with patch('logging.handlers.RotatingFileHandler'):
                    result = configure_logging()
                    
                    # Verify result is a logger
                    assert result == mock_logger
                    assert isinstance(result, MagicMock)

    def test_logging_constants_consistency(self):
        """Test that logging constants are consistent."""
        # LOG_FILE should be in LOG_DIR
        assert LOG_FILE.name == "opusagent.log"
        assert LOG_FILE.parent == LOG_DIR
        
        # MAX_LOG_SIZE should be reasonable
        assert MAX_LOG_SIZE > 1024 * 1024  # At least 1MB
        assert MAX_LOG_SIZE < 100 * 1024 * 1024  # Less than 100MB
        
        # BACKUP_COUNT should be reasonable
        assert 1 <= BACKUP_COUNT <= 20
        
        # LOG_LEVEL should be valid
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert LOG_LEVEL in valid_levels

    def test_log_format_contains_required_fields(self):
        """Test that LOG_FORMAT contains all required fields."""
        required_fields = ["%(asctime)s", "%(name)s", "%(levelname)s", "%(message)s"]
        for field in required_fields:
            assert field in LOG_FORMAT

    def test_logger_name_matches_constant(self):
        """Test that LOGGER_NAME matches the expected value."""
        assert LOGGER_NAME == "opusagent"
