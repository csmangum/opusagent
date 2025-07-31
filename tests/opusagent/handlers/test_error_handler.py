"""
Unit tests for the error handler module.

Tests the centralized error handling system including:
- ErrorContext and ErrorSeverity enums
- ErrorInfo dataclass
- ErrorHandler class functionality
- Global error handler functions
- Error statistics and monitoring
- Callback registration and execution
"""

import asyncio
import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from opusagent.handlers.error_handler import (
    ErrorContext,
    ErrorSeverity,
    ErrorInfo,
    ErrorHandler,
    get_error_handler,
    register_error_handler,
    handle_error,
)


class TestErrorContext:
    """Test ErrorContext enum functionality."""

    def test_error_context_values(self):
        """Test that ErrorContext has the expected values."""
        assert ErrorContext.WEBSOCKET.value == "websocket"
        assert ErrorContext.AUDIO.value == "audio"
        assert ErrorContext.SESSION.value == "session"
        assert ErrorContext.API.value == "api"
        assert ErrorContext.NETWORK.value == "network"
        assert ErrorContext.SYSTEM.value == "system"
        assert ErrorContext.UNKNOWN.value == "unknown"

    def test_error_context_enumeration(self):
        """Test that all ErrorContext values can be enumerated."""
        contexts = list(ErrorContext)
        assert len(contexts) == 7
        assert ErrorContext.WEBSOCKET in contexts
        assert ErrorContext.AUDIO in contexts
        assert ErrorContext.SESSION in contexts
        assert ErrorContext.API in contexts
        assert ErrorContext.NETWORK in contexts
        assert ErrorContext.SYSTEM in contexts
        assert ErrorContext.UNKNOWN in contexts


