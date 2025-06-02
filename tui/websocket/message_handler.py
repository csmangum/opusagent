class MessageHandler:
    """Handles WebSocket message processing and routing."""

    def handle_telephony_message(self, message: dict) -> None:
        pass

    def handle_session_event(self, event_type: str, data: dict) -> None:
        pass

    def handle_audio_event(self, event_type: str, data: dict) -> None:
        pass

    def handle_error_event(self, error: dict) -> None:
        pass 