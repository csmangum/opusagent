"""
Audio management for the TUI application.

This module provides real-time audio playback, recording, and streaming
capabilities for testing TelephonyRealtimeBridge functionality.
"""

import asyncio
import base64
import logging
import threading
import time
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import queue

import sounddevice as sd
import numpy as np
from scipy import signal

from opusagent.config.constants import DEFAULT_SAMPLE_RATE

logger = logging.getLogger(__name__)

class AudioFormat(Enum):
    """Supported audio formats."""
    PCM16 = "raw/lpcm16"
    G711_ULAW = "g711/ulaw" 
    G711_ALAW = "g711/alaw"

@dataclass
class AudioConfig:
    """Audio configuration settings."""
    sample_rate: int = DEFAULT_SAMPLE_RATE
    channels: int = 1
    chunk_size: int = 1024  # frames per chunk
    format: AudioFormat = AudioFormat.PCM16
    buffer_size: int = 8192  # frames to buffer
    latency: float = 0.1  # target latency in seconds

class AudioManager:
    """
    Manages real-time audio playback, recording, and streaming.
    
    Provides low-latency audio operations for TelephonyRealtimeBridge testing
    with support for multiple audio formats and real-time visualization.
    """
    
    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        
        # Playback state
        self.playing = False
        self.recording = False
        self.volume = 1.0  # 0.0 to 1.0
        self.muted = False
        
        # Audio streams
        self.input_stream: Optional[sd.InputStream] = None
        self.output_stream: Optional[sd.OutputStream] = None
        
        # Audio buffers
        self.playback_queue = queue.Queue(maxsize=20)
        self.recording_queue = queue.Queue(maxsize=20)
        
        # Threading
        self.playback_thread: Optional[threading.Thread] = None
        self.recording_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Audio analysis
        self.current_input_level = 0.0
        self.current_output_level = 0.0
        self._level_decay = 0.95
        
        # Event callbacks
        self.on_audio_chunk: Optional[Callable[[bytes], None]] = None
        self.on_level_update: Optional[Callable[[float, float], None]] = None
        self.on_playback_complete: Optional[Callable[[], None]] = None
        
        # Statistics
        self.bytes_played = 0
        self.bytes_recorded = 0
        self.chunks_played = 0
        self.chunks_recorded = 0
        
        logger.info(f"AudioManager initialized: {self.config}")
    
    def start_playback(self) -> bool:
        """Start audio playback system."""
        if self.playing:
            logger.warning("Playback already active")
            return True
        
        try:
            # Clear any existing data
            while not self.playback_queue.empty():
                self.playback_queue.get_nowait()
            
            self.playing = True
            self._stop_event.clear()
            
            # Start playback thread
            self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self.playback_thread.start()
            
            logger.info("Audio playback started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start playback: {e}")
            self.playing = False
            return False
    
    def stop_playback(self) -> None:
        """Stop audio playback system."""
        if not self.playing:
            return
        
        self.playing = False
        self._stop_event.set()
        
        # Wait for thread to finish
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=2.0)
        
        # Clean up stream
        if self.output_stream:
            self.output_stream.stop()
            self.output_stream.close()
            self.output_stream = None
        
        logger.info("Audio playback stopped")
    
    def start_recording(self) -> bool:
        """Start audio recording from microphone."""
        if self.recording:
            logger.warning("Recording already active")
            return True
        
        try:
            # Clear any existing data
            while not self.recording_queue.empty():
                self.recording_queue.get_nowait()
            
            self.recording = True
            self._stop_event.clear()
            
            # Start recording thread
            self.recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
            self.recording_thread.start()
            
            logger.info("Audio recording started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.recording = False
            return False
    
    def stop_recording(self) -> None:
        """Stop audio recording."""
        if not self.recording:
            return
        
        self.recording = False
        self._stop_event.set()
        
        # Wait for thread to finish
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=2.0)
        
        # Clean up stream
        if self.input_stream:
            self.input_stream.stop()
            self.input_stream.close()
            self.input_stream = None
        
        logger.info("Audio recording stopped")
    
    async def play_audio_chunk(self, audio_data: bytes) -> None:
        """Queue audio chunk for playback."""
        try:
            if not self.playing:
                logger.warning("Cannot queue audio: playback not active")
                return
            
            # Add to playback queue (non-blocking)
            try:
                self.playback_queue.put_nowait(audio_data)
                self.chunks_played += 1
                self.bytes_played += len(audio_data)
            except queue.Full:
                logger.warning("Playback queue full, dropping audio chunk")
                
        except Exception as e:
            logger.error(f"Error queuing audio chunk: {e}")
    
    async def get_recorded_chunk(self) -> Optional[bytes]:
        """Get next recorded audio chunk."""
        try:
            if not self.recording:
                return None
            
            # Non-blocking get from recording queue
            try:
                chunk = self.recording_queue.get_nowait()
                self.chunks_recorded += 1
                self.bytes_recorded += len(chunk)
                return chunk
            except queue.Empty:
                return None
                
        except Exception as e:
            logger.error(f"Error getting recorded chunk: {e}")
            return None
    
    def _playback_loop(self) -> None:
        """Main playback loop running in separate thread."""
        try:
            # Open output stream
            self.output_stream = sd.OutputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=np.int16,
                latency=self.config.latency,
                blocksize=self.config.chunk_size,
                callback=self._playback_callback
            )
            
            self.output_stream.start()
            
            # Keep thread alive while playing
            while self.playing and not self._stop_event.is_set():
                time.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Error in playback loop: {e}")
        finally:
            if self.output_stream:
                self.output_stream.stop()
                self.output_stream.close()
    
    def _recording_loop(self) -> None:
        """Main recording loop running in separate thread."""
        try:
            # Open input stream  
            self.input_stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=np.int16,
                latency=self.config.latency,
                blocksize=self.config.chunk_size,
                callback=self._recording_callback
            )
            
            self.input_stream.start()
            
            # Keep thread alive while recording
            while self.recording and not self._stop_event.is_set():
                time.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Error in recording loop: {e}")
        finally:
            if self.input_stream:
                self.input_stream.stop()
                self.input_stream.close()
    
    def _playback_callback(self, outdata: np.ndarray, frames: int, time, status) -> None:
        """Audio playback callback function."""
        try:
            if status:
                logger.warning(f"Playback status: {status}")
            
            # Initialize with silence
            outdata.fill(0)
            
            # Try to get data from queue
            try:
                audio_bytes = self.playback_queue.get_nowait()
                
                # Convert bytes to numpy array
                audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
                
                # Handle volume and mute
                if self.muted:
                    audio_array = audio_array * 0
                else:
                    audio_array = audio_array * self.volume
                
                # Reshape to match output channels
                if self.config.channels == 1:
                    audio_array = audio_array.reshape(-1, 1)
                
                # Copy to output buffer (handle size mismatch)
                copy_frames = min(frames, len(audio_array))
                outdata[:copy_frames] = audio_array[:copy_frames]
                
                # Calculate output level for visualization
                if len(audio_array) > 0:
                    level = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2)) / 32768.0
                    self.current_output_level = max(level, self.current_output_level * self._level_decay)
                
                # Debug: Log when audio is actually being played
                logger.debug(f"Playing audio chunk: {len(audio_bytes)} bytes, level: {self.current_output_level:.3f}, copy_frames: {copy_frames}")
                
                # Check if audio data is non-zero (not silence)
                if np.any(audio_array != 0):
                    logger.info(f"🎵 Non-zero audio data detected: max={np.max(np.abs(audio_array))}, mean={np.mean(np.abs(audio_array)):.1f}")
                else:
                    logger.warning("🔇 Audio data is all zeros (silence)")
                
            except queue.Empty:
                # No data available, output silence
                self.current_output_level *= self._level_decay
                logger.debug("No audio data in queue, outputting silence")
                
        except Exception as e:
            logger.error(f"Error in playback callback: {e}")
    
    def _recording_callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        """Audio recording callback function."""
        try:
            if status:
                logger.warning(f"Recording status: {status}")
            
            # Convert to bytes
            audio_bytes = indata.astype(np.int16).tobytes()
            
            # Calculate input level for visualization
            level = np.sqrt(np.mean(indata.astype(np.float32) ** 2))
            self.current_input_level = max(level, self.current_input_level * self._level_decay)
            
            # Queue the audio data
            try:
                self.recording_queue.put_nowait(audio_bytes)
                
                # Trigger callback if set
                if self.on_audio_chunk:
                    self.on_audio_chunk(audio_bytes)
                    
            except queue.Full:
                logger.warning("Recording queue full, dropping audio chunk")
                
        except Exception as e:
            logger.error(f"Error in recording callback: {e}")
    
    def set_volume(self, volume: float) -> None:
        """Set playback volume (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, volume))
        logger.debug(f"Volume set to {self.volume:.2f}")
    
    def set_mute(self, muted: bool) -> None:
        """Set mute state."""
        self.muted = muted
        logger.debug(f"Mute set to {self.muted}")
    
    def get_volume_level(self) -> Tuple[float, float]:
        """Get current input and output volume levels."""
        return self.current_input_level, self.current_output_level
    
    def get_statistics(self) -> Dict[str, int]:
        """Get audio processing statistics."""
        return {
            "bytes_played": self.bytes_played,
            "bytes_recorded": self.bytes_recorded,
            "chunks_played": self.chunks_played,
            "chunks_recorded": self.chunks_recorded,
            "queue_size_playback": self.playback_queue.qsize(),
            "queue_size_recording": self.recording_queue.qsize(),
        }
    
    def cleanup(self) -> None:
        """Clean up audio resources."""
        self.stop_playback()
        self.stop_recording()
        logger.info("AudioManager cleanup complete")
    
    @staticmethod
    def get_available_devices() -> Dict[str, List]:
        """Get available audio input/output devices."""
        try:
            devices = sd.query_devices()
            input_devices = []
            output_devices = []
            
            for i, device in enumerate(devices):
                # Cast device to Dict[str, Any] for type safety
                device_dict: Dict[str, Any] = device  # type: ignore
                device_info = {
                    "index": i,
                    "name": str(device_dict.get("name", f"Device {i}")),
                    "channels": int(device_dict.get("max_input_channels", 0) if device_dict.get("max_input_channels", 0) > 0 else device_dict.get("max_output_channels", 0))
                }
                
                if int(device_dict.get("max_input_channels", 0)) > 0:
                    input_devices.append(device_info)
                if int(device_dict.get("max_output_channels", 0)) > 0:
                    output_devices.append(device_info)
            
            return {
                "input": input_devices,
                "output": output_devices
            }
        except Exception as e:
            logger.error(f"Error querying audio devices: {e}")
            return {"input": [], "output": []} 