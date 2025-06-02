import asyncio
import base64
import json
import time
import websockets
import uuid
from validate.validate import AudioRecorder, load_audio_chunks

async def validate_replacement_card_flow(
    WS_URL,
    AUDIO_FILE_PATH,
    load_audio_chunks,
    AudioRecorder,
    TIMEOUT_SECONDS=15
):
    """Validate the replacement card flow: session.initiate → session.accepted → playStream.start → playStream.stop."""
    print(f"\n[1/3] Testing replacement card flow...")
    print(f"Connecting to {WS_URL}...")


