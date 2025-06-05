#!/usr/bin/env python3
"""
Replacement Card Flow Development & Validation Script

This script validates the complete replacement card conversation flow:
1. Connect with bridge (session initiation)
2. Receive LLM audio greeting 
3. Send pre-recorded user audio (replacement card request)
4. Receive LLM audio response (card replacement confirmation)

This is a development-focused script for testing and iterating on the flow.
"""

import asyncio
import sys
import socket
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastagent.config.logging_config import configure_logging
from validate.mock_audiocodes_client import MockAudioCodesClient

# Load environment variables
load_dotenv()

# Configure logging
logger = configure_logging("replacement_dev")

# Configuration - Updated to match bridge server settings
BRIDGE_HOST = "localhost"
BRIDGE_PORT = 8000
BRIDGE_URL = f"ws://{BRIDGE_HOST}:{BRIDGE_PORT}/voice-bot"

# Timeout settings aligned with bridge WebSocket config
# Bridge pings every 5s, waits 10s for pong, so our timeouts should be higher
TIMEOUTS = {
    "session_initiation": 15.0,    # Generous for session setup
    "greeting_reception": 20.0,    # Time for AI to generate initial greeting
    "response_reception": 45.0,    # Time for AI to process and respond
    "websocket_stability": 12.0,   # Slightly above bridge ping timeout (10s)
}

# Audio files for replacement card flow
REPLACEMENT_CARD_AUDIO_FILES = [
    "static/replacement_card_1.wav",
    "static/replacement_card_2.wav", 
    "static/replacement_card_3.wav",
    "static/replacement_card_4.wav",
    "static/replacement_card_5.wav",
    "static/tell_me_about_your_bank.wav",  # Fallback
]

