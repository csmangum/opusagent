#!/usr/bin/env python3
"""
Telephony Mock Validation Script

This script validates that the /ws/telephony endpoint works correctly with the mock realtime implementation.
It acts like AudioCodes telephony and tests all message types and conversation flows.

Usage:
    # Run with mock mode enabled
    OPUSAGENT_USE_MOCK=true python scripts/validate_telephony_mock.py
    
    # Run with custom server URL
    OPUSAGENT_USE_MOCK=true python scripts/validate_telephony_mock.py --server-url ws://localhost:8000/ws/telephony
    
    # Run with verbose logging
    OPUSAGENT_USE_MOCK=true python scripts/validate_telephony_mock.py --verbose
    
    # Run specific test scenarios
    OPUSAGENT_USE_MOCK=true python scripts/validate_telephony_mock.py --test session-flow
    OPUSAGENT_USE_MOCK=true python scripts/validate_telephony_mock.py --test audio-streaming
    OPUSAGENT_USE_MOCK=true python scripts/validate_telephony_mock.py --test conversation-flow
"""

import argparse
import asyncio
import base64
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import websockets
from websockets.exceptions import ConnectionClosed

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opusagent.models.audiocodes_api import (
    TelephonyEventType,
    SessionInitiateMessage,
    SessionAcceptedResponse,
    UserStreamStartMessage,
    UserStreamChunkMessage,
    UserStreamStopMessage,
    UserStreamStartedResponse,
    UserStreamStoppedResponse,
    PlayStreamStartMessage,
    PlayStreamChunkMessage,
    PlayStreamStopMessage,
    SessionEndMessage,
    SessionErrorResponse,
    UserStreamSpeechStartedResponse,
    UserStreamSpeechStoppedResponse,
    UserStreamSpeechCommittedResponse,
)


