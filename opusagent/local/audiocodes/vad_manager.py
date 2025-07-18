"""
VAD (Voice Activity Detection) manager for the AudioCodes mock client.

This module provides comprehensive VAD integration for the AudioCodes mock client,
enabling realistic speech event simulation during audio streaming. It processes
audio chunks in real-time to detect speech activity and emit appropriate VAD events.

The VADManager handles:
- Real-time audio processing and speech detection
- Speech state tracking and event emission
- Configurable VAD thresholds and parameters
- Speech hypothesis and commitment simulation
- Integration with AudioCodes bridge protocol
- Performance optimization and error handling

The VAD manager provides a bridge between the VAD processing system and the
AudioCodes mock client, ensuring realistic speech event generation for testing
scenarios.
"""

import asyncio
import base64
import logging
import time
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from opusagent.vad.audio_processor import to_float32_mono
from opusagent.vad.vad_config import load_vad_config
from opusagent.vad.vad_factory import VADFactory
from .models import StreamState


class VADManager:
    """
    VAD manager for the AudioCodes mock client.

    This class integrates the VAD module with the AudioCodes mock client to
    provide realistic speech event simulation during audio streaming. It processes
    audio chunks in real-time and generates appropriate speech events that match
    the AudioCodes bridge protocol.

    The VADManager provides:
    - Real-time audio processing with configurable VAD backends
    - Speech state tracking with consecutive chunk counting
    - Automatic event emission for speech start/stop events
    - Speech hypothesis and commitment simulation
    - Integration with stream state management
    - Performance monitoring and error handling

    Attributes:
        logger (logging.Logger): Logger instance for debugging and monitoring
        vad: VAD backend instance (SileroVAD, etc.) for audio processing
        enabled (bool): Whether VAD processing is currently enabled
        config (Dict[str, Any]): Current VAD configuration parameters
        stream_state (StreamState): Reference to stream state for updates
        event_callback (Optional[Callable]): Callback function for VAD events
        _speech_start_time (Optional[float]): Timestamp when speech started
        _last_vad_result (Optional[Dict]): Last VAD processing result
        _consecutive_speech_chunks (int): Count of consecutive speech chunks
        _consecutive_silence_chunks (int): Count of consecutive silence chunks
    """

    def __init__(
        self,
        stream_state: StreamState,
        logger: Optional[logging.Logger] = None,
        event_callback: Optional[Callable] = None,
    ):
        """
        Initialize the VAD manager with stream state and optional callbacks.

        Args:
            stream_state (StreamState): Stream state to update with speech events
            logger (Optional[logging.Logger]): Logger instance for debugging and monitoring.
                                             If None, creates a default logger for this module.
            event_callback (Optional[Callable]): Callback function for VAD events.
                                               Should accept event_type and event_data parameters.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.stream_state = stream_state
        self.event_callback = event_callback
        self.vad = None
        self.enabled = False
        self.config = {}
        
        # VAD state tracking for speech detection
        self._speech_start_time: Optional[float] = None
        self._last_vad_result: Optional[Dict] = None
        self._consecutive_speech_chunks = 0
        self._consecutive_silence_chunks = 0
        
        # VAD configuration defaults for speech detection
        self._vad_config = {
            "threshold": 0.5,                    # Speech detection threshold
            "silence_threshold": 0.3,            # Silence detection threshold
            "min_speech_duration_ms": 500,       # Minimum speech duration
            "min_silence_duration_ms": 300,      # Minimum silence duration
            "speech_start_threshold": 2,         # Consecutive speech chunks to start
            "speech_stop_threshold": 3,          # Consecutive silence chunks to stop
        }

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialize the VAD system with configuration.

        This method sets up the VAD backend, loads configuration, and prepares
        the system for real-time audio processing. It handles VAD backend
        creation and initialization with error handling.

        The initialization process:
        1. Load default VAD configuration
        2. Merge with provided configuration
        3. Create VAD backend instance
        4. Initialize VAD with configuration
        5. Enable VAD processing
        6. Log initialization results

        Args:
            config (Optional[Dict[str, Any]]): Additional VAD configuration to merge
                                             with defaults

        Returns:
            bool: True if initialization was successful, False otherwise

        Example:
            success = vad_manager.initialize({
                "threshold": 0.6,
                "min_speech_duration_ms": 300
            })
            if success:
                print("VAD initialized successfully")
        """
        try:
            # Load default VAD configuration
            vad_config = load_vad_config()
            if config:
                vad_config.update(config)
            
            # Update internal configuration
            self._vad_config.update(vad_config)
            self.config = vad_config
            
            # Create VAD backend instance
            self.vad = VADFactory.create_vad(vad_config)
            if self.vad is None:
                self.logger.error("[VAD] Failed to create VAD instance")
                return False
            
            # Initialize VAD backend
            self.vad.initialize(vad_config)
            self.enabled = True
            
            self.logger.info(f"[VAD] Initialized with config: {vad_config}")
            return True
            
        except Exception as e:
            self.logger.error(f"[VAD] Initialization failed: {e}")
            self.enabled = False
            return False

    def process_audio_chunk(self, audio_chunk: str) -> Optional[Dict[str, Any]]:
        """
        Process an audio chunk and detect speech activity in real-time.

        This method takes a base64-encoded audio chunk, processes it through
        the VAD system, and updates speech state accordingly. It handles audio
        format conversion and VAD processing with comprehensive error handling.

        The processing pipeline:
        1. Decode base64 audio chunk to binary data
        2. Convert to numpy array for processing
        3. Convert to float32 mono format for VAD
        4. Process through VAD backend
        5. Update speech state and emit events
        6. Return VAD result for further processing

        Args:
            audio_chunk (str): Base64-encoded audio chunk to process

        Returns:
            Optional[Dict[str, Any]]: VAD processing result containing speech
                                    probability, state, and other metrics, or
                                    None if processing failed

        Example:
            result = vad_manager.process_audio_chunk(base64_audio_chunk)
            if result:
                speech_prob = result.get("speech_prob", 0.0)
                is_speech = result.get("is_speech", False)
        """
        if not self.enabled or self.vad is None:
            return None

        try:
            # Decode base64 audio chunk to binary data
            audio_bytes = base64.b64decode(audio_chunk)
            
            # Convert binary data to numpy array
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # Convert to float32 mono format for VAD processing
            audio_float = to_float32_mono(audio_array, 2, 1)  # 16-bit, mono
            
            # Process audio through VAD backend
            vad_result = self.vad.process_audio(audio_float)
            
            # Update speech state and emit events
            self._update_speech_state(vad_result)
            
            return vad_result
            
        except Exception as e:
            self.logger.error(f"[VAD] Error processing audio chunk: {e}")
            return None

    def _update_speech_state(self, vad_result: Dict[str, Any]) -> None:
        """
        Update speech state based on VAD result and emit appropriate events.

        This method analyzes VAD results to determine speech state changes
        and emits corresponding events. It uses consecutive chunk counting
        to avoid false positives and ensure stable speech detection.

        The state update process:
        1. Extract speech probability and state from VAD result
        2. Update consecutive chunk counters
        3. Check for speech start conditions
        4. Check for speech stop conditions
        5. Emit appropriate events for state changes
        6. Update stream state accordingly

        Args:
            vad_result (Dict[str, Any]): VAD processing result containing
                                       speech probability, state, and other metrics

        Example:
            vad_manager._update_speech_state({
                "speech_prob": 0.8,
                "is_speech": True,
                "speech_state": "speaking"
            })
        """
        if not vad_result:
            return

        # Extract speech metrics from VAD result
        speech_prob = vad_result.get("speech_prob", 0.0)
        is_speech = vad_result.get("is_speech", False)
        speech_state = vad_result.get("speech_state", "idle")
        
        current_time = time.time()
        
        # Update consecutive chunk counters for stability
        if is_speech:
            self._consecutive_speech_chunks += 1
            self._consecutive_silence_chunks = 0
        else:
            self._consecutive_silence_chunks += 1
            self._consecutive_speech_chunks = 0
        
        # Check for speech start condition
        if (not self.stream_state.speech_active and 
            self._consecutive_speech_chunks >= self._vad_config["speech_start_threshold"]):
            
            # Update stream state to indicate speech is active
            self.stream_state.speech_active = True
            self._speech_start_time = current_time
            
            # Emit speech started event
            self._emit_speech_event("userStream.speech.started", {
                "timestamp": current_time,
                "speech_prob": speech_prob
            })
            
            self.logger.info(f"[VAD] Speech started (prob: {speech_prob:.3f})")
        
        # Check for speech stop condition
        elif (self.stream_state.speech_active and 
              self._consecutive_silence_chunks >= self._vad_config["speech_stop_threshold"]):
            
            # Update stream state to indicate speech has stopped
            self.stream_state.speech_active = False
            
            # Calculate speech duration for the completed utterance
            speech_duration = 0
            if self._speech_start_time:
                speech_duration = (current_time - self._speech_start_time) * 1000
                self._speech_start_time = None
            
            # Emit speech stopped event
            self._emit_speech_event("userStream.speech.stopped", {
                "timestamp": current_time,
                "speech_prob": speech_prob,
                "speech_duration_ms": int(speech_duration)
            })
            
            self.logger.info(f"[VAD] Speech stopped (duration: {speech_duration:.0f}ms)")

    def _emit_speech_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Emit a speech event through the callback system.

        This method sends speech events to registered callbacks, enabling
        integration with the AudioCodes bridge protocol and other systems.

        Args:
            event_type (str): Type of speech event (e.g., "userStream.speech.started")
            event_data (Dict[str, Any]): Event data including timestamps and metrics

        Example:
            vad_manager._emit_speech_event("userStream.speech.started", {
                "timestamp": time.time(),
                "speech_prob": 0.8
            })
        """
        if self.event_callback:
            try:
                self.event_callback({
                    "type": event_type,
                    "data": event_data
                })
            except Exception as e:
                self.logger.error(f"[VAD] Error in event callback: {e}")

    def simulate_speech_hypothesis(self, text: str, confidence: float = 0.8) -> None:
        """
        Simulate a speech hypothesis event for testing purposes.

        This method generates a speech hypothesis event, simulating interim
        speech recognition results that would be sent by the bridge server.

        The hypothesis simulation:
        1. Create hypothesis event data with text and confidence
        2. Emit hypothesis event through callback system
        3. Update stream state with hypothesis information
        4. Log hypothesis generation for debugging

        Args:
            text (str): Hypothesized text from speech recognition
            confidence (float): Confidence score for the hypothesis (0.0 to 1.0)

        Example:
            vad_manager.simulate_speech_hypothesis("Hello, how can I help you?", 0.85)
        """
        if not self.enabled:
            return
        
        hypothesis_data = {
            "timestamp": time.time(),
            "alternatives": [{
                "text": text,
                "confidence": confidence
            }]
        }
        
        self._emit_speech_event("userStream.speech.hypothesis", hypothesis_data)
        self.stream_state.current_hypothesis = hypothesis_data["alternatives"]
        self.logger.info(f"[VAD] Speech hypothesis: '{text}' (confidence: {confidence:.2f})")

    def simulate_speech_committed(self, text: str) -> None:
        """
        Simulate a speech committed event for testing purposes.

        This method generates a speech committed event, simulating final
        speech recognition results that would be sent by the bridge server.

        The commitment simulation:
        1. Create committed event data with final text
        2. Emit committed event through callback system
        3. Update stream state to indicate speech is committed
        4. Log commitment generation for debugging

        Args:
            text (str): Final committed text from speech recognition

        Example:
            vad_manager.simulate_speech_committed("I need help with my account")
        """
        if not self.enabled:
            return
        
        committed_data = {
            "timestamp": time.time(),
            "text": text
        }
        
        self._emit_speech_event("userStream.speech.committed", committed_data)
        self.stream_state.speech_committed = True
        self.logger.info(f"[VAD] Speech committed: '{text}'")

    def reset(self) -> None:
        """
        Reset VAD state to initial values.

        This method clears all VAD state and returns the system to its
        initial condition. It's useful for testing scenarios or when
        preparing for a new audio stream.

        The reset process:
        1. Reset VAD backend if available
        2. Clear speech timing and state tracking
        3. Reset consecutive chunk counters
        4. Clear stream state speech flags
        5. Log reset operation

        Example:
            vad_manager.reset()
            print("VAD state reset")
        """
        if self.vad:
            self.vad.reset()
        
        # Reset all state tracking variables
        self._speech_start_time = None
        self._last_vad_result = None
        self._consecutive_speech_chunks = 0
        self._consecutive_silence_chunks = 0
        
        # Reset stream state speech flags
        self.stream_state.speech_active = False
        self.stream_state.speech_committed = False
        self.stream_state.current_hypothesis = None
        
        self.logger.info("[VAD] State reset")

    def cleanup(self) -> None:
        """
        Clean up VAD resources and disable processing.

        This method properly shuts down the VAD system, releasing resources
        and disabling processing. It should be called when the VAD manager
        is no longer needed.

        The cleanup process:
        1. Clean up VAD backend resources
        2. Disable VAD processing
        3. Clear VAD instance reference
        4. Log cleanup operation

        Example:
            vad_manager.cleanup()
            print("VAD resources cleaned up")
        """
        if self.vad:
            self.vad.cleanup()
            self.vad = None
        
        self.enabled = False
        self.logger.info("[VAD] Cleaned up")

    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive VAD status information.

        This method provides detailed information about the current state
        of the VAD system, including configuration, processing status,
        and performance metrics.

        Returns:
            Dict[str, Any]: VAD status information including:
                           - enabled: Whether VAD is currently enabled
                           - speech_active: Whether speech is currently detected
                           - speech_committed: Whether speech has been committed
                           - consecutive_speech_chunks: Count of consecutive speech chunks
                           - consecutive_silence_chunks: Count of consecutive silence chunks
                           - last_vad_result: Last VAD processing result
                           - config: Current VAD configuration

        Example:
            status = vad_manager.get_status()
            print(f"VAD enabled: {status['enabled']}")
            print(f"Speech active: {status['speech_active']}")
        """
        return {
            "enabled": self.enabled,
            "speech_active": self.stream_state.speech_active,
            "speech_committed": self.stream_state.speech_committed,
            "consecutive_speech_chunks": self._consecutive_speech_chunks,
            "consecutive_silence_chunks": self._consecutive_silence_chunks,
            "last_vad_result": self._last_vad_result,
            "config": self._vad_config
        }

    def enable(self) -> None:
        """
        Enable VAD processing.

        This method enables VAD processing if the system has been properly
        initialized. It's useful for temporarily disabling and re-enabling
        VAD without reinitializing the entire system.

        Example:
            vad_manager.enable()
            print("VAD processing enabled")
        """
        if self.vad is not None:
            self.enabled = True
            self.logger.info("[VAD] Enabled")

    def disable(self) -> None:
        """
        Disable VAD processing.

        This method disables VAD processing while keeping the system
        initialized. It's useful for temporarily stopping VAD processing
        without cleaning up resources.

        Example:
            vad_manager.disable()
            print("VAD processing disabled")
        """
        self.enabled = False
        self.logger.info("[VAD] Disabled") 