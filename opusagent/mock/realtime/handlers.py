"""
Event handlers for the LocalRealtime module.

This module provides a comprehensive event handling system for the LocalRealtimeClient,
which simulates the OpenAI Realtime API for testing and development purposes. It includes:

Key Components:
- EventHandlerManager: Centralized event handler registration and management
- Session Management: Handle session creation, updates, and state tracking
- Audio Buffer Operations: Process incoming audio data, speech detection, and buffer management
- Response Management: Handle response creation, cancellation, and lifecycle events

Supported Events:
- session.update: Update session configuration and parameters
- input_audio_buffer.append: Add audio data to the input buffer
- input_audio_buffer.commit: Commit buffered audio to conversation
- input_audio_buffer.clear: Clear the current audio buffer
- response.create: Initiate response generation
- response.cancel: Cancel active response generation

The module implements the complete event flow expected by OpenAI Realtime API clients,
including proper event sequencing, state management, and error handling. It's designed
to be extensible, allowing custom event handlers to be registered for specialized testing
scenarios.

Usage:
    handler_manager = EventHandlerManager(logger, session_config)
    handler_manager.register_event_handler("custom.event", custom_handler)
    await handler_manager.handle_message(json_message)
"""

import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import websockets
from websockets.asyncio.client import ClientConnection

from opusagent.models.openai_api import (
    ClientEventType,
    ResponseCreateOptions,
    ServerEventType,
    SessionConfig,
)
from opusagent.vad.audio_processor import to_float32_mono


