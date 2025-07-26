"""
Conversation management for the AudioCodes mock client.

This module provides comprehensive multi-turn conversation handling, audio collection,
and conversation result tracking for the AudioCodes mock client. It manages the
complete lifecycle of conversations from initiation to completion.

The ConversationManager handles:
- Multi-turn conversation orchestration
- Audio collection and management (greeting and response)
- Conversation state tracking and analysis
- Turn-by-turn result recording
- Audio saving and analysis capabilities
- Conversation timing and performance metrics
- Error handling and recovery

The conversation manager provides a high-level interface for conducting
realistic conversation testing scenarios with detailed result analysis.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from opusagent.config.constants import NO_NEW_CHUNKS_THRESHOLD

from .audio_manager import AudioManager
from .models import ConversationResult, ConversationState
from .session_manager import SessionManager


class ConversationManager:
    """
    Conversation manager for the AudioCodes mock client.

    This class handles multi-turn conversations, audio collection, and provides
    methods for conversation testing and analysis. It orchestrates the complete
    conversation flow from user input to AI response collection.

    The ConversationManager provides:
    - Multi-turn conversation orchestration with configurable parameters
    - Automatic audio collection for greetings and responses
    - Turn-by-turn result tracking and analysis
    - Conversation timing and performance metrics
    - Audio saving and analysis capabilities
    - Comprehensive error handling and recovery
    - Conversation state management and reset functionality

    Attributes:
        logger (logging.Logger): Logger instance for debugging and monitoring
        session_manager (SessionManager): Session manager for state coordination
        audio_manager (AudioManager): Audio manager for file operations
        conversation_state (Optional[ConversationState]): Current conversation state
    """

    def __init__(
        self,
        session_manager: SessionManager,
        audio_manager: AudioManager,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the ConversationManager with dependencies and logging.

        Args:
            session_manager (SessionManager): Session manager for state coordination
            audio_manager (AudioManager): Audio manager for file operations and saving
            logger (Optional[logging.Logger]): Logger instance for debugging and monitoring.
                                             If None, creates a default logger for this module.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.session_manager = session_manager
        self.audio_manager = audio_manager
        self.conversation_state: Optional[ConversationState] = None

    def start_conversation(self, conversation_id: str) -> None:
        """
        Start a new conversation with the specified ID.

        This method initializes a new conversation state and prepares for
        multi-turn conversation testing. It sets up the conversation tracking
        and audio collection infrastructure.

        Args:
            conversation_id (str): Unique conversation identifier

        Example:
            conversation_manager.start_conversation("conv_12345")
        """
        self.conversation_state = ConversationState(conversation_id=conversation_id)
        self.logger.info(f"[CONVERSATION] Started conversation: {conversation_id}")

    async def wait_for_greeting(self, timeout: float = 20.0) -> List[str]:
        """
        Wait for and collect LLM greeting audio from the bridge server.

        This method waits for the initial greeting audio from the AI system,
        collecting all audio chunks until the greeting is complete. It's used
        to capture the AI's initial response before user interaction begins.

        The greeting collection process:
        1. Wait for greeting audio to start (playStream.start)
        2. Collect all audio chunks until playStream.stop
        3. Return collected greeting chunks for analysis
        4. Handle timeout scenarios gracefully

        Args:
            timeout (float): Maximum time to wait for greeting in seconds (default: 20.0)

        Returns:
            List[str]: List of base64-encoded greeting audio chunks, or empty list if timeout

        Example:
            greeting_chunks = await conversation_manager.wait_for_greeting(timeout=15.0)
            if greeting_chunks:
                print(f"Received greeting with {len(greeting_chunks)} chunks")
        """
        if not self.conversation_state:
            self.logger.error("[CONVERSATION] No conversation state available")
            return []

        self.logger.info("[CONVERSATION] Waiting for LLM greeting...")

        # Calculate end time for timeout
        end_time = asyncio.get_event_loop().time() + timeout
        last_chunk_count = 0
        no_new_chunks_count = 0

        # Poll for greeting completion
        while asyncio.get_event_loop().time() < end_time:
            current_chunk_count = len(self.conversation_state.greeting_chunks)

            # Check if we have greeting chunks and collection is complete
            if (
                current_chunk_count > 0
                and not self.conversation_state.collecting_greeting
            ):
                self.logger.info(
                    f"[CONVERSATION] Greeting received: {current_chunk_count} chunks"
                )
                return self.conversation_state.greeting_chunks.copy()

            # Check if we have greeting chunks but collection flag is still true
            # This can happen if the play stream stop message hasn't been processed yet
            if current_chunk_count > 0:
                if current_chunk_count == last_chunk_count:
                    no_new_chunks_count += 1
                    # If no new chunks for 2 seconds, assume greeting is complete
                    if no_new_chunks_count >= NO_NEW_CHUNKS_THRESHOLD:
                        self.logger.info(
                            f"[CONVERSATION] Greeting appears complete (no new chunks for 2s): {current_chunk_count} chunks"
                        )
                        return self.conversation_state.greeting_chunks.copy()
                else:
                    no_new_chunks_count = 0
                    last_chunk_count = current_chunk_count

            await asyncio.sleep(0.1)

        self.logger.error("[CONVERSATION] Timeout waiting for LLM greeting")
        return []

    async def wait_for_response(self, timeout: float = 45.0) -> List[str]:
        """
        Wait for and collect LLM response audio from the bridge server.

        This method waits for the AI response audio after user input, collecting
        all audio chunks until the response is complete. It's used for each
        conversation turn to capture the AI's response.

        The response collection process:
        1. Clear previous response chunks to start fresh
        2. Wait for response audio to start (playStream.start)
        3. Collect all audio chunks until playStream.stop
        4. Return collected response chunks for analysis
        5. Handle timeout scenarios gracefully

        Args:
            timeout (float): Maximum time to wait for response in seconds (default: 45.0)

        Returns:
            List[str]: List of base64-encoded response audio chunks, or empty list if timeout

        Example:
            response_chunks = await conversation_manager.wait_for_response(timeout=30.0)
            if response_chunks:
                print(f"Received response with {len(response_chunks)} chunks")
        """
        if not self.conversation_state:
            self.logger.error("[CONVERSATION] No conversation state available")
            return []

        # Clear previous response chunks for this turn
        self.conversation_state.response_chunks.clear()

        self.logger.info("[CONVERSATION] Waiting for LLM response...")

        # Calculate end time for timeout
        end_time = asyncio.get_event_loop().time() + timeout
        last_chunk_count = 0
        no_new_chunks_count = 0

        # Poll for response completion
        while asyncio.get_event_loop().time() < end_time:
            current_chunk_count = len(self.conversation_state.response_chunks)

            # Check if we have response chunks and collection is complete
            if (
                current_chunk_count > 0
                and not self.conversation_state.collecting_response
            ):
                self.logger.info(
                    f"[CONVERSATION] Response received: {current_chunk_count} chunks"
                )
                return self.conversation_state.response_chunks.copy()

            # Check if we have response chunks but collection flag is still true
            # This can happen if the play stream stop message hasn't been processed yet
            if current_chunk_count > 0:
                if current_chunk_count == last_chunk_count:
                    no_new_chunks_count += 1
                    # If no new chunks for 2 seconds, assume response is complete
                    if no_new_chunks_count >= NO_NEW_CHUNKS_THRESHOLD:
                        self.logger.info(
                            f"[CONVERSATION] Response appears complete (no new chunks for 2s): {current_chunk_count} chunks"
                        )
                        return self.conversation_state.response_chunks.copy()
                else:
                    no_new_chunks_count = 0
                    last_chunk_count = current_chunk_count

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
        Conduct a comprehensive multi-turn conversation using a list of audio files.

        This method orchestrates a complete multi-turn conversation, processing
        each audio file as a user turn and collecting the corresponding AI responses.
        It provides detailed tracking and analysis of the conversation flow.

        The conversation process:
        1. Wait for initial greeting if requested
        2. Process each audio file as a conversation turn
        3. Send user audio and wait for AI response
        4. Track turn-by-turn results and timing
        5. Handle errors gracefully and continue if possible
        6. Generate comprehensive conversation results

        Args:
            audio_files: List of paths to audio files for user turns
            wait_for_greeting: Whether to wait for initial AI greeting (default: True)
            turn_delay: Delay between conversation turns in seconds (default: 2.0)
            chunk_delay: Delay between audio chunks in seconds (default: 0.02)

        Returns:
            ConversationResult: Comprehensive conversation results including:
                               - Success metrics and timing
                               - Turn-by-turn analysis
                               - Audio collection statistics
                               - Error information if any

        Example:
            result = await conversation_manager.multi_turn_conversation([
                "audio/turn1.wav",
                "audio/turn2.wav",
                "audio/turn3.wav"
            ])
            print(f"Conversation success rate: {result.success_rate:.1f}%")
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

        # Initialize conversation result tracking
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

                # Initialize turn result tracking
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

                # Send user audio for this turn
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

                # Wait for AI response for this turn
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

            # Log conversation completion summary
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
        Send user audio to the bridge server for processing.

        This method loads and sends user audio to the bridge server, simulating
        user input during conversation turns. It handles audio loading, chunking,
        and streaming with configurable timing.

        The audio sending process:
        1. Load audio file and convert to chunks
        2. Send audio chunks with specified timing
        3. Handle errors and provide detailed logging
        4. Return success/failure status

        Args:
            audio_file_path (str): Path to the audio file to send
            chunk_delay (float): Delay between audio chunks in seconds (default: 0.02)

        Returns:
            bool: True if audio was sent successfully, False otherwise

        Example:
            success = await conversation_manager._send_user_audio("audio/user_input.wav")
            if success:
                print("User audio sent successfully")
        """
        # This method would need to be implemented to actually send audio
        # For now, we'll simulate the process
        try:
            # Load audio chunks from file
            audio_chunks = self.audio_manager.load_audio_chunks(audio_file_path)
            if not audio_chunks:
                return False

            self.logger.info(
                f"[CONVERSATION] Sending user audio: {Path(audio_file_path).name} ({len(audio_chunks)} chunks)"
            )

            # Simulate sending chunks with timing
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
        Save audio from a specific conversation turn for analysis.

        This method saves the AI response audio from a specific conversation turn
        to a file for later analysis, testing, or debugging purposes.

        The saving process:
        1. Create output directory if it doesn't exist
        2. Generate filename based on turn number and conversation ID
        3. Save audio chunks as WAV file
        4. Log saving operation for tracking

        Args:
            turn_number (int): Turn number for filename generation
            audio_chunks (List[str]): Base64-encoded audio chunks to save
            output_dir (str): Output directory for saved files (default: "validation_output")

        Example:
            conversation_manager._save_turn_audio(3, response_chunks, "output/")
        """
        try:
            if not self.conversation_state:
                return

            # Ensure output directory exists
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)

            # Save audio if chunks are available
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
        Save all collected audio for comprehensive analysis.

        This method saves all collected audio (greeting and response) from the
        conversation for later analysis, testing, or debugging purposes.

        The saving process:
        1. Create output directory if it doesn't exist
        2. Save greeting audio if available
        3. Save response audio if available
        4. Use conversation ID for unique filenames
        5. Log saving operations for tracking

        Args:
            output_dir (str): Output directory for saved files (default: "validation_output")

        Example:
            conversation_manager.save_collected_audio("output/")
        """
        if not self.conversation_state:
            self.logger.error("[CONVERSATION] No conversation state available")
            return

        # Ensure output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Generate conversation ID for filename
        conv_id = self.conversation_state.conversation_id[:8]

        # Save greeting audio if available
        if self.conversation_state.greeting_chunks:
            self.audio_manager.save_audio_chunks(
                self.conversation_state.greeting_chunks,
                str(output_path / f"greeting_{conv_id}.wav"),
            )

        # Save response audio if available
        if self.conversation_state.response_chunks:
            self.audio_manager.save_audio_chunks(
                self.conversation_state.response_chunks,
                str(output_path / f"response_{conv_id}.wav"),
            )

    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive summary of the current conversation.

        This method provides a detailed overview of the current conversation
        state, including timing, audio collection statistics, and activity
        tracking information.

        Returns:
            Dict[str, Any]: Conversation summary including:
                           - conversation_id: Unique conversation identifier
                           - turn_count: Number of completed turns
                           - greeting_chunks: Number of greeting audio chunks
                           - response_chunks: Number of response audio chunks
                           - activities_count: Number of received activities
                           - started_at: Conversation start timestamp
                           - last_turn_at: Last turn timestamp
                           - collecting_greeting: Whether currently collecting greeting
                           - collecting_response: Whether currently collecting response

        Example:
            summary = conversation_manager.get_conversation_summary()
            print(f"Conversation ID: {summary['conversation_id']}")
            print(f"Turns completed: {summary['turn_count']}")
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
        """
        Reset the conversation state to initial values.

        This method clears all conversation state and returns the conversation
        manager to its initial state. It's useful for testing scenarios or
        when preparing for a new conversation after a previous one has ended.

        The reset process:
        1. Preserve conversation ID for continuity
        2. Clear all audio chunks and activities
        3. Reset collection flags and turn count
        4. Update timestamps
        5. Log reset operation

        Example:
            conversation_manager.reset_conversation_state()
            print("Conversation state reset")
        """
        if self.conversation_state:
            # Preserve conversation ID but reset everything else
            conv_id = self.conversation_state.conversation_id
            self.conversation_state = ConversationState(conversation_id=conv_id)
            self.logger.info("[CONVERSATION] Conversation state reset")
