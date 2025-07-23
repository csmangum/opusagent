"""
Audio Panel component for the Interactive TUI Validator.

This panel provides audio controls, visualization, and file management
for testing audio streams with the TelephonyRealtimeBridge.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, List

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Button, ProgressBar, Label
from textual.widget import Widget
from textual.timer import Timer

from tui.models.audio_manager import AudioManager, AudioConfig, AudioFormat
from tui.utils.audio_utils import AudioUtils
from tui.utils.helpers import format_bytes, format_duration

logger = logging.getLogger(__name__)

class AudioPanel(Widget):
    """Panel for audio controls and visualization."""
    
    CSS = """
    AudioPanel {
        background: $surface;
        border: solid $primary;
        height: auto;
        min-height: 12;
    }
    
    .audio-controls {
        layout: horizontal;
        height: 1;
        align: center middle;
    }
    
    .volume-controls {
        layout: horizontal;
        height: 1;
        align: center middle;
    }
    
    .audio-viz {
        background: $surface;
        color: $text;
        text-align: center;
        height: 4;
    }
    
    .audio-info {
        background: $surface;
        color: $text;
        text-align: center;
        height: 1;
    }
    
    .file-info {
        background: $surface;
        color: $text;
        height: 1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parent_app = None
        
        # Audio manager
        self.audio_manager: Optional[AudioManager] = None
        self._init_audio_manager()
        
        # State
        self.recording = False
        self.playing = False
        self.audio_file: Optional[str] = None
        self.audio_data: Optional[bytes] = None
        self.audio_chunks: List[bytes] = []
        self.current_chunk_index = 0
        self.file_sample_rate = 16000
        self.file_channels = 1
        
        # Volume control
        self.volume = 1.0
        self.muted = False
        
        # Visualization update timer
        self.viz_timer: Optional[Timer] = None
        
        # Audio streaming
        self.streaming_task: Optional[asyncio.Task] = None
        self.file_streaming_task: Optional[asyncio.Task] = None
        
        logger.info("AudioPanel initialized")
    
    def _init_audio_manager(self) -> None:
        """Initialize the audio manager."""
        try:
            config = AudioConfig(
                sample_rate=16000,
                channels=1,
                chunk_size=1024,
                format=AudioFormat.PCM16,
                latency=0.1
            )
            self.audio_manager = AudioManager(config)
            
            # Set up callbacks
            self.audio_manager.on_audio_chunk = self._on_audio_chunk
            self.audio_manager.on_level_update = self._on_level_update
            
            logger.info("AudioManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AudioManager: {e}")
            self.audio_manager = None
        
    def compose(self) -> ComposeResult:
        """Create the audio panel layout."""
        with Vertical():
            # Audio controls
            with Horizontal(classes="audio-controls"):
                yield Button("🎤 Start Stream", id="start-stream-btn", disabled=True)
                yield Button("⏹ Stop Stream", id="stop-stream-btn", disabled=True)
                yield Button("📁 Browse Audio", id="browse-audio-btn")
                yield Button("📤 Send Audio", id="send-audio-btn", disabled=True)
            
            # Volume controls
            with Horizontal(classes="volume-controls"):
                yield Label("🔊 Volume:")
                yield Button("➖", id="volume-down-btn", variant="default")
                yield Button("➕", id="volume-up-btn", variant="default")
                yield Button("🔇 Mute", id="mute-btn", variant="default")
            
            # Audio file info
            yield Static("No audio file selected", id="audio-file-info", classes="file-info")
            yield ProgressBar(total=100, show_eta=False, id="audio-progress")
            
            # Audio visualization
            yield Static(
                "🔊 Bot:  ▁▁▁▁▁▁▁▁▁▁▁▁▁ 🔊 Vol: ████████░░\n"
                "🎤 User: ▁▁▁▁▁▁▁▁▁▁▁▁▁ 🎤 Rec: ⚫\n"
                "Waveform:\n"
                "        ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁        ",
                id="audio-visualization",
                classes="audio-viz"
            )
            
            # Audio format info
            yield Static(
                "Format: PCM16 16kHz | Latency: -- | Status: Idle",
                id="audio-format-info",
                classes="audio-info"
            )
    
    async def on_mount(self) -> None:
        """Initialize visualization timer when mounted."""
        # Start visualization update timer
        self.viz_timer = self.set_interval(0.1, self._update_visualization)
        
        # Auto-start playback for live audio (bot responses)
        if self.audio_manager:
            playback_success = self.audio_manager.start_playback()
            if playback_success:
                self._update_format_info(status="Ready for Audio")
                logger.info("Audio playback system ready for bot responses")
            else:
                self._update_format_info(status="Audio System Error")
                logger.warning("Failed to initialize audio playback system")
    
    async def on_unmount(self) -> None:
        """Clean up when unmounting."""
        if self.viz_timer:
            self.viz_timer.stop()
        
        # Stop any active audio operations
        await self._cleanup_audio()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "start-stream-btn":
            asyncio.create_task(self._async_start_stream())
        elif event.button.id == "stop-stream-btn":
            asyncio.create_task(self._async_stop_stream())
        elif event.button.id == "browse-audio-btn":
            self._browse_audio_file()
        elif event.button.id == "send-audio-btn":
            asyncio.create_task(self._async_send_audio_file())
        elif event.button.id == "mute-btn":
            self._toggle_mute()
        elif event.button.id == "volume-up-btn":
            self._change_volume(0.1)
        elif event.button.id == "volume-down-btn":
            self._change_volume(-0.1)
    
    def _change_volume(self, delta: float) -> None:
        """Increase or decrease the volume by delta (clamped 0.0-1.0)."""
        new_volume = max(0.0, min(1.0, self.volume + delta))
        self._set_volume(new_volume)
    
    async def _async_start_stream(self) -> None:
        """Start audio streaming."""
        if not self.audio_manager:
            logger.error("AudioManager not available")
            return
        
        try:
            # Start recording and playback
            recording_success = self.audio_manager.start_recording()
            playback_success = self.audio_manager.start_playback()
            
            if recording_success and playback_success:
                self.recording = True
                self.playing = True
                
                # Start streaming task
                self.streaming_task = asyncio.create_task(self._streaming_loop())
                
                self._update_controls()
                self._update_format_info(status="Recording & Playing")
                
                if self.parent_app and hasattr(self.parent_app, "events_panel"):
                    self.parent_app.events_panel.add_event(
                        "audio_stream_started", status="success", 
                        details="Audio streaming started"
                    )
                
                logger.info("Audio streaming started")
            else:
                logger.error("Failed to start audio streaming")
                
        except Exception as e:
            logger.error(f"Error starting audio stream: {e}")
    
    async def _async_stop_stream(self) -> None:
        """Stop audio streaming."""
        if not self.audio_manager:
            return
        
        try:
            # Stop streaming task
            if self.streaming_task:
                self.streaming_task.cancel()
                try:
                    await self.streaming_task
                except asyncio.CancelledError:
                    pass
                self.streaming_task = None
            
            # Stop audio manager
            self.audio_manager.stop_recording()
            self.audio_manager.stop_playback()
            
            self.recording = False
            self.playing = False
            
            self._update_controls()
            self._update_format_info(status="Idle")
            
            if self.parent_app and hasattr(self.parent_app, "events_panel"):
                self.parent_app.events_panel.add_event(
                    "audio_stream_stopped", status="info", 
                    details="Audio streaming stopped"
                )
            
            logger.info("Audio streaming stopped")
            
        except Exception as e:
            logger.error(f"Error stopping audio stream: {e}")
    
    def _browse_audio_file(self) -> None:
        """Browse for audio file."""
        # For now, use a predefined test file
        # TODO: Implement actual file browser dialog
        
        # Try to find test audio files
        test_files = [
            "static/tell_me_about_your_bank.wav",
            "static/sample.wav", 
            "tell_me_about_your_bank.wav",
            "sample.wav"
        ]
        
        selected_file = None
        for test_file in test_files:
            if Path(test_file).exists():
                selected_file = test_file
                break
        
        if selected_file:
            success = self._load_audio_file(selected_file)
            if success:
                if self.parent_app:
                    self.parent_app.bell()
            else:
                logger.error(f"Failed to load audio file: {selected_file}")
        else:
            logger.warning("No test audio files found")
            # Simulate file selection for demo
            self.audio_file = "tell_me_about_your_bank.wav"
            self._update_file_info()
            if self.parent_app:
                self.parent_app.bell()
    
    def _load_audio_file(self, filepath: str) -> bool:
        """Load an audio file."""
        try:
            if not AudioUtils.validate_audio_format(filepath):
                logger.error(f"Unsupported audio format: {filepath}")
                return False
            
            # Load audio data
            audio_data, sample_rate, channels = AudioUtils.load_audio_file(filepath, target_sample_rate=16000)
            
            if not audio_data:
                logger.error(f"Failed to load audio data from: {filepath}")
                return False
            
            # Store audio information
            self.audio_file = filepath
            self.audio_data = audio_data
            self.file_sample_rate = sample_rate
            self.file_channels = channels
            
            # Chunk the audio for streaming (1 second chunks)
            chunk_duration_ms = 1000  # 1 second chunks
            self.audio_chunks = AudioUtils.chunk_audio_by_duration(
                audio_data, sample_rate, chunk_duration_ms, channels
            )
            self.current_chunk_index = 0
            
            # Update UI
            self._update_file_info()
            
            logger.info(f"Loaded audio file: {filepath} - {len(self.audio_chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Error loading audio file {filepath}: {e}")
            return False
    
    async def _async_send_audio_file(self) -> None:
        """Send selected audio file."""
        if not self.audio_chunks or not self.parent_app:
            logger.warning("No audio file loaded or parent app not available")
            return
        
        try:
            # Start file streaming task
            self.file_streaming_task = asyncio.create_task(self._file_streaming_loop())
            
            if self.parent_app and hasattr(self.parent_app, "events_panel"):
                self.parent_app.events_panel.add_event(
                    "audio_file_send_started", status="info", 
                    details=f"Sending audio file: {Path(self.audio_file or '').name}"
                )
            
        except Exception as e:
            logger.error(f"Error sending audio file: {e}")
    
    async def _streaming_loop(self) -> None:
        """Main streaming loop for real-time audio."""
        try:
            while self.recording and self.audio_manager and self.audio_manager.recording:
                # Get recorded audio chunk
                chunk = await self.audio_manager.get_recorded_chunk()
                if chunk:
                    # Send to TelephonyRealtimeBridge via parent app
                    if self.parent_app and hasattr(self.parent_app, "connection_panel"):
                        connection_panel = self.parent_app.connection_panel
                        if connection_panel and connection_panel.websocket_client.connected:
                            # Convert to base64 for transmission
                            chunk_b64 = AudioUtils.convert_to_base64(chunk)
                            
                            # Create userStream.chunk message
                            from tui.websocket.message_handler import SessionMessageBuilder
                            session_state = connection_panel.get_session_state()
                            if session_state.conversation_id:
                                message = SessionMessageBuilder.create_user_stream_chunk(
                                    session_state.conversation_id, chunk_b64
                                )
                                # Type: ignore to handle linter issue with async method
                                success = await connection_panel.websocket_client.send_message(message)  # type: ignore
                                if not success:
                                    logger.warning("Failed to send audio chunk")
                
                await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
                
        except asyncio.CancelledError:
            logger.info("Streaming loop cancelled")
        except Exception as e:
            logger.error(f"Error in streaming loop: {e}")
    
    async def _file_streaming_loop(self) -> None:
        """Stream audio file chunks."""
        try:
            total_chunks = len(self.audio_chunks)
            
            for i, chunk in enumerate(self.audio_chunks):
                # Update progress
                progress = int((i / total_chunks) * 100)
                self._update_progress(progress)
                
                # Send chunk
                if self.parent_app and hasattr(self.parent_app, "connection_panel"):
                    connection_panel = self.parent_app.connection_panel
                    if connection_panel and connection_panel.websocket_client.connected:
                        # Convert to base64 for transmission
                        chunk_b64 = AudioUtils.convert_to_base64(chunk)
                        
                        # Create userStream.chunk message
                        from tui.websocket.message_handler import SessionMessageBuilder
                        session_state = connection_panel.get_session_state()
                        if session_state.conversation_id:
                            message = SessionMessageBuilder.create_user_stream_chunk(
                                session_state.conversation_id, chunk_b64
                            )
                            # Type: ignore to handle linter issue with async method
                            success = await connection_panel.websocket_client.send_message(message)  # type: ignore
                            if not success:
                                logger.warning("Failed to send audio chunk")
                
                # Wait before sending next chunk (simulate real-time)
                await asyncio.sleep(1.0)  # 1 second per chunk
            
            # Complete
            self._update_progress(100)
            
            if self.parent_app and hasattr(self.parent_app, "events_panel"):
                self.parent_app.events_panel.add_event(
                    "audio_file_send_complete", status="success", 
                    details="Audio file transmission complete"
                )
            
        except asyncio.CancelledError:
            logger.info("File streaming cancelled")
        except Exception as e:
            logger.error(f"Error in file streaming: {e}")
    
    def _on_audio_chunk(self, audio_data: bytes) -> None:
        """Handle recorded audio chunk."""
        # This is called from the audio manager for each recorded chunk
        pass
    
    def _on_level_update(self, input_level: float, output_level: float) -> None:
        """Handle audio level updates."""
        # This could be used for more sophisticated level monitoring
        pass
    
    def _update_visualization(self) -> None:
        """Update audio visualization display."""
        if not self.audio_manager:
            return
        
        try:
            # Get current audio levels
            input_level, output_level = self.audio_manager.get_volume_level()
            
            # Create visualization bars
            input_bars = AudioUtils.visualize_audio_level(b'\x00' * int(input_level * 1000), max_bars=13)
            output_bars = AudioUtils.visualize_audio_level(b'\x00' * int(output_level * 1000), max_bars=13)
            
            # Volume indicator
            volume_bars = "█" * int(self.volume * 10) + "░" * (10 - int(self.volume * 10))
            
            # Recording indicator
            rec_indicator = "🔴" if self.recording else "⚫"
            
            # Status indicators
            if self.playing and self.recording:
                status = "Recording & Playing"
            elif self.recording:
                status = "Recording"
            elif self.playing:
                status = "Playing"
            else:
                status = "Idle"
            
            # Create visualization text
            viz_text = (
                f"🔊 Bot:  {output_bars} 🔊 Vol: {volume_bars}\n"
                f"🎤 User: {input_bars} 🎤 Rec: {rec_indicator}\n"
                f"Status: {status}\n"
                f"        ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁        "
            )
            
            # Update the visualization widget
            viz_widget = self.query_one("#audio-visualization", Static)
            viz_widget.update(viz_text)
            
        except Exception as e:
            logger.debug(f"Error updating visualization: {e}")
    
    def _update_controls(self) -> None:
        """Update button states based on current status."""
        start_btn = self.query_one("#start-stream-btn", Button)
        stop_btn = self.query_one("#stop-stream-btn", Button)
        send_btn = self.query_one("#send-audio-btn", Button)
        
        # Connection state
        connected = False
        if self.parent_app and hasattr(self.parent_app, "connection_panel"):
            connection_panel = self.parent_app.connection_panel
            connected = connection_panel and connection_panel.websocket_client.connected
        
        start_btn.disabled = not connected or self.recording
        stop_btn.disabled = not self.recording
        send_btn.disabled = not self.audio_file or self.recording or not connected
    
    def _update_file_info(self) -> None:
        """Update audio file information display."""
        file_info = self.query_one("#audio-file-info", Static)
        
        if self.audio_file and self.audio_data:
            file_path = Path(self.audio_file)
            file_size = format_bytes(len(self.audio_data))
            duration = AudioUtils.get_audio_duration(
                self.audio_data, self.file_sample_rate, self.file_channels
            )
            duration_str = format_duration(duration)
            
            file_info.update(
                f"File: {file_path.name} | Size: {file_size} | "
                f"Duration: {duration_str} | Rate: {self.file_sample_rate}Hz"
            )
        else:
            file_info.update("No audio file selected")
        
        self._update_controls()
    
    def _update_progress(self, percentage: int) -> None:
        """Update audio progress bar."""
        progress = self.query_one("#audio-progress", ProgressBar)
        progress.progress = percentage
    
    def _update_format_info(self, format_str: Optional[str] = None, latency: Optional[float] = None, status: Optional[str] = None) -> None:
        """Update audio format information."""
        format_info = self.query_one("#audio-format-info", Static)
        
        format_part = format_str or "PCM16 16kHz"
        latency_part = f"{latency:.0f}ms" if latency else "--"
        status_part = status or ("Recording" if self.recording else "Playing" if self.playing else "Idle")
        
        # Add statistics if audio manager is available
        stats_part = ""
        if self.audio_manager:
            stats = self.audio_manager.get_statistics()
            stats_part = f" | Chunks: {stats['chunks_recorded']}/{stats['chunks_played']}"
        
        format_info.update(f"Format: {format_part} | Latency: {latency_part} | Status: {status_part}{stats_part}")
    
    def _set_volume(self, volume: float) -> None:
        """Set playback volume."""
        self.volume = max(0.0, min(1.0, volume))
        if self.audio_manager:
            self.audio_manager.set_volume(self.volume)
        # Update mute button text
        mute_btn = self.query_one("#mute-btn", Button)
        if self.volume == 0.0:
            mute_btn.label = "🔇 Muted"
        else:
            mute_btn.label = "🔇 Mute"
        logger.debug(f"Volume set to {self.volume:.2f}")
    
    def _toggle_mute(self) -> None:
        """Toggle mute state."""
        self.muted = not self.muted
        
        if self.audio_manager:
            self.audio_manager.set_mute(self.muted)
        
        # Update button
        mute_btn = self.query_one("#mute-btn", Button)
        if self.muted:
            mute_btn.label = "🔊 Unmute"
            mute_btn.variant = "warning"
        else:
            mute_btn.label = "🔇 Mute"
            mute_btn.variant = "default"
        
        logger.debug(f"Mute toggled: {self.muted}")
    
    def set_connection_state(self, connected: bool) -> None:
        """Update controls based on connection state."""
        self._update_controls()
    
    async def handle_bot_audio_chunk(self, audio_data: bytes) -> None:
        """Handle incoming audio chunk from bot."""
        try:
            if self.audio_manager and self.audio_manager.playing:
                await self.audio_manager.play_audio_chunk(audio_data)
                
                # Update visualization to show we're receiving bot audio
                self._update_format_info(status="Playing Bot Audio")
                
                # Log audio reception
                logger.debug(f"Playing bot audio chunk: {len(audio_data)} bytes")
                
        except Exception as e:
            logger.error(f"Error playing bot audio chunk: {e}")
    
    async def _cleanup_audio(self) -> None:
        """Clean up audio resources."""
        try:
            # Cancel streaming tasks
            if self.streaming_task:
                self.streaming_task.cancel()
                try:
                    await self.streaming_task
                except asyncio.CancelledError:
                    pass
            
            if self.file_streaming_task:
                self.file_streaming_task.cancel()
                try:
                    await self.file_streaming_task
                except asyncio.CancelledError:
                    pass
            
            # Stop audio manager
            if self.audio_manager:
                self.audio_manager.cleanup()
            
        except Exception as e:
            logger.error(f"Error cleaning up audio: {e}") 