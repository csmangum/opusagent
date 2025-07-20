#!/usr/bin/env python3
"""
Example script demonstrating Redis-based session resume functionality.

This script shows how to:
1. Set up Redis session storage for production
2. Initialize session management with Redis
3. Create and resume sessions with Redis backend
4. Handle Redis connection issues gracefully
5. Monitor session storage performance

Requirements:
    pip install redis
    Redis server running (default: localhost:6379)
"""

import asyncio
import logging
import os
from datetime import datetime

from opusagent.session_storage.redis_storage import RedisSessionStorage
from opusagent.services.session_manager_service import SessionManagerService
from opusagent.models.session_state import SessionState, SessionStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_redis_session_resume():
    """Demonstrate Redis-based session resume functionality."""
    
    # Redis configuration
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    session_prefix = "opusagent:session:"
    default_ttl = 3600  # 1 hour
    
    logger.info(f"Initializing Redis session storage with URL: {redis_url}")
    
    try:
        # 1. Create Redis session storage
        redis_storage = RedisSessionStorage(
            redis_url=redis_url,
            session_prefix=session_prefix,
            default_ttl=default_ttl,
            max_connections=10
        )
        
        # 2. Initialize session manager service
        session_service = SessionManagerService(redis_storage)
        
        # 3. Start the service
        await session_service.start()
        logger.info("Session manager service started with Redis backend")
        
        # 4. Create a new session
        conversation_id = "redis-test-123"
        session = await session_service.create_session(
            conversation_id,
            status=SessionStatus.ACTIVE,
            media_format="pcm16",
            bridge_type="audiocodes"
        )
        
        logger.info(f"Created session: {conversation_id}")
        
        # 5. Add conversation context
        session.conversation_history = [
            {"type": "input", "text": "Hello, I need help with my account"},
            {"type": "output", "text": "Hi! I'd be happy to help you with your account."},
            {"type": "input", "text": "I want to check my balance"}
        ]
        
        # 6. Add function calls
        session.function_calls = [
            {
                "call_id": "func-1",
                "function_name": "get_balance",
                "arguments": {"account_id": "12345"},
                "status": "completed",
                "result": {"balance": 1500.00}
            }
        ]
        
        # 7. Store updated session
        await redis_storage.store_session(conversation_id, session.to_dict())
        logger.info("Stored session with conversation context and function calls")
        
        # 8. Simulate session resume
        logger.info("Simulating session resume...")
        resumed_session = await session_service.resume_session(conversation_id)
        
        if resumed_session:
            logger.info(f"✅ Session resumed successfully!")
            logger.info(f"   Resume count: {resumed_session.resumed_count}")
            logger.info(f"   Status: {resumed_session.status}")
            logger.info(f"   Media format: {resumed_session.media_format}")
            logger.info(f"   Conversation history items: {len(resumed_session.conversation_history)}")
            logger.info(f"   Function calls: {len(resumed_session.function_calls)}")
            
            # 9. Display conversation context
            logger.info("\n📝 Conversation Context:")
            for i, item in enumerate(resumed_session.conversation_history, 1):
                logger.info(f"   {i}. [{item['type']}] {item['text']}")
            
            # 10. Display function calls
            logger.info("\n🔧 Function Calls:")
            for i, func_call in enumerate(resumed_session.function_calls, 1):
                logger.info(f"   {i}. {func_call['function_name']} - {func_call['status']}")
                if func_call.get('result'):
                    logger.info(f"      Result: {func_call['result']}")
        else:
            logger.error("❌ Failed to resume session")
        
        # 11. Test session updates
        logger.info("\n🔄 Testing session updates...")
        success = await session_service.update_session(
            conversation_id,
            media_format="opus",
            status=SessionStatus.PAUSED
        )
        
        if success:
            logger.info("✅ Session updated successfully")
            
            # Retrieve updated session
            updated_session = await session_service.get_session(conversation_id)
            logger.info(f"   New media format: {updated_session.media_format}")
            logger.info(f"   New status: {updated_session.status}")
        else:
            logger.error("❌ Failed to update session")
        
        # 12. Test session validation
        logger.info("\n🔍 Testing session validation...")
        validation_result = await session_service.validate_session(conversation_id)
        logger.info(f"Validation result: {validation_result}")
        
        # 13. Get session statistics
        logger.info("\n📊 Session Statistics:")
        stats = await session_service.get_session_stats()
        for key, value in stats.items():
            logger.info(f"   {key}: {value}")
        
        # 14. List active sessions
        logger.info("\n📋 Active Sessions:")
        active_sessions = await session_service.list_active_sessions()
        logger.info(f"   Found {len(active_sessions)} active sessions")
        for session_id in active_sessions:
            logger.info(f"   - {session_id}")
        
        # 15. Test cleanup (optional)
        logger.info("\n🧹 Testing session cleanup...")
        cleaned = await session_service.cleanup_expired_sessions(max_age_seconds=300)  # 5 minutes
        logger.info(f"   Cleaned up {cleaned} expired sessions")
        
        # 16. End session
        logger.info("\n🔚 Ending session...")
        await session_service.end_session(conversation_id, "Example completed")
        logger.info("✅ Session ended successfully")
        
        # 17. Verify session cannot be resumed after ending
        logger.info("\n🚫 Testing resume after end...")
        ended_resume = await session_service.resume_session(conversation_id)
        if ended_resume is None:
            logger.info("✅ Correctly prevented resume of ended session")
        else:
            logger.warning("⚠️  Unexpectedly able to resume ended session")
        
    except Exception as e:
        logger.error(f"❌ Error during Redis session resume example: {e}")
        logger.error("Make sure Redis server is running and accessible")
        
    finally:
        # Cleanup
        try:
            await session_service.stop()
            await redis_storage.close()
            logger.info("✅ Redis session storage cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def example_redis_connection_handling():
    """Demonstrate Redis connection error handling."""
    
    logger.info("\n" + "="*60)
    logger.info("REDIS CONNECTION ERROR HANDLING EXAMPLE")
    logger.info("="*60)
    
    # Test with invalid Redis URL
    invalid_redis_url = "redis://invalid-host:6379"
    
    try:
        redis_storage = RedisSessionStorage(redis_url=invalid_redis_url)
        session_service = SessionManagerService(redis_storage)
        
        # Try to create session (should fail gracefully)
        session = await session_service.create_session("test-connection")
        
        if session:
            logger.info("✅ Unexpectedly created session with invalid Redis")
        else:
            logger.info("✅ Correctly handled invalid Redis connection")
            
    except Exception as e:
        logger.info(f"✅ Correctly caught Redis connection error: {e}")


async def example_redis_performance_monitoring():
    """Demonstrate Redis performance monitoring."""
    
    logger.info("\n" + "="*60)
    logger.info("REDIS PERFORMANCE MONITORING EXAMPLE")
    logger.info("="*60)
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    try:
        redis_storage = RedisSessionStorage(redis_url=redis_url)
        
        # Get storage statistics
        stats = redis_storage.get_stats()
        logger.info("Redis Storage Statistics:")
        for key, value in stats.items():
            logger.info(f"   {key}: {value}")
        
        # Test connection performance
        import time
        
        start_time = time.time()
        success = await redis_storage.store_session("perf-test", {"test": "data"})
        store_time = time.time() - start_time
        
        start_time = time.time()
        retrieved = await redis_storage.retrieve_session("perf-test")
        retrieve_time = time.time() - start_time
        
        logger.info(f"Performance Metrics:")
        logger.info(f"   Store operation: {store_time:.4f} seconds")
        logger.info(f"   Retrieve operation: {retrieve_time:.4f} seconds")
        
        # Cleanup
        await redis_storage.delete_session("perf-test")
        await redis_storage.close()
        
    except Exception as e:
        logger.error(f"Error during performance monitoring: {e}")


async def main():
    """Run all Redis session resume examples."""
    logger.info("🚀 Starting Redis Session Resume Examples")
    logger.info("="*60)
    
    # Check if Redis is available
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    logger.info(f"Using Redis URL: {redis_url}")
    logger.info("Make sure Redis server is running for full functionality")
    
    # Run examples
    await example_redis_session_resume()
    await example_redis_connection_handling()
    await example_redis_performance_monitoring()
    
    logger.info("\n" + "="*60)
    logger.info("✅ Redis Session Resume Examples Completed")
    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(main()) 