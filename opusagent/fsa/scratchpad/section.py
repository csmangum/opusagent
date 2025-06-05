"""
ReasoningSection - Specialized containers for different aspects of reasoning
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set

from opusagent.fsa.scratchpad.content import ScratchpadContent


class SectionType(Enum):
    """Standard section types for reasoning."""
    FACTS = "facts"
    HYPOTHESES = "hypotheses"
    CALCULATIONS = "calculations"
    CONCLUSIONS = "conclusions"
    QUESTIONS = "questions"
    NOTES = "notes"
    CUSTOM = "custom"


class ReasoningSection:
    """
    Specialized container within scratchpads dedicated to a specific aspect of reasoning.
    
    Maintains relationships between content in different sections.
    """
    
    def __init__(self, section_type: SectionType, name: Optional[str] = None):
        """
        Initialize a new reasoning section.
        
        Args:
            section_type: The type of reasoning this section contains
            name: Optional custom name for this section
        """
        self.section_type = section_type
        self.name = name or section_type.value
        self.content = ScratchpadContent(name=self.name)
        self.references: Dict[str, Set[str]] = {}  # Maps entry IDs to related entry IDs
    
    def add(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add content to this reasoning section.
        
        Args:
            content: The text content to add
            metadata: Optional metadata about this content
            
        Returns:
            ID of the new entry (timestamp as string)
        """
        # Ensure metadata exists
        metadata = metadata or {}
        
        # Add the content to the scratchpad
        self.content.append(content, metadata)
        
        # Use the timestamp as the entry ID
        entry_id = str(self.content.entries[-1].timestamp)
        
        # Initialize reference tracking for this entry
        self.references[entry_id] = set()
        
        return entry_id
    
    def relate(self, source_id: str, target_id: str) -> None:
        """
        Establish a relationship between entries.
        
        Args:
            source_id: ID of the source entry
            target_id: ID of the target entry this is related to
        """
        if source_id in self.references:
            self.references[source_id].add(target_id)
    
    def get_related(self, entry_id: str) -> List[str]:
        """
        Get all entries related to the specified entry.
        
        Args:
            entry_id: ID of the entry to find relations for
            
        Returns:
            List of related entry IDs
        """
        return list(self.references.get(entry_id, set()))
    
    def get_all_content(self) -> str:
        """Get all content in this section as a string."""
        return self.content.get_content()
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for entries containing the query string.
        
        Args:
            query: String to search for
            
        Returns:
            List of matching entries with their IDs and content
        """
        entries = self.content.search(query)
        return [
            {
                "id": str(entry.timestamp),
                "content": entry.content,
                "metadata": entry.metadata,
                "timestamp": entry.timestamp
            }
            for entry in entries
        ]
    
    def clear(self) -> None:
        """Clear all content and references in this section."""
        self.content.clear()
        self.references.clear()
    
    def __str__(self) -> str:
        """String representation of the section."""
        return f"ReasoningSection({self.section_type.value}, {len(self.content)} entries)" 