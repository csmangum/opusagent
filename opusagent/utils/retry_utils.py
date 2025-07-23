"""
Shared retry utilities for the OpusAgent project.

This module contains common retry logic that can be used
across different parts of the codebase to avoid duplication.
"""

import asyncio
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class RetryUtils:
    """Shared retry utility functions."""

    @staticmethod
    async def retry_operation(
        operation: Callable, 
        max_retries: int = 3, 
        delay: float = 1.0, 
        logger_instance: Optional[logging.Logger] = None,
        operation_name: str = "operation"
    ) -> Any:
        """
        Retry an async operation with exponential backoff.
        
        Args:
            operation: Async function to retry
            max_retries (int): Maximum number of retries
            delay (float): Initial delay between retries
            logger_instance (Optional[logging.Logger]): Logger for retry messages
            operation_name (str): Name of the operation for logging
        
        Returns:
            Result of the operation
        
        Raises:
            Exception: If all retries fail
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await operation()
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    if logger_instance:
                        logger_instance.warning(f"{operation_name} failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                else:
                    if logger_instance:
                        logger_instance.error(f"{operation_name} failed after {max_retries + 1} attempts: {e}")
        
        if last_exception:
            raise last_exception
        else:
            raise Exception(f"{operation_name} failed but no exception was captured")

    @staticmethod
    async def retry_with_backoff(
        operation: Callable,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        logger_instance: Optional[logging.Logger] = None,
        operation_name: str = "operation"
    ) -> Any:
        """
        Retry an async operation with configurable exponential backoff.
        
        Args:
            operation: Async function to retry
            max_attempts (int): Maximum number of attempts
            base_delay (float): Initial delay between retries
            max_delay (float): Maximum delay between retries
            backoff_factor (float): Factor to multiply delay by on each retry
            logger_instance (Optional[logging.Logger]): Logger for retry messages
            operation_name (str): Name of the operation for logging
        
        Returns:
            Result of the operation
        
        Raises:
            Exception: If all attempts fail
        """
        last_exception = None
        delay = base_delay
        
        for attempt in range(max_attempts):
            try:
                return await operation()
            except Exception as e:
                last_exception = e
                if attempt < max_attempts - 1:  # Don't sleep after last attempt
                    if logger_instance:
                        logger_instance.warning(f"{operation_name} failed (attempt {attempt + 1}/{max_attempts}): {e}")
                    
                    # Sleep with exponential backoff
                    await asyncio.sleep(min(delay, max_delay))
                    delay = min(delay * backoff_factor, max_delay)
                else:
                    if logger_instance:
                        logger_instance.error(f"{operation_name} failed after {max_attempts} attempts: {e}")
        
        if last_exception:
            raise last_exception
        else:
            raise Exception(f"{operation_name} failed but no exception was captured")

    @staticmethod
    def calculate_backoff_delay(
        attempt: int, 
        base_delay: float = 1.0, 
        max_delay: float = 60.0, 
        backoff_factor: float = 2.0
    ) -> float:
        """
        Calculate delay for exponential backoff.
        
        Args:
            attempt (int): Current attempt number (0-based)
            base_delay (float): Initial delay
            max_delay (float): Maximum delay
            backoff_factor (float): Factor to multiply delay by
        
        Returns:
            float: Delay in seconds
        """
        delay = base_delay * (backoff_factor ** attempt)
        return min(delay, max_delay) 