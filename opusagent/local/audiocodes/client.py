"""
Main AudioCodes local client.

This module provides the main LocalAudioCodesClient class that integrates all
the modular components (session management, message handling, audio management,
and conversation management) into a cohesive client for testing AudioCodes
bridge server interactions.
"""

import asyncio
import base64
import json
import logging
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Union
import queue

import websockets

from .audio_manager import AudioManager
from .audio_playback import AudioPlaybackManager, AudioPlaybackConfig
from .conversation_manager import ConversationManager
from .live_audio_manager import LiveAudioManager
from .message_handler import MessageHandler
from .models import (
    AudioChunk,
    ConversationResult,
    MessageEvent,
    MessageType,
    SessionConfig,
    SessionState,
    StreamState,
)
from .session_manager import SessionManager
from .vad_manager import VADManager


class LocalAudioCodesClient:
    """
    LocalAudioCodes client that connects to the bridge server.

    This class integrates all the modular components to provide a comprehensive
    local implementation of the AudioCodes VAIC client for testing and development.

    Attributes:
        logger (logging.Logger): Logger instance for debugging
        config (SessionConfig): Session configuration
        session_manager (SessionManager): Session state manager
        message_handler (MessageHandler): WebSocket message handler
        audio_manager (AudioManager): Audio file manager
        conversation_manager (ConversationManager): Conversation manager
        _ws: WebSocket connection
        _message_task: Background message handling task
    """

    def __init__(
        self,
        bridge_url: str,
        bot_name: str = "TestBot",
        caller: str = "+15551234567",
        logger: Optional[logging.Logger] = None,
        vad_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the LocalAudioCodesClient.

        Args:
            bridge_url (str): WebSocket URL for bridge server
            bot_name (str): Name of the bot
            caller (str): Caller phone number
            logger (Optional[logging.Logger]): Logger instance for debugging
            vad_config (Optional[Dict[str, Any]]): VAD configuration
        """
        self.logger = logger or logging.getLogger(__name__)

        # Create configuration
        self.config = SessionConfig(
            bridge_url=bridge_url, bot_name=bot_name, caller=caller
        )

        # Initialize components
        self.session_manager = SessionManager(self.config, self.logger)
        self.audio_manager = AudioManager(self.logger)
        self.message_handler = MessageHandler(self.session_manager, self.logger)
        self.conversation_manager = ConversationManager(
            self.session_manager, self.audio_manager, self.logger
        )

        # Initialize VAD manager
        self.vad_manager = VADManager(
            self.session_manager.stream_state,
            self.logger,
            self._handle_vad_event
        )
        
        # Initialize VAD if enabled
        if self.config.enable_vad:
            vad_config = vad_config or {}
            vad_config.update({
                "threshold": self.config.vad_threshold,
                "silence_threshold": self.config.vad_silence_threshold,
                "min_speech_duration_ms": self.config.vad_min_speech_duration_ms,
                "min_silence_duration_ms": self.config.vad_min_silence_duration_ms,
            })
            self.vad_manager.initialize(vad_config)

        # Initialize audio playback manager
        self.audio_playback = AudioPlaybackManager(
            config=AudioPlaybackConfig(enable_playback=True),
            logger=self.logger
        )

        # WebSocket connection
        self._ws = None
        self._message_task = None
        self.connected = False
        
        # Live audio capture
        self._live_audio_manager = None
        self._live_audio_enabled = False

        # Thread-safe queues for audio and VAD events from live capture
        self._audio_queue = queue.Queue(maxsize=100)
        self._vad_queue = queue.Queue(maxsize=50)
        self._queue_consumer_task = None

    async def __aenter__(self):
        """Connect to the bridge server."""
        self.logger.info(
            f"[CLIENT] Connecting to bridge at {self.config.bridge_url}..."
        )
        self._ws = await websockets.connect(self.config.bridge_url)
        self.connected = True
        self.logger.info("[CLIENT] Connected to bridge server")

        # Start message handler
        self._message_task = asyncio.create_task(self._message_handler())
        
        # Connect audio playback to message handler and start playback
        self.audio_playback.connect_to_message_handler(self.message_handler)
        self.audio_playback.start()
        
        # Start queue consumer task for live audio/VAD events
        self._queue_consumer_task = asyncio.create_task(self._consume_queues())
        
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Disconnect from bridge server."""
        self.connected = False
        
        if self._message_task:
            self._message_task.cancel()
        if self._queue_consumer_task:
            self._queue_consumer_task.cancel()
        if self._ws:
            await self._ws.close()
        
        # Clean up VAD resources
        if hasattr(self, 'vad_manager'):
            self.vad_manager.cleanup()
        
        # Clean up audio playback resources
        if hasattr(self, 'audio_playback'):
            self.audio_playback.cleanup()
        
        # Clean up live audio resources
        if self._live_audio_manager:
            self._live_audio_manager.stop_capture()
            self._live_audio_manager = None
        
        self.logger.info("[CLIENT] Disconnected from bridge server")



    async def _consume_queues(self) -> None:
        """Consume audio and VAD events from queues and send to bridge."""
        while self._ws and self.connected:
            try:
                # Process audio chunks
                try:
                    while not self._audio_queue.empty():
                        audio_chunk = self._audio_queue.get_nowait()
                        await self._send_audio_chunk(audio_chunk)
                except queue.Empty:
                    pass

                # Process VAD events
                try:
                    while not self._vad_queue.empty():
                        vad_event = self._vad_queue.get_nowait()
                        await self._send_vad_event(vad_event)
                except queue.Empty:
                    pass

                await asyncio.sleep(0.01)  # Small delay to prevent busy waiting

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"[CLIENT] Error in queue consumer: {e}")
                await asyncio.sleep(0.1)

    async def _send_audio_chunk(self, audio_chunk: str) -> None:
        """Send audio chunk to bridge server."""
        if not self._ws or not self.connected:
            return

        try:
            message = {
                "type": "userStream.chunk",
                "conversationId": self.session_manager.get_conversation_id(),
                "audioChunk": audio_chunk,
            }
            
            await self._ws.send(json.dumps(message))
            self.logger.debug(f"[CLIENT] Sent live audio chunk ({len(audio_chunk)} chars)")
            
        except Exception as e:
            self.logger.error(f"[CLIENT] Error sending audio chunk: {e}")

    async def _send_vad_event(self, vad_event: Dict[str, Any]) -> None:
        """Send VAD event to bridge server."""
        if not self._ws or not self.connected:
            return

        try:
            event_type = vad_event["type"]
            event_data = vad_event["data"]
            
            message = {
                "type": event_type,
                "conversationId": self.session_manager.get_conversation_id(),
                **event_data
            }
            
            await self._ws.send(json.dumps(message))
            self.logger.debug(f"[CLIENT] Sent live VAD event: {event_type}")
            
        except Exception as e:
            self.logger.error(f"[CLIENT] Error sending VAD event: {e}")

    def _handle_vad_event(self, event: Dict[str, Any]) -> None:
        """
        Handle VAD events and send them to the bridge.

        Args:
            event (Dict[str, Any]): VAD event data
        """
        if self._ws is None:
            return

        try:
            # Create message for the bridge
            message = {
                "type": event["type"],
                "conversationId": self.session_manager.get_conversation_id(),
                "timestamp": event.get("timestamp", time.time()),
            }
            
            # Add event-specific data
            if event["type"] == "userStream.speech.hypothesis":
                message["alternatives"] = event["data"].get("alternatives", [])
            elif event["type"] == "userStream.speech.committed":
                message["text"] = event["data"].get("text", "")
            elif event["type"] in ["userStream.speech.started", "userStream.speech.stopped"]:
                message["speech_prob"] = event["data"].get("speech_prob", 0.0)
                if event["type"] == "userStream.speech.stopped":
                    message["speech_duration_ms"] = event["data"].get("speech_duration_ms", 0)

            # Send to bridge
            asyncio.create_task(self._ws.send(json.dumps(message)))
            self.logger.debug(f"[CLIENT] Sent VAD event: {event['type']}")

        except Exception as e:
            self.logger.error(f"[CLIENT] Error sending VAD event: {e}")

    async def _message_handler(self):
        """Handle incoming messages from the bridge."""
        try:
            if self._ws is None:
                self.logger.error("[CLIENT] WebSocket connection is None")
                return

            async for message in self._ws:
                try:
                    # Convert bytes/bytearray to string if needed
                    if isinstance(message, (bytes, bytearray)):
                        message_str = message.decode("utf-8")
                    else:
                        message_str = str(message)
                    event = self.message_handler.process_message(message_str)
                    if event and event.type.value == "session.accepted":
                        # Start conversation when session is accepted
                        if self.session_manager.conversation_state:
                            self.conversation_manager.start_conversation(
                                self.session_manager.conversation_state.conversation_id
                            )
                except Exception as e:
                    self.logger.error(f"[CLIENT] Error processing message: {e}")
        except websockets.ConnectionClosed:
            self.logger.info("[CLIENT] Bridge connection closed")
        except Exception as e:
            self.logger.error(f"[CLIENT] Message handler error: {e}")

    async def initiate_session(self, conversation_id: Optional[str] = None) -> bool:
        """
        Send session.initiate to the bridge.

        Args:
            conversation_id (Optional[str]): Conversation ID to use

        Returns:
            bool: True if session was accepted, False otherwise
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return False

        # Create session
        conv_id = self.session_manager.create_session(conversation_id)

        # Send initiation message
        message = self.session_manager.initiate_session()
        await self._ws.send(json.dumps(message))

        self.logger.info(f"[CLIENT] Sent session.initiate for conversation: {conv_id}")

        # Wait for session.accepted
        for _ in range(100):  # 10 seconds timeout
            if self.session_manager.session_state.accepted:
                return True
            elif self.session_manager.session_state.error:
                self.logger.error(
                    f"[CLIENT] Session rejected: {self.session_manager.session_state.error_reason}"
                )
                return False
            await asyncio.sleep(0.1)

        self.logger.error("[CLIENT] Session not accepted within timeout")
        return False

    async def resume_session(self, conversation_id: str) -> bool:
        """
        Send session.resume to the bridge.

        Args:
            conversation_id (str): Conversation ID to resume

        Returns:
            bool: True if session was resumed, False otherwise
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return False

        # Send resume message
        message = self.session_manager.resume_session(conversation_id)
        await self._ws.send(json.dumps(message))

        self.logger.info(
            f"[CLIENT] Sent session.resume for conversation: {conversation_id}"
        )

        # Wait for session.resumed
        for _ in range(100):  # 10 seconds timeout
            if self.session_manager.session_state.resumed:
                return True
            elif self.session_manager.session_state.error:
                self.logger.error(
                    f"[CLIENT] Session resume failed: {self.session_manager.session_state.error_reason}"
                )
                return False
            await asyncio.sleep(0.1)

        self.logger.error("[CLIENT] Session not resumed within timeout")
        return False

    async def validate_connection(self) -> bool:
        """
        Send connection.validate and wait for response.

        Returns:
            bool: True if connection was validated, False otherwise
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return False

        # Send validation message
        message = self.session_manager.validate_connection()
        await self._ws.send(json.dumps(message))

        self.logger.info(
            f"[CLIENT] Sent connection.validate for conversation: {self.session_manager.get_conversation_id()}"
        )

        # Wait for connection.validated
        for _ in range(50):  # 5 seconds timeout
            if self.session_manager.session_state.connection_validated:
                return True
            await asyncio.sleep(0.1)

        self.logger.error("[CLIENT] Connection validation timeout")
        return False

    async def send_dtmf_event(self, digit: str) -> bool:
        """
        Send DTMF event to bridge.

        Args:
            digit (str): DTMF digit to send

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return False

        try:
            message = self.session_manager.send_dtmf_event(digit)
            await self._ws.send(json.dumps(message))
            return True
        except Exception as e:
            self.logger.error(f"[CLIENT] Error sending DTMF event: {e}")
            return False

    async def send_hangup_event(self) -> bool:
        """
        Send hangup event to bridge.

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return False

        try:
            message = self.session_manager.send_hangup_event()
            await self._ws.send(json.dumps(message))
            return True
        except Exception as e:
            self.logger.error(f"[CLIENT] Error sending hangup event: {e}")
            return False

    async def send_custom_activity(self, activity: Dict[str, Any]) -> bool:
        """
        Send custom activity to bridge.

        Args:
            activity (Dict[str, Any]): Custom activity data

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return False

        try:
            message = self.session_manager.send_custom_activity(activity)
            await self._ws.send(json.dumps(message))
            return True
        except Exception as e:
            self.logger.error(f"[CLIENT] Error sending custom activity: {e}")
            return False

    async def send_user_audio(
        self, audio_file_path: str, chunk_delay: float = 0.02, enable_vad: bool = True
    ) -> bool:
        """
        Send user audio to the bridge with optional VAD processing.

        Args:
            audio_file_path (str): Path to audio file
            chunk_delay (float): Delay between audio chunks
            enable_vad (bool): Whether to enable VAD processing for this audio

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return False

        try:
            # Load audio chunks
            audio_chunks = self.audio_manager.load_audio_chunks(audio_file_path)
            if not audio_chunks:
                return False

            self.logger.info(
                f"[CLIENT] Sending user audio: {audio_file_path} ({len(audio_chunks)} chunks)"
            )

            # Start user stream
            user_stream_start = {
                "type": "userStream.start",
                "conversationId": self.session_manager.get_conversation_id(),
            }
            await self._ws.send(json.dumps(user_stream_start))

            # Wait for userStream.started
            for _ in range(20):
                if self.session_manager.stream_state.user_stream.value == "active":
                    break
                await asyncio.sleep(0.1)
            else:
                self.logger.error("[CLIENT] User stream not started")
                return False

            # Send audio chunks with VAD processing
            for i, chunk in enumerate(audio_chunks):
                audio_chunk_msg = {
                    "type": "userStream.chunk",
                    "conversationId": self.session_manager.get_conversation_id(),
                    "audioChunk": chunk,
                }
                await self._ws.send(json.dumps(audio_chunk_msg))

                # Process VAD if enabled
                if enable_vad and self.vad_manager.enabled:
                    vad_result = self.vad_manager.process_audio_chunk(chunk)
                    if vad_result and self.config.enable_speech_hypothesis:
                        # Simulate speech hypothesis for demonstration
                        if vad_result.get("is_speech", False):
                            # Generate a simple hypothesis based on speech probability
                            prob = vad_result.get("speech_prob", 0.0)
                            if prob > 0.7:
                                self.vad_manager.simulate_speech_hypothesis(
                                    "Hello, I need help", prob
                                )

                if i % 10 == 0 or i == len(audio_chunks) - 1:
                    self.logger.debug(f"[CLIENT] Sent chunk {i+1}/{len(audio_chunks)}")
                await asyncio.sleep(chunk_delay)

            # Stop user stream
            user_stream_stop = {
                "type": "userStream.stop",
                "conversationId": self.session_manager.get_conversation_id(),
            }
            await self._ws.send(json.dumps(user_stream_stop))

            self.logger.info("[CLIENT] User audio sent successfully")
            return True

        except Exception as e:
            self.logger.error(f"[CLIENT] Error sending user audio: {e}")
            return False

    async def send_user_audio_with_vad(
        self, 
        audio_file_path: str, 
        chunk_delay: float = 0.02,
        vad_threshold: float = 0.5,
        simulate_hypothesis: bool = True
    ) -> bool:
        """
        Send user audio with enhanced VAD processing and realistic speech events.

        Args:
            audio_file_path (str): Path to audio file
            chunk_delay (float): Delay between audio chunks
            vad_threshold (float): VAD threshold for speech detection
            simulate_hypothesis (bool): Whether to simulate speech hypothesis

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return False

        if not self.vad_manager.enabled:
            self.logger.warning("[CLIENT] VAD not enabled, falling back to regular audio sending")
            return await self.send_user_audio(audio_file_path, chunk_delay, enable_vad=False)

        try:
            # Load audio chunks
            audio_chunks = self.audio_manager.load_audio_chunks(audio_file_path)
            if not audio_chunks:
                return False

            self.logger.info(
                f"[CLIENT] Sending user audio with VAD: {audio_file_path} ({len(audio_chunks)} chunks)"
            )

            # Start user stream
            user_stream_start = {
                "type": "userStream.start",
                "conversationId": self.session_manager.get_conversation_id(),
            }
            await self._ws.send(json.dumps(user_stream_start))

            # Wait for userStream.started
            for _ in range(20):
                if self.session_manager.stream_state.user_stream.value == "active":
                    break
                await asyncio.sleep(0.1)
            else:
                self.logger.error("[CLIENT] User stream not started")
                return False

            # Reset VAD state
            self.vad_manager.reset()

            # Send audio chunks with enhanced VAD processing
            speech_segments = []
            current_segment = {"start": None, "chunks": [], "end": None}

            for i, chunk in enumerate(audio_chunks):
                # Send audio chunk
                audio_chunk_msg = {
                    "type": "userStream.chunk",
                    "conversationId": self.session_manager.get_conversation_id(),
                    "audioChunk": chunk,
                }
                await self._ws.send(json.dumps(audio_chunk_msg))

                # Process VAD
                vad_result = self.vad_manager.process_audio_chunk(chunk)
                
                if vad_result:
                    speech_prob = vad_result.get("speech_prob", 0.0)
                    is_speech = vad_result.get("is_speech", False)
                    
                    # Track speech segments
                    if is_speech and speech_prob > vad_threshold:
                        if current_segment["start"] is None:
                            current_segment["start"] = i
                        current_segment["chunks"].append(chunk)
                    elif current_segment["start"] is not None:
                        # End of speech segment
                        current_segment["end"] = i
                        speech_segments.append(current_segment.copy())
                        current_segment = {"start": None, "chunks": [], "end": None}

                    # Simulate speech hypothesis if enabled
                    if simulate_hypothesis and is_speech and speech_prob > 0.7:
                        # Generate more realistic hypotheses based on speech probability
                        if speech_prob > 0.9:
                            hypothesis_text = "Hello, I need assistance with my account"
                        elif speech_prob > 0.8:
                            hypothesis_text = "Can you help me please"
                        else:
                            hypothesis_text = "I have a question"
                        
                        self.vad_manager.simulate_speech_hypothesis(hypothesis_text, speech_prob)

                if i % 10 == 0 or i == len(audio_chunks) - 1:
                    self.logger.debug(f"[CLIENT] Sent chunk {i+1}/{len(audio_chunks)}")
                await asyncio.sleep(chunk_delay)

            # Handle final speech segment
            if current_segment["start"] is not None:
                current_segment["end"] = len(audio_chunks) - 1
                speech_segments.append(current_segment)

            # Stop user stream
            user_stream_stop = {
                "type": "userStream.stop",
                "conversationId": self.session_manager.get_conversation_id(),
            }
            await self._ws.send(json.dumps(user_stream_stop))

            # Log speech analysis
            self.logger.info(f"[CLIENT] VAD analysis complete: {len(speech_segments)} speech segments detected")
            for i, segment in enumerate(speech_segments):
                duration = (segment["end"] - segment["start"]) * chunk_delay
                self.logger.info(f"[CLIENT] Segment {i+1}: chunks {segment['start']}-{segment['end']} ({duration:.2f}s)")

            return True

        except Exception as e:
            self.logger.error(f"[CLIENT] Error sending user audio with VAD: {e}")
            return False

    def enable_vad(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Enable VAD processing.

        Args:
            config (Optional[Dict[str, Any]]): VAD configuration

        Returns:
            bool: True if VAD was enabled successfully, False otherwise
        """
        try:
            if config:
                success = self.vad_manager.initialize(config)
            else:
                success = self.vad_manager.initialize()
            
            if success:
                self.config.enable_vad = True
                self.logger.info("[CLIENT] VAD enabled")
            else:
                self.config.enable_vad = False
                self.logger.error("[CLIENT] Failed to enable VAD")
            
            return success
        except Exception as e:
            self.config.enable_vad = False
            self.logger.error(f"[CLIENT] Error enabling VAD: {e}")
            return False

    def disable_vad(self) -> None:
        """Disable VAD processing."""
        self.vad_manager.disable()
        self.config.enable_vad = False
        self.logger.info("[CLIENT] VAD disabled")

    def get_vad_status(self) -> Dict[str, Any]:
        """
        Get VAD status information.

        Returns:
            Dict[str, Any]: VAD status
        """
        return {
            "enabled": self.config.enable_vad,
            "vad_manager_status": self.vad_manager.get_status(),
            "config": {
                "threshold": self.config.vad_threshold,
                "silence_threshold": self.config.vad_silence_threshold,
                "min_speech_duration_ms": self.config.vad_min_speech_duration_ms,
                "enable_speech_hypothesis": self.config.enable_speech_hypothesis,
            }
        }

    def simulate_speech_committed(self, text: str) -> None:
        """
        Simulate a speech committed event.

        Args:
            text (str): Committed text
        """
        if self.vad_manager.enabled:
            self.vad_manager.simulate_speech_committed(text)
        else:
            self.logger.warning("[CLIENT] VAD not enabled, cannot simulate speech committed")

    def simulate_speech_hypothesis(self, text: str, confidence: float = 0.8) -> None:
        """
        Simulate a speech hypothesis event.

        Args:
            text (str): Hypothesized text
            confidence (float): Confidence score
        """
        if self.vad_manager.enabled:
            self.vad_manager.simulate_speech_hypothesis(text, confidence)
        else:
            self.logger.warning("[CLIENT] VAD not enabled, cannot simulate speech hypothesis")

    # ===== LIVE AUDIO CAPTURE METHODS =====

    def start_live_audio_capture(
        self, 
        config: Optional[Dict[str, Any]] = None,
        device_index: Optional[int] = None
    ) -> bool:
        """
        Start live audio capture from microphone.

        Args:
            config (Optional[Dict[str, Any]]): Audio configuration
            device_index (Optional[int]): Audio device index

        Returns:
            bool: True if capture started successfully, False otherwise
        """
        try:
            if self._live_audio_enabled:
                self.logger.warning("[CLIENT] Live audio capture already running")
                return True

            # Create live audio manager
            live_config = config or {}
            if device_index is not None:
                live_config["device_index"] = device_index

            self._live_audio_manager = LiveAudioManager(
                audio_callback=self._handle_live_audio_chunk,
                vad_callback=self._handle_live_vad_event,
                logger=self.logger,
                config=live_config
            )

            # Start capture
            success = self._live_audio_manager.start_capture()
            if success:
                self._live_audio_enabled = True
                self.logger.info("[CLIENT] Live audio capture started")
            else:
                self.logger.error("[CLIENT] Failed to start live audio capture")
                self._live_audio_manager = None

            return success

        except Exception as e:
            self.logger.error(f"[CLIENT] Error starting live audio capture: {e}")
            return False

    def stop_live_audio_capture(self) -> None:
        """Stop live audio capture."""
        if self._live_audio_manager:
            self._live_audio_manager.stop_capture()
            self._live_audio_manager = None
        
        self._live_audio_enabled = False
        self.logger.info("[CLIENT] Live audio capture stopped")

    def _handle_live_audio_chunk(self, audio_chunk: str) -> None:
        """
        Handle live audio chunk from microphone.

        Args:
            audio_chunk (str): Base64-encoded audio chunk
        """
        if not self._live_audio_enabled:
            return

        try:
            # Queue audio chunk for sending (thread-safe)
            try:
                self._audio_queue.put_nowait(audio_chunk)
            except queue.Full:
                self.logger.warning("[CLIENT] Audio queue full, dropping chunk")
                
        except Exception as e:
            self.logger.error(f"[CLIENT] Error handling live audio chunk: {e}")

    def _handle_live_vad_event(self, event: Dict[str, Any]) -> None:
        """
        Handle VAD event from live audio capture.

        Args:
            event (Dict[str, Any]): VAD event data
        """
        if not self._live_audio_enabled:
            return

        try:
            # Queue VAD event for sending (thread-safe)
            try:
                self._vad_queue.put_nowait(event)
            except queue.Full:
                self.logger.warning("[CLIENT] VAD queue full, dropping event")
                
        except Exception as e:
            self.logger.error(f"[CLIENT] Error handling live VAD event: {e}")

    def get_available_audio_devices(self) -> List[Dict[str, Any]]:
        """
        Get list of available audio input devices.

        Returns:
            List[Dict[str, Any]]: List of device information
        """
        try:
            if self._live_audio_manager:
                return self._live_audio_manager.get_available_devices()
            else:
                # Create temporary manager to get device list
                temp_manager = LiveAudioManager(logger=self.logger)
                devices = temp_manager.get_available_devices()
                return devices
        except Exception as e:
            self.logger.error(f"[CLIENT] Error getting audio devices: {e}")
            return []

    def set_audio_device(self, device_index: int) -> bool:
        """
        Set the audio input device for live capture.

        Args:
            device_index (int): Device index

        Returns:
            bool: True if device was set successfully, False otherwise
        """
        if self._live_audio_manager:
            return self._live_audio_manager.set_device(device_index)
        else:
            self.logger.warning("[CLIENT] Live audio not initialized")
            return False

    def get_live_audio_status(self) -> Dict[str, Any]:
        """
        Get live audio capture status.

        Returns:
            Dict[str, Any]: Live audio status information
        """
        if self._live_audio_manager:
            return self._live_audio_manager.get_status()
        else:
            return {
                "running": False,
                "enabled": self._live_audio_enabled,
                "manager": None
            }

    def get_audio_level(self) -> float:
        """
        Get current audio level for visualization.

        Returns:
            float: Current audio level (0.0 to 1.0)
        """
        if self._live_audio_manager:
            return self._live_audio_manager.get_audio_level()
        return 0.0

    def is_live_audio_enabled(self) -> bool:
        """
        Check if live audio capture is enabled.

        Returns:
            bool: True if live audio is enabled, False otherwise
        """
        return self._live_audio_enabled

    # ===== AUDIO PLAYBACK METHODS =====

    def enable_audio_playback(self, volume: float = 1.0) -> bool:
        """
        Enable audio playback for incoming audio.

        Args:
            volume (float): Initial volume level (0.0 to 1.0)

        Returns:
            bool: True if enabled successfully, False otherwise
        """
        if hasattr(self, 'audio_playback'):
            self.audio_playback.set_volume(volume)
            return self.audio_playback.start()
        return False

    def disable_audio_playback(self) -> None:
        """Disable audio playback."""
        if hasattr(self, 'audio_playback'):
            self.audio_playback.stop()

    def set_playback_volume(self, volume: float) -> None:
        """
        Set audio playback volume.

        Args:
            volume (float): Volume level from 0.0 to 1.0
        """
        if hasattr(self, 'audio_playback'):
            self.audio_playback.set_volume(volume)

    def mute_playback(self) -> None:
        """Mute audio playback."""
        if hasattr(self, 'audio_playback'):
            self.audio_playback.mute()

    def unmute_playback(self) -> None:
        """Unmute audio playback."""
        if hasattr(self, 'audio_playback'):
            self.audio_playback.unmute()

    def get_playback_audio_level(self) -> float:
        """
        Get current audio playback level for visualization.

        Returns:
            float: Current audio level (0.0 to 1.0)
        """
        if hasattr(self, 'audio_playback'):
            return self.audio_playback.get_audio_level()
        return 0.0

    def get_audio_playback_status(self) -> Dict[str, Any]:
        """
        Get audio playback status information.

        Returns:
            Dict[str, Any]: Audio playback status
        """
        if hasattr(self, 'audio_playback'):
            return self.audio_playback.get_status()
        return {"enabled": False, "connected": False, "manager_active": False}

    async def wait_for_llm_greeting(self, timeout: float = 20.0) -> List[str]:
        """
        Wait for and collect LLM greeting audio.

        Args:
            timeout (float): Timeout in seconds

        Returns:
            List[str]: List of greeting audio chunks
        """
        return await self.conversation_manager.wait_for_greeting(timeout)

    async def wait_for_llm_response(self, timeout: float = 45.0) -> List[str]:
        """
        Wait for and collect LLM response audio.

        Args:
            timeout (float): Timeout in seconds

        Returns:
            List[str]: List of response audio chunks
        """
        return await self.conversation_manager.wait_for_response(timeout)

    async def multi_turn_conversation(
        self,
        audio_files: List[str],
        wait_for_greeting: bool = True,
        turn_delay: float = 2.0,
        chunk_delay: float = 0.02,
    ) -> ConversationResult:
        """
        Conduct a multi-turn conversation using a list of audio files.

        Args:
            audio_files: List of paths to audio files for user turns
            wait_for_greeting: Whether to wait for initial AI greeting
            turn_delay: Delay between conversation turns (seconds)
            chunk_delay: Delay between audio chunks (seconds)

        Returns:
            ConversationResult: Conversation results and statistics
        """
        return await self.conversation_manager.multi_turn_conversation(
            audio_files, wait_for_greeting, turn_delay, chunk_delay
        )

    async def end_session(self, reason: str = "Test completed") -> None:
        """
        End the session gracefully.

        Args:
            reason (str): Reason for ending the session
        """
        if self._ws is None:
            self.logger.error("[CLIENT] WebSocket connection is None")
            return

        try:
            message = self.session_manager.end_session(reason)
            await self._ws.send(json.dumps(message))
            self.logger.info(f"[CLIENT] Sent session.end: {reason}")
        except Exception as e:
            self.logger.error(f"[CLIENT] Error ending session: {e}")

    def get_session_status(self) -> Dict[str, Any]:
        """
        Get current session status information.

        Returns:
            Dict[str, Any]: Session status information
        """
        status = self.session_manager.get_session_status()
        
        # Add VAD status
        if hasattr(self, 'vad_manager'):
            status["vad"] = self.get_vad_status()
        
        # Add audio playback status
        if hasattr(self, 'audio_playback'):
            status["audio_playback"] = self.audio_playback.get_status()
        
        # Add live audio status
        status["live_audio"] = self.get_live_audio_status()
        
        return status

    def reset_session_state(self) -> None:
        """Reset all session-related state variables."""
        self.session_manager.reset_session_state()
        self.conversation_manager.reset_conversation_state()
        self.message_handler.clear_message_history()
        
        # Reset VAD state
        if hasattr(self, 'vad_manager'):
            self.vad_manager.reset()
        
        # Clean up audio playback
        if hasattr(self, 'audio_playback'):
            self.audio_playback.cleanup()

    def save_collected_audio(self, output_dir: str = "validation_output") -> None:
        """
        Save collected audio for analysis.

        Args:
            output_dir (str): Output directory
        """
        self.conversation_manager.save_collected_audio(output_dir)

    async def simple_conversation_test(
        self, audio_files: List[str], session_name: str = "MultiTurnTest"
    ) -> bool:
        """
        Simple wrapper for testing multi-turn conversations.

        Args:
            audio_files: List of audio files for conversation turns
            session_name: Name for the test session

        Returns:
            bool: True if the conversation was successful, False otherwise
        """
        try:
            # Initiate session
            success = await self.initiate_session()
            if not success:
                self.logger.error("[CLIENT] Failed to initiate session")
                return False

            # Run multi-turn conversation
            result = await self.multi_turn_conversation(audio_files)

            # End session
            await self.end_session(f"{session_name} completed")

            # Save all collected audio
            self.save_collected_audio()

            # Print summary
            self._print_conversation_summary(result)

            return result.success

        except Exception as e:
            self.logger.error(f"[CLIENT] Simple conversation test failed: {e}")
            return False

    def _print_conversation_summary(self, result: ConversationResult) -> None:
        """
        Print a summary of the multi-turn conversation.

        Args:
            result (ConversationResult): Conversation result to summarize
        """
        self.logger.info("\n" + "=" * 50)
        self.logger.info("[CLIENT] MULTI-TURN CONVERSATION SUMMARY")
        self.logger.info("=" * 50)

        success_status = "SUCCESS" if result.success else "FAILED"
        self.logger.info(f"Overall Status: {success_status}")
        self.logger.info(
            f"Completed Turns: {result.completed_turns}/{result.total_turns}"
        )

        if result.greeting_received:
            self.logger.info(
                f"Initial Greeting: Received ({result.greeting_chunks} chunks)"
            )
        else:
            self.logger.info("Initial Greeting: Not received")

        if result.error:
            self.logger.error(f"Overall Error: {result.error}")

        if result.duration:
            self.logger.info(f"Duration: {result.duration:.2f}s")

        self.logger.info(f"Success Rate: {result.success_rate:.1f}%")

        self.logger.info("\nTurn-by-turn Results:")
        for turn in result.turns:
            turn_num = turn["turn_number"]
            audio_file = turn["audio_file"]

            status_parts = []
            if turn["user_audio_sent"]:
                status_parts.append("Audio Sent")
            if turn["ai_response_received"]:
                status_parts.append(
                    f"Response Received ({turn['response_chunks']} chunks)"
                )

            status = " → ".join(status_parts) if status_parts else "Failed"

            self.logger.info(f"  Turn {turn_num}: {audio_file} → {status}")

            if turn.get("error"):
                self.logger.error(f"    Error: {turn['error']}")

        self.logger.info("=" * 50)
