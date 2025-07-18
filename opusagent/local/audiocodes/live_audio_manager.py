"""
Live audio capture for the AudioCodes mock client.

This module provides real-time microphone input functionality for the AudioCodes
mock client, enabling live testing scenarios with actual voice input.
"""

import asyncio
import base64
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import pyaudio
from scipy import signal


class LiveAudioManager:
    """
    Live audio capture manager for the AudioCodes mock client.

    This class handles real-time microphone input, audio processing, and
    streaming to the bridge server. It supports VAD integration and
    configurable audio parameters.

    Attributes:
        logger (logging.Logger): Logger instance for debugging
        audio_callback (Optional[Callable]): Callback for processed audio chunks
        vad_callback (Optional[Callable]): Callback for VAD events
        _audio_stream: PyAudio stream for microphone input
        _capture_thread: Thread for audio capture
        _running: Flag to control capture loop
        _audio_buffer: Buffer for audio data
        _config: Audio configuration
    """

    def __init__(
        self,
        audio_callback: Optional[Callable[[str], None]] = None,
        vad_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        logger: Optional[logging.Logger] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the LiveAudioManager.

        Args:
            audio_callback (Optional[Callable]): Callback for audio chunks
            vad_callback (Optional[Callable]): Callback for VAD events
            logger (Optional[logging.Logger]): Logger instance for debugging
            config (Optional[Dict[str, Any]]): Audio configuration
        """
        self.logger = logger or logging.getLogger(__name__)
        self.audio_callback = audio_callback
        self.vad_callback = vad_callback

        # Default configuration
        self._config = {
            "sample_rate": 16000,
            "channels": 1,
            "chunk_size": 1024,
            "format": pyaudio.paInt16,
            "device_index": None,  # Use default device
            "vad_enabled": True,
            "vad_threshold": 0.5,
            "vad_silence_threshold": 0.3,
            "min_speech_duration_ms": 500,
            "min_silence_duration_ms": 300,
            "chunk_delay": 0.02,
            "buffer_size": 32000,  # 2 seconds at 16kHz
        }
        
        if config:
            self._config.update(config)

        # Audio capture state
        self._audio_stream = None
        self._capture_thread = None
        self._running = False
        self._audio_buffer = []
        self._pyaudio = None
        
        # VAD state
        self._speech_active = False
        self._speech_start_time = None
        self._silence_start_time = None
        self._last_vad_time = 0

    def start_capture(self) -> bool:
        """
        Start live audio capture from microphone.

        Returns:
            bool: True if capture started successfully, False otherwise
        """
        try:
            if self._running:
                self.logger.warning("[LIVE_AUDIO] Capture already running")
                return True

            self._pyaudio = pyaudio.PyAudio()
            
            # Get available devices
            device_info = self._get_default_device_info()
            if device_info:
                self.logger.info(f"[LIVE_AUDIO] Using device: {device_info['name']}")

            # Open audio stream
            self._audio_stream = self._pyaudio.open(
                format=self._config["format"],
                channels=self._config["channels"],
                rate=self._config["sample_rate"],
                input=True,
                input_device_index=self._config["device_index"],
                frames_per_buffer=self._config["chunk_size"],
                stream_callback=self._audio_callback_internal
            )

            self._running = True
            self._audio_buffer.clear()
            
            # Start capture thread
            self._capture_thread = threading.Thread(target=self._capture_loop)
            self._capture_thread.daemon = True
            self._capture_thread.start()

            self.logger.info("[LIVE_AUDIO] Live audio capture started")
            return True

        except Exception as e:
            self.logger.error(f"[LIVE_AUDIO] Error starting capture: {e}")
            self._cleanup()
            return False

    def stop_capture(self) -> None:
        """Stop live audio capture."""
        self._running = False
        
        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None

        self._cleanup()
        self.logger.info("[LIVE_AUDIO] Live audio capture stopped")

    def _cleanup(self) -> None:
        """Clean up audio resources."""
        if self._audio_stream:
            try:
                self._audio_stream.stop_stream()
                self._audio_stream.close()
            except Exception as e:
                self.logger.error(f"[LIVE_AUDIO] Error closing audio stream: {e}")
            finally:
                self._audio_stream = None

        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception as e:
                self.logger.error(f"[LIVE_AUDIO] Error terminating PyAudio: {e}")
            finally:
                self._pyaudio = None

    def _get_default_device_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the default input device."""
        try:
            if self._pyaudio is None:
                return None
                
            if self._config["device_index"] is not None:
                device_info = self._pyaudio.get_device_info_by_index(
                    self._config["device_index"]
                )
            else:
                device_info = self._pyaudio.get_default_input_device_info()
            
            return {
                "name": device_info.get("name", "Unknown"),
                "index": device_info.get("index", -1),
                "channels": device_info.get("maxInputChannels", 1),
                "sample_rate": device_info.get("defaultSampleRate", 16000),
            }
        except Exception as e:
            self.logger.warning(f"[LIVE_AUDIO] Could not get device info: {e}")
            return None

    def _audio_callback_internal(self, in_data, frame_count, time_info, status):
        """Internal PyAudio callback for audio data."""
        if status:
            self.logger.warning(f"[LIVE_AUDIO] Audio callback status: {status}")
        
        if self._running:
            # Convert to numpy array for processing
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            self._audio_buffer.extend(audio_data)
            
            # Process buffer if it's large enough
            if len(self._audio_buffer) >= self._config["buffer_size"]:
                self._process_audio_buffer()
        
        return (None, pyaudio.paContinue)

    def _capture_loop(self) -> None:
        """Main capture loop for processing audio data."""
        while self._running:
            try:
                # Process any remaining audio in buffer
                if self._audio_buffer:
                    self._process_audio_buffer()
                
                time.sleep(self._config["chunk_delay"])
                
            except Exception as e:
                self.logger.error(f"[LIVE_AUDIO] Error in capture loop: {e}")
                break

    def _process_audio_buffer(self) -> None:
        """Process accumulated audio buffer."""
        if not self._audio_buffer:
            return

        # Convert buffer to numpy array
        audio_array = np.array(self._audio_buffer, dtype=np.int16)
        self._audio_buffer.clear()

        # Process VAD if enabled
        if self._config["vad_enabled"]:
            self._process_vad(audio_array)

        # Convert to base64 and send via callback
        audio_bytes = audio_array.tobytes()
        encoded_chunk = base64.b64encode(audio_bytes).decode("utf-8")
        
        if self.audio_callback:
            self.audio_callback(encoded_chunk)

    def _process_vad(self, audio_array: np.ndarray) -> None:
        """
        Process Voice Activity Detection on audio data.

        Args:
            audio_array (np.ndarray): Audio data as numpy array
        """
        try:
            # Handle empty arrays
            if len(audio_array) == 0:
                return
            
            # Simple energy-based VAD
            energy = np.mean(np.abs(audio_array))
            normalized_energy = energy / 32768.0  # Normalize to 0-1 range
            
            current_time = time.time()
            
            # Determine speech state
            if normalized_energy > self._config["vad_threshold"]:
                if not self._speech_active:
                    # Speech started
                    self._speech_active = True
                    self._speech_start_time = current_time
                    self._silence_start_time = None
                    
                    if self.vad_callback:
                        self.vad_callback({
                            "type": "userStream.speech.started",
                            "data": {
                                "speech_prob": normalized_energy,
                                "timestamp": current_time
                            }
                        })
                        self.logger.debug(f"[LIVE_AUDIO] Speech started (energy: {normalized_energy:.3f})")
                
                self._last_vad_time = current_time
                
            elif normalized_energy < self._config["vad_silence_threshold"]:
                if self._speech_active:
                    # Check if silence duration is long enough
                    silence_duration = (current_time - self._last_vad_time) * 1000
                    
                    if silence_duration >= self._config["min_silence_duration_ms"]:
                        # Check if speech duration meets minimum requirement
                        speech_duration = 0
                        if self._speech_start_time:
                            speech_duration = (self._last_vad_time - self._speech_start_time) * 1000
                        
                        # Only stop speech if it has met the minimum duration requirement
                        if speech_duration >= self._config["min_speech_duration_ms"]:
                            # Speech stopped
                            self._speech_active = False
                            self._silence_start_time = current_time
                            
                            if self.vad_callback:
                                self.vad_callback({
                                    "type": "userStream.speech.stopped",
                                    "data": {
                                        "speech_prob": normalized_energy,
                                        "speech_duration_ms": int(speech_duration),
                                        "timestamp": current_time
                                    }
                                })
                                self.logger.debug(f"[LIVE_AUDIO] Speech stopped (duration: {speech_duration:.0f}ms)")
                        else:
                            # Speech duration too short, keep it active
                            self.logger.debug(f"[LIVE_AUDIO] Speech duration too short ({speech_duration:.0f}ms), keeping active")
                
        except Exception as e:
            self.logger.error(f"[LIVE_AUDIO] VAD processing error: {e}")

    def get_available_devices(self) -> List[Dict[str, Any]]:
        """
        Get list of available audio input devices.

        Returns:
            List[Dict[str, Any]]: List of device information
        """
        devices = []
        
        try:
            if not self._pyaudio:
                self._pyaudio = pyaudio.PyAudio()
            
            for i in range(self._pyaudio.get_device_count()):
                try:
                    device_info = self._pyaudio.get_device_info_by_index(i)
                    max_channels = device_info.get("maxInputChannels", 0)
                    if isinstance(max_channels, (int, float)) and max_channels > 0:
                        devices.append({
                            "index": i,
                            "name": device_info.get("name", f"Device {i}"),
                            "channels": max_channels,
                            "sample_rate": device_info.get("defaultSampleRate", 16000),
                            "is_default": device_info.get("index") == self._pyaudio.get_default_input_device_info().get("index")
                        })
                except Exception as e:
                    self.logger.debug(f"[LIVE_AUDIO] Error getting device {i} info: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"[LIVE_AUDIO] Error getting available devices: {e}")
        
        return devices

    def set_device(self, device_index: int) -> bool:
        """
        Set the audio input device.

        Args:
            device_index (int): Device index

        Returns:
            bool: True if device was set successfully, False otherwise
        """
        if self._running:
            self.logger.warning("[LIVE_AUDIO] Cannot change device while capture is running")
            return False

        devices = self.get_available_devices()
        device_indices = [d["index"] for d in devices]
        
        if device_index in device_indices:
            self._config["device_index"] = device_index
            self.logger.info(f"[LIVE_AUDIO] Set device to index {device_index}")
            return True
        else:
            self.logger.error(f"[LIVE_AUDIO] Invalid device index: {device_index}")
            return False

    def update_config(self, config: Dict[str, Any]) -> None:
        """
        Update audio configuration.

        Args:
            config (Dict[str, Any]): New configuration values
        """
        if self._running:
            self.logger.warning("[LIVE_AUDIO] Cannot update config while capture is running")
            return

        self._config.update(config)
        self.logger.info(f"[LIVE_AUDIO] Configuration updated: {list(config.keys())}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status information.

        Returns:
            Dict[str, Any]: Status information
        """
        return {
            "running": self._running,
            "config": self._config.copy(),
            "speech_active": self._speech_active,
            "buffer_size": len(self._audio_buffer),
            "device_index": self._config["device_index"],
            "vad_enabled": self._config["vad_enabled"],
        }

    def is_capturing(self) -> bool:
        """
        Check if audio capture is currently running.

        Returns:
            bool: True if capturing, False otherwise
        """
        return self._running

    def get_audio_level(self) -> float:
        """
        Get current audio level (for visualization).

        Returns:
            float: Current audio level (0.0 to 1.0)
        """
        if not self._audio_buffer:
            return 0.0
        
        try:
            audio_array = np.array(self._audio_buffer, dtype=np.int16)
            energy = np.mean(np.abs(audio_array))
            return float(min(energy / 32768.0, 1.0))
        except Exception:
            return 0.0 