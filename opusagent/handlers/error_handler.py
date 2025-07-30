"""
Centralized error handling system with callback support.

This module provides a comprehensive error handling system that supports
registering multiple error handlers for different error types and contexts.
It reduces code duplication and provides consistent error handling across
the OpusAgent codebase.
"""

import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass
from datetime import datetime


class ErrorSeverity(Enum):
    """Error severity levels for prioritizing error handling."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorContext(Enum):
    """Error context types for categorizing errors."""
    WEBSOCKET = "websocket"
    AUDIO = "audio"
    SESSION = "session"
    API = "api"
    VALIDATION = "validation"
    SYSTEM = "system"
    NETWORK = "network"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Structured error information for context-aware handling."""
    error: Exception
    context: ErrorContext
    severity: ErrorSeverity
    operation: str
    metadata: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error info to dictionary for logging/storage."""
        return {
            "error_type": type(self.error).__name__,
            "error_message": str(self.error),
            "context": self.context.value,
            "severity": self.severity.value,
            "operation": self.operation,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "traceback": traceback.format_exception(type(self.error), self.error, self.error.__traceback__)
        }


class ErrorHandler:
    """
    Centralized error handling system with callback support.
    
    This class provides a comprehensive error handling system that supports:
    - Multiple error handlers for different error types and contexts
    - Priority-based handler execution
    - Async and sync callback support
    - Context-aware error processing
    - Automatic logging and metrics collection
    - Error recovery strategies
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the error handler."""
        self.logger = logger or logging.getLogger(__name__)
        self._handlers: Dict[ErrorContext, List[Callable]] = {context: [] for context in ErrorContext}
        self._global_handlers: List[Callable] = []
        self._error_count: Dict[ErrorContext, int] = {context: 0 for context in ErrorContext}
        self._last_errors: Dict[ErrorContext, ErrorInfo] = {}
        
    def register_handler(
        self, 
        handler: Callable[[ErrorInfo], Any],
        context: Optional[ErrorContext] = None,
        priority: int = 0
    ) -> None:
        """
        Register an error handler for a specific context or globally.
        
        Args:
            handler: Error handler function that takes ErrorInfo as parameter
            context: Error context to handle (None for global handlers)
            priority: Handler priority (higher numbers execute first)
        """
        handler_wrapper = (priority, handler)
        
        if context is None:
            self._global_handlers.append(handler_wrapper)
            self._global_handlers.sort(key=lambda x: x[0], reverse=True)
            self.logger.debug(f"Registered global error handler with priority {priority}")
        else:
            self._handlers[context].append(handler_wrapper)
            self._handlers[context].sort(key=lambda x: x[0], reverse=True)
            self.logger.debug(f"Registered error handler for {context.value} with priority {priority}")
    
    def unregister_handler(
        self, 
        handler: Callable,
        context: Optional[ErrorContext] = None
    ) -> bool:
        """
        Unregister an error handler.
        
        Args:
            handler: Handler function to remove
            context: Error context (None for global handlers)
            
        Returns:
            bool: True if handler was found and removed
        """
        target_list = self._global_handlers if context is None else self._handlers[context]
        
        for i, (priority, h) in enumerate(target_list):
            if h == handler:
                target_list.pop(i)
                self.logger.debug(f"Unregistered error handler for {context.value if context else 'global'}")
                return True
        return False
    
    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext = ErrorContext.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        operation: str = "unknown",
        **metadata
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
            timestamp=datetime.now()
        )
        
        # Update error statistics
        self._error_count[context] += 1
        self._last_errors[context] = error_info
        
        # Log the error
        log_level = {
            ErrorSeverity.LOW: logging.DEBUG,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }[severity]
        
        self.logger.log(
            log_level,
            f"Error in {context.value} ({operation}): {error}",
            extra={"error_info": error_info.to_dict()}
        )
        
        # Execute context-specific handlers
        await self._execute_handlers(self._handlers[context], error_info)
        
        # Execute global handlers
        await self._execute_handlers(self._global_handlers, error_info)
    
    async def _execute_handlers(self, handlers: List[tuple], error_info: ErrorInfo) -> None:
        """Execute error handlers with proper error isolation."""
        for priority, handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(error_info)
                else:
                    handler(error_info)
            except Exception as handler_error:
                self.logger.error(
                    f"Error in error handler: {handler_error}",
                    exc_info=True
                )
    
    @asynccontextmanager
    async def error_context(
        self,
        context: ErrorContext,
        operation: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        **metadata
    ):
        """
        Context manager for automatic error handling.
        
        Usage:
            async with error_handler.error_context(ErrorContext.WEBSOCKET, "connect"):
                # WebSocket connection code
                pass
        """
        try:
            yield
        except Exception as e:
            await self.handle_error(
                error=e,
                context=context,
                severity=severity,
                operation=operation,
                **metadata
            )
            raise
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for monitoring and debugging."""
        return {
            "error_counts": {ctx.value: count for ctx, count in self._error_count.items()},
            "total_errors": sum(self._error_count.values()),
            "last_errors": {
                ctx.value: info.to_dict() if info else None 
                for ctx, info in self._last_errors.items()
            },
            "registered_handlers": {
                ctx.value: len(handlers) for ctx, handlers in self._handlers.items()
            },
            "global_handlers": len(self._global_handlers)
        }
    
    def reset_stats(self) -> None:
        """Reset error statistics."""
        self._error_count = {context: 0 for context in ErrorContext}
        self._last_errors = {}


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def register_error_handler(
    handler: Callable[[ErrorInfo], Any],
    context: Optional[ErrorContext] = None,
    priority: int = 0
) -> None:
    """Register an error handler on the global error handler."""
    get_error_handler().register_handler(handler, context, priority)


async def handle_error(
    error: Exception,
    context: ErrorContext = ErrorContext.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    operation: str = "unknown",
    **metadata
) -> None:
    """Handle an error using the global error handler."""
    await get_error_handler().handle_error(error, context, severity, operation, **metadata)


# Convenience decorators for common error handling patterns
def error_context(
    context: ErrorContext,
    operation: str,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    **metadata
):
    """Decorator for automatic error handling."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                async with get_error_handler().error_context(context, operation, severity, **metadata):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    asyncio.create_task(
                        get_error_handler().handle_error(e, context, severity, operation, **metadata)
                    )
                    raise
            return sync_wrapper
    return decorator