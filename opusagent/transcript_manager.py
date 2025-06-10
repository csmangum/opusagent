"""Manager for handling transcripts in real-time audio communication.

This module provides functionality to manage transcripts for both input (user) and output (AI)
audio streams, including buffering, logging, and recording transcripts.
"""

from typing import List, Optional

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
