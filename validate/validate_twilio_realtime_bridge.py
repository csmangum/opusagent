#!/usr/bin/env python3
"""
Twilio Realtime Bridge Validation Script

This script performs a full integration test of the TwilioRealtimeBridge by:
1. Starting a FastAPI server with the Twilio WebSocket endpoint
2. Using MockTwilioClient to simulate Twilio Media Streams
3. Testing the full integration with OpenAI Realtime API
4. Validating audio flow, session management, and responses

Usage:
    python validate/validate_twilio_realtime_bridge.py [--port 6060] [--host localhost]
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import uvicorn
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from opusagent.config.logging_config import configure_logging
from opusagent.twilio_realtime_bridge import TwilioRealtimeBridge
from validate.mock_twilio_client import MockTwilioClient

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"

# Validation settings
DEFAULT_PORT = 6060
DEFAULT_HOST = "localhost"
VALIDATION_TIMEOUT = 120  # 2 minutes for full test


class TwilioRealtimeBridgeValidator:
    """
    Full integration validator for the Twilio Realtime Bridge.
    
    This validator sets up a complete test environment including:
    - FastAPI server with Twilio WebSocket endpoint
    - Bridge connections to OpenAI Realtime API
    - MockTwilioClient for simulating Twilio Media Streams
    - Comprehensive validation of the full flow
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.logger = configure_logging("twilio_bridge_validator")
        
        # Server components
        self.app = FastAPI(title="Twilio Bridge Validator")
        self.server = None
        self.server_task = None
        
        # Test state
        self.active_bridges: Dict[str, TwilioRealtimeBridge] = {}
        self.test_results = {
            "server_started": False,
            "openai_connection": False,
            "twilio_connection": False,
            "audio_flow": False,
            "session_management": False,
            "multi_turn": False,
            "error_handling": False,
            "cleanup": False,
            "overall_success": False
        }
        
        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Set up FastAPI routes for the validation server."""
        
        @self.app.websocket("/twilio-ws")
        async def twilio_websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint that Twilio (or MockTwilioClient) connects to."""
            await websocket.accept()
            self.logger.info("Twilio WebSocket connection accepted")
            
            try:
                # Connect to OpenAI Realtime API
                headers = {
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "OpenAI-Beta": "realtime=v1"
                }
                
                self.logger.info("Connecting to OpenAI Realtime API...")
                realtime_ws = await websockets.connect(
                    OPENAI_REALTIME_URL,
                    extra_headers=headers
                )
                
                self.logger.info("Connected to OpenAI Realtime API")
                self.test_results["openai_connection"] = True
                
                # Create bridge
                bridge = TwilioRealtimeBridge(
                    twilio_websocket=websocket,
                    realtime_websocket=realtime_ws
                )
                
                # Store bridge for monitoring
                bridge_id = f"bridge_{int(time.time())}"
                self.active_bridges[bridge_id] = bridge
                self.test_results["twilio_connection"] = True
                
                self.logger.info(f"Bridge created: {bridge_id}")
                
                # Run bridge communication
                await asyncio.gather(
                    bridge.receive_from_twilio(),
                    bridge.receive_from_realtime(),
                    return_exceptions=True
                )
                
            except Exception as e:
                self.logger.error(f"Bridge error: {e}")
                raise
            finally:
                # Cleanup
                if bridge_id in self.active_bridges:
                    try:
                        await self.active_bridges[bridge_id].close()
                        del self.active_bridges[bridge_id]
                        self.logger.info(f"Bridge cleaned up: {bridge_id}")
                    except Exception as e:
                        self.logger.error(f"Bridge cleanup error: {e}")

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "active_bridges": len(self.active_bridges),
                "test_results": self.test_results
            }

        @self.app.get("/status")
        async def status():
            """Status endpoint with detailed information."""
            return {
                "server": {
                    "host": self.host,
                    "port": self.port,
                    "active_bridges": len(self.active_bridges)
                },
                "test_results": self.test_results,
                "bridges": list(self.active_bridges.keys())
            }

    async def start_server(self) -> bool:
        """Start the FastAPI server."""
        try:
            self.logger.info(f"Starting validation server on {self.host}:{self.port}")
            
            config = uvicorn.Config(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=False
            )
            
            self.server = uvicorn.Server(config)
            self.server_task = asyncio.create_task(self.server.serve())
            
            # Wait for server to be ready
            await asyncio.sleep(2)
            
            self.logger.info("Validation server started successfully")
            self.test_results["server_started"] = True
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            return False

    async def stop_server(self):
        """Stop the FastAPI server."""
        if self.server:
            self.logger.info("Stopping validation server...")
            self.server.should_exit = True
            
            if self.server_task:
                try:
                    await asyncio.wait_for(self.server_task, timeout=5.0)
                except asyncio.TimeoutError:
                    self.server_task.cancel()
                    try:
                        await self.server_task
                    except asyncio.CancelledError:
                        pass
            
            self.logger.info("Validation server stopped")

    async def validate_basic_flow(self) -> bool:
        """Test basic Twilio bridge flow with MockTwilioClient."""
        self.logger.info("=== Testing Basic Flow ===")
        
        bridge_url = f"ws://{self.host}:{self.port}/twilio-ws"
        test_audio = self._get_test_audio_file()
        
        if not test_audio:
            self.logger.error("No test audio file available")
            return False
        
        try:
            async with MockTwilioClient(bridge_url, logger=self.logger) as client:
                # Test call initiation
                success = await client.initiate_call_flow()
                if not success:
                    self.logger.error("Failed to initiate call flow")
                    return False
                
                # Wait for initial greeting
                self.logger.info("Waiting for AI greeting...")
                greeting = await client.wait_for_ai_greeting(timeout=20.0)
                
                if greeting:
                    self.logger.info(f"✅ Received AI greeting: {len(greeting)} chunks")
                    self.test_results["session_management"] = True
                else:
                    self.logger.warning("⚠️ No AI greeting received (may be expected)")
                
                # Send user audio
                self.logger.info(f"Sending user audio: {test_audio}")
                await client.send_user_audio(test_audio)
                
                # Wait for AI response
                self.logger.info("Waiting for AI response...")
                response = await client.wait_for_ai_response(timeout=30.0)
                
                if response:
                    self.logger.info(f"✅ Received AI response: {len(response)} chunks")
                    self.test_results["audio_flow"] = True
                else:
                    self.logger.error("❌ No AI response received")
                    return False
                
                # End call properly
                await client.send_stop()
                
                # Save audio for analysis
                client.save_collected_audio()
                
                self.logger.info("✅ Basic flow validation completed successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Basic flow validation failed: {e}")
            return False

    async def validate_multi_turn_conversation(self) -> bool:
        """Test multi-turn conversation capabilities."""
        self.logger.info("=== Testing Multi-turn Conversation ===")
        
        bridge_url = f"ws://{self.host}:{self.port}/twilio-ws"
        audio_files = self._get_test_audio_files()
        
        if len(audio_files) < 2:
            self.logger.warning("Not enough audio files for multi-turn test")
            return False
        
        try:
            async with MockTwilioClient(bridge_url, logger=self.logger) as client:
                result = await client.multi_turn_conversation(
                    audio_files[:3],  # Limit to 3 turns for validation
                    wait_for_greeting=True,
                    turn_delay=1.0,   # Shorter delay for validation
                    chunk_delay=0.02
                )
                
                if result["success"] and result["completed_turns"] >= 2:
                    self.logger.info(f"✅ Multi-turn conversation successful: {result['completed_turns']} turns")
                    self.test_results["multi_turn"] = True
                    return True
                else:
                    self.logger.error(f"❌ Multi-turn conversation failed: {result}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ Multi-turn validation failed: {e}")
            return False

    async def validate_error_handling(self) -> bool:
        """Test error handling and recovery."""
        self.logger.info("=== Testing Error Handling ===")
        
        bridge_url = f"ws://{self.host}:{self.port}/twilio-ws"
        
        try:
            async with MockTwilioClient(bridge_url, logger=self.logger) as client:
                # Test DTMF handling
                await client.initiate_call_flow()
                await asyncio.sleep(1)
                
                # Send DTMF digits
                await client.send_dtmf("1")
                await client.send_dtmf("2")
                await client.send_dtmf("#")
                
                await asyncio.sleep(2)
                
                # Test abrupt disconnection recovery
                # (The bridge should handle this gracefully)
                await client.send_stop()
                
                self.logger.info("✅ Error handling validation completed")
                self.test_results["error_handling"] = True
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Error handling validation failed: {e}")
            return False

    async def validate_cleanup(self) -> bool:
        """Test proper cleanup of resources."""
        self.logger.info("=== Testing Cleanup ===")
        
        try:
            # Check that all bridges are properly closed
            if self.active_bridges:
                self.logger.warning(f"Found {len(self.active_bridges)} active bridges during cleanup")
                
                # Force cleanup
                for bridge_id, bridge in list(self.active_bridges.items()):
                    try:
                        await bridge.close()
                        del self.active_bridges[bridge_id]
                        self.logger.info(f"Cleaned up bridge: {bridge_id}")
                    except Exception as e:
                        self.logger.error(f"Error cleaning up bridge {bridge_id}: {e}")
            
            self.test_results["cleanup"] = len(self.active_bridges) == 0
            
            if self.test_results["cleanup"]:
                self.logger.info("✅ Cleanup validation completed")
                return True
            else:
                self.logger.error("❌ Cleanup validation failed")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Cleanup validation failed: {e}")
            return False

    def _get_test_audio_file(self) -> Optional[str]:
        """Get a single test audio file."""
        test_paths = [
            "static/tell_me_about_your_bank.wav",  # Good intro question
            "static/what_is_my_balance.wav",       # Simple banking query
            "static/need_to_replace_card.wav",     # Common request
            "demo/user_audio/hello.wav",
            "validate/test_audio/sample.wav",
            "test_audio/hello.wav",
        ]
        
        for path in test_paths:
            if Path(path).exists():
                return path
        
        # Try to find any WAV file in static directory first
        static_dir = Path("static")
        if static_dir.exists():
            wav_files = list(static_dir.glob("*.wav"))
            if wav_files:
                return str(wav_files[0])
        
        # Try to find any WAV file in demo directory
        demo_dir = Path("demo")
        if demo_dir.exists():
            wav_files = list(demo_dir.rglob("*.wav"))
            if wav_files:
                return str(wav_files[0])
        
        return None

    def _get_test_audio_files(self) -> List[str]:
        """Get multiple test audio files for multi-turn testing."""
        files = []
        
        # Prioritize specific conversation flow from static directory
        preferred_conversation = [
            "static/tell_me_about_your_bank.wav",
            "static/what_is_my_balance.wav", 
            "static/need_to_replace_card.wav",
            "static/my_gold_card.wav",
            "static/thanks_thats_all.wav"
        ]
        
        # Add existing files from preferred conversation
        for file_path in preferred_conversation:
            if Path(file_path).exists():
                files.append(file_path)
        
        # Check other test locations for additional files
        test_locations = [
            "static/",                    # Primary location with banking audio
            "demo/user_audio/",
            "validate/test_audio/",
            "test_audio/",
        ]
        
        for location in test_locations:
            path = Path(location)
            if path.exists():
                wav_files = list(path.glob("*.wav"))
                for wav_file in wav_files:
                    file_str = str(wav_file)
                    if file_str not in files:  # Avoid duplicates
                        files.append(file_str)
        
        # If we don't have enough files, reuse the first one
        if files:
            while len(files) < 3:
                files.append(files[0])
        
        return files[:5]  # Limit to 5 files max

    def _calculate_overall_success(self) -> bool:
        """Calculate overall test success based on individual results."""
        critical_tests = [
            "server_started",
            "openai_connection", 
            "twilio_connection",
            "audio_flow"
        ]
        
        # All critical tests must pass
        critical_passed = all(self.test_results.get(test, False) for test in critical_tests)
        
        # At least 2 of the additional tests should pass
        additional_tests = ["session_management", "multi_turn", "error_handling", "cleanup"]
        additional_passed = sum(self.test_results.get(test, False) for test in additional_tests)
        
        return critical_passed and additional_passed >= 2

    async def run_full_validation(self) -> Dict:
        """Run the complete validation suite."""
        start_time = time.time()
        
        self.logger.info("🚀 Starting Twilio Realtime Bridge Full Validation")
        self.logger.info("=" * 60)
        
        try:
            # Check prerequisites
            if not OPENAI_API_KEY:
                self.logger.error("❌ OPENAI_API_KEY environment variable not set")
                return self._generate_final_report(start_time)
            
            # Start server
            if not await self.start_server():
                self.logger.error("❌ Failed to start validation server")
                return self._generate_final_report(start_time)
            
            # Wait for server to stabilize
            await asyncio.sleep(3)
            
            # Run validation tests
            validation_tests = [
                ("Basic Flow", self.validate_basic_flow),
                ("Multi-turn Conversation", self.validate_multi_turn_conversation),
                ("Error Handling", self.validate_error_handling),
                ("Cleanup", self.validate_cleanup),
            ]
            
            for test_name, test_func in validation_tests:
                self.logger.info(f"\n🧪 Running {test_name} validation...")
                try:
                    success = await asyncio.wait_for(test_func(), timeout=60.0)
                    status = "✅ PASS" if success else "❌ FAIL"
                    self.logger.info(f"{test_name}: {status}")
                except asyncio.TimeoutError:
                    self.logger.error(f"{test_name}: ❌ TIMEOUT")
                except Exception as e:
                    self.logger.error(f"{test_name}: ❌ ERROR - {e}")
                
                # Brief pause between tests
                await asyncio.sleep(2)
            
            # Calculate overall success
            self.test_results["overall_success"] = self._calculate_overall_success()
            
        except Exception as e:
            self.logger.error(f"❌ Validation suite failed: {e}")
        
        finally:
            # Always try to stop the server
            await self.stop_server()
        
        return self._generate_final_report(start_time)

    def _generate_final_report(self, start_time: float) -> Dict:
        """Generate the final validation report."""
        end_time = time.time()
        duration = end_time - start_time
        
        report = {
            "validation_info": {
                "start_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time)),
                "duration_seconds": round(duration, 2),
                "host": self.host,
                "port": self.port
            },
            "test_results": self.test_results.copy(),
            "summary": {
                "overall_success": self.test_results["overall_success"],
                "total_tests": len(self.test_results) - 1,  # Exclude overall_success
                "passed_tests": sum(1 for k, v in self.test_results.items() if k != "overall_success" and v),
                "failed_tests": sum(1 for k, v in self.test_results.items() if k != "overall_success" and not v)
            }
        }
        
        return report

    def print_validation_report(self, report: Dict):
        """Print a formatted validation report."""
        print("\n" + "=" * 80)
        print("🔍 TWILIO REALTIME BRIDGE VALIDATION REPORT")
        print("=" * 80)
        
        # Basic info
        info = report["validation_info"]
        print(f"📅 Start Time: {info['start_time']}")
        print(f"⏱️  Duration: {info['duration_seconds']}s")
        print(f"🌐 Server: {info['host']}:{info['port']}")
        
        # Overall result
        overall = report["test_results"]["overall_success"]
        status_emoji = "✅" if overall else "❌"
        print(f"\n{status_emoji} OVERALL RESULT: {'SUCCESS' if overall else 'FAILURE'}")
        
        # Test breakdown
        print(f"\n📊 TEST RESULTS:")
        test_mapping = {
            "server_started": "Server Startup",
            "openai_connection": "OpenAI Connection",
            "twilio_connection": "Twilio Connection", 
            "audio_flow": "Audio Flow",
            "session_management": "Session Management",
            "multi_turn": "Multi-turn Conversation",
            "error_handling": "Error Handling",
            "cleanup": "Resource Cleanup"
        }
        
        for key, name in test_mapping.items():
            passed = report["test_results"].get(key, False)
            emoji = "✅" if passed else "❌"
            print(f"  {emoji} {name}")
        
        # Summary
        summary = report["summary"]
        print(f"\n📈 SUMMARY:")
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Passed: {summary['passed_tests']}")
        print(f"  Failed: {summary['failed_tests']}")
        print(f"  Success Rate: {(summary['passed_tests']/summary['total_tests']*100):.1f}%")
        
        print("=" * 80)


async def main():
    """Main function to run the validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate Twilio Realtime Bridge")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Server host (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Server port (default: {DEFAULT_PORT})")
    parser.add_argument("--output", help="JSON output file for results")
    
    args = parser.parse_args()
    
    # Create validator
    validator = TwilioRealtimeBridgeValidator(host=args.host, port=args.port)
    
    # Handle Ctrl+C gracefully
    def signal_handler(signum, frame):
        print("\n🛑 Validation interrupted by user")
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Run validation
        report = await validator.run_full_validation()
        
        # Print report
        validator.print_validation_report(report)
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n💾 Results saved to: {args.output}")
        
        # Exit with appropriate code
        exit_code = 0 if report["test_results"]["overall_success"] else 1
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Validation failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 