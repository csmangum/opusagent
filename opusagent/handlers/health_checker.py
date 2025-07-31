"""
Basic health checking system.

This module provides a simple health checking system for monitoring
key components without the complexity of enterprise monitoring features.
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass


class HealthStatus(Enum):
    """Health status enumeration."""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    WARNING = "warning"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """Configuration for a health check."""
    name: str
    check_function: Callable
    interval: float
    last_status: HealthStatus = HealthStatus.UNKNOWN
    last_check: Optional[datetime] = None
    last_message: str = "No checks performed"


class HealthChecker:
    """
    Basic health checking system.
    
    Provides simple health monitoring for critical components without
    the complexity of enterprise-level monitoring features.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the health checker."""
        self.logger = logger or logging.getLogger(__name__)
        self._checks: Dict[str, HealthCheck] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._shutdown = False
    
    def register_check(
        self,
        name: str,
        check_function: Callable,
        interval: float = 60.0,
        auto_start: bool = True
    ) -> None:
        """
        Register a health check.
        
        Args:
            name: Unique name for the health check
            check_function: Function that returns health status
            interval: Check interval in seconds
            auto_start: Whether to start checking immediately
        """
        if name in self._checks:
            raise ValueError(f"Health check '{name}' already exists")
        
        self._checks[name] = HealthCheck(
            name=name,
            check_function=check_function,
            interval=interval
        )
        
        self.logger.info(f"Registered health check: {name} (interval: {interval}s)")
        
        if auto_start:
            self.start_check(name)
    
    def start_check(self, name: str) -> bool:
        """Start a health check."""
        if name not in self._checks:
            self.logger.error(f"Health check '{name}' not found")
            return False
        
        if name in self._running_tasks:
            self.logger.warning(f"Health check '{name}' already running")
            return True
        
        self._running_tasks[name] = asyncio.create_task(self._check_loop(name))
        self.logger.info(f"Started health check: {name}")
        return True
    
    def stop_check(self, name: str) -> bool:
        """Stop a health check."""
        if name in self._running_tasks:
            self._running_tasks[name].cancel()
            del self._running_tasks[name]
            self.logger.info(f"Stopped health check: {name}")
            return True
        return False
    
    async def check_now(self, name: str) -> Optional[Dict[str, Any]]:
        """Run a single health check immediately."""
        if name not in self._checks:
            return None
        
        check = self._checks[name]
        return await self._perform_check(check)
    
    async def check_all(self) -> Dict[str, Dict[str, Any]]:
        """Run all health checks immediately."""
        results = {}
        for name in self._checks.keys():
            result = await self.check_now(name)
            if result:
                results[name] = result
        return results
    
    def get_status(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get health status for a specific check or all checks."""
        if name:
            if name not in self._checks:
                return {"error": f"Health check '{name}' not found"}
            
            check = self._checks[name]
            return {
                "name": name,
                "status": check.last_status.value,
                "message": check.last_message,
                "last_check": check.last_check.isoformat() if check.last_check else None,
                "interval": check.interval,
                "running": name in self._running_tasks
            }
        else:
            # Return all checks
            checks = {}
            for check_name in self._checks.keys():
                checks[check_name] = self.get_status(check_name)
            
            # Calculate overall status
            statuses = [self._checks[name].last_status for name in self._checks.keys()]
            if not statuses:
                overall = HealthStatus.UNKNOWN
            elif any(s == HealthStatus.UNHEALTHY for s in statuses):
                overall = HealthStatus.UNHEALTHY
            elif any(s == HealthStatus.WARNING for s in statuses):
                overall = HealthStatus.WARNING
            elif all(s == HealthStatus.HEALTHY for s in statuses):
                overall = HealthStatus.HEALTHY
            else:
                overall = HealthStatus.UNKNOWN
            
            return {
                "overall_status": overall.value,
                "checks": checks,
                "total_checks": len(self._checks),
                "running_checks": len(self._running_tasks)
            }
    
    async def _check_loop(self, name: str) -> None:
        """Main loop for a health check."""
        check = self._checks[name]
        
        while not self._shutdown:
            try:
                await self._perform_check(check)
                await asyncio.sleep(check.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop for '{name}': {e}")
                await asyncio.sleep(check.interval)
    
    async def _perform_check(self, check: HealthCheck) -> Dict[str, Any]:
        """Perform a single health check."""
        try:
            if asyncio.iscoroutinefunction(check.check_function):
                result = await check.check_function()
            else:
                result = check.check_function()
            
            # Normalize result
            if isinstance(result, dict):
                status_str = result.get("status", "unknown").lower()
                message = result.get("message", "No message provided")
            elif isinstance(result, bool):
                status_str = "healthy" if result else "unhealthy"
                message = "Check passed" if result else "Check failed"
            else:
                status_str = "unknown"
                message = str(result) if result else "No result"
            
            # Convert to HealthStatus
            status = HealthStatus.UNKNOWN
            for health_status in HealthStatus:
                if health_status.value == status_str:
                    status = health_status
                    break
            
            check.last_status = status
            check.last_message = message
            check.last_check = datetime.now()
            
            self.logger.debug(f"Health check '{check.name}': {status.value} - {message}")
            
            return {
                "status": status.value,
                "message": message,
                "timestamp": check.last_check.isoformat()
            }
            
        except Exception as e:
            check.last_status = HealthStatus.UNHEALTHY
            check.last_message = f"Check failed: {str(e)}"
            check.last_check = datetime.now()
            
            self.logger.error(f"Health check '{check.name}' failed: {e}")
            
            return {
                "status": "unhealthy",
                "message": check.last_message,
                "timestamp": check.last_check.isoformat()
            }
    
    async def shutdown(self) -> None:
        """Shutdown the health checker."""
        self.logger.info("Shutting down health checker")
        self._shutdown = True
        
        # Cancel all running tasks
        for task in self._running_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
        
        self._running_tasks.clear()
        self.logger.info("Health checker shutdown complete")


# Global health checker instance
_global_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    global _global_health_checker
    if _global_health_checker is None:
        _global_health_checker = HealthChecker()
    return _global_health_checker


def register_health_check(
    name: str,
    check_function: Callable,
    interval: float = 60.0,
    auto_start: bool = True
) -> None:
    """Register a health check on the global health checker."""
    return get_health_checker().register_check(name, check_function, interval, auto_start)


def get_health_status(name: Optional[str] = None) -> Dict[str, Any]:
    """Get health status using the global health checker."""
    return get_health_checker().get_status(name)