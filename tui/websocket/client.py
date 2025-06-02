import asyncio
import json
import websockets

class WebSocketClient:
    def __init__(self):
        self.websocket = None
        self.connected = False

    async def connect(self, url: str) -> bool:
        try:
            self.websocket = await websockets.connect(url)
            self.connected = True
            return True
        except Exception as e:
            self.connected = False
            return False

    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
            self.connected = False

    async def send_message(self, message: dict):
        if self.websocket:
            await self.websocket.send(json.dumps(message))

    async def receive_messages(self):
        if self.websocket:
            async for msg in self.websocket:
                yield json.loads(msg)

    def is_connected(self) -> bool:
        return self.connected 