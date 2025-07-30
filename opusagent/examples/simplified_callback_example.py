"""
Example demonstrating simplified callback systems in OpusAgent.

This example shows how to use the streamlined error handling, resource cleanup, 
and health checking systems to improve code quality without over-engineering.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

# Import the simplified callback systems
from opusagent.handlers.error_handler import (
    get_error_handler, 
    ErrorContext, 
    ErrorSeverity,
    ErrorInfo,
    register_error_handler
)
from opusagent.handlers.resource_manager import (
    get_resource_manager,
    ResourceType,
    CleanupPriority,
    register_cleanup
)
from opusagent.handlers.health_checker import (
    get_health_checker,
    register_health_check
)
from opusagent.utils.polling_utils import start_simple_poll
from opusagent.models.session_state import SessionState, SessionStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimplifiedCallbackExample:
    """Example demonstrating simplified callback system integration."""
    
    def __init__(self):
        """Initialize the example with simplified callback systems."""
        self.session = None
        self.websocket_connection = None
        self.polling_task = None
        
        # Setup simplified systems
        self.setup_error_handling()
        self.setup_resource_management()
        self.setup_health_monitoring()
    
    def setup_error_handling(self):
        """Setup centralized error handling."""
        logger.info("🔧 Setting up error handling...")
        
        # Register global error handler for logging
        def log_error_handler(error_info: ErrorInfo):
            logger.error(f"[{error_info.context.value.upper()}] {error_info.error}")
        
        register_error_handler(log_error_handler)
        
        # Register WebSocket-specific error handler
        def websocket_error_handler(error_info: ErrorInfo):
            if error_info.context == ErrorContext.WEBSOCKET:
                logger.warning(f"WebSocket issue: {error_info.operation}, attempting reconnection...")
                # Could trigger reconnection logic here
        
        register_error_handler(websocket_error_handler, ErrorContext.WEBSOCKET)
    
    def setup_resource_management(self):
        """Setup resource cleanup callbacks."""
        logger.info("🧹 Setting up resource cleanup...")
        
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
        """Setup basic health monitoring."""
        logger.info("🏥 Setting up health monitoring...")
        
        # Register database health check (simulated)
        def check_database_health():
            # Simulate database connectivity check
            import random
            if random.random() > 0.1:  # 90% success rate
                return {
                    "status": "healthy",
                    "message": "Database is responsive"
                }
            else:
                return {
                    "status": "unhealthy", 
                    "message": "Database connection timeout"
                }
        
        register_health_check(
            name="database",
            check_function=check_database_health,
            interval=30.0
        )
        
        # Register API health check
        def check_api_health():
            # Simulate API health check
            import random
            return random.random() > 0.05  # 95% success rate (returns boolean)
        
        register_health_check(
            name="api",
            check_function=check_api_health,
            interval=20.0
        )
    
    async def simulate_session_lifecycle(self):
        """Simulate a session lifecycle with simplified callback systems."""
        logger.info("🚀 Starting session lifecycle simulation...")
        
        # Create session
        self.session = SessionState(
            conversation_id="demo_session_123",
            bot_name="demo-bot",
            caller="+1234567890"
        )
        
        # Register session cleanup
        register_cleanup(
            callback=lambda: logger.info(f"Cleaning up session {self.session.conversation_id}"),
            resource_type=ResourceType.SESSION,
            priority=CleanupPriority.HIGH,
            description=f"Session {self.session.conversation_id}"
        )
        
        # Simulate session activity
        logger.info("📞 Session initiated...")
        await asyncio.sleep(1)
        
        self.session.status = SessionStatus.ACTIVE
        logger.info(f"Session status: {self.session.status.value}")
        await asyncio.sleep(1)
        
        # Add conversation activity
        self.session.add_conversation_item({
            "role": "user",
            "content": "Hello, I need help"
        })
        
        # Simulate WebSocket connection
        logger.info("🔌 Establishing WebSocket connection...")
        self.websocket_connection = self.simulate_websocket_connection()
        
        # Register WebSocket cleanup
        register_cleanup(
            callback=lambda: self.cleanup_websocket(),
            resource_type=ResourceType.WEBSOCKET,
            priority=CleanupPriority.CRITICAL,
            description="Main WebSocket connection"
        )
        
        # Start simple polling for WebSocket health
        def check_websocket_health():
            if self.websocket_connection and not self.websocket_connection.closed:
                logger.debug("WebSocket connection is healthy")
            else:
                logger.warning("WebSocket connection is unhealthy")
        
        self.polling_task = start_simple_poll(
            check_function=check_websocket_health,
            interval=10.0,
            condition=lambda: self.websocket_connection is not None
        )
        
        await asyncio.sleep(3)
        
        # Simulate some errors to test error handling
        try:
            raise ConnectionError("Simulated WebSocket connection error")
        except Exception as e:
            await get_error_handler().handle_error(
                error=e,
                context=ErrorContext.WEBSOCKET,
                severity=ErrorSeverity.HIGH,
                operation="websocket_communication"
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
                operation="process_user_input"
            )
        
        await asyncio.sleep(1)
        
        # End session
        logger.info("⏹️ Ending session...")
        self.session.status = SessionStatus.ENDED
        
        # Stop polling
        if self.polling_task:
            self.polling_task.cancel()
        
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
    
    async def run_demo(self):
        """Run the complete demo."""
        logger.info("🎬 Starting Simplified OpusAgent Callback Demo")
        logger.info("=" * 60)
        
        try:
            # Run the session lifecycle simulation
            await self.simulate_session_lifecycle()
            
            # Let health monitoring run for a bit
            logger.info("⏱️ Running health monitoring for 15 seconds...")
            await asyncio.sleep(15)
            
            # Show health status
            health_status = get_health_checker().get_status()
            logger.info("🏥 Health status:")
            logger.info(f"  Overall: {health_status['overall_status']}")
            for name, status in health_status['checks'].items():
                logger.info(f"  {name}: {status['status']} - {status['message']}")
            
            # Show error statistics
            error_stats = get_error_handler().get_error_stats()
            logger.info("🔧 Error handling statistics:")
            logger.info(f"  Total errors: {error_stats['total_errors']}")
            for context, count in error_stats['error_counts'].items():
                if count > 0:
                    logger.info(f"  {context}: {count} errors")
            
            # Show resource statistics
            resource_stats = get_resource_manager().get_stats()
            logger.info("🧹 Resource management statistics:")
            logger.info(f"  Total cleanup callbacks: {resource_stats['total_callbacks']}")
            for resource_type, count in resource_stats['by_type'].items():
                if count > 0:
                    logger.info(f"  {resource_type}: {count} callbacks")
            
        except Exception as e:
            logger.error(f"Demo error: {e}")
        finally:
            # Shutdown all systems
            logger.info("🔄 Shutting down simplified callback systems...")
            await get_health_checker().shutdown()
            await get_resource_manager().cleanup_all()
            
            logger.info("✅ Simplified demo completed successfully!")


async def main():
    """Main function to run the simplified integration example."""
    example = SimplifiedCallbackExample()
    await example.run_demo()


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())