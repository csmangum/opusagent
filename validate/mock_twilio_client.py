#!/usr/bin/env python3
"""
MockTwilio Client - Connects to the bridge server simulating Twilio Media Streams

This version acts as a WebSocket client that connects to the bridge server,
properly simulating how Twilio Media Streams would connect and communicate.
"""

import asyncio
import base64
import json
import logging
import uuid
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import websockets
from scipy import signal


class MockTwilioClient:
    """
    MockTwilio client that connects to the bridge server.

    This properly simulates Twilio Media Streams connecting to your bridge
    and follows the Twilio Media Streams WebSocket protocol.
    """

    def __init__(
        self,
        bridge_url: str,
        stream_sid: str = None,
        account_sid: str = None,
        call_sid: str = None,
        logger: logging.Logger = None,
    ):
        self.bridge_url = bridge_url
        self.logger = logger or logging.getLogger(__name__)
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self.received_messages: List[Dict[str, Any]] = []

        # Twilio identifiers
        self.stream_sid = stream_sid or f"MZ{uuid.uuid4().hex}"
        self.account_sid = account_sid or f"AC{uuid.uuid4().hex}"
        self.call_sid = call_sid or f"CA{uuid.uuid4().hex}"

        # Protocol state
        self.sequence_number = 0
        self.connected = False
        self.stream_started = False
        self.stream_stopped = False

        # Audio collection
        self.received_media_chunks: List[str] = []
        self.received_marks: List[str] = []
        self.greeting_audio_chunks: List[str] = []
        self.response_audio_chunks: List[str] = []
        self._collecting_greeting = False
        self._collecting_response = False

        # Conversation state
        self.conversation_turns: List[Dict[str, Any]] = []

    async def __aenter__(self):
        """Connect to the bridge server."""
        self.logger.info(f"[MOCK TWILIO] Connecting to bridge at {self.bridge_url}...")
        self._ws = await websockets.connect(self.bridge_url)
        self.logger.info("[MOCK TWILIO] Connected to bridge server")

        # Start message handler
        self._message_task = asyncio.create_task(self._message_handler())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Disconnect from bridge server."""
        if hasattr(self, "_message_task"):
            self._message_task.cancel()
        if self._ws:
            await self._ws.close()
        self.logger.info("[MOCK TWILIO] Disconnected from bridge server")

    async def _message_handler(self):
        """Handle incoming messages from the bridge."""
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    await self._process_bridge_message(data)
                except json.JSONDecodeError:
                    self.logger.warning(f"[MOCK TWILIO] Received non-JSON message: {message}")
                except Exception as e:
                    self.logger.error(f"[MOCK TWILIO] Error processing message: {e}")
        except websockets.ConnectionClosed:
            self.logger.info("[MOCK TWILIO] Bridge connection closed")
        except Exception as e:
            self.logger.error(f"[MOCK TWILIO] Message handler error: {e}")

    async def _process_bridge_message(self, data: Dict[str, Any]):
        """Process messages received from the bridge (audio, marks, etc.)."""
        msg_type = data.get("event")
        self.received_messages.append(data)

        self.logger.debug(f"[MOCK TWILIO] Received from bridge: {msg_type}")

        if msg_type == "media":
            # Bridge is sending audio back to us
            media_payload = data.get("media", {}).get("payload", "")
            if media_payload:
                self.received_media_chunks.append(media_payload)
                
                # Determine if this is greeting or response audio
                if not self.greeting_audio_chunks and not self._collecting_response:
                    if not self._collecting_greeting:
                        self._collecting_greeting = True
                        self.logger.info("[MOCK TWILIO] Started collecting greeting audio...")
                    self.greeting_audio_chunks.append(media_payload)
                elif self._collecting_response:
                    self.response_audio_chunks.append(media_payload)
                
                self.logger.debug(f"[MOCK TWILIO] Received audio chunk ({len(media_payload)} bytes base64)")

        elif msg_type == "mark":
            # Bridge is sending a mark (audio playback completion)
            mark_name = data.get("mark", {}).get("name", "")
            self.received_marks.append(mark_name)
            self.logger.info(f"[MOCK TWILIO] Received mark: {mark_name}")
            
            # Use marks to detect when greeting/response is complete
            if self._collecting_greeting and "audio_complete" in mark_name:
                self._collecting_greeting = False
                self.logger.info(f"[MOCK TWILIO] Greeting completed: {len(self.greeting_audio_chunks)} chunks")
            elif self._collecting_response and "audio_complete" in mark_name:
                self._collecting_response = False
                self.logger.info(f"[MOCK TWILIO] Response completed: {len(self.response_audio_chunks)} chunks")

        elif msg_type == "clear":
            # Bridge is clearing audio queue
            self.logger.info("[MOCK TWILIO] Received clear command")

    def _get_next_sequence(self) -> str:
        """Get next sequence number as string."""
        self.sequence_number += 1
        return str(self.sequence_number)

    async def send_connected(self) -> bool:
        """Send the initial 'connected' message."""
        connected_msg = {
            "event": "connected",
            "protocol": "Call",
            "version": "1.0.0"
        }
        
        await self._ws.send(json.dumps(connected_msg))
        self.connected = True
        self.logger.info("[MOCK TWILIO] Sent connected message")
        return True

    async def send_start(self, tracks: List[str] = None) -> bool:
        """Send the 'start' message with stream metadata."""
        if not self.connected:
            self.logger.error("[MOCK TWILIO] Must send connected message first")
            return False

        tracks = tracks or ["inbound", "outbound"]
        
        start_msg = {
            "event": "start",
            "sequenceNumber": self._get_next_sequence(),
            "streamSid": self.stream_sid,
            "start": {
                "streamSid": self.stream_sid,
                "accountSid": self.account_sid,
                "callSid": self.call_sid,
                "tracks": tracks,
                "customParameters": {},
                "mediaFormat": {
                    "encoding": "audio/x-mulaw",
                    "sampleRate": 8000,
                    "channels": 1
                }
            }
        }
        
        await self._ws.send(json.dumps(start_msg))
        self.stream_started = True
        self.logger.info(f"[MOCK TWILIO] Sent start message for stream: {self.stream_sid}")
        return True

    async def send_media_chunk(self, audio_chunk: str, track: str = "inbound") -> bool:
        """Send a media message with audio data."""
        if not self.stream_started:
            self.logger.error("[MOCK TWILIO] Stream not started")
            return False

        media_msg = {
            "event": "media",
            "sequenceNumber": self._get_next_sequence(),
            "streamSid": self.stream_sid,
            "media": {
                "track": track,
                "chunk": str(self.sequence_number),
                "timestamp": str(self.sequence_number * 20),  # 20ms per chunk
                "payload": audio_chunk
            }
        }
        
        await self._ws.send(json.dumps(media_msg))
        return True

    async def send_stop(self) -> bool:
        """Send the 'stop' message."""
        if not self.stream_started:
            self.logger.error("[MOCK TWILIO] Stream not started")
            return False

        stop_msg = {
            "event": "stop",
            "sequenceNumber": self._get_next_sequence(),
            "streamSid": self.stream_sid,
            "stop": {
                "accountSid": self.account_sid,
                "callSid": self.call_sid
            }
        }
        
        await self._ws.send(json.dumps(stop_msg))
        self.stream_stopped = True
        self.logger.info("[MOCK TWILIO] Sent stop message")
        return True

    async def send_dtmf(self, digit: str) -> bool:
        """Send a DTMF message."""
        if not self.stream_started:
            self.logger.error("[MOCK TWILIO] Stream not started")
            return False

        dtmf_msg = {
            "event": "dtmf",
            "streamSid": self.stream_sid,
            "sequenceNumber": self._get_next_sequence(),
            "dtmf": {
                "track": "inbound_track",
                "digit": digit
            }
        }
        
        await self._ws.send(json.dumps(dtmf_msg))
        self.logger.info(f"[MOCK TWILIO] Sent DTMF: {digit}")
        return True

    async def initiate_call_flow(self) -> bool:
        """Send the standard Twilio call initiation sequence."""
        try:
            # Step 1: Send connected
            if not await self.send_connected():
                return False
            
            # Step 2: Send start
            if not await self.send_start():
                return False
            
            self.logger.info("[MOCK TWILIO] Call flow initiated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"[MOCK TWILIO] Error initiating call flow: {e}")
            return False

    async def wait_for_ai_greeting(self, timeout: float = 20.0) -> List[str]:
        """Wait for and collect AI greeting audio."""
        self.logger.info("[MOCK TWILIO] Waiting for AI greeting...")

        end_time = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < end_time:
            if self.greeting_audio_chunks and not self._collecting_greeting:
                self.logger.info(f"[MOCK TWILIO] Greeting received: {len(self.greeting_audio_chunks)} chunks")
                return self.greeting_audio_chunks.copy()
            await asyncio.sleep(0.1)

        self.logger.error("[MOCK TWILIO] Timeout waiting for AI greeting")
        return []

    async def send_user_audio(self, audio_file_path: str, chunk_delay: float = 0.02) -> bool:
        """Send user audio from file as mulaw chunks."""
        audio_chunks = self._load_audio_as_mulaw_chunks(audio_file_path)
        if not audio_chunks:
            return False

        self.logger.info(f"[MOCK TWILIO] Sending user audio: {Path(audio_file_path).name} ({len(audio_chunks)} chunks)")

        # Send audio chunks
        for i, chunk in enumerate(audio_chunks):
            await self.send_media_chunk(chunk)

            if i % 20 == 0 or i == len(audio_chunks) - 1:
                self.logger.debug(f"[MOCK TWILIO] Sent chunk {i+1}/{len(audio_chunks)}")
            await asyncio.sleep(chunk_delay)

        self.logger.info("[MOCK TWILIO] User audio sent successfully")
        return True

    async def wait_for_ai_response(self, timeout: float = 45.0) -> List[str]:
        """Wait for and collect AI response audio."""
        self.logger.info("[MOCK TWILIO] Waiting for AI response...")

        # Clear previous response chunks and start collecting
        self.response_audio_chunks.clear()
        self._collecting_response = True

        end_time = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < end_time:
            if self.response_audio_chunks and not self._collecting_response:
                self.logger.info(f"[MOCK TWILIO] Response received: {len(self.response_audio_chunks)} chunks")
                return self.response_audio_chunks.copy()
            await asyncio.sleep(0.1)

        self.logger.error("[MOCK TWILIO] Timeout waiting for AI response")
        return []

    def _load_audio_as_mulaw_chunks(self, file_path: str, chunk_duration: float = 0.02) -> List[str]:
        """Load audio file and convert to mulaw chunks for Twilio."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                self.logger.error(f"[MOCK TWILIO] Audio file not found: {file_path}")
                return []

            with wave.open(str(file_path), "rb") as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()

                self.logger.info(f"[MOCK TWILIO] Loading audio: {file_path.name}")
                self.logger.info(f"   Format: {channels}ch, {sample_width*8}bit, {frame_rate}Hz")

                audio_data = wav_file.readframes(wav_file.getnframes())

                # Convert to mono if stereo
                if channels == 2:
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    # Average the channels
                    audio_array = audio_array.reshape(-1, 2).mean(axis=1).astype(np.int16)
                    audio_data = audio_array.tobytes()

                # Resample to 8kHz for mulaw (Twilio requirement)
                if frame_rate != 8000:
                    self.logger.info(f"   Resampling from {frame_rate}Hz to 8000Hz...")
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    number_of_samples = round(len(audio_array) * 8000 / frame_rate)
                    audio_array = signal.resample(audio_array, number_of_samples)
                    audio_array = audio_array.astype(np.int16)
                    audio_data = audio_array.tobytes()
                    frame_rate = 8000

                # Convert PCM16 to mulaw
                mulaw_data = self._convert_pcm16_to_mulaw(audio_data)

                # Calculate chunk size for desired duration (20ms default)
                samples_per_chunk = int(frame_rate * chunk_duration)
                bytes_per_chunk = samples_per_chunk  # 1 byte per mulaw sample

                # Chunk the mulaw data
                chunks = []
                for i in range(0, len(mulaw_data), bytes_per_chunk):
                    chunk = mulaw_data[i:i + bytes_per_chunk]
                    # Pad last chunk if needed
                    if len(chunk) < bytes_per_chunk:
                        chunk += b'\xff' * (bytes_per_chunk - len(chunk))  # mulaw silence
                    encoded_chunk = base64.b64encode(chunk).decode("utf-8")
                    chunks.append(encoded_chunk)

                duration = len(mulaw_data) / frame_rate
                self.logger.info(f"   Converted to mulaw and split into {len(chunks)} chunks (~{duration:.2f}s total)")
                return chunks

        except Exception as e:
            self.logger.error(f"[MOCK TWILIO] Error loading audio file: {e}")
            return []

    def _convert_pcm16_to_mulaw(self, pcm16_data: bytes) -> bytes:
        """Convert PCM16 audio to mulaw format."""
        try:
            import audioop
            return audioop.lin2ulaw(pcm16_data, 2)
        except ImportError:
            self.logger.warning("[MOCK TWILIO] audioop not available, using simple conversion")
            # Simple approximation - take every other byte
            return pcm16_data[::2]

    def _convert_mulaw_to_pcm16(self, mulaw_data: bytes) -> bytes:
        """Convert mulaw audio to PCM16 format."""
        try:
            import audioop
            return audioop.ulaw2lin(mulaw_data, 2)
        except ImportError:
            self.logger.warning("[MOCK TWILIO] audioop not available, using simple conversion")
            # Simple approximation - repeat each byte twice
            return b"".join([bytes([b, b]) for b in mulaw_data])

    async def multi_turn_conversation(
        self, 
        audio_files: List[str], 
        wait_for_greeting: bool = True,
        turn_delay: float = 2.0,
        chunk_delay: float = 0.02
    ) -> Dict[str, Any]:
        """
        Conduct a multi-turn conversation using a list of audio files.
        
        Args:
            audio_files: List of paths to audio files for user turns
            wait_for_greeting: Whether to wait for initial AI greeting
            turn_delay: Delay between conversation turns (seconds)
            chunk_delay: Delay between audio chunks (seconds)
            
        Returns:
            Dictionary with conversation results and statistics
        """
        self.logger.info(f"[MOCK TWILIO] Starting multi-turn conversation with {len(audio_files)} turns")
        
        conversation_result = {
            "total_turns": len(audio_files),
            "completed_turns": 0,
            "greeting_received": False,
            "turns": [],
            "success": False,
            "error": None
        }
        
        try:
            # Step 1: Initiate call flow
            if not await self.initiate_call_flow():
                conversation_result["error"] = "Failed to initiate call flow"
                return conversation_result

            # Step 2: Wait for initial greeting if requested
            if wait_for_greeting:
                self.logger.info("[MOCK TWILIO] Waiting for initial greeting...")
                greeting = await self.wait_for_ai_greeting(timeout=20.0)
                if greeting:
                    conversation_result["greeting_received"] = True
                    conversation_result["greeting_chunks"] = len(greeting)
                    self.logger.info(f"[MOCK TWILIO] Initial greeting received: {len(greeting)} chunks")
                else:
                    self.logger.warning("[MOCK TWILIO] No initial greeting received, continuing anyway...")

            # Step 3: Process each audio file as a conversation turn
            for turn_num, audio_file in enumerate(audio_files, 1):
                self.logger.info(f"\n[MOCK TWILIO] === Turn {turn_num}/{len(audio_files)} ===")
                self.logger.info(f"[MOCK TWILIO] Sending: {Path(audio_file).name}")
                
                turn_result = {
                    "turn_number": turn_num,
                    "audio_file": str(Path(audio_file).name),
                    "user_audio_sent": False,
                    "ai_response_received": False,
                    "response_chunks": 0,
                    "error": None
                }

                # Send user audio
                try:
                    success = await self.send_user_audio(audio_file, chunk_delay=chunk_delay)
                    if success:
                        turn_result["user_audio_sent"] = True
                        self.logger.info(f"[MOCK TWILIO] Turn {turn_num}: User audio sent successfully")
                    else:
                        turn_result["error"] = "Failed to send user audio"
                        self.logger.error(f"[MOCK TWILIO] Turn {turn_num}: Failed to send user audio")
                        conversation_result["turns"].append(turn_result)
                        continue
                        
                except Exception as e:
                    turn_result["error"] = f"Audio send error: {str(e)}"
                    self.logger.error(f"[MOCK TWILIO] Turn {turn_num}: Audio send error: {e}")
                    conversation_result["turns"].append(turn_result)
                    continue

                # Wait for AI response
                try:
                    response = await self.wait_for_ai_response(timeout=45.0)
                    if response:
                        turn_result["ai_response_received"] = True
                        turn_result["response_chunks"] = len(response)
                        conversation_result["completed_turns"] += 1
                        self.logger.info(f"[MOCK TWILIO] Turn {turn_num}: AI response received ({len(response)} chunks)")
                        
                        # Save this turn's audio for analysis
                        self._save_turn_audio(turn_num, response)
                        
                    else:
                        turn_result["error"] = "No AI response received"
                        self.logger.error(f"[MOCK TWILIO] Turn {turn_num}: No AI response received")
                        
                except Exception as e:
                    turn_result["error"] = f"Response wait error: {str(e)}"
                    self.logger.error(f"[MOCK TWILIO] Turn {turn_num}: Response wait error: {e}")

                conversation_result["turns"].append(turn_result)
                
                # Delay before next turn (except for last turn)
                if turn_num < len(audio_files):
                    self.logger.info(f"[MOCK TWILIO] Waiting {turn_delay}s before next turn...")
                    await asyncio.sleep(turn_delay)

            # Step 4: End the call
            await self.send_stop()

            # Mark as successful if at least some turns completed
            if conversation_result["completed_turns"] > 0:
                conversation_result["success"] = True
                
            self.logger.info(f"\n[MOCK TWILIO] Multi-turn conversation completed:")
            self.logger.info(f"   Completed turns: {conversation_result['completed_turns']}/{conversation_result['total_turns']}")
            
            return conversation_result
            
        except Exception as e:
            conversation_result["error"] = str(e)
            self.logger.error(f"[MOCK TWILIO] Multi-turn conversation failed: {e}")
            return conversation_result

    def save_collected_audio(self, output_dir: str = "validation_output"):
        """Save collected audio for analysis."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        if self.greeting_audio_chunks:
            self._save_chunks_to_wav(
                self.greeting_audio_chunks,
                output_path / f"twilio_greeting_{self.stream_sid[:8]}.wav",
                is_mulaw=True
            )

        if self.response_audio_chunks:
            self._save_chunks_to_wav(
                self.response_audio_chunks,
                output_path / f"twilio_response_{self.stream_sid[:8]}.wav",
                is_mulaw=True
            )

    def _save_turn_audio(self, turn_number: int, audio_chunks: List[str], output_dir: str = "validation_output"):
        """Save audio from a specific conversation turn."""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            if audio_chunks:
                filename = f"twilio_turn_{turn_number:02d}_response_{self.stream_sid[:8]}.wav"
                self._save_chunks_to_wav(audio_chunks, output_path / filename, is_mulaw=True)
                
        except Exception as e:
            self.logger.error(f"[MOCK TWILIO] Error saving turn {turn_number} audio: {e}")

    def _save_chunks_to_wav(self, chunks: List[str], filepath: Path, is_mulaw: bool = True):
        """Save base64 audio chunks to a WAV file."""
        try:
            audio_data = b""
            for chunk in chunks:
                audio_data += base64.b64decode(chunk)

            # Convert mulaw to PCM16 for WAV file
            if is_mulaw:
                pcm16_data = self._convert_mulaw_to_pcm16(audio_data)
                sample_rate = 8000
            else:
                pcm16_data = audio_data
                sample_rate = 16000

            with wave.open(str(filepath), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm16_data)

            duration = len(pcm16_data) / (sample_rate * 2)
            self.logger.info(f"[MOCK TWILIO] Saved audio: {filepath.name} ({duration:.2f}s)")

        except Exception as e:
            self.logger.error(f"[MOCK TWILIO] Error saving audio: {e}")

    async def simple_conversation_test(
        self, 
        audio_files: List[str], 
        session_name: str = "TwilioMultiTurnTest"
    ) -> bool:
        """
        Simple wrapper for testing multi-turn conversations.
        
        Returns True if the conversation was successful, False otherwise.
        """
        try:
            # Run multi-turn conversation
            result = await self.multi_turn_conversation(audio_files)
            
            # Save all collected audio
            self.save_collected_audio()
            
            # Print summary
            self._print_conversation_summary(result)
            
            return result["success"]
            
        except Exception as e:
            self.logger.error(f"[MOCK TWILIO] Simple conversation test failed: {e}")
            return False

    def _print_conversation_summary(self, result: Dict[str, Any]):
        """Print a summary of the multi-turn conversation."""
        self.logger.info("\n" + "=" * 50)
        self.logger.info("[MOCK TWILIO] MULTI-TURN CONVERSATION SUMMARY")
        self.logger.info("=" * 50)
        
        success_status = "SUCCESS" if result["success"] else "FAILED"
        self.logger.info(f"Overall Status: {success_status}")
        self.logger.info(f"Completed Turns: {result['completed_turns']}/{result['total_turns']}")
        
        if result.get("greeting_received"):
            self.logger.info(f"Initial Greeting: Received ({result.get('greeting_chunks', 0)} chunks)")
        else:
            self.logger.info("Initial Greeting: Not received")
        
        if result.get("error"):
            self.logger.error(f"Overall Error: {result['error']}")
        
        self.logger.info("\nTurn-by-turn Results:")
        for turn in result.get("turns", []):
            turn_num = turn["turn_number"]
            audio_file = turn["audio_file"]
            
            status_parts = []
            if turn["user_audio_sent"]:
                status_parts.append("Audio Sent")
            if turn["ai_response_received"]:
                status_parts.append(f"Response Received ({turn['response_chunks']} chunks)")
            
            status = " → ".join(status_parts) if status_parts else "Failed"
            
            self.logger.info(f"  Turn {turn_num}: {audio_file} → {status}")
            
            if turn.get("error"):
                self.logger.error(f"    Error: {turn['error']}")
        
        self.logger.info("=" * 50) 