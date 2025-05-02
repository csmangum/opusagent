"""
Handler for session.update events.

The session.update event allows updating the session's default configuration.
The client may send this event at any time to update any field, except for voice.
Note that once a session has been initialized with a particular model, it can't
be changed to another model using session.update.

When the server receives a session.update, it will respond with a session.updated
event showing the full, effective configuration. Only the fields that are present
are updated. To clear a field like instructions, pass an empty string.

Fields that can be updated:
- modalities: The set of modalities the model can respond with (must be 'text' or 'audio')
- instructions: The default system instructions prepended to model calls
- input_audio_format: Format of input audio (pcm16, g711_ulaw, g711_alaw)
- output_audio_format: Format of output audio (pcm16, g711_ulaw, g711_alaw)
- turn_detection: Configuration for turn detection (Server VAD or Semantic VAD)
- tools: Tools (functions) available to the model
- tool_choice: How the model chooses tools (auto, none, required, or function name)
- temperature: Sampling temperature for the model [0.6, 1.2]
- max_response_output_tokens: Maximum number of output tokens for a response (1-4096 or 'inf')

Error Handling:
- Invalid model changes will result in an error response
- Invalid temperature values will result in an error response
- Invalid audio formats will result in an error response
- Invalid tool choices will result in an error response
- Invalid modalities will result in an error response
- Any other errors during processing will result in an internal_error response
"""

from typing import Any, Awaitable, Callable, Dict, Optional


