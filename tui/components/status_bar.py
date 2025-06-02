"""
Status Bar component for the Interactive TUI Validator.

This component displays system status information at the bottom of the screen,
including connection status, audio status, latency, and statistics.
"""

from textual.app import ComposeResult
from textual.widgets import Static
from textual.widget import Widget


class StatusBar(Widget):
    """Status bar for displaying system information."""
    
    CSS = """
    StatusBar {
        background: $primary;
        color: $primary-background;
        height: 1;
        dock: bottom;
    }
    
    .status-text {
        text-align: center;
        height: 1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parent_app = None
        self.connection_status = "Disconnected"
        self.audio_status = "Idle"
        self.latency = None
        self.message_count = 0
        self.error_count = 0
        
    def compose(self) -> ComposeResult:
        """Create the status bar layout."""
        yield Static(
            "Status: Disconnected | Audio: Idle | Latency: -- | Messages: 0 | Errors: 0",
            id="status-text",
            classes="status-text"
        )
    
    def update_connection_status(self, status: str) -> None:
        """Update connection status."""
        self.connection_status = status
        self._update_display()
    
    def update_audio_status(self, status: str) -> None:
        """Update audio status."""
        self.audio_status = status
        self._update_display()
    
    def update_latency(self, latency_ms: float) -> None:
        """Update latency information."""
        self.latency = latency_ms
        self._update_display()
    
    def increment_message_count(self) -> None:
        """Increment message counter."""
        self.message_count += 1
        self._update_display()
    
    def increment_error_count(self) -> None:
        """Increment error counter."""
        self.error_count += 1
        self._update_display()
    
    def reset_counters(self) -> None:
        """Reset all counters."""
        self.message_count = 0
        self.error_count = 0
        self._update_display()
    
    def _update_display(self) -> None:
        """Update the status bar display."""
        status_widget = self.query_one("#status-text", Static)
        
        # Format latency
        latency_str = f"{self.latency:.0f}ms" if self.latency else "--"
        
        # Create status string
        status_text = (
            f"Status: {self.connection_status} | "
            f"Audio: {self.audio_status} | "
            f"Latency: {latency_str} | "
            f"Messages: {self.message_count} | "
            f"Errors: {self.error_count}"
        )
        
        status_widget.update(status_text)
    
    def set_custom_status(self, message: str) -> None:
        """Set a custom status message."""
        status_widget = self.query_one("#status-text", Static)
        status_widget.update(message) 