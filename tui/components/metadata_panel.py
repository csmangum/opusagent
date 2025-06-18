"""
Metadata Panel component for the Call Review Interface.

This panel displays call metadata in a compact, readable format
including caller info, scenario, duration, result, and other key metrics.
"""

from typing import Optional
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Label
from textual.widget import Widget

from ..models.review_session import ReviewSession, CallMetadata


class MetadataPanel(Widget):
    """Panel for displaying call metadata."""
    
    CSS = """
    MetadataPanel {
        background: $surface;
        border: solid $primary;
        height: auto;
        min-height: 3;
        max-height: 3;
    }
    
    .metadata-header {
        background: $primary;
        color: $primary-background;
        text-align: center;
        height: 1;
    }
    
    .metadata-content {
        background: $surface;
        color: $text;
        height: 2;
        layout: horizontal;
    }
    
    .metadata-column {
        width: 1fr;
        layout: vertical;
        padding: 0 1;
    }
    
    .metadata-item {
        background: $surface;
        color: $text;
        height: 1;
    }
    
    .metadata-value {
        color: $accent;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.review_session: Optional[ReviewSession] = None
        
        # Widget references
        self.call_id_widget = None
        self.caller_widget = None
        self.scenario_widget = None
        self.duration_widget = None
        self.result_widget = None
        self.sentiment_widget = None
        self.agent_widget = None
        self.start_time_widget = None
        
    def compose(self) -> ComposeResult:
        """Create the metadata panel layout."""
        with Vertical():
            yield Static("📊 Call Metadata", classes="metadata-header")
            
            with Horizontal(classes="metadata-content"):
                # Left column
                with Vertical(classes="metadata-column"):
                    self.call_id_widget = Static("Call ID: --", classes="metadata-item")
                    yield self.call_id_widget
                    
                    self.caller_widget = Static("Caller: --", classes="metadata-item")
                    yield self.caller_widget
                
                # Center column
                with Vertical(classes="metadata-column"):
                    self.scenario_widget = Static("Scenario: --", classes="metadata-item")
                    yield self.scenario_widget
                    
                    self.duration_widget = Static("Duration: --", classes="metadata-item")
                    yield self.duration_widget
                
                # Right column
                with Vertical(classes="metadata-column"):
                    self.result_widget = Static("Result: --", classes="metadata-item")
                    yield self.result_widget
                    
                    self.sentiment_widget = Static("Sentiment: --", classes="metadata-item")
                    yield self.sentiment_widget
                
                # Far right column
                with Vertical(classes="metadata-column"):
                    self.agent_widget = Static("Agent: --", classes="metadata-item")
                    yield self.agent_widget
                    
                    self.start_time_widget = Static("Started: --", classes="metadata-item")
                    yield self.start_time_widget
    
    def set_review_session(self, review_session: ReviewSession) -> None:
        """Set the review session and update display."""
        self.review_session = review_session
        self.update_metadata_display()
    
    def update_metadata_display(self) -> None:
        """Update the metadata display."""
        if not self.review_session or not self.review_session.metadata:
            self._show_no_metadata()
            return
        
        metadata = self.review_session.metadata
        
        # Update call ID
        if self.call_id_widget:
            call_id_display = metadata.call_id[:12] + "..." if len(metadata.call_id) > 15 else metadata.call_id
            self.call_id_widget.update(f"[bold]Call ID:[/bold] [cyan]{call_id_display}[/cyan]")
        
        # Update caller
        if self.caller_widget:
            self.caller_widget.update(f"[bold]Caller:[/bold] [green]{metadata.caller_number}[/green]")
        
        # Update scenario
        if self.scenario_widget:
            scenario_color = self._get_scenario_color(metadata.scenario)
            self.scenario_widget.update(f"[bold]Scenario:[/bold] [{scenario_color}]{metadata.scenario}[/{scenario_color}]")
        
        # Update duration
        if self.duration_widget:
            duration_str = metadata.get_duration_str()
            self.duration_widget.update(f"[bold]Duration:[/bold] [yellow]{duration_str}[/yellow]")
        
        # Update result
        if self.result_widget:
            result_color = self._get_result_color(metadata.result)
            self.result_widget.update(f"[bold]Result:[/bold] [{result_color}]{metadata.result}[/{result_color}]")
        
        # Update sentiment
        if self.sentiment_widget:
            sentiment_color = self._get_sentiment_color(metadata.sentiment)
            self.sentiment_widget.update(f"[bold]Sentiment:[/bold] [{sentiment_color}]{metadata.sentiment}[/{sentiment_color}]")
        
        # Update agent
        if self.agent_widget:
            self.agent_widget.update(f"[bold]Agent:[/bold] [magenta]{metadata.agent_name}[/magenta]")
        
        # Update start time
        if self.start_time_widget:
            if metadata.start_time:
                time_str = metadata.start_time.strftime("%H:%M:%S")
                self.start_time_widget.update(f"[bold]Started:[/bold] [dim]{time_str}[/dim]")
            else:
                self.start_time_widget.update(f"[bold]Started:[/bold] [dim]--[/dim]")
    
    def _show_no_metadata(self) -> None:
        """Show placeholder text when no metadata is available."""
        placeholder_text = "[dim]No metadata available[/dim]"
        
        widgets = [
            self.call_id_widget,
            self.caller_widget,
            self.scenario_widget,
            self.duration_widget,
            self.result_widget,
            self.sentiment_widget,
            self.agent_widget,
            self.start_time_widget,
        ]
        
        labels = [
            "Call ID:",
            "Caller:",
            "Scenario:",
            "Duration:",
            "Result:",
            "Sentiment:",
            "Agent:",
            "Started:",
        ]
        
        for widget, label in zip(widgets, labels):
            if widget:
                widget.update(f"[bold]{label}[/bold] {placeholder_text}")
    
    def _get_scenario_color(self, scenario: str) -> str:
        """Get color for scenario based on type."""
        scenario_lower = scenario.lower()
        
        if "card" in scenario_lower or "replacement" in scenario_lower:
            return "red"
        elif "balance" in scenario_lower or "inquiry" in scenario_lower:
            return "blue"
        elif "loan" in scenario_lower or "application" in scenario_lower:
            return "green"
        elif "transfer" in scenario_lower or "payment" in scenario_lower:
            return "yellow"
        else:
            return "white"
    
    def _get_result_color(self, result: str) -> str:
        """Get color for result based on status."""
        result_lower = result.lower()
        
        if result_lower in ["success", "completed", "resolved"]:
            return "green"
        elif result_lower in ["failed", "error", "cancelled"]:
            return "red"
        elif result_lower in ["pending", "in progress", "ongoing"]:
            return "yellow"
        else:
            return "white"
    
    def _get_sentiment_color(self, sentiment: str) -> str:
        """Get color for sentiment."""
        sentiment_lower = sentiment.lower()
        
        if sentiment_lower in ["positive", "happy", "satisfied"]:
            return "green"
        elif sentiment_lower in ["negative", "angry", "frustrated"]:
            return "red"
        elif sentiment_lower in ["neutral", "calm"]:
            return "blue"
        else:
            return "white"
    
    def clear_metadata(self) -> None:
        """Clear the metadata display."""
        self.review_session = None
        self._show_no_metadata()