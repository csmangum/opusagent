"""
Main AudioCodes mock client.

This module provides the main MockAudioCodesClient class that integrates all
the modular components (session management, message handling, audio management,
and conversation management) into a cohesive client for testing AudioCodes
bridge server interactions.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import websockets

from .audio_manager import AudioManager
from .conversation_manager import ConversationManager
from .message_handler import MessageHandler
from .models import ConversationResult, SessionConfig
from .session_manager import SessionManager


class MockAudioCodesClient:
    """
    MockAudioCodes client that connects to the bridge server.

    This class integrates all the modular components to provide a comprehensive
    mock implementation of the AudioCodes VAIC client for testing and development.

    Attributes:
        logger (logging.Logger): Logger instance for debugging
        config (SessionConfig): Session configuration
        session_manager (SessionManager): Session state manager
        message_handler (MessageHandler): WebSocket message handler
        audio_manager (AudioManager): Audio file manager
        conversation_manager (ConversationManager): Conversation manager
        _ws: WebSocket connection
        _message_task: Background message handling task
    """

    def __init__(
        self,
        bridge_url: str,
        bot_name: str = "TestBot",
        caller: str = "+15551234567",
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the MockAudioCodesClient.

        Args:
            bridge_url (str): WebSocket URL for bridge server
            bot_name (str): Name of the bot
            caller (str): Caller phone number
            logger (Optional[logging.Logger]): Logger instance for debugging
        """
        self.logger = logger or logging.getLogger(__name__)

        # Create configuration
        self.config = SessionConfig(
            bridge_url=bridge_url, bot_name=bot_name, caller=caller
        )

        # Initialize components
        self.session_manager = SessionManager(self.config, self.logger)
        self.audio_manager = AudioManager(self.logger)
        self.message_handler = MessageHandler(self.session_manager, self.logger)
        self.conversation_manager = ConversationManager(
            self.session_manager, self.audio_manager, self.logger
        )

        # WebSocket connection
        self._ws = None
        self._message_task = None

    async def __aenter__(self):
        """Connect to the bridge server."""
        self.logger.info(
            f"[CLIENT] Connecting to bridge at {self.config.bridge_url}..."
        )
        self._ws = await websockets.connect(self.config.bridge_url)
        self.logger.info("[CLIENT] Connected to bridge server")

        # Start message handler
        self._message_task = asyncio.create_task(self._message_handler())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Disconnect from bridge server."""
        if self._message_task:
            self._message_task.cancel()
        if self._ws:
            await self._ws.close()
        self.logger.info("[CLIENT] Disconnected from bridge server")

    async def _message_handler(self):
        """Handle incoming messages from the bridge."""
        try:
            if self._ws is None:
                self.logger.error("[CLIENT] WebSocket connection is None")
                return

            async for message in self._ws:
                try:
                    # Convert bytes/bytearray to string if needed
                    if isinstance(message, (bytes, bytearray)):
                        message_str = message.decode("utf-8")
                    else:
                        message_str = str(message)
                    event = self.message_handler.process_message(message_str)
                    if event and event.type.value == "session.accepted":
                        # Start conversation when session is accepted
                        if self.session_manager.conversation_state:
                            self.conversation_manager.start_conversation(
                                self.session_manager.conversation_state.conversation_id
                            )
                except Exception as e:
                    self.logger.error(f"[CLIENT] Error processing message: {e}")
        except websockets.ConnectionClosed:
            self.logger.info("[CLIENT] Bridge connection closed")
        except Exception as e:
            self.logger.error(f"[CLIENT] Message handler error: {e}")

    async def initiate_session(self, conversation_id: Optional[str] = None) -> bool:
        """
        Send session.initiate to the bridge.

        Args:
            conversation_id (Optional[str]): Conversation ID to use

        Returns:
            bool: True if session was accepted, False otherwise
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return False

        # Create session
        conv_id = self.session_manager.create_session(conversation_id)

        # Send initiation message
        message = self.session_manager.initiate_session()
        await self._ws.send(json.dumps(message))

        self.logger.info(f"[CLIENT] Sent session.initiate for conversation: {conv_id}")

        # Wait for session.accepted
        for _ in range(100):  # 10 seconds timeout
            if self.session_manager.session_state.accepted:
                return True
            elif self.session_manager.session_state.error:
                self.logger.error(
                    f"[CLIENT] Session rejected: {self.session_manager.session_state.error_reason}"
                )
                return False
            await asyncio.sleep(0.1)

        self.logger.error("[CLIENT] Session not accepted within timeout")
        return False

    async def resume_session(self, conversation_id: str) -> bool:
        """
        Send session.resume to the bridge.

        Args:
            conversation_id (str): Conversation ID to resume

        Returns:
            bool: True if session was resumed, False otherwise
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return False

        # Send resume message
        message = self.session_manager.resume_session(conversation_id)
        await self._ws.send(json.dumps(message))

        self.logger.info(
            f"[CLIENT] Sent session.resume for conversation: {conversation_id}"
        )

        # Wait for session.resumed
        for _ in range(100):  # 10 seconds timeout
            if self.session_manager.session_state.resumed:
                return True
            elif self.session_manager.session_state.error:
                self.logger.error(
                    f"[CLIENT] Session resume failed: {self.session_manager.session_state.error_reason}"
                )
                return False
            await asyncio.sleep(0.1)

        self.logger.error("[CLIENT] Session not resumed within timeout")
        return False

    async def validate_connection(self) -> bool:
        """
        Send connection.validate and wait for response.

        Returns:
            bool: True if connection was validated, False otherwise
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return False

        # Send validation message
        message = self.session_manager.validate_connection()
        await self._ws.send(json.dumps(message))

        self.logger.info(
            f"[CLIENT] Sent connection.validate for conversation: {self.session_manager.get_conversation_id()}"
        )

        # Wait for connection.validated
        for _ in range(50):  # 5 seconds timeout
            if self.session_manager.session_state.connection_validated:
                return True
            await asyncio.sleep(0.1)

        self.logger.error("[CLIENT] Connection validation timeout")
        return False

    async def send_dtmf_event(self, digit: str) -> bool:
        """
        Send DTMF event to bridge.

        Args:
            digit (str): DTMF digit to send

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return False

        try:
            message = self.session_manager.send_dtmf_event(digit)
            await self._ws.send(json.dumps(message))
            return True
        except Exception as e:
            self.logger.error(f"[CLIENT] Error sending DTMF event: {e}")
            return False

    async def send_hangup_event(self) -> bool:
        """
        Send hangup event to bridge.

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return False

        try:
            message = self.session_manager.send_hangup_event()
            await self._ws.send(json.dumps(message))
            return True
        except Exception as e:
            self.logger.error(f"[CLIENT] Error sending hangup event: {e}")
            return False

    async def send_custom_activity(self, activity: Dict[str, Any]) -> bool:
        """
        Send custom activity to bridge.

        Args:
            activity (Dict[str, Any]): Custom activity data

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return False

        try:
            message = self.session_manager.send_custom_activity(activity)
            await self._ws.send(json.dumps(message))
            return True
        except Exception as e:
            self.logger.error(f"[CLIENT] Error sending custom activity: {e}")
            return False

    async def send_user_audio(
        self, audio_file_path: str, chunk_delay: float = 0.02
    ) -> bool:
        """
        Send user audio to the bridge.

        Args:
            audio_file_path (str): Path to audio file
            chunk_delay (float): Delay between audio chunks

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return False

        try:
            # Load audio chunks
            audio_chunks = self.audio_manager.load_audio_chunks(audio_file_path)
            if not audio_chunks:
                return False

            self.logger.info(
                f"[CLIENT] Sending user audio: {audio_file_path} ({len(audio_chunks)} chunks)"
            )

            # Start user stream
            user_stream_start = {
                "type": "userStream.start",
                "conversationId": self.session_manager.get_conversation_id(),
            }
            await self._ws.send(json.dumps(user_stream_start))

            # Wait for userStream.started
            for _ in range(20):
                if self.session_manager.stream_state.user_stream.value == "active":
                    break
                await asyncio.sleep(0.1)
            else:
                self.logger.error("[CLIENT] User stream not started")
                return False

            # Send audio chunks
            for i, chunk in enumerate(audio_chunks):
                audio_chunk_msg = {
                    "type": "userStream.chunk",
                    "conversationId": self.session_manager.get_conversation_id(),
                    "audioChunk": chunk,
                }
                await self._ws.send(json.dumps(audio_chunk_msg))

                if i % 10 == 0 or i == len(audio_chunks) - 1:
                    self.logger.debug(f"[CLIENT] Sent chunk {i+1}/{len(audio_chunks)}")
                await asyncio.sleep(chunk_delay)

            # Stop user stream
            user_stream_stop = {
                "type": "userStream.stop",
                "conversationId": self.session_manager.get_conversation_id(),
            }
            await self._ws.send(json.dumps(user_stream_stop))

            self.logger.info("[CLIENT] User audio sent successfully")
            return True

        except Exception as e:
            self.logger.error(f"[CLIENT] Error sending user audio: {e}")
            return False

    async def wait_for_llm_greeting(self, timeout: float = 20.0) -> List[str]:
        """
        Wait for and collect LLM greeting audio.

        Args:
            timeout (float): Timeout in seconds

        Returns:
            List[str]: List of greeting audio chunks
        """
        return await self.conversation_manager.wait_for_greeting(timeout)

    async def wait_for_llm_response(self, timeout: float = 45.0) -> List[str]:
        """
        Wait for and collect LLM response audio.

        Args:
            timeout (float): Timeout in seconds

        Returns:
            List[str]: List of response audio chunks
        """
        return await self.conversation_manager.wait_for_response(timeout)

    async def multi_turn_conversation(
        self,
        audio_files: List[str],
        wait_for_greeting: bool = True,
        turn_delay: float = 2.0,
        chunk_delay: float = 0.02,
    ) -> ConversationResult:
        """
        Conduct a multi-turn conversation using a list of audio files.

        Args:
            audio_files: List of paths to audio files for user turns
            wait_for_greeting: Whether to wait for initial AI greeting
            turn_delay: Delay between conversation turns (seconds)
            chunk_delay: Delay between audio chunks (seconds)

        Returns:
            ConversationResult: Conversation results and statistics
        """
        return await self.conversation_manager.multi_turn_conversation(
            audio_files, wait_for_greeting, turn_delay, chunk_delay
        )

    async def end_session(self, reason: str = "Test completed") -> None:
        """
        End the session gracefully.

        Args:
            reason (str): Reason for ending the session
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return

        try:
            message = self.session_manager.end_session(reason)
            await self._ws.send(json.dumps(message))
            self.logger.info(f"[CLIENT] Sent session.end: {reason}")
        except Exception as e:
            self.logger.error(f"[CLIENT] Error ending session: {e}")

    def get_session_status(self) -> Dict[str, Any]:
        """
        Get current session status information.

        Returns:
            Dict[str, Any]: Session status information
        """
        return self.session_manager.get_session_status()

    def reset_session_state(self) -> None:
        """Reset all session-related state variables."""
        self.session_manager.reset_session_state()
        self.conversation_manager.reset_conversation_state()
        self.message_handler.clear_message_history()

    def save_collected_audio(self, output_dir: str = "validation_output") -> None:
        """
        Save collected audio for analysis.

        Args:
            output_dir (str): Output directory
        """
        self.conversation_manager.save_collected_audio(output_dir)

    async def simple_conversation_test(
        self, audio_files: List[str], session_name: str = "MultiTurnTest"
    ) -> bool:
        """
        Simple wrapper for testing multi-turn conversations.

        Args:
            audio_files: List of audio files for conversation turns
            session_name: Name for the test session

        Returns:
            bool: True if the conversation was successful, False otherwise
        """
        try:
            # Initiate session
            success = await self.initiate_session()
            if not success:
                self.logger.error("[CLIENT] Failed to initiate session")
                return False

            # Run multi-turn conversation
            result = await self.multi_turn_conversation(audio_files)

            # End session
            await self.end_session(f"{session_name} completed")

            # Save all collected audio
            self.save_collected_audio()

            # Print summary
            self._print_conversation_summary(result)

            return result.success

        except Exception as e:
            self.logger.error(f"[CLIENT] Simple conversation test failed: {e}")
            return False

    def _print_conversation_summary(self, result: ConversationResult) -> None:
        """
        Print a summary of the multi-turn conversation.

        Args:
            result (ConversationResult): Conversation result to summarize
        """
        self.logger.info("\n" + "=" * 50)
        self.logger.info("[CLIENT] MULTI-TURN CONVERSATION SUMMARY")
        self.logger.info("=" * 50)

        success_status = "SUCCESS" if result.success else "FAILED"
        self.logger.info(f"Overall Status: {success_status}")
        self.logger.info(
            f"Completed Turns: {result.completed_turns}/{result.total_turns}"
        )

        if result.greeting_received:
            self.logger.info(
                f"Initial Greeting: Received ({result.greeting_chunks} chunks)"
            )
        else:
            self.logger.info("Initial Greeting: Not received")

        if result.error:
            self.logger.error(f"Overall Error: {result.error}")

        if result.duration:
            self.logger.info(f"Duration: {result.duration:.2f}s")

        self.logger.info(f"Success Rate: {result.success_rate:.1f}%")

        self.logger.info("\nTurn-by-turn Results:")
        for turn in result.turns:
            turn_num = turn["turn_number"]
            audio_file = turn["audio_file"]

            status_parts = []
            if turn["user_audio_sent"]:
                status_parts.append("Audio Sent")
            if turn["ai_response_received"]:
                status_parts.append(
                    f"Response Received ({turn['response_chunks']} chunks)"
                )

            status = " → ".join(status_parts) if status_parts else "Failed"

            self.logger.info(f"  Turn {turn_num}: {audio_file} → {status}")

            if turn.get("error"):
                self.logger.error(f"    Error: {turn['error']}")

        self.logger.info("=" * 50)
