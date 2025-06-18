#!/usr/bin/env python3
"""
Test script for the Call Review Interface implementation.

This script verifies that the core components can be imported and
instantiated without errors.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_imports():
    """Test that all components can be imported."""
    print("Testing imports...")
    
    try:
        from tui.models.review_session import (
            ReviewSession, CallMetadata, TranscriptEntry, 
            LogEntry, FunctionCall, StateTransition
        )
        print("✅ Review session models imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import review session models: {e}")
        return False
    
    try:
        from tui.models.review_session_loader import ReviewSessionLoader
        print("✅ Review session loader imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import review session loader: {e}")
        return False
    
    # Test optional textual imports (may not be available in all environments)
    try:
        from tui.components.metadata_panel import MetadataPanel
        from tui.components.state_timeline_panel import StateTimelinePanel
        from tui.components.search_filter_box import SearchFilterBox
        print("✅ TUI components imported successfully")
    except ImportError as e:
        print(f"⚠️  TUI components not available (textual dependency): {e}")
        # This is OK - textual may not be installed
    
    return True


def test_review_session():
    """Test ReviewSession functionality."""
    print("\nTesting ReviewSession...")
    
    try:
        from tui.models.review_session import ReviewSession, CallMetadata
        
        # Create a test session
        session = ReviewSession("test_call_001")
        
        # Test metadata
        session.metadata = CallMetadata(
            call_id="test_call_001",
            caller_number="+1-555-0123",
            scenario="Test Scenario",
            duration_seconds=120.0,
            result="Success"
        )
        
        print(f"✅ Created session: {session.call_id}")
        print(f"✅ Duration string: {session.metadata.get_duration_str()}")
        
        # Test filtering
        session.apply_filter("test")
        print("✅ Filter applied successfully")
        
        # Test seeking
        session.seek_to_timestamp(30.0)
        print(f"✅ Seek to timestamp: {session.current_timestamp}")
        
        return True
        
    except Exception as e:
        print(f"❌ ReviewSession test failed: {e}")
        return False


def test_session_loader():
    """Test ReviewSessionLoader functionality."""
    print("\nTesting ReviewSessionLoader...")
    
    try:
        from tui.models.review_session_loader import ReviewSessionLoader
        
        loader = ReviewSessionLoader()
        
        # Test finding sessions
        sessions = loader.find_available_sessions()
        print(f"✅ Found {len(sessions)} available sessions")
        
        # Test demo session creation
        demo_session = loader.create_demo_session()
        if demo_session:
            print(f"✅ Created demo session: {demo_session.call_id}")
            print(f"   - Transcript entries: {len(demo_session.transcript)}")
            print(f"   - Function calls: {len(demo_session.function_calls)}")
            print(f"   - Log entries: {len(demo_session.logs)}")
            print(f"   - State transitions: {len(demo_session.state_transitions)}")
        else:
            print("❌ Failed to create demo session")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ ReviewSessionLoader test failed: {e}")
        return False


def test_data_structures():
    """Test the data structure classes."""
    print("\nTesting data structures...")
    
    try:
        from tui.models.review_session import (
            TranscriptEntry, LogEntry, FunctionCall, StateTransition
        )
        
        # Test TranscriptEntry
        transcript = TranscriptEntry(
            timestamp=10.5,
            speaker="user",
            text="Hello, I need help with my account"
        )
        print(f"✅ TranscriptEntry: {transcript.get_time_str()} - {transcript.speaker}")
        
        # Test LogEntry
        log = LogEntry(
            timestamp=15.2,
            level="INFO",
            module="session",
            message="User request processed"
        )
        print(f"✅ LogEntry: {log.get_time_str()} - {log.level}")
        
        # Test FunctionCall
        func_call = FunctionCall(
            timestamp=20.0,
            function_name="lookup_account",
            arguments={"account_number": "12345"},
            result={"status": "success"}
        )
        print(f"✅ FunctionCall: {func_call.get_time_str()} - {func_call.function_name}")
        
        # Test StateTransition
        transition = StateTransition(
            timestamp=25.0,
            from_state="listening",
            to_state="processing",
            trigger="user_input"
        )
        print(f"✅ StateTransition: {transition.get_time_str()} - {transition.from_state} → {transition.to_state}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data structures test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Call Review Interface - Implementation Test")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 4
    
    if test_imports():
        tests_passed += 1
    
    if test_data_structures():
        tests_passed += 1
    
    if test_review_session():
        tests_passed += 1
    
    if test_session_loader():
        tests_passed += 1
    
    print("\n" + "=" * 50)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Call Review Interface implementation is working.")
        print("\nTo try the interface:")
        print("1. Run: python tui/review_main.py --demo")
        print("2. Or from main TUI: press Ctrl+M")
    else:
        print("❌ Some tests failed. Check the implementation.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())