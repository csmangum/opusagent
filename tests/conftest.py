import pytest
import logging
import asyncio

"""
Pytest configuration file for the FastAgent framework test suite.

This file contains fixtures that are shared across multiple test files.
"""

@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test"""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    logging.basicConfig(level=logging.NOTSET)
    yield 

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close() 