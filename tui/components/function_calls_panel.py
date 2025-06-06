"""
Function Calls Panel component for the Interactive TUI Validator.

This panel provides detailed monitoring of function calls made by the AI agent,
including arguments, results, and execution flow visualization.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, Button, RichLog, DataTable, Tree
from textual.widget import Widget

logger = logging.getLogger(__name__)

class FunctionCallsPanel(Widget):
    """Panel for monitoring AI function calls and results."""
    
    CSS = """
    FunctionCallsPanel {
        background: $surface;
        border: solid $primary;
        height: auto;
        min-height: 20;
    }
    
    .function-header {
        background: $primary;
        color: $primary-background;
        text-align: center;
        height: 1;
    }
    
    .function-stats {
        layout: horizontal;
        height: 1;
        align: center middle;
        padding: 0 1;
    }
    
    .function-log {
        height: 15;
    }
    
    .controls-row {
        layout: horizontal;
        height: 1;
        align: center middle;
        padding: 0 1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parent_app = None
        
        # Function call tracking
        self.function_calls: List[Dict[str, Any]] = []
        self.function_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "functions_used": set()
        }
        
        # Current session
        self.session_active = False
        self.current_conversation_id = None
        
    def compose(self) -> ComposeResult:
        """Create the function calls panel layout."""
        with Vertical():
            # Header
            yield Static("🔧 Function Calls Monitor", classes="function-header")
            
            # Stats
            with Horizontal(classes="function-stats"):
                yield Static("Total: 0", id="total-calls-stat")
                yield Static("Success: 0", id="success-calls-stat")
                yield Static("Failed: 0", id="failed-calls-stat")
                yield Static("Functions: 0", id="functions-used-stat")
            
            # Controls
            with Horizontal(classes="controls-row"):
                yield Button("Clear Log", id="clear-function-log-btn")
                yield Button("Export Calls", id="export-function-calls-btn")
                yield Button("📋 Copy JSON", id="copy-json-btn")
            
            # Function call log
            self.function_log = RichLog(
                highlight=True,
                markup=True,
                id="function-log",
                classes="function-log"
            )
            yield self.function_log
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "clear-function-log-btn":
            self._clear_log()
        elif event.button.id == "export-function-calls-btn":
            asyncio.create_task(self._export_function_calls())
        elif event.button.id == "copy-json-btn":
            self._copy_calls_as_json()
    
    def add_function_call(self, function_name: str, arguments: Dict[str, Any], 
                         call_id: str = None, status: str = "started") -> None:
        """Add a function call to the log."""
        timestamp = datetime.now()
        
        # Create function call record
        call_record = {
            "timestamp": timestamp,
            "function_name": function_name,
            "arguments": arguments,
            "call_id": call_id,
            "status": status,
            "conversation_id": self.current_conversation_id,
            "result": None,
            "error": None,
            "duration_ms": None
        }
        
        # Add to tracking
        self.function_calls.append(call_record)
        
        # Update stats
        self.function_stats["total_calls"] += 1
        self.function_stats["functions_used"].add(function_name)
        
        # Format and display
        self._display_function_call(call_record)
        self._update_stats_display()
        
        # Log to events panel
        if self.parent_app and hasattr(self.parent_app, "events_panel"):
            self.parent_app.events_panel.add_event(
                "function_call", status="info",
                details=f"Called: {function_name}"
            )
    
    def update_function_result(self, call_id: str, result: Any = None, 
                             error: str = None, duration_ms: float = None) -> None:
        """Update a function call with its result."""
        # Find the function call by call_id
        for call_record in reversed(self.function_calls):
            if call_record.get("call_id") == call_id:
                call_record["result"] = result
                call_record["error"] = error
                call_record["duration_ms"] = duration_ms
                
                if error:
                    call_record["status"] = "failed"
                    self.function_stats["failed_calls"] += 1
                else:
                    call_record["status"] = "completed"
                    self.function_stats["successful_calls"] += 1
                
                # Re-display the updated call
                self._display_function_result(call_record)
                self._update_stats_display()
                break
    
    def _display_function_call(self, call_record: Dict[str, Any]) -> None:
        """Display a function call in the log."""
        timestamp = call_record["timestamp"].strftime("%H:%M:%S.%f")[:-3]
        function_name = call_record["function_name"]
        arguments = call_record["arguments"]
        call_id = call_record.get("call_id", "N/A")
        
        # Format arguments for display
        args_preview = self._format_arguments_preview(arguments)
        
        # Color based on status
        if call_record["status"] == "started":
            color = "yellow"
            icon = "🚀"
        elif call_record["status"] == "completed":
            color = "green"
            icon = "✅"
        elif call_record["status"] == "failed":
            color = "red"
            icon = "❌"
        else:
            color = "white"
            icon = "🔧"
        
        # Display function call
        self.function_log.write(
            f"[dim]{timestamp}[/dim] [{color}]{icon} {function_name}[/{color}]"
        )
        self.function_log.write(
            f"  [dim]Call ID:[/dim] {call_id[:8]}..."
        )
        self.function_log.write(
            f"  [dim]Args:[/dim] {args_preview}"
        )
    
    def _display_function_result(self, call_record: Dict[str, Any]) -> None:
        """Display the result of a function call."""
        function_name = call_record["function_name"]
        result = call_record.get("result")
        error = call_record.get("error")
        duration_ms = call_record.get("duration_ms")
        
        # Format duration
        duration_str = f"{duration_ms:.1f}ms" if duration_ms else "N/A"
        
        if error:
            self.function_log.write(
                f"  [red]❌ Error:[/red] {error}"
            )
        else:
            result_preview = self._format_result_preview(result)
            self.function_log.write(
                f"  [green]✅ Result:[/green] {result_preview}"
            )
        
        self.function_log.write(
            f"  [dim]Duration:[/dim] {duration_str}"
        )
        self.function_log.write("")  # Empty line for separation
    
    def _format_arguments_preview(self, arguments: Dict[str, Any]) -> str:
        """Format function arguments for preview display."""
        if not arguments:
            return "{}"
        
        # Create a shortened version for display
        preview_parts = []
        for key, value in arguments.items():
            if isinstance(value, str) and len(value) > 30:
                value_str = f'"{value[:30]}..."'
            elif isinstance(value, (dict, list)) and len(str(value)) > 50:
                value_str = f"{type(value).__name__}(...)"
            else:
                value_str = json.dumps(value)
            
            preview_parts.append(f"{key}: {value_str}")
        
        preview = "{" + ", ".join(preview_parts) + "}"
        
        # Truncate if still too long
        if len(preview) > 100:
            preview = preview[:97] + "...}"
        
        return preview
    
    def _format_result_preview(self, result: Any) -> str:
        """Format function result for preview display."""
        if result is None:
            return "null"
        
        if isinstance(result, str) and len(result) > 100:
            return f'"{result[:100]}..."'
        elif isinstance(result, (dict, list)):
            result_str = json.dumps(result)
            if len(result_str) > 100:
                return f"{type(result).__name__}({len(result)} items)"
            return result_str
        else:
            return str(result)
    
    def _update_stats_display(self) -> None:
        """Update the statistics display."""
        try:
            total_stat = self.query_one("#total-calls-stat", Static)
            success_stat = self.query_one("#success-calls-stat", Static)
            failed_stat = self.query_one("#failed-calls-stat", Static)
            functions_stat = self.query_one("#functions-used-stat", Static)
            
            total_stat.update(f"Total: {self.function_stats['total_calls']}")
            success_stat.update(f"Success: {self.function_stats['successful_calls']}")
            failed_stat.update(f"Failed: {self.function_stats['failed_calls']}")
            functions_stat.update(f"Functions: {len(self.function_stats['functions_used'])}")
        except:
            pass
    
    def _clear_log(self) -> None:
        """Clear the function call log."""
        self.function_log.clear()
        self.function_calls.clear()
        self.function_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "functions_used": set()
        }
        self._update_stats_display()
        
        if self.parent_app and hasattr(self.parent_app, "events_panel"):
            self.parent_app.events_panel.add_event(
                "function_log_cleared", status="info",
                details="Function call log cleared"
            )
    
    async def _export_function_calls(self) -> None:
        """Export function calls to JSON file."""
        if not self.function_calls:
            logger.warning("No function calls to export")
            return
        
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"function_calls_{timestamp}.json"
            
            # Prepare export data
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "conversation_id": self.current_conversation_id,
                "statistics": {
                    "total_calls": self.function_stats["total_calls"],
                    "successful_calls": self.function_stats["successful_calls"],
                    "failed_calls": self.function_stats["failed_calls"],
                    "functions_used": list(self.function_stats["functions_used"])
                },
                "function_calls": []
            }
            
            # Convert function calls to serializable format
            for call in self.function_calls:
                export_call = call.copy()
                export_call["timestamp"] = call["timestamp"].isoformat()
                export_data["function_calls"].append(export_call)
            
            # Write to file
            import json
            from pathlib import Path
            
            output_dir = Path("call_recordings")
            output_dir.mkdir(exist_ok=True)
            filepath = output_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Function calls exported to {filepath}")
            
            if self.parent_app and hasattr(self.parent_app, "events_panel"):
                self.parent_app.events_panel.add_event(
                    "function_calls_exported", status="success",
                    details=f"Exported to {filename}"
                )
                
        except Exception as e:
            logger.error(f"Error exporting function calls: {e}")
            if self.parent_app and hasattr(self.parent_app, "events_panel"):
                self.parent_app.events_panel.add_event(
                    "export_error", status="error",
                    details=f"Export failed: {e}"
                )
    
    def _copy_calls_as_json(self) -> None:
        """Copy function calls as JSON to clipboard (placeholder)."""
        # This would implement clipboard copying functionality
        logger.info("Function calls copied to clipboard (not implemented)")
        
        if self.parent_app and hasattr(self.parent_app, "events_panel"):
            self.parent_app.events_panel.add_event(
                "function_calls_copied", status="info",
                details="Function calls copied to clipboard"
            )
    
    def set_session_state(self, active: bool, conversation_id: str = None) -> None:
        """Update session state."""
        self.session_active = active
        self.current_conversation_id = conversation_id
        
        if not active:
            # Session ended, add separator
            if self.function_calls:
                self.function_log.write("")
                self.function_log.write("[dim]--- Session Ended ---[/dim]")
                self.function_log.write("")
    
    def get_function_call_summary(self) -> Dict[str, Any]:
        """Get a summary of function calls for the current session."""
        if not self.function_calls:
            return {"total": 0, "functions": [], "success_rate": 0}
        
        success_rate = (
            self.function_stats["successful_calls"] / self.function_stats["total_calls"] * 100
            if self.function_stats["total_calls"] > 0 else 0
        )
        
        return {
            "total": self.function_stats["total_calls"],
            "successful": self.function_stats["successful_calls"],
            "failed": self.function_stats["failed_calls"],
            "functions": list(self.function_stats["functions_used"]),
            "success_rate": success_rate,
            "conversation_id": self.current_conversation_id
        } 