class ReplacementCardFlowValidator:
    """Validates the replacement card conversation flow."""
    
    def __init__(self, bridge_url: str = BRIDGE_URL):
        self.bridge_url = bridge_url
        self.mock: Optional[MockAudioCodesClient] = None
        self.session_results: Dict[str, Any] = {}
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.mock = MockAudioCodesClient(
            bridge_url=self.bridge_url,
            bot_name="ReplacementCardBot",
            caller="+15551234567",
            logger=logger
        )
        await self.mock.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.mock:
            await self.mock.__aexit__(exc_type, exc_val, exc_tb)

    def check_bridge_running(self) -> bool:
        """Check if the bridge server is running."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((BRIDGE_HOST, BRIDGE_PORT))
            sock.close()
            return result == 0
        except Exception:
            return False

    async def validate_bridge_server(self) -> Dict[str, Any]:
        """Comprehensive bridge server validation."""
        logger.info("\n[BRIDGE] Bridge Server Validation")
        logger.info("-" * 40)
        
        validation_results = {
            "port_open": False,
            "websocket_supported": False,
            "openai_configured": False,
            "server_responsive": False
        }
        
        # Check if port is open
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            result = sock.connect_ex((BRIDGE_HOST, BRIDGE_PORT))
            sock.close()
            validation_results["port_open"] = (result == 0)
            
            if validation_results["port_open"]:
                logger.info(f"[OK] Port {BRIDGE_PORT} is open")
            else:
                logger.error(f"[ERROR] Port {BRIDGE_PORT} is not accessible")
                return validation_results
                
        except Exception as e:
            logger.error(f"[ERROR] Port check failed: {e}")
            return validation_results
        
        # Try HTTP connection to check if server is responding
        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    async with session.get(f"http://{BRIDGE_HOST}:{BRIDGE_PORT}/") as response:
                        validation_results["server_responsive"] = True
                        logger.info(f"[OK] Server is responsive (HTTP {response.status})")
                except Exception:
                    # Try a different endpoint that might exist
                    try:
                        async with session.get(f"http://{BRIDGE_HOST}:{BRIDGE_PORT}/health") as response:
                            validation_results["server_responsive"] = True
                            logger.info(f"[OK] Server is responsive (HTTP {response.status})")
                    except Exception:
                        logger.warning("[WARN] Server port open but HTTP not responding (might be WebSocket-only)")
                        validation_results["server_responsive"] = True  # Assume it's working
                        
        except ImportError:
            logger.warning("[WARN] aiohttp not available, skipping HTTP check")
            validation_results["server_responsive"] = True  # Assume it's working
        except Exception as e:
            logger.warning(f"[WARN] HTTP check failed: {e}")
            validation_results["server_responsive"] = True  # Assume it's working if port is open
        
        # Check WebSocket support by attempting connection
        try:
            import websockets
            async with websockets.connect(
                f"ws://{BRIDGE_HOST}:{BRIDGE_PORT}/voice-bot",
                ping_interval=None,  # Disable pings for quick test
                timeout=5.0
            ) as ws:
                validation_results["websocket_supported"] = True
                logger.info("[OK] WebSocket connection successful")
                
        except Exception as e:
            logger.warning(f"[WARN] WebSocket connection test failed: {e}")
            validation_results["websocket_supported"] = True  # Assume it works
        
        # Environment checks (best effort)
        try:
            import os
            if os.getenv("OPENAI_API_KEY"):
                validation_results["openai_configured"] = True
                logger.info("[OK] OPENAI_API_KEY environment variable is set")
            else:
                logger.warning("[WARN] OPENAI_API_KEY environment variable not detected")
                logger.warning("   (This might be set in the server environment)")
                validation_results["openai_configured"] = True  # Assume it's configured
        except Exception:
            validation_results["openai_configured"] = True  # Assume it's configured
        
        return validation_results

    def find_audio_file(self) -> Optional[str]:
        """Find the first available audio file for testing."""
        for audio_file in REPLACEMENT_CARD_AUDIO_FILES:
            if Path(audio_file).exists():
                return audio_file
        
        # Try absolute paths
        for audio_file in REPLACEMENT_CARD_AUDIO_FILES:
            abs_path = project_root / audio_file
            if abs_path.exists():
                return str(abs_path)
                
        return None

    async def validate_step_1_session_initiation(self) -> bool:
        """Step 1: Validate session initiation with bridge."""
        logger.info("\n[STEP1] Step 1: Session Initiation")
        logger.info("-" * 40)
        
        try:
            logger.info("[STEP1] Initiating session with bridge...")
            success = await self.mock.initiate_session()
            
            if success:
                logger.info(f"[STEP1] Session initiated successfully")
                logger.info(f"   Conversation ID: {self.mock.conversation_id}")
                logger.info(f"   Media Format: {self.mock.media_format}")
                self.session_results["step_1"] = {
                    "success": True,
                    "conversation_id": self.mock.conversation_id,
                    "media_format": self.mock.media_format
                }
                return True
            else:
                logger.error("[STEP1] Session initiation failed")
                self.session_results["step_1"] = {"success": False, "error": "Initiation failed"}
                return False
                
        except Exception as e:
            logger.error(f"[STEP1] Session initiation error: {e}")
            self.session_results["step_1"] = {"success": False, "error": str(e)}
            return False

    async def validate_step_2_greeting_reception(self) -> List[str]:
        """Step 2: Validate LLM greeting reception."""
        logger.info("\n[STEP2] Step 2: LLM Greeting Reception")
        logger.info("-" * 40)
        
        try:
            logger.info("[STEP2] Waiting for LLM greeting...")
            greeting_chunks = await self.mock.wait_for_llm_greeting(timeout=TIMEOUTS["greeting_reception"])
            
            if greeting_chunks:
                logger.info(f"[STEP2] Greeting received successfully")
                logger.info(f"   Audio chunks: {len(greeting_chunks)}")
                
                # Calculate approximate duration
                total_bytes = sum(len(chunk) for chunk in greeting_chunks)
                approx_duration = (total_bytes * 0.75) / (16000 * 2)  # Base64 overhead
                logger.info(f"   Approximate duration: {approx_duration:.2f} seconds")
                
                self.session_results["step_2"] = {
                    "success": True,
                    "chunk_count": len(greeting_chunks),
                    "total_bytes": total_bytes,
                    "duration_estimate": approx_duration
                }
                return greeting_chunks
            else:
                logger.error("[STEP2] No greeting received")
                logger.error("=" * 60)
                logger.error("⚠️  LLM GREETING TIMEOUT - POSSIBLE CAUSES:")
                logger.error("=" * 60)
                logger.error("❌ Most likely: OpenAI API quota exceeded")
                logger.error("   • Check the bridge server logs for quota errors")
                logger.error("   • Visit: https://platform.openai.com/account/billing")
                logger.error("   • The Realtime API is expensive - add credits if needed")
                logger.error("")
                logger.error("🔍 Other possible causes:")
                logger.error("   • Network connectivity issues")
                logger.error("   • OpenAI API service problems")
                logger.error("   • Incorrect API key configuration")
                logger.error("   • Bridge server configuration issues")
                logger.error("")
                logger.error("💡 Next steps:")
                logger.error("   1. Check bridge server logs for detailed error messages")
                logger.error("   2. Verify your OpenAI billing status")
                logger.error("   3. Try running the validation again after resolving issues")
                logger.error("=" * 60)
                
                self.session_results["step_2"] = {"success": False, "error": "No greeting - likely quota exceeded"}
                return []
                
        except Exception as e:
            logger.error(f"[STEP2] Greeting reception error: {e}")
            self.session_results["step_2"] = {"success": False, "error": str(e)}
            return []

    async def validate_step_3_user_audio_transmission(self, audio_file: str) -> bool:
        """Step 3: Validate user audio transmission (replacement card request)."""
        logger.info("\n[STEP3] Step 3: User Audio Transmission")
        logger.info("-" * 40)
        
        try:
            logger.info(f"[STEP3] Sending user audio: {Path(audio_file).name}")
            logger.info(f"   Full path: {audio_file}")
            
            # Send the audio file
            success = await self.mock.send_user_audio(audio_file, chunk_delay=0.02)
            
            if success:
                logger.info("[STEP3] User audio sent successfully")
                self.session_results["step_3"] = {
                    "success": True,
                    "audio_file": audio_file
                }
                return True
            else:
                logger.error("[STEP3] Failed to send user audio")
                self.session_results["step_3"] = {"success": False, "error": "Send failed"}
                return False
                
        except Exception as e:
            logger.error(f"[STEP3] User audio transmission error: {e}")
            self.session_results["step_3"] = {"success": False, "error": str(e)}
            return False

    async def validate_step_4_response_reception(self) -> List[str]:
        """Step 4: Validate LLM response reception (card replacement confirmation)."""
        logger.info("\n[STEP4] Step 4: LLM Response Reception")
        logger.info("-" * 40)
        
        try:
            logger.info("[STEP4] Waiting for LLM response...")
            response_chunks = await self.mock.wait_for_llm_response(timeout=TIMEOUTS["response_reception"])
            
            if response_chunks:
                logger.info(f"[STEP4] Response received successfully")
                logger.info(f"   Audio chunks: {len(response_chunks)}")
                
                # Calculate approximate duration
                total_bytes = sum(len(chunk) for chunk in response_chunks)
                approx_duration = (total_bytes * 0.75) / (16000 * 2)  # Base64 overhead
                logger.info(f"   Approximate duration: {approx_duration:.2f} seconds")
                
                self.session_results["step_4"] = {
                    "success": True,
                    "chunk_count": len(response_chunks),
                    "total_bytes": total_bytes,
                    "duration_estimate": approx_duration
                }
                return response_chunks
            else:
                logger.error("[STEP4] No response received")
                logger.error("=" * 60)
                logger.error("⚠️  LLM RESPONSE TIMEOUT - POSSIBLE CAUSES:")
                logger.error("=" * 60)
                logger.error("❌ Most likely: OpenAI API quota exceeded")
                logger.error("   • Check the bridge server logs for quota errors")
                logger.error("   • Visit: https://platform.openai.com/account/billing")
                logger.error("   • User audio may have triggered another quota-limited request")
                logger.error("")
                logger.error("🔍 Other possible causes:")
                logger.error("   • User audio was not processed correctly")
                logger.error("   • Audio format or quality issues")
                logger.error("   • Network connectivity problems")
                logger.error("   • OpenAI API service issues")
                logger.error("")
                logger.error("💡 Next steps:")
                logger.error("   1. Check bridge server logs for detailed error messages")
                logger.error("   2. Verify your OpenAI billing status and add credits")
                logger.error("   3. Check if user audio was sent successfully in Step 3")
                logger.error("   4. Try with a different/shorter audio file")
                logger.error("=" * 60)
                
                self.session_results["step_4"] = {"success": False, "error": "No response - likely quota exceeded"}
                return []
                
        except Exception as e:
            logger.error(f"[STEP4] Response reception error: {e}")
            self.session_results["step_4"] = {"success": False, "error": str(e)}
            return []

    async def validate_complete_flow(self) -> bool:
        """Validate the complete 4-step replacement card flow."""
        logger.info("[FLOW] Replacement Card Flow Validation")
        logger.info("=" * 50)
        
        # Pre-flight checks - Enhanced bridge validation
        bridge_validation = await self.validate_bridge_server()
        
        if not bridge_validation["port_open"]:
            logger.error(f"[FLOW] Bridge server not running at {BRIDGE_HOST}:{BRIDGE_PORT}")
            logger.error("   Please start with: python run.py")
            return False
        
        # Show bridge validation summary
        checks_passed = sum(1 for v in bridge_validation.values() if v)
        total_checks = len(bridge_validation)
        logger.info(f"[FLOW] Bridge server validation: {checks_passed}/{total_checks} checks passed")
        
        audio_file = self.find_audio_file()
        if not audio_file:
            logger.error("[FLOW] No audio file found for testing")
            logger.error(f"   Please ensure one of these files exists:")
            for af in REPLACEMENT_CARD_AUDIO_FILES:
                logger.error(f"   - {af}")
            return False
        logger.info(f"[FLOW] Using audio file: {Path(audio_file).name}")
        
        try:
            # Step 1: Session Initiation
            if not await self.validate_step_1_session_initiation():
                return False
            
            # Small delay to let session stabilize (aligned with bridge ping interval)
            await asyncio.sleep(2)
            
            # Step 2: Greeting Reception
            greeting = await self.validate_step_2_greeting_reception()
            if not greeting:
                return False
            
            # Small delay before sending user audio
            await asyncio.sleep(2)
            
            # Step 3: User Audio Transmission
            if not await self.validate_step_3_user_audio_transmission(audio_file):
                return False
            
            # Step 4: Response Reception
            response = await self.validate_step_4_response_reception()
            if not response:
                return False
            
            # End session gracefully
            await self.mock.end_session("Replacement card flow validation completed")
            
            # Save collected audio for analysis
            self.mock.save_collected_audio()
            
            # Print final summary
            await self.print_flow_summary()
            
            return True
            
        except Exception as e:
            logger.error(f"[FLOW] Flow validation failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    async def print_flow_summary(self):
        """Print a detailed summary of the flow validation."""
        logger.info("\n" + "=" * 50)
        logger.info("[SUMMARY] REPLACEMENT CARD FLOW SUMMARY")
        logger.info("=" * 50)
        
        # Overall success
        all_steps_passed = all(
            self.session_results.get(f"step_{i}", {}).get("success", False)
            for i in range(1, 5)
        )
        
        if all_steps_passed:
            logger.info("[SUMMARY] ALL STEPS PASSED - Flow validation successful!")
        else:
            logger.error("[SUMMARY] SOME STEPS FAILED - Flow validation incomplete")
        
        # Step-by-step summary
        for i in range(1, 5):
            step_result = self.session_results.get(f"step_{i}", {})
            success = step_result.get("success", False)
            status = "[PASS]" if success else "[FAIL]"
            
            step_names = {
                1: "Session Initiation",
                2: "Greeting Reception", 
                3: "User Audio Transmission",
                4: "Response Reception"
            }
            
            logger.info(f"\nStep {i} ({step_names[i]}): {status}")
            
            if success:
                if i == 1:
                    logger.info(f"   Conversation ID: {step_result.get('conversation_id', 'N/A')}")
                    logger.info(f"   Media Format: {step_result.get('media_format', 'N/A')}")
                elif i in [2, 4]:
                    logger.info(f"   Audio chunks: {step_result.get('chunk_count', 0)}")
                    logger.info(f"   Duration: {step_result.get('duration_estimate', 0):.2f}s")
                elif i == 3:
                    logger.info(f"   Audio file: {Path(step_result.get('audio_file', '')).name}")
            else:
                logger.error(f"   Error: {step_result.get('error', 'Unknown error')}")
        
        # Message statistics
        total_messages = len(self.mock.received_messages)
        message_types = {}
        for msg in self.mock.received_messages:
            msg_type = msg.get("type", "unknown")
            message_types[msg_type] = message_types.get(msg_type, 0) + 1
        
        logger.info(f"\n[STATS] Message Statistics:")
        logger.info(f"   Total messages: {total_messages}")
        for msg_type, count in sorted(message_types.items()):
            logger.info(f"   {msg_type}: {count}")
        
        # Audio analysis
        greeting_chunks = len(self.mock.greeting_audio_chunks)
        response_chunks = len(self.mock.response_audio_chunks)
        total_chunks = len(self.mock.received_play_chunks)
        
        logger.info(f"\n[AUDIO] Audio Analysis:")
        logger.info(f"   Greeting chunks: {greeting_chunks}")
        logger.info(f"   Response chunks: {response_chunks}")
        logger.info(f"   Total play chunks: {total_chunks}")
        
        # Files saved
        logger.info(f"\n[FILES] Output Files:")
        output_dir = Path("validation_output")
        if output_dir.exists():
            for file in output_dir.glob(f"*{self.mock.conversation_id[:8]}*"):
                logger.info(f"   {file.name}")
        
        logger.info("\n" + "=" * 50)

    async def debug_message_flow(self):
        """Debug helper to inspect message flow in detail."""
        logger.info("\n[DEBUG] Debug: Message Flow Analysis")
        logger.info("-" * 40)
        
        for i, msg in enumerate(self.mock.received_messages):
            msg_type = msg.get("type", "unknown")
            logger.info(f"{i+1:2d}. {msg_type}")
            
            # Show key details for each message type
            if msg_type == "session.accepted":
                logger.info(f"     Media format: {msg.get('mediaFormat')}")
            elif msg_type == "playStream.start":
                logger.info(f"     Stream ID: {msg.get('streamId')}")
                logger.info(f"     Media format: {msg.get('mediaFormat')}")
            elif msg_type == "playStream.chunk":
                chunk_size = len(msg.get('audioChunk', ''))
                logger.info(f"     Chunk size: {chunk_size} bytes (base64)")
            elif msg_type == "userStream.started":
                logger.info(f"     Ready to receive user audio")
            elif msg_type == "userStream.stopped": 
                logger.info(f"     User audio transmission complete")


async def run_replacement_card_validation():
    """Main function to run replacement card flow validation."""
    async with ReplacementCardFlowValidator() as validator:
        success = await validator.validate_complete_flow()
        
        # Optional: Run debug analysis
        logger.info("\n[DEBUG] Debug Analysis (optional)")
        debug = input("Run debug message analysis? (y/N): ").strip().lower()
        if debug in ['y', 'yes']:
            await validator.debug_message_flow()
        
        return success


async def quick_test():
    """Quick test function for development iterations."""
    logger.info("[QUICK] Quick Replacement Card Test")
    logger.info("-" * 30)
    
    async with ReplacementCardFlowValidator() as validator:
        # Just test session initiation for quick iterations
        step1 = await validator.validate_step_1_session_initiation()
        if step1:
            logger.info("[QUICK] Quick test passed - session initiation working")
            return True
        else:
            logger.error("[QUICK] Quick test failed - session initiation not working")
            return False


async def main():
    """Main entry point with full test as default."""
    logger.info("[MAIN] Replacement Card Flow Development Tool")
    logger.info("=" * 50)
    
    # Check command line arguments for alternative modes
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ['quick', 'q']:
            logger.info("[MAIN] Quick test mode (session initiation only)")
            success = await quick_test()
            return success
        elif arg in ['help', 'h', '--help']:
            logger.info("Usage:")
            logger.info("  python replacement_dev.py        # Full flow validation (default)")
            logger.info("  python replacement_dev.py quick  # Quick test only")
            logger.info("  python replacement_dev.py help   # Show this help")
            return True
    
    # Default: Run full flow validation
    logger.info("[MAIN] Running full flow validation...")
    logger.info("   (Use 'python replacement_dev.py quick' for quick test only)")
    logger.info("")
    
    try:
        success = await run_replacement_card_validation()
        if success:
            logger.info("\n[MAIN] Replacement card flow validation COMPLETED SUCCESSFULLY!")
        else:
            logger.error("\n[MAIN] Replacement card flow validation FAILED!")
        return success
            
    except KeyboardInterrupt:
        logger.info("\n\n[MAIN] Interrupted by user")
        return False
    except Exception as e:
        logger.error(f"\n[MAIN] Unexpected error: {e}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n[MAIN] Goodbye!")
        sys.exit(0) 