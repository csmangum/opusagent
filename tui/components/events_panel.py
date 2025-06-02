"""
Events Panel component for the Interactive TUI Validator.

This panel displays session events, status updates, and real-time
event monitoring for TelephonyRealtimeBridge interactions.
"""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, RichLog
from textual.widget import Widget


class EventsPanel(Widget):
    """Panel for displaying session events and status updates."""
    
    CSS = """
    EventsPanel {
        background: $surface;
        border: solid $primary;
        height: 40%;
    }
    
    .events-header {
        background: $primary;
        color: $primary-background;
        text-align: center;
        height: 1;
    }
    
    .events-log {
        background: $surface;
        color: $text;
        height: 1fr;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parent_app = None
        self.events_log = None
        self.event_count = 0
        
    def compose(self) -> ComposeResult:
        """Create the events panel layout."""
        with Vertical():
            yield Static("📋 Session Events", classes="events-header")
            
            self.events_log = RichLog(
                highlight=True,
                markup=True,
                id="events-log",
                classes="events-log"
            )
            yield self.events_log
    
    def add_event(self, event_type: str, status: str = "info", details: str = None) -> None:
        """Add an event to the events log."""
        if not self.events_log:
            return
        
        self.event_count += 1
        
        # Get appropriate icon and color
        icon = self._get_event_icon(event_type)
        color = self._get_status_color(status)
        
        # Format event message
        timestamp = self._get_timestamp()
        message = f"[{color}]{icon} {event_type}[/{color}]"
        
        if details:
            message += f" - {details}"
        
        # Add to log
        self.events_log.write(f"[dim]{timestamp}[/dim] {message}")
        
        # Keep log size manageable
        if self.event_count > 200:
            self.events_log.clear()
            self.event_count = 0
    
    def _get_event_icon(self, event_type: str) -> str:
        """Get icon for event type."""
        icons = {
            "session.initiate": "🚀",
            "session.accepted": "✅",
            "session.end": "🛑",
            "userStream.start": "🎤",
            "userStream.started": "▶️",
            "userStream.stopped": "⏸️",
            "playStream.start": "🔊",
            "playStream.stop": "🔇",
            "connected": "🔗",
            "disconnected": "💔",
            "error": "❌",
            "warning": "⚠️",
        }
        return icons.get(event_type, "📄")
    
    def _get_status_color(self, status: str) -> str:
        """Get color for status."""
        colors = {
            "success": "green",
            "error": "red", 
            "warning": "yellow",
            "info": "blue",
        }
        return colors.get(status, "white")
    
    def _get_timestamp(self) -> str:
        """Get formatted timestamp."""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
    
    def clear_events(self) -> None:
        """Clear all events from the log."""
        if self.events_log:
            self.events_log.clear()
            self.event_count = 0 