"""
Search/Filter Box component for the Call Review Interface.

This component provides a global search and filter interface that can
filter content across all review panels simultaneously.
"""

from typing import Optional, Callable
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Label, Button
from textual.widget import Widget
from textual.events import Key

from ..models.review_session import ReviewSession


class SearchFilterBox(Widget):
    """Panel for global search and filtering."""
    
    CSS = """
    SearchFilterBox {
        background: $surface;
        border: solid $primary;
        height: auto;
        min-height: 3;
        max-height: 3;
    }
    
    .search-header {
        background: $primary;
        color: $primary-background;
        text-align: center;
        height: 1;
    }
    
    .search-content {
        background: $surface;
        color: $text;
        height: 2;
        layout: horizontal;
        align: center middle;
        padding: 0 2;
    }
    
    .search-input {
        width: 1fr;
        margin: 0 1;
    }
    
    .search-button {
        width: auto;
        margin: 0 1;
    }
    
    .search-stats {
        background: $surface;
        color: $text-muted;
        width: auto;
        margin: 0 1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.review_session: Optional[ReviewSession] = None
        self.on_filter_callback: Optional[Callable[[str], None]] = None
        
        # Widget references
        self.search_input = None
        self.search_stats = None
        
        # Filter state
        self.current_filter = ""
        self.last_results = {
            "transcript": 0,
            "logs": 0,
            "function_calls": 0
        }
    
    def compose(self) -> ComposeResult:
        """Create the search/filter box layout."""
        with Vertical():
            yield Label("🔍 Search & Filter", classes="search-header")
            
            with Horizontal(classes="search-content"):
                yield Label("Filter:")
                
                self.search_input = Input(
                    placeholder="Enter search term...",
                    id="search-input",
                    classes="search-input"
                )
                yield self.search_input
                
                yield Button("Clear", id="clear-btn", variant="default", classes="search-button")
                yield Button("Apply", id="apply-btn", variant="primary", classes="search-button")
                
                self.search_stats = Label("No results", classes="search-stats")
                yield self.search_stats
    
    def set_review_session(self, review_session: ReviewSession) -> None:
        """Set the review session and update filter capabilities."""
        self.review_session = review_session
        
        if review_session:
            # Subscribe to filter events
            review_session.add_filter_listener(self._on_filter_applied)
        
        self.update_stats_display()
    
    def set_filter_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for when filter is applied."""
        self.on_filter_callback = callback
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes for real-time filtering."""
        if event.input.id == "search-input":
            query = event.value.strip()
            
            # Apply filter in real-time if not too short
            if len(query) >= 2 or len(query) == 0:
                self._apply_filter(query)
    
    def on_key(self, event: Key) -> None:
        """Handle key presses."""
        if event.key == "enter":
            # Apply current filter on Enter
            if self.search_input:
                query = self.search_input.value.strip()
                self._apply_filter(query)
        elif event.key == "escape":
            # Clear filter on Escape
            self._clear_filter()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "apply-btn":
            if self.search_input:
                query = self.search_input.value.strip()
                self._apply_filter(query)
        elif event.button.id == "clear-btn":
            self._clear_filter()
    
    def _apply_filter(self, query: str) -> None:
        """Apply filter to the review session."""
        self.current_filter = query
        
        if self.review_session:
            self.review_session.apply_filter(query)
        
        # Trigger callback
        if self.on_filter_callback:
            self.on_filter_callback(query)
        
        self.update_stats_display()
    
    def _clear_filter(self) -> None:
        """Clear the current filter."""
        if self.search_input:
            self.search_input.value = ""
        
        self._apply_filter("")
    
    def _on_filter_applied(self, query: str) -> None:
        """Handle filter events from the review session."""
        # Update input if it doesn't match (external filter change)
        if self.search_input and self.search_input.value != query:
            self.search_input.value = query
        
        self.current_filter = query
        self.update_stats_display()
    
    def update_stats_display(self) -> None:
        """Update the statistics display."""
        if not self.search_stats:
            return
        
        if not self.review_session:
            self.search_stats.update("No data")
            return
        
        # Count filtered results
        transcript_count = len(self.review_session.filtered_transcript)
        logs_count = len(self.review_session.filtered_logs)
        function_calls_count = len(self.review_session.filtered_function_calls)
        
        self.last_results = {
            "transcript": transcript_count,
            "logs": logs_count,
            "function_calls": function_calls_count
        }
        
        # Format stats display
        if self.current_filter:
            total_results = transcript_count + logs_count + function_calls_count
            stats_text = f"Found: {total_results} ({transcript_count}T, {logs_count}L, {function_calls_count}F)"
        else:
            # Show total counts when no filter
            total_transcript = len(self.review_session.transcript)
            total_logs = len(self.review_session.logs)
            total_functions = len(self.review_session.function_calls)
            total = total_transcript + total_logs + total_functions
            stats_text = f"Total: {total} ({total_transcript}T, {total_logs}L, {total_functions}F)"
        
        self.search_stats.update(stats_text)
    
    def get_filter_query(self) -> str:
        """Get the current filter query."""
        return self.current_filter
    
    def set_filter_query(self, query: str) -> None:
        """Set the filter query programmatically."""
        if self.search_input:
            self.search_input.value = query
        self._apply_filter(query)
    
    def get_search_help_text(self) -> str:
        """Get help text for search functionality."""
        return """
Search Help:
- Enter text to filter across transcript, logs, and function calls
- Press Enter to apply filter
- Press Escape to clear filter
- Use Clear button to remove filter
- Search is case-insensitive
- Results show: (T)ranscript, (L)ogs, (F)unctions

Examples:
- "error" - Find all error messages
- "account" - Find account-related items
- "card" - Find card operations
- "user" - Find user interactions
"""
    
    def focus_search(self) -> None:
        """Focus the search input box."""
        if self.search_input:
            self.search_input.focus()
    
    def clear_all(self) -> None:
        """Clear all filter state."""
        self.current_filter = ""
        self.last_results = {"transcript": 0, "logs": 0, "function_calls": 0}
        
        if self.search_input:
            self.search_input.value = ""
        
        if self.search_stats:
            self.search_stats.update("No data")