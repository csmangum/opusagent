"""
Example demonstrating integration of all callback systems in OpusAgent.

This example shows how to use the error handling, state transition, polling,
resource cleanup, event processing, and health monitoring callback systems
together to create a robust and reactive application.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any

# Import all the callback systems
from opusagent.handlers.error_handler import (
    get_error_handler, 
    ErrorContext, 
    ErrorSeverity,
    ErrorInfo,
    register_error_handler
)
from opusagent.handlers.polling_manager import (
    get_polling_manager,
    register_polling_task
)
from opusagent.handlers.resource_manager import (
    get_resource_manager,
    ResourceType,
    CleanupPriority,
    register_cleanup
)
from opusagent.handlers.health_monitor import (
    get_health_monitor,
    HealthStatus,
    HealthAlert,
    register_health_check
)
from opusagent.handlers.event_router import EventRouter
from opusagent.models.session_state import SessionState, SessionStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpusAgentIntegrationExample:
    """Example demonstrating comprehensive callback system integration."""
    
    def __init__(self):
        """Initialize the example with all callback systems."""
        self.session = None
        self.websocket_connection = None
        self.event_router = EventRouter()
        
        # Initialize callback systems
        self.setup_error_handling()
        self.setup_session_callbacks()
        self.setup_polling_tasks()
        self.setup_resource_management()
        self.setup_health_monitoring()
        self.setup_event_processing()
    
    def setup_error_handling(self):
        """Setup centralized error handling with context-specific callbacks."""
        logger.info("🔧 Setting up error handling callbacks...")
        
        # Register global error handler for logging
        def log_error_handler(error_info: ErrorInfo):
            logger.error(f"[{error_info.context.value.upper()}] {error_info.error}")
            if error_info.severity == ErrorSeverity.CRITICAL:
                logger.critical(f"CRITICAL ERROR: {error_info.operation} failed!")
        
        register_error_handler(log_error_handler, priority=100)
        
        # Register WebSocket-specific error handler
        def websocket_error_handler(error_info: ErrorInfo):
            if error_info.context == ErrorContext.WEBSOCKET:
                logger.warning(f"WebSocket issue in {error_info.operation}, attempting reconnection...")
                # Could trigger reconnection logic here
        
        register_error_handler(websocket_error_handler, ErrorContext.WEBSOCKET, priority=50)
        
        # Register session error handler
        def session_error_handler(error_info: ErrorInfo):
            if error_info.context == ErrorContext.SESSION and self.session:
                self.session.set_error(f"{error_info.operation}: {error_info.error}")
                logger.info(f"Session error count: {self.session.error_count}")
        
        register_error_handler(session_error_handler, ErrorContext.SESSION, priority=75)
    
    def setup_session_callbacks(self):
        """Setup session state transition callbacks."""
        logger.info("📊 Setting up session state callbacks...")
        
        def on_session_status_change(old_status, new_status, session):
            logger.info(f"Session {session.conversation_id} status: {old_status.value} → {new_status.value}")
            
            # Example reactive logic based on status changes
            if new_status == SessionStatus.ACTIVE:
                logger.info("🟢 Session became active - starting real-time monitoring")
                self.start_session_monitoring()
            elif new_status == SessionStatus.ERROR:
                logger.warning("🔴 Session entered error state - triggering recovery")
                self.handle_session_error()
            elif new_status == SessionStatus.ENDED:
                logger.info("⏹️ Session ended - performing cleanup")
                asyncio.create_task(self.cleanup_session_resources())
        
        # We'll register this callback when we create a session
        self.session_status_callback = on_session_status_change
    
    def setup_polling_tasks(self):
        """Setup configurable polling tasks for monitoring."""
        logger.info("⏰ Setting up polling tasks...")
        
        # Register WebSocket health check
        def check_websocket_health():
            if self.websocket_connection:
                # Simulate WebSocket health check
                if hasattr(self.websocket_connection, 'closed') and not self.websocket_connection.closed:
                    return {"status": "healthy", "latency": 0.02}
                else:
                    return {"status": "unhealthy", "reason": "connection_closed"}
            return {"status": "unknown", "reason": "no_connection"}
        
        register_polling_task(
            name="websocket_health",
            callback=check_websocket_health,
            interval=10.0,  # Check every 10 seconds
            condition=lambda: self.websocket_connection is not None,
            auto_start=False,  # Start manually when connection is established
            component="websocket"
        )
        
        # Register memory usage monitoring
        def check_memory_usage():
            import psutil
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 90:
                return {"status": "critical", "memory_percent": memory_percent}
            elif memory_percent > 75:
                return {"status": "warning", "memory_percent": memory_percent}
            else:
                return {"status": "healthy", "memory_percent": memory_percent}
        
        register_polling_task(
            name="memory_monitor",
            callback=check_memory_usage,
            interval=30.0,  # Check every 30 seconds
            auto_start=True,
            system="memory"
        )
    
    def setup_resource_management(self):
        """Setup resource cleanup callbacks."""
        logger.info("🧹 Setting up resource cleanup callbacks...")
        
        # Register global cleanup handler
        def log_cleanup_handler():
            logger.info("Performing global cleanup...")
        
        register_cleanup(
            callback=log_cleanup_handler,
            resource_type=ResourceType.OTHER,
            priority=CleanupPriority.LOW,
            description="Global cleanup logger"
        )
    
    def setup_health_monitoring(self):
        """Setup health monitoring with alerts."""
        logger.info("🏥 Setting up health monitoring...")
        
        # Register alert callback
        def handle_health_alert(alert: HealthAlert):
            logger.warning(f"🚨 HEALTH ALERT: {alert.message} (severity: {alert.severity.value})")
            
            # Example: Send alert to monitoring system
            if alert.severity.value in ["error", "critical"]:
                logger.critical(f"Critical health issue detected in {alert.component}!")
        
        get_health_monitor().register_alert_callback(handle_health_alert)
        
        # Register status change callback
        def handle_health_status_change(component, old_status, new_status):
            logger.info(f"Health status for {component}: {old_status.value} → {new_status.value}")
        
        get_health_monitor().register_status_callback(handle_health_status_change)
        
        # Register database health check (simulated)
        def check_database_health():
            # Simulate database connectivity check
            import random
            if random.random() > 0.1:  # 90% success rate
                return {
                    "status": "healthy",
                    "message": "Database is responsive",
                    "query_time": random.uniform(0.01, 0.1)
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Database connection timeout"
                }
        
        register_health_check(
            component="database",
            check_function=check_database_health,
            interval=60.0,  # Check every minute
            critical=True,
            service="postgresql"
        )
        
        # Register OpenAI API health check
        def check_openai_api():
            # Simulate OpenAI API health check
            import random
            if random.random() > 0.05:  # 95% success rate
                return {
                    "status": "healthy",
                    "message": "OpenAI API is responsive",
                    "api_latency": random.uniform(0.1, 0.5)
                }
            else:
                return {
                    "status": "warning",
                    "message": "OpenAI API experiencing high latency"
                }
        
        register_health_check(
            component="openai_api",
            check_function=check_openai_api,
            interval=45.0,  # Check every 45 seconds
            critical=False,
            service="openai"
        )
    
    def setup_event_processing(self):
        """Setup enhanced event processing with middleware."""
        logger.info("📡 Setting up event processing...")
        
        # Register event middleware for logging
        def event_logging_middleware(event_type, data):
            logger.debug(f"Processing event: {event_type}")
            # Add timestamp to all events
            data["processed_at"] = datetime.now().isoformat()
            return data
        
        self.event_router.register_middleware(event_logging_middleware, priority=100)
        
        # Register event middleware for filtering sensitive data
        def security_filter_middleware(event_type, data):
            # Remove sensitive fields from events
            if "auth_token" in data:
                data = data.copy()
                data["auth_token"] = "***REDACTED***"
            return data
        
        self.event_router.register_middleware(security_filter_middleware, priority=200)
        
        # Register multiple handlers for the same event type
        def primary_audio_handler(data):
            logger.info(f"Primary audio handler processing chunk of size: {len(data.get('audioChunk', ''))}")
        
        def secondary_audio_handler(data):
            # Could be for analytics, recording, etc.
            logger.debug("Secondary audio handler - analytics processing")
        
        from opusagent.models.audiocodes_api import TelephonyEventType
        
        # Register multiple handlers with different priorities
        self.event_router.register_platform_handler(
            TelephonyEventType.AUDIO_IN, 
            primary_audio_handler, 
            priority=100
        )
        self.event_router.register_platform_handler(
            TelephonyEventType.AUDIO_IN, 
            secondary_audio_handler, 
            priority=50
        )
    
    async def simulate_session_lifecycle(self):
        """Simulate a complete session lifecycle with all callback systems."""
        logger.info("🚀 Starting session lifecycle simulation...")
        
        # Create session with callback registration
        self.session = SessionState(
            conversation_id="demo_session_123",
            bot_name="demo-bot",
            caller="+1234567890"
        )
        
        # Register session status callback
        self.session.register_status_callback(self.session_status_callback)
        
        # Register session cleanup
        cleanup_id = register_cleanup(
            callback=lambda: logger.info(f"Cleaning up session {self.session.conversation_id}"),
            resource_type=ResourceType.SESSION,
            priority=CleanupPriority.HIGH,
            description=f"Session {self.session.conversation_id}",
            resource_id=self.session.conversation_id
        )
        
        # Simulate session state changes
        logger.info("📞 Session initiated...")
        await asyncio.sleep(1)
        
        self.session.update_status(SessionStatus.ACTIVE)
        await asyncio.sleep(2)
        
        # Simulate some conversation activity
        self.session.add_conversation_item({
            "role": "user",
            "content": "Hello, I need help with my account"
        })
        
        # Simulate WebSocket connection
        logger.info("🔌 Establishing WebSocket connection...")
        self.websocket_connection = self.simulate_websocket_connection()
        
        # Register WebSocket cleanup
        register_cleanup(
            callback=lambda: self.cleanup_websocket(),
            resource_type=ResourceType.WEBSOCKET,
            priority=CleanupPriority.CRITICAL,
            description="Main WebSocket connection",
            resource_id="main_ws"
        )
        
        # Start WebSocket health monitoring
        from opusagent.handlers.polling_manager import start_polling_task
        start_polling_task("websocket_health")
        
        await asyncio.sleep(3)
        
        # Simulate some errors to test error handling
        try:
            raise ConnectionError("Simulated WebSocket connection error")
        except Exception as e:
            await get_error_handler().handle_error(
                error=e,
                context=ErrorContext.WEBSOCKET,
                severity=ErrorSeverity.HIGH,
                operation="websocket_communication",
                connection_id="main_ws"
            )
        
        await asyncio.sleep(2)
        
        # Simulate session error
        try:
            raise ValueError("Simulated session processing error")
        except Exception as e:
            await get_error_handler().handle_error(
                error=e,
                context=ErrorContext.SESSION,
                severity=ErrorSeverity.MEDIUM,
                operation="process_user_input",
                session_id=self.session.conversation_id
            )
        
        await asyncio.sleep(1)
        
        # End session
        logger.info("⏹️ Ending session...")
        self.session.update_status(SessionStatus.ENDED)
        
        await asyncio.sleep(1)
        
        # Demonstrate resource cleanup
        logger.info("🧹 Performing cleanup...")
        await get_resource_manager().cleanup_all()
    
    def simulate_websocket_connection(self):
        """Simulate a WebSocket connection object."""
        class MockWebSocket:
            def __init__(self):
                self.closed = False
            
            def close(self):
                self.closed = True
        
        return MockWebSocket()
    
    def cleanup_websocket(self):
        """Clean up WebSocket connection."""
        if self.websocket_connection:
            logger.info("🔌 Closing WebSocket connection")
            self.websocket_connection.close()
            self.websocket_connection = None
    
    def start_session_monitoring(self):
        """Start additional monitoring when session becomes active."""
        logger.info("📊 Starting session-specific monitoring...")
        # Could start additional polling tasks, health checks, etc.
    
    def handle_session_error(self):
        """Handle session error state."""
        logger.warning("🔧 Handling session error - implementing recovery logic...")
        # Could implement session recovery, restart logic, etc.
    
    async def cleanup_session_resources(self):
        """Clean up session-specific resources."""
        logger.info("🧹 Cleaning up session resources...")
        # Perform session-specific cleanup
        if self.session:
            logger.info(f"Session {self.session.conversation_id} final stats:")
            logger.info(f"  - Conversation turns: {self.session.current_turn}")
            logger.info(f"  - Error count: {self.session.error_count}")
            logger.info(f"  - Resume count: {self.session.resumed_count}")
    
    async def run_demo(self):
        """Run the complete demo."""
        logger.info("🎬 Starting OpusAgent Callback Integration Demo")
        logger.info("=" * 60)
        
        try:
            # Run the session lifecycle simulation
            await self.simulate_session_lifecycle()
            
            # Let health monitoring run for a bit
            logger.info("⏱️ Running health monitoring for 30 seconds...")
            await asyncio.sleep(30)
            
            # Show health status
            health_status = get_health_monitor().get_health_status()
            logger.info("🏥 Overall health status:")
            logger.info(f"  Status: {health_status['overall_status']}")
            for component, status in health_status['components'].items():
                logger.info(f"  {component}: {status['status']} - {status['message']}")
            
            # Show polling task status
            polling_status = get_polling_manager().get_all_tasks_status()
            logger.info("⏰ Polling task status:")
            for task_name, status in polling_status.items():
                logger.info(f"  {task_name}: {status['status']} (errors: {status['error_count']})")
            
            # Show error statistics
            error_stats = get_error_handler().get_error_stats()
            logger.info("🔧 Error handling statistics:")
            logger.info(f"  Total errors: {error_stats['total_errors']}")
            for context, count in error_stats['error_counts'].items():
                if count > 0:
                    logger.info(f"  {context}: {count} errors")
            
        except Exception as e:
            logger.error(f"Demo error: {e}")
        finally:
            # Shutdown all systems
            logger.info("🔄 Shutting down all callback systems...")
            await get_health_monitor().shutdown()
            await get_polling_manager().shutdown()
            await get_resource_manager().cleanup_all()
            
            logger.info("✅ Demo completed successfully!")


async def main():
    """Main function to run the integration example."""
    example = OpusAgentIntegrationExample()
    await example.run_demo()


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())