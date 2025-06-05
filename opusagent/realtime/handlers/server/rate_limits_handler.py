"""
Handler for server rate limits events.

This module contains the handler for processing rate limits-related events 
received from the OpenAI Realtime API.
"""

from typing import Any, Dict, List

from opusagent.realtime.handlers.server.base_handler import BaseServerHandler

class RateLimitsHandler(BaseServerHandler):
    """Handler for server rate limits events.
    
    This handler processes rate limits-related events from the OpenAI Realtime API server.
    """
    
    async def handle_updated(self, event_data: Dict[str, Any]) -> None:
        """Handle a rate_limits.updated event.
        
        Args:
            event_data: The rate limits updated event data
        """
        rate_limits = event_data.get("rate_limits", [])
        
        # Format the rate limits for logging
        limits_info = []
        for limit in rate_limits:
            name = limit.get("name")
            limit_value = limit.get("limit")
            remaining = limit.get("remaining")
            reset_seconds = limit.get("reset_seconds")
            
            # Calculate percentage remaining
            percent = round((remaining / limit_value) * 100) if limit_value else 0
            
            limits_info.append(
                f"{name}: {remaining}/{limit_value} ({percent}%) remaining, resets in {reset_seconds}s"
            )
        
        # Log the rate limits
        if limits_info:
            self.logger.info("Rate limits updated:")
            for info in limits_info:
                self.logger.info(f"  - {info}")
        
        # Check for low remaining limits and log warnings
        self._check_for_low_limits(rate_limits)
        
        # Call the callback if provided
        if self.callback:
            try:
                await self.callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in callback for rate_limits.updated: {str(e)}")
                import traceback
                self.logger.debug(f"Callback error details: {traceback.format_exc()}")
    
    def _check_for_low_limits(self, rate_limits: List[Dict[str, Any]]) -> None:
        """Check for low rate limits and log warnings.
        
        Args:
            rate_limits: List of rate limit objects
        """
        for limit in rate_limits:
            name = limit.get("name")
            limit_value = limit.get("limit", 0)
            remaining = limit.get("remaining", 0)
            reset_seconds = limit.get("reset_seconds", 0)
            
            # Calculate percentage remaining
            percent = (remaining / limit_value) * 100 if limit_value else 0
            
            # Issue warnings if limits are getting low
            if percent <= 10:
                self.logger.warning(
                    f"Rate limit '{name}' is very low: {remaining}/{limit_value} "
                    f"({percent:.1f}%) remaining, resets in {reset_seconds}s"
                )
            elif percent <= 25:
                self.logger.info(
                    f"Rate limit '{name}' is getting low: {remaining}/{limit_value} "
                    f"({percent:.1f}%) remaining, resets in {reset_seconds}s"
                ) 