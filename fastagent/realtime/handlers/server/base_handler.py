"""
Base handler for processing server events.

This module defines a base class for all server event handlers to inherit from,
providing common functionality and interface requirements.
"""

import logging
from typing import Any, Callable, Dict, Optional

from fastagent.config.constants import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


class BaseServerHandler:
    """Base class for all server event handlers.
    
    This class provides common functionality for handling server events 
    and defines the interface that all server handlers must implement.
    
    Attributes:
        callback: Optional callback function to be called when events are processed
        logger: Logger instance for this handler
    """
    
    def __init__(self, callback: Optional[Callable] = None):
        """Initialize the handler.
        
        Args:
            callback: Optional callback function to be called when events are processed
        """
        self.callback = callback
        self.logger = logging.getLogger(f"{LOGGER_NAME}.handlers.server")
    
    async def handle_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Process a server event.
        
        This method dispatches the event to the appropriate handler method
        based on the event type.
        
        Args:
            event_type: The type of the event
            event_data: The event data
            
        Raises:
            NotImplementedError: If the handler method is not implemented
        """
        # Extract the specific event name from the event type
        # For example, "session.created" -> "created"
        event_name = event_type.split(".")[-1]
        
        # Construct the handler method name
        handler_method_name = f"handle_{event_name}"
        
        # Check if the handler method exists
        if not hasattr(self, handler_method_name):
            self.logger.warning(f"No handler method found for event type: {event_type}")
            return
        
        # Get the handler method
        handler_method = getattr(self, handler_method_name)
        
        # Call the handler method
        try:
            await handler_method(event_data)
        except Exception as e:
            self.logger.error(f"Error processing event {event_type}: {str(e)}")
            import traceback
            self.logger.debug(f"Error details: {traceback.format_exc()}") 