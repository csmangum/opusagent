"""
Audio Panel component for the Interactive TUI Validator.

This panel provides audio controls, visualization, and file management
for testing audio streams with the TelephonyRealtimeBridge.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Button, ProgressBar
from textual.widget import Widget


class AudioPanel(Widget):
    """Panel for audio controls and visualization."""
    
    CSS = """
    AudioPanel {
        background: $surface;
        border: solid $primary;
        height: auto;
        min-height: 8;
    }
    
    .audio-controls {
        layout: horizontal;
        height: 1;
        align: center middle;
    }
    
    .audio-viz {
        background: $surface;
        color: $text;
        text-align: center;
        height: 3;
    }
    
    .audio-info {
        background: $surface;
        color: $text;
        text-align: center;
        height: 1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parent_app = None
        self.recording = False
        self.playing = False
        self.audio_file = None
        
    def compose(self) -> ComposeResult:
        """Create the audio panel layout."""
        with Vertical():
            # Audio controls
            with Horizontal(classes="audio-controls"):
                yield Button("🎤 Start Stream", id="start-stream-btn", disabled=True)
                yield Button("⏹ Stop Stream", id="stop-stream-btn", disabled=True)
                yield Button("📁 Browse Audio", id="browse-audio-btn")
                yield Button("📤 Send Audio", id="send-audio-btn", disabled=True)
            
            # Audio file progress
            yield Static("No audio file selected", id="audio-file-info", classes="audio-info")
            yield ProgressBar(total=100, show_eta=False, id="audio-progress")
            
            # Audio visualization placeholder
            yield Static(
                "🔊 Bot:  ▁▁▁▁▁▁▁▁▁▁▁▁▁ 🔊 Vol: ████████░░\n"
                "🎤 User: ▁▁▁▁▁▁▁▁▁▁▁▁▁ 🎤 Rec: ⚫",
                id="audio-visualization",
                classes="audio-viz"
            )
            
            # Audio format info
            yield Static(
                "Format: PCM16 16kHz | Latency: -- | Status: Idle",
                id="audio-format-info",
                classes="audio-info"
            )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "start-stream-btn":
            self.start_stream()
        elif event.button.id == "stop-stream-btn":
            self.stop_stream()
        elif event.button.id == "browse-audio-btn":
            self.browse_audio_file()
        elif event.button.id == "send-audio-btn":
            self.send_audio_file()
    
    def start_stream(self) -> None:
        """Start audio streaming."""
        # TODO: Implement audio streaming
        self.recording = True
        self.update_controls()
        self.update_visualization("recording")
    
    def stop_stream(self) -> None:
        """Stop audio streaming."""
        # TODO: Implement stop streaming
        self.recording = False
        self.update_controls()
        self.update_visualization("idle")
    
    def browse_audio_file(self) -> None:
        """Browse for audio file."""
        # TODO: Implement file browser
        # Placeholder - simulate file selection
        self.audio_file = "tell_me_about_your_bank.wav"
        self.update_file_info()
        if self.parent_app:
            self.parent_app.bell()
    
    def send_audio_file(self) -> None:
        """Send selected audio file."""
        # TODO: Implement file sending
        if self.audio_file:
            self.update_progress(0)
            # Simulate progress
            # TODO: Real progress tracking
    
    def update_controls(self) -> None:
        """Update button states based on current status."""
        start_btn = self.query_one("#start-stream-btn", Button)
        stop_btn = self.query_one("#stop-stream-btn", Button)
        send_btn = self.query_one("#send-audio-btn", Button)
        
        start_btn.disabled = self.recording
        stop_btn.disabled = not self.recording
        send_btn.disabled = not self.audio_file or self.recording
    
    def update_file_info(self) -> None:
        """Update audio file information display."""
        file_info = self.query_one("#audio-file-info", Static)
        if self.audio_file:
            file_info.update(f"File: {self.audio_file}")
        else:
            file_info.update("No audio file selected")
        self.update_controls()
    
    def update_progress(self, percentage: int) -> None:
        """Update audio progress bar."""
        progress = self.query_one("#audio-progress", ProgressBar)
        progress.progress = percentage
    
    def update_visualization(self, status: str) -> None:
        """Update audio visualization."""
        viz = self.query_one("#audio-visualization", Static)
        
        if status == "recording":
            viz.update(
                "🔊 Bot:  ▁▁▁▁▁▁▁▁▁▁▁▁▁ 🔊 Vol: ████████░░\n"
                "🎤 User: ▁▂▃▅▆▇█▇▆▅▃▂▁ 🎤 Rec: 🔴"
            )
        elif status == "playing":
            viz.update(
                "🔊 Bot:  ▁▂▃▅▆▇█▇▆▅▃▂▁ 🔊 Vol: ████████░░\n"
                "🎤 User: ▁▁▁▁▁▁▁▁▁▁▁▁▁ 🎤 Rec: ⚫"
            )
        else:  # idle
            viz.update(
                "🔊 Bot:  ▁▁▁▁▁▁▁▁▁▁▁▁▁ 🔊 Vol: ████████░░\n"
                "🎤 User: ▁▁▁▁▁▁▁▁▁▁▁▁▁ 🎤 Rec: ⚫"
            )
    
    def update_format_info(self, format_str: str = None, latency: float = None) -> None:
        """Update audio format information."""
        format_info = self.query_one("#audio-format-info", Static)
        
        format_part = format_str or "PCM16 16kHz"
        latency_part = f"{latency:.0f}ms" if latency else "--"
        status_part = "Recording" if self.recording else "Playing" if self.playing else "Idle"
        
        format_info.update(f"Format: {format_part} | Latency: {latency_part} | Status: {status_part}")
    
    def set_connection_state(self, connected: bool) -> None:
        """Update controls based on connection state."""
        start_btn = self.query_one("#start-stream-btn", Button)
        start_btn.disabled = not connected or self.recording 