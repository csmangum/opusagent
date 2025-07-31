"""
Simple polling utilities for basic monitoring needs.

This module provides lightweight polling utilities for the few cases
that need periodic checking without the complexity of a full polling system.
"""

import asyncio
import logging
from typing import Callable, Optional


async def simple_poll(
    check_function: Callable,
    interval: float,
    condition: Optional[Callable[[], bool]] = None,
    max_errors: int = 3,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Simple polling loop for periodic checks.
    
    Args:
        check_function: Function to call periodically (sync or async)
        interval: Polling interval in seconds
        condition: Optional condition function that must return True to continue
        max_errors: Maximum consecutive errors before stopping
        logger: Optional logger for error reporting
    
    Example:
        def check_connection():
            return websocket.is_connected()
        
        # Start polling in background
        task = asyncio.create_task(simple_poll(
            check_function=check_connection,
            interval=30.0,
            condition=lambda: app.is_running
        ))
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    error_count = 0
    
    while True:
        try:
            # Check condition if provided
            if condition and not condition():
                await asyncio.sleep(interval)
                continue
            
            # Execute check function
            if asyncio.iscoroutinefunction(check_function):
                await check_function()
            else:
                check_function()
            
            # Reset error count on success
            error_count = 0
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            error_count += 1
            logger.error(f"Error in polling function (attempt {error_count}/{max_errors}): {e}")
            
            if error_count >= max_errors:
                logger.error("Too many consecutive errors, stopping polling")
                break
        
        await asyncio.sleep(interval)


def start_simple_poll(
    check_function: Callable,
    interval: float,
    condition: Optional[Callable[[], bool]] = None,
    max_errors: int = 3,
    logger: Optional[logging.Logger] = None
) -> asyncio.Task:
    """
    Start a simple polling task in the background.
    
    Args:
        check_function: Function to call periodically
        interval: Polling interval in seconds
        condition: Optional condition function
        max_errors: Maximum consecutive errors before stopping
        logger: Optional logger for error reporting
        
    Returns:
        asyncio.Task: The polling task (can be cancelled)
    
    Example:
        # Start background polling
        poll_task = start_simple_poll(
            check_function=lambda: print("Health check"),
            interval=60.0
        )
        
        # Later, stop polling
        poll_task.cancel()
    """
    return asyncio.create_task(simple_poll(
        check_function, interval, condition, max_errors, logger
    ))