"""
Event logging and management for the Interactive TUI Validator.

This module provides the EventLogger class for capturing, filtering,
and managing events from the TelephonyRealtimeBridge session.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Set, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

class EventLevel(Enum):
    """Event level enumeration."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class EventCategory(Enum):
    """Event category enumeration."""
    CONNECTION = "connection"
    SESSION = "session"
    AUDIO = "audio"
    MESSAGE = "message"
    ERROR = "error"
    SYSTEM = "system"

@dataclass
class LogEvent:
    """Represents a single logged event."""
    timestamp: datetime
    level: EventLevel
    category: EventCategory
    event_type: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "category": self.category.value,
            "event_type": self.event_type,
            "message": self.message,
            "data": self.data,
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
        }

class EventLogger:
    """
    Manages event logging, filtering, and export for TUI validation sessions.
    
    Provides comprehensive event tracking with filtering capabilities,
    export functionality, and real-time event processing.
    """
    
    def __init__(self, max_events: int = 1000):
        # Event storage
        self.events: List[LogEvent] = []
        self.max_events = max_events
        
        # Filtering options
        self.enabled_levels: Set[EventLevel] = set(EventLevel)
        self.enabled_categories: Set[EventCategory] = set(EventCategory)
        self.enabled_types: Set[str] = set()  # Empty means all types
        
        # Statistics
        self.stats = {
            level.value: 0 for level in EventLevel
        }
        self.category_stats = {
            category.value: 0 for category in EventCategory
        }
        
        # Event handlers
        self._event_handlers: List[Callable[[LogEvent], None]] = []
        
        # Session tracking
        self.current_session_id: Optional[str] = None
        self.current_conversation_id: Optional[str] = None
        
    def log_event(self, 
                  event_type: str,
                  message: str,
                  level: EventLevel = EventLevel.INFO,
                  category: EventCategory = EventCategory.SYSTEM,
                  data: Dict[str, Any] = None,
                  session_id: str = None,
                  conversation_id: str = None) -> None:
        """
        Log a new event.
        
        Args:
            event_type: Type of the event
            message: Human-readable message
            level: Event level
            category: Event category
            data: Additional event data
            session_id: Associated session ID
            conversation_id: Associated conversation ID
        """
        # Check if event should be logged based on filters
        if not self._should_log_event(level, category, event_type):
            return
        
        # Use current session/conversation if not provided
        event_session_id = session_id or self.current_session_id
        event_conversation_id = conversation_id or self.current_conversation_id
        
        # Create event
        event = LogEvent(
            timestamp=datetime.now(),
            level=level,
            category=category,
            event_type=event_type,
            message=message,
            data=data or {},
            session_id=event_session_id,
            conversation_id=event_conversation_id
        )
        
        # Add to storage
        self.events.append(event)
        
        # Maintain size limit
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # Update statistics
        self.stats[level.value] += 1
        self.category_stats[category.value] += 1
        
        # Trigger event handlers
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
        
        # Log to Python logger as well
        python_level = self._get_python_log_level(level)
        logger.log(python_level, f"[{category.value}] {event_type}: {message}")
    
    def log_connection_event(self, event_type: str, message: str, 
                           level: EventLevel = EventLevel.INFO, 
                           **kwargs) -> None:
        """Log a connection-related event."""
        self.log_event(event_type, message, level, EventCategory.CONNECTION, **kwargs)
    
    def log_session_event(self, event_type: str, message: str,
                         level: EventLevel = EventLevel.INFO,
                         **kwargs) -> None:
        """Log a session-related event."""
        self.log_event(event_type, message, level, EventCategory.SESSION, **kwargs)
    
    def log_audio_event(self, event_type: str, message: str,
                       level: EventLevel = EventLevel.DEBUG,
                       **kwargs) -> None:
        """Log an audio-related event."""
        self.log_event(event_type, message, level, EventCategory.AUDIO, **kwargs)
    
    def log_message_event(self, event_type: str, message: str,
                         level: EventLevel = EventLevel.DEBUG,
                         **kwargs) -> None:
        """Log a message-related event."""
        self.log_event(event_type, message, level, EventCategory.MESSAGE, **kwargs)
    
    def log_error_event(self, event_type: str, message: str,
                       error_data: Dict[str, Any] = None,
                       **kwargs) -> None:
        """Log an error event."""
        self.log_event(event_type, message, EventLevel.ERROR, EventCategory.ERROR, 
                      data=error_data, **kwargs)
    
    def filter_events(self, 
                     levels: Set[EventLevel] = None,
                     categories: Set[EventCategory] = None,
                     event_types: Set[str] = None,
                     session_id: str = None,
                     conversation_id: str = None,
                     since: datetime = None,
                     until: datetime = None) -> List[LogEvent]:
        """
        Filter events based on criteria.
        
        Args:
            levels: Event levels to include
            categories: Event categories to include  
            event_types: Event types to include
            session_id: Session ID to filter by
            conversation_id: Conversation ID to filter by
            since: Start time filter
            until: End time filter
            
        Returns:
            Filtered list of events
        """
        filtered = []
        
        for event in self.events:
            # Level filter
            if levels and event.level not in levels:
                continue
            
            # Category filter
            if categories and event.category not in categories:
                continue
            
            # Event type filter
            if event_types and event.event_type not in event_types:
                continue
            
            # Session ID filter
            if session_id and event.session_id != session_id:
                continue
            
            # Conversation ID filter
            if conversation_id and event.conversation_id != conversation_id:
                continue
            
            # Time filters
            if since and event.timestamp < since:
                continue
            if until and event.timestamp > until:
                continue
            
            filtered.append(event)
        
        return filtered
    
    def get_recent_events(self, count: int = 50) -> List[LogEvent]:
        """Get the most recent events."""
        return self.events[-count:] if count < len(self.events) else self.events
    
    def get_events_by_session(self, session_id: str) -> List[LogEvent]:
        """Get all events for a specific session."""
        return [event for event in self.events if event.session_id == session_id]
    
    def get_events_by_conversation(self, conversation_id: str) -> List[LogEvent]:
        """Get all events for a specific conversation."""
        return [event for event in self.events if event.conversation_id == conversation_id]
    
    def get_error_events(self) -> List[LogEvent]:
        """Get all error events."""
        return [event for event in self.events if event.level in [EventLevel.ERROR, EventLevel.CRITICAL]]
    
    def set_session_context(self, session_id: str = None, conversation_id: str = None) -> None:
        """Set the current session context for new events."""
        self.current_session_id = session_id
        self.current_conversation_id = conversation_id
    
    def clear_session_context(self) -> None:
        """Clear the current session context."""
        self.current_session_id = None
        self.current_conversation_id = None
    
    def set_level_filter(self, levels: Set[EventLevel]) -> None:
        """Set which event levels to log."""
        self.enabled_levels = levels
    
    def set_category_filter(self, categories: Set[EventCategory]) -> None:
        """Set which event categories to log."""
        self.enabled_categories = categories
    
    def set_type_filter(self, event_types: Set[str]) -> None:
        """Set which event types to log. Empty set means all types."""
        self.enabled_types = event_types
    
    def add_event_handler(self, handler: Callable[[LogEvent], None]) -> None:
        """Add a handler to be called for each new event."""
        self._event_handlers.append(handler)
    
    def remove_event_handler(self, handler: Callable[[LogEvent], None]) -> None:
        """Remove an event handler."""
        if handler in self._event_handlers:
            self._event_handlers.remove(handler)
    
    async def export_logs(self, filepath: str, format: str = "json", 
                         filters: Dict[str, Any] = None) -> bool:
        """
        Export events to a file.
        
        Args:
            filepath: Output file path
            format: Export format ("json", "csv", "txt")
            filters: Event filters to apply
            
        Returns:
            True if export successful
        """
        try:
            # Apply filters if provided
            events_to_export = self.events
            if filters:
                events_to_export = self.filter_events(**filters)
            
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == "json":
                await self._export_json(filepath, events_to_export)
            elif format.lower() == "csv":
                await self._export_csv(filepath, events_to_export)
            elif format.lower() == "txt":
                await self._export_txt(filepath, events_to_export)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Exported {len(events_to_export)} events to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting logs: {e}")
            return False
    
    async def _export_json(self, filepath: Path, events: List[LogEvent]) -> None:
        """Export events to JSON format."""
        data = {
            "export_timestamp": datetime.now().isoformat(),
            "event_count": len(events),
            "events": [event.to_dict() for event in events],
            "statistics": self.get_statistics()
        }
        
        with filepath.open('w') as f:
            json.dump(data, f, indent=2, default=str)
    
    async def _export_csv(self, filepath: Path, events: List[LogEvent]) -> None:
        """Export events to CSV format."""
        import csv
        
        with filepath.open('w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                "timestamp", "level", "category", "event_type", "message",
                "session_id", "conversation_id", "data"
            ])
            
            # Write events
            for event in events:
                writer.writerow([
                    event.timestamp.isoformat(),
                    event.level.value,
                    event.category.value,
                    event.event_type,
                    event.message,
                    event.session_id or "",
                    event.conversation_id or "",
                    json.dumps(event.data) if event.data else ""
                ])
    
    async def _export_txt(self, filepath: Path, events: List[LogEvent]) -> None:
        """Export events to text format."""
        with filepath.open('w') as f:
            f.write(f"Event Log Export - {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")
            
            for event in events:
                f.write(f"[{event.timestamp.strftime('%H:%M:%S.%f')[:-3]}] ")
                f.write(f"{event.level.value.upper()} ")
                f.write(f"[{event.category.value}] ")
                f.write(f"{event.event_type}: {event.message}\n")
                
                if event.session_id or event.conversation_id:
                    f.write(f"  Session: {event.session_id or 'N/A'}, ")
                    f.write(f"Conversation: {event.conversation_id or 'N/A'}\n")
                
                if event.data:
                    f.write(f"  Data: {json.dumps(event.data, indent=4)}\n")
                
                f.write("\n")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event statistics."""
        total_events = len(self.events)
        
        recent_events = self.get_recent_events(100)
        recent_timespan = None
        if recent_events:
            start_time = recent_events[0].timestamp
            end_time = recent_events[-1].timestamp
            recent_timespan = (end_time - start_time).total_seconds()
        
        return {
            "total_events": total_events,
            "max_events": self.max_events,
            "level_counts": self.stats.copy(),
            "category_counts": self.category_stats.copy(),
            "recent_events_count": len(recent_events),
            "recent_timespan_seconds": recent_timespan,
            "current_session_id": self.current_session_id,
            "current_conversation_id": self.current_conversation_id,
        }
    
    def clear_events(self) -> None:
        """Clear all events and reset statistics."""
        self.events.clear()
        self.stats = {level.value: 0 for level in EventLevel}
        self.category_stats = {category.value: 0 for category in EventCategory}
        
        logger.info("Event log cleared")
    
    def _should_log_event(self, level: EventLevel, category: EventCategory, 
                         event_type: str) -> bool:
        """Check if an event should be logged based on current filters."""
        if level not in self.enabled_levels:
            return False
        
        if category not in self.enabled_categories:
            return False
        
        if self.enabled_types and event_type not in self.enabled_types:
            return False
        
        return True
    
    def _get_python_log_level(self, level: EventLevel) -> int:
        """Convert EventLevel to Python logging level."""
        mapping = {
            EventLevel.DEBUG: logging.DEBUG,
            EventLevel.INFO: logging.INFO,
            EventLevel.WARNING: logging.WARNING,
            EventLevel.ERROR: logging.ERROR,
            EventLevel.CRITICAL: logging.CRITICAL,
        }
        return mapping.get(level, logging.INFO) 