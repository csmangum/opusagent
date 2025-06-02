#!/usr/bin/env python3
"""
Test script for Phase 2 implementation of the TUI Validator.

This script validates that the basic components and session management
are working correctly.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Test imports
try:
    print("Testing imports...")
    
    # Test WebSocket components
    from tui.websocket.client import WebSocketClient
    from tui.websocket.message_handler import MessageHandler, SessionMessageBuilder
    print("✓ WebSocket components imported successfully")
    
    # Test models
    from tui.models.session_state import SessionState, SessionStatus, StreamStatus
    from tui.models.event_logger import EventLogger, EventLevel, EventCategory
    print("✓ Models imported successfully")
    
    # Test configuration
    from tui.utils.config import TUIConfig
    print("✓ Configuration imported successfully")
    
    # Test UI components
    from tui.components.connection_panel import ConnectionPanel
    from tui.components.events_panel import EventsPanel
    print("✓ UI components imported successfully")
    
    print("✓ All imports successful!")
    
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

async def test_session_management():
    """Test session state management."""
    print("\nTesting session management...")
    
    try:
        # Test session state
        session = SessionState()
        assert session.status == SessionStatus.IDLE
        
        # Test session initiation
        conv_id = session.initiate_session("test-bot", "test-caller")
        assert session.status == SessionStatus.INITIATING
        assert session.conversation_id == conv_id
        
        # Test session acceptance
        session.accept_session("test-session-123")
        assert session.status == SessionStatus.ACTIVE
        assert session.is_active
        
        # Test session end
        session.end_session()
        assert session.status == SessionStatus.ENDED
        assert not session.is_active
        
        print("✓ Session management tests passed")
        
    except Exception as e:
        print(f"❌ Session management test failed: {e}")
        return False
    
    return True

async def test_event_logging():
    """Test event logging functionality."""
    print("\nTesting event logging...")
    
    try:
        # Test event logger
        logger = EventLogger(max_events=100)
        
        # Test logging events
        logger.log_connection_event("test_connect", "Test connection", EventLevel.INFO)
        logger.log_session_event("test_session", "Test session", EventLevel.INFO)
        logger.log_error_event("test_error", "Test error", {"error": "test"})
        
        assert len(logger.events) == 3
        
        # Test filtering
        error_events = logger.get_error_events()
        assert len(error_events) == 1
        assert error_events[0].event_type == "test_error"
        
        # Test statistics
        stats = logger.get_statistics()
        assert stats["total_events"] == 3
        assert stats["level_counts"]["error"] == 1
        
        print("✓ Event logging tests passed")
        
    except Exception as e:
        print(f"❌ Event logging test failed: {e}")
        return False
    
    return True

async def test_websocket_client():
    """Test WebSocket client functionality."""
    print("\nTesting WebSocket client...")
    
    try:
        # Test WebSocket client creation
        client = WebSocketClient(
            max_reconnect_attempts=3,
            reconnect_delay=1.0,
            connection_timeout=5.0
        )
        
        assert not client.connected
        assert not client.connecting
        
        # Test connection stats
        stats = client.get_connection_stats()
        assert "connected" in stats
        assert "reconnect_attempts" in stats
        
        print("✓ WebSocket client tests passed")
        
    except Exception as e:
        print(f"❌ WebSocket client test failed: {e}")
        return False
    
    return True

async def test_message_handler():
    """Test message handler functionality."""
    print("\nTesting message handler...")
    
    try:
        # Test message handler
        handler = MessageHandler()
        
        # Test message building
        conv_id = "test-conversation-123"
        
        session_msg = SessionMessageBuilder.create_session_initiate(
            conversation_id=conv_id,
            bot_name="test-bot"
        )
        
        assert session_msg["type"] == "session.initiate"
        assert session_msg["conversationId"] == conv_id
        assert session_msg["botName"] == "test-bot"
        
        end_msg = SessionMessageBuilder.create_session_end(conv_id)
        assert end_msg["type"] == "session.end"
        assert end_msg["conversationId"] == conv_id
        
        print("✓ Message handler tests passed")
        
    except Exception as e:
        print(f"❌ Message handler test failed: {e}")
        return False
    
    return True

async def test_configuration():
    """Test configuration management."""
    print("\nTesting configuration...")
    
    try:
        # Test configuration
        config = TUIConfig()
        
        assert config.host == "localhost"
        assert config.port == 8000
        assert config.ws_path == "/voice-bot"
        
        # Test URL generation
        assert config.ws_url == "ws://localhost:8000/voice-bot"
        
        # Test validation
        assert config.is_valid()
        
        # Test dictionary conversion
        config_dict = config.to_dict()
        assert "host" in config_dict
        assert "ws_url" in config_dict
        
        print("✓ Configuration tests passed")
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False
    
    return True

async def test_integration():
    """Test component integration."""
    print("\nTesting component integration...")
    
    try:
        # Test integration of components
        session = SessionState()
        logger = EventLogger()
        handler = MessageHandler()
        
        # Setup event logger callback
        events_received = []
        def on_event(event):
            events_received.append(event)
        
        logger.add_event_handler(on_event)
        
        # Log an event
        logger.log_session_event("integration_test", "Integration test event")
        
        # Check event was received
        assert len(events_received) == 1
        assert events_received[0].event_type == "integration_test"
        
        print("✓ Integration tests passed")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False
    
    return True

async def main():
    """Run all tests."""
    print("🚀 Starting Phase 2 validation tests...\n")
    
    tests = [
        test_configuration,
        test_session_management,
        test_event_logging,
        test_websocket_client,
        test_message_handler,
        test_integration,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 2 tests passed! Implementation is ready.")
        return True
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        sys.exit(1) 