class TestErrorSeverity:
    """Test ErrorSeverity enum functionality."""

    def test_error_severity_values(self):
        """Test that ErrorSeverity has the expected values."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"

    def test_error_severity_enumeration(self):
        """Test that all ErrorSeverity values can be enumerated."""
        severities = list(ErrorSeverity)
        assert len(severities) == 4
        assert ErrorSeverity.LOW in severities
        assert ErrorSeverity.MEDIUM in severities
        assert ErrorSeverity.HIGH in severities
        assert ErrorSeverity.CRITICAL in severities


class TestErrorInfo:
    """Test ErrorInfo dataclass functionality."""

    def test_error_info_creation(self):
        """Test creating an ErrorInfo instance."""
        error = ValueError("Test error")
        error_info = ErrorInfo(
            error=error,
            context=ErrorContext.AUDIO,
            severity=ErrorSeverity.HIGH,
            operation="test_operation",
            metadata={"key": "value"},
            timestamp=datetime.now(),
        )
        
        assert error_info.error == error
        assert error_info.context == ErrorContext.AUDIO
        assert error_info.severity == ErrorSeverity.HIGH
        assert error_info.operation == "test_operation"
        assert error_info.metadata == {"key": "value"}

    def test_error_info_with_timestamp(self):
        """Test ErrorInfo with explicit timestamp."""
        from datetime import datetime
        
        timestamp = datetime.now()
        error_info = ErrorInfo(
            error=ValueError("Test"),
            context=ErrorContext.WEBSOCKET,
            severity=ErrorSeverity.MEDIUM,
            operation="test",
            metadata={},
            timestamp=timestamp,
        )
        
        assert error_info.timestamp == timestamp


class TestErrorHandler:
    """Test ErrorHandler class functionality."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        return MagicMock(spec=logging.Logger)

    @pytest.fixture
    def error_handler(self, mock_logger):
        """Create an ErrorHandler instance for testing."""
        return ErrorHandler(mock_logger)

    def test_error_handler_initialization(self, error_handler, mock_logger):
        """Test ErrorHandler initialization."""
        assert error_handler.logger == mock_logger
        assert len(error_handler._handlers) == len(ErrorContext)
        assert len(error_handler._global_handlers) == 0
        assert len(error_handler._error_count) == len(ErrorContext)
        
        # Check that all contexts are initialized
        for context in ErrorContext:
            assert context in error_handler._handlers
            assert context in error_handler._error_count
            assert error_handler._error_count[context] == 0

    def test_error_handler_initialization_default_logger(self):
        """Test ErrorHandler initialization with default logger."""
        handler = ErrorHandler()
        assert handler.logger is not None
        assert isinstance(handler.logger, logging.Logger)

    def test_register_handler_context_specific(self, error_handler, mock_logger):
        """Test registering a context-specific error handler."""
        def test_handler(error_info):
            pass

        error_handler.register_handler(test_handler, ErrorContext.AUDIO)
        
        assert test_handler in error_handler._handlers[ErrorContext.AUDIO]
        assert len(error_handler._handlers[ErrorContext.AUDIO]) == 1
        mock_logger.debug.assert_called_with("Registered error handler for audio")

    def test_register_handler_global(self, error_handler, mock_logger):
        """Test registering a global error handler."""
        def test_handler(error_info):
            pass

        error_handler.register_handler(test_handler)
        
        assert test_handler in error_handler._global_handlers
        assert len(error_handler._global_handlers) == 1
        mock_logger.debug.assert_called_with("Registered global error handler")

    def test_register_handler_multiple(self, error_handler):
        """Test registering multiple handlers for the same context."""
        def handler1(error_info):
            pass
        
        def handler2(error_info):
            pass

        error_handler.register_handler(handler1, ErrorContext.WEBSOCKET)
        error_handler.register_handler(handler2, ErrorContext.WEBSOCKET)
        
        assert len(error_handler._handlers[ErrorContext.WEBSOCKET]) == 2
        assert handler1 in error_handler._handlers[ErrorContext.WEBSOCKET]
        assert handler2 in error_handler._handlers[ErrorContext.WEBSOCKET]

    def test_unregister_handler_context_specific(self, error_handler):
        """Test unregistering a context-specific error handler."""
        def test_handler(error_info):
            pass

        error_handler.register_handler(test_handler, ErrorContext.API)
        result = error_handler.unregister_handler(test_handler, ErrorContext.API)
        
        assert result is True
        assert test_handler not in error_handler._handlers[ErrorContext.API]

    def test_unregister_handler_global(self, error_handler):
        """Test unregistering a global error handler."""
        def test_handler(error_info):
            pass

        error_handler.register_handler(test_handler)
        result = error_handler.unregister_handler(test_handler)
        
        assert result is True
        assert test_handler not in error_handler._global_handlers

    def test_unregister_handler_not_found(self, error_handler):
        """Test unregistering a handler that doesn't exist."""
        def test_handler(error_info):
            pass

        result = error_handler.unregister_handler(test_handler, ErrorContext.SESSION)
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_error_basic(self, error_handler, mock_logger):
        """Test basic error handling."""
        test_error = ValueError("Test error")
        
        await error_handler.handle_error(
            error=test_error,
            context=ErrorContext.AUDIO,
            severity=ErrorSeverity.HIGH,
            operation="test_operation",
            key="value"
        )
        
        # Check that error was logged
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.ERROR
        assert "Error in audio (test_operation): Test error" in call_args[0][1]
        
        # Check that error count was incremented
        assert error_handler._error_count[ErrorContext.AUDIO] == 1

    @pytest.mark.asyncio
    async def test_handle_error_defaults(self, error_handler, mock_logger):
        """Test error handling with default parameters."""
        test_error = RuntimeError("Test error")
        
        await error_handler.handle_error(test_error)
        
        # Check that error was logged with default context and severity
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.WARNING  # MEDIUM severity
        assert "Error in unknown (unknown): Test error" in call_args[0][1]
        
        # Check that error count was incremented for UNKNOWN context
        assert error_handler._error_count[ErrorContext.UNKNOWN] == 1

    @pytest.mark.asyncio
    async def test_handle_error_different_severities(self, error_handler, mock_logger):
        """Test error handling with different severity levels."""
        test_error = Exception("Test error")
        
        # Test LOW severity
        await error_handler.handle_error(
            test_error, 
            context=ErrorContext.SYSTEM, 
            severity=ErrorSeverity.LOW,
            operation="test"
        )
        mock_logger.log.assert_called_with(logging.DEBUG, "Error in system (test): Test error")
        
        # Test CRITICAL severity
        mock_logger.reset_mock()
        await error_handler.handle_error(
            test_error, 
            context=ErrorContext.API, 
            severity=ErrorSeverity.CRITICAL,
            operation="test"
        )
        mock_logger.log.assert_called_with(logging.CRITICAL, "Error in api (test): Test error")

    @pytest.mark.asyncio
    async def test_handle_error_with_metadata(self, error_handler, mock_logger):
        """Test error handling with additional metadata."""
        test_error = ConnectionError("Connection failed")
        
        await error_handler.handle_error(
            test_error,
            context=ErrorContext.NETWORK,
            severity=ErrorSeverity.HIGH,
            operation="connect",
            url="https://example.com",
            timeout=30
        )
        
        # Check that error was logged
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert "Error in network (connect): Connection failed" in call_args[0][1]
        
        # Check that error count was incremented
        assert error_handler._error_count[ErrorContext.NETWORK] == 1

    @pytest.mark.asyncio
    async def test_handle_error_with_context_handlers(self, error_handler, mock_logger):
        """Test error handling with registered context handlers."""
        handler_called = False
        handler_error_info = None
        
        def test_handler(error_info):
            nonlocal handler_called, handler_error_info
            handler_called = True
            handler_error_info = error_info
        
        error_handler.register_handler(test_handler, ErrorContext.WEBSOCKET)
        
        test_error = TimeoutError("Connection timeout")
        await error_handler.handle_error(
            test_error,
            context=ErrorContext.WEBSOCKET,
            severity=ErrorSeverity.HIGH,
            operation="connect"
        )
        
        assert handler_called
        assert handler_error_info is not None
        assert handler_error_info.error == test_error
        assert handler_error_info.context == ErrorContext.WEBSOCKET
        assert handler_error_info.severity == ErrorSeverity.HIGH
        assert handler_error_info.operation == "connect"

    @pytest.mark.asyncio
    async def test_handle_error_with_global_handlers(self, error_handler, mock_logger):
        """Test error handling with registered global handlers."""
        handler_called = False
        
        def test_handler(error_info):
            nonlocal handler_called
            handler_called = True
        
        error_handler.register_handler(test_handler)  # Global handler
        
        test_error = ValueError("Test error")
        await error_handler.handle_error(
            test_error,
            context=ErrorContext.API,
            severity=ErrorSeverity.MEDIUM,
            operation="test"
        )
        
        assert handler_called

    @pytest.mark.asyncio
    async def test_handle_error_handler_exception(self, error_handler, mock_logger):
        """Test error handling when a handler raises an exception."""
        def failing_handler(error_info):
            raise RuntimeError("Handler failed")
        
        error_handler.register_handler(failing_handler, ErrorContext.SESSION)
        
        test_error = ValueError("Original error")
        await error_handler.handle_error(
            test_error,
            context=ErrorContext.SESSION,
            severity=ErrorSeverity.MEDIUM,
            operation="test"
        )
        
        # Should log the handler error
        mock_logger.error.assert_called_with("Error in error handler: Handler failed")

    @pytest.mark.asyncio
    async def test_handle_error_async_handler(self, error_handler, mock_logger):
        """Test error handling with async handlers."""
        handler_called = False
        
        async def async_handler(error_info):
            nonlocal handler_called
            handler_called = True
        
        error_handler.register_handler(async_handler, ErrorContext.AUDIO)
        
        test_error = OSError("Audio error")
        await error_handler.handle_error(
            test_error,
            context=ErrorContext.AUDIO,
            severity=ErrorSeverity.HIGH,
            operation="audio_processing"
        )
        
        assert handler_called

    def test_get_error_stats(self, error_handler):
        """Test getting error statistics."""
        # Simulate some errors
        error_handler._error_count[ErrorContext.WEBSOCKET] = 5
        error_handler._error_count[ErrorContext.AUDIO] = 3
        error_handler._error_count[ErrorContext.API] = 1
        
        # Register some handlers
        def handler1(error_info):
            pass
        def handler2(error_info):
            pass
        
        error_handler.register_handler(handler1, ErrorContext.WEBSOCKET)
        error_handler.register_handler(handler2, ErrorContext.WEBSOCKET)
        error_handler.register_handler(handler1)  # Global handler
        
        stats = error_handler.get_error_stats()
        
        assert stats["error_counts"]["websocket"] == 5
        assert stats["error_counts"]["audio"] == 3
        assert stats["error_counts"]["api"] == 1
        assert stats["total_errors"] == 9
        assert stats["registered_handlers"]["websocket"] == 2
        assert stats["global_handlers"] == 1

    def test_reset_stats(self, error_handler):
        """Test resetting error statistics."""
        # Set some error counts
        error_handler._error_count[ErrorContext.WEBSOCKET] = 5
        error_handler._error_count[ErrorContext.AUDIO] = 3
        
        error_handler.reset_stats()
        
        # Check that all counts are reset to 0
        for context in ErrorContext:
            assert error_handler._error_count[context] == 0


