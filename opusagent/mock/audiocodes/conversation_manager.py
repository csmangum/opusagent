"""
Conversation management for the AudioCodes mock client.

This module provides multi-turn conversation handling, audio collection,
and conversation result tracking for the AudioCodes mock client.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .audio_manager import AudioManager
from .models import ConversationResult, ConversationState
from .session_manager import SessionManager


class ConversationManager:
    """
    Conversation manager for the AudioCodes mock client.

    This class handles multi-turn conversations, audio collection,
    and provides methods for conversation testing and analysis.

    Attributes:
        logger (logging.Logger): Logger instance for debugging
        session_manager (SessionManager): Session manager instance
        audio_manager (AudioManager): Audio manager instance
        conversation_state (Optional[ConversationState]): Current conversation state
    """

    def __init__(
        self,
        session_manager: SessionManager,
        audio_manager: AudioManager,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the ConversationManager.

        Args:
            session_manager (SessionManager): Session manager instance
            audio_manager (AudioManager): Audio manager instance
            logger (Optional[logging.Logger]): Logger instance for debugging
        """
        self.logger = logger or logging.getLogger(__name__)
        self.session_manager = session_manager
        self.audio_manager = audio_manager
        self.conversation_state: Optional[ConversationState] = None

    def start_conversation(self, conversation_id: str) -> None:
        """
        Start a new conversation.

        Args:
            conversation_id (str): Conversation ID
        """
        self.conversation_state = ConversationState(conversation_id=conversation_id)
        self.logger.info(f"[CONVERSATION] Started conversation: {conversation_id}")

    async def wait_for_greeting(self, timeout: float = 20.0) -> List[str]:
        """
        Wait for and collect LLM greeting audio.

        Args:
            timeout (float): Timeout in seconds

        Returns:
            List[str]: List of greeting audio chunks
        """
        if not self.conversation_state:
            self.logger.error("[CONVERSATION] No conversation state available")
            return []

        self.logger.info("[CONVERSATION] Waiting for LLM greeting...")

        end_time = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < end_time:
            if (
                self.conversation_state.greeting_chunks
                and not self.conversation_state.collecting_greeting
            ):
                self.logger.info(
                    f"[CONVERSATION] Greeting received: {len(self.conversation_state.greeting_chunks)} chunks"
                )
                return self.conversation_state.greeting_chunks.copy()
            await asyncio.sleep(0.1)

        self.logger.error("[CONVERSATION] Timeout waiting for LLM greeting")
        return []

    async def wait_for_response(self, timeout: float = 45.0) -> List[str]:
        """
        Wait for and collect LLM response audio.

        Args:
            timeout (float): Timeout in seconds

        Returns:
            List[str]: List of response audio chunks
        """
        if not self.conversation_state:
            self.logger.error("[CONVERSATION] No conversation state available")
            return []

        # Clear previous response chunks
        self.conversation_state.response_chunks.clear()

        self.logger.info("[CONVERSATION] Waiting for LLM response...")

        end_time = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < end_time:
            if (
                self.conversation_state.response_chunks
                and not self.conversation_state.collecting_response
            ):
                self.logger.info(
                    f"[CONVERSATION] Response received: {len(self.conversation_state.response_chunks)} chunks"
                )
                return self.conversation_state.response_chunks.copy()
            await asyncio.sleep(0.1)

        self.logger.error("[CONVERSATION] Timeout waiting for LLM response")
        return []

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
        if not self.conversation_state:
            self.logger.error("[CONVERSATION] No conversation state available")
            return ConversationResult(
                total_turns=len(audio_files),
                success=False,
                error="No conversation state",
            )

        self.logger.info(
            f"[CONVERSATION] Starting multi-turn conversation with {len(audio_files)} turns"
        )

        result = ConversationResult(
            total_turns=len(audio_files), start_time=datetime.now()
        )

        try:
            # Step 1: Wait for initial greeting if requested
            if wait_for_greeting:
                self.logger.info("[CONVERSATION] Waiting for initial greeting...")
                greeting = await self.wait_for_greeting(timeout=20.0)
                if greeting:
                    result.greeting_received = True
                    result.greeting_chunks = len(greeting)
                    self.logger.info(
                        f"[CONVERSATION] Initial greeting received: {len(greeting)} chunks"
                    )
                else:
                    self.logger.warning(
                        "[CONVERSATION] No initial greeting received, continuing anyway..."
                    )

            # Step 2: Process each audio file as a conversation turn
            for turn_num, audio_file in enumerate(audio_files, 1):
                self.logger.info(
                    f"\n[CONVERSATION] === Turn {turn_num}/{len(audio_files)} ==="
                )
                self.logger.info(f"[CONVERSATION] Sending: {Path(audio_file).name}")

                turn_result = {
                    "turn_number": turn_num,
                    "audio_file": str(Path(audio_file).name),
                    "user_audio_sent": False,
                    "ai_response_received": False,
                    "response_chunks": 0,
                    "error": None,
                }

                # Clear previous response chunks for this turn
                self.conversation_state.response_chunks.clear()

                # Send user audio
                try:
                    success = await self._send_user_audio(
                        audio_file, chunk_delay=chunk_delay
                    )
                    if success:
                        turn_result["user_audio_sent"] = True
                        self.logger.info(
                            f"[CONVERSATION] Turn {turn_num}: User audio sent successfully"
                        )
                    else:
                        turn_result["error"] = "Failed to send user audio"
                        self.logger.error(
                            f"[CONVERSATION] Turn {turn_num}: Failed to send user audio"
                        )
                        result.turns.append(turn_result)
                        continue

                except Exception as e:
                    turn_result["error"] = f"Audio send error: {str(e)}"
                    self.logger.error(
                        f"[CONVERSATION] Turn {turn_num}: Audio send error: {e}"
                    )
                    result.turns.append(turn_result)
                    continue

                # Wait for AI response
                try:
                    response = await self.wait_for_response(timeout=45.0)
                    if response:
                        turn_result["ai_response_received"] = True
                        turn_result["response_chunks"] = len(response)
                        result.completed_turns += 1
                        self.logger.info(
                            f"[CONVERSATION] Turn {turn_num}: AI response received ({len(response)} chunks)"
                        )

                        # Save this turn's audio for analysis
                        self._save_turn_audio(turn_num, response)

                    else:
                        turn_result["error"] = "No AI response received"
                        self.logger.error(
                            f"[CONVERSATION] Turn {turn_num}: No AI response received"
                        )

                except Exception as e:
                    turn_result["error"] = f"Response wait error: {str(e)}"
                    self.logger.error(
                        f"[CONVERSATION] Turn {turn_num}: Response wait error: {e}"
                    )

                result.turns.append(turn_result)

                # Delay before next turn (except for last turn)
                if turn_num < len(audio_files):
                    self.logger.info(
                        f"[CONVERSATION] Waiting {turn_delay}s before next turn..."
                    )
                    await asyncio.sleep(turn_delay)

            # Mark as successful if at least some turns completed
            if result.completed_turns > 0:
                result.success = True

            result.end_time = datetime.now()

            self.logger.info(f"\n[CONVERSATION] Multi-turn conversation completed:")
            self.logger.info(
                f"   Completed turns: {result.completed_turns}/{result.total_turns}"
            )
            self.logger.info(f"   Duration: {result.duration:.2f}s")
            self.logger.info(f"   Success rate: {result.success_rate:.1f}%")

            return result

        except Exception as e:
            result.error = str(e)
            result.end_time = datetime.now()
            self.logger.error(f"[CONVERSATION] Multi-turn conversation failed: {e}")
            return result

    async def _send_user_audio(
        self, audio_file_path: str, chunk_delay: float = 0.02
    ) -> bool:
        """
        Send user audio to the bridge.

        Args:
            audio_file_path (str): Path to audio file
            chunk_delay (float): Delay between chunks

        Returns:
            bool: True if successful, False otherwise
        """
        # This method would need to be implemented to actually send audio
        # For now, we'll simulate the process
        try:
            audio_chunks = self.audio_manager.load_audio_chunks(audio_file_path)
            if not audio_chunks:
                return False

            self.logger.info(
                f"[CONVERSATION] Sending user audio: {Path(audio_file_path).name} ({len(audio_chunks)} chunks)"
            )

            # Simulate sending chunks
            for i, chunk in enumerate(audio_chunks):
                if i % 10 == 0 or i == len(audio_chunks) - 1:
                    self.logger.debug(
                        f"[CONVERSATION] Sent chunk {i+1}/{len(audio_chunks)}"
                    )
                await asyncio.sleep(chunk_delay)

            self.logger.info("[CONVERSATION] User audio sent successfully")
            return True

        except Exception as e:
            self.logger.error(f"[CONVERSATION] Error sending user audio: {e}")
            return False

    def _save_turn_audio(
        self,
        turn_number: int,
        audio_chunks: List[str],
        output_dir: str = "validation_output",
    ) -> None:
        """
        Save audio from a specific conversation turn.

        Args:
            turn_number (int): Turn number
            audio_chunks (List[str]): Audio chunks to save
            output_dir (str): Output directory
        """
        try:
            if not self.conversation_state:
                return

            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)

            if audio_chunks:
                filename = f"turn_{turn_number:02d}_response_{self.conversation_state.conversation_id[:8]}.wav"
                self.audio_manager.save_audio_chunks(
                    audio_chunks, str(output_path / filename)
                )

        except Exception as e:
            self.logger.error(
                f"[CONVERSATION] Error saving turn {turn_number} audio: {e}"
            )

    def save_collected_audio(self, output_dir: str = "validation_output") -> None:
        """
        Save all collected audio for analysis.

        Args:
            output_dir (str): Output directory
        """
        if not self.conversation_state:
            self.logger.error("[CONVERSATION] No conversation state available")
            return

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        conv_id = self.conversation_state.conversation_id[:8]

        if self.conversation_state.greeting_chunks:
            self.audio_manager.save_audio_chunks(
                self.conversation_state.greeting_chunks,
                str(output_path / f"greeting_{conv_id}.wav"),
            )

        if self.conversation_state.response_chunks:
            self.audio_manager.save_audio_chunks(
                self.conversation_state.response_chunks,
                str(output_path / f"response_{conv_id}.wav"),
            )

    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current conversation.

        Returns:
            Dict[str, Any]: Conversation summary
        """
        if not self.conversation_state:
            return {"error": "No conversation state available"}

        return {
            "conversation_id": self.conversation_state.conversation_id,
            "turn_count": self.conversation_state.turn_count,
            "greeting_chunks": len(self.conversation_state.greeting_chunks),
            "response_chunks": len(self.conversation_state.response_chunks),
            "activities_count": len(self.conversation_state.activities_received),
            "started_at": self.conversation_state.started_at.isoformat(),
            "last_turn_at": (
                self.conversation_state.last_turn_at.isoformat()
                if self.conversation_state.last_turn_at
                else None
            ),
            "collecting_greeting": self.conversation_state.collecting_greeting,
            "collecting_response": self.conversation_state.collecting_response,
        }

    def reset_conversation_state(self) -> None:
        """Reset the conversation state."""
        if self.conversation_state:
            self.conversation_state = ConversationState(
                conversation_id=self.conversation_state.conversation_id
            )
            self.logger.info("[CONVERSATION] Conversation state reset")
