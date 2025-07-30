"""
Health monitoring system with callback support.

This module provides a comprehensive health monitoring system that supports
registering health check callbacks, aggregating results, and triggering
alerts based on health status changes. It enables proactive monitoring
of system components and automatic response to health issues.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from statistics import mean


class HealthStatus(Enum):
    """Health status enumeration."""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    WARNING = "warning"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    component: str
    status: HealthStatus
    message: str
    timestamp: datetime
    duration: float  # seconds
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "duration": self.duration,
            "metadata": self.metadata
        }


@dataclass
class HealthCheckConfig:
    """Configuration for a health check."""
    component: str
    check_function: Callable[[], Union[HealthCheckResult, Dict[str, Any], bool]]
    interval: float
    timeout: float = 30.0
    enabled: bool = True
    critical: bool = False  # Whether this check is critical for overall health
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Runtime state
    last_result: Optional[HealthCheckResult] = field(default=None, init=False)
    consecutive_failures: int = field(default=0, init=False)
    last_run: Optional[datetime] = field(default=None, init=False)
    task: Optional[asyncio.Task] = field(default=None, init=False, repr=False)


@dataclass
class HealthAlert:
    """Health alert information."""
    component: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    old_status: HealthStatus
    new_status: HealthStatus
    metadata: Dict[str, Any] = field(default_factory=dict)


class HealthMonitor:
    """
    Comprehensive health monitoring system with callback support.
    
    This class provides a health monitoring system that supports:
    - Multiple health checks with configurable intervals
    - Health status aggregation and trending
    - Alert generation on status changes
    - Callback system for health events
    - Debouncing to prevent alert spam
    - Historical health data tracking
    - Component dependency tracking
    """
    
    def __init__(
        self, 
        logger: Optional[logging.Logger] = None,
        alert_debounce_seconds: float = 60.0,
        history_retention_hours: int = 24
    ):
        """Initialize the health monitor."""
        self.logger = logger or logging.getLogger(__name__)
        self._health_checks: Dict[str, HealthCheckConfig] = {}
        self._alert_callbacks: List[Callable[[HealthAlert], Any]] = []
        self._status_callbacks: List[Callable[[str, HealthStatus, HealthStatus], Any]] = []
        self._health_history: Dict[str, List[HealthCheckResult]] = {}
        self._overall_status = HealthStatus.UNKNOWN
        self._alert_debounce_seconds = alert_debounce_seconds
        self._history_retention_hours = history_retention_hours
        self._last_alerts: Dict[str, datetime] = {}
        self._shutdown = False
        
        # Start background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def register_health_check(
        self,
        component: str,
        check_function: Callable,
        interval: float,
        timeout: float = 30.0,
        critical: bool = False,
        auto_start: bool = True,
        **metadata
    ) -> None:
        """
        Register a health check for a component.
        
        Args:
            component: Name of the component to monitor
            check_function: Function that performs the health check
            interval: Check interval in seconds
            timeout: Timeout for the check in seconds
            critical: Whether this check is critical for overall health
            auto_start: Whether to start monitoring immediately
            **metadata: Additional metadata for the health check
            
        Example:
            ```python
            def check_database():
                try:
                    # Check database connectivity
                    result = db.execute("SELECT 1")
                    return {
                        "status": "healthy",
                        "message": "Database is responsive",
                        "query_time": 0.05
                    }
                except Exception as e:
                    return {
                        "status": "unhealthy",
                        "message": f"Database error: {e}"
                    }
            
            health_monitor.register_health_check(
                component="database",
                check_function=check_database,
                interval=30.0,
                critical=True,
                service="postgresql"
            )
            ```
        """
        if component in self._health_checks:
            raise ValueError(f"Health check for component '{component}' already exists")
        
        config = HealthCheckConfig(
            component=component,
            check_function=check_function,
            interval=interval,
            timeout=timeout,
            critical=critical,
            metadata=metadata
        )
        
        self._health_checks[component] = config
        self._health_history[component] = []
        
        self.logger.info(
            f"Registered health check for '{component}' "
            f"(interval: {interval}s, critical: {critical})"
        )
        
        if auto_start:
            self.start_monitoring(component)
    
    def unregister_health_check(self, component: str) -> bool:
        """
        Unregister a health check.
        
        Args:
            component: Name of the component
            
        Returns:
            bool: True if check was found and removed
        """
        if component not in self._health_checks:
            return False
        
        self.stop_monitoring(component)
        del self._health_checks[component]
        del self._health_history[component]
        
        self.logger.info(f"Unregistered health check for '{component}'")
        return True
    
    def start_monitoring(self, component: Optional[str] = None) -> None:
        """
        Start health monitoring for a component or all components.
        
        Args:
            component: Component name, or None for all components
        """
        if component:
            if component in self._health_checks:
                config = self._health_checks[component]
                if config.task and not config.task.done():
                    config.task.cancel()
                
                config.task = asyncio.create_task(self._monitoring_loop(config))
                config.enabled = True
                self.logger.info(f"Started monitoring for '{component}'")
        else:
            for component_name in self._health_checks.keys():
                self.start_monitoring(component_name)
    
    def stop_monitoring(self, component: Optional[str] = None) -> None:
        """
        Stop health monitoring for a component or all components.
        
        Args:
            component: Component name, or None for all components
        """
        if component:
            if component in self._health_checks:
                config = self._health_checks[component]
                if config.task and not config.task.done():
                    config.task.cancel()
                
                config.enabled = False
                self.logger.info(f"Stopped monitoring for '{component}'")
        else:
            for component_name in self._health_checks.keys():
                self.stop_monitoring(component_name)
    
    def register_alert_callback(self, callback: Callable[[HealthAlert], Any]) -> None:
        """
        Register a callback for health alerts.
        
        Args:
            callback: Function to call when alerts are generated
        """
        self._alert_callbacks.append(callback)
        self.logger.debug("Registered health alert callback")
    
    def register_status_callback(
        self, 
        callback: Callable[[str, HealthStatus, HealthStatus], Any]
    ) -> None:
        """
        Register a callback for status changes.
        
        Args:
            callback: Function to call with (component, old_status, new_status)
        """
        self._status_callbacks.append(callback)
        self.logger.debug("Registered health status callback")
    
    async def _monitoring_loop(self, config: HealthCheckConfig) -> None:
        """Main monitoring loop for a health check."""
        while not self._shutdown and config.enabled:
            try:
                await self._perform_health_check(config)
                await asyncio.sleep(config.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop for '{config.component}': {e}")
                await asyncio.sleep(config.interval)
    
    async def _perform_health_check(self, config: HealthCheckConfig) -> None:
        """Perform a single health check."""
        start_time = time.time()
        
        try:
            # Execute health check with timeout
            if asyncio.iscoroutinefunction(config.check_function):
                raw_result = await asyncio.wait_for(
                    config.check_function(), 
                    timeout=config.timeout
                )
            else:
                raw_result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, config.check_function
                    ),
                    timeout=config.timeout
                )
            
            duration = time.time() - start_time
            result = self._normalize_health_result(config.component, raw_result, duration)
            
            # Reset consecutive failures on success
            if result.status in [HealthStatus.HEALTHY, HealthStatus.WARNING]:
                config.consecutive_failures = 0
            else:
                config.consecutive_failures += 1
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            result = HealthCheckResult(
                component=config.component,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {config.timeout}s",
                timestamp=datetime.now(),
                duration=duration
            )
            config.consecutive_failures += 1
            
        except Exception as e:
            duration = time.time() - start_time
            result = HealthCheckResult(
                component=config.component,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.now(),
                duration=duration
            )
            config.consecutive_failures += 1
        
        # Store result
        old_status = config.last_result.status if config.last_result else HealthStatus.UNKNOWN
        config.last_result = result
        config.last_run = result.timestamp
        
        # Add to history
        self._health_history[config.component].append(result)
        
        # Trigger callbacks if status changed
        if old_status != result.status:
            await self._handle_status_change(config.component, old_status, result.status)
        
        # Update overall health status
        self._update_overall_status()
        
        self.logger.debug(
            f"Health check for '{config.component}': {result.status.value} "
            f"({result.duration:.3f}s) - {result.message}"
        )
    
    def _normalize_health_result(
        self, 
        component: str, 
        raw_result: Any, 
        duration: float
    ) -> HealthCheckResult:
        """Normalize different result formats to HealthCheckResult."""
        timestamp = datetime.now()
        
        if isinstance(raw_result, HealthCheckResult):
            return raw_result
        elif isinstance(raw_result, dict):
            status_str = raw_result.get("status", "unknown").lower()
            status = HealthStatus.UNKNOWN
            
            for health_status in HealthStatus:
                if health_status.value == status_str:
                    status = health_status
                    break
            
            return HealthCheckResult(
                component=component,
                status=status,
                message=raw_result.get("message", "No message provided"),
                timestamp=timestamp,
                duration=duration,
                metadata=raw_result.get("metadata", {})
            )
        elif isinstance(raw_result, bool):
            return HealthCheckResult(
                component=component,
                status=HealthStatus.HEALTHY if raw_result else HealthStatus.UNHEALTHY,
                message="Health check passed" if raw_result else "Health check failed",
                timestamp=timestamp,
                duration=duration
            )
        else:
            # Try to convert to string
            message = str(raw_result) if raw_result else "No result"
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNKNOWN,
                message=message,
                timestamp=timestamp,
                duration=duration
            )
    
    async def _handle_status_change(
        self, 
        component: str, 
        old_status: HealthStatus, 
        new_status: HealthStatus
    ) -> None:
        """Handle health status changes."""
        # Execute status callbacks
        for callback in self._status_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(component, old_status, new_status)
                else:
                    callback(component, old_status, new_status)
            except Exception as e:
                self.logger.error(f"Error in status callback: {e}")
        
        # Generate alert if needed
        await self._maybe_generate_alert(component, old_status, new_status)
    
    async def _maybe_generate_alert(
        self, 
        component: str, 
        old_status: HealthStatus, 
        new_status: HealthStatus
    ) -> None:
        """Generate alert if conditions are met and debounce allows."""
        # Check if we should generate an alert
        should_alert = (
            old_status != new_status and
            new_status in [HealthStatus.WARNING, HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]
        )
        
        if not should_alert:
            return
        
        # Check debounce
        now = datetime.now()
        last_alert = self._last_alerts.get(component)
        if last_alert and (now - last_alert).total_seconds() < self._alert_debounce_seconds:
            return
        
        # Determine alert severity
        severity_map = {
            HealthStatus.WARNING: AlertSeverity.WARNING,
            HealthStatus.UNHEALTHY: AlertSeverity.ERROR,
            HealthStatus.CRITICAL: AlertSeverity.CRITICAL
        }
        severity = severity_map.get(new_status, AlertSeverity.INFO)
        
        # Create alert
        config = self._health_checks[component]
        alert = HealthAlert(
            component=component,
            severity=severity,
            message=f"Component '{component}' status changed from {old_status.value} to {new_status.value}",
            timestamp=now,
            old_status=old_status,
            new_status=new_status,
            metadata={
                "critical": config.critical,
                "consecutive_failures": config.consecutive_failures,
                "last_result": config.last_result.to_dict() if config.last_result else None
            }
        )
        
        # Update debounce timestamp
        self._last_alerts[component] = now
        
        # Execute alert callbacks
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
        
        self.logger.warning(f"Health alert: {alert.message}")
    
    def _update_overall_status(self) -> None:
        """Update overall system health status."""
        if not self._health_checks:
            self._overall_status = HealthStatus.UNKNOWN
            return
        
        statuses = []
        critical_statuses = []
        
        for component, config in self._health_checks.items():
            if config.last_result:
                statuses.append(config.last_result.status)
                if config.critical:
                    critical_statuses.append(config.last_result.status)
        
        if not statuses:
            self._overall_status = HealthStatus.UNKNOWN
            return
        
        # If any critical component is unhealthy, overall status is critical
        if critical_statuses and any(s in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL] for s in critical_statuses):
            self._overall_status = HealthStatus.CRITICAL
        # If any component is unhealthy, overall status is unhealthy
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            self._overall_status = HealthStatus.UNHEALTHY
        # If any component has warnings, overall status is warning
        elif any(s == HealthStatus.WARNING for s in statuses):
            self._overall_status = HealthStatus.WARNING
        # If all components are healthy, overall status is healthy
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            self._overall_status = HealthStatus.HEALTHY
        else:
            self._overall_status = HealthStatus.UNKNOWN
    
    def get_health_status(self, component: Optional[str] = None) -> Dict[str, Any]:
        """
        Get health status for a component or overall system.
        
        Args:
            component: Component name, or None for overall status
            
        Returns:
            Dict containing health status information
        """
        if component:
            if component not in self._health_checks:
                return {"error": f"Component '{component}' not found"}
            
            config = self._health_checks[component]
            history = self._health_history[component]
            
            # Calculate some basic metrics
            recent_checks = [r for r in history if (datetime.now() - r.timestamp).total_seconds() < 3600]
            avg_duration = mean([r.duration for r in recent_checks]) if recent_checks else 0
            success_rate = len([r for r in recent_checks if r.status == HealthStatus.HEALTHY]) / len(recent_checks) if recent_checks else 0
            
            return {
                "component": component,
                "status": config.last_result.status.value if config.last_result else "unknown",
                "message": config.last_result.message if config.last_result else "No checks performed",
                "last_check": config.last_run.isoformat() if config.last_run else None,
                "consecutive_failures": config.consecutive_failures,
                "enabled": config.enabled,
                "critical": config.critical,
                "metrics": {
                    "avg_duration_1h": avg_duration,
                    "success_rate_1h": success_rate,
                    "total_checks": len(history)
                },
                "metadata": config.metadata
            }
        else:
            # Overall status
            components = {}
            for comp_name in self._health_checks.keys():
                components[comp_name] = self.get_health_status(comp_name)
            
            return {
                "overall_status": self._overall_status.value,
                "components": components,
                "summary": {
                    "total_components": len(self._health_checks),
                    "healthy": len([c for c in components.values() if c.get("status") == "healthy"]),
                    "warning": len([c for c in components.values() if c.get("status") == "warning"]),
                    "unhealthy": len([c for c in components.values() if c.get("status") == "unhealthy"]),
                    "critical": len([c for c in components.values() if c.get("status") == "critical"])
                }
            }
    
    def _start_cleanup_task(self) -> None:
        """Start background cleanup task."""
        try:
            asyncio.get_running_loop()
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        except RuntimeError:
            # No event loop running
            pass
    
    async def _cleanup_loop(self) -> None:
        """Background task for cleaning up old health data."""
        while not self._shutdown:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # Clean up every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old health check results."""
        cutoff_time = datetime.now() - timedelta(hours=self._history_retention_hours)
        
        for component, history in self._health_history.items():
            original_count = len(history)
            self._health_history[component] = [
                result for result in history 
                if result.timestamp > cutoff_time
            ]
            
            cleaned_count = original_count - len(self._health_history[component])
            if cleaned_count > 0:
                self.logger.debug(f"Cleaned up {cleaned_count} old health records for '{component}'")
    
    async def shutdown(self) -> None:
        """Shutdown the health monitor."""
        self.logger.info("Shutting down health monitor")
        self._shutdown = True
        
        # Stop all monitoring
        self.stop_monitoring()
        
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Wait for all monitoring tasks to complete
        monitoring_tasks = [
            config.task for config in self._health_checks.values()
            if config.task and not config.task.done()
        ]
        if monitoring_tasks:
            await asyncio.gather(*monitoring_tasks, return_exceptions=True)
        
        self.logger.info("Health monitor shutdown complete")


# Global health monitor instance
_global_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance."""
    global _global_health_monitor
    if _global_health_monitor is None:
        _global_health_monitor = HealthMonitor()
    return _global_health_monitor


def register_health_check(
    component: str,
    check_function: Callable,
    interval: float,
    timeout: float = 30.0,
    critical: bool = False,
    auto_start: bool = True,
    **metadata
) -> None:
    """Register a health check on the global health monitor."""
    return get_health_monitor().register_health_check(
        component, check_function, interval, timeout, critical, auto_start, **metadata
    )


def get_health_status(component: Optional[str] = None) -> Dict[str, Any]:
    """Get health status using the global health monitor."""
    return get_health_monitor().get_health_status(component)