class TestGlobalErrorHandler:
    """Test global error handler functions."""

    def test_get_error_handler_singleton(self):
        """Test that get_error_handler returns a singleton."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        
        assert handler1 is handler2
        assert isinstance(handler1, ErrorHandler)

    def test_register_error_handler_global(self):
        """Test registering an error handler globally."""
        def test_handler(error_info):
            pass
        
        register_error_handler(test_handler)
        
        handler = get_error_handler()
        assert test_handler in handler._global_handlers

    def test_register_error_handler_context_specific(self):
        """Test registering an error handler for a specific context."""
        def test_handler(error_info):
            pass
        
        register_error_handler(test_handler, ErrorContext.NETWORK)
        
        handler = get_error_handler()
        assert test_handler in handler._handlers[ErrorContext.NETWORK]

    @pytest.mark.asyncio
    async def test_handle_error_global_function(self):
        """Test the global handle_error function."""
        test_error = ValueError("Test error")
        
        await handle_error(
            test_error,
            context=ErrorContext.SESSION,
            severity=ErrorSeverity.HIGH,
            operation="test_operation"
        )
        
        # Verify the error was handled by checking the global handler's stats
        handler = get_error_handler()
        assert handler._error_count[ErrorContext.SESSION] == 1

    @pytest.mark.asyncio
    async def test_handle_error_global_function_defaults(self):
        """Test the global handle_error function with defaults."""
        test_error = RuntimeError("Test error")
        
        await handle_error(test_error)
        
        # Verify the error was handled with default context
        handler = get_error_handler()
        assert handler._error_count[ErrorContext.UNKNOWN] == 1


class TestErrorHandlerIntegration:
    """Integration tests for error handler functionality."""

    @pytest.mark.asyncio
    async def test_error_handler_integration_scenario(self):
        """Test a complete error handling scenario."""
        # Create a fresh error handler for this test
        test_handler = ErrorHandler()
        
        # Create a custom error handler that tracks calls
        websocket_errors = []
        audio_errors = []
        global_errors = []
        
        def websocket_handler(error_info):
            websocket_errors.append(error_info)
        
        def audio_handler(error_info):
            audio_errors.append(error_info)
        
        def global_handler(error_info):
            global_errors.append(error_info)
        
        # Register handlers on the test handler
        test_handler.register_handler(websocket_handler, ErrorContext.WEBSOCKET)
        test_handler.register_handler(audio_handler, ErrorContext.AUDIO)
        test_handler.register_handler(global_handler)
        
        # Simulate various errors using the test handler directly
        await test_handler.handle_error(
            ConnectionError("WebSocket connection failed"),
            context=ErrorContext.WEBSOCKET,
            severity=ErrorSeverity.HIGH,
            operation="websocket_connect"
        )
        
        await test_handler.handle_error(
            OSError("Audio device not found"),
            context=ErrorContext.AUDIO,
            severity=ErrorSeverity.MEDIUM,
            operation="audio_initialization"
        )
        
        await test_handler.handle_error(
            ValueError("Invalid parameter"),
            context=ErrorContext.API,
            severity=ErrorSeverity.LOW,
            operation="parameter_validation"
        )
        
        # Verify handlers were called correctly
        assert len(websocket_errors) == 1
        assert websocket_errors[0].context == ErrorContext.WEBSOCKET
        assert websocket_errors[0].operation == "websocket_connect"
        
        assert len(audio_errors) == 1
        assert audio_errors[0].context == ErrorContext.AUDIO
        assert audio_errors[0].operation == "audio_initialization"
        
        # Global handler should have been called for all errors
        assert len(global_errors) == 3
        
        # Check error statistics
        stats = test_handler.get_error_stats()
        assert stats["error_counts"]["websocket"] == 1
        assert stats["error_counts"]["audio"] == 1
        assert stats["error_counts"]["api"] == 1
        assert stats["total_errors"] == 3

    @pytest.mark.asyncio
    async def test_error_handler_with_metadata_integration(self):
        """Test error handler with rich metadata."""
        captured_metadata = []
        
        def metadata_handler(error_info):
            captured_metadata.append(error_info.metadata)
        
        register_error_handler(metadata_handler, ErrorContext.NETWORK)
        
        # Simulate network error with metadata
        await handle_error(
            TimeoutError("Request timeout"),
            context=ErrorContext.NETWORK,
            severity=ErrorSeverity.HIGH,
            operation="api_request",
            url="https://api.example.com",
            timeout=30,
            retry_count=3,
            user_id="user123"
        )
        
        assert len(captured_metadata) == 1
        metadata = captured_metadata[0]
        assert metadata["url"] == "https://api.example.com"
        assert metadata["timeout"] == 30
        assert metadata["retry_count"] == 3
        assert metadata["user_id"] == "user123" 