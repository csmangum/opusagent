"""
Configure logging for the application.

This module provides a consistent logging configuration across the entire
application, ensuring log messages are formatted correctly and directed
to the appropriate outputs (console, file, etc.).
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from opusagent.config.constants import LOGGER_NAME

# Log levels
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Log file configuration
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "opusagent.log"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5


def configure_logging(name: str = LOGGER_NAME, file_path: str = "logs/", log_filename: str = "opusagent.log"):
    """
    Configure the application logger with console and file handlers.
    
    Returns:
        logging.Logger: The configured logger instance
    """
    global LOG_FILE
    LOG_FILE = Path(file_path) / log_filename

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Remove existing handlers if any
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    # Set encoding to utf-8 if possible (Python 3.7+)
    if hasattr(console_handler.stream, 'reconfigure'):
        try:
            console_handler.stream.reconfigure(encoding='utf-8')  # type: ignore
        except Exception as e:
            logger.warning(f"Could not reconfigure console stream encoding: {e}")
    logger.addHandler(console_handler)
    
    # Create file handler if log directory exists or can be created
    try:
        # Create logs directory if it doesn't exist
        LOG_DIR.mkdir(exist_ok=True)
        
        # Create rotating file handler
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not set up file logging: {e}")
    
    # Prevent log propagation to root logger
    logger.propagate = False
    
    logger.info("Logging configured")
    return logger
