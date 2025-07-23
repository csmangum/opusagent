"""Manager for handling transcripts in real-time audio communication.

This module provides functionality to manage transcripts for both input (user) and output (AI)
audio streams, including buffering, logging, and recording transcripts.
"""

from typing import List, Optional, Dict, Any

from opusagent.call_recorder import AudioChannel, CallRecorder, TranscriptType
from opusagent.config.logging_config import configure_logging

logger = configure_logging("transcript_manager")


class TranscriptManager:
    """Manager class for handling transcripts in real-time audio communication.

    This class manages the buffering, logging, and recording of transcripts for both
    input (user) and output (AI) audio streams.

    Attributes:
        call_recorder (Optional[CallRecorder]): Recorder for call transcripts and audio
        input_transcript_buffer (List[str]): Buffer for accumulating input audio transcriptions
        output_transcript_buffer (List[str]): Buffer for accumulating output audio transcriptions
    """

    def __init__(self, call_recorder: Optional[CallRecorder] = None):
        """Initialize the transcript manager.

        Args:
            call_recorder (Optional[CallRecorder]): Recorder for call transcripts and audio
        """
        self.call_recorder = call_recorder
        self.input_transcript_buffer: List[str] = []  # User → AI
        self.output_transcript_buffer: List[str] = []  # AI → User

    async def handle_input_transcript_delta(self, delta: str) -> None:
        """Handle input audio transcription delta events.

        Args:
            delta (str): The transcript delta to process
        """
        if delta:
            self.input_transcript_buffer.append(delta)
        logger.debug(f"Received input audio transcription delta: {delta}")

    async def handle_input_transcript_completed(self) -> None:
        """Handle input audio transcription completion events."""
        full_transcript = "".join(self.input_transcript_buffer)
        logger.info(f"Full user transcript (input audio): {full_transcript}")

        # Record transcript if recorder is available
        if self.call_recorder and full_transcript.strip():
            await self.call_recorder.add_transcript(
                text=full_transcript,
                channel=AudioChannel.CALLER,
                transcript_type=TranscriptType.INPUT,
            )

        self.input_transcript_buffer.clear()
        logger.info("Input audio transcription completed")

    async def handle_output_transcript_delta(self, delta: str) -> None:
        """Handle output audio transcript delta events.

        Args:
            delta (str): The transcript delta to process
        """
        if delta:
            self.output_transcript_buffer.append(delta)
        logger.debug(f"Received audio transcript delta: {delta}")

    async def handle_output_transcript_completed(self) -> None:
        """Handle output audio transcript completion events."""
        full_transcript = "".join(self.output_transcript_buffer)
        logger.info(f"Full AI transcript (output audio): {full_transcript}")

        # Record transcript if recorder is available
        if self.call_recorder and full_transcript.strip():
            await self.call_recorder.add_transcript(
                text=full_transcript,
                channel=AudioChannel.BOT,
                transcript_type=TranscriptType.OUTPUT,
            )

        self.output_transcript_buffer.clear()
        logger.info("Audio transcript completed")

    def set_call_recorder(self, call_recorder: CallRecorder) -> None:
        """Set the call recorder instance.

        Args:
            call_recorder (CallRecorder): The call recorder instance to use
        """
        self.call_recorder = call_recorder

    def restore_conversation_context(self, conversation_history: List[Dict[str, Any]]) -> None:
        """Restore conversation context from session state.
        
        Args:
            conversation_history: List of conversation items from session state
        """
        if not conversation_history:
            return
            
        logger.info(f"Restoring conversation context with {len(conversation_history)} items")
        
        for item in conversation_history:
            try:
                # Restore based on item type
                if item.get("type") == "input":
                    # Restore input transcript
                    text = item.get("text", "")
                    if text:
                        self.input_transcript_buffer.append(text)
                        logger.debug(f"Restored input transcript: {text}")
                        
                elif item.get("type") == "output":
                    # Restore output transcript
                    text = item.get("text", "")
                    if text:
                        self.output_transcript_buffer.append(text)
                        logger.debug(f"Restored output transcript: {text}")
                        
            except Exception as e:
                logger.error(f"Error restoring conversation item: {e}")
                
        logger.info(f"Restored {len(self.input_transcript_buffer)} input and {len(self.output_transcript_buffer)} output transcript items")

    def get_conversation_context(self) -> List[Dict[str, Any]]:
        """Get current conversation context for session state storage.
        
        Returns:
            List of conversation items representing current context
        """
        conversation_items = []
        
        # Add input transcript items
        for text in self.input_transcript_buffer:
            conversation_items.append({
                "type": "input",
                "text": text,
                "timestamp": None  # Could add timestamp tracking if needed
            })
            
        # Add output transcript items
        for text in self.output_transcript_buffer:
            conversation_items.append({
                "type": "output", 
                "text": text,
                "timestamp": None  # Could add timestamp tracking if needed
            })
            
        return conversation_items

    def clear_conversation_context(self) -> None:
        """Clear all conversation context buffers."""
        self.input_transcript_buffer.clear()
        self.output_transcript_buffer.clear()
        logger.info("Cleared conversation context buffers")
