#!/usr/bin/env python3
"""
MockAudioCodes Client - Connects TO the bridge server

This version acts as a WebSocket client that connects to the bridge server,
properly simulating how the real AudioCodes VAIC would connect.
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


class MockAudioCodesClient:
    """
    MockAudioCodes client that connects to the bridge server.

    This properly simulates the AudioCodes VAIC connecting to your bridge.
    """

    def __init__(
        self,
        bridge_url: str,
        bot_name: str = "TestBot",
        caller: str = "+15551234567",
        logger: logging.Logger = None,
    ):
        self.bridge_url = bridge_url
        self.bot_name = bot_name
        self.caller = caller
        self.logger = logger or logging.getLogger(__name__)
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self.received_messages: List[Dict[str, Any]] = []

        # Session state
        self.conversation_id: Optional[str] = None
        self.session_accepted = False
        self.media_format = "raw/lpcm16"

        # Stream state
        self.user_stream_active = False
        self.play_stream_active = False
        self.current_stream_id: Optional[str] = None

        # Audio collection
        self.received_play_chunks: List[str] = []
        self.greeting_audio_chunks: List[str] = []
        self.response_audio_chunks: List[str] = []
        self._collecting_greeting = False
        self._collecting_response = False

        # Multi-turn conversation state
        self.conversation_turns: List[Dict[str, Any]] = []
        self._current_turn = 0

    async def __aenter__(self):
        """Connect to the bridge server."""
        self.logger.info(f"[MOCK] Connecting to bridge at {self.bridge_url}...")
        self._ws = await websockets.connect(self.bridge_url)
        self.logger.info("[MOCK] Connected to bridge server")

        # Start message handler
        self._message_task = asyncio.create_task(self._message_handler())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Disconnect from bridge server."""
        if hasattr(self, "_message_task"):
            self._message_task.cancel()
        if self._ws:
            await self._ws.close()
        self.logger.info("[MOCK] Disconnected from bridge server")

    async def _message_handler(self):
        """Handle incoming messages from the bridge."""
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    await self._process_bridge_message(data)
                except json.JSONDecodeError:
                    self.logger.warning(f"[MOCK] Received non-JSON message: {message}")
                except Exception as e:
                    self.logger.error(f"[MOCK] Error processing message: {e}")
        except websockets.ConnectionClosed:
            self.logger.info("[MOCK] Bridge connection closed")
        except Exception as e:
            self.logger.error(f"[MOCK] Message handler error: {e}")

    async def _process_bridge_message(self, data: Dict[str, Any]):
        """Process messages received from the bridge."""
        msg_type = data.get("type")
        self.received_messages.append(data)

        self.logger.info(f"[MOCK] Received from bridge: {msg_type}")

        if msg_type == "session.accepted":
            self.session_accepted = True
            self.media_format = data.get("mediaFormat", "raw/lpcm16")
            self.logger.info(
                f"[MOCK] Session accepted with format: {self.media_format}"
            )

        elif msg_type == "userStream.started":
            self.user_stream_active = True
            self.logger.info("[MOCK] User stream started")

        elif msg_type == "userStream.stopped":
            self.user_stream_active = False
            self.logger.info("[MOCK] User stream stopped")

        elif msg_type == "playStream.start":
            self.play_stream_active = True
            self.current_stream_id = data.get("streamId")
            self.logger.info(f"[MOCK] Play stream started: {self.current_stream_id}")

            # Determine if this is greeting or response
            if not self.greeting_audio_chunks and not self._collecting_response:
                self._collecting_greeting = True
                self.logger.info("[MOCK] Collecting greeting audio...")
            else:
                self._collecting_response = True
                self.logger.info("[MOCK] Collecting response audio...")

        elif msg_type == "playStream.chunk":
            audio_chunk = data.get("audioChunk")
            if audio_chunk:
                self.received_play_chunks.append(audio_chunk)

                if self._collecting_greeting:
                    self.greeting_audio_chunks.append(audio_chunk)
                elif self._collecting_response:
                    self.response_audio_chunks.append(audio_chunk)

                self.logger.debug(
                    f"[MOCK] Received audio chunk ({len(audio_chunk)} bytes base64)"
                )

        elif msg_type == "playStream.stop":
            self.play_stream_active = False
            if self._collecting_greeting:
                self._collecting_greeting = False
                self.logger.info(
                    f"[MOCK] Greeting collected: {len(self.greeting_audio_chunks)} chunks"
                )
            elif self._collecting_response:
                self._collecting_response = False
                self.logger.info(
                    f"[MOCK] Response collected: {len(self.response_audio_chunks)} chunks"
                )
            self.logger.info(f"[MOCK] Play stream stopped: {self.current_stream_id}")
            self.current_stream_id = None

    async def initiate_session(self, conversation_id: Optional[str] = None) -> bool:
        """Send session.initiate to the bridge."""
        self.conversation_id = conversation_id or str(uuid.uuid4())

        session_initiate = {
            "type": "session.initiate",
            "conversationId": self.conversation_id,
            "expectAudioMessages": True,
            "botName": self.bot_name,
            "caller": self.caller,
            "supportedMediaFormats": [self.media_format],
        }

        await self._ws.send(json.dumps(session_initiate))
        self.logger.info(
            f"[MOCK] Sent session.initiate for conversation: {self.conversation_id}"
        )

        # Wait for session.accepted
        for _ in range(100):  # 10 seconds timeout
            if self.session_accepted:
                return True
            await asyncio.sleep(0.1)

        self.logger.error("[MOCK] Session not accepted within timeout")
        return False

    async def wait_for_llm_greeting(self, timeout: float = 20.0) -> List[str]:
        """Wait for and collect LLM greeting audio."""
        self.logger.info("[MOCK] Waiting for LLM greeting...")

        end_time = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < end_time:
            if self.greeting_audio_chunks and not self._collecting_greeting:
                self.logger.info(
                    f"[MOCK] Greeting received: {len(self.greeting_audio_chunks)} chunks"
                )
                return self.greeting_audio_chunks.copy()
            await asyncio.sleep(0.1)

        self.logger.error("[MOCK] Timeout waiting for LLM greeting")
        return []

    async def send_user_audio(
        self, audio_file_path: str, chunk_delay: float = 0.02
    ) -> bool:
        """Send user audio to the bridge."""
        audio_chunks = self._load_audio_chunks(audio_file_path)
        if not audio_chunks:
            return False

        self.logger.info(
            f"[MOCK] Sending user audio: {Path(audio_file_path).name} ({len(audio_chunks)} chunks)"
        )

        # Start user stream
        user_stream_start = {
            "type": "userStream.start",
            "conversationId": self.conversation_id,
        }
        await self._ws.send(json.dumps(user_stream_start))

        # Wait for userStream.started
        for _ in range(20):
            if self.user_stream_active:
                break
            await asyncio.sleep(0.1)
        else:
            self.logger.error("[MOCK] User stream not started")
            return False

        # Send audio chunks
        for i, chunk in enumerate(audio_chunks):
            audio_chunk_msg = {
                "type": "userStream.chunk",
                "conversationId": self.conversation_id,
                "audioChunk": chunk,
            }
            await self._ws.send(json.dumps(audio_chunk_msg))

            if i % 10 == 0 or i == len(audio_chunks) - 1:
                self.logger.debug(f"[MOCK] Sent chunk {i+1}/{len(audio_chunks)}")
            await asyncio.sleep(chunk_delay)

        # Stop user stream
        user_stream_stop = {
            "type": "userStream.stop",
            "conversationId": self.conversation_id,
        }
        await self._ws.send(json.dumps(user_stream_stop))
        self.logger.info("[MOCK] User audio sent successfully")
        return True

    async def wait_for_llm_response(self, timeout: float = 45.0) -> List[str]:
        """Wait for and collect LLM response audio."""
        self.logger.info("[MOCK] Waiting for LLM response...")

        # Clear previous response chunks
        self.response_audio_chunks.clear()

        end_time = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < end_time:
            if self.response_audio_chunks and not self._collecting_response:
                self.logger.info(
                    f"[MOCK] Response received: {len(self.response_audio_chunks)} chunks"
                )
                return self.response_audio_chunks.copy()
            await asyncio.sleep(0.1)

        self.logger.error("[MOCK] Timeout waiting for LLM response")
        return []

    async def end_session(self, reason: str = "Test completed"):
        """End the session gracefully."""
        if self.conversation_id:
            session_end = {
                "type": "session.end",
                "conversationId": self.conversation_id,
                "reasonCode": "normal",
                "reason": reason,
            }
            await self._ws.send(json.dumps(session_end))
            self.logger.info(f"[MOCK] Sent session.end: {reason}")

    def _load_audio_chunks(self, file_path: str, chunk_size: int = 32000) -> List[str]:
        """Load and chunk audio file."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                self.logger.error(f"[MOCK] Audio file not found: {file_path}")
                return []

            with wave.open(str(file_path), "rb") as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()

                self.logger.info(f"[MOCK] Loading audio: {file_path.name}")
                self.logger.info(
                    f"   Format: {channels}ch, {sample_width*8}bit, {frame_rate}Hz"
                )

                audio_data = wav_file.readframes(wav_file.getnframes())

                # Resample to 16kHz if needed
                if frame_rate != 16000:
                    self.logger.info(f"   Resampling from {frame_rate}Hz to 16000Hz...")
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    number_of_samples = round(len(audio_array) * 16000 / frame_rate)
                    audio_array = signal.resample(audio_array, number_of_samples)
                    audio_array = audio_array.astype(np.int16)
                    audio_data = audio_array.tobytes()
                    frame_rate = 16000

                # Calculate minimum chunk size
                min_chunk_size = int(0.1 * frame_rate * sample_width)
                chunk_size = max(chunk_size, min_chunk_size)

                # Chunk the audio data
                chunks = []
                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i : i + chunk_size]
                    if len(chunk) < min_chunk_size:
                        chunk += b"\x00" * (min_chunk_size - len(chunk))
                    encoded_chunk = base64.b64encode(chunk).decode("utf-8")
                    chunks.append(encoded_chunk)

                duration = len(audio_data) / (frame_rate * sample_width)
                self.logger.info(
                    f"   Split into {len(chunks)} chunks (~{duration:.2f}s total)"
                )
                return chunks

        except Exception as e:
            self.logger.error(f"[MOCK] Error loading audio file: {e}")
            return []

    def save_collected_audio(self, output_dir: str = "validation_output"):
        """Save collected audio for analysis."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        if self.greeting_audio_chunks:
            self._save_chunks_to_wav(
                self.greeting_audio_chunks,
                output_path / f"greeting_{self.conversation_id[:8]}.wav",
            )

        if self.response_audio_chunks:
            self._save_chunks_to_wav(
                self.response_audio_chunks,
                output_path / f"response_{self.conversation_id[:8]}.wav",
            )

    def _save_chunks_to_wav(self, chunks: List[str], filepath: Path):
        """Save base64 audio chunks to a WAV file."""
        try:
            audio_data = b""
            for chunk in chunks:
                audio_data += base64.b64decode(chunk)

            with wave.open(str(filepath), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(audio_data)

            duration = len(audio_data) / (16000 * 2)
            self.logger.info(f"[MOCK] Saved audio: {filepath.name} ({duration:.2f}s)")

        except Exception as e:
            self.logger.error(f"[MOCK] Error saving audio: {e}")

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
        self.logger.info(f"[MOCK] Starting multi-turn conversation with {len(audio_files)} turns")
        
        conversation_result = {
            "total_turns": len(audio_files),
            "completed_turns": 0,
            "greeting_received": False,
            "turns": [],
            "success": False,
            "error": None
        }
        
        try:
            # Step 1: Wait for initial greeting if requested
            if wait_for_greeting:
                self.logger.info("[MOCK] Waiting for initial greeting...")
                greeting = await self.wait_for_llm_greeting(timeout=20.0)
                if greeting:
                    conversation_result["greeting_received"] = True
                    conversation_result["greeting_chunks"] = len(greeting)
                    self.logger.info(f"[MOCK] Initial greeting received: {len(greeting)} chunks")
                else:
                    self.logger.warning("[MOCK] No initial greeting received, continuing anyway...")
            
            # Step 2: Process each audio file as a conversation turn
            for turn_num, audio_file in enumerate(audio_files, 1):
                self.logger.info(f"\n[MOCK] === Turn {turn_num}/{len(audio_files)} ===")
                self.logger.info(f"[MOCK] Sending: {Path(audio_file).name}")
                
                turn_result = {
                    "turn_number": turn_num,
                    "audio_file": str(Path(audio_file).name),
                    "user_audio_sent": False,
                    "ai_response_received": False,
                    "response_chunks": 0,
                    "error": None
                }
                
                # Clear previous response chunks for this turn
                self.response_audio_chunks.clear()
                
                # Send user audio
                try:
                    success = await self.send_user_audio(audio_file, chunk_delay=chunk_delay)
                    if success:
                        turn_result["user_audio_sent"] = True
                        self.logger.info(f"[MOCK] Turn {turn_num}: User audio sent successfully")
                    else:
                        turn_result["error"] = "Failed to send user audio"
                        self.logger.error(f"[MOCK] Turn {turn_num}: Failed to send user audio")
                        conversation_result["turns"].append(turn_result)
                        continue
                        
                except Exception as e:
                    turn_result["error"] = f"Audio send error: {str(e)}"
                    self.logger.error(f"[MOCK] Turn {turn_num}: Audio send error: {e}")
                    conversation_result["turns"].append(turn_result)
                    continue
                
                # Wait for AI response
                try:
                    response = await self.wait_for_llm_response(timeout=45.0)
                    if response:
                        turn_result["ai_response_received"] = True
                        turn_result["response_chunks"] = len(response)
                        conversation_result["completed_turns"] += 1
                        self.logger.info(f"[MOCK] Turn {turn_num}: AI response received ({len(response)} chunks)")
                        
                        # Save this turn's audio for analysis
                        self._save_turn_audio(turn_num, response)
                        
                    else:
                        turn_result["error"] = "No AI response received"
                        self.logger.error(f"[MOCK] Turn {turn_num}: No AI response received")
                        
                except Exception as e:
                    turn_result["error"] = f"Response wait error: {str(e)}"
                    self.logger.error(f"[MOCK] Turn {turn_num}: Response wait error: {e}")
                
                conversation_result["turns"].append(turn_result)
                
                # Delay before next turn (except for last turn)
                if turn_num < len(audio_files):
                    self.logger.info(f"[MOCK] Waiting {turn_delay}s before next turn...")
                    await asyncio.sleep(turn_delay)
            
            # Mark as successful if at least some turns completed
            if conversation_result["completed_turns"] > 0:
                conversation_result["success"] = True
                
            self.logger.info(f"\n[MOCK] Multi-turn conversation completed:")
            self.logger.info(f"   Completed turns: {conversation_result['completed_turns']}/{conversation_result['total_turns']}")
            
            return conversation_result
            
        except Exception as e:
            conversation_result["error"] = str(e)
            self.logger.error(f"[MOCK] Multi-turn conversation failed: {e}")
            return conversation_result

    def _save_turn_audio(self, turn_number: int, audio_chunks: List[str], output_dir: str = "validation_output"):
        """Save audio from a specific conversation turn."""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            if audio_chunks:
                filename = f"turn_{turn_number:02d}_response_{self.conversation_id[:8]}.wav"
                self._save_chunks_to_wav(audio_chunks, output_path / filename)
                
        except Exception as e:
            self.logger.error(f"[MOCK] Error saving turn {turn_number} audio: {e}")

    async def simple_conversation_test(
        self, 
        audio_files: List[str], 
        session_name: str = "MultiTurnTest"
    ) -> bool:
        """
        Simple wrapper for testing multi-turn conversations.
        
        Returns True if the conversation was successful, False otherwise.
        """
        try:
            # Initiate session
            success = await self.initiate_session()
            if not success:
                self.logger.error("[MOCK] Failed to initiate session")
                return False
            
            # Run multi-turn conversation
            result = await self.multi_turn_conversation(audio_files)
            
            # End session
            await self.end_session(f"{session_name} completed")
            
            # Save all collected audio
            self.save_collected_audio()
            
            # Print summary
            self._print_conversation_summary(result)
            
            return result["success"]
            
        except Exception as e:
            self.logger.error(f"[MOCK] Simple conversation test failed: {e}")
            return False

    def _print_conversation_summary(self, result: Dict[str, Any]):
        """Print a summary of the multi-turn conversation."""
        self.logger.info("\n" + "=" * 50)
        self.logger.info("[MOCK] MULTI-TURN CONVERSATION SUMMARY")
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
