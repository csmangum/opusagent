"""
Bot module for integrating OpenAI Realtime API with telephony platforms.

This module provides components for real-time speech-to-speech conversations
by connecting telephony WebSocket protocols (like AudioCodes, Twilio, etc.) with OpenAI's Realtime API.

Key components:
- RealtimeClient: Client for connecting to OpenAI's Realtime API over WebSockets
  to stream audio in both directions with features like auto-reconnection and heartbeats.
- TelephonyRealtimeBridge: Bidirectional bridge that handles protocol conversion between
  telephony platforms and OpenAI's Realtime API, including audio format
  conversion and stream management.

This module is the core of the voice agent system, enabling real-time voice conversations
with OpenAI's models through telephony infrastructure.

Usage examples:
```python
# Using the singleton bridge instance (recommended for most cases)
from app.bot import bridge
import asyncio

async def handle_new_conversation(conversation_id, websocket):
    # Create a new client for this conversation
    await bridge.create_client(conversation_id, websocket)
    
    # Send audio to OpenAI
    await bridge.send_audio_chunk(conversation_id, base64_audio_data)
    
    # Clean up when conversation ends
    await bridge.close_client(conversation_id)

# Direct usage of RealtimeClient (for custom implementations)
from app.bot import RealtimeClient
import os

async def custom_client_usage():
    # Create and connect client
    api_key = os.getenv("OPENAI_API_KEY")
    model = "gpt-4o-realtime-preview-2024-12-17"
    client = RealtimeClient(api_key, model)
    await client.connect()
    
    # Send and receive audio
    await client.send_audio_chunk(audio_bytes)
    response_chunk = await client.receive_audio_chunk()
    
    # Close when done
    await client.close()
```
"""

from fastagent.bot.realtime_client import RealtimeClient
from fastagent.bot.telephony_realtime_bridge import bridge, TelephonyRealtimeBridge

__all__ = ["RealtimeClient", "bridge", "TelephonyRealtimeBridge"]
