#!/usr/bin/env python3
"""
AudioCodes Bridge Validation Script

This script provides comprehensive validation of a running AudioCodes bridge server
using the LocalAudioCodesClient mock implementation. It tests all major functionality
including session management, audio streaming, VAD, and multi-turn conversations.

Usage:
    python validate_audiocodes_bridge.py [OPTIONS]

Examples:
    # Basic validation with default settings
    python validate_audiocodes_bridge.py

    # Validate specific bridge URL
    python validate_audiocodes_bridge.py --bridge-url ws://localhost:8080

    # Run with custom audio files
    python validate_audiocodes_bridge.py --audio-dir ./test_audio

    # Extended validation with all tests
    python validate_audiocodes_bridge.py --extended --verbose

    # Quick validation (basic tests only)
    python validate_audiocodes_bridge.py --quick

    # Generate test report
    python validate_audiocodes_bridge.py --report-file validation_report.json
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

from opusagent.config.env_loader import load_env_file
from opusagent.local.audiocodes import LocalAudioCodesClient


class BridgeValidationResults:
    """Container for validation test results."""

    def __init__(self):
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results: List[Dict[str, Any]] = []
        self.overall_success = False
        self.errors: List[str] = []

    def add_test_result(
        self,
        test_name: str,
        success: bool,
        details: Dict[str, Any],
        error: Optional[str] = None,
    ):
        """Add a test result."""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
            if error:
                self.errors.append(f"{test_name}: {error}")

        self.test_results.append(
            {
                "test_name": test_name,
                "success": success,
                "timestamp": datetime.now().isoformat(),
                "details": details,
                "error": error,
            }
        )

    def finalize(self):
        """Finalize results and calculate overall success."""
        self.end_time = datetime.now()
        self.overall_success = self.tests_failed == 0 and self.tests_passed > 0

    @property
    def duration(self) -> float:
        """Get total validation duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.tests_run == 0:
            return 0.0
        return (self.tests_passed / self.tests_run) * 100.0