class EventHandlerManager:
    """
    Manages event handlers for WebSocket messages in the LocalRealtimeClient.
    
    This class provides a centralized way to register and handle different
    types of WebSocket events, making the mock client extensible and
    maintainable.
    
    Attributes:
        logger (logging.Logger): Logger instance for debugging
        _event_handlers (Dict[str, List[Callable]]): Registered event handlers
        _ws (Optional[ClientConnection]): WebSocket connection
        _session_config (SessionConfig): Current session configuration
        _session_state (Dict[str, Any]): Current session state
    """
    
    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        session_config: Optional[SessionConfig] = None,
        vad: Optional[Any] = None
    ):
        """
        Initialize the EventHandlerManager.
        
        Args:
            logger (Optional[logging.Logger]): Logger instance for debugging.
            session_config (Optional[SessionConfig]): Session configuration.
        """
        self.logger = logger or logging.getLogger(__name__)
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._ws: Optional[ClientConnection] = None
        self._session_config = session_config
        self._vad = vad
        self._session_state: Dict[str, Any] = {
            "session_id": str(uuid.uuid4()),
            "conversation_id": str(uuid.uuid4()),
            "connected": False,
            "active_response_id": None,
            "speech_detected": False,
            "audio_buffer": [],
            "response_audio": [],
            "response_text": ""
        }
        
        # Register default event handlers
        self._register_default_handlers()
        
        # VAD state management
        self._vad_state = {
            "speech_active": False,
            "last_speech_time": None,
            "speech_start_time": None,
            "confidence_history": [],
            "silence_counter": 0,
            "speech_counter": 0
        }
    
    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """
        Register an event handler for a specific event type.
        
        This method allows you to register custom event handlers for processing
        specific types of WebSocket events. Multiple handlers can be registered
        for the same event type.
        
        Args:
            event_type (str): The type of event to handle (e.g., "session.update")
            handler (Callable): Async function to handle the event.
                               Should accept a single dict parameter.
        
        Example:
            ```python
            async def custom_handler(data):
                print(f"Handling event: {data}")
            
            handler_manager.register_event_handler("custom.event", custom_handler)
            ```
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        self.logger.debug(f"Registered handler for event type: {event_type}")
    
    def set_websocket_connection(self, ws: ClientConnection) -> None:
        """
        Set the WebSocket connection for sending events.
        
        Args:
            ws (ClientConnection): WebSocket connection to use for sending events.
        """
        self._ws = ws
    
    def get_session_state(self) -> Dict[str, Any]:
        """
        Get the current session state.
        
        Returns:
            Dict[str, Any]: Current session state.
        """
        return self._session_state.copy()
    
    def update_session_state(self, updates: Dict[str, Any]) -> None:
        """
        Update the session state with new values.
        
        Args:
            updates (Dict[str, Any]): Updates to apply to session state.
        """
        self._session_state.update(updates)
    
    async def handle_message(self, message: str) -> None:
        """
        Handle an incoming WebSocket message.
        
        This method parses the message and routes it to appropriate
        event handlers based on the message type.
        
        Args:
            message (str): Raw WebSocket message to handle.
        """
        try:
            data = json.loads(message)
            event_type = data.get("type")
            
            if event_type in self._event_handlers:
                for handler in self._event_handlers[event_type]:
                    await handler(data)
            else:
                self.logger.warning(f"[MOCK REALTIME] No handler for event type: {event_type}")
                
        except json.JSONDecodeError:
            self.logger.warning(f"[MOCK REALTIME] Received non-JSON message: {message}")
        except Exception as e:
            self.logger.error(f"[MOCK REALTIME] Error processing message: {e}")
    
    async def _send_event(self, event: Dict[str, Any]) -> None:
        """
        Send an event to the connected WebSocket client.
        
        This method serializes and sends an event to the WebSocket connection.
        It handles the JSON serialization and error conditions.
        
        Args:
            event (Dict[str, Any]): Event data to send. Must be JSON serializable.
        
        Raises:
            Exception: If sending fails (e.g., connection closed)
        """
        from opusagent.utils.websocket_utils import WebSocketUtils
        
        success = await WebSocketUtils.safe_send_event(self._ws, event, self.logger)
        if not success:
            raise Exception("Failed to send event to WebSocket")
    
    def _register_default_handlers(self) -> None:
        """
        Register default event handlers for common OpenAI Realtime API events.
        
        This method sets up the default event handlers that process incoming
        WebSocket messages. It registers handlers for session management,
        audio buffer operations, and response creation/cancellation.
        
        Registered Events:
            - session.update: Handle session configuration updates
            - input_audio_buffer.append: Handle incoming audio data
            - input_audio_buffer.commit: Commit audio buffer to conversation
            - input_audio_buffer.clear: Clear the audio buffer
            - response.create: Start response generation
            - response.cancel: Cancel active response generation
        """
        self.register_event_handler(ClientEventType.SESSION_UPDATE, self._handle_session_update)
        self.register_event_handler(ClientEventType.INPUT_AUDIO_BUFFER_APPEND, self._handle_audio_append)
        self.register_event_handler(ClientEventType.INPUT_AUDIO_BUFFER_COMMIT, self._handle_audio_commit)
        self.register_event_handler(ClientEventType.INPUT_AUDIO_BUFFER_CLEAR, self._handle_audio_clear)
        self.register_event_handler(ClientEventType.RESPONSE_CREATE, self._handle_response_create)
        self.register_event_handler(ClientEventType.RESPONSE_CANCEL, self._handle_response_cancel)
    
    async def _handle_session_update(self, data: Dict[str, Any]) -> None:
        """
        Handle session.update events from the client.
        
        This method processes session configuration updates sent by the client.
        It updates the internal session configuration and sends a confirmation
        event back to the client. It also handles VAD configuration updates
        based on turn_detection settings.
        
        Args:
            data (Dict[str, Any]): Session update data containing new configuration.
        """
        session = data.get("session", {})
        
        # Check if turn_detection is being updated
        turn_detection_changed = False
        if "turn_detection" in session:
            old_turn_detection = self._session_config.turn_detection if self._session_config else None
            new_turn_detection = session.get("turn_detection")
            if old_turn_detection != new_turn_detection:
                turn_detection_changed = True
                self.logger.info(f"[MOCK REALTIME] Turn detection changed from {old_turn_detection} to {new_turn_detection}")
        
        if self._session_config:
            # Update session config with new values
            for key, value in session.items():
                if hasattr(self._session_config, key):
                    setattr(self._session_config, key, value)
        
        # Handle VAD configuration based on turn_detection
        if turn_detection_changed:
            await self._handle_vad_configuration_change()
        
        # Send session.updated event
        event = {
            "type": ServerEventType.SESSION_UPDATED,
            "session": session
        }
        await self._send_event(event)
        self.logger.info("[MOCK REALTIME] Session updated successfully")

    async def _handle_vad_configuration_change(self) -> None:
        """
        Handle VAD configuration changes when turn_detection is updated.
        
        This method is called when the turn_detection setting changes in the
        session configuration. It handles enabling or disabling VAD based on
        the new turn_detection setting.
        """
        if not self._session_config:
            return
            
        turn_detection = self._session_config.turn_detection
        
        if turn_detection and turn_detection.get("type") == "server_vad":
            # Enable VAD if not already enabled
            if not self._vad:
                self.logger.info("[MOCK REALTIME] Enabling VAD due to server_vad turn detection")
                # Note: We can't directly call LocalRealtimeClient methods from here
                # The VAD will be enabled when the client processes the session update
            else:
                self.logger.debug("[MOCK REALTIME] VAD already enabled")
        else:
            # Disable VAD if currently enabled
            if self._vad:
                self.logger.info("[MOCK REALTIME] VAD disabled due to turn detection change")
                # Note: We can't directly call LocalRealtimeClient methods from here
                # The VAD will be disabled when the client processes the session update
            else:
                self.logger.debug("[MOCK REALTIME] VAD already disabled")
    
    async def _handle_audio_append(self, data: Dict[str, Any]) -> None:
        """
        Handle input_audio_buffer.append events from the client.
        
        This method processes incoming audio data and adds it to the audio buffer.
        It uses VAD (Voice Activity Detection) for speech detection if enabled,
        otherwise falls back to simple buffer size monitoring.
        
        Args:
            data (Dict[str, Any]): Audio data containing base64-encoded audio.
        """
        audio = data.get("audio")
        if audio:
            try:
                audio_bytes = base64.b64decode(audio)
                self._session_state["audio_buffer"].append(audio_bytes)
                
                # Use VAD for speech detection if available
                if self._vad:
                    await self._process_audio_with_vad(audio_bytes)
                else:
                    # Fallback to simple speech detection
                    if not self._session_state["speech_detected"] and len(self._session_state["audio_buffer"]) > 10:
                        self._session_state["speech_detected"] = True
                        event = {
                            "type": ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED,
                            "audio_start_ms": 0,
                            "item_id": str(uuid.uuid4())
                        }
                        await self._send_event(event)
                        self.logger.debug("[MOCK REALTIME] Speech detection started (simple)")
                    
            except Exception as e:
                self.logger.error(f"[MOCK REALTIME] Error processing audio data: {e}")

    async def _process_audio_with_vad(self, audio_bytes: bytes) -> None:
        """
        Process audio data using VAD to detect speech activity.
        
        This method converts audio data to the format expected by VAD,
        processes it through the VAD system, and sends appropriate
        speech detection events based on the results.
        
        Args:
            audio_bytes (bytes): Raw audio data to process.
        """
        try:
            # Get the audio format from session configuration
            audio_format = self._get_audio_format()
            
            # Convert audio to format expected by VAD
            audio_array = self._convert_audio_for_vad(audio_bytes, audio_format)
            
            if audio_array is None:
                # Fallback to simple detection if conversion fails
                if not self._session_state["speech_detected"] and len(self._session_state["audio_buffer"]) > 10:
                    self._session_state["speech_detected"] = True
                    event = {
                        "type": ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED,
                        "audio_start_ms": 0,
                        "item_id": str(uuid.uuid4())
                    }
                    await self._send_event(event)
                    self.logger.debug("[MOCK REALTIME] Speech detection started (VAD conversion fallback)")
                return
            
            # Process through VAD
            if not self._vad:
                raise ValueError("VAD instance is not available")
            vad_result = self._vad.process_audio(audio_array)
            is_speech = vad_result.get("is_speech", False)
            speech_prob = vad_result.get("speech_prob", 0.0)
            
            # Update VAD state with smoothing and hysteresis
            state_info = self._update_vad_state(is_speech, speech_prob)
            
            # Handle speech state transitions
            if state_info["speech_started"]:
                # Speech started
                self._session_state["speech_detected"] = True
                event = {
                    "type": ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED,
                    "audio_start_ms": 0,
                    "item_id": str(uuid.uuid4())
                }
                await self._send_event(event)
                self.logger.debug(f"[MOCK REALTIME] Speech started (VAD confidence: {state_info['confidence']:.3f})")
                
            elif state_info["speech_stopped"]:
                # Speech stopped
                self._session_state["speech_detected"] = False
                event = {
                    "type": ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED,
                    "audio_end_ms": 0,
                    "item_id": str(uuid.uuid4())
                }
                await self._send_event(event)
                self.logger.debug(f"[MOCK REALTIME] Speech stopped (VAD confidence: {state_info['confidence']:.3f})")
                
            # Log detailed VAD state for debugging (only if state changed)
            if state_info["state_changed"]:
                self.logger.debug(f"[MOCK REALTIME] VAD state: active={state_info['speech_active']}, "
                                f"confidence={state_info['confidence']:.3f}, "
                                f"speech_counter={self._vad_state['speech_counter']}, "
                                f"silence_counter={self._vad_state['silence_counter']}")
                
        except Exception as e:
            self.logger.error(f"[MOCK REALTIME] Error in VAD processing: {e}")
            # Fallback to simple detection if VAD fails
            if not self._session_state["speech_detected"] and len(self._session_state["audio_buffer"]) > 10:
                self._session_state["speech_detected"] = True
                event = {
                    "type": ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED,
                    "audio_start_ms": 0,
                    "item_id": str(uuid.uuid4())
                }
                await self._send_event(event)
                self.logger.debug("[MOCK REALTIME] Speech detection started (VAD fallback)")

    def _convert_audio_for_vad(self, audio_bytes: bytes, input_format: str = "pcm16") -> Optional[Any]:
        """
        Convert audio data to the format expected by VAD processing.
        
        This method handles different audio input formats and converts them
        to the float32 mono format expected by VAD systems.
        
        Args:
            audio_bytes (bytes): Raw audio data to convert.
            input_format (str): Format of input audio ("pcm16", "pcm24", "g711_ulaw", "g711_alaw").
        
        Returns:
            Optional[np.ndarray]: Converted audio array or None if conversion fails.
        """
        try:
            import numpy as np
            
            if input_format == "pcm16":
                # 16-bit PCM mono (most common format)
                return to_float32_mono(audio_bytes, sample_width=2, channels=1)
            elif input_format == "pcm24":
                # 24-bit PCM mono
                return to_float32_mono(audio_bytes, sample_width=3, channels=1)
            elif input_format == "g711_ulaw":
                # G.711 μ-law format (telephony)
                # Note: This would need proper G.711 decoding implementation
                self.logger.warning("[MOCK REALTIME] G.711 μ-law format not fully implemented")
                return None
            elif input_format == "g711_alaw":
                # G.711 A-law format (telephony)
                # Note: This would need proper G.711 decoding implementation
                self.logger.warning("[MOCK REALTIME] G.711 A-law format not fully implemented")
                return None
            else:
                self.logger.warning(f"[MOCK REALTIME] Unknown audio format: {input_format}")
                return None
                
        except Exception as e:
            self.logger.error(f"[MOCK REALTIME] Error converting audio format {input_format}: {e}")
            return None

    def _get_audio_format(self) -> str:
        """
        Get the expected audio format from session configuration.
        
        Returns:
            str: Audio format string (defaults to "pcm16" if not specified).
        """
        if self._session_config and self._session_config.input_audio_format:
            return self._session_config.input_audio_format
        return "pcm16"  # Default format

    def _update_vad_state(self, is_speech: bool, confidence: float) -> Dict[str, Any]:
        """
        Update VAD state tracking and return state transition information.
        
        This method manages the VAD state transitions and provides smoothing
        to prevent rapid speech on/off transitions. It tracks confidence history
        and implements simple hysteresis to improve detection stability.
        
        Args:
            is_speech (bool): Whether speech is currently detected
            confidence (float): VAD confidence score (0.0 to 1.0)
            
        Returns:
            Dict[str, Any]: State transition information with keys:
                - speech_started: bool
                - speech_stopped: bool
                - state_changed: bool
                - confidence: float
        """
        try:
            import time
            current_time = time.time()
        except Exception as e:
            self.logger.warning(f"[MOCK REALTIME] Error getting current time: {e}")
            # Use a fallback time value
            current_time = 0.0
        
        # Update confidence history (keep last 5 values for smoothing)
        self._vad_state["confidence_history"].append(confidence)
        if len(self._vad_state["confidence_history"]) > 5:
            self._vad_state["confidence_history"].pop(0)
        
        # Calculate smoothed confidence
        smoothed_confidence = sum(self._vad_state["confidence_history"]) / len(self._vad_state["confidence_history"])
        
        # Update speech/silence counters for hysteresis
        if is_speech:
            self._vad_state["speech_counter"] += 1
            self._vad_state["silence_counter"] = 0
        else:
            self._vad_state["silence_counter"] += 1
            self._vad_state["speech_counter"] = 0
        
        # Determine state transitions with hysteresis
        # Require 2 consecutive speech detections to start speech
        # Require 3 consecutive silence detections to stop speech
        speech_started = False
        speech_stopped = False
        
        current_speech_active = self._vad_state["speech_active"]
        
        if not current_speech_active and self._vad_state["speech_counter"] >= 2:
            # Start speech
            self._vad_state["speech_active"] = True
            self._vad_state["speech_start_time"] = current_time
            speech_started = True
            
        elif current_speech_active and self._vad_state["silence_counter"] >= 3:
            # Stop speech
            self._vad_state["speech_active"] = False
            self._vad_state["last_speech_time"] = current_time
            speech_stopped = True
        
        return {
            "speech_started": speech_started,
            "speech_stopped": speech_stopped,
            "state_changed": speech_started or speech_stopped,
            "confidence": smoothed_confidence,
            "speech_active": self._vad_state["speech_active"]
        }

    def _reset_vad_state(self) -> None:
        """
        Reset VAD state tracking to initial values.
        
        This method is called when the audio buffer is cleared or committed
        to reset the VAD state management for the next audio session.
        """
        self._vad_state = {
            "speech_active": False,
            "last_speech_time": None,
            "speech_start_time": None,
            "confidence_history": [],
            "silence_counter": 0,
            "speech_counter": 0
        }
        self.logger.debug("[MOCK REALTIME] VAD state reset")

    async def _handle_audio_commit(self, data: Dict[str, Any]) -> None:
        """
        Handle input_audio_buffer.commit events from the client.
        
        This method commits the current audio buffer to the conversation,
        creating a new conversation item. It sends a confirmation event
        and clears the buffer for future use.
        
        Args:
            data (Dict[str, Any]): Commit event data (usually empty).
        """
        if self._session_state["audio_buffer"]:
            # Create a new conversation item
            item_id = str(uuid.uuid4())
            
            # Send committed event
            event = {
                "type": ServerEventType.INPUT_AUDIO_BUFFER_COMMITTED,
                "item_id": item_id
            }
            await self._send_event(event)
            
            # Clear buffer
            self._session_state["audio_buffer"].clear()
            self._session_state["speech_detected"] = False
            
            # Reset VAD state for next audio session
            self._reset_vad_state()
            
            self.logger.info(f"[MOCK REALTIME] Audio buffer committed, item_id: {item_id}")
        else:
            self.logger.warning("[MOCK REALTIME] Attempted to commit empty audio buffer")
    
    async def _handle_audio_clear(self, data: Dict[str, Any]) -> None:
        """
        Handle input_audio_buffer.clear events from the client.
        
        This method clears the current audio buffer and resets speech detection.
        It sends a confirmation event back to the client and resets VAD state.
        
        Args:
            data (Dict[str, Any]): Clear event data (usually empty).
        """
        self._session_state["audio_buffer"].clear()
        self._session_state["speech_detected"] = False
        
        # Reset VAD state for next audio session
        self._reset_vad_state()
        
        event = {
            "type": ServerEventType.INPUT_AUDIO_BUFFER_CLEARED
        }
        await self._send_event(event)
        self.logger.info("[MOCK REALTIME] Audio buffer cleared")
    
    async def _handle_response_create(self, data: Dict[str, Any]) -> None:
        """
        Handle response.create events from the client.
        
        This method initiates response generation based on the client's request.
        It creates a new response ID, sends a response.created event, and
        starts the response generation process in the background.
        
        Args:
            data (Dict[str, Any]): Response creation data containing options.
        """
        response = data.get("response", {})
        self._session_state["active_response_id"] = str(uuid.uuid4())
        
        # Send response.created event
        event = {
            "type": ServerEventType.RESPONSE_CREATED,
            "response": {
                "id": self._session_state["active_response_id"],
                "created_at": int(datetime.now().timestamp() * 1000)
            }
        }
        await self._send_event(event)
        
        # Start response generation (this will be handled by the main client)
        self.logger.info(f"[MOCK REALTIME] Response generation started: {self._session_state['active_response_id']}")
    
    async def _handle_response_cancel(self, data: Dict[str, Any]) -> None:
        """
        Handle response.cancel events from the client.
        
        This method cancels an active response generation. It checks if the
        specified response ID matches the active response and sends a
        cancellation confirmation event.
        
        Args:
            data (Dict[str, Any]): Cancel event data containing response_id.
        """
        response_id = data.get("response_id")
        if response_id == self._session_state["active_response_id"]:
            self._session_state["active_response_id"] = None
            
            event = {
                "type": ServerEventType.RESPONSE_CANCELLED,
                "response_id": response_id
            }
            await self._send_event(event)
            self.logger.info(f"[MOCK REALTIME] Response cancelled: {response_id}")
        else:
            self.logger.warning(f"[MOCK REALTIME] Attempted to cancel non-active response: {response_id}")
    
    async def send_session_created(self) -> None:
        """
        Send a session.created event to simulate session initialization.
        
        This method sends the initial session.created event that the
        OpenAI Realtime API sends when a connection is established.
        It includes the current session configuration and metadata.
        
        The event contains:
        - Session ID and creation timestamp
        - Model configuration and modalities
        - Voice settings and audio formats
        - Tool configurations and other settings
        """
        if not self._session_config:
            self.logger.error("[MOCK REALTIME] No session config available for session.created")
            return
            
        event = {
            "type": ServerEventType.SESSION_CREATED,
            "session": {
                "id": self._session_state["session_id"],
                "created_at": int(datetime.now().timestamp() * 1000),
                "modalities": self._session_config.modalities,
                "model": self._session_config.model,
                "instructions": self._session_config.instructions,
                "voice": self._session_config.voice,
                "input_audio_format": self._session_config.input_audio_format,
                "output_audio_format": self._session_config.output_audio_format,
                "turn_detection": self._session_config.turn_detection,
                "tools": self._session_config.tools,
                "tool_choice": self._session_config.tool_choice,
                "temperature": self._session_config.temperature,
                "max_response_output_tokens": self._session_config.max_response_output_tokens,
                "input_audio_transcription": self._session_config.input_audio_transcription,
                "input_audio_noise_reduction": self._session_config.input_audio_noise_reduction,
            }
        }
        await self._send_event(event) 