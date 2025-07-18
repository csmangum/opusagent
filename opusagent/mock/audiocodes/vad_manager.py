"""
VAD (Voice Activity Detection) manager for the AudioCodes mock client.

This module provides VAD integration for the AudioCodes mock client, enabling
realistic speech event simulation during audio streaming. It processes audio
chunks in real-time to detect speech activity and emit appropriate VAD events.
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
    provide realistic speech event simulation during audio streaming.

    Attributes:
        logger (logging.Logger): Logger instance for debugging
        vad: VAD backend instance (SileroVAD, etc.)
        enabled (bool): Whether VAD is enabled
        config (Dict[str, Any]): VAD configuration
        stream_state (StreamState): Reference to stream state
        event_callback (Optional[Callable]): Callback for VAD events
        _speech_start_time (Optional[float]): Time when speech started
        _last_vad_result (Optional[Dict]): Last VAD processing result
    """

    def __init__(
        self,
        stream_state: StreamState,
        logger: Optional[logging.Logger] = None,
        event_callback: Optional[Callable] = None,
    ):
        """
        Initialize the VAD manager.

        Args:
            stream_state (StreamState): Stream state to update
            logger (Optional[logging.Logger]): Logger instance for debugging
            event_callback (Optional[Callable]): Callback for VAD events
        """
        self.logger = logger or logging.getLogger(__name__)
        self.stream_state = stream_state
        self.event_callback = event_callback
        self.vad = None
        self.enabled = False
        self.config = {}
        
        # VAD state tracking
        self._speech_start_time: Optional[float] = None
        self._last_vad_result: Optional[Dict] = None
        self._consecutive_speech_chunks = 0
        self._consecutive_silence_chunks = 0
        
        # VAD configuration defaults
        self._vad_config = {
            "threshold": 0.5,
            "silence_threshold": 0.3,
            "min_speech_duration_ms": 500,
            "min_silence_duration_ms": 300,
            "speech_start_threshold": 2,  # consecutive speech chunks
            "speech_stop_threshold": 3,   # consecutive silence chunks
        }

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialize the VAD system.

        Args:
            config (Optional[Dict[str, Any]]): VAD configuration

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Load VAD configuration
            vad_config = load_vad_config()
            if config:
                vad_config.update(config)
            
            # Update internal config
            self._vad_config.update(vad_config)
            self.config = vad_config
            
            # Create VAD instance
            self.vad = VADFactory.create_vad(vad_config)
            if self.vad is None:
                self.logger.error("[VAD] Failed to create VAD instance")
                return False
            
            # Initialize VAD
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
        Process an audio chunk and detect speech activity.

        Args:
            audio_chunk (str): Base64-encoded audio chunk

        Returns:
            Optional[Dict[str, Any]]: VAD result or None if processing failed
        """
        if not self.enabled or self.vad is None:
            return None

        try:
            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_chunk)
            
            # Convert to float32 mono for VAD processing
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float = to_float32_mono(audio_array, 2, 1)  # 16-bit, mono
            
            # Process with VAD
            vad_result = self.vad.process_audio(audio_float)
            
            # Update state and emit events
            self._update_speech_state(vad_result)
            
            return vad_result
            
        except Exception as e:
            self.logger.error(f"[VAD] Error processing audio chunk: {e}")
            return None

    def _update_speech_state(self, vad_result: Dict[str, Any]) -> None:
        """
        Update speech state based on VAD result and emit events.

        Args:
            vad_result (Dict[str, Any]): VAD processing result
        """
        if not vad_result:
            return

        speech_prob = vad_result.get("speech_prob", 0.0)
        is_speech = vad_result.get("is_speech", False)
        speech_state = vad_result.get("speech_state", "idle")
        
        current_time = time.time()
        
        # Update consecutive counters
        if is_speech:
            self._consecutive_speech_chunks += 1
            self._consecutive_silence_chunks = 0
        else:
            self._consecutive_silence_chunks += 1
            self._consecutive_speech_chunks = 0
        
        # Check for speech start
        if (not self.stream_state.speech_active and 
            self._consecutive_speech_chunks >= self._vad_config["speech_start_threshold"]):
            
            self.stream_state.speech_active = True
            self._speech_start_time = current_time
            
            # Emit speech started event
            self._emit_speech_event("userStream.speech.started", {
                "timestamp": current_time,
                "speech_prob": speech_prob
            })
            
            self.logger.info(f"[VAD] Speech started (prob: {speech_prob:.3f})")
        
        # Check for speech stop
        elif (self.stream_state.speech_active and 
              self._consecutive_silence_chunks >= self._vad_config["speech_stop_threshold"]):
            
            self.stream_state.speech_active = False
            
            # Calculate speech duration
            speech_duration = 0
            if self._speech_start_time:
                speech_duration = (current_time - self._speech_start_time) * 1000
                self._speech_start_time = None
            
            # Emit speech stopped event
            self._emit_speech_event("userStream.speech.stopped", {
                "timestamp": current_time,
                "speech_duration_ms": speech_duration,
                "speech_prob": speech_prob
            })
            
            self.logger.info(f"[VAD] Speech stopped (duration: {speech_duration:.1f}ms)")
        
        # Store last result
        self._last_vad_result = vad_result

    def _emit_speech_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Emit a speech event via callback.

        Args:
            event_type (str): Type of speech event
            event_data (Dict[str, Any]): Event data
        """
        if self.event_callback:
            try:
                event = {
                    "type": event_type,
                    "timestamp": event_data.get("timestamp", time.time()),
                    "data": event_data
                }
                self.event_callback(event)
            except Exception as e:
                self.logger.error(f"[VAD] Error emitting speech event: {e}")

    def simulate_speech_hypothesis(self, text: str, confidence: float = 0.8) -> None:
        """
        Simulate speech hypothesis events.

        Args:
            text (str): Hypothesized text
            confidence (float): Confidence score (0.0 to 1.0)
        """
        if not self.enabled:
            return
        
        hypothesis_data = {
            "timestamp": time.time(),
            "alternatives": [
                {
                    "text": text,
                    "confidence": confidence
                }
            ]
        }
        
        self._emit_speech_event("userStream.speech.hypothesis", hypothesis_data)
        self.logger.info(f"[VAD] Speech hypothesis: '{text}' (conf: {confidence:.3f})")

    def simulate_speech_committed(self, text: str) -> None:
        """
        Simulate speech committed event.

        Args:
            text (str): Committed text
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
        """Reset VAD state."""
        if self.vad:
            self.vad.reset()
        
        self._speech_start_time = None
        self._last_vad_result = None
        self._consecutive_speech_chunks = 0
        self._consecutive_silence_chunks = 0
        
        # Reset stream state
        self.stream_state.speech_active = False
        self.stream_state.speech_committed = False
        self.stream_state.current_hypothesis = None
        
        self.logger.info("[VAD] State reset")

    def cleanup(self) -> None:
        """Clean up VAD resources."""
        if self.vad:
            self.vad.cleanup()
            self.vad = None
        
        self.enabled = False
        self.logger.info("[VAD] Cleaned up")

    def get_status(self) -> Dict[str, Any]:
        """
        Get VAD status information.

        Returns:
            Dict[str, Any]: VAD status
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
        """Enable VAD processing."""
        if self.vad is not None:
            self.enabled = True
            self.logger.info("[VAD] Enabled")

    def disable(self) -> None:
        """Disable VAD processing."""
        self.enabled = False
        self.logger.info("[VAD] Disabled") 