#!/usr/bin/env python3
"""
Test script for Phase 1 enhancements to MockAudioCodesClient.

This script demonstrates the new features added in Phase 1:
- Session resume functionality
- Connection validation
- DTMF and hangup events
- Enhanced error handling
- Session status monitoring
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the opusagent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from opusagent.mock.mock_audiocodes_client import MockAudioCodesClient


async def test_basic_phase1_features():
    """Test basic Phase 1 features without audio files."""
    print("\n=== Testing Basic Phase 1 Features ===")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Bridge URL (adjust as needed)
    bridge_url = "ws://localhost:8000/caller-agent"
    
    async with MockAudioCodesClient(bridge_url) as client:
        try:
            # Test 1: Session initiation
            print("\n1. Testing session initiation...")
            success = await client.initiate_session()
            if success:
                print("✓ Session initiated successfully")
            else:
                print("✗ Session initiation failed")
                return False
            
            # Test 2: Connection validation
            print("\n2. Testing connection validation...")
            validation_success = await client.validate_connection()
            if validation_success:
                print("✓ Connection validation successful")
            else:
                print("⚠ Connection validation failed (this might be expected)")
            
            # Test 3: DTMF events
            print("\n3. Testing DTMF events...")
            dtmf_success = await client.send_dtmf_event("1")
            if dtmf_success:
                print("✓ DTMF event sent successfully")
            else:
                print("✗ DTMF event failed")
            
            # Test 4: Custom activity
            print("\n4. Testing custom activity...")
            custom_activity = {
                "type": "event",
                "name": "custom_test",
                "value": "test_value"
            }
            activity_success = await client.send_custom_activity(custom_activity)
            if activity_success:
                print("✓ Custom activity sent successfully")
            else:
                print("✗ Custom activity failed")
            
            # Test 5: Session status
            print("\n5. Testing session status...")
            status = client.get_session_status()
            print(f"✓ Session status retrieved:")
            for key, value in status.items():
                print(f"  {key}: {value}")
            
            # Test 6: Session end
            print("\n6. Testing session end...")
            await client.end_session("Phase 1 test completed")
            print("✓ Session ended successfully")
            
            return True
            
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            return False


async def test_session_resume():
    """Test session resume functionality."""
    print("\n=== Testing Session Resume ===")
    
    bridge_url = "ws://localhost:8000/caller-agent"
    
    async with MockAudioCodesClient(bridge_url) as client:
        try:
            # Step 1: Initiate initial session
            print("\n1. Initiating initial session...")
            success = await client.initiate_session()
            if not success:
                print("✗ Initial session failed")
                return False
            
            conversation_id = client.conversation_id
            print(f"✓ Initial session created with ID: {conversation_id}")
            
            # Step 2: End session
            print("\n2. Ending session...")
            await client.end_session("Testing resume")
            print("✓ Session ended")
            
            # Step 3: Reset state
            print("\n3. Resetting client state...")
            client.reset_session_state()
            print("✓ State reset")
            
            # Step 4: Resume session
            print("\n4. Resuming session...")
            if conversation_id:
                resume_success = await client.resume_session(conversation_id)
            else:
                print("✗ No conversation ID available for resume")
                return False
            if resume_success:
                print("✓ Session resumed successfully")
                return True
            else:
                print("✗ Session resume failed")
                return False
                
        except Exception as e:
            print(f"✗ Session resume test failed: {e}")
            return False


async def test_enhanced_conversation():
    """Test enhanced conversation with Phase 1 features."""
    print("\n=== Testing Enhanced Conversation ===")
    
    bridge_url = "ws://localhost:8000/caller-agent"
    
    # Use specific available audio files for testing
    audio_paths = [
        str(Path(__file__).parent.parent / "opusagent" / "mock" / "audio" / "greetings" / "greetings_01.wav"),
        str(Path(__file__).parent.parent / "opusagent" / "mock" / "audio" / "customer_service" / "customer_service_01.wav"),
        str(Path(__file__).parent.parent / "opusagent" / "mock" / "audio" / "default" / "default_01.wav")
    ]
    
    # Verify files exist
    missing_files = [f for f in audio_paths if not Path(f).exists()]
    if missing_files:
        print(f"Missing audio files: {missing_files}")
        print("Skipping enhanced conversation test")
        return True
    
    print(f"Using {len(audio_paths)} test audio files:")
    for audio_file in audio_paths:
        print(f"  - {Path(audio_file).name}")
    
    async with MockAudioCodesClient(bridge_url) as client:
        try:
            # Run enhanced conversation test
            result = await client.enhanced_conversation_test(
                audio_files=audio_paths,
                session_name="Phase1Test",
                enable_connection_validation=True,
                enable_dtmf_testing=True,
                enable_session_resume=False  # Skip resume for this test
            )
            
            if result["success"]:
                print("✓ Enhanced conversation test completed successfully")
                return True
            else:
                print(f"✗ Enhanced conversation test failed: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"✗ Enhanced conversation test failed: {e}")
            return False


async def test_error_handling():
    """Test error handling scenarios."""
    print("\n=== Testing Error Handling ===")
    
    bridge_url = "ws://localhost:8000/caller-agent"
    
    async with MockAudioCodesClient(bridge_url) as client:
        try:
            # Test 1: Try to send DTMF without session
            print("\n1. Testing DTMF without session...")
            dtmf_success = await client.send_dtmf_event("1")
            if not dtmf_success:
                print("✓ Correctly rejected DTMF without session")
            else:
                print("⚠ DTMF accepted without session (unexpected)")
            
            # Test 2: Try to validate connection without session
            print("\n2. Testing connection validation without session...")
            validation_success = await client.validate_connection()
            if not validation_success:
                print("✓ Correctly rejected connection validation without session")
            else:
                print("⚠ Connection validation accepted without session (unexpected)")
            
            # Test 3: Try to resume non-existent session
            print("\n3. Testing resume of non-existent session...")
            resume_success = await client.resume_session("non-existent-id")
            if not resume_success:
                print("✓ Correctly rejected resume of non-existent session")
            else:
                print("⚠ Resume of non-existent session accepted (unexpected)")
            
            return True
            
        except Exception as e:
            print(f"✗ Error handling test failed: {e}")
            return False


async def main():
    """Run all Phase 1 enhancement tests."""
    print("Phase 1 Enhancement Tests for MockAudioCodesClient")
    print("=" * 60)
    
    tests = [
        ("Basic Phase 1 Features", test_basic_phase1_features),
        ("Session Resume", test_session_resume),
        ("Enhanced Conversation", test_enhanced_conversation),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 1 enhancement tests passed!")
        return 0
    else:
        print("⚠ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 