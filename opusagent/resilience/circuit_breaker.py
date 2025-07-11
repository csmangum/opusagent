"""
Circuit breaker pattern implementation for external service calls.

This module provides a circuit breaker implementation to prevent cascading
failures and improve system resilience when calling external services.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional, Type, Union

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"         # Failing, reject requests
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls.
    
    The circuit breaker prevents cascading failures by monitoring the success
    rate of external service calls and temporarily stopping calls when the
    failure rate exceeds a threshold.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Union[Type[Exception], tuple] = Exception,
        name: str = "circuit_breaker",
        monitor_callback: Optional[Callable] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery (seconds)
            expected_exception: Exception types that count as failures
            name: Name for logging and monitoring
            monitor_callback: Optional callback for state changes
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        self.monitor_callback = monitor_callback
        
        # State
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        
        # Statistics
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.circuit_open_count = 0
        self.circuit_close_count = 0
        
        # Performance tracking
        self.request_times = []
        self.max_request_times = 100  # Keep last 100 request times
        
    async def call(
        self, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: Circuit breaker is open or function failed
        """
        start_time = time.time()
        self.total_requests += 1
        
        # Check circuit state
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise self._create_circuit_open_exception()
        
        # Execute function
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            self._on_success(start_time)
            return result
            
        except self.expected_exception as e:
            self._on_failure(start_time, e)
            raise e
        except Exception as e:
            # Unexpected exception - log but don't count as circuit breaker failure
            logger.warning(f"Unexpected exception in {self.name}: {e}")
            self._record_request_time(time.time() - start_time)
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        time_since_failure = time.time() - self.last_failure_time
        should_reset = time_since_failure >= self.recovery_timeout
        if should_reset:
            logger.debug(f"{self.name}: Recovery timeout reached ({time_since_failure:.1f}s >= {self.recovery_timeout}s)")
        return should_reset
    
    def _transition_to_half_open(self) -> None:
        """Transition circuit to half-open state."""
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        logger.info(f"{self.name}: Circuit transitioning from {old_state.value} to {self.state.value}")
        self._notify_state_change(old_state, self.state)
    
    def _on_success(self, start_time: float) -> None:
        """Handle successful function execution."""
        self.success_count += 1
        self.total_successes += 1
        self.last_success_time = time.time()
        self._record_request_time(time.time() - start_time)
        
        if self.state == CircuitState.HALF_OPEN:
            # Success in half-open state - close circuit
            self._close_circuit()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
        
        logger.debug(f"{self.name}: Success (state: {self.state.value}, failures: {self.failure_count})")
    
    def _on_failure(self, start_time: float, exception: Exception) -> None:
        """Handle failed function execution."""
        self.failure_count += 1
        self.total_failures += 1
        self.last_failure_time = time.time()
        self._record_request_time(time.time() - start_time)
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._open_circuit()
        elif self.state == CircuitState.HALF_OPEN:
            # Failure in half-open state - open circuit again
            self._open_circuit()
        
        logger.warning(
            f"{self.name}: Failure {self.failure_count}/{self.failure_threshold} "
            f"(state: {self.state.value}): {exception}"
        )
    
    def _open_circuit(self) -> None:
        """Open the circuit breaker."""
        old_state = self.state
        self.state = CircuitState.OPEN
        self.circuit_open_count += 1
        logger.error(f"{self.name}: Circuit opened after {self.failure_count} failures")
        self._notify_state_change(old_state, self.state)
    
    def _close_circuit(self) -> None:
        """Close the circuit breaker."""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.circuit_close_count += 1
        logger.info(f"{self.name}: Circuit closed after successful recovery")
        self._notify_state_change(old_state, self.state)
    
    def _create_circuit_open_exception(self) -> Exception:
        """Create exception for circuit open state."""
        if self.last_failure_time is None:
            wait_time = self.recovery_timeout
        else:
            wait_time = self.recovery_timeout - (time.time() - self.last_failure_time)
        return Exception(
            f"Circuit breaker '{self.name}' is OPEN. "
            f"Last failure: {self.last_failure_time}, "
            f"Recovery in: {max(0, wait_time):.1f}s"
        )
    
    def _record_request_time(self, duration: float) -> None:
        """Record request duration for performance monitoring."""
        self.request_times.append(duration)
        if len(self.request_times) > self.max_request_times:
            self.request_times.pop(0)
    
    def _notify_state_change(self, old_state: CircuitState, new_state: CircuitState) -> None:
        """Notify monitoring callback of state change."""
        if self.monitor_callback:
            try:
                self.monitor_callback(self.name, old_state, new_state)
            except Exception as e:
                logger.error(f"Error in circuit breaker monitor callback: {e}")
    
    def get_statistics(self) -> dict:
        """
        Get circuit breaker statistics.
        
        Returns:
            Dictionary with circuit breaker statistics
        """
        if self.total_requests == 0:
            return {
                'name': self.name,
                'state': self.state.value,
                'total_requests': 0,
                'success_rate': 0.0,
                'failure_rate': 0.0,
                'average_response_time': 0.0,
                'circuit_opens': 0,
                'circuit_closes': 0
            }
        
        return {
            'name': self.name,
            'state': self.state.value,
            'total_requests': self.total_requests,
            'total_successes': self.total_successes,
            'total_failures': self.total_failures,
            'success_rate': self.total_successes / self.total_requests,
            'failure_rate': self.total_failures / self.total_requests,
            'current_failure_count': self.failure_count,
            'average_response_time': sum(self.request_times) / len(self.request_times) if self.request_times else 0.0,
            'circuit_opens': self.circuit_open_count,
            'circuit_closes': self.circuit_close_count,
            'last_failure_time': self.last_failure_time,
            'last_success_time': self.last_success_time,
            'recovery_timeout': self.recovery_timeout
        }
    
    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        logger.info(f"{self.name}: Circuit manually reset")
        self._notify_state_change(old_state, self.state)
    
    def force_open(self) -> None:
        """Force circuit breaker to open state."""
        if self.state != CircuitState.OPEN:
            self._open_circuit()
    
    def force_close(self) -> None:
        """Force circuit breaker to closed state."""
        if self.state != CircuitState.CLOSED:
            self._close_circuit()


class CircuitBreakerManager:
    """Manager for multiple circuit breakers."""
    
    def __init__(self):
        self.circuit_breakers = {}
    
    def get_circuit_breaker(
        self, 
        name: str, 
        **kwargs
    ) -> CircuitBreaker:
        """
        Get or create a circuit breaker by name.
        
        Args:
            name: Circuit breaker name
            **kwargs: Circuit breaker configuration
            
        Returns:
            CircuitBreaker instance
        """
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name=name, **kwargs)
        return self.circuit_breakers[name]
    
    def get_all_statistics(self) -> dict:
        """Get statistics for all circuit breakers."""
        return {
            name: cb.get_statistics() 
            for name, cb in self.circuit_breakers.items()
        }
    
    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for cb in self.circuit_breakers.values():
            cb.reset()
    
    def force_open_all(self) -> None:
        """Force all circuit breakers to open state."""
        for cb in self.circuit_breakers.values():
            cb.force_open()
    
    def force_close_all(self) -> None:
        """Force all circuit breakers to closed state."""
        for cb in self.circuit_breakers.values():
            cb.force_close() 