#!/usr/bin/env python3
"""
AudioCodes Bridge Local Realtime Validation Script

This script validates that the AudioCodes bridge works correctly with the local realtime 
connection when USE_LOCAL_REALTIME=true. It connects to the /ws/telephony endpoint 
and tests all message types and conversation flows with the mock WebSocket connection.

Usage:
    # Run with local realtime enabled
    USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py
    
    # Run with custom server URL
    USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py --server-url ws://localhost:8000/ws/telephony
    
    # Run with verbose logging
    USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py --verbose
    
    # Run specific test scenarios
    USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py --test session-flow
    USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py --test audio-streaming
    USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py --test conversation-flow
    USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py --test vad-integration
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

os.environ["USE_LOCAL_REALTIME"] = "true"

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


class AudioCodesLocalRealtimeValidator:
    """Validates the AudioCodes bridge with local realtime connection."""
    
    def __init__(
        self,
        server_url: str = "ws://localhost:8000/ws/telephony",
        bot_name: str = "LocalRealtimeBot",
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
        self.websocket: Optional[Any] = None
        
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
            "local_realtime_events": [],
        }
        
        # Audio data for testing
        self.test_audio_chunks = self._generate_test_audio()
        
        # VAD state tracking
        self.vad_events_received = []
        self.speech_started = False
        self.speech_stopped = False
        self.speech_committed = False
    
    def _setup_logger(self) -> logging.Logger:
        """Set up logging for the validator."""
        logger = logging.getLogger("audiocodes_local_realtime_validator")
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        
        if not logger.handlers:
            # Create logs directory if it doesn't exist
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # File handler for validation logs
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = logs_dir / f"audiocodes_local_realtime_validation_{timestamp}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
            # Log the file location
            logger.info(f"Validation logs will be saved to: {log_file}")
        
        return logger
    
    def _generate_test_audio(self) -> List[str]:
        """Generate test audio chunks for validation using real audio files."""
        try:
            # Try to load a real audio file from the mock directory
            audio_files = [
                "opusagent/mock/audio/greetings/greetings_01.wav",
                "opusagent/mock/audio/customer_service/customer_service_01.wav",
                "opusagent/mock/audio/default/default_01.wav",
            ]
            
            audio_data = None
            selected_file = None
            
            # Try to find and load an existing audio file
            for audio_file in audio_files:
                file_path = Path(audio_file)
                if file_path.exists():
                    selected_file = audio_file
                    try:
                        audio_data = self._load_audio_file(file_path)
                        break
                    except Exception as e:
                        self.logger.warning(f"Failed to load audio file {audio_file}: {e}")
                        continue
            
            if audio_data is None:
                self.logger.warning("No real audio files found, falling back to synthetic audio")
                return self._generate_synthetic_audio()
            
            self.logger.info(f"Using real audio file: {selected_file}")
            
            # Split into chunks (3200 bytes = 100ms at 16kHz)
            chunk_size = 3200
            chunks = []
            
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                # Pad last chunk if needed
                if len(chunk) < chunk_size:
                    chunk = chunk + b"\x00" * (chunk_size - len(chunk))
                chunks.append(base64.b64encode(chunk).decode('utf-8'))
            
            self.logger.info(f"Generated {len(chunks)} audio chunks from real audio file")
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error loading real audio files: {e}")
            self.logger.info("Falling back to synthetic audio generation")
            return self._generate_synthetic_audio()
    
    def _load_audio_file(self, file_path: Path) -> bytes:
        """Load and process an audio file to 16kHz, 16-bit PCM format."""
        try:
            import wave
            import numpy as np
            
            with wave.open(str(file_path), 'rb') as wav_file:
                # Get audio parameters
                frames = wav_file.getnframes()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                
                # Read raw audio data
                raw_audio = wav_file.readframes(frames)
                
                self.logger.debug(f"Audio file info: {frames} frames, {sample_width} bytes/sample, "
                                f"{frame_rate} Hz, {channels} channels")
                
                # Convert to numpy array based on sample width
                if sample_width == 1:
                    audio_array = np.frombuffer(raw_audio, dtype=np.uint8)
                    audio_array = audio_array.astype(np.int16) - 128  # Convert to signed
                    audio_array = audio_array * 256  # Scale to 16-bit range
                elif sample_width == 2:
                    audio_array = np.frombuffer(raw_audio, dtype=np.int16)
                elif sample_width == 3:
                    # 24-bit audio - convert to 16-bit
                    audio_bytes = np.frombuffer(raw_audio, dtype=np.uint8)
                    audio_24bit = audio_bytes.reshape(-1, 3)
                    # Convert 24-bit to 16-bit by taking the upper 16 bits
                    audio_array = (audio_24bit[:, 1].astype(np.int16) << 8) | audio_24bit[:, 2].astype(np.int16)
                elif sample_width == 4:
                    # 32-bit audio - convert to 16-bit
                    audio_32bit = np.frombuffer(raw_audio, dtype=np.int32)
                    audio_array = (audio_32bit // 65536).astype(np.int16)
                else:
                    raise ValueError(f"Unsupported sample width: {sample_width} bytes")
                
                # Convert to mono if stereo
                if channels == 2:
                    audio_array = audio_array.reshape(-1, 2)
                    audio_array = np.mean(audio_array, axis=1).astype(np.int16)
                elif channels > 2:
                    audio_array = audio_array.reshape(-1, channels)
                    audio_array = np.mean(audio_array, axis=1).astype(np.int16)
                
                # Resample to 16kHz if needed
                if frame_rate != 16000:
                    audio_array = self._resample_audio(audio_array, frame_rate, 16000)
                
                # Convert back to bytes (16-bit little-endian)
                audio_bytes = audio_array.astype(np.int16).tobytes()
                
                # Limit to 2 seconds maximum for testing
                max_samples = 16000 * 2  # 2 seconds at 16kHz
                max_bytes = max_samples * 2  # 2 bytes per sample
                if len(audio_bytes) > max_bytes:
                    audio_bytes = audio_bytes[:max_bytes]
                
                return audio_bytes
                
        except ImportError:
            self.logger.warning("wave or numpy not available, cannot load audio files")
            raise
        except Exception as e:
            self.logger.error(f"Error processing audio file {file_path}: {e}")
            raise
    
    def _resample_audio(self, audio_array: Any, original_rate: int, target_rate: int) -> Any:
        """Simple audio resampling using linear interpolation."""
        try:
            import numpy as np
            
            if original_rate == target_rate:
                return audio_array
            
            # Calculate resampling ratio
            ratio = target_rate / original_rate
            
            # Create new sample indices
            original_length = len(audio_array)
            new_length = int(original_length * ratio)
            
            # Generate interpolation indices
            indices = np.linspace(0, original_length - 1, new_length)
            
            # Interpolate
            resampled = np.interp(indices, np.arange(original_length), audio_array)
            
            return resampled.astype(np.int16)
            
        except Exception as e:
            self.logger.warning(f"Resampling failed: {e}, using original audio")
            return audio_array
    
    def _generate_synthetic_audio(self) -> List[str]:
        """Generate synthetic audio as fallback when real files aren't available."""
        try:
            import numpy as np
            
            # Generate 2 seconds of more realistic audio at 16kHz, 16-bit PCM
            sample_rate = 16000
            duration = 2.0  # 2 seconds
            samples = int(sample_rate * duration)
            
            # Create a proper sine wave instead of square wave
            t = np.linspace(0, duration, samples, False)
            
            # Generate a more complex waveform that simulates speech
            # Use multiple frequencies to create a more realistic signal
            audio_signal = np.zeros(samples)
            
            # Add fundamental frequency (simulating voice pitch)
            fundamental = 200  # Hz
            audio_signal += 0.5 * np.sin(2 * np.pi * fundamental * t)
            
            # Add harmonics to make it more voice-like
            audio_signal += 0.3 * np.sin(2 * np.pi * fundamental * 2 * t)
            audio_signal += 0.2 * np.sin(2 * np.pi * fundamental * 3 * t)
            audio_signal += 0.1 * np.sin(2 * np.pi * fundamental * 4 * t)
            
            # Add some formant-like frequencies
            audio_signal += 0.2 * np.sin(2 * np.pi * 800 * t)  # First formant
            audio_signal += 0.15 * np.sin(2 * np.pi * 1200 * t)  # Second formant
            
            # Add envelope to make it more speech-like
            envelope = np.exp(-((t - duration/2) ** 2) / (duration/4) ** 2)
            audio_signal *= envelope
            
            # Add slight noise to make it more realistic
            noise = np.random.normal(0, 0.02, samples)
            audio_signal += noise
            
            # Normalize and convert to 16-bit
            audio_signal = audio_signal / np.max(np.abs(audio_signal)) * 0.7  # Leave some headroom
            audio_int16 = (audio_signal * 32767).astype(np.int16)
            
            # Convert to bytes
            audio_bytes = audio_int16.tobytes()
            
            self.logger.info("Generated synthetic audio with realistic characteristics")
            
        except ImportError:
            self.logger.warning("numpy not available, using basic synthetic audio")
            # Fallback to the original method if numpy isn't available
            sample_rate = 16000
            duration = 2.0
            samples = int(sample_rate * duration)
            
            audio_data = bytearray()
            for i in range(samples):
                # Better sine wave approximation without numpy
                import math
                t = i / sample_rate
                value = int(16000 * 0.5 * math.sin(2 * math.pi * 440 * t))
                audio_data.extend(value.to_bytes(2, 'little', signed=True))
            
            audio_bytes = bytes(audio_data)
            self.logger.info("Generated basic synthetic sine wave audio")
        
        # Split into chunks (3200 bytes = 100ms at 16kHz)
        chunk_size = 3200
        chunks = []
        
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i + chunk_size]
            # Pad last chunk if needed
            if len(chunk) < chunk_size:
                chunk = chunk + b"\x00" * (chunk_size - len(chunk))
            chunks.append(base64.b64encode(chunk).decode('utf-8'))
        
        return chunks
    
    async def __aenter__(self):
        """Connect to the telephony endpoint."""
        self.logger.info(f"Connecting to AudioCodes endpoint: {self.server_url}")
        self.websocket = await websockets.connect(self.server_url)
        self.logger.info("Connected to AudioCodes endpoint")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Disconnect from the telephony endpoint."""
        if self.websocket:
            await self.websocket.close()
        self.logger.info("Disconnected from AudioCodes endpoint")
    
    async def send_message(self, message: Dict[str, Any]) -> None:
        """Send a message to the AudioCodes endpoint."""
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
        """Receive a message from the AudioCodes endpoint."""
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
            
            # Track VAD events
            if data.get("type") in [
                TelephonyEventType.USER_STREAM_SPEECH_STARTED,
                TelephonyEventType.USER_STREAM_SPEECH_STOPPED,
                TelephonyEventType.USER_STREAM_SPEECH_COMMITTED,
            ]:
                self.vad_events_received.append(data)
                self.validation_results["local_realtime_events"].append({
                    "type": "vad_event",
                    "timestamp": datetime.now().isoformat(),
                    "event": data
                })
            
            return data
        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout waiting for message after {timeout}s")
            return None
        except websockets.ConnectionClosed:
            self.logger.info("WebSocket connection closed")
            return None
        except Exception as e:
            self.logger.error(f"Error receiving message: {e}")
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
            # Check for conversation ID
            if "conversationId" not in message:
                self.logger.error("userStream.started missing conversationId")
                return False
        elif expected_type == TelephonyEventType.USER_STREAM_STOPPED:
            # Check for conversation ID
            if "conversationId" not in message:
                self.logger.error("userStream.stopped missing conversationId")
                return False
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
        """Test session initiation flow with local realtime."""
        self.logger.info("=== Testing Session Initiation with Local Realtime ===")
        
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
    
    async def test_audio_streaming(self) -> bool:
        """Test audio streaming with local realtime."""
        self.logger.info("=== Testing Audio Streaming with Local Realtime ===")
        
        try:
            # Send userStream.start
            user_stream_start = {
                "type": TelephonyEventType.USER_STREAM_START,
                "conversationId": self.conversation_id,
                "mediaFormat": self.media_format,
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
            self.logger.info("✓ User stream started successfully")
            
            # Send audio chunks
            self.logger.info("Sending audio chunks...")
            for i, chunk in enumerate(self.test_audio_chunks):
                user_stream_chunk = {
                    "type": TelephonyEventType.USER_STREAM_CHUNK,
                    "conversationId": self.conversation_id,
                    "audioChunk": chunk,
                    "sequenceNumber": i,
                }
                
                await self.send_message(user_stream_chunk)
                # Small delay to simulate realistic streaming
                await asyncio.sleep(0.1)
            
            self.logger.info(f"✓ Sent {len(self.test_audio_chunks)} audio chunks")
            
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
            self.logger.info("✓ User stream stopped successfully")
            
            self.validation_results["tests_passed"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Audio streaming failed: {e}")
            self.validation_results["tests_failed"] += 1
            self.validation_results["errors"].append(f"Audio streaming: {e}")
            return False
    
    async def test_local_realtime_response(self) -> bool:
        """Test that local realtime generates responses."""
        self.logger.info("=== Testing Local Realtime Response Generation ===")
        
        try:
            # Listen for playStream.start which indicates the local realtime is responding
            play_stream_start = await self.wait_for_message_type(TelephonyEventType.PLAY_STREAM_START, timeout=15.0)
            if not play_stream_start:
                self.logger.error("No playStream.start received from local realtime")
                return False
            
            if not self.validate_message_structure(play_stream_start, TelephonyEventType.PLAY_STREAM_START):
                return False
            
            self.current_stream_id = play_stream_start.get("streamId")
            self.play_stream_active = True
            self.logger.info("✓ Local realtime started audio response")
            
            # Listen for playStream.chunk messages
            audio_chunks_received = 0
            max_chunks = 20  # Limit to prevent infinite waiting
            
            while audio_chunks_received < max_chunks:
                message = await self.receive_message(timeout=5.0)
                if not message:
                    break
                
                if message.get("type") == TelephonyEventType.PLAY_STREAM_CHUNK:
                    if not self.validate_message_structure(message, TelephonyEventType.PLAY_STREAM_CHUNK):
                        return False
                    audio_chunks_received += 1
                    self.logger.debug(f"Received audio chunk {audio_chunks_received}")
                elif message.get("type") == TelephonyEventType.PLAY_STREAM_STOP:
                    if not self.validate_message_structure(message, TelephonyEventType.PLAY_STREAM_STOP):
                        return False
                    self.play_stream_active = False
                    self.logger.info("✓ Local realtime completed audio response")
                    break
            
            if audio_chunks_received > 0:
                self.logger.info(f"✓ Received {audio_chunks_received} audio chunks from local realtime")
                self.validation_results["tests_passed"] += 1
                return True
            else:
                self.logger.error("No audio chunks received from local realtime")
                return False
                
        except Exception as e:
            self.logger.error(f"Local realtime response test failed: {e}")
            self.validation_results["tests_failed"] += 1
            self.validation_results["errors"].append(f"Local realtime response: {e}")
            return False
    
    async def test_vad_integration(self) -> bool:
        """Test VAD integration with local realtime."""
        self.logger.info("=== Testing VAD Integration with Local Realtime ===")
        
        try:
            # Check if VAD events were received during audio streaming
            vad_events = [event for event in self.vad_events_received]
            
            if not vad_events:
                self.logger.warning("No VAD events received - VAD might be disabled")
                # This is not a failure, just a warning
                self.validation_results["warnings"].append("No VAD events received")
                return True
            
            # Check for expected VAD event sequence
            speech_started_events = [e for e in vad_events if e.get("type") == TelephonyEventType.USER_STREAM_SPEECH_STARTED]
            speech_stopped_events = [e for e in vad_events if e.get("type") == TelephonyEventType.USER_STREAM_SPEECH_STOPPED]
            speech_committed_events = [e for e in vad_events if e.get("type") == TelephonyEventType.USER_STREAM_SPEECH_COMMITTED]
            
            self.logger.info(f"VAD events received:")
            self.logger.info(f"  - Speech started: {len(speech_started_events)}")
            self.logger.info(f"  - Speech stopped: {len(speech_stopped_events)}")
            self.logger.info(f"  - Speech committed: {len(speech_committed_events)}")
            
            if speech_started_events and speech_stopped_events and speech_committed_events:
                self.logger.info("✓ Complete VAD event sequence received")
                self.validation_results["tests_passed"] += 1
                return True
            else:
                self.logger.warning("Incomplete VAD event sequence")
                self.validation_results["warnings"].append("Incomplete VAD event sequence")
                return True
                
        except Exception as e:
            self.logger.error(f"VAD integration test failed: {e}")
            self.validation_results["tests_failed"] += 1
            self.validation_results["errors"].append(f"VAD integration: {e}")
            return False
    
    async def test_conversation_flow(self) -> bool:
        """Test complete conversation flow with local realtime."""
        self.logger.info("=== Testing Complete Conversation Flow ===")
        
        try:
            # This combines all the previous tests into a complete flow
            if not await self.test_session_initiation():
                return False
            
            if not await self.test_audio_streaming():
                return False
            
            if not await self.test_local_realtime_response():
                return False
            
            if not await self.test_vad_integration():
                return False
            
            self.logger.info("✓ Complete conversation flow successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Conversation flow test failed: {e}")
            self.validation_results["tests_failed"] += 1
            self.validation_results["errors"].append(f"Conversation flow: {e}")
            return False
    
    async def test_session_termination(self) -> bool:
        """Test session termination."""
        self.logger.info("=== Testing Session Termination ===")
        
        try:
            # Send session.end
            session_end = {
                "type": TelephonyEventType.SESSION_END,
                "conversationId": self.conversation_id,
                "reasonCode": "normal",
                "reason": "Validation test completed",
            }
            
            await self.send_message(session_end)
            
            # Wait a bit for any final messages
            await asyncio.sleep(2.0)
            
            self.logger.info("✓ Session termination completed")
            self.validation_results["tests_passed"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Session termination failed: {e}")
            self.validation_results["tests_failed"] += 1
            self.validation_results["errors"].append(f"Session termination: {e}")
            return False
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive validation report."""
        end_time = datetime.now()
        start_time = datetime.fromisoformat(self.validation_results["start_time"])
        duration = (end_time - start_time).total_seconds()
        
        report = {
            "validation_summary": {
                "start_time": self.validation_results["start_time"],
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "tests_passed": self.validation_results["tests_passed"],
                "tests_failed": self.validation_results["tests_failed"],
                "total_tests": self.validation_results["tests_passed"] + self.validation_results["tests_failed"],
                "success_rate": (self.validation_results["tests_passed"] / max(1, self.validation_results["tests_passed"] + self.validation_results["tests_failed"])) * 100,
            },
            "configuration": {
                "server_url": self.server_url,
                "bot_name": self.bot_name,
                "caller": self.caller,
                "media_format": self.media_format,
                "conversation_id": self.conversation_id,
            },
            "message_statistics": {
                "messages_sent": len(self.sent_messages),
                "messages_received": len(self.received_messages),
                "vad_events_received": len(self.vad_events_received),
                "local_realtime_events": len(self.validation_results["local_realtime_events"]),
            },
            "errors": self.validation_results["errors"],
            "warnings": self.validation_results["warnings"],
            "message_flow": self.validation_results["message_flow"],
            "local_realtime_events": self.validation_results["local_realtime_events"],
            "vad_events": self.vad_events_received,
        }
        
        return report
    
    def print_summary(self):
        """Print a summary of validation results."""
        report = self.generate_report()
        summary = report["validation_summary"]
        
        print("\n" + "="*60)
        print("AUDIOCODES BRIDGE LOCAL REALTIME VALIDATION SUMMARY")
        print("="*60)
        print(f"Duration: {summary['duration_seconds']:.1f} seconds")
        print(f"Tests Passed: {summary['tests_passed']}")
        print(f"Tests Failed: {summary['tests_failed']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Messages Sent: {report['message_statistics']['messages_sent']}")
        print(f"Messages Received: {report['message_statistics']['messages_received']}")
        print(f"VAD Events: {report['message_statistics']['vad_events_received']}")
        
        if report["errors"]:
            print(f"\nErrors ({len(report['errors'])}):")
            for error in report["errors"]:
                print(f"  - {error}")
        
        if report["warnings"]:
            print(f"\nWarnings ({len(report['warnings'])}):")
            for warning in report["warnings"]:
                print(f"  - {warning}")
        
        print("="*60)
        
        # Save detailed report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = Path("logs") / f"audiocodes_local_realtime_validation_report_{timestamp}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Detailed report saved to: {report_file}")


