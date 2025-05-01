import os
import logging
import pytest
from dotenv import load_dotenv
from fastagent.bot.realtime_client import RealtimeClient

# Load environment variables (including OPENAI_API_KEY)
load_dotenv()
logging.basicConfig(level=logging.DEBUG)
API_KEY = os.getenv("OPENAI_API_KEY")

@pytest.mark.asyncio
@pytest.mark.integration
async def test_connect_creates_session():
    """
    Verify that the RealtimeClient can connect to the OpenAI Realtime API
    and that a session_id is assigned.
    """
    client = RealtimeClient(
        api_key=API_KEY,
        model="gpt-4o-realtime-preview",
        voice="alloy",
        log_level=logging.DEBUG,
    )
    connected = await client.connect()
    assert connected, "Client failed to connect to the API"
    assert client.session_id is not None, "Session ID should be set after connection"
    await client.close() 