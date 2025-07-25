"""
Shared WebSocket utilities for the OpusAgent project.

This module contains common WebSocket operations that can be used
across different parts of the codebase to avoid duplication.
"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class WebSocketUtils:
    """Shared WebSocket utility functions."""

    @staticmethod
    async def safe_send_event(
        websocket: Any,
        event: Dict[str, Any],
        logger_instance: Optional[logging.Logger] = None,
    ) -> bool:
        """
        Safely send an event to a WebSocket connection.

        Args:
            websocket: WebSocket connection
            event (Dict[str, Any]): Event to send
            logger_instance (Optional[logging.Logger]): Logger for error reporting

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not websocket or WebSocketUtils.is_websocket_closed(websocket):
            if logger_instance:
                logger_instance.warning(
                    "Attempted to send on closed WebSocket; event not sent."
                )
            return False

        try:
            await websocket.send(json.dumps(event))
            if logger_instance:
                logger_instance.debug(f"Sent event: {event.get('type', 'unknown')}")
            return True
        except Exception as e:
            if logger_instance:
                logger_instance.error(f"Error sending event: {e}")
            return False

    @staticmethod
    async def safe_send_message(
        websocket: Any,
        message: Dict[str, Any],
        logger_instance: Optional[logging.Logger] = None,
    ) -> bool:
        """
        Safely send a message to a WebSocket connection.

        Args:
            websocket: WebSocket connection
            message (Dict[str, Any]): Message to send
            logger_instance (Optional[logging.Logger]): Logger for error reporting

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not websocket or WebSocketUtils.is_websocket_closed(websocket):
            if logger_instance:
                logger_instance.warning(
                    "Attempted to send on closed WebSocket; message not sent."
                )
            return False

        try:
            message_str = json.dumps(message)
            await websocket.send(message_str)
            if logger_instance:
                logger_instance.debug(f"Sent message: {message.get('type', 'unknown')}")
            return True
        except Exception as e:
            if logger_instance:
                logger_instance.error(f"Error sending message: {e}")
            return False

    @staticmethod
    def is_websocket_closed(websocket: Any) -> bool:
        """
        Check if a WebSocket connection is closed.

        Args:
            websocket: WebSocket connection to check

        Returns:
            bool: True if closed, False otherwise
        """
        if not websocket:
            return True

        try:
            # Check if websocket has a close_code attribute
            if hasattr(websocket, "close_code"):
                return websocket.close_code is not None

            # Check if websocket has a closed attribute
            if hasattr(websocket, "closed"):
                return websocket.closed

            # Check if websocket has a state attribute
            if hasattr(websocket, "state"):
                return websocket.state.name in ["CLOSED", "CLOSING"]

            return False
        except Exception:
            return True

    @staticmethod
    def format_event_log(event_type: str, data: Dict[str, Any]) -> str:
        """
        Format an event for logging.

        Args:
            event_type (str): Type of event
            data (Dict[str, Any]): Event data

        Returns:
            str: Formatted log message
        """
        # Truncate large data for logging
        if len(str(data)) > 200:
            data_str = str(data)[:200] + "..."
        else:
            data_str = str(data)

        return f"Event[{event_type}]: {data_str}"