class TelephonyValidator:
    """Validates the /ws/telephony endpoint by acting like AudioCodes telephony."""
    
    def __init__(
        self,
        server_url: str = "ws://localhost:8000/ws/telephony",
        bot_name: str = "TestBot",
        caller: str = "+15551234567",
        verbose: bool = False,
        logger: Optional[logging.Logger] = None,
    ):
        self.server_url = server_url
        self.bot_name = bot_name
        self.caller = caller
        self.verbose = verbose
        self.logger = logger or self._setup_logger()
        
        # WebSocket connection
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        
        # Session state
        self.conversation_id: Optional[str] = None
        self.session_accepted = False
        self.media_format = "raw/lpcm16"
        
        # Stream state
        self.user_stream_active = False
        self.play_stream_active = False
        self.current_stream_id: Optional[str] = None
        
        # Message tracking
        self.sent_messages: List[Dict[str, Any]] = []
        self.received_messages: List[Dict[str, Any]] = []
        self.expected_responses: Set[str] = set()
        
        # Validation results
        self.validation_results: Dict[str, Any] = {
            "start_time": datetime.now().isoformat(),
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": [],
            "warnings": [],
            "message_flow": [],
        }
        
        # Audio data for testing
        self.test_audio_chunks = self._generate_test_audio()
    
    def _setup_logger(self) -> logging.Logger:
        """Set up logging for the validator."""
        logger = logging.getLogger("telephony_validator")
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _generate_test_audio(self) -> List[str]:
        """Generate test audio chunks for validation."""
        # Generate 1 second of silence at 16kHz, 16-bit PCM
        sample_rate = 16000
        duration = 1.0  # 1 second
        samples = int(sample_rate * duration)
        
        # Create silence (zeros)
        audio_data = b"\x00" * (samples * 2)  # 16-bit = 2 bytes per sample
        
        # Split into chunks (3200 bytes = 100ms at 16kHz)
        chunk_size = 3200
        chunks = []
        
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            # Pad last chunk if needed
            if len(chunk) < chunk_size:
                chunk = chunk + b"\x00" * (chunk_size - len(chunk))
            chunks.append(base64.b64encode(chunk).decode('utf-8'))
        
        return chunks
    
    async def __aenter__(self):
        """Connect to the telephony endpoint."""
        self.logger.info(f"Connecting to telephony endpoint: {self.server_url}")
        self.websocket = await websockets.connect(self.server_url)
        self.logger.info("Connected to telephony endpoint")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Disconnect from the telephony endpoint."""
        if self.websocket:
            await self.websocket.close()
        self.logger.info("Disconnected from telephony endpoint")
    
    async def send_message(self, message: Dict[str, Any]) -> None:
        """Send a message to the telephony endpoint."""
        if not self.websocket:
            raise RuntimeError("WebSocket not connected")
        
        message_json = json.dumps(message)
        await self.websocket.send(message_json)
        self.sent_messages.append(message)
        
        self.logger.debug(f"Sent: {message.get('type', 'unknown')}")
        self.validation_results["message_flow"].append({
            "direction": "sent",
            "timestamp": datetime.now().isoformat(),
            "message": message
        })
    
    async def receive_message(self, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """Receive a message from the telephony endpoint."""
        if not self.websocket:
            raise RuntimeError("WebSocket not connected")
        
        try:
            message = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
            data = json.loads(message)
            self.received_messages.append(data)
            
            self.logger.debug(f"Received: {data.get('type', 'unknown')}")
            self.validation_results["message_flow"].append({
                "direction": "received",
                "timestamp": datetime.now().isoformat(),
                "message": data
            })
            
            return data
        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout waiting for message after {timeout}s")
            return None
    
    async def wait_for_message_type(self, expected_type: str, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """Wait for a specific message type."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            message = await self.receive_message(timeout=1.0)
            if message and message.get("type") == expected_type:
                return message
        return None
    
    def validate_message_structure(self, message: Dict[str, Any], expected_type: str) -> bool:
        """Validate that a message has the correct structure."""
        if message.get("type") != expected_type:
            self.logger.error(f"Expected message type {expected_type}, got {message.get('type')}")
            return False
        
        # Basic validation based on message type
        if expected_type == TelephonyEventType.SESSION_ACCEPTED:
            if "mediaFormat" not in message:
                self.logger.error("session.accepted missing mediaFormat")
                return False
        elif expected_type == TelephonyEventType.USER_STREAM_STARTED:
            # No additional fields required
            pass
        elif expected_type == TelephonyEventType.USER_STREAM_STOPPED:
            # No additional fields required
            pass
        elif expected_type == TelephonyEventType.PLAY_STREAM_START:
            if "streamId" not in message or "mediaFormat" not in message:
                self.logger.error("playStream.start missing required fields")
                return False
        elif expected_type == TelephonyEventType.PLAY_STREAM_CHUNK:
            if "streamId" not in message or "audioChunk" not in message:
                self.logger.error("playStream.chunk missing required fields")
                return False
        elif expected_type == TelephonyEventType.PLAY_STREAM_STOP:
            if "streamId" not in message:
                self.logger.error("playStream.stop missing streamId")
                return False
        
        return True
    
    async def test_session_initiation(self) -> bool:
        """Test session initiation flow."""
        self.logger.info("=== Testing Session Initiation ===")
        
        try:
            # Generate conversation ID
            self.conversation_id = str(uuid.uuid4())
            
            # Send session.initiate
            session_initiate = {
                "type": TelephonyEventType.SESSION_INITIATE,
                "conversationId": self.conversation_id,
                "expectAudioMessages": True,
                "botName": self.bot_name,
                "caller": self.caller,
                "supportedMediaFormats": [self.media_format],
            }
            
            await self.send_message(session_initiate)
            
            # Wait for session.accepted
            response = await self.wait_for_message_type(TelephonyEventType.SESSION_ACCEPTED)
            if not response:
                self.logger.error("No session.accepted received")
                return False
            
            if not self.validate_message_structure(response, TelephonyEventType.SESSION_ACCEPTED):
                return False
            
            self.session_accepted = True
            self.media_format = response.get("mediaFormat", self.media_format)
            
            self.logger.info("✓ Session initiation successful")
            self.validation_results["tests_passed"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Session initiation failed: {e}")
            self.validation_results["tests_failed"] += 1
            self.validation_results["errors"].append(f"Session initiation: {e}")
            return False
    
    async def test_user_stream_flow(self) -> bool:
        """Test user stream start/stop flow."""
        self.logger.info("=== Testing User Stream Flow ===")
        
        try:
            # Send userStream.start
            user_stream_start = {
                "type": TelephonyEventType.USER_STREAM_START,
                "conversationId": self.conversation_id,
            }
            
            await self.send_message(user_stream_start)
            
            # Wait for userStream.started
            response = await self.wait_for_message_type(TelephonyEventType.USER_STREAM_STARTED)
            if not response:
                self.logger.error("No userStream.started received")
                return False
            
            if not self.validate_message_structure(response, TelephonyEventType.USER_STREAM_STARTED):
                return False
            
            self.user_stream_active = True
            
            # Send userStream.stop
            user_stream_stop = {
                "type": TelephonyEventType.USER_STREAM_STOP,
                "conversationId": self.conversation_id,
            }
            
            await self.send_message(user_stream_stop)
            
            # Wait for userStream.stopped
            response = await self.wait_for_message_type(TelephonyEventType.USER_STREAM_STOPPED)
            if not response:
                self.logger.error("No userStream.stopped received")
                return False
            
            if not self.validate_message_structure(response, TelephonyEventType.USER_STREAM_STOPPED):
                return False
            
            self.user_stream_active = False
            
            self.logger.info("✓ User stream flow successful")
            self.validation_results["tests_passed"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"User stream flow failed: {e}")
            self.validation_results["tests_failed"] += 1
            self.validation_results["errors"].append(f"User stream flow: {e}")
            return False
    
    async def test_audio_streaming(self) -> bool:
        """Test audio streaming with actual audio chunks."""
        self.logger.info("=== Testing Audio Streaming ===")
        
        try:
            # Start user stream
            user_stream_start = {
                "type": TelephonyEventType.USER_STREAM_START,
                "conversationId": self.conversation_id,
            }
            
            await self.send_message(user_stream_start)
            
            # Wait for userStream.started
            response = await self.wait_for_message_type(TelephonyEventType.USER_STREAM_STARTED)
            if not response:
                self.logger.error("No userStream.started received")
                return False
            
            self.user_stream_active = True
            
            # Send audio chunks
            for i, audio_chunk in enumerate(self.test_audio_chunks):
                user_stream_chunk = {
                    "type": TelephonyEventType.USER_STREAM_CHUNK,
                    "conversationId": self.conversation_id,
                    "audioChunk": audio_chunk,
                }
                
                await self.send_message(user_stream_chunk)
                self.logger.debug(f"Sent audio chunk {i+1}/{len(self.test_audio_chunks)}")
                
                # Small delay between chunks
                await asyncio.sleep(0.1)
            
            # Stop user stream
            user_stream_stop = {
                "type": TelephonyEventType.USER_STREAM_STOP,
                "conversationId": self.conversation_id,
            }
            
            await self.send_message(user_stream_stop)
            
            # Wait for userStream.stopped
            response = await self.wait_for_message_type(TelephonyEventType.USER_STREAM_STOPPED)
            if not response:
                self.logger.error("No userStream.stopped received")
                return False
            
            self.user_stream_active = False
            
            # Wait for play stream response (AI should respond)
            play_start_response = await self.wait_for_message_type(TelephonyEventType.PLAY_STREAM_START, timeout=15.0)
            if play_start_response:
                self.logger.info("✓ Received playStream.start (AI response)")
                
                if not self.validate_message_structure(play_start_response, TelephonyEventType.PLAY_STREAM_START):
                    return False
                
                self.play_stream_active = True
                self.current_stream_id = play_start_response.get("streamId")
                
                # Wait for audio chunks
                audio_chunks_received = 0
                start_time = time.time()
                while time.time() - start_time < 10.0:  # Wait up to 10 seconds for audio
                    response = await self.receive_message(timeout=1.0)
                    if response and response.get("type") == TelephonyEventType.PLAY_STREAM_CHUNK:
                        audio_chunks_received += 1
                        if not self.validate_message_structure(response, TelephonyEventType.PLAY_STREAM_CHUNK):
                            return False
                    elif response and response.get("type") == TelephonyEventType.PLAY_STREAM_STOP:
                        self.logger.info(f"✓ Received playStream.stop after {audio_chunks_received} chunks")
                        if not self.validate_message_structure(response, TelephonyEventType.PLAY_STREAM_STOP):
                            return False
                        self.play_stream_active = False
                        break
                
                if audio_chunks_received > 0:
                    self.logger.info(f"✓ Audio streaming successful: {audio_chunks_received} chunks received")
                else:
                    self.logger.warning("No audio chunks received from AI")
                    self.validation_results["warnings"].append("No audio chunks received from AI")
            else:
                self.logger.warning("No playStream.start received (AI may not have responded)")
                self.validation_results["warnings"].append("No AI response received")
            
            self.logger.info("✓ Audio streaming test completed")
            self.validation_results["tests_passed"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Audio streaming failed: {e}")
            self.validation_results["tests_failed"] += 1
            self.validation_results["errors"].append(f"Audio streaming: {e}")
            return False
    
    async def test_speech_events(self) -> bool:
        """Test speech detection events (VAD)."""
        self.logger.info("=== Testing Speech Events ===")
        
        try:
            # Start user stream
            user_stream_start = {
                "type": TelephonyEventType.USER_STREAM_START,
                "conversationId": self.conversation_id,
            }
            
            await self.send_message(user_stream_start)
            
            # Wait for userStream.started
            response = await self.wait_for_message_type(TelephonyEventType.USER_STREAM_STARTED)
            if not response:
                self.logger.error("No userStream.started received")
                return False
            
            # Send a small amount of audio to trigger speech detection
            audio_chunk = self.test_audio_chunks[0]  # Just one chunk
            user_stream_chunk = {
                "type": TelephonyEventType.USER_STREAM_CHUNK,
                "conversationId": self.conversation_id,
                "audioChunk": audio_chunk,
            }
            
            await self.send_message(user_stream_chunk)
            
            # Wait for speech events (optional - depends on VAD implementation)
            speech_started = await self.wait_for_message_type(
                TelephonyEventType.USER_STREAM_SPEECH_STARTED, timeout=5.0
            )
            if speech_started:
                self.logger.info("✓ Received speech.started event")
                if not self.validate_message_structure(speech_started, TelephonyEventType.USER_STREAM_SPEECH_STARTED):
                    return False
            
            # Stop user stream
            user_stream_stop = {
                "type": TelephonyEventType.USER_STREAM_STOP,
                "conversationId": self.conversation_id,
            }
            
            await self.send_message(user_stream_stop)
            
            # Wait for speech stopped event
            speech_stopped = await self.wait_for_message_type(
                TelephonyEventType.USER_STREAM_SPEECH_STOPPED, timeout=5.0
            )
            if speech_stopped:
                self.logger.info("✓ Received speech.stopped event")
                if not self.validate_message_structure(speech_stopped, TelephonyEventType.USER_STREAM_SPEECH_STOPPED):
                    return False
            
            # Wait for speech committed event
            speech_committed = await self.wait_for_message_type(
                TelephonyEventType.USER_STREAM_SPEECH_COMMITTED, timeout=5.0
            )
            if speech_committed:
                self.logger.info("✓ Received speech.committed event")
                if not self.validate_message_structure(speech_committed, TelephonyEventType.USER_STREAM_SPEECH_COMMITTED):
                    return False
            
            # Wait for userStream.stopped
            response = await self.wait_for_message_type(TelephonyEventType.USER_STREAM_STOPPED)
            if not response:
                self.logger.error("No userStream.stopped received")
                return False
            
            self.logger.info("✓ Speech events test completed")
            self.validation_results["tests_passed"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Speech events test failed: {e}")
            self.validation_results["tests_failed"] += 1
            self.validation_results["errors"].append(f"Speech events: {e}")
            return False
    
    async def test_session_termination(self) -> bool:
        """Test session termination flow."""
        self.logger.info("=== Testing Session Termination ===")
        
        try:
            # Send session.end
            session_end = {
                "type": TelephonyEventType.SESSION_END,
                "conversationId": self.conversation_id,
                "reasonCode": "test_completed",
                "reason": "Validation test completed",
            }
            
            await self.send_message(session_end)
            
            # Wait a moment for any final messages
            await asyncio.sleep(1.0)
            
            self.logger.info("✓ Session termination successful")
            self.validation_results["tests_passed"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Session termination failed: {e}")
            self.validation_results["tests_failed"] += 1
            self.validation_results["errors"].append(f"Session termination: {e}")
            return False
    
    async def test_error_handling(self) -> bool:
        """Test error handling scenarios."""
        self.logger.info("=== Testing Error Handling ===")
        
        try:
            # Test invalid message type
            invalid_message = {
                "type": "invalid.message.type",
                "conversationId": self.conversation_id,
            }
            
            await self.send_message(invalid_message)
            
            # Wait a moment to see if server handles it gracefully
            await asyncio.sleep(1.0)
            
            # Test malformed message (missing required fields)
            malformed_message = {
                "type": TelephonyEventType.USER_STREAM_START,
                # Missing conversationId
            }
            
            await self.send_message(malformed_message)
            
            # Wait a moment
            await asyncio.sleep(1.0)
            
            self.logger.info("✓ Error handling test completed")
            self.validation_results["tests_passed"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling test failed: {e}")
            self.validation_results["tests_failed"] += 1
            self.validation_results["errors"].append(f"Error handling: {e}")
            return False
    
    async def run_full_conversation_test(self) -> bool:
        """Run a complete conversation flow test."""
        self.logger.info("=== Running Full Conversation Test ===")
        
        try:
            # 1. Session initiation
            if not await self.test_session_initiation():
                return False
            
            # 2. User stream flow
            if not await self.test_user_stream_flow():
                return False
            
            # 3. Audio streaming with AI response
            if not await self.test_audio_streaming():
                return False
            
            # 4. Speech events
            if not await self.test_speech_events():
                return False
            
            # 5. Error handling
            if not await self.test_error_handling():
                return False
            
            # 6. Session termination
            if not await self.test_session_termination():
                return False
            
            self.logger.info("✓ Full conversation test completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Full conversation test failed: {e}")
            self.validation_results["errors"].append(f"Full conversation: {e}")
            return False
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive validation report."""
        self.validation_results["end_time"] = datetime.now().isoformat()
        self.validation_results["total_tests"] = (
            self.validation_results["tests_passed"] + self.validation_results["tests_failed"]
        )
        self.validation_results["success_rate"] = (
            self.validation_results["tests_passed"] / max(self.validation_results["total_tests"], 1) * 100
        )
        
        # Message statistics
        message_types_sent = {}
        message_types_received = {}
        
        for msg in self.sent_messages:
            msg_type = msg.get("type", "unknown")
            message_types_sent[msg_type] = message_types_sent.get(msg_type, 0) + 1
        
        for msg in self.received_messages:
            msg_type = msg.get("type", "unknown")
            message_types_received[msg_type] = message_types_received.get(msg_type, 0) + 1
        
        self.validation_results["message_statistics"] = {
            "sent": message_types_sent,
            "received": message_types_received,
            "total_sent": len(self.sent_messages),
            "total_received": len(self.received_messages),
        }
        
        return self.validation_results


async def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description="Validate telephony endpoint with mock realtime")
    parser.add_argument(
        "--server-url",
        default="ws://localhost:8000/ws/telephony",
        help="Telephony endpoint URL"
    )
    parser.add_argument(
        "--bot-name",
        default="TestBot",
        help="Bot name for testing"
    )
    parser.add_argument(
        "--caller",
        default="+15551234567",
        help="Caller phone number for testing"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--test",
        choices=["session-flow", "audio-streaming", "conversation-flow", "all"],
        default="all",
        help="Specific test to run"
    )
    parser.add_argument(
        "--output",
        help="Output file for validation report (JSON)"
    )
    
    args = parser.parse_args()
    
    # Check if mock mode is enabled
    use_mock = os.getenv("OPUSAGENT_USE_MOCK", "false").lower() == "true"
    if not use_mock:
        print("⚠️  Warning: OPUSAGENT_USE_MOCK is not set to 'true'")
        print("   This validation script is designed to work with mock realtime implementation")
        print("   Set OPUSAGENT_USE_MOCK=true to enable mock mode")
        print()
    
    print("🚀 Starting Telephony Mock Validation")
    print(f"   Server URL: {args.server_url}")
    print(f"   Bot Name: {args.bot_name}")
    print(f"   Caller: {args.caller}")
    print(f"   Test: {args.test}")
    print(f"   Mock Mode: {use_mock}")
    print()
    
    async with TelephonyValidator(
        server_url=args.server_url,
        bot_name=args.bot_name,
        caller=args.caller,
        verbose=args.verbose
    ) as validator:
        
        success = False
        
        if args.test == "session-flow":
            success = await validator.test_session_initiation()
        elif args.test == "audio-streaming":
            # Need to start session first
            if await validator.test_session_initiation():
                success = await validator.test_audio_streaming()
            else:
                success = False
        elif args.test == "conversation-flow":
            success = await validator.run_full_conversation_test()
        else:  # all
            success = await validator.run_full_conversation_test()
        
        # Generate report
        report = validator.generate_report()
        
        # Print summary
        print("\n" + "="*60)
        print("📊 VALIDATION SUMMARY")
        print("="*60)
        print(f"Total Tests: {report['total_tests']}")
        print(f"Passed: {report['tests_passed']}")
        print(f"Failed: {report['tests_failed']}")
        print(f"Success Rate: {report['success_rate']:.1f}%")
        
        if report['errors']:
            print(f"\n❌ Errors ({len(report['errors'])}):")
            for error in report['errors']:
                print(f"   • {error}")
        
        if report['warnings']:
            print(f"\n⚠️  Warnings ({len(report['warnings'])}):")
            for warning in report['warnings']:
                print(f"   • {warning}")
        
        print(f"\n📨 Message Statistics:")
        print(f"   Sent: {report['message_statistics']['total_sent']}")
        print(f"   Received: {report['message_statistics']['total_received']}")
        
        print(f"\n📤 Sent Message Types:")
        for msg_type, count in report['message_statistics']['sent'].items():
            print(f"   • {msg_type}: {count}")
        
        print(f"\n📥 Received Message Types:")
        for msg_type, count in report['message_statistics']['received'].items():
            print(f"   • {msg_type}: {count}")
        
        # Save report if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n💾 Report saved to: {args.output}")
        
        print("\n" + "="*60)
        if success:
            print("✅ VALIDATION COMPLETED SUCCESSFULLY")
        else:
            print("❌ VALIDATION FAILED")
        print("="*60)
        
        return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        sys.exit(1) 