class AudioCodesBridgeValidator:
    """Comprehensive AudioCodes bridge validation."""

    DEFAULT_TARGET_TURNS = 8

    def __init__(
        self,
        bridge_url: str = "ws://localhost:8000/ws/telephony",
        audio_dir: Optional[str] = None,
        timeout: float = 30.0,
        verbose: bool = False,
    ):
        self.bridge_url = bridge_url
        self.audio_dir = Path(audio_dir) if audio_dir else None
        self.timeout = timeout
        self.verbose = verbose
        self.results = BridgeValidationResults()

        # Configure logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger("bridge_validator")

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
            Path("audio"),
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
        self.logger.info(f"🚀 Starting AudioCodes bridge validation")
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
        self.logger.info("🔧 Running standard validation tests...")

        await self._test_basic_connectivity()
        await self._test_session_lifecycle()
        await self._test_connection_validation()
        await self._test_basic_audio_streaming()
        await self._test_multi_turn_conversation()
        await self._test_vad_functionality()
        await self._test_session_resumption()
        await self._test_error_handling()

    async def _run_extended_tests(self):
        """Run extended validation tests (comprehensive testing)."""
        self.logger.info("🔬 Running extended validation tests...")

        await self._test_basic_connectivity()
        await self._test_session_lifecycle()
        await self._test_connection_validation()
        await self._test_basic_audio_streaming()
        await self._test_multi_turn_conversation()
        await self._test_vad_functionality()
        await self._test_session_resumption()
        await self._test_dtmf_events()
        await self._test_custom_activities()
        await self._test_concurrent_sessions()
        await self._test_performance_metrics()
        await self._test_error_handling()
        await self._test_long_conversation()

    async def _test_basic_connectivity(self):
        """Test basic WebSocket connectivity to the bridge."""
        test_name = "basic_connectivity"
        self.logger.info(f"🔌 Testing basic connectivity...")

        try:
            async with LocalAudioCodesClient(
                self.bridge_url,
                bot_name="ValidationBot",
                caller="+15551234567",
                logger=self.logger,
            ) as client:
                # Test connection establishment
                connected = client.connected

                self.results.add_test_result(
                    test_name,
                    connected,
                    {
                        "bridge_url": self.bridge_url,
                        "connected": connected,
                        "client_status": client.get_session_status(),
                    },
                    None if connected else "Failed to establish WebSocket connection",
                )

                if connected:
                    self.logger.info("✅ Basic connectivity successful")
                else:
                    self.logger.error("❌ Basic connectivity failed")

        except Exception as e:
            self.logger.error(f"❌ Basic connectivity failed: {e}")
            self.results.add_test_result(test_name, False, {"error": str(e)}, None)

    async def _test_session_lifecycle(self):
        """Test session initiation, acceptance, and termination."""
        test_name = "session_lifecycle"
        self.logger.info(f"📋 Testing session lifecycle...")

        try:
            async with LocalAudioCodesClient(
                self.bridge_url, logger=self.logger
            ) as client:
                # Test session initiation
                session_initiated = await client.initiate_session()

                if session_initiated:
                    # Test session status
                    status = client.get_session_status()
                    session_active = status.get("status") == "active"
                    conversation_id = status.get("conversation_id")

                    # Test session termination
                    await client.end_session("Validation test completed")

                    self.results.add_test_result(
                        test_name,
                        bool(session_initiated and session_active and conversation_id),
                        {
                            "session_initiated": session_initiated,
                            "session_active": session_active,
                            "conversation_id": conversation_id,
                            "status": status,
                        },
                    )

                    if session_initiated and session_active:
                        self.logger.info("✅ Session lifecycle successful")
                    else:
                        self.logger.error("❌ Session lifecycle failed")
                else:
                    self.results.add_test_result(
                        test_name,
                        False,
                        {"session_initiated": False},
                        "Session initiation failed",
                    )
                    self.logger.error("❌ Session initiation failed")

        except Exception as e:
            self.logger.error(f"❌ Session lifecycle failed: {e}")
            self.results.add_test_result(test_name, False, {"error": str(e)}, None)

    async def _test_connection_validation(self):
        """Test connection validation functionality."""
        test_name = "connection_validation"
        self.logger.info(f"🔍 Testing connection validation...")

        try:
            async with LocalAudioCodesClient(
                self.bridge_url, logger=self.logger
            ) as client:
                # Initiate session first
                await client.initiate_session()

                # Test connection validation
                validated = await client.validate_connection()

                self.results.add_test_result(
                    test_name,
                    validated,
                    {"connection_validated": validated},
                    None if validated else "Connection validation failed",
                )

                if validated:
                    self.logger.info("✅ Connection validation successful")
                else:
                    self.logger.error("❌ Connection validation failed")

        except Exception as e:
            self.logger.error(f"❌ Connection validation failed: {e}")
            self.results.add_test_result(test_name, False, {"error": str(e)}, None)

    async def _test_basic_audio_streaming(self):
        """Test basic audio streaming functionality."""
        test_name = "basic_audio_streaming"
        self.logger.info(f"🎵 Testing basic audio streaming...")

        try:
            # Check if we have test audio files
            if not self.test_audio_files:
                self.logger.warning(
                    "⚠️ No test audio files found, skipping audio streaming test"
                )
                self.results.add_test_result(
                    test_name,
                    False,
                    {"audio_files_available": False},
                    "No test audio files available",
                )
                return

            async with LocalAudioCodesClient(
                self.bridge_url, logger=self.logger
            ) as client:
                # Initiate session
                await client.initiate_session()

                # Test audio streaming with first available file
                test_file = self.test_audio_files[0]
                self.logger.info(f"   Using test file: {Path(test_file).name}")

                audio_sent = await client.send_user_audio(test_file, chunk_delay=0.01)

                # Wait for potential response
                if audio_sent:
                    response_chunks = await client.wait_for_llm_response(timeout=15.0)
                    response_received = len(response_chunks) > 0
                else:
                    response_received = False
                    response_chunks = []

                self.results.add_test_result(
                    test_name,
                    audio_sent,  # Success if audio was sent (response is optional)
                    {
                        "test_file": str(Path(test_file).name),
                        "audio_sent": audio_sent,
                        "response_received": response_received,
                        "response_chunks": len(response_chunks),
                    },
                    None if audio_sent else "Failed to send audio",
                )

                if audio_sent:
                    self.logger.info(
                        f"✅ Audio streaming successful (response: {len(response_chunks)} chunks)"
                    )
                else:
                    self.logger.error("❌ Audio streaming failed")

        except Exception as e:
            self.logger.error(f"❌ Audio streaming failed: {e}")
            self.results.add_test_result(test_name, False, {"error": str(e)}, None)

    async def _test_multi_turn_conversation(self):
        """Test multi-turn conversation functionality."""
        test_name = "multi_turn_conversation"
        self.logger.info(f"💬 Testing multi-turn conversation...")

        try:
            # Check if we have enough audio files for multi-turn
            available_files = self.test_audio_files[:3]  # Use up to 3 files
            if not available_files:
                self.logger.warning(
                    "⚠️ No test audio files found, skipping multi-turn test"
                )
                self.results.add_test_result(
                    test_name,
                    False,
                    {"audio_files_available": False},
                    "No test audio files available",
                )
                return

            async with LocalAudioCodesClient(
                self.bridge_url, logger=self.logger
            ) as client:
                # Initiate session before running multi-turn conversation
                session_started = await client.initiate_session()
                if not session_started:
                    self.logger.error(
                        "❌ Failed to initiate session for multi-turn conversation"
                    )
                    self.results.add_test_result(
                        test_name,
                        False,
                        {"session_initiated": False},
                        "Failed to initiate session before multi-turn conversation",
                    )
                    return

                # Run multi-turn conversation
                result = await client.multi_turn_conversation(
                    available_files,
                    wait_for_greeting=True,
                    turn_delay=1.0,
                    chunk_delay=0.01,
                )

                success = (
                    result.success and result.success_rate >= 50.0
                )  # At least 50% success rate

                self.results.add_test_result(
                    test_name,
                    bool(success),
                    {
                        "total_turns": result.total_turns,
                        "completed_turns": result.completed_turns,
                        "success_rate": result.success_rate,
                        "greeting_received": result.greeting_received,
                        "greeting_chunks": result.greeting_chunks,
                        "duration": result.duration,
                        "files_used": [str(Path(f).name) for f in available_files],
                    },
                    (
                        None
                        if success
                        else f"Multi-turn conversation failed: {result.error}"
                    ),
                )

                if success:
                    self.logger.info(
                        f"✅ Multi-turn conversation successful ({result.success_rate:.1f}% success rate)"
                    )
                else:
                    self.logger.error(
                        f"❌ Multi-turn conversation failed ({result.success_rate:.1f}% success rate)"
                    )

        except Exception as e:
            self.logger.error(f"❌ Multi-turn conversation failed: {e}")
            self.results.add_test_result(test_name, False, {"error": str(e)}, None)

    async def _test_vad_functionality(self):
        """Test Voice Activity Detection functionality."""
        test_name = "vad_functionality"
        self.logger.info(f"🎤 Testing VAD functionality...")

        try:
            async with LocalAudioCodesClient(
                self.bridge_url, logger=self.logger
            ) as client:
                # Initiate session
                await client.initiate_session()

                # Test VAD enablement
                vad_enabled = client.enable_vad()
                vad_status = client.get_vad_status()

                # Test VAD with audio if available
                vad_tested = False
                if self.test_audio_files and vad_enabled:
                    test_file = self.test_audio_files[0]
                    vad_tested = await client.send_user_audio_with_vad(
                        test_file,
                        chunk_delay=0.01,
                        vad_threshold=0.3,
                        simulate_hypothesis=True,
                    )

                self.results.add_test_result(
                    test_name,
                    vad_enabled,
                    {
                        "vad_enabled": vad_enabled,
                        "vad_status": vad_status,
                        "vad_tested_with_audio": vad_tested,
                        "audio_files_available": len(self.test_audio_files) > 0,
                    },
                    None if vad_enabled else "VAD could not be enabled",
                )

                if vad_enabled:
                    self.logger.info("✅ VAD functionality successful")
                else:
                    self.logger.error("❌ VAD functionality failed")

        except Exception as e:
            self.logger.error(f"❌ VAD functionality failed: {e}")
            self.results.add_test_result(test_name, False, {"error": str(e)}, None)

    async def _test_session_resumption(self):
        """Test session resumption functionality."""
        test_name = "session_resumption"
        self.logger.info(f"🔄 Testing session resumption...")

        try:
            conversation_id = None

            # First, create a session to get a conversation ID
            async with LocalAudioCodesClient(
                self.bridge_url, logger=self.logger
            ) as client:
                session_initiated = await client.initiate_session()
                if session_initiated:
                    status = client.get_session_status()
                    conversation_id = status.get("conversation_id")

            if not conversation_id:
                self.results.add_test_result(
                    test_name,
                    False,
                    {"initial_session_created": False},
                    "Could not create initial session for resumption test",
                )
                return

            # Now test resumption
            async with LocalAudioCodesClient(
                self.bridge_url, logger=self.logger
            ) as client:
                resumed = await client.resume_session(conversation_id)

                self.results.add_test_result(
                    test_name,
                    resumed,
                    {"conversation_id": conversation_id, "session_resumed": resumed},
                    None if resumed else "Session resumption failed",
                )

                if resumed:
                    self.logger.info("✅ Session resumption successful")
                else:
                    self.logger.error("❌ Session resumption failed")

        except Exception as e:
            self.logger.error(f"❌ Session resumption failed: {e}")
            self.results.add_test_result(test_name, False, {"error": str(e)}, None)

    async def _test_dtmf_events(self):
        """Test DTMF event functionality."""
        test_name = "dtmf_events"
        self.logger.info(f"📞 Testing DTMF events...")

        try:
            async with LocalAudioCodesClient(
                self.bridge_url, logger=self.logger
            ) as client:
                # Initiate session
                await client.initiate_session()

                # Test sending DTMF digits
                dtmf_digits = ["1", "2", "3", "*", "#"]
                dtmf_results = []

                for digit in dtmf_digits:
                    sent = await client.send_dtmf_event(digit)
                    dtmf_results.append({"digit": digit, "sent": sent})
                    if sent:
                        await asyncio.sleep(0.1)  # Small delay between digits

                success = all(result["sent"] for result in dtmf_results)

                self.results.add_test_result(
                    test_name,
                    success,
                    {
                        "dtmf_digits_tested": dtmf_digits,
                        "dtmf_results": dtmf_results,
                        "all_sent": success,
                    },
                    None if success else "Some DTMF events failed to send",
                )

                if success:
                    self.logger.info("✅ DTMF events successful")
                else:
                    self.logger.error("❌ DTMF events failed")

        except Exception as e:
            self.logger.error(f"❌ DTMF events failed: {e}")
            self.results.add_test_result(test_name, False, {"error": str(e)}, None)

    async def _test_custom_activities(self):
        """Test custom activity functionality."""
        test_name = "custom_activities"
        self.logger.info(f"🎯 Testing custom activities...")

        try:
            async with LocalAudioCodesClient(
                self.bridge_url, logger=self.logger
            ) as client:
                # Initiate session
                await client.initiate_session()

                # Test custom activities
                test_activities = [
                    {"type": "event", "name": "test_event", "value": "test_value"},
                    {
                        "type": "event",
                        "name": "validation_check",
                        "value": "bridge_test",
                    },
                    {"type": "event", "name": "custom_action", "value": "example"},
                ]

                activity_results = []
                for activity in test_activities:
                    sent = await client.send_custom_activity(activity)
                    activity_results.append({"activity": activity, "sent": sent})

                success = all(result["sent"] for result in activity_results)

                self.results.add_test_result(
                    test_name,
                    success,
                    {
                        "activities_tested": test_activities,
                        "activity_results": activity_results,
                        "all_sent": success,
                    },
                    None if success else "Some custom activities failed to send",
                )

                if success:
                    self.logger.info("✅ Custom activities successful")
                else:
                    self.logger.error("❌ Custom activities failed")

        except Exception as e:
            self.logger.error(f"❌ Custom activities failed: {e}")
            self.results.add_test_result(test_name, False, {"error": str(e)}, None)

    async def _test_concurrent_sessions(self):
        """Test concurrent session handling."""
        test_name = "concurrent_sessions"
        self.logger.info(f"🔀 Testing concurrent sessions...")

        try:
            # Create multiple concurrent sessions
            session_tasks = []
            num_sessions = 3

            for i in range(num_sessions):
                task = self._create_concurrent_session(
                    f"ConcurrentBot{i+1}", f"+155512345{i+67}"
                )
                session_tasks.append(task)

            # Run sessions concurrently
            session_results = await asyncio.gather(
                *session_tasks, return_exceptions=True
            )

            # Analyze results
            successful_sessions = 0
            failed_sessions = 0

            for i, result in enumerate(session_results):
                if isinstance(result, Exception):
                    failed_sessions += 1
                    self.logger.warning(f"   Session {i+1} failed: {result}")
                elif result:
                    successful_sessions += 1
                else:
                    failed_sessions += 1

            success = (
                successful_sessions >= num_sessions // 2
            )  # At least half should succeed

            self.results.add_test_result(
                test_name,
                success,
                {
                    "sessions_attempted": num_sessions,
                    "sessions_successful": successful_sessions,
                    "sessions_failed": failed_sessions,
                    "success_rate": (successful_sessions / num_sessions) * 100,
                },
                (
                    None
                    if success
                    else f"Only {successful_sessions}/{num_sessions} concurrent sessions succeeded"
                ),
            )

            if success:
                self.logger.info(
                    f"✅ Concurrent sessions successful ({successful_sessions}/{num_sessions})"
                )
            else:
                self.logger.error(
                    f"❌ Concurrent sessions failed ({successful_sessions}/{num_sessions})"
                )

        except Exception as e:
            self.logger.error(f"❌ Concurrent sessions failed: {e}")
            self.results.add_test_result(test_name, False, {"error": str(e)}, None)

    async def _create_concurrent_session(self, bot_name: str, caller: str) -> bool:
        """Create a single concurrent session for testing."""
        try:
            async with LocalAudioCodesClient(
                self.bridge_url, bot_name=bot_name, caller=caller, logger=self.logger
            ) as client:
                # Simple session test
                session_initiated = await client.initiate_session()
                if session_initiated:
                    await asyncio.sleep(1.0)  # Hold session briefly
                    await client.end_session("Concurrent test completed")
                return session_initiated
        except Exception as e:
            self.logger.debug(f"Concurrent session {bot_name} failed: {e}")
            return False

    async def _test_performance_metrics(self):
        """Test performance metrics and response times."""
        test_name = "performance_metrics"
        self.logger.info(f"⚡ Testing performance metrics...")

        try:
            metrics = {
                "session_initiation_times": [],
                "response_times": [],
                "audio_streaming_times": [],
            }

            # Test multiple session initiations for timing
            for i in range(3):
                start_time = time.time()

                async with LocalAudioCodesClient(
                    self.bridge_url, logger=self.logger
                ) as client:
                    session_initiated = await client.initiate_session()
                    if session_initiated:
                        initiation_time = time.time() - start_time
                        metrics["session_initiation_times"].append(initiation_time)

                        # Test audio streaming time if files available
                        if self.test_audio_files:
                            audio_start = time.time()
                            await client.send_user_audio(
                                self.test_audio_files[0], chunk_delay=0.005
                            )
                            audio_time = time.time() - audio_start
                            metrics["audio_streaming_times"].append(audio_time)

                        await client.end_session("Performance test")

            # Calculate averages
            avg_initiation = (
                sum(metrics["session_initiation_times"])
                / len(metrics["session_initiation_times"])
                if metrics["session_initiation_times"]
                else 0
            )
            avg_audio = (
                sum(metrics["audio_streaming_times"])
                / len(metrics["audio_streaming_times"])
                if metrics["audio_streaming_times"]
                else 0
            )

            # Performance thresholds (adjust as needed)
            good_initiation_time = avg_initiation < 5.0  # Less than 5 seconds
            good_audio_time = (
                avg_audio < 10.0 or not metrics["audio_streaming_times"]
            )  # Less than 10 seconds or no audio

            success = good_initiation_time and good_audio_time

            self.results.add_test_result(
                test_name,
                success,
                {
                    "avg_session_initiation_time": avg_initiation,
                    "avg_audio_streaming_time": avg_audio,
                    "session_initiation_times": metrics["session_initiation_times"],
                    "audio_streaming_times": metrics["audio_streaming_times"],
                    "good_initiation_time": good_initiation_time,
                    "good_audio_time": good_audio_time,
                },
                (
                    None
                    if success
                    else "Performance metrics outside acceptable thresholds"
                ),
            )

            if success:
                self.logger.info(
                    f"✅ Performance metrics acceptable (init: {avg_initiation:.2f}s, audio: {avg_audio:.2f}s)"
                )
            else:
                self.logger.error(
                    f"❌ Performance metrics poor (init: {avg_initiation:.2f}s, audio: {avg_audio:.2f}s)"
                )

        except Exception as e:
            self.logger.error(f"❌ Performance metrics failed: {e}")
            self.results.add_test_result(test_name, False, {"error": str(e)}, None)

    async def _test_error_handling(self):
        """Test error handling and recovery."""
        test_name = "error_handling"
        self.logger.info(f"🚨 Testing error handling...")

        try:
            error_tests = []

            # Test invalid session resumption
            try:
                async with LocalAudioCodesClient(
                    self.bridge_url, logger=self.logger
                ) as client:
                    invalid_resume = await client.resume_session(
                        "invalid-conversation-id"
                    )
                    error_tests.append(
                        {"test": "invalid_resume", "handled": not invalid_resume}
                    )
            except Exception:
                error_tests.append({"test": "invalid_resume", "handled": True})

            # Test hangup event
            try:
                async with LocalAudioCodesClient(
                    self.bridge_url, logger=self.logger
                ) as client:
                    await client.initiate_session()
                    hangup_sent = await client.send_hangup_event()
                    error_tests.append({"test": "hangup_event", "handled": hangup_sent})
            except Exception as e:
                error_tests.append(
                    {"test": "hangup_event", "handled": False, "error": str(e)}
                )

            # Analyze error handling
            handled_count = sum(1 for test in error_tests if test["handled"])
            success = handled_count == len(error_tests)

            self.results.add_test_result(
                test_name,
                success,
                {
                    "error_tests": error_tests,
                    "handled_count": handled_count,
                    "total_tests": len(error_tests),
                },
                (
                    None
                    if success
                    else f"Error handling failed for {len(error_tests) - handled_count} tests"
                ),
            )

            if success:
                self.logger.info("✅ Error handling successful")
            else:
                self.logger.error("❌ Error handling failed")

        except Exception as e:
            self.logger.error(f"❌ Error handling test failed: {e}")
            self.results.add_test_result(test_name, False, {"error": str(e)}, None)

    async def _test_long_conversation(self):
        """Test long conversation with multiple turns."""
        test_name = "long_conversation"
        self.logger.info(f"📚 Testing long conversation...")

        try:
            if len(self.test_audio_files) < 2:
                self.logger.warning(
                    "⚠️ Need at least 2 audio files for long conversation test"
                )
                self.results.add_test_result(
                    test_name,
                    False,
                    {"audio_files_available": len(self.test_audio_files)},
                    "Insufficient audio files for long conversation test",
                )
                return

            # Create extended conversation (repeat files if needed)
            extended_files = []
            target_turns = self.DEFAULT_TARGET_TURNS
            while len(extended_files) < target_turns:
                extended_files.extend(self.test_audio_files)
            extended_files = extended_files[:target_turns]

            async with LocalAudioCodesClient(
                self.bridge_url, logger=self.logger
            ) as client:
                # Run extended conversation
                result = await client.multi_turn_conversation(
                    extended_files,
                    wait_for_greeting=True,
                    turn_delay=0.5,  # Shorter delay for longer conversation
                    chunk_delay=0.005,
                )

                # Success criteria for long conversation
                success = (
                    result.completed_turns
                    >= target_turns // 2  # At least half completed
                    and result.success_rate >= 40.0  # At least 40% success rate
                    and result.duration
                    and result.duration < 300.0  # Completed within 5 minutes
                )

                self.results.add_test_result(
                    test_name,
                    bool(success),
                    {
                        "target_turns": target_turns,
                        "total_turns": result.total_turns,
                        "completed_turns": result.completed_turns,
                        "success_rate": result.success_rate,
                        "duration": result.duration,
                        "greeting_received": result.greeting_received,
                    },
                    None if success else f"Long conversation failed: {result.error}",
                )

                if success:
                    self.logger.info(
                        f"✅ Long conversation successful ({result.completed_turns}/{target_turns} turns)"
                    )
                else:
                    self.logger.error(
                        f"❌ Long conversation failed ({result.completed_turns}/{target_turns} turns)"
                    )

        except Exception as e:
            self.logger.error(f"❌ Long conversation failed: {e}")
            self.results.add_test_result(test_name, False, {"error": str(e)}, None)

    def print_results(self):
        """Print validation results to console."""
        print("\n" + "=" * 80)
        print("🎯 AUDIOCODES BRIDGE VALIDATION RESULTS")
        print("=" * 80)

        # Overall summary
        status_emoji = "✅" if self.results.overall_success else "❌"
        print(
            f"\n{status_emoji} Overall Status: {'PASSED' if self.results.overall_success else 'FAILED'}"
        )
        print(f"   Bridge URL: {self.bridge_url}")
        print(f"   Duration: {self.results.duration:.2f}s")
        print(f"   Tests Run: {self.results.tests_run}")
        print(f"   Tests Passed: {self.results.tests_passed}")
        print(f"   Tests Failed: {self.results.tests_failed}")
        print(f"   Success Rate: {self.results.success_rate:.1f}%")

        # Test details
        print(f"\n📋 Test Results:")
        for test in self.results.test_results:
            status_emoji = "✅" if test["success"] else "❌"
            print(f"   {status_emoji} {test['test_name']}")
            if not test["success"] and test["error"]:
                print(f"      Error: {test['error']}")

        # Errors summary
        if self.results.errors:
            print(f"\n🚨 Errors Encountered:")
            for error in self.results.errors:
                print(f"   • {error}")

        # Recommendations
        print(f"\n💡 Recommendations:")
        if self.results.overall_success:
            print("   • Bridge is functioning correctly")
            print("   • All core functionality validated")
        else:
            print("   • Review failed tests and error messages")
            print("   • Check bridge server logs for details")
            if not self.test_audio_files:
                print("   • Provide test audio files for complete validation")

        print("=" * 80)

    def save_report(self, filename: str):
        """Save detailed validation report to JSON file."""
        report = {
            "validation_summary": {
                "bridge_url": self.bridge_url,
                "start_time": self.results.start_time.isoformat(),
                "end_time": (
                    self.results.end_time.isoformat() if self.results.end_time else None
                ),
                "duration": self.results.duration,
                "overall_success": self.results.overall_success,
                "tests_run": self.results.tests_run,
                "tests_passed": self.results.tests_passed,
                "tests_failed": self.results.tests_failed,
                "success_rate": self.results.success_rate,
            },
            "test_results": self.results.test_results,
            "errors": self.results.errors,
            "test_environment": {
                "audio_files_found": len(self.test_audio_files),
                "audio_files": [str(Path(f).name) for f in self.test_audio_files],
                "timeout": self.timeout,
                "verbose": self.verbose,
            },
        }

        Path(filename).write_text(json.dumps(report, indent=2))
        self.logger.info(f"📄 Validation report saved to: {filename}")


