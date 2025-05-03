import argparse
import asyncio
import json
import os
from typing import Optional

import uvicorn
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketDisconnect

load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PORT = int(os.getenv("PORT", 6060))
SYSTEM_MESSAGE = (
    "You are a helpful and bubbly AI assistant who loves to chat about "
    "anything the user is interested in and is prepared to offer them facts. "
    "You have a penchant for dad jokes, owl jokes, and rickrolling – subtly. "
    "Always stay positive, but work in a joke when appropriate."
)
VOICE = "alloy"
LOG_EVENT_TYPES = [
    "error",
    "response.content.done",
    "rate_limits.updated",
    "response.done",
    "input_audio_buffer.committed",
    "input_audio_buffer.speech_stopped",
    "input_audio_buffer.speech_started",
    "session.created",
]

app = FastAPI()


@app.get("/", response_class=JSONResponse)
async def index_page():
    return {"message": "Telephony Bridge is running!"}


class TelephonyRealtimeBridge:
    def __init__(
        self, websocket: WebSocket, openai_ws: websockets.WebSocketClientProtocol
    ):
        self.websocket = websocket
        self.openai_ws = openai_ws
        self.stream_sid: Optional[str] = None
        self._closed = False

    async def close(self):
        """Safely close both WebSocket connections."""
        if not self._closed:
            self._closed = True
            try:
                if self.openai_ws.close_code is None:
                    await self.openai_ws.close()
            except Exception as e:
                print(f"Error closing OpenAI connection: {e}")
            try:
                await self.websocket.close()
            except Exception as e:
                print(f"Error closing telephony connection: {e}")

    async def receive_from_telephony(self):
        """Receive audio data from telephony and send it to the OpenAI Realtime API."""
        try:
            async for message in self.websocket.iter_text():
                if self._closed:
                    break

                data = json.loads(message)
                if (
                    data["event"] == "media"
                    and not self._closed
                    and self.openai_ws.close_code is None
                ):
                    audio_append = {
                        "type": "input_audio_buffer.append",
                        "audio": data["media"]["payload"],
                    }
                    await self.openai_ws.send(json.dumps(audio_append))
                elif data["event"] == "start":
                    self.stream_sid = data["start"]["streamSid"]
                    print(f"Incoming stream has started {self.stream_sid}")
                elif data["event"] == "stop":
                    print(f"Stream {self.stream_sid} stopped")
                    await self.close()
                    break
        except WebSocketDisconnect:
            print("Client disconnected.")
            await self.close()
        except Exception as e:
            print(f"Error in receive_from_telephony: {e}")
            await self.close()

    async def send_to_telephony(self):
        """Receive events from the OpenAI Realtime API, send audio back to the telephony."""
        try:
            async for openai_message in self.openai_ws:
                if self._closed:
                    break

                response = json.loads(openai_message)
                if response["type"] in LOG_EVENT_TYPES:
                    print(f"Received event: {response['type']}", response)
                if response["type"] == "session.updated":
                    print("Session updated successfully:", response)
                if response["type"] == "response.audio.delta" and response.get("delta"):
                    try:
                        if not self._closed and self.stream_sid:
                            audio_delta = {
                                "event": "media",
                                "streamSid": self.stream_sid,
                                "media": {"payload": response["delta"]},
                            }
                            await self.websocket.send_json(audio_delta)
                            print("Sent audio delta to client")
                    except Exception as e:
                        print(f"Error processing audio data: {e}")
                        if not self._closed:
                            await self.close()
        except Exception as e:
            print(f"Error in send_to_telephony: {e}")
            await self.close()


@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between telephony provider and OpenAI."""
    print("Client connected")
    await websocket.accept()

    try:
        #! Make RealtimeClient work like this
        async with websockets.connect(
            "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01",
            subprotocols=["realtime"],
            additional_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1",
            },
        ) as openai_ws:
            bridge = TelephonyRealtimeBridge(websocket, openai_ws)
            await initialize_session(openai_ws)

            # Run both tasks and handle cleanup
            try:
                await asyncio.gather(
                    bridge.receive_from_telephony(), bridge.send_to_telephony()
                )
            except Exception as e:
                print(f"Error in main connection loop: {e}")
            finally:
                await bridge.close()
    except Exception as e:
        print(f"Error establishing OpenAI connection: {e}")
        await websocket.close()


async def send_initial_conversation_item(openai_ws):
    """Send initial conversation so AI talks first."""
    initial_conversation_item = {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "Hello! Please introduce yourself and tell me a joke.",
                }
            ],
        },
    }
    print("Sending initial conversation item:", json.dumps(initial_conversation_item))
    await openai_ws.send(json.dumps(initial_conversation_item))
    await openai_ws.send(json.dumps({"type": "response.create"}))


async def initialize_session(openai_ws):
    """Control initial session with OpenAI."""
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": VOICE,
            "instructions": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
        },
    }
    print("Sending session update:", json.dumps(session_update))
    await openai_ws.send(json.dumps(session_update))

    # Have the AI speak first
    await send_initial_conversation_item(openai_ws)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telephony Media Stream Server")
    parser.add_argument(
        "--port", type=int, default=PORT, help="Port to run the server on"
    )
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)
