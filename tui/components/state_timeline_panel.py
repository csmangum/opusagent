"""
State Timeline Panel component for the Call Review Interface.

This panel displays state machine transitions as a visual timeline,
showing how the conversation flow evolved over time with clickable states.
"""

from typing import Optional, List, Callable
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Button
from textual.widget import Widget
from textual.events import Click

from ..models.review_session import ReviewSession, StateTransition


class StateTimelinePanel(Widget):
    """Panel for displaying state machine transitions as a timeline."""
    
    CSS = """
    StateTimelinePanel {
        background: $surface;
        border: solid $primary;
        height: auto;
        min-height: 8;
    }
    
    .timeline-header {
        background: $primary;
        color: $primary-background;
        text-align: center;
        height: 1;
    }
    
    .timeline-content {
        background: $surface;
        color: $text;
        height: 1fr;
        layout: vertical;
        padding: 1;
    }
    
    .timeline-bar {
        height: 3;
        layout: horizontal;
        margin: 1 0;
    }
    
    .state-block {
        height: 2;
        text-align: center;
        border: round;
        margin: 0 1;
        min-width: 8;
    }
    
    .state-current {
        background: $accent;
        color: $primary-background;
    }
    
    .state-idle {
        background: $surface-lighten-1;
        color: $text-muted;
    }
    
    .state-active {
        background: $success;
        color: $primary-background;
    }
    
    .state-processing {
        background: $warning;
        color: $primary-background;
    }
    
    .state-error {
        background: $error;
        color: $primary-background;
    }
    
    .timeline-controls {
        height: 2;
        layout: horizontal;
        align: center middle;
    }
    
    .timeline-info {
        height: 1;
        background: $surface;
        color: $text-muted;
        text-align: center;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.review_session: Optional[ReviewSession] = None
        self.on_seek_callback: Optional[Callable[[float], None]] = None
        
        # Timeline state
        self.current_timestamp: float = 0.0
        self.timeline_duration: float = 0.0
        
        # Widget references
        self.timeline_content = None
        self.timeline_info_widget = None
        
    def compose(self) -> ComposeResult:
        """Create the state timeline panel layout."""
        with Vertical():
            yield Static("🔄 State Timeline", classes="timeline-header")
            
            self.timeline_content = Vertical(classes="timeline-content")
            yield self.timeline_content
            
            # Controls
            with Horizontal(classes="timeline-controls"):
                yield Button("⏪ Previous", id="prev-state-btn", variant="default")
                yield Button("⏩ Next", id="next-state-btn", variant="default")
                yield Button("🔄 Refresh", id="refresh-timeline-btn", variant="default")
            
            # Info display
            self.timeline_info_widget = Static("No state data available", classes="timeline-info")
            yield self.timeline_info_widget
    
    def set_review_session(self, review_session: ReviewSession) -> None:
        """Set the review session and update timeline."""
        self.review_session = review_session
        if review_session:
            self.timeline_duration = review_session.get_duration()
            
            # Subscribe to seek events
            review_session.add_seek_listener(self._on_seek_event)
        
        self.update_timeline_display()
    
    def set_seek_callback(self, callback: Callable[[float], None]) -> None:
        """Set callback for when user clicks on timeline."""
        self.on_seek_callback = callback
    
    def _on_seek_event(self, timestamp: float) -> None:
        """Handle seek events from the review session."""
        self.current_timestamp = timestamp
        self.update_current_state_highlight()
    
    def update_timeline_display(self) -> None:
        """Update the timeline display with state transitions."""
        if not self.timeline_content:
            return
        
        # Clear existing content
        self.timeline_content.remove_children()
        
        if not self.review_session or not self.review_session.state_transitions:
            self._show_no_states()
            return
        
        transitions = self.review_session.state_transitions
        
        # Create timeline visualization
        with self.timeline_content:
            self._create_timeline_bars(transitions)
        
        # Update info
        self._update_info_display()
    
    def _create_timeline_bars(self, transitions: List[StateTransition]) -> None:
        """Create visual timeline bars for state transitions."""
        if not transitions:
            return
        
        # Group transitions by rows to fit multiple states
        max_states_per_row = 6
        current_row = []
        
        for i, transition in enumerate(transitions):
            current_row.append(transition)
            
            # Start new row when full or at end
            if len(current_row) >= max_states_per_row or i == len(transitions) - 1:
                self._create_timeline_row(current_row)
                current_row = []
    
    def _create_timeline_row(self, transitions: List[StateTransition]) -> None:
        """Create a single row of state timeline."""
        with Horizontal(classes="timeline-bar"):
            for transition in transitions:
                state_class = self._get_state_css_class(transition.to_state)
                
                # Create clickable state button
                state_button = Button(
                    self._format_state_display(transition),
                    id=f"state-{transition.timestamp}",
                    classes=f"state-block {state_class}"
                )
                yield state_button
    
    def _format_state_display(self, transition: StateTransition) -> str:
        """Format state display text."""
        time_str = transition.get_time_str()
        state_name = transition.to_state.replace("_", " ").title()
        
        # Truncate long state names
        if len(state_name) > 8:
            state_name = state_name[:8] + "..."
        
        return f"{state_name}\n{time_str}"
    
    def _get_state_css_class(self, state: str) -> str:
        """Get CSS class for state type."""
        state_lower = state.lower()
        
        if state_lower in ["idle", "ended", "closed"]:
            return "state-idle"
        elif state_lower in ["error", "failed", "cancelled"]:
            return "state-error"
        elif state_lower in ["processing", "thinking", "waiting"]:
            return "state-processing"
        elif state_lower in ["active", "talking", "listening", "greeting"]:
            return "state-active"
        else:
            return "state-active"
    
    def _show_no_states(self) -> None:
        """Show message when no state data is available."""
        with self.timeline_content:
            yield Static("No state transition data available", classes="timeline-info")
    
    def _update_info_display(self) -> None:
        """Update the timeline info display."""
        if not self.timeline_info_widget:
            return
        
        if not self.review_session or not self.review_session.state_transitions:
            self.timeline_info_widget.update("No state data available")
            return
        
        transitions = self.review_session.state_transitions
        current_state = self._get_current_state()
        
        info_text = f"States: {len(transitions)} | Current: {current_state} | Duration: {self.timeline_duration:.1f}s"
        self.timeline_info_widget.update(info_text)
    
    def _get_current_state(self) -> str:
        """Get the current state based on timestamp."""
        if not self.review_session or not self.review_session.state_transitions:
            return "Unknown"
        
        # Find the state at current timestamp
        current_state = "Unknown"
        
        for transition in self.review_session.state_transitions:
            if transition.timestamp <= self.current_timestamp:
                current_state = transition.to_state
            else:
                break
        
        return current_state.replace("_", " ").title()
    
    def update_current_state_highlight(self) -> None:
        """Update highlighting for current state."""
        # This could be enhanced to visually highlight the current state
        self._update_info_display()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id and button_id.startswith("state-"):
            # Extract timestamp from button ID
            try:
                timestamp_str = button_id.replace("state-", "")
                timestamp = float(timestamp_str)
                
                # Trigger seek callback
                if self.on_seek_callback:
                    self.on_seek_callback(timestamp)
                    
            except ValueError:
                pass
        
        elif button_id == "prev-state-btn":
            self._seek_to_previous_state()
        elif button_id == "next-state-btn":
            self._seek_to_next_state()
        elif button_id == "refresh-timeline-btn":
            self.update_timeline_display()
    
    def _seek_to_previous_state(self) -> None:
        """Seek to the previous state transition."""
        if not self.review_session or not self.review_session.state_transitions:
            return
        
        # Find previous transition
        prev_timestamp = 0.0
        
        for transition in self.review_session.state_transitions:
            if transition.timestamp >= self.current_timestamp:
                break
            prev_timestamp = transition.timestamp
        
        if self.on_seek_callback:
            self.on_seek_callback(prev_timestamp)
    
    def _seek_to_next_state(self) -> None:
        """Seek to the next state transition."""
        if not self.review_session or not self.review_session.state_transitions:
            return
        
        # Find next transition
        for transition in self.review_session.state_transitions:
            if transition.timestamp > self.current_timestamp:
                if self.on_seek_callback:
                    self.on_seek_callback(transition.timestamp)
                break
    
    def clear_timeline(self) -> None:
        """Clear the timeline display."""
        self.review_session = None
        self.current_timestamp = 0.0
        self.timeline_duration = 0.0
        
        if self.timeline_content:
            self.timeline_content.remove_children()
        
        if self.timeline_info_widget:
            self.timeline_info_widget.update("No state data available")