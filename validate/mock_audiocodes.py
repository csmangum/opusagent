import asyncio
import json
from typing import List, Dict, Any, Callable, Optional
import websockets
from websockets.server import WebSocketServerProtocol

class MockAudioCodes:
    """
    MockAudioCodes simulates the AudioCodes VAIC WebSocket server for validation/testing.

    Usage:
        async with MockAudioCodes(port=9000, scripted_events=[...]) as mock:
            # Run your client/bot code that connects to ws://localhost:9000
            # Use mock.received_messages for assertions
    """
    def __init__(self, host: str = "localhost", port: int = 9000, scripted_events: Optional[List[Dict[str, Any]]] = None):
        self.host = host
        self.port = port
        self.scripted_events = scripted_events or []
        self._server = None
        self._ws: Optional[WebSocketServerProtocol] = None
        self.received_messages: List[Dict[str, Any]] = []
        self._send_task = None
        self._connection_event = asyncio.Event()

    async def __aenter__(self):
        self._server = await websockets.serve(self._handler, self.host, self.port)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._server.close()
        await self._server.wait_closed()
        if self._send_task:
            self._send_task.cancel()

    async def _handler(self, ws: WebSocketServerProtocol):
        self._ws = ws
        self._connection_event.set()
        # Send scripted events in order
        if self.scripted_events:
            self._send_task = asyncio.create_task(self._send_scripted_events())
        try:
            async for message in ws:
                try:
                    data = json.loads(message)
                except Exception:
                    data = message
                self.received_messages.append(data)
        except websockets.ConnectionClosed:
            pass

    async def _send_scripted_events(self):
        for event in self.scripted_events:
            await asyncio.sleep(event.get("delay", 0))
            await self.send(event["message"])

    async def send(self, message: Any):
        if not self._ws:
            await self._connection_event.wait()
        if isinstance(message, dict):
            msg = json.dumps(message)
        else:
            msg = message
        await self._ws.send(msg)

    async def wait_for_message(self, predicate: Callable[[Any], bool], timeout: float = 5.0):
        """Wait for a received message matching the predicate."""
        end_time = asyncio.get_running_loop().time() + timeout
        idx = 0
        while True:
            while idx < len(self.received_messages):
                msg = self.received_messages[idx]
                idx += 1
                if predicate(msg):
                    return msg
            if asyncio.get_event_loop().time() > end_time:
                raise TimeoutError("Timeout waiting for message")
            await asyncio.sleep(0.05)

# Example usage in a test/validation:
#
# async def test_bot():
#     scripted = [
#         {"message": {"type": "session.initiate", ...}, "delay": 0},
#         {"message": {"type": "session.accepted", ...}, "delay": 1},
#     ]
#     async with MockAudioCodes(port=9000, scripted_events=scripted) as mock:
#         # Run your bot/client code that connects to ws://localhost:9000
#         ...
#         # Assert on mock.received_messages 