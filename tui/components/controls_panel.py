"""
Controls Panel component for the Interactive TUI Validator.

This panel provides call flow control buttons for managing sessions,
audio streams, and call operations.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, Button, Input
from textual.widget import Widget


class ControlsPanel(Widget):
    """Panel for call flow control buttons and actions."""
    
    CSS = """
    ControlsPanel {
        background: $surface;
        border: solid $primary;
        height: auto;
        min-height: 3;
    }
    
    .controls-row {
        layout: horizontal;
        height: 1;
        align: center middle;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parent_app = None
        self.call_active = False
        self.stream_active = False
        
    def compose(self) -> ComposeResult:
        """Create the controls panel layout."""
        with Horizontal(classes="controls-row"):
            yield Button("Start Call", id="start-call-btn", variant="success", disabled=True)
            yield Button("End Call", id="end-call-btn", variant="error", disabled=True)
            yield Button("Hangup", id="hangup-btn", variant="error", disabled=True)
            yield Input(placeholder="DTMF", id="dtmf-input", max_length=1)
            yield Button("Send", id="send-dtmf-btn", disabled=True)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "start-call-btn":
            self.start_call()
        elif event.button.id == "end-call-btn":
            self.end_call()
        elif event.button.id == "hangup-btn":
            self.hangup()
        elif event.button.id == "send-dtmf-btn":
            self.send_dtmf()
    
    def start_call(self) -> None:
        """Start a new call session."""
        # TODO: Implement call start logic
        self.call_active = True
        self.update_button_states()
        if self.parent_app:
            self.parent_app.bell()
    
    def end_call(self) -> None:
        """End the current call session."""
        # TODO: Implement call end logic  
        self.call_active = False
        self.update_button_states()
        
    def hangup(self) -> None:
        """Hangup the current call."""
        # TODO: Implement hangup logic
        self.call_active = False
        self.update_button_states()
    
    def send_dtmf(self) -> None:
        """Send DTMF tone."""
        # TODO: Implement DTMF sending
        dtmf_input = self.query_one("#dtmf-input", Input)
        dtmf_input.value = ""
    
    def update_button_states(self) -> None:
        """Update button enabled/disabled states based on call status."""
        start_btn = self.query_one("#start-call-btn", Button)
        end_btn = self.query_one("#end-call-btn", Button)
        hangup_btn = self.query_one("#hangup-btn", Button)
        dtmf_btn = self.query_one("#send-dtmf-btn", Button)
        
        if self.call_active:
            start_btn.disabled = True
            end_btn.disabled = False
            hangup_btn.disabled = False
            dtmf_btn.disabled = False
        else:
            start_btn.disabled = False  # Will be enabled when connected
            end_btn.disabled = True
            hangup_btn.disabled = True
            dtmf_btn.disabled = True
    
    def set_connection_state(self, connected: bool) -> None:
        """Update controls based on connection state."""
        start_btn = self.query_one("#start-call-btn", Button)
        if connected and not self.call_active:
            start_btn.disabled = False
        else:
            start_btn.disabled = True 