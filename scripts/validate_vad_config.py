#!/usr/bin/env python3
"""
VAD Configuration Validation Script

This script validates that the Voice Activity Detection (VAD) configuration
is properly implemented in the AudioCodes bridge. It tests:
1. VAD configuration loading from environment variables
2. VAD event handler registration
3. VAD event processing behavior
4. VAD message generation

Usage:
    python scripts/validate_vad_config.py

Environment Variables:
    VAD_ENABLED=true/false - Enable/disable VAD functionality
    TUI_VAD_ENABLED=true/false - Enable/disable VAD in TUI
    TUI_SHOW_VAD_EVENTS=true/false - Show VAD events in TUI
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from opusagent.bridges.audiocodes_bridge import AudioCodesBridge
from opusagent.models.audiocodes_api import (
    TelephonyEventType,
    UserStreamSpeechCommittedResponse,
    UserStreamSpeechStartedResponse,
    UserStreamSpeechStoppedResponse,
)
from opusagent.models.openai_api import SessionConfig
from tui.utils.config import TUIConfig


class VADValidator:
    """Validates VAD configuration and functionality."""

    def __init__(self):
        self.results = []
        self.session_config = SessionConfig(
            input_audio_format="pcm16",
            output_audio_format="pcm16",
            voice="verse",
            instructions="You are a test customer service agent.",
            modalities=["text", "audio"],
            temperature=0.8,
            model="gpt-4o-realtime-preview-2025-06-03",
        )

    def log_result(self, test_name: str, passed: bool, message: str):
        """Log a test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results.append((test_name, passed, message))
        print(f"{status} {test_name}: {message}")

    def create_mock_bridge(self, vad_enabled: bool = True) -> AudioCodesBridge:
        """Create a mock AudioCodes bridge for testing."""
        mock_platform_ws = MagicMock()
        mock_platform_ws.send_json = AsyncMock()

        mock_realtime_ws = MagicMock()
        mock_realtime_ws.send = AsyncMock()

        # Create bridge with VAD configuration
        bridge = AudioCodesBridge(
            mock_platform_ws,
            mock_realtime_ws,
            self.session_config,
            vad_enabled=vad_enabled,
        )

        # Mock the dependencies to avoid actual initialization
        bridge.session_manager.initialize_session = AsyncMock()
        bridge.session_manager.send_initial_conversation_item = AsyncMock()
        bridge.audio_handler.initialize_stream = AsyncMock()
        bridge.conversation_id = "test-conversation-id"

        return bridge

    def test_environment_variable_loading(self):
        """Test that VAD configuration is loaded from environment variables."""
        try:
            # Test default values
            original_vad = os.getenv("VAD_ENABLED")
            original_tui_vad = os.getenv("TUI_VAD_ENABLED")
            original_tui_show = os.getenv("TUI_SHOW_VAD_EVENTS")

            # Test with VAD enabled
            os.environ["VAD_ENABLED"] = "true"
            os.environ["TUI_VAD_ENABLED"] = "true"
            os.environ["TUI_SHOW_VAD_EVENTS"] = "true"

            config = TUIConfig()
            if config.vad_enabled and config.show_vad_events:
                self.log_result(
                    "Environment VAD Loading",
                    True,
                    "VAD configuration loaded correctly",
                )
            else:
                self.log_result(
                    "Environment VAD Loading",
                    False,
                    "VAD configuration not loaded correctly",
                )

            # Test with VAD disabled
            os.environ["VAD_ENABLED"] = "false"
            os.environ["TUI_VAD_ENABLED"] = "false"
            os.environ["TUI_SHOW_VAD_EVENTS"] = "false"

            config = TUIConfig()
            if not config.vad_enabled and not config.show_vad_events:
                self.log_result(
                    "Environment VAD Disabled",
                    True,
                    "VAD disable configuration loaded correctly",
                )
            else:
                self.log_result(
                    "Environment VAD Disabled",
                    False,
                    "VAD disable configuration not loaded correctly",
                )

            # Restore original values
            if original_vad:
                os.environ["VAD_ENABLED"] = original_vad
            elif "VAD_ENABLED" in os.environ:
                del os.environ["VAD_ENABLED"]

            if original_tui_vad:
                os.environ["TUI_VAD_ENABLED"] = original_tui_vad
            elif "TUI_VAD_ENABLED" in os.environ:
                del os.environ["TUI_VAD_ENABLED"]

            if original_tui_show:
                os.environ["TUI_SHOW_VAD_EVENTS"] = original_tui_show
            elif "TUI_SHOW_VAD_EVENTS" in os.environ:
                del os.environ["TUI_SHOW_VAD_EVENTS"]

        except Exception as e:
            self.log_result("Environment VAD Loading", False, f"Error: {e}")

    def test_vad_configuration_setting(self):
        """Test that VAD configuration is properly set in bridge."""
        try:
            # Test VAD enabled
            bridge_enabled = self.create_mock_bridge(vad_enabled=True)
            if bridge_enabled.vad_enabled:
                self.log_result(
                    "VAD Configuration Enabled",
                    True,
                    "VAD enabled configuration set correctly",
                )
            else:
                self.log_result(
                    "VAD Configuration Enabled",
                    False,
                    "VAD enabled configuration not set correctly",
                )

            # Test VAD disabled
            bridge_disabled = self.create_mock_bridge(vad_enabled=False)
            if not bridge_disabled.vad_enabled:
                self.log_result(
                    "VAD Configuration Disabled",
                    True,
                    "VAD disabled configuration set correctly",
                )
            else:
                self.log_result(
                    "VAD Configuration Disabled",
                    False,
                    "VAD disabled configuration not set correctly",
                )

        except Exception as e:
            self.log_result("VAD Configuration Setting", False, f"Error: {e}")

    async def test_vad_event_processing(self):
        """Test VAD event processing behavior."""
        try:
            # Test VAD enabled bridge
            bridge_enabled = self.create_mock_bridge(vad_enabled=True)
            bridge_enabled.send_speech_started = AsyncMock()
            bridge_enabled.send_speech_stopped = AsyncMock()
            bridge_enabled.send_speech_committed = AsyncMock()

            # Test speech events are processed
            await bridge_enabled.handle_speech_started({})
            await bridge_enabled.handle_speech_stopped({})
            await bridge_enabled.handle_speech_committed({})

            if (
                bridge_enabled.send_speech_started.called
                and bridge_enabled.send_speech_stopped.called
                and bridge_enabled.send_speech_committed.called
            ):
                self.log_result(
                    "VAD Event Processing Enabled",
                    True,
                    "VAD events processed when enabled",
                )
            else:
                self.log_result(
                    "VAD Event Processing Enabled",
                    False,
                    "VAD events not processed when enabled",
                )

            # Test VAD disabled bridge
            bridge_disabled = self.create_mock_bridge(vad_enabled=False)
            bridge_disabled.send_speech_started = AsyncMock()
            bridge_disabled.send_speech_stopped = AsyncMock()
            bridge_disabled.send_speech_committed = AsyncMock()

            # Test speech events are ignored
            await bridge_disabled.handle_speech_started({})
            await bridge_disabled.handle_speech_stopped({})
            await bridge_disabled.handle_speech_committed({})

            if (
                not bridge_disabled.send_speech_started.called
                and not bridge_disabled.send_speech_stopped.called
                and not bridge_disabled.send_speech_committed.called
            ):
                self.log_result(
                    "VAD Event Processing Disabled",
                    True,
                    "VAD events ignored when disabled",
                )
            else:
                self.log_result(
                    "VAD Event Processing Disabled",
                    False,
                    "VAD events not ignored when disabled",
                )

        except Exception as e:
            self.log_result("VAD Event Processing", False, f"Error: {e}")

    async def test_vad_message_generation(self):
        """Test VAD message generation."""
        try:
            bridge = self.create_mock_bridge(vad_enabled=True)

            # Test speech started message
            await bridge.send_speech_started()
            platform_calls = bridge.platform_websocket.send_json.call_args_list
            if platform_calls:
                last_call = platform_calls[-1][0][
                    0
                ]  # Get the message from the last call
                if (
                    last_call.get("type")
                    == TelephonyEventType.USER_STREAM_SPEECH_STARTED
                ):
                    self.log_result(
                        "VAD Message Generation",
                        True,
                        "Speech started message generated correctly",
                    )
                else:
                    self.log_result(
                        "VAD Message Generation",
                        False,
                        f"Unexpected message type: {last_call.get('type')}",
                    )
            else:
                self.log_result(
                    "VAD Message Generation", False, "No messages sent to platform"
                )

        except Exception as e:
            self.log_result("VAD Message Generation", False, f"Error: {e}")

    def test_vad_message_models(self):
        """Test VAD message models."""
        try:
            conversation_id = "test-conversation-id"

            # Test UserStreamSpeechStartedResponse
            started_msg = UserStreamSpeechStartedResponse(
                type=TelephonyEventType.USER_STREAM_SPEECH_STARTED,
                conversationId=conversation_id,
                participant=None,
                participantId=None,
            )

            # Test UserStreamSpeechStoppedResponse
            stopped_msg = UserStreamSpeechStoppedResponse(
                type=TelephonyEventType.USER_STREAM_SPEECH_STOPPED,
                conversationId=conversation_id,
                participant=None,
                participantId=None,
            )

            # Test UserStreamSpeechCommittedResponse
            committed_msg = UserStreamSpeechCommittedResponse(
                type=TelephonyEventType.USER_STREAM_SPEECH_COMMITTED,
                conversationId=conversation_id,
                participant=None,
                participantId=None,
            )

            # Validate all models can be serialized
            started_dict = started_msg.model_dump()
            stopped_dict = stopped_msg.model_dump()
            committed_dict = committed_msg.model_dump()

            if (
                started_dict["type"] == TelephonyEventType.USER_STREAM_SPEECH_STARTED
                and stopped_dict["type"]
                == TelephonyEventType.USER_STREAM_SPEECH_STOPPED
                and committed_dict["type"]
                == TelephonyEventType.USER_STREAM_SPEECH_COMMITTED
            ):
                self.log_result(
                    "VAD Message Models", True, "VAD message models validate correctly"
                )
            else:
                self.log_result(
                    "VAD Message Models", False, "VAD message models validation failed"
                )

        except Exception as e:
            self.log_result("VAD Message Models", False, f"Error: {e}")

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 60)
        print("VAD VALIDATION SUMMARY")
        print("=" * 60)

        total_tests = len(self.results)
        passed_tests = sum(1 for _, passed, _ in self.results if passed)
        failed_tests = total_tests - passed_tests

        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

        if failed_tests > 0:
            print("\nFailed Tests:")
            for test_name, passed, message in self.results:
                if not passed:
                    print(f"  - {test_name}: {message}")

        print("\nEnvironment Variables:")
        print(f"  VAD_ENABLED: {os.getenv('VAD_ENABLED', 'not set')}")
        print(f"  TUI_VAD_ENABLED: {os.getenv('TUI_VAD_ENABLED', 'not set')}")
        print(f"  TUI_SHOW_VAD_EVENTS: {os.getenv('TUI_SHOW_VAD_EVENTS', 'not set')}")

        return failed_tests == 0


async def main():
    """Main validation function."""
    print("VAD Configuration Validation Script")
    print("=" * 60)

    validator = VADValidator()

    # Run validation tests
    validator.test_environment_variable_loading()
    validator.test_vad_configuration_setting()
    await validator.test_vad_event_processing()
    await validator.test_vad_message_generation()
    validator.test_vad_message_models()

    # Print summary
    success = validator.print_summary()

    if success:
        print("\n🎉 All VAD validation tests passed!")
        return 0
    else:
        print("\n❌ Some VAD validation tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
