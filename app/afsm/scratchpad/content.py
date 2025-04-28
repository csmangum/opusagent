"""
ScratchpadContent - Container for structured reasoning data
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Entry:
    """A single entry in the scratchpad with timestamp and metadata."""
    content: str
    timestamp: float = field(default_factory=lambda: (time.sleep(0.001), time.time())[1])
    metadata: Dict[str, Any] = field(default_factory=dict)


class ScratchpadContent:
    """
    Structured container for agent reasoning data.
    
    Supports append, clear, and retrieve operations with timestamped
    entries for tracking thought progression.
    """
    
    def __init__(self, max_entries: int = 1000, name: str = "default"):
        """
        Initialize a new scratchpad content container.
        
        Args:
            max_entries: Maximum number of entries to store before rotation
            name: Identifier for this scratchpad
        """
        self.name = name
        self.max_entries = max_entries
        self.entries: List[Entry] = []
        self.metadata: Dict[str, Any] = {}
    
    def append(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a new entry to the scratchpad.
        
        Args:
            content: The text content to add
            metadata: Optional metadata about this entry
        """
        if len(self.entries) >= self.max_entries:
            # Remove oldest entry when limit is reached
            self.entries.pop(0)
        
        self.entries.append(Entry(
            content=content,
            metadata=metadata or {}
        ))
    
    def clear(self) -> None:
        """Clear all entries from the scratchpad."""
        self.entries = []
    
    def get_content(self, last_n: Optional[int] = None) -> str:
        """
        Retrieve the content of the scratchpad.
        
        Args:
            last_n: If specified, only return the last N entries
            
        Returns:
            String containing all entries, separated by newlines
        """
        entries_to_return = self.entries
        if last_n is not None:
            entries_to_return = self.entries[-last_n:]
        
        return "\n".join(entry.content for entry in entries_to_return)
    
    def get_entries(self, last_n: Optional[int] = None) -> List[Entry]:
        """
        Get the raw entries with timestamps and metadata.
        
        Args:
            last_n: If specified, only return the last N entries
            
        Returns:
            List of Entry objects
        """
        if last_n is not None:
            return self.entries[-last_n:]
        return self.entries
    
    def search(self, query: str) -> List[Entry]:
        """
        Search entries for containing the query string.
        
        Args:
            query: String to search for in entries
            
        Returns:
            List of matching entries
        """
        return [entry for entry in self.entries if query.lower() in entry.content.lower()]
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata for the entire scratchpad."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata for the entire scratchpad."""
        return self.metadata.get(key, default)
    
    def __len__(self) -> int:
        """Return the number of entries in the scratchpad."""
        return len(self.entries)
    
    def __str__(self) -> str:
        """String representation of the scratchpad."""
        return f"ScratchpadContent('{self.name}', {len(self)} entries)" 