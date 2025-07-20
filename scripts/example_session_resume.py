#!/usr/bin/env python3
"""
Example script demonstrating session resume functionality.

This script shows how to:
1. Create a session storage backend
2. Initialize session management
3. Create and resume sessions
4. Handle session state persistence
"""

import asyncio
import logging
from datetime import datetime

from opusagent.session_storage.memory_storage import MemorySessionStorage
from opusagent.services.session_manager_service import SessionManagerService
from opusagent.models.session_state import SessionState, SessionStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_session_resume():
    """Demonstrate session resume functionality."""
    
    # 1. Create session storage backend
    storage = MemorySessionStorage(max_sessions=100, cleanup_interval=60)
    
    # 2. Initialize session manager service
    session_service = SessionManagerService(storage)
    await session_service.start()
    
    try:
        # 3. Create a new session
        conversation_id = "conv_example_123"
        session_state = await session_service.create_session(
            conversation_id=conversation_id,
            bridge_type="audiocodes",
            bot_name="CustomerServiceBot",
            caller="+15551234567",
            media_format="raw/lpcm16"
        )
        
        logger.info(f"Created session: {session_state.conversation_id}")
        logger.info(f"Session status: {session_state.status.value}")
        
        # 4. Simulate some conversation activity
        session_state.add_conversation_item({
            "type": "user_message",
            "text": "Hello, I need help with my account",
            "timestamp": datetime.now().isoformat()
        })
        
        session_state.add_function_call({
            "name": "get_balance",
            "arguments": {"account_id": "12345"},
            "timestamp": datetime.now().isoformat()
        })
        
        # 5. Update session in storage
        await session_service.update_session(
            conversation_id,
            conversation_history=session_state.conversation_history,
            function_calls=session_state.function_calls
        )
        
        logger.info(f"Updated session with {len(session_state.conversation_history)} conversation items")
        logger.info(f"Session has {len(session_state.function_calls)} function calls")
        
        # 6. Simulate session end (but keep in storage)
        await session_service.end_session(conversation_id, "User temporarily disconnected")
        
        # 7. Resume the session
        logger.info("Attempting to resume session...")
        resumed_session = await session_service.resume_session(conversation_id)
        
        if resumed_session:
            logger.info(f"✅ Successfully resumed session: {resumed_session.conversation_id}")
            logger.info(f"Resume count: {resumed_session.resumed_count}")
            logger.info(f"Conversation items: {len(resumed_session.conversation_history)}")
            logger.info(f"Function calls: {len(resumed_session.function_calls)}")
            
            # 8. Add more conversation activity
            resumed_session.add_conversation_item({
                "type": "user_message",
                "text": "I'm back, can you continue helping me?",
                "timestamp": datetime.now().isoformat()
            })
            
            await session_service.update_session(
                conversation_id,
                conversation_history=resumed_session.conversation_history
            )
            
            logger.info("Added new conversation item to resumed session")
        else:
            logger.error("❌ Failed to resume session")
        
        # 9. Get session statistics
        stats = await session_service.get_session_stats()
        logger.info(f"Session stats: {stats}")
        
        # 10. Validate session
        validation = await session_service.validate_session(conversation_id)
        logger.info(f"Session validation: {validation}")
        
        # 11. List active sessions
        active_sessions = await session_service.list_active_sessions()
        logger.info(f"Active sessions: {active_sessions}")
        
        # 12. Clean up
        await session_service.delete_session(conversation_id)
        logger.info("Session deleted")
        
    finally:
        # 13. Stop the service
        await session_service.stop()


async def example_multiple_sessions():
    """Demonstrate handling multiple sessions."""
    
    storage = MemorySessionStorage(max_sessions=10, cleanup_interval=30)
    session_service = SessionManagerService(storage)
    await session_service.start()
    
    try:
        # Create multiple sessions
        sessions = []
        for i in range(3):
            conv_id = f"conv_multi_{i}"
            session = await session_service.create_session(
                conversation_id=conv_id,
                bridge_type="audiocodes",
                bot_name=f"Bot_{i}",
                caller=f"+1555{i:06d}"
            )
            sessions.append(session)
            logger.info(f"Created session {i}: {conv_id}")
        
        # List all sessions
        active_sessions = await session_service.list_active_sessions()
        logger.info(f"All active sessions: {active_sessions}")
        
        # Resume a specific session
        if sessions:
            target_session = sessions[1]  # Resume the second session
            resumed = await session_service.resume_session(target_session.conversation_id)
            if resumed:
                logger.info(f"Resumed session: {resumed.conversation_id}")
        
        # Clean up all sessions
        for session in sessions:
            await session_service.delete_session(session.conversation_id)
        
        logger.info("All sessions cleaned up")
        
    finally:
        await session_service.stop()


async def example_session_expiration():
    """Demonstrate session expiration and cleanup."""
    
    storage = MemorySessionStorage(max_sessions=5, cleanup_interval=5)  # Short cleanup interval
    session_service = SessionManagerService(storage)
    await session_service.start()
    
    try:
        # Create a session
        conv_id = "conv_expire_test"
        session = await session_service.create_session(
            conversation_id=conv_id,
            bridge_type="audiocodes"
        )
        
        logger.info(f"Created session: {session.conversation_id}")
        
        # Wait for cleanup to run
        logger.info("Waiting for cleanup to run...")
        await asyncio.sleep(10)
        
        # Check if session was cleaned up
        active_sessions = await session_service.list_active_sessions()
        logger.info(f"Active sessions after cleanup: {active_sessions}")
        
        if conv_id not in active_sessions:
            logger.info("✅ Session was cleaned up due to inactivity")
        else:
            logger.info("❌ Session was not cleaned up")
        
    finally:
        await session_service.stop()


if __name__ == "__main__":
    async def main():
        logger.info("=== Session Resume Example ===")
        await example_session_resume()
        
        logger.info("\n=== Multiple Sessions Example ===")
        await example_multiple_sessions()
        
        logger.info("\n=== Session Expiration Example ===")
        await example_session_expiration()
        
        logger.info("\n=== All examples completed ===")
    
    asyncio.run(main()) 