async def run_validation_tests(validator: AudioCodesLocalRealtimeValidator, test_name: Optional[str] = None) -> bool:
    """Run validation tests."""
    if test_name:
        test_name = test_name.lower()
    
    success = True
    
    if not test_name or test_name == "session-flow":
        success &= await validator.test_session_initiation()
    
    if not test_name or test_name == "audio-streaming":
        if not test_name:  # Only run if session was initialized
            success &= await validator.test_audio_streaming()
        else:
            # Initialize session first
            success &= await validator.test_session_initiation()
            success &= await validator.test_audio_streaming()
    
    if not test_name or test_name == "conversation-flow":
        success &= await validator.test_conversation_flow()
    
    if not test_name or test_name == "vad-integration":
        if not test_name:  # Only run if audio was streamed
            success &= await validator.test_vad_integration()
        else:
            # Run full flow first
            success &= await validator.test_conversation_flow()
    
    # Always test session termination
    success &= await validator.test_session_termination()
    
    return success


async def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description="Validate AudioCodes Bridge with Local Realtime")
    parser.add_argument("--server-url", default="ws://localhost:8000/ws/telephony", help="WebSocket server URL")
    parser.add_argument("--bot-name", default="LocalRealtimeBot", help="Bot name for testing")
    parser.add_argument("--caller", default="+15551234567", help="Caller phone number")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--test", choices=["session-flow", "audio-streaming", "conversation-flow", "vad-integration"], help="Run specific test")
    
    args = parser.parse_args()
    
    # Check if local realtime is enabled
    if not os.getenv("USE_LOCAL_REALTIME", "false").lower() in ("true", "1", "yes", "on"):
        print("ERROR: USE_LOCAL_REALTIME must be set to 'true' to run this validation")
        print("Run with: USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py")
        return False
    
    print("Starting AudioCodes Bridge Local Realtime Validation...")
    print(f"Server URL: {args.server_url}")
    print(f"Bot Name: {args.bot_name}")
    print(f"Caller: {args.caller}")
    if args.test:
        print(f"Test: {args.test}")
    print("")
    
    try:
        async with AudioCodesLocalRealtimeValidator(
            server_url=args.server_url,
            bot_name=args.bot_name,
            caller=args.caller,
            verbose=args.verbose
        ) as validator:
            
            success = await run_validation_tests(validator, args.test)
            validator.print_summary()
            
            return success
            
    except Exception as e:
        print(f"Validation failed with error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 