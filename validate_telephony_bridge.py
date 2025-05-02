from fastagent.bot.telephony_realtime_bridge import bridge
import asyncio
import logging
import base64
from fastagent.config.constants import LOGGER_NAME

# Configure logging
logger = logging.getLogger(LOGGER_NAME)
logging.basicConfig(level=logging.INFO)

class MockWebSocket:
    """A simple mock WebSocket for testing purposes."""
    
    async def send_text(self, text):
        logger.info(f"Mock WebSocket received: {text}")

async def test_bridge():
    mock_websocket = MockWebSocket()
    
    # Create client with mock websocket
    await bridge.create_client("test-conversation-1", mock_websocket)
    
    # Send audio chunk - encode as base64 to avoid padding error
    dummy_audio = b"This is a test audio chunk"
    base64_audio = base64.b64encode(dummy_audio).decode('utf-8')
    await bridge.send_audio_chunk("test-conversation-1", base64_audio)
    
    # Clean up
    await bridge.close_client("test-conversation-1")

def main():
    asyncio.run(test_bridge())

if __name__ == "__main__":
    main()
