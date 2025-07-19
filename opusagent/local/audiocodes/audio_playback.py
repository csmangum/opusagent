"""
Audio playback module for the AudioCodes mock client.

This module provides real-time audio playback functionality for playing
incoming audio chunks from the bridge server through local speakers.
It integrates with the existing AudioCodes client architecture and
provides low-latency audio playback with proper format handling.

Features:
- Real-time audio playback from base64-encoded chunks
- Automatic audio format conversion and resampling
- Thread-safe audio queuing and playback
- Volume control and mute functionality
- Audio level monitoring and visualization
- Integration with existing AudioCodes client components

Audio Processing Pipeline:
1. Receive base64-encoded audio chunks from bridge
2. Decode chunks to raw audio data
3. Convert to target format (16kHz, 16-bit PCM)
4. Queue for playback in separate thread
5. Play through system audio output
6. Monitor audio levels for visualization

Dependencies:
- sounddevice: For low-latency audio playback
- numpy: For audio data processing
- scipy: For audio resampling (if needed)
"""

import asyncio
import base64
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional
import queue

try:
    import sounddevice as sd
    import numpy as np
    from scipy import signal
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    sd = None
    np = None
    signal = None


class AudioPlaybackConfig:
    """Configuration for audio playback settings."""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        latency: float = 0.1,
        volume: float = 1.0,
        enable_playback: bool = True
    ):
        """
        Initialize audio playback configuration.
        
        Args:
            sample_rate (int): Target sample rate (default: 16000)
            channels (int): Number of audio channels (default: 1 for mono)
            chunk_size (int): Audio chunk size in samples (default: 1024)
            latency (float): Audio latency in seconds (default: 0.1)
            volume (float): Playback volume 0.0 to 1.0 (default: 1.0)
            enable_playback (bool): Whether to enable audio playback (default: True)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.latency = latency
        self.volume = max(0.0, min(1.0, volume))
        self.enable_playback = enable_playback


class AudioPlayback:
    """
    Audio playback manager for the AudioCodes mock client.
    
    This class handles real-time audio playback of incoming audio chunks
    from the bridge server. It provides thread-safe audio queuing,
    format conversion, and low-latency playback through system speakers.
    
    The AudioPlayback manager integrates with the existing AudioCodes
    client architecture and can be easily enabled/disabled as needed.
    
    Usage:
        # Create playback manager
        playback = AudioPlayback(config=AudioPlaybackConfig())
        
        # Start playback
        playback.start()
        
        # Queue audio chunks for playback
        await playback.queue_audio_chunk(base64_audio_chunk)
        
        # Stop playback
        playback.stop()
    """
    
    def __init__(
        self,
        config: Optional[AudioPlaybackConfig] = None,
        logger: Optional[logging.Logger] = None,
        on_audio_level: Optional[Callable[[float], None]] = None
    ):
        """
        Initialize the audio playback manager.
        
        Args:
            config (Optional[AudioPlaybackConfig]): Audio playback configuration
            logger (Optional[logging.Logger]): Logger instance for debugging
            on_audio_level (Optional[Callable[[float], None]]): Callback for audio level updates
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or AudioPlaybackConfig()
        self.on_audio_level = on_audio_level
        
        # Check if audio dependencies are available
        if not AUDIO_AVAILABLE:
            self.logger.warning("[AUDIO PLAYBACK] Audio dependencies not available. Install sounddevice, numpy, and scipy.")
            self.config.enable_playback = False
        
        # Playback state
        self.playing = False
        self.muted = False
        self.volume = self.config.volume
        
        # Audio streams and buffers
        self.output_stream: Optional[Any] = None  # sd.OutputStream when available
        self.playback_queue = queue.Queue(maxsize=50)  # Buffer for audio chunks
        
        # Threading
        self.playback_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Audio analysis
        self.current_audio_level = 0.0
        self._level_decay = 0.95
        
        # Statistics
        self.chunks_played = 0
        self.bytes_played = 0
        self.playback_errors = 0
        
        self.logger.info(f"[AUDIO PLAYBACK] Initialized with config: {self.config}")
    
    def start(self) -> bool:
        """
        Start audio playback system.
        
        Returns:
            bool: True if playback started successfully, False otherwise
        """
        if not self.config.enable_playback:
            self.logger.warning("[AUDIO PLAYBACK] Playback disabled in config")
            return False
        
        if self.playing:
            self.logger.warning("[AUDIO PLAYBACK] Playback already active")
            return True
        
        if not AUDIO_AVAILABLE:
            self.logger.error("[AUDIO PLAYBACK] Audio dependencies not available")
            return False
        
        try:
            # Clear any existing data
            while not self.playback_queue.empty():
                try:
                    self.playback_queue.get_nowait()
                except queue.Empty:
                    break
            
            self.playing = True
            self._stop_event.clear()
            
            # Start playback thread
            self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self.playback_thread.start()
            
            self.logger.info("[AUDIO PLAYBACK] Audio playback started")
            return True
            
        except Exception as e:
            self.logger.error(f"[AUDIO PLAYBACK] Failed to start playback: {e}")
            self.playing = False
            return False
    
    def stop(self) -> None:
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
            try:
                self.output_stream.stop()
                self.output_stream.close()
            except Exception as e:
                self.logger.error(f"[AUDIO PLAYBACK] Error closing output stream: {e}")
            finally:
                self.output_stream = None
        
        self.logger.info("[AUDIO PLAYBACK] Audio playback stopped")
    
    async def queue_audio_chunk(self, audio_chunk: str) -> bool:
        """
        Queue a base64-encoded audio chunk for playback.
        
        Args:
            audio_chunk (str): Base64-encoded audio chunk
            
        Returns:
            bool: True if chunk was queued successfully, False otherwise
        """
        if not self.playing:
            self.logger.warning("[AUDIO PLAYBACK] Cannot queue audio: playback not active")
            return False
        
        try:
            # Decode base64 audio chunk
            audio_data = base64.b64decode(audio_chunk)
            
            # Add to playback queue (non-blocking)
            try:
                self.playback_queue.put_nowait(audio_data)
                self.chunks_played += 1
                self.bytes_played += len(audio_data)
                return True
            except queue.Full:
                self.logger.warning("[AUDIO PLAYBACK] Playback queue full, dropping audio chunk")
                return False
                
        except Exception as e:
            self.logger.error(f"[AUDIO PLAYBACK] Error queuing audio chunk: {e}")
            self.playback_errors += 1
            return False
    
    def set_volume(self, volume: float) -> None:
        """
        Set playback volume.
        
        Args:
            volume (float): Volume level from 0.0 to 1.0
        """
        self.volume = max(0.0, min(1.0, volume))
        self.logger.debug(f"[AUDIO PLAYBACK] Volume set to {self.volume}")
    
    def mute(self) -> None:
        """Mute audio playback."""
        self.muted = True
        self.logger.debug("[AUDIO PLAYBACK] Audio muted")
    
    def unmute(self) -> None:
        """Unmute audio playback."""
        self.muted = False
        self.logger.debug("[AUDIO PLAYBACK] Audio unmuted")
    
    def get_audio_level(self) -> float:
        """
        Get current audio level for visualization.
        
        Returns:
            float: Current audio level (0.0 to 1.0)
        """
        return self.current_audio_level
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get playback statistics.
        
        Returns:
            Dict[str, Any]: Playback statistics
        """
        return {
            "playing": self.playing,
            "muted": self.muted,
            "volume": self.volume,
            "chunks_played": self.chunks_played,
            "bytes_played": self.bytes_played,
            "playback_errors": self.playback_errors,
            "queue_size": self.playback_queue.qsize(),
            "audio_level": self.current_audio_level
        }
    
    def _playback_loop(self) -> None:
        """Main playback loop running in separate thread."""
        if not AUDIO_AVAILABLE or sd is None or np is None:
            self.logger.error("[AUDIO PLAYBACK] Audio dependencies not available")
            return
            
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
            self.logger.error(f"[AUDIO PLAYBACK] Error in playback loop: {e}")
            self.playback_errors += 1
        finally:
            if self.output_stream:
                try:
                    self.output_stream.stop()
                    self.output_stream.close()
                except Exception as e:
                    self.logger.error(f"[AUDIO PLAYBACK] Error closing stream: {e}")
    
    def _playback_callback(self, outdata: Any, frames: int, time, status) -> None:
        """Audio playback callback function."""
        if not AUDIO_AVAILABLE or np is None:
            return
            
        try:
            if status:
                self.logger.warning(f"[AUDIO PLAYBACK] Playback status: {status}")
            
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
                    self.current_audio_level = max(level, self.current_audio_level * self._level_decay)
                    
                    # Call audio level callback if provided
                    if self.on_audio_level:
                        try:
                            self.on_audio_level(self.current_audio_level)
                        except Exception as e:
                            self.logger.error(f"[AUDIO PLAYBACK] Error in audio level callback: {e}")
                
            except queue.Empty:
                # No audio data available, output silence
                pass
                
        except Exception as e:
            self.logger.error(f"[AUDIO PLAYBACK] Error in playback callback: {e}")
            self.playback_errors += 1
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop()
        
        # Clear queue
        while not self.playback_queue.empty():
            try:
                self.playback_queue.get_nowait()
            except queue.Empty:
                break
        
        self.logger.info("[AUDIO PLAYBACK] Cleanup completed")


class AudioPlaybackManager:
    """
    High-level audio playback manager for AudioCodes client integration.
    
    This class provides a simplified interface for integrating audio playback
    with the AudioCodes mock client. It handles the connection between
    incoming audio chunks and the playback system.
    
    Integration:
    - Connects to MessageHandler for incoming playStream.chunk events
    - Manages audio playback lifecycle
    - Provides status and control methods
    - Handles audio format compatibility
    """
    
    def __init__(
        self,
        config: Optional[AudioPlaybackConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the audio playback manager.
        
        Args:
            config (Optional[AudioPlaybackConfig]): Audio playback configuration
            logger (Optional[logging.Logger]): Logger instance for debugging
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or AudioPlaybackConfig()
        
        # Create playback instance
        self.playback = AudioPlayback(config=self.config, logger=self.logger)
        
        # Integration state
        self.enabled = self.config.enable_playback
        self.connected = False
        
        self.logger.info(f"[AUDIO PLAYBACK MANAGER] Initialized with enabled={self.enabled}")
    
    def connect_to_message_handler(self, message_handler) -> None:
        """
        Connect to MessageHandler for automatic audio playback.
        
        Args:
            message_handler: MessageHandler instance to connect to
        """
        if not self.enabled:
            self.logger.warning("[AUDIO PLAYBACK MANAGER] Playback disabled, not connecting")
            return
        
        try:
            # Register handler for playStream.chunk events
            message_handler.register_event_handler(
                "playStream.chunk",
                self._handle_play_stream_chunk
            )
            
            self.connected = True
            self.logger.info("[AUDIO PLAYBACK MANAGER] Connected to MessageHandler")
            
        except Exception as e:
            self.logger.error(f"[AUDIO PLAYBACK MANAGER] Error connecting to MessageHandler: {e}")
    
    def start(self) -> bool:
        """
        Start audio playback system.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if not self.enabled:
            self.logger.warning("[AUDIO PLAYBACK MANAGER] Playback disabled")
            return False
        
        success = self.playback.start()
        if success:
            self.logger.info("[AUDIO PLAYBACK MANAGER] Audio playback started")
        else:
            self.logger.error("[AUDIO PLAYBACK MANAGER] Failed to start audio playback")
        
        return success
    
    def stop(self) -> None:
        """Stop audio playback system."""
        self.playback.stop()
        self.logger.info("[AUDIO PLAYBACK MANAGER] Audio playback stopped")
    
    def _handle_play_stream_chunk(self, data: Dict[str, Any]) -> None:
        """
        Handle playStream.chunk events from MessageHandler.
        
        Args:
            data (Dict[str, Any]): Play stream chunk event data
        """
        if not self.enabled or not self.connected:
            return
        
        audio_chunk = data.get("audioChunk")
        if audio_chunk:
            # Queue audio chunk for playback
            asyncio.create_task(self.playback.queue_audio_chunk(audio_chunk))
    
    def set_volume(self, volume: float) -> None:
        """
        Set playback volume.
        
        Args:
            volume (float): Volume level from 0.0 to 1.0
        """
        self.playback.set_volume(volume)
    
    def mute(self) -> None:
        """Mute audio playback."""
        self.playback.mute()
    
    def unmute(self) -> None:
        """Unmute audio playback."""
        self.playback.unmute()
    
    def get_audio_level(self) -> float:
        """
        Get current audio level.
        
        Returns:
            float: Current audio level (0.0 to 1.0)
        """
        return self.playback.get_audio_level()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get playback status information.
        
        Returns:
            Dict[str, Any]: Playback status
        """
        status = self.playback.get_statistics()
        status.update({
            "enabled": self.enabled,
            "connected": self.connected,
            "manager_active": self.enabled and self.connected
        })
        return status
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.playback.cleanup()
        self.connected = False
        self.logger.info("[AUDIO PLAYBACK MANAGER] Cleanup completed") 