class SessionUpdateHandler:
    def __init__(
        self,
        session_config: Dict[str, Any],
        send_event_callback: Callable[[Dict[str, Any]], Awaitable[None]],
    ):
        """
        Initialize the session update handler.

        Args:
            session_config: The current session configuration dictionary
            send_event_callback: Callback function to send events back to the server

        Sets up validation rules for:
        - Audio formats (pcm16, g711_ulaw, g711_alaw)
        - Tool choices (auto, none, required)
        - Modalities (text, audio)
        """
        self.session_config = session_config
        self.send_event = send_event_callback

        # Define valid values for validation
        self.valid_audio_formats = {"pcm16", "g711_ulaw", "g711_alaw"}
        self.valid_tool_choices = {"auto", "none", "required"}
        self.valid_modalities = {"text", "audio"}

    async def handle(self, event: Dict[str, Any]) -> None:
        """
        Handle the session.update event.

        This updates the session configuration with the new values provided
        in the event. Note that model cannot be changed once set, and voice
        cannot be changed after the model has responded with audio.

        The handler performs extensive validation:
        - Model changes are rejected if the model is already set
        - Temperature must be between 0.6 and 1.2
        - max_response_output_tokens must be between 1 and 4096 or 'inf'
        - Audio formats must be one of: pcm16, g711_ulaw, g711_alaw
        - Tool choice must be 'auto', 'none', 'required', or a function name
        - Modalities must be a list containing only 'text' and/or 'audio'

        Args:
            event: The session.update event data containing:
                - event_id: Optional client-generated ID for the event
                - type: Must be "session.update"
                - session: The session configuration object to update

        Returns:
            None, but sends a session.updated event with the full configuration
            or an error event if validation fails.
        """
        event_id = event.get("event_id")

        try:
            # Get the session data directly from the event
            if "session" not in event or not isinstance(event["session"], dict):
                await self._send_error_response(
                    event_id=event_id,
                    code="invalid_request_error",
                    message="Missing or invalid session field in the update event",
                )
                return

            # Get the update data directly from the event
            update_data = event["session"]

            # Check if trying to change model when it's already set
            if (
                "model" in update_data
                and self.session_config.get("model") is not None
                and update_data["model"] != self.session_config["model"]
            ):
                await self._send_error_response(
                    event_id=event_id,
                    code="invalid_request_error",
                    message="Model cannot be changed after session initialization",
                )
                return

            # Validate temperature range
            if "temperature" in update_data:
                temperature = update_data["temperature"]
                if not 0.6 <= temperature <= 1.2:
                    await self._send_error_response(
                        event_id=event_id,
                        code="invalid_request_error",
                        message="Temperature must be between 0.6 and 1.2",
                    )
                    return

            # Validate max_response_output_tokens
            if "max_response_output_tokens" in update_data:
                tokens = update_data["max_response_output_tokens"]
                if isinstance(tokens, int) and not 1 <= tokens <= 4096:
                    await self._send_error_response(
                        event_id=event_id,
                        code="invalid_request_error",
                        message="max_response_output_tokens must be between 1 and 4096",
                    )
                    return
                elif not isinstance(tokens, int) and tokens != "inf":
                    await self._send_error_response(
                        event_id=event_id,
                        code="invalid_request_error",
                        message="max_response_output_tokens must be an integer or 'inf'",
                    )
                    return

            # Validate audio formats
            if "input_audio_format" in update_data:
                if update_data["input_audio_format"] not in self.valid_audio_formats:
                    await self._send_error_response(
                        event_id=event_id,
                        code="invalid_request_error",
                        message=f"input_audio_format must be one of {self.valid_audio_formats}",
                    )
                    return

            if "output_audio_format" in update_data:
                if update_data["output_audio_format"] not in self.valid_audio_formats:
                    await self._send_error_response(
                        event_id=event_id,
                        code="invalid_request_error",
                        message=f"output_audio_format must be one of {self.valid_audio_formats}",
                    )
                    return

            # Validate tool_choice
            if "tool_choice" in update_data:
                tool_choice = update_data["tool_choice"]
                # Get valid function names from tools
                valid_function_names = []
                if "tools" in self.session_config and self.session_config["tools"]:
                    valid_function_names = [
                        tool.get("function", {}).get("name")
                        for tool in self.session_config["tools"]
                        if tool.get("function", {}).get("name")
                    ]

                if (
                    tool_choice not in self.valid_tool_choices
                    and tool_choice not in valid_function_names
                ):
                    await self._send_error_response(
                        event_id=event_id,
                        code="invalid_request_error",
                        message="tool_choice must be 'auto', 'none', 'required', or a valid function name",
                    )
                    return

            # Validate modalities
            if "modalities" in update_data:
                modalities = update_data["modalities"]
                if not isinstance(modalities, list):
                    await self._send_error_response(
                        event_id=event_id,
                        code="invalid_request_error",
                        message="modalities must be a list",
                    )
                    return

                if not all(m in self.valid_modalities for m in modalities):
                    await self._send_error_response(
                        event_id=event_id,
                        code="invalid_request_error",
                        message=f"modalities must only contain values from {self.valid_modalities}",
                    )
                    return

            # Apply updates to the session configuration
            try:
                for field, value in update_data.items():
                    if field == "instructions" and value == "":
                        # Clear instructions
                        self.session_config[field] = ""
                    elif field == "max_response_output_tokens" and value == "inf":
                        # Handle special case for 'inf'
                        self.session_config[field] = "inf"
                    elif value is not None:
                        self.session_config[field] = value

                # Send the session.updated event with the full configuration
                await self.send_event(
                    {
                        "type": "session.updated",
                        "event_id": event_id,
                        "session": self.session_config,
                    }
                )
            except Exception as e:
                # Handle any errors during update
                await self._send_error_response(
                    event_id=event_id,
                    code="internal_error",
                    message=f"Failed to update session: {str(e)}",
                )
                return

        except Exception as e:
            # Handle any errors during validation
            await self._send_error_response(
                event_id=event_id,
                code="invalid_request_error",
                message=f"Invalid session update: {str(e)}",
            )

    async def _send_error_response(
        self, event_id: Optional[str], code: str, message: str
    ) -> None:
        """Send an error response."""
        await self.send_event(
            {"type": "error", "event_id": event_id, "code": code, "message": message}
        )