async def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Validate AudioCodes Bridge Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_audiocodes_bridge.py
  python validate_audiocodes_bridge.py --bridge-url ws://localhost:8080
  python validate_audiocodes_bridge.py --extended --verbose
  python validate_audiocodes_bridge.py --quick --report-file results.json
        """,
    )

    parser.add_argument(
        "--bridge-url",
        default="ws://localhost:8000/ws/telephony",
        help="Bridge WebSocket URL (default: ws://localhost:8000/ws/telephony)",
    )
    parser.add_argument("--audio-dir", help="Directory containing test audio files")
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Test timeout in seconds (default: 30.0)",
    )
    parser.add_argument(
        "--quick", action="store_true", help="Run quick validation tests only"
    )
    parser.add_argument(
        "--extended", action="store_true", help="Run extended validation tests"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--report-file", help="Save detailed report to JSON file")

    args = parser.parse_args()

    # Determine test suite
    if args.quick:
        test_suite = "quick"
    elif args.extended:
        test_suite = "extended"
    else:
        test_suite = "standard"

    # Create validator
    validator = AudioCodesBridgeValidator(
        bridge_url=args.bridge_url,
        audio_dir=args.audio_dir,
        timeout=args.timeout,
        verbose=args.verbose,
    )

    # Run validation
    try:
        results = await validator.validate_bridge(test_suite)

        # Print results
        validator.print_results()

        # Save report if requested
        if args.report_file:
            validator.save_report(args.report_file)

        # Exit with appropriate code
        sys.exit(0 if results.overall_success else 1)

    except KeyboardInterrupt:
        print("\n⚠️ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    load_env_file()  # Add this line to load environment variables
    asyncio.run(main())
