#!/usr/bin/env python3
"""
Local VAD Client - Real-time microphone input with voice activity detection

This client connects to the bridge server and provides real-time microphone input
with local voice activity detection, replacing the file-based mock client.
"""

import asyncio
import base64
import json
import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import sounddevice as sd
import websockets
from scipy import signal


class LocalVADClient:
    """
    Local VAD client that connects to the bridge server with real-time microphone input.
    
    Features:
    - Real-time microphone input using SoundDevice
    - Local voice activity detection using energy-based VAD
    - Audio playback of responses from the bridge
    - Automatic session management
    """

    def __init__(
        self,
        bridge_url: str,
        bot_name: str = "LocalVADBot",
        caller: str = "+15551234567",
        logger: Optional[logging.Logger] = None,
        vad_sensitivity: float = 0.1,
        vad_silence_duration: float = 1.0,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
    ):
        self.bridge_url = bridge_url
        self.bot_name = bot_name
        self.caller = caller
        self.logger = logger or logging.getLogger(__name__)
        self._ws: Optional[Any] = None
        
        # VAD settings
        self.vad_sensitivity = vad_sensitivity
        self.vad_silence_duration = vad_silence_duration
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        
        # Audio state
        self.recording = False
        self.playing = False
        self.speech_detected = False
        self.silence_start_time = None
        
        # Session state
        self.conversation_id: Optional[str] = None
        self.session_accepted = False
        self.media_format = "raw/lpcm16"
        
        # Stream state
        self.user_stream_active = False
        self.play_stream_active = False
        self.current_stream_id: Optional[str] = None
        
        # Audio buffers
        self.audio_buffer: List[bytes] = []
        self.playback_buffer: List[bytes] = []
        
        # Threading
        self.audio_thread: Optional[threading.Thread] = None
        self.playback_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Message tracking
        self.received_messages: List[Dict[str, Any]] = []
        self.loop = None  # Store the main asyncio event loop

    async def __aenter__(self):
        """Connect to the bridge server."""
        self.logger.info(f"[LOCAL VAD] Connecting to bridge at {self.bridge_url}...")
        self._ws = await websockets.connect(self.bridge_url)
        self.logger.info("[LOCAL VAD] Connected to bridge server")

        # Store the main event loop for use in callbacks
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.get_event_loop()

        # Start message handler
        self._message_task = asyncio.create_task(self._message_handler())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Disconnect from bridge server."""
        self._stop_event.set()
        
        if hasattr(self, "_message_task"):
            self._message_task.cancel()
        if self._ws:
            await self._ws.close()
        self.logger.info("[LOCAL VAD] Disconnected from bridge server")

    async def _message_handler(self):
        """Handle incoming messages from the bridge."""
        try:
            if self._ws is None:
                self.logger.error("[LOCAL VAD] WebSocket connection is None")
                return
                
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    await self._process_bridge_message(data)
                except json.JSONDecodeError:
                    self.logger.warning(f"[LOCAL VAD] Received non-JSON message: {message}")
                except Exception as e:
                    self.logger.error(f"[LOCAL VAD] Error processing message: {e}")
        except websockets.ConnectionClosed:
            self.logger.info("[LOCAL VAD] Bridge connection closed")
        except Exception as e:
            self.logger.error(f"[LOCAL VAD] Message handler error: {e}")

    async def _process_bridge_message(self, data: Dict[str, Any]):
        """Process messages received from the bridge."""
        msg_type = data.get("type")
        self.received_messages.append(data)

        self.logger.info(f"[LOCAL VAD] Received from bridge: {msg_type}")

        if msg_type == "session.accepted":
            self.session_accepted = True
            self.media_format = data.get("mediaFormat", "raw/lpcm16")
            self.logger.info(f"[LOCAL VAD] Session accepted with format: {self.media_format}")

        elif msg_type == "userStream.started":
            self.user_stream_active = True
            self.logger.info("[LOCAL VAD] User stream started")

        elif msg_type == "userStream.stopped":
            self.user_stream_active = False
            self.logger.info("[LOCAL VAD] User stream stopped")

        elif msg_type == "playStream.start":
            self.play_stream_active = True
            self.current_stream_id = data.get("streamId")
            self.logger.info(f"[LOCAL VAD] Play stream started: {self.current_stream_id}")
            
            # Start playback thread
            if not self.playback_thread or not self.playback_thread.is_alive():
                self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
                self.playback_thread.start()

        elif msg_type == "playStream.chunk":
            audio_chunk = data.get("audioChunk")
            if audio_chunk:
                # Decode and add to playback buffer
                try:
                    audio_bytes = base64.b64decode(audio_chunk)
                    self.playback_buffer.append(audio_bytes)
                    self.logger.debug(f"[LOCAL VAD] Received audio chunk ({len(audio_chunk)} bytes base64)")
                except Exception as e:
                    self.logger.error(f"[LOCAL VAD] Error decoding audio chunk: {e}")

        elif msg_type == "playStream.stop":
            self.play_stream_active = False
            self.logger.info(f"[LOCAL VAD] Play stream stopped: {self.current_stream_id}")
            self.current_stream_id = None

    async def initiate_session(self, conversation_id: Optional[str] = None) -> bool:
        """Send session.initiate to the bridge."""
        if self._ws is None:
            self.logger.error("[LOCAL VAD] WebSocket connection is None")
            return False
            
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
        self.logger.info(f"[LOCAL VAD] Sent session.initiate for conversation: {self.conversation_id}")

        # Wait for session.accepted
        for _ in range(100):  # 10 seconds timeout
            if self.session_accepted:
                return True
            await asyncio.sleep(0.1)

        self.logger.error("[LOCAL VAD] Session not accepted within timeout")
        return False

    def start_recording(self):
        """Start real-time microphone recording with VAD."""
        if self.recording:
            self.logger.warning("[LOCAL VAD] Already recording")
            return
            
        self.recording = True
        self._stop_event.clear()
        
        # Start audio thread
        self.audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
        self.audio_thread.start()
        
        self.logger.info("[LOCAL VAD] Started microphone recording with VAD")

    def stop_recording(self):
        """Stop microphone recording."""
        self.recording = False
        self._stop_event.set()
        
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=2.0)
            
        self.logger.info("[LOCAL VAD] Stopped microphone recording")

    def _audio_loop(self):
        """Main audio recording loop with VAD."""
        try:
            def audio_callback(indata, frames, time_info, status):
                if status:
                    self.logger.warning(f"[LOCAL VAD] Audio callback status: {status}")
                
                # Convert to bytes
                audio_bytes = indata.astype(np.int16).tobytes()
                
                # VAD processing
                if self._detect_speech(audio_bytes):
                    if not self.speech_detected:
                        self.speech_detected = True
                        self.silence_start_time = None
                        self.logger.info("[LOCAL VAD] Speech detected - starting stream")
                        
                        # Start user stream
                        if self.loop:
                            asyncio.run_coroutine_threadsafe(
                                self._start_user_stream(), 
                                self.loop
                            )
                        else:
                            self.logger.warning("[LOCAL VAD] No event loop set for run_coroutine_threadsafe (start_user_stream)")
                    
                    # Add to buffer and send
                    self.audio_buffer.append(audio_bytes)
                    if self.loop:
                        asyncio.run_coroutine_threadsafe(
                            self._send_audio_chunk(audio_bytes),
                            self.loop
                        )
                    else:
                        self.logger.warning("[LOCAL VAD] No event loop set for run_coroutine_threadsafe (send_audio_chunk)")
                else:
                    if self.speech_detected:
                        if self.silence_start_time is None:
                            self.silence_start_time = time.time()
                        elif time.time() - self.silence_start_time > self.vad_silence_duration:
                            self.speech_detected = False
                            self.logger.info("[LOCAL VAD] Speech ended - stopping stream")
                            
                            # Stop user stream
                            if self.loop:
                                asyncio.run_coroutine_threadsafe(
                                    self._stop_user_stream(),
                                    self.loop
                                )
                            else:
                                self.logger.warning("[LOCAL VAD] No event loop set for run_coroutine_threadsafe (stop_user_stream)")

            # Start audio stream
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.int16,
                blocksize=self.chunk_size,
                callback=audio_callback
            ):
                # Keep thread alive
                while self.recording and not self._stop_event.is_set():
                    time.sleep(0.01)
                    
        except Exception as e:
            self.logger.error(f"[LOCAL VAD] Error in audio loop: {e}")

    def _detect_speech(self, audio_bytes: bytes) -> bool:
        """Simple energy-based VAD."""
        try:
            # Convert to numpy array
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            
            # Calculate RMS energy
            rms = np.sqrt(np.mean(audio_array ** 2))
            
            # Normalize to 0-1 range
            normalized_rms = rms / 32768.0
            
            # VAD threshold
            return normalized_rms > self.vad_sensitivity
            
        except Exception as e:
            self.logger.error(f"[LOCAL VAD] Error in VAD: {e}")
            return False

    async def _start_user_stream(self):
        """Start user audio stream."""
        if self._ws is None:
            return
            
        user_stream_start = {
            "type": "userStream.start",
            "conversationId": self.conversation_id,
        }
        await self._ws.send(json.dumps(user_stream_start))

    async def _stop_user_stream(self):
        """Stop user audio stream."""
        if self._ws is None:
            return
            
        user_stream_stop = {
            "type": "userStream.stop",
            "conversationId": self.conversation_id,
        }
        await self._ws.send(json.dumps(user_stream_stop))

    async def _send_audio_chunk(self, audio_bytes: bytes):
        """Send audio chunk to bridge."""
        if self._ws is None or not self.user_stream_active:
            return
            
        # Encode to base64
        audio_chunk_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        
        # Send chunk
        audio_chunk_msg = {
            "type": "userStream.chunk",
            "conversationId": self.conversation_id,
            "audioChunk": audio_chunk_b64,
        }
        await self._ws.send(json.dumps(audio_chunk_msg))

    def _playback_loop(self):
        """Audio playback loop."""
        try:
            def playback_callback(outdata, frames, time, status):
                if status:
                    self.logger.warning(f"[LOCAL VAD] Playback callback status: {status}")
                
                # Initialize with silence
                outdata.fill(0)
                
                # Get audio from buffer
                if self.playback_buffer:
                    try:
                        audio_bytes = self.playback_buffer.pop(0)
                        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
                        
                        # Copy to output buffer
                        copy_frames = min(frames, len(audio_array))
                        outdata[:copy_frames, 0] = audio_array[:copy_frames]
                        
                    except IndexError:
                        pass  # No more audio data

            # Start playback stream
            with sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.int16,
                blocksize=self.chunk_size,
                callback=playback_callback
            ):
                # Keep thread alive while playing
                while self.play_stream_active and not self._stop_event.is_set():
                    time.sleep(0.01)
                    
        except Exception as e:
            self.logger.error(f"[LOCAL VAD] Error in playback loop: {e}")

    async def end_session(self, reason: str = "Local VAD test completed"):
        """End the session gracefully."""
        if self._ws is None:
            self.logger.error("[LOCAL VAD] WebSocket connection is None")
            return
            
        if self.conversation_id:
            session_end = {
                "type": "session.end",
                "conversationId": self.conversation_id,
                "reasonCode": "normal",
                "reason": reason,
            }
            await self._ws.send(json.dumps(session_end))
            self.logger.info(f"[LOCAL VAD] Sent session.end: {reason}")

    async def run_conversation(self, duration: float = 30.0):
        """Run a conversation for a specified duration."""
        try:
            # Initiate session
            success = await self.initiate_session()
            if not success:
                self.logger.error("[LOCAL VAD] Failed to initiate session")
                return False
            
            # Start recording
            self.start_recording()
            
            # Run for specified duration
            self.logger.info(f"[LOCAL VAD] Running conversation for {duration} seconds...")
            self.logger.info("[LOCAL VAD] Speak into your microphone to start the conversation")
            
            await asyncio.sleep(duration)
            
            # Stop recording
            self.stop_recording()
            
            # End session
            await self.end_session("Conversation duration completed")
            
            return True
            
        except Exception as e:
            self.logger.error(f"[LOCAL VAD] Error in conversation: {e}")
            return False


async def main():
    """Example usage of LocalVADClient."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Local VAD Client for Bridge Testing")
    parser.add_argument("--bridge-url", default="ws://localhost:8000/caller-agent", 
                       help="Bridge WebSocket URL")
    parser.add_argument("--duration", type=float, default=30.0,
                       help="Conversation duration in seconds")
    parser.add_argument("--vad-sensitivity", type=float, default=0.1,
                       help="VAD sensitivity (0.0-1.0)")
    parser.add_argument("--vad-silence", type=float, default=1.0,
                       help="Silence duration to end speech (seconds)")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run client
    async with LocalVADClient(
        bridge_url=args.bridge_url,
        vad_sensitivity=args.vad_sensitivity,
        vad_silence_duration=args.vad_silence
    ) as client:
        await client.run_conversation(duration=args.duration)


if __name__ == "__main__":
    asyncio.run(main()) 