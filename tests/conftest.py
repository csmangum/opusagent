import pytest
import logging
import asyncio
import os
from fastapi import FastAPI
from fastapi.testclient import TestClient

"""
Pytest configuration file for the OpusAgent framework test suite.

This file contains fixtures that are shared across multiple test files.
"""

# Load environment variables for tests
try:
    from opusagent.config.env_loader import load_env_file
    load_env_file()
except ImportError:
    # If opusagent is not available, try to load .env file directly
    from dotenv import load_dotenv
    load_dotenv()

@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test"""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    logging.basicConfig(level=logging.NOTSET)
    yield 

# Removed custom event_loop fixture to avoid conflicts with pytest-asyncio
# pytest-asyncio will provide its own event_loop fixture

@pytest.fixture(autouse=True)
def skip_integration_when_no_api_key(request):
    if request.node.get_closest_marker("integration") and not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("Skipping integration tests: OPENAI_API_KEY not set")

@pytest.fixture
def app():
    """Create a FastAPI application instance for testing."""
    app = FastAPI()
    
    @app.get("/")
    async def index():
        return {"message": "Telephony Bridge is running!"}
        
    return app

@pytest.fixture
def test_client(app):
    """Create a TestClient instance for testing FastAPI endpoints."""
    return TestClient(app) 