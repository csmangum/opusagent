#!/usr/bin/env python3
"""
Demo script for Local Realtime Bridge integration.

This script demonstrates how to use the local realtime client with the bridges
instead of connecting to the OpenAI Realtime API. This is useful for testing,
development, and scenarios where you want to avoid API costs or network dependencies.

Usage:
    # Basic demo with default configuration
    python scripts/demo_local_realtime_bridge.py

    # Demo with custom configuration
    USE_LOCAL_REALTIME=true LOCAL_REALTIME_ENABLE_TRANSCRIPTION=true python scripts/demo_local_realtime_bridge.py

    # Demo with custom VAD settings
    USE_LOCAL_REALTIME=true LOCAL_REALTIME_VAD_THRESHOLD=0.3 python scripts/demo_local_realtime_bridge.py
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path



# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opusagent.local.realtime import LocalRealtimeClient, LocalResponseConfig, ResponseSelectionCriteria


async def demo_local_realtime_bridge():
    """Demonstrate local realtime bridge functionality."""
    print("🚀 Local Realtime Bridge Demo")
    print("=" * 50)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("demo")
    
    # Check if local realtime is enabled
    use_local_realtime = os.getenv("USE_LOCAL_REALTIME", "false").lower() in ("true", "1", "yes", "on")
    
    if not use_local_realtime:
        print("❌ Local realtime is not enabled.")
        print("Set USE_LOCAL_REALTIME=true to enable local realtime client.")
        print("\nExample:")
        print("  USE_LOCAL_REALTIME=true python scripts/demo_local_realtime_bridge.py")
        print("\nOr set it programmatically:")
        print("  os.environ['USE_LOCAL_REALTIME'] = 'true'")
        
        # Try to enable it programmatically for demo purposes
        print("\n🔧 Enabling local realtime programmatically for demo...")
        os.environ['USE_LOCAL_REALTIME'] = 'true'
        use_local_realtime = True
    
    print("✅ Local realtime is enabled")
    
    # Create a local realtime client with custom configuration
    print("\n🔧 Creating local realtime client...")
    
    # Custom response configurations
    custom_responses = {
        "greeting": LocalResponseConfig(
            text="Hello! Welcome to our local realtime demo. How can I help you today?",
            delay_seconds=0.02,
            selection_criteria=ResponseSelectionCriteria(
                required_keywords=["hello", "hi", "hey"],
                priority=20
            )
        ),
        "help": LocalResponseConfig(
            text="I'm here to help! This is a local realtime client demo. What would you like to know?",
            delay_seconds=0.03,
            selection_criteria=ResponseSelectionCriteria(
                required_keywords=["help", "assist", "support"],
                priority=15
            )
        ),
        "demo_info": LocalResponseConfig(
            text="This demo shows how the local realtime client works with the bridges. It simulates the OpenAI Realtime API without requiring an internet connection or API key.",
            delay_seconds=0.05,
            selection_criteria=ResponseSelectionCriteria(
                required_keywords=["demo", "local", "realtime"],
                priority=10
            )
        )
    }
    
    # Local realtime configuration
    local_config = {
        "enable_transcription": os.getenv("LOCAL_REALTIME_ENABLE_TRANSCRIPTION", "false").lower() in ("true", "1", "yes", "on"),
        "setup_smart_responses": True,
        "response_configs": custom_responses,
        "vad_config": {
            "backend": os.getenv("LOCAL_REALTIME_VAD_BACKEND", "silero"),
            "threshold": float(os.getenv("LOCAL_REALTIME_VAD_THRESHOLD", "0.5")),
            "sample_rate": int(os.getenv("LOCAL_REALTIME_VAD_SAMPLE_RATE", "16000")),
        },
        "transcription_config": {
            "backend": os.getenv("LOCAL_REALTIME_TRANSCRIPTION_BACKEND", "pocketsphinx"),
            "language": os.getenv("LOCAL_REALTIME_TRANSCRIPTION_LANGUAGE", "en"),
            "model_size": os.getenv("LOCAL_REALTIME_TRANSCRIPTION_MODEL_SIZE", "base"),
        }
    }
    
    # Create a serializable version of the config for display
    display_config = {
        "enable_transcription": local_config["enable_transcription"],
        "setup_smart_responses": local_config["setup_smart_responses"],
        "response_configs": {
            key: {
                "text": config.text,
                "delay_seconds": config.delay_seconds,
                "selection_criteria": {
                    "required_keywords": config.selection_criteria.required_keywords if config.selection_criteria else [],
                    "priority": config.selection_criteria.priority if config.selection_criteria else 0
                } if config.selection_criteria else None
            }
            for key, config in local_config["response_configs"].items()
        },
        "vad_config": local_config["vad_config"],
        "transcription_config": local_config["transcription_config"]
    }
    
    print(f"📋 Configuration: {json.dumps(display_config, indent=2)}")
    
    try:
        # Create local realtime client
        client = LocalRealtimeClient(
            logger=logger,
            enable_vad=True,
            vad_config=local_config["vad_config"],
            enable_transcription=local_config["enable_transcription"],
            transcription_config=local_config["transcription_config"],
            response_configs=local_config["response_configs"],
        )
        
        print("✅ Local realtime client created successfully")
        
        # Connect to mock server (optional)
        try:
            # Try connecting to the caller-agent endpoint which is designed for testing
            await client.connect("ws://localhost:8000/caller-agent")
            print("✅ Connected to mock server at /caller-agent endpoint")
        except Exception as e:
            print(f"⚠️  Could not connect to mock server: {e}")
            print("   (This is normal if no mock server is running)")
            print("   Available endpoints:")
            print("     - /ws/telephony (AudioCodes bridge)")
            print("     - /caller-agent (Caller agent bridge)")
            print("     - /twilio-agent (Twilio bridge)")
            print("     - /agent-conversation (Dual agent conversations)")
        
        # Demo conversation simulation
        print("\n💬 Simulating conversation...")
        
        # Test different conversation scenarios
        test_inputs = [
            "Hello there!",
            "Can you help me with something?",
            "Tell me about this demo",
            "What is local realtime?",
            "Thank you for your help"
        ]
        
        for i, user_input in enumerate(test_inputs, 1):
            print(f"\n--- Turn {i} ---")
            print(f"User: {user_input}")
            
            # Update conversation context
            client.update_conversation_context(user_input)
            
            # Simulate response generation
            await asyncio.sleep(0.1)  # Simulate processing time
            
            # Get session state to see what happened
            session_state = client.get_session_state()
            context = session_state.get("conversation_context")
            
            if context:
                print(f"Detected intents: {context.detected_intents}")
                print(f"Turn count: {context.turn_count}")
            
            # Get response timing metrics
            timings = client.get_response_timings()
            if timings:
                latest = timings[-1]
                print(f"Latest response: {latest.get('response_key', 'unknown')} in {latest.get('duration', 0):.3f}s")
        
        # Show VAD state if enabled
        if client.is_vad_enabled():
            vad_state = client.get_vad_state()
            print(f"\n🎤 VAD State: {json.dumps(vad_state, indent=2)}")
        
        # Show transcription state if enabled
        if client.is_transcription_enabled():
            transcription_state = client.get_transcription_state()
            print(f"\n📝 Transcription State: {json.dumps(transcription_state, indent=2)}")
        
        # Show performance metrics
        timings = client.get_response_timings()
        if timings:
            print(f"\n📊 Performance Metrics:")
            avg_duration = sum(t['duration'] for t in timings) / len(timings)
            print(f"  Average response time: {avg_duration:.3f}s")
            print(f"  Total responses: {len(timings)}")
        
        print("\n✅ Demo completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        logger.error(f"Demo error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up
        if 'client' in locals():
            try:
                await client.disconnect()
                print("🔌 Local realtime client disconnected")
            except Exception as e:
                print(f"⚠️  Error disconnecting client: {e}")


async def demo_bridge_integration():
    """Demonstrate how the local realtime client integrates with bridges."""
    print("\n🌉 Bridge Integration Demo")
    print("=" * 50)
    
    print("This demo shows how the local realtime client integrates with the bridges:")
    print("1. BaseRealtimeBridge supports use_local_realtime parameter")
    print("2. Local realtime client is initialized when use_local_realtime=True")
    print("3. Bridges can use either OpenAI API or local client transparently")
    print("4. All bridge functionality works the same regardless of backend")
    
    print("\n📋 Environment Variables for Bridge Integration:")
    print("  USE_LOCAL_REALTIME=true                    # Enable local realtime")
    print("  LOCAL_REALTIME_ENABLE_TRANSCRIPTION=true   # Enable transcription")
    print("  LOCAL_REALTIME_VAD_THRESHOLD=0.3          # Adjust VAD sensitivity")
    print("  LOCAL_REALTIME_SETUP_SMART_RESPONSES=true # Use smart responses")
    
    print("\n🔗 WebSocket Endpoints that support local realtime:")
    print("  /ws/telephony     - AudioCodes bridge")
    print("  /caller-agent     - Caller agent bridge")
    print("  /twilio-agent     - Twilio bridge")
    
    print("\n💡 Usage Examples:")
    print("  # Start server with local realtime")
    print("  USE_LOCAL_REALTIME=true python opusagent/main.py")
    print("")
    print("  # Test with local VAD client")
    print("  python scripts/test_local_vad.py")
    print("")
    print("  # Test with mock telephony client")
    print("  python scripts/validate_telephony_mock.py")


def test_bridge_imports():
    """Test that bridge imports work with new parameters."""
    print("\n🔧 Testing bridge imports...")
    
    try:
        from opusagent.bridges.base_bridge import BaseRealtimeBridge
        from opusagent.bridges.audiocodes_bridge import AudioCodesBridge
        from opusagent.bridges.twilio_bridge import TwilioBridge
        from opusagent.bridges.call_agent_bridge import CallAgentBridge
        from opusagent.models.openai_api import SessionConfig
        
        print("✅ All bridge imports successful")
        
        # Test that we can create a session config
        session_config = SessionConfig(
            model="gpt-4o-realtime-preview-2025-06-03",
            modalities=["text", "audio"],
            voice="alloy",
        )
        print("✅ SessionConfig creation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Bridge import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main demo function."""
    print("🎯 Local Realtime Bridge Integration Demo")
    print("=" * 60)
    
    # Test bridge imports first
    if not test_bridge_imports():
        print("\n❌ Bridge import test failed. Cannot continue.")
        sys.exit(1)
    
    # Run the demos
    success = asyncio.run(demo_local_realtime_bridge())
    asyncio.run(demo_bridge_integration())
    
    if success:
        print("\n🎉 All demos completed successfully!")
        print("\nNext steps:")
        print("1. Start the server with local realtime: USE_LOCAL_REALTIME=true python opusagent/main.py")
        print("2. Test with a client: python scripts/test_local_vad.py")
        print("3. Check the API docs: curl http://localhost:8000/")
    else:
        print("\n❌ Demo failed. Check the logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main() 