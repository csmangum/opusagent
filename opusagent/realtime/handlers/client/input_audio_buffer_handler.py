"""
Handler for input audio buffer events.

The input audio buffer events allow managing audio input for the session:

- input_audio_buffer.append: Append audio data to the input buffer
- input_audio_buffer.commit: Commit the audio buffer to the conversation
- input_audio_buffer.clear: Clear the audio buffer

The audio format must match the session's input_audio_format setting:
- pcm16: 16-bit PCM at 24kHz sample rate, single channel (mono), little-endian
- g711_ulaw: G.711 µ-law encoded audio
- g711_alaw: G.711 A-law encoded audio

Audio data should be sent as base64 encoded strings.
"""

from typing import Any, Dict, Optional, Callable, Awaitable, List
import base64
from opusagent.models.openai_api import (
    InputAudioBufferAppendEvent,
    InputAudioBufferCommitEvent,
    InputAudioBufferClearEvent
)

class InputAudioBufferHandler:
    def __init__(
        self,
        send_event_callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ):
        """
        Initialize the input audio buffer handler.
        
        Args:
            send_event_callback: Callback function to send events back to the server
        """
        self.send_event = send_event_callback
        self.audio_buffer: List[str] = []  # Store base64 encoded audio chunks
        self.MAX_AUDIO_SIZE = 15 * 1024 * 1024  # 15 MiB in bytes
        
    async def handle_append(self, event: Dict[str, Any]) -> None:
        """
        Handle the input_audio_buffer.append event.
        
        This appends audio data to the input buffer. The audio data must not exceed 15 MiB.
        
        Args:
            event: The input_audio_buffer.append event data containing:
                - event_id: Optional client-generated ID for the event
                - type: Must be "input_audio_buffer.append"
                - audio: Base64 encoded audio data
        """
        try:
            append_event = InputAudioBufferAppendEvent(**event)
            
            # Calculate the size of the base64 decoded audio data
            audio_bytes = base64.b64decode(append_event.audio)
            if len(audio_bytes) > self.MAX_AUDIO_SIZE:
                await self._send_error_response(
                    event.get("event_id"),
                    "invalid_request_error",
                    f"Audio data exceeds maximum size of {self.MAX_AUDIO_SIZE} bytes"
                )
                return
                
            self.audio_buffer.append(append_event.audio)
        except Exception as e:
            await self._send_error_response(
                event.get("event_id"),
                "invalid_request_error",
                f"Failed to append audio: {str(e)}"
            )
            
    async def handle_commit(self, event: Dict[str, Any]) -> None:
        """
        Handle the input_audio_buffer.commit event.
        
        This commits the audio buffer to the conversation. The server will process
        the audio and respond with appropriate events (e.g., transcription, turn
        detection).
        
        Args:
            event: The input_audio_buffer.commit event data containing:
                - event_id: Optional client-generated ID for the event
                - type: Must be "input_audio_buffer.commit"
        """
        try:
            if not self.audio_buffer:
                await self._send_error_response(
                    event.get("event_id"),
                    "invalid_request_error",
                    "No audio data to commit"
                )
                return
                
            # Process the audio buffer here (e.g., send to transcription service)
            # For now, just clear the buffer and send a committed event
            self.audio_buffer.clear()
            
            await self.send_event({
                "type": "input_audio_buffer.committed",
                "event_id": event.get("event_id")
            })
        except Exception as e:
            await self._send_error_response(
                event.get("event_id"),
                "internal_error",
                f"Failed to commit audio: {str(e)}"
            )
            
    async def handle_clear(self, event: Dict[str, Any]) -> None:
        """
        Handle the input_audio_buffer.clear event.
        
        This clears the audio buffer without processing it.
        
        Args:
            event: The input_audio_buffer.clear event data containing:
                - event_id: Optional client-generated ID for the event
                - type: Must be "input_audio_buffer.clear"
        """
        self.audio_buffer.clear()
        await self.send_event({
            "type": "input_audio_buffer.cleared",
            "event_id": event.get("event_id")
        })
        
    async def _send_error_response(
        self, 
        event_id: Optional[str], 
        code: str, 
        message: str
    ) -> None:
        """Send an error response."""
        await self.send_event({
            "type": "error",
            "event_id": event_id,
            "code": code,
            "message": message
        }) 