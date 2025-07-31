"""
Centralized error handling system with callback support and categorization.

This module provides a comprehensive error handling framework designed for
real-time audio processing applications. It offers:

Key Features:
- Error categorization by context (websocket, audio, session, API, etc.)
- Severity-based error handling with automatic logging
- Callback-based error handlers for custom processing
- Global and context-specific error handlers
- Error statistics and monitoring capabilities
- Async/sync handler support with proper error isolation

Components:
- ErrorContext: Enum for categorizing errors by domain
- ErrorSeverity: Enum for error severity levels (low, medium, high, critical)
- ErrorInfo: Dataclass containing complete error context
- ErrorHandler: Main error handling class with callback registration
- Global convenience functions for easy access

Usage:
    # Register a custom error handler
    async def my_error_handler(error_info: ErrorInfo):
        # Custom error processing logic
        pass

    register_error_handler(my_error_handler, ErrorContext.AUDIO)

    # Handle errors
    await handle_error(
        exception,
        context=ErrorContext.AUDIO,
        severity=ErrorSeverity.HIGH,
        operation="audio_processing"
    )

This system reduces boilerplate try-except blocks while providing
structured error handling suitable for production audio applications.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ErrorContext(Enum):
    """Error context types for categorizing errors."""

    WEBSOCKET = "websocket"
    AUDIO = "audio"
    SESSION = "session"
    API = "api"
    NETWORK = "network"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    """Simple error information structure."""

    error: Exception
    context: ErrorContext
    severity: ErrorSeverity
    operation: str
    metadata: Dict[str, Any]
    timestamp: datetime


class ErrorHandler:
    """
    Simplified error handling system with callback support.

    Provides centralized error handling to reduce try-except boilerplate
    while maintaining error categorization and custom handler support.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the error handler."""
        self.logger = logger or logging.getLogger(__name__)
        self._handlers: Dict[ErrorContext, List[Callable]] = {
            context: [] for context in ErrorContext
        }
        self._global_handlers: List[Callable] = []
        self._error_count: Dict[ErrorContext, int] = {
            context: 0 for context in ErrorContext
        }

    def register_handler(
        self,
        handler: Callable[[ErrorInfo], Any],
        context: Optional[ErrorContext] = None,
    ) -> None:
        """
        Register an error handler for a specific context or globally.

        Args:
            handler: Error handler function that takes ErrorInfo as parameter
            context: Error context to handle (None for global handlers)
        """
        if context is None:
            self._global_handlers.append(handler)
            self.logger.debug("Registered global error handler")
        else:
            self._handlers[context].append(handler)
            self.logger.debug(f"Registered error handler for {context.value}")

    def unregister_handler(
        self, handler: Callable, context: Optional[ErrorContext] = None
    ) -> bool:
        """
        Unregister an error handler.

        Args:
            handler: Handler function to remove
            context: Error context (None for global handlers)

        Returns:
            bool: True if handler was found and removed
        """
        target_list = (
            self._global_handlers if context is None else self._handlers[context]
        )

        if handler in target_list:
            target_list.remove(handler)
            self.logger.debug(
                f"Unregistered error handler for {context.value if context else 'global'}"
            )
            return True
        return False

    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext = ErrorContext.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        operation: str = "unknown",
        **metadata,
    ) -> None:
        """
        Handle an error using registered callbacks.

        Args:
            error: The exception that occurred
            context: Error context for categorization
            severity: Error severity level
            operation: Name of the operation that failed
            **metadata: Additional context-specific metadata
        """
        error_info = ErrorInfo(
            error=error,
            context=context,
            severity=severity,
            operation=operation,
            metadata=metadata,
            timestamp=datetime.now(),
        )

        # Update error statistics
        self._error_count[context] += 1

        # Log the error
        log_level = {
            ErrorSeverity.LOW: logging.DEBUG,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }[severity]

        self.logger.log(log_level, f"Error in {context.value} ({operation}): {error}")

        # Execute context-specific handlers
        await self._execute_handlers(self._handlers[context], error_info)

        # Execute global handlers
        await self._execute_handlers(self._global_handlers, error_info)

    async def _execute_handlers(
        self, handlers: List[Callable], error_info: ErrorInfo
    ) -> None:
        """Execute error handlers with proper error isolation."""
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(error_info)
                else:
                    handler(error_info)
            except Exception as handler_error:
                self.logger.error(f"Error in error handler: {handler_error}")

    def get_error_stats(self) -> Dict[str, Any]:
        """Get simple error statistics."""
        return {
            "error_counts": {
                ctx.value: count for ctx, count in self._error_count.items()
            },
            "total_errors": sum(self._error_count.values()),
            "registered_handlers": {
                ctx.value: len(handlers) for ctx, handlers in self._handlers.items()
            },
            "global_handlers": len(self._global_handlers),
        }

    def reset_stats(self) -> None:
        """Reset error statistics."""
        self._error_count = {context: 0 for context in ErrorContext}


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def register_error_handler(
    handler: Callable[[ErrorInfo], Any], context: Optional[ErrorContext] = None
) -> None:
    """Register an error handler on the global error handler."""
    get_error_handler().register_handler(handler, context)


async def handle_error(
    error: Exception,
    context: ErrorContext = ErrorContext.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    operation: str = "unknown",
    **metadata,
) -> None:
    """Handle an error using the global error handler."""
    await get_error_handler().handle_error(
        error, context, severity, operation, **metadata
    )
