import asyncio
import base64
import json
import logging
import os
import sys
import uuid
from pathlib import Path

import numpy as np
import soundfile as sf
import websockets

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("twilio_bridge_validator")

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def generate_silence_mulaw(duration_sec: float = 1.0, sample_rate: int = 8000) -> bytes:
    """Generate silent μ-law audio of the given duration."""
    num_samples = int(duration_sec * sample_rate)
    return b"\xff" * num_samples  # μ-law silence (0x7f in linear PCM)


def mulaw_to_base64(mulaw_bytes: bytes) -> str:
    """Encode μ-law bytes to base64 string."""
    return base64.b64encode(mulaw_bytes).decode()


def read_wav_as_mulaw(path: Path, target_rate: int = 8000) -> bytes:
    """Read a WAV file and return μ-law mono at target_rate."""
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

    # Convert to μ-law
    try:
        import audioop

        pcm_bytes = data.tobytes()
        return audioop.lin2ulaw(pcm_bytes, 2)
    except ImportError:
        # Fallback if audioop not available
        return data.tobytes()[::2]  # Simple downsampling


async def send_and_log(ws, payload: dict):
    """Send JSON payload and log it."""
    await ws.send(json.dumps(payload))
    logger.info(f"--> Sent: {payload['event']}")


async def expect(ws, expected_event: str, timeout: float = 5.0) -> dict:
    """Wait for a message of expected_event within timeout."""
    try:
        msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
        data = json.loads(msg)
        if data.get("event") != expected_event:
            raise AssertionError(f"Expected {expected_event}, got {data.get('event')}")
        logger.info(f"<-- Received: {data['event']}")
        return data
    except asyncio.TimeoutError:
        raise AssertionError(f"Timeout waiting for {expected_event}")


# ---------------------------------------------------------------------------
# Validation coroutine
# ---------------------------------------------------------------------------


async def validate_once(server_ws_url: str, wav_paths: list[Path]):
    stream_sid = str(uuid.uuid4())
    call_sid = str(uuid.uuid4())
    account_sid = "AC" + str(uuid.uuid4())

    async with websockets.connect(server_ws_url) as ws:
        # 1. CONNECTED
        await send_and_log(
            ws,
            {
                "event": "connected",
                "protocol": "WebSocket",
                "version": "1.0",
                "streamSid": stream_sid,
            },
        )

        # 2. START
        await send_and_log(
            ws,
            {
                "event": "start",
                "streamSid": stream_sid,
                "start": {
                    "accountSid": account_sid,
                    "callSid": call_sid,
                    "mediaFormat": {
                        "encoding": "audio/x-mulaw",
                        "sampleRate": 8000,
                        "channels": 1,
                    },
                },
            },
        )

        # 3. Send WAV(s)
        if not wav_paths:
            wav_paths = []
        if not wav_paths:
            # Fallback to 1s silence if no wav provided
            wav_paths.append(None)

        for path in wav_paths:
            if path is None:
                mulaw_bytes = generate_silence_mulaw(1.0)
            else:
                logger.info(f"Sending audio from {path}")
                mulaw_bytes = read_wav_as_mulaw(path)

            chunk_b64 = mulaw_to_base64(mulaw_bytes)
            await send_and_log(
                ws,
                {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {
                        "payload": chunk_b64,
                    },
                },
            )

        # 4. STOP
        await send_and_log(
            ws,
            {
                "event": "stop",
                "streamSid": stream_sid,
                "stop": {
                    "accountSid": account_sid,
                    "callSid": call_sid,
                },
            },
        )

        # 5. Expect media messages back
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=15.0)
                data = json.loads(msg)
                if data.get("event") == "media":
                    logger.debug(
                        "<-- audio chunk %d bytes",
                        len(data.get("media", {}).get("payload", "")),
                    )
                elif data.get("event") == "mark":
                    logger.info(f"<-- mark: {data.get('mark', {}).get('name')}")
                else:
                    logger.info(f"<-- Other message: {data.get('event')}")
            except asyncio.TimeoutError:
                break

        logger.info("Validation run completed successfully.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate Twilio bridge over WebSocket"
    )
    parser.add_argument(
        "--url",
        default="ws://localhost:8000/ws/telephony",
        help="WebSocket URL of the /ws/telephony endpoint",
    )
    parser.add_argument(
        "--wav",
        nargs="*",
        default=["static/need_to_replace_card.wav"],
        help="Path(s) to WAV files to stream instead of silence. Must be 8kHz mono or will be converted.",
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
