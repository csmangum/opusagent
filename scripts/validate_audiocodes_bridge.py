import asyncio
import base64
import json
import logging
import os
import sys
import uuid
from pathlib import Path

import websockets
import soundfile as sf
import numpy as np

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("audiocodes_bridge_validator")

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def generate_silence_pcm16(duration_sec: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate silent PCM16 audio of the given duration."""
    num_samples = int(duration_sec * sample_rate)
    return b"\x00\x00" * num_samples  # 16-bit little-endian silence


def pcm16_to_base64(pcm_bytes: bytes) -> str:
    """Encode PCM bytes to base64 string."""
    return base64.b64encode(pcm_bytes).decode()


async def send_and_log(ws, payload: dict):
    """Send JSON payload and log it."""
    await ws.send(json.dumps(payload))
    logger.info(f"--> Sent: {payload['type']}")


async def expect(ws, expected_type: str, timeout: float = 5.0) -> dict:
    """Wait for a message of expected_type within timeout."""
    try:
        msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
        data = json.loads(msg)
        if data.get("type") != expected_type:
            raise AssertionError(f"Expected {expected_type}, got {data.get('type')}")
        logger.info(f"<-- Received: {data['type']}")
        return data
    except asyncio.TimeoutError:
        raise AssertionError(f"Timeout waiting for {expected_type}")


def read_wav_as_pcm16(path: Path, target_rate: int = 16000) -> bytes:
    """Read a WAV file and return raw PCM16 mono at target_rate (little-endian)."""
    # Read the audio file
    data, source_rate = sf.read(str(path))
    
    # Convert to mono if stereo
    if len(data.shape) > 1:
        data = np.mean(data, axis=1)
    
    # Resample if needed
    if source_rate != target_rate:
        from scipy import signal
        samples = len(data)
        new_samples = int(samples * target_rate / source_rate)
        data = signal.resample(data, new_samples)
    
    # Convert to 16-bit PCM
    data = np.clip(data, -1.0, 1.0)  # Ensure values are in [-1, 1]
    data = (data * 32767).astype(np.int16)  # Convert to 16-bit
    
    # Convert to bytes (little-endian)
    return data.tobytes()


# ---------------------------------------------------------------------------
# Validation coroutine
# ---------------------------------------------------------------------------

async def validate_once(server_ws_url: str, wav_paths: list[Path]):
    conversation_id = str(uuid.uuid4())
    async with websockets.connect(server_ws_url) as ws:
        # 1. SESSION INITIATE
        await send_and_log(
            ws,
            {
                "type": "session.initiate",
                "conversationId": conversation_id,
                "botName": "validator",
                "caller": "+15551234567",
                "expectAudioMessages": True,
                "supportedMediaFormats": ["raw/lpcm16"],
            },
        )
        await expect(ws, "session.accepted")

        # 2. USER STREAM START
        await send_and_log(
            ws,
            {
                "type": "userStream.start",
                "conversationId": conversation_id,
            },
        )
        await expect(ws, "userStream.started")

        # 3. Send WAV(s)
        if not wav_paths:
            wav_paths = []
        if not wav_paths:
            # Fallback to 1s silence if no wav provided
            wav_paths.append(None)

        for path in wav_paths:
            if path is None:
                pcm_bytes = generate_silence_pcm16(1.0)
            else:
                logger.info(f"Sending audio from {path}")
                pcm_bytes = read_wav_as_pcm16(path)

            chunk_b64 = pcm16_to_base64(pcm_bytes)
            await send_and_log(
                ws,
                {
                    "type": "userStream.chunk",
                    "conversationId": conversation_id,
                    "audioChunk": chunk_b64,
                },
            )

        # 4. USER STREAM STOP
        await send_and_log(
            ws,
            {
                "type": "userStream.stop",
                "conversationId": conversation_id,
            },
        )
        await expect(ws, "userStream.stopped")

        # 5. Expect a playStream.start indicating bot response (allow longer timeout)
        play_start = await expect(ws, "playStream.start", timeout=15.0)
        stream_id = play_start.get("streamId")
        logger.info(f"Bot started play stream {stream_id}")

        # 6. Read chunks until playStream.stop received
        while True:
            msg = json.loads(await ws.recv())
            msg_type = msg.get("type")
            if msg_type == "playStream.chunk":
                logger.debug("<-- audio chunk %d bytes", len(msg.get("audioChunk", "")))
            elif msg_type == "playStream.stop":
                logger.info("Bot finished play stream")
                break
            else:
                logger.info("<-- Other message: %s", msg_type)

        logger.info("Validation run completed successfully.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate AudioCodes bridge over WebSocket")
    parser.add_argument(
        "--url",
        default="ws://localhost:8000/ws/telephony",
        help="WebSocket URL of the /ws/telephony endpoint",
    )
    parser.add_argument(
        "--wav",
        nargs="*",
        default=["static/need_to_replace_card.wav"],
        help="Path(s) to WAV files to stream instead of silence. Must be 16-bit PCM mono or will be converted.",
    )
    args = parser.parse_args()

    try:
        wav_files = [Path(p) for p in args.wav] if args.wav else []
        asyncio.run(validate_once(args.url, wav_files))
    except AssertionError as e:
        logger.error("Validation failed: %s", e)
        sys.exit(1)
    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        sys.exit(1) 