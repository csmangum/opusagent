"""
Handler for transcription session update events.

The transcription_session.update event allows updating transcription-specific settings
for the session. This includes:

- input_audio_format: Format of input audio (pcm16, g711_ulaw, g711_alaw)
- input_audio_transcription: Configuration for transcription settings
  - model: The transcription model to use (e.g., "gpt-4o-transcribe")
  - prompt: Optional prompt for transcription
  - language: Optional language code for transcription
- turn_detection: Configuration for turn detection
  - type: "server_vad" or "semantic_vad"
  - threshold: VAD threshold (0.0 to 1.0)
  - prefix_padding_ms: Padding before speech start
  - silence_duration_ms: Duration of silence to detect end of speech
  - create_response: Whether to automatically create responses
- input_audio_noise_reduction: Configuration for noise reduction
  - type: "near_field" or other noise reduction types
- include: List of additional fields to include in responses
  - e.g., "item.input_audio_transcription.logprobs"

The server will respond with a transcription_session.updated event showing the full,
effective configuration. Only the fields that are present are updated.
"""

from typing import Any, Awaitable, Callable, Dict, Optional, List

class TranscriptionSessionHandler:
    def __init__(
        self,
        send_event_callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ):
        """
        Initialize the transcription session handler.

        Args:
            send_event_callback: Callback function to send events back to the server
        """
        self.send_event = send_event_callback
        self.transcription_config: Dict[str, Any] = {}

    async def handle(self, event: Dict[str, Any]) -> None:
        """
        Handle the transcription_session.update event.

        Args:
            event: The transcription_session.update event data containing:
                - event_id: Optional client-generated ID for the event
                - type: Must be "transcription_session.update"
                - session: The transcription session configuration to update
        """
        try:
            # Validate event type
            if event.get("type") != "transcription_session.update":
                await self._send_error_response(
                    event.get("event_id"),
                    "invalid_event_type",
                    "Event type must be 'transcription_session.update'"
                )
                return

            session_config = event.get("session", {})
            if not isinstance(session_config, dict):
                await self._send_error_response(
                    event.get("event_id"),
                    "invalid_session_config",
                    "Session configuration must be a dictionary"
                )
                return

            # Validate and update input_audio_format
            if "input_audio_format" in session_config:
                audio_format = session_config["input_audio_format"]
                if audio_format not in ["pcm16", "g711_ulaw", "g711_alaw"]:
                    await self._send_error_response(
                        event.get("event_id"),
                        "invalid_audio_format",
                        "Input audio format must be one of: pcm16, g711_ulaw, g711_alaw"
                    )
                    return
                self.transcription_config["input_audio_format"] = audio_format

            # Validate and update input_audio_transcription
            if "input_audio_transcription" in session_config:
                transcription = session_config["input_audio_transcription"]
                if transcription is not None:
                    if not isinstance(transcription, dict):
                        await self._send_error_response(
                            event.get("event_id"),
                            "invalid_transcription_config",
                            "Transcription configuration must be a dictionary or null"
                        )
                        return
                    
                    if "model" not in transcription:
                        await self._send_error_response(
                            event.get("event_id"),
                            "missing_transcription_model",
                            "Transcription configuration must include a model"
                        )
                        return
                    
                    self.transcription_config["input_audio_transcription"] = {
                        "model": transcription["model"],
                        "prompt": transcription.get("prompt", ""),
                        "language": transcription.get("language", "")
                    }
                else:
                    self.transcription_config["input_audio_transcription"] = None

            # Validate and update turn_detection
            if "turn_detection" in session_config:
                turn_detection = session_config["turn_detection"]
                if turn_detection is not None:
                    if not isinstance(turn_detection, dict):
                        await self._send_error_response(
                            event.get("event_id"),
                            "invalid_turn_detection_config",
                            "Turn detection configuration must be a dictionary or null"
                        )
                        return

                    if "type" not in turn_detection:
                        await self._send_error_response(
                            event.get("event_id"),
                            "missing_turn_detection_type",
                            "Turn detection configuration must include a type"
                        )
                        return

                    if turn_detection["type"] not in ["server_vad", "semantic_vad"]:
                        await self._send_error_response(
                            event.get("event_id"),
                            "invalid_turn_detection_type",
                            "Turn detection type must be 'server_vad' or 'semantic_vad'"
                        )
                        return

                    self.transcription_config["turn_detection"] = {
                        "type": turn_detection["type"],
                        "threshold": turn_detection.get("threshold", 0.5),
                        "prefix_padding_ms": turn_detection.get("prefix_padding_ms", 300),
                        "silence_duration_ms": turn_detection.get("silence_duration_ms", 500),
                        "create_response": turn_detection.get("create_response", True)
                    }
                else:
                    self.transcription_config["turn_detection"] = None

            # Validate and update input_audio_noise_reduction
            if "input_audio_noise_reduction" in session_config:
                noise_reduction = session_config["input_audio_noise_reduction"]
                if noise_reduction is not None:
                    if not isinstance(noise_reduction, dict):
                        await self._send_error_response(
                            event.get("event_id"),
                            "invalid_noise_reduction_config",
                            "Noise reduction configuration must be a dictionary or null"
                        )
                        return

                    if "type" not in noise_reduction:
                        await self._send_error_response(
                            event.get("event_id"),
                            "missing_noise_reduction_type",
                            "Noise reduction configuration must include a type"
                        )
                        return

                    self.transcription_config["input_audio_noise_reduction"] = {
                        "type": noise_reduction["type"]
                    }
                else:
                    self.transcription_config["input_audio_noise_reduction"] = None

            # Validate and update include list
            if "include" in session_config:
                include = session_config["include"]
                if not isinstance(include, list):
                    await self._send_error_response(
                        event.get("event_id"),
                        "invalid_include_config",
                        "Include configuration must be a list"
                    )
                    return
                self.transcription_config["include"] = include

            # Send success response with updated configuration
            await self.send_event({
                "type": "transcription_session.updated",
                "event_id": event.get("event_id"),
                "session": self.transcription_config
            })

        except Exception as e:
            await self._send_error_response(
                event.get("event_id"),
                "internal_error",
                f"An error occurred while processing the transcription session update: {str(e)}"
            )

    async def _send_error_response(
        self,
        event_id: Optional[str],
        code: str,
        message: str
    ) -> None:
        """
        Send an error response event.

        Args:
            event_id: The ID of the event that caused the error
            code: The error code
            message: The error message
        """
        await self.send_event({
            "type": "error",
            "event_id": event_id,
            "error": {
                "code": code,
                "message": message
            }
        }) 