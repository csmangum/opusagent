"""
Handler for server transcription session events.

This module contains the handler for processing transcription session-related events 
received from the OpenAI Realtime API.
"""

from typing import Any, Dict

from opusagent.realtime.handlers.server.base_handler import BaseServerHandler

class TranscriptionSessionHandler(BaseServerHandler):
    """Handler for server transcription session events.
    
    This handler processes transcription session-related events from the OpenAI Realtime API server,
    such as session updates.
    """
    
    async def handle_updated(self, event_data: Dict[str, Any]) -> None:
        """Handle a transcription_session.updated event.
        
        Args:
            event_data: The transcription session updated event data
        """
        session = event_data.get("session", {})
        session_id = session.get("id")
        
        # Extract key settings
        input_audio_format = session.get("input_audio_format")
        input_audio_transcription = session.get("input_audio_transcription", {})
        turn_detection = session.get("turn_detection", {})
        noise_reduction = session.get("input_audio_noise_reduction", {})
        
        self.logger.info(f"Transcription session updated: {session_id}")
        
        # Log details of the transcription configuration
        if input_audio_transcription:
            model = input_audio_transcription.get("model")
            prompt = input_audio_transcription.get("prompt")
            language = input_audio_transcription.get("language")
            self.logger.debug(
                f"Transcription config: model={model}, format={input_audio_format}, "
                f"language={language}, prompt={prompt[:50] + '...' if prompt and len(prompt) > 50 else prompt}"
            )
            
        # Log turn detection details if present
        if turn_detection:
            turn_type = turn_detection.get("type")
            threshold = turn_detection.get("threshold")
            padding = turn_detection.get("prefix_padding_ms")
            silence = turn_detection.get("silence_duration_ms")
            create_response = turn_detection.get("create_response")
            
            self.logger.debug(
                f"Turn detection: type={turn_type}, threshold={threshold}, "
                f"padding={padding}ms, silence={silence}ms, create_response={create_response}"
            )
            
        # Log noise reduction details if present
        if noise_reduction:
            noise_type = noise_reduction.get("type")
            self.logger.debug(f"Noise reduction: type={noise_type}")
            
        self.logger.debug(f"Full session details: {session}")
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for transcription_session.updated: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}") 