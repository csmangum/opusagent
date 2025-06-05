"""
WebSocket client utilities for connecting to telephony platforms.

This module provides client-side utilities for connecting to telephony platforms.
It handles message formatting, validation, and connection management using
Pydantic models for type safety.
"""

import json
import logging
import uuid
from typing import Any, Callable, Dict, Optional

import websockets

from opusagent.config.constants import LOGGER_NAME
from opusagent.models.audiocodes_api import (
    ActivitiesMessage,
    ActivityEvent,
    SessionInitiateMessage,
    UserStreamStartMessage,
    UserStreamStopMessage,
)

logger = logging.getLogger(LOGGER_NAME)


class TelephonyClient:
    """
    Client for interacting with telephony platforms via WebSocket.

    This class provides methods to connect to telephony services, send formatted messages,
    and receive responses. It uses Pydantic models to ensure message validity.
    """

    def __init__(self, url: str):
        """
        Initialize the telephony WebSocket client.

        Args:
            url: The WebSocket URL of the telephony service
        """
        self.url = url
        self.websocket = None
        self.conversation_id = None
        self.media_format = "raw/lpcm16"
        self.message_handlers = {}

    async def connect(self) -> bool:
        """
        Establish a connection to the telephony WebSocket server.

        Returns:
            True if connection was successful, False otherwise
        """
        try:
            self.websocket = await websockets.connect(self.url)
            logger.info(f"Connected to telephony WebSocket at {self.url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to telephony: {e}")
            return False

    async def initiate_session(
        self, bot_name: str, caller: str = "unknown"
    ) -> Optional[str]:
        """
        Initiate a new session with telephony.

        Args:
            bot_name: The name of the bot
            caller: The caller's identifier/phone number

        Returns:
            The conversation ID if session was accepted, None otherwise
        """
        if not self.websocket:
            logger.error("Cannot initiate session: Not connected")
            return None

        # Generate a unique conversation ID
        self.conversation_id = str(uuid.uuid4())

        # Create a session.initiate message
        message = SessionInitiateMessage(
            type="session.initiate",
            conversationId=self.conversation_id,
            botName=bot_name,
            caller=caller,
            expectAudioMessages=True,
            supportedMediaFormats=[self.media_format],
        )

        # Send the message
        await self.websocket.send(message.json())
        logger.info(f"Initiated session with conversation ID: {self.conversation_id}")

        # Wait for response
        response_data = await self.websocket.recv()
        response = json.loads(response_data)

        if response.get("type") == "session.accepted":
            logger.info("Session accepted")
            return self.conversation_id
        else:
            logger.error(f"Session rejected: {response}")
            self.conversation_id = None
            return None

    async def start_user_stream(self) -> bool:
        """
        Start a user audio stream.

        Returns:
            True if the stream was successfully started, False otherwise
        """
        if not self.websocket or not self.conversation_id:
            logger.error("Cannot start stream: No active session")
            return False

        # Create a userStream.start message
        message = UserStreamStartMessage(
            type="userStream.start", conversationId=self.conversation_id
        )

        # Send the message
        await self.websocket.send(message.json())
        logger.info("Started user stream")

        # Wait for response
        response_data = await self.websocket.recv()
        response = json.loads(response_data)

        if response.get("type") == "userStream.started":
            logger.info("User stream started")
            return True
        else:
            logger.error(f"Failed to start user stream: {response}")
            return False

    async def send_audio_chunk(self, audio_data: bytes) -> None:
        """
        Send an audio chunk to telephony.

        Args:
            audio_data: The raw audio data to send (will be base64 encoded)
        """
        if not self.websocket or not self.conversation_id:
            logger.error("Cannot send audio: No active session")
            return

        import base64

        # Encode the audio data
        encoded_data = base64.b64encode(audio_data).decode("utf-8")

        # Create a userStream.chunk message
        message = {
            "type": "userStream.chunk",
            "conversationId": self.conversation_id,
            "audioChunk": encoded_data,
        }

        # Send the message
        await self.websocket.send(json.dumps(message))
        logger.debug(f"Sent audio chunk of length: {len(encoded_data)}")

    async def stop_user_stream(self) -> bool:
        """
        Stop the user audio stream.

        Returns:
            True if the stream was successfully stopped, False otherwise
        """
        if not self.websocket or not self.conversation_id:
            logger.error("Cannot stop stream: No active session")
            return False

        # Create a userStream.stop message
        message = UserStreamStopMessage(
            type="userStream.stop", conversationId=self.conversation_id
        )

        # Send the message
        await self.websocket.send(message.json())
        logger.info("Stopped user stream")

        # Wait for response
        response_data = await self.websocket.recv()
        response = json.loads(response_data)

        if response.get("type") == "userStream.stopped":
            logger.info("User stream stopped")
            return True
        else:
            logger.error(f"Failed to stop user stream: {response}")
            return False

    async def send_hangup(self) -> None:
        """
        Send a hangup event to end the call.
        """
        if not self.websocket or not self.conversation_id:
            logger.error("Cannot send hangup: No active session")
            return

        # Create the hangup activity message
        hangup_activity = ActivityEvent(type="event", name="hangup")
        message = ActivitiesMessage(
            type="activities",
            activities=[hangup_activity],
            conversationId=self.conversation_id,
        )

        # Send the message
        await self.websocket.send(message.json())
        logger.info("Sent hangup activity")

    async def close(self) -> None:
        """
        Close the WebSocket connection.
        """
        if self.websocket:
            await self.websocket.close()
            logger.info("Closed WebSocket connection")
            self.websocket = None
            self.conversation_id = None

    async def listen(self, message_handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        Listen for incoming messages from telephony.

        Args:
            message_handler: Callback function to handle incoming messages
        """
        if not self.websocket:
            logger.error("Cannot listen: Not connected")
            return

        try:
            while True:
                message_data = await self.websocket.recv()
                message = json.loads(message_data)

                # Process the message with the handler
                await message_handler(message)

                # Check for session.end message
                if message.get("type") == "session.end":
                    logger.info("Received session.end message, closing connection")
                    await self.close()
                    break

        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed by server")
            self.websocket = None
            self.conversation_id = None
        except Exception as e:
            logger.error(f"Error in WebSocket listener: {e}")
            await self.close()


# Example usage of the client:
#
# async def main():
#     client = TelephonyClient("wss://telephony-server.example.com/ws")
#
#     if await client.connect():
#         conversation_id = await client.initiate_session("MyBot", "+1234567890")
#
#         if conversation_id:
#             if await client.start_user_stream():
#                 # Send audio data
#                 audio_data = b"some audio bytes"
#                 await client.send_audio_chunk(audio_data)
#
#                 # Stop streaming when done
#                 await client.stop_user_stream()
#
#             # End the call
#             await client.send_hangup()
#
#     await client.close()
#
# if __name__ == "__main__":
#     asyncio.run(main())
