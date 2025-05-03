"""
Handler for session.get_config events.

The session.get_config event allows retrieving the current session configuration.
The server will respond with a session.config event containing the full session
configuration, including any default values that were not explicitly set.
"""

from typing import Any, Dict, Callable, Awaitable

class SessionGetConfigHandler:
    def __init__(
        self,
        session_config: Dict[str, Any],
        send_event_callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ):
        """
        Initialize the session get config handler.
        
        Args:
            session_config: The current session configuration dictionary
            send_event_callback: Callback function to send events back to the server
        """
        self.session_config = session_config
        self.send_event = send_event_callback
        
    async def handle(self, event: Dict[str, Any]) -> None:
        """
        Handle the session.get_config event.
        
        This sends back the current session configuration.
        
        Args:
            event: The session.get_config event data containing:
                - event_id: Optional client-generated ID for the event
                - type: Must be "session.get_config"
        """
        event_id = event.get("event_id")
        await self.send_event({
            "type": "session.config",
            "event_id": event_id,
            "session": self.session_config
        }) 