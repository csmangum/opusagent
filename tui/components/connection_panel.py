"""
Connection Panel component for the Interactive TUI Validator.

This panel manages WebSocket connection status and controls for connecting
to the TelephonyRealtimeBridge server.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Button, Input, Label
from textual.widget import Widget
from tui.websocket.client import WebSocketClient
import asyncio


class ConnectionPanel(Widget):
    """Panel for managing WebSocket connection and displaying status."""
    
    CSS = """
    ConnectionPanel {
        background: $surface;
        border: solid $primary;
        height: auto;
        min-height: 5;
    }
    
    .connection-status {
        background: $surface;
        color: $text;
        text-align: center;
        height: 1;
    }
    
    .connection-controls {
        layout: horizontal;
        height: 2;
        align: center middle;
    }
    
    .status-connected {
        color: $success;
    }
    
    .status-disconnected {
        color: $error;
    }
    
    .status-connecting {
        color: $warning;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parent_app = None
        self.connection_status = "Disconnected"
        self.session_id = None
        self.conversation_id = None
        self.websocket_client = WebSocketClient()
        
    def compose(self) -> ComposeResult:
        """Create the connection panel layout."""
        with Vertical():
            # Connection status display
            yield Static(
                "🔴 Disconnected from ws://localhost:8000/voice-bot",
                id="connection-status",
                classes="connection-status status-disconnected"
            )
            
            # Connection controls
            with Horizontal(classes="connection-controls"):
                yield Button("Connect", id="connect-btn", variant="success")
                yield Button("Disconnect", id="disconnect-btn", variant="error", disabled=True)
                yield Button("Reconnect", id="reconnect-btn", disabled=True)
            
            # Session info
            yield Static(
                "Session: Not established | Conv: N/A",
                id="session-info",
                classes="connection-status"
            )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "connect-btn":
            asyncio.create_task(self.async_initiate_connection())
        elif event.button.id == "disconnect-btn":
            asyncio.create_task(self.async_disconnect())
        elif event.button.id == "reconnect-btn":
            asyncio.create_task(self.async_reconnect())
    
    async def async_initiate_connection(self):
        """Initiate WebSocket connection."""
        self.update_status("Connecting...")
        url = self.parent_app.config.ws_url if self.parent_app else "ws://localhost:8000/voice-bot"
        success = await self.websocket_client.connect(url)
        if success:
            self.update_status("Connected")
            if self.parent_app and hasattr(self.parent_app, "events_panel"):
                self.parent_app.events_panel.add_event("connected", status="success", details=f"Connected to {url}")
        else:
            self.update_status("Disconnected")
            if self.parent_app and hasattr(self.parent_app, "events_panel"):
                self.parent_app.events_panel.add_event("error", status="error", details=f"Failed to connect to {url}")
    
    async def async_disconnect(self):
        """Disconnect from WebSocket."""
        await self.websocket_client.disconnect()
        self.update_status("Disconnected")
        if self.parent_app and hasattr(self.parent_app, "events_panel"):
            self.parent_app.events_panel.add_event("disconnected", status="info", details="Disconnected from server")
    
    async def async_reconnect(self):
        """Reconnect to WebSocket."""
        await self.async_disconnect()
        await self.async_initiate_connection()
    
    def update_status(self, status: str) -> None:
        """Update the connection status display."""
        self.connection_status = status
        
        # Update UI elements
        status_widget = self.query_one("#connection-status", Static)
        
        if status == "Connected":
            status_widget.update("🟢 Connected to ws://localhost:8000/voice-bot")
            status_widget.set_class(False, "status-disconnected", "status-connecting")
            status_widget.set_class(True, "status-connected")
            
            # Enable/disable buttons
            self.query_one("#connect-btn", Button).disabled = True
            self.query_one("#disconnect-btn", Button).disabled = False
            self.query_one("#reconnect-btn", Button).disabled = False
            
        elif status == "Connecting...":
            status_widget.update("🟡 Connecting to ws://localhost:8000/voice-bot")
            status_widget.set_class(False, "status-disconnected", "status-connected")
            status_widget.set_class(True, "status-connecting")
            
            # Disable all buttons during connection
            self.query_one("#connect-btn", Button).disabled = True
            self.query_one("#disconnect-btn", Button).disabled = True
            self.query_one("#reconnect-btn", Button).disabled = True
            
        else:  # Disconnected
            status_widget.update("🔴 Disconnected from ws://localhost:8000/voice-bot")
            status_widget.set_class(False, "status-connected", "status-connecting")
            status_widget.set_class(True, "status-disconnected")
            
            # Enable/disable buttons
            self.query_one("#connect-btn", Button).disabled = False
            self.query_one("#disconnect-btn", Button).disabled = True
            self.query_one("#reconnect-btn", Button).disabled = True
    
    def update_session_info(self, session_id: str = None, conversation_id: str = None) -> None:
        """Update session information display."""
        self.session_id = session_id
        self.conversation_id = conversation_id
        
        session_widget = self.query_one("#session-info", Static)
        
        session_str = session_id[:8] + "..." if session_id else "Not established"
        conv_str = conversation_id[:8] + "..." if conversation_id else "N/A"
        
        session_widget.update(f"Session: {session_str} | Conv: {conv_str}") 