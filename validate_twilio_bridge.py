#!/usr/bin/env python3
"""
Twilio Bridge Validation Script

This script provides comprehensive validation of a running Twilio bridge server
using the MockTwilioClient mock implementation. It tests all major functionality
including session management, audio streaming, and multi-turn conversations.

Usage:
    python validate_twilio_bridge.py [OPTIONS]

Examples:
    # Basic validation with default settings
    python validate_twilio_bridge.py

    # Validate specific bridge URL
    python validate_twilio_bridge.py --bridge-url ws://localhost:8000/twilio-agent

    # Run with custom audio files
    python validate_twilio_bridge.py --audio-dir ./test_audio

    # Extended validation with all tests
    python validate_twilio_bridge.py --extended --verbose

    # Quick validation (basic tests only)
    python validate_twilio_bridge.py --quick

    # Generate test report
    python validate_twilio_bridge.py --report-file validation_report.json

    # Run with custom logging
    python validate_twilio_bridge.py --log-level DEBUG --log-file validation.log

    # Run with custom log file path
    python validate_twilio_bridge.py --log-file logs/bridge_validation.log
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from opusagent.config import get_config
from opusagent.config.env_loader import load_env_file
from opusagent.config.logging_config import configure_logging
from opusagent.local.mock_twilio_client import MockTwilioClient


class BridgeValidationResults:
    """Container for validation test results."""

    def __init__(self):
        self.tests: Dict[str, Dict[str, Any]] = {}
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.success = True

    def add_test_result(
        self,
        test_name: str,
        passed: bool,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        """Add a test result to the collection."""
        self.tests[test_name] = {
            "passed": passed,
            "details": details or {},
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }
        if not passed:
            self.success = False

    def finalize(self):
        """Finalize the results."""
        self.end_time = time.time()

    @property
    def duration(self) -> float:
        """Get validation duration."""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    @property
    def passed_tests(self) -> int:
        """Get number of passed tests."""
        return sum(1 for result in self.tests.values() if result["passed"])

    @property
    def total_tests(self) -> int:
        """Get total number of tests."""
        return len(self.tests)

    @property
    def success_rate(self) -> float:
        """Get success rate percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary for reporting."""
        return {
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(
                self.end_time or time.time()
            ).isoformat(),
            "duration": self.duration,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "success_rate": self.success_rate,
            "overall_success": self.success,
            "tests": self.tests,
        }


class TwilioBridgeValidator:
    """Comprehensive Twilio bridge validation."""

    DEFAULT_TARGET_TURNS = 8

    def __init__(
        self,
        bridge_url: str = "ws://localhost:8000/twilio-agent",
        audio_dir: Optional[str] = None,
        timeout: float = 30.0,
        verbose: bool = False,
    ):
        self.bridge_url = bridge_url
        self.audio_dir = Path(audio_dir) if audio_dir else None
        self.timeout = timeout
        self.verbose = verbose
        self.results = BridgeValidationResults()

        # Configure logging using centralized configuration
        self.logger = configure_logging(
            "bridge_validator", log_filename="bridge_validation.log"
        )

        # Test audio files
        self.test_audio_files = self._discover_audio_files()

    def _discover_audio_files(self) -> List[str]:
        """Discover available test audio files, searching recursively in default directories."""
        audio_files = []

        # Check for audio directory (user-specified)
        if self.audio_dir and self.audio_dir.exists():
            for ext in ["*.wav", "*.mp3"]:
                audio_files.extend([str(f) for f in self.audio_dir.rglob(ext)])

        # Check for default audio locations (recursively)
        default_dirs = [
            Path("demo/audio"),
            Path("test_audio"),
            Path("opusagent/local/audio"),
            Path("validation_audio"),
        ]

        for dir_path in default_dirs:
            if dir_path.exists():
                for ext in ["*.wav", "*.mp3"]:
                    audio_files.extend([str(f) for f in dir_path.rglob(ext)])

        # Remove duplicates and return
        return list(set(audio_files))

    async def validate_bridge(
        self, test_suite: str = "standard"
    ) -> BridgeValidationResults:
        """
        Run comprehensive bridge validation.

        Args:
            test_suite: Type of test suite to run ("quick", "standard", "extended")

        Returns:
            BridgeValidationResults: Validation results
        """
        self.logger.info(f"🚀 Starting Twilio bridge validation")
        self.logger.info(f"   Bridge URL: {self.bridge_url}")
        self.logger.info(f"   Test Suite: {test_suite}")
        self.logger.info(f"   Audio Files: {len(self.test_audio_files)} found")

        try:
            # Run test suite based on type
            if test_suite == "quick":
                await self._run_quick_tests()
            elif test_suite == "extended":
                await self._run_extended_tests()
            else:  # standard
                await self._run_standard_tests()

        except Exception as e:
            self.logger.error(f"Validation failed with error: {e}")
            self.results.add_test_result(
                "validation_execution", False, {"error": str(e)}, str(e)
            )

        self.results.finalize()
        return self.results

    async def _run_quick_tests(self):
        """Run quick validation tests (basic functionality only)."""
        self.logger.info("🏃 Running quick validation tests...")

        await self._test_basic_connectivity()
        await self._test_session_lifecycle()
        await self._test_basic_audio_streaming()

    async def _run_standard_tests(self):
        """Run standard validation tests (recommended for most use cases)."""
        self.logger.info("🧪 Running standard validation tests...")

        await self._test_basic_connectivity()
        await self._test_session_lifecycle()
        await self._test_basic_audio_streaming()
        await self._test_multi_turn_conversation()
        await self._test_audio_quality()

    async def _run_extended_tests(self):
        """Run extended validation tests (all tests including stress and edge cases)."""
        self.logger.info("🔬 Running extended validation tests...")

        await self._test_basic_connectivity()
        await self._test_session_lifecycle()
        await self._test_basic_audio_streaming()
        await self._test_multi_turn_conversation()
        await self._test_audio_quality()
        await self._test_dtmf_handling()
        await self._test_mark_handling()
        await self._test_error_handling()
        await self._test_performance()

    async def _test_basic_connectivity(self):
        """Test basic WebSocket connectivity to the bridge."""
        self.logger.info("Testing basic connectivity...")
        start_time = time.time()

        try:
            async with MockTwilioClient(self.bridge_url) as client:
                # Send connected and start messages
                await client.send_connected()
                await client.send_start()

                # Small delay to receive any initial messages
                await asyncio.sleep(1)

                duration = time.time() - start_time
                details = {
                    "duration": duration,
                    "received_messages": len(client.received_messages),
                }

                self.results.add_test_result("basic_connectivity", True, details)
                self.logger.info("✅ Basic connectivity test passed")

        except Exception as e:
            self.results.add_test_result("basic_connectivity", False, error=str(e))
            self.logger.error(f"❌ Basic connectivity test failed: {e}")

    async def _test_session_lifecycle(self):
        """Test complete session lifecycle: connect, start, stop."""
        self.logger.info("Testing session lifecycle...")
        start_time = time.time()

        try:
            async with MockTwilioClient(self.bridge_url) as client:
                await client.send_connected()
                await client.send_start()
                await asyncio.sleep(1)  # Allow time for processing
                await client.send_stop()

                duration = time.time() - start_time
                details = {
                    "duration": duration,
                    "received_messages": len(client.received_messages),
                    "stream_started": client.stream_started,
                    "stream_stopped": client.stream_stopped,
                }

                passed = client.stream_started and client.stream_stopped
                self.results.add_test_result("session_lifecycle", passed, details)

                if passed:
                    self.logger.info("✅ Session lifecycle test passed")
                else:
                    self.logger.error("❌ Session lifecycle test failed")

        except Exception as e:
            self.results.add_test_result("session_lifecycle", False, error=str(e))
            self.logger.error(f"❌ Session lifecycle test failed: {e}")

    async def _test_basic_audio_streaming(self):
        """Test basic audio streaming functionality."""
        self.logger.info("Testing basic audio streaming...")

        if not self.test_audio_files:
            self.logger.warning("No audio files found, skipping audio streaming test")
            self.results.add_test_result(
                "basic_audio_streaming", False, error="No audio files available"
            )
            return

        test_file = self.test_audio_files[0]
        start_time = time.time()

        try:
            async with MockTwilioClient(self.bridge_url) as client:
                await client.initiate_call_flow()
                success = await client.send_user_audio(test_file)
                response = await client.wait_for_ai_response(timeout=self.timeout)
                await client.send_stop()

                duration = time.time() - start_time
                details = {
                    "duration": duration,
                    "audio_file": test_file,
                    "audio_sent": success,
                    "response_received": bool(response),
                    "response_chunks": len(response) if response else 0,
                }

                passed = success and bool(response)
                self.results.add_test_result("basic_audio_streaming", passed, details)

                if passed:
                    self.logger.info("✅ Basic audio streaming test passed")
                else:
                    self.logger.error("❌ Basic audio streaming test failed")

        except Exception as e:
            self.results.add_test_result("basic_audio_streaming", False, error=str(e))
            self.logger.error(f"❌ Basic audio streaming test failed: {e}")

    async def _test_multi_turn_conversation(self, target_turns: Optional[int] = None):
        """Test multi-turn conversation with multiple audio exchanges."""
        self.logger.info("Testing multi-turn conversation...")

        target_turns = target_turns or self.DEFAULT_TARGET_TURNS
        if len(self.test_audio_files) < target_turns:
            self.logger.warning(
                f"Insufficient audio files for {target_turns} turns, using {len(self.test_audio_files)}"
            )
            target_turns = len(self.test_audio_files)

        audio_files = self.test_audio_files[:target_turns]
        start_time = time.time()

        try:
            async with MockTwilioClient(self.bridge_url) as client:
                result = await client.multi_turn_conversation(audio_files)

                duration = time.time() - start_time
                details = {
                    "duration": duration,
                    "target_turns": target_turns,
                    "completed_turns": result["completed_turns"],
                    "success_rate": (
                        (result["completed_turns"] / target_turns) * 100
                        if target_turns > 0
                        else 0
                    ),
                    "greeting_received": result["greeting_received"],
                    "turns": result["turns"],
                }

                passed = result["success"] and result["completed_turns"] == target_turns
                self.results.add_test_result("multi_turn_conversation", passed, details)

                if passed:
                    self.logger.info("✅ Multi-turn conversation test passed")
                else:
                    self.logger.error("❌ Multi-turn conversation test failed")

        except Exception as e:
            self.results.add_test_result("multi_turn_conversation", False, error=str(e))
            self.logger.error(f"❌ Multi-turn conversation test failed: {e}")

    async def _test_dtmf_handling(self):
        """Test DTMF handling in the bridge."""
        self.logger.info("Testing DTMF handling...")
        start_time = time.time()

        try:
            async with MockTwilioClient(self.bridge_url) as client:
                await client.initiate_call_flow()
                await asyncio.sleep(1)  # Allow time for greeting

                # Send DTMF digits
                dtmf_digits = ["1", "2", "3", "#"]
                for digit in dtmf_digits:
                    await client.send_dtmf(digit)
                    await asyncio.sleep(0.5)

                # Wait for any response
                await asyncio.sleep(2)
                await client.send_stop()

                duration = time.time() - start_time
                details = {
                    "duration": duration,
                    "dtmf_sent": len(dtmf_digits),
                    "received_messages": len(client.received_messages),
                }

                # For now, just check if we received any marks or media after DTMF
                passed = (
                    len(client.received_marks) > 0
                    or len(client.received_media_chunks) > 0
                )
                self.results.add_test_result("dtmf_handling", passed, details)

                if passed:
                    self.logger.info("✅ DTMF handling test passed")
                else:
                    self.logger.warning(
                        "❌ DTMF handling test failed - no response detected"
                    )

        except Exception as e:
            self.results.add_test_result("dtmf_handling", False, error=str(e))
            self.logger.error(f"❌ DTMF handling test failed: {e}")

    async def _test_mark_handling(self):
        """Test mark message handling in the bridge."""
        self.logger.info("Testing mark handling...")
        start_time = time.time()

        try:
            async with MockTwilioClient(self.bridge_url) as client:
                await client.initiate_call_flow()
                await asyncio.sleep(1)

                # The mock client receives marks from the bridge
                # Wait for any marks during initial interaction
                await asyncio.sleep(5)
                await client.send_stop()

                duration = time.time() - start_time
                details = {
                    "duration": duration,
                    "received_marks": len(client.received_marks),
                    "marks": client.received_marks,
                }

                passed = len(client.received_marks) > 0
                self.results.add_test_result("mark_handling", passed, details)

                if passed:
                    self.logger.info("✅ Mark handling test passed")
                else:
                    self.logger.warning(
                        "❌ Mark handling test failed - no marks received"
                    )

        except Exception as e:
            self.results.add_test_result("mark_handling", False, error=str(e))
            self.logger.error(f"❌ Mark handling test failed: {e}")

    async def _test_audio_quality(self):
        """Test audio quality and processing."""
        self.logger.info("Testing audio quality...")

        if not self.test_audio_files:
            self.logger.warning("No audio files found, skipping audio quality test")
            self.results.add_test_result(
                "audio_quality", False, error="No audio files available"
            )
            return

        test_file = self.test_audio_files[0]
        start_time = time.time()

        try:
            async with MockTwilioClient(self.bridge_url) as client:
                await client.initiate_call_flow()
                await client.send_user_audio(test_file)
                response = await client.wait_for_ai_response(timeout=self.timeout)
                await client.send_stop()

                duration = time.time() - start_time
                details = {
                    "duration": duration,
                    "audio_file": test_file,
                    "response_chunks": len(response) if response else 0,
                }

                # Basic quality check: received some response audio
                passed = bool(response) and len(response) > 10  # Arbitrary threshold
                self.results.add_test_result("audio_quality", passed, details)

                if passed:
                    self.logger.info("✅ Audio quality test passed")
                else:
                    self.logger.error("❌ Audio quality test failed")

        except Exception as e:
            self.results.add_test_result("audio_quality", False, error=str(e))
            self.logger.error(f"❌ Audio quality test failed: {e}")

    async def _test_error_handling(self):
        """Test error handling and recovery."""
        self.logger.info("Testing error handling...")
        start_time = time.time()

        try:
            # Test invalid connection
            try:
                async with MockTwilioClient("ws://invalid-url:9999") as client:
                    await client.initiate_call_flow()
                passed = False  # Should have raised an exception
            except Exception:
                passed = True  # Expected to fail

            # Test sending audio without starting stream
            async with MockTwilioClient(self.bridge_url) as client:
                await client.send_connected()
                # Don't send start, try to send audio
                # Note: This intentionally uses a potentially non-existent file to test error handling
                # The test expects this to fail, so using "nonexistent.wav" when no test files are available
                success = await client.send_user_audio(
                    self.test_audio_files[0]
                    if self.test_audio_files
                    else "nonexistent.wav"
                )
                passed = passed and not success  # Should fail

            duration = time.time() - start_time
            details = {
                "duration": duration,
            }

            self.results.add_test_result("error_handling", passed, details)
            if passed:
                self.logger.info("✅ Error handling test passed")
            else:
                self.logger.error("❌ Error handling test failed")

        except Exception as e:
            self.results.add_test_result("error_handling", False, error=str(e))
            self.logger.error(f"❌ Error handling test failed: {e}")

    async def _test_performance(self, num_turns: int = 10):
        """Test performance with multiple turns."""
        self.logger.info(f"Testing performance with {num_turns} turns...")

        if len(self.test_audio_files) < num_turns:
            self.logger.warning(
                f"Insufficient audio files, reducing to {len(self.test_audio_files)} turns"
            )
            num_turns = len(self.test_audio_files)

        audio_files = self.test_audio_files[:num_turns]
        start_time = time.time()

        try:
            async with MockTwilioClient(self.bridge_url) as client:
                result = await client.multi_turn_conversation(
                    audio_files, turn_delay=0.5
                )

                duration = time.time() - start_time
                avg_turn_time = (
                    duration / result["completed_turns"]
                    if result["completed_turns"] > 0
                    else 0
                )

                details = {
                    "duration": duration,
                    "turns": result["completed_turns"],
                    "avg_turn_time": avg_turn_time,
                    "success_rate": (result["completed_turns"] / num_turns) * 100,
                }

                passed = (
                    result["completed_turns"] == num_turns and avg_turn_time < 10
                )  # Arbitrary threshold
                self.results.add_test_result("performance", passed, details)

                if passed:
                    self.logger.info("✅ Performance test passed")
                else:
                    self.logger.error("❌ Performance test failed")

        except Exception as e:
            self.results.add_test_result("performance", False, error=str(e))
            self.logger.error(f"❌ Performance test failed: {e}")

    def generate_report(self, output_file: Optional[str] = None) -> str:
        """Generate validation report."""
        report = self.results.to_dict()

        if output_file:
            with open(output_file, "w") as f:
                json.dump(report, f, indent=4)
            self.logger.info(f"📊 Report saved to {output_file}")

        return json.dumps(report, indent=4)

    def print_summary(self):
        """Print summary of validation results."""
        self.logger.info("\n=== Validation Summary ===")
        self.logger.info(f"Total Tests: {self.results.total_tests}")
        self.logger.info(f"Passed: {self.results.passed_tests}")
        self.logger.info(f"Success Rate: {self.results.success_rate:.2f}%")
        self.logger.info(f"Duration: {self.results.duration:.2f}s")
        self.logger.info("==========================")

        for test_name, result in self.results.tests.items():
            status = "✅ PASSED" if result["passed"] else "❌ FAILED"
            self.logger.info(f"{test_name}: {status}")
            if result["error"]:
                self.logger.error(f"   Error: {result['error']}")
            if self.verbose and result["details"]:
                self.logger.debug(f"   Details: {result['details']}")


async def main():
    """Main function for command-line usage."""
    # Load environment variables
    load_env_file()

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Twilio Bridge Validation Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--bridge-url",
        default="ws://localhost:8000/twilio-agent",
        help="Bridge server WebSocket URL (default: ws://localhost:8000/twilio-agent)",
    )
    parser.add_argument(
        "--audio-dir",
        help="Directory containing test audio files (default: auto-discover)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Test timeout in seconds (default: 30.0)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick validation (basic tests only)",
    )
    parser.add_argument(
        "--extended",
        action="store_true",
        help="Run extended validation (all tests including stress tests)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--report-file",
        help="Output file for JSON report",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)",
    )
    parser.add_argument(
        "--log-file",
        help="Custom log file path (default: logs/opusagent.log)",
    )

    args = parser.parse_args()

    # Configure logging
    if args.log_file:
        # Use custom log file path
        log_file_path = Path(args.log_file)
        log_dir = log_file_path.parent
        log_filename = log_file_path.name
        logger = configure_logging("validation_script", str(log_dir), log_filename)
    else:
        # Use default logging configuration
        logger = configure_logging("validation_script")

    # Log validation configuration
    logger.info("=== Bridge Validation Configuration ===")
    logger.info(f"Bridge URL: {args.bridge_url}")
    logger.info(f"Audio Directory: {args.audio_dir or 'Auto-discover'}")
    logger.info(f"Timeout: {args.timeout}s")
    logger.info(f"Log Level: {args.log_level}")
    logger.info(f"Verbose: {args.verbose}")
    logger.info("=====================================")

    # Determine test suite
    if args.quick:
        test_suite = "quick"
    elif args.extended:
        test_suite = "extended"
    else:
        test_suite = "standard"

    # Create validator
    validator = TwilioBridgeValidator(
        bridge_url=args.bridge_url,
        audio_dir=args.audio_dir,
        timeout=args.timeout,
        verbose=args.verbose,
    )

    # Run validation
    try:
        results = await validator.validate_bridge(test_suite=test_suite)
        validator.print_summary()

        if args.report_file:
            validator.generate_report(args.report_file)

        sys.exit(0 if results.success else 1)

    except KeyboardInterrupt:
        logger.warning("Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
