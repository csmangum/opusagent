"""
ScratchpadManager - Central manager for scratchpad operations
"""

import json
import uuid
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
import os

from fastagent.fsa.scratchpad.content import ScratchpadContent
from fastagent.fsa.scratchpad.section import ReasoningSection, SectionType


class ScratchpadManager:
    """
    Central manager for scratchpad operations.
    
    Handles persistence and retrieval of scratchpad content and
    provides isolation between different reasoning contexts.
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize the scratchpad manager.
        
        Args:
            storage_dir: Optional directory for persisting scratchpads
        """
        self.storage_dir = storage_dir
        if storage_dir and not storage_dir.exists():
            storage_dir.mkdir(parents=True, exist_ok=True)
            
        self.scratchpads: Dict[str, ScratchpadContent] = {}
        self.sections: Dict[str, Dict[str, ReasoningSection]] = {}
        self.active_scratchpad_id: Optional[str] = None
    
    def create_scratchpad(self, name: Optional[str] = None) -> str:
        """
        Create a new scratchpad.
        
        Args:
            name: Optional name for the scratchpad
            
        Returns:
            ID of the new scratchpad
        """
        pad_id = str(uuid.uuid4())
        pad_name = name or f"scratchpad_{pad_id[:8]}"
        
        self.scratchpads[pad_id] = ScratchpadContent(name=pad_name)
        self.sections[pad_id] = {}
        
        # Set as active if no active scratchpad
        if self.active_scratchpad_id is None:
            self.active_scratchpad_id = pad_id
            
        return pad_id
    
    def set_active_scratchpad(self, pad_id: str) -> None:
        """
        Set the active scratchpad.
        
        Args:
            pad_id: ID of the scratchpad to make active
        
        Raises:
            ValueError: If the scratchpad ID doesn't exist
        """
        if pad_id not in self.scratchpads:
            raise ValueError(f"Scratchpad {pad_id} does not exist")
        
        self.active_scratchpad_id = pad_id
    
    def get_active_scratchpad(self) -> Optional[ScratchpadContent]:
        """
        Get the currently active scratchpad.
        
        Returns:
            The active scratchpad or None if no active scratchpad
        """
        if self.active_scratchpad_id is None:
            return None
        
        return self.scratchpads.get(self.active_scratchpad_id)
    
    def write(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Write to the active scratchpad.
        
        Args:
            content: Content to write
            metadata: Optional metadata
            
        Raises:
            ValueError: If no active scratchpad exists
        """
        if self.active_scratchpad_id is None:
            raise ValueError("No active scratchpad")
        
        pad = self.scratchpads[self.active_scratchpad_id]
        pad.append(content, metadata)
    
    def read(self, pad_id: Optional[str] = None, last_n: Optional[int] = None) -> str:
        """
        Read content from a scratchpad.
        
        Args:
            pad_id: ID of the scratchpad to read (uses active if None)
            last_n: Optional limit to only read the last N entries
            
        Returns:
            Content of the scratchpad as a string
            
        Raises:
            ValueError: If the scratchpad doesn't exist or no active scratchpad
        """
        target_id = pad_id or self.active_scratchpad_id
        
        if target_id is None:
            raise ValueError("No active scratchpad")
            
        if target_id not in self.scratchpads:
            raise ValueError(f"Scratchpad {target_id} does not exist")
            
        return self.scratchpads[target_id].get_content(last_n)
    
    def create_section(
        self, 
        section_type: SectionType, 
        name: Optional[str] = None,
        pad_id: Optional[str] = None
    ) -> str:
        """
        Create a new reasoning section in a scratchpad.
        
        Args:
            section_type: Type of reasoning section
            name: Optional custom name for the section
            pad_id: ID of scratchpad to add section to (uses active if None)
            
        Returns:
            ID of the new section (same as name)
            
        Raises:
            ValueError: If the scratchpad doesn't exist or no active scratchpad
        """
        target_id = pad_id or self.active_scratchpad_id
        
        if target_id is None:
            raise ValueError("No active scratchpad")
            
        if target_id not in self.scratchpads:
            raise ValueError(f"Scratchpad {target_id} does not exist")
        
        section_name = name or section_type.value
        
        # Check if section with this name already exists
        if section_name in self.sections[target_id]:
            return section_name
            
        self.sections[target_id][section_name] = ReasoningSection(
            section_type=section_type,
            name=section_name
        )
        
        return section_name
    
    def get_section(
        self, 
        section_name: str, 
        pad_id: Optional[str] = None
    ) -> ReasoningSection:
        """
        Get a reasoning section from a scratchpad.
        
        Args:
            section_name: Name of the section to get
            pad_id: ID of scratchpad to get section from (uses active if None)
            
        Returns:
            The reasoning section
            
        Raises:
            ValueError: If the scratchpad or section doesn't exist
        """
        target_id = pad_id or self.active_scratchpad_id
        
        if target_id is None:
            raise ValueError("No active scratchpad")
            
        if target_id not in self.scratchpads:
            raise ValueError(f"Scratchpad {target_id} does not exist")
            
        if section_name not in self.sections[target_id]:
            raise ValueError(f"Section {section_name} does not exist in scratchpad {target_id}")
            
        return self.sections[target_id][section_name]
    
    def write_to_section(
        self,
        section_name: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        pad_id: Optional[str] = None
    ) -> str:
        """
        Write content to a specific reasoning section.
        
        Args:
            section_name: Name of the section to write to
            content: Content to write
            metadata: Optional metadata
            pad_id: ID of scratchpad containing section (uses active if None)
            
        Returns:
            ID of the new entry
            
        Raises:
            ValueError: If the scratchpad or section doesn't exist
        """
        section = self.get_section(section_name, pad_id)
        return section.add(content, metadata)
    
    def get_all_sections(self, pad_id: Optional[str] = None) -> Dict[str, ReasoningSection]:
        """
        Get all sections for a scratchpad.
        
        Args:
            pad_id: ID of scratchpad to get sections from (uses active if None)
            
        Returns:
            Dictionary mapping section names to ReasoningSection objects
            
        Raises:
            ValueError: If the scratchpad doesn't exist or no active scratchpad
        """
        target_id = pad_id or self.active_scratchpad_id
        
        if target_id is None:
            raise ValueError("No active scratchpad")
            
        if target_id not in self.scratchpads:
            raise ValueError(f"Scratchpad {target_id} does not exist")
            
        return self.sections[target_id]
    
    def persist(self, pad_id: Optional[str] = None) -> bool:
        """
        Persist a scratchpad to storage.
        
        Args:
            pad_id: ID of scratchpad to persist (uses active if None)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: If the scratchpad doesn't exist
        """
        target_id = pad_id or self.active_scratchpad_id
        
        if target_id is None:
            raise ValueError("No active scratchpad")
            
        if target_id not in self.scratchpads:
            raise ValueError(f"Scratchpad {target_id} does not exist")
            
        if self.storage_dir is None:
            return False
        
        try:
            # Create serializable representation
            pad_data = {
                "id": target_id,
                "name": self.scratchpads[target_id].name,
                "metadata": self.scratchpads[target_id].metadata,
                "entries": [
                    {
                        "content": entry.content,
                        "timestamp": entry.timestamp,
                        "metadata": entry.metadata
                    }
                    for entry in self.scratchpads[target_id].entries
                ],
                "sections": {
                    name: {
                        "type": section.section_type.value,
                        "name": section.name,
                        "entries": [
                            {
                                "content": entry.content,
                                "timestamp": entry.timestamp,
                                "metadata": entry.metadata
                            }
                            for entry in section.content.entries
                        ],
                        "references": {
                            k: list(v) for k, v in section.references.items()
                        }
                    }
                    for name, section in self.sections[target_id].items()
                }
            }
            
            # Write to file
            file_path = self.storage_dir / f"{target_id}.json"
            with open(file_path, 'w') as f:
                json.dump(pad_data, f, indent=2)
                
            return True
        
        except Exception as e:
            print(f"Error persisting scratchpad: {e}")
            return False
    
    def load(self, pad_id: str) -> bool:
        """
        Load a scratchpad from storage.
        
        Args:
            pad_id: ID of scratchpad to load
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: If no storage directory or file doesn't exist
        """
        if self.storage_dir is None:
            return False
            
        file_path = self.storage_dir / f"{pad_id}.json"
        
        if not file_path.exists():
            return False
            
        try:
            # Read from file
            with open(file_path, 'r') as f:
                pad_data = json.load(f)
                
            # Create scratchpad
            self.scratchpads[pad_id] = ScratchpadContent(name=pad_data["name"])
            self.scratchpads[pad_id].metadata = pad_data["metadata"]
            
            # Load entries
            for entry_data in pad_data["entries"]:
                self.scratchpads[pad_id].append(
                    content=entry_data["content"],
                    metadata=entry_data["metadata"]
                )
                
            # Initialize sections dict
            self.sections[pad_id] = {}
                
            # Load sections
            for section_name, section_data in pad_data["sections"].items():
                section_type = SectionType(section_data["type"])
                section = ReasoningSection(
                    section_type=section_type,
                    name=section_data["name"]
                )
                
                # Load section entries
                for entry_data in section_data["entries"]:
                    section.content.append(
                        content=entry_data["content"],
                        metadata=entry_data["metadata"]
                    )
                
                # Load references
                for source_id, target_ids in section_data["references"].items():
                    section.references[source_id] = set(target_ids)
                
                self.sections[pad_id][section_name] = section
                
            return True
        
        except Exception as e:
            print(f"Error loading scratchpad: {e}")
            return False
    
    def delete(self, pad_id: str) -> bool:
        """
        Delete a scratchpad.
        
        Args:
            pad_id: ID of scratchpad to delete
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: If the scratchpad doesn't exist
        """
        if pad_id not in self.scratchpads:
            raise ValueError(f"Scratchpad {pad_id} does not exist")
            
        # Remove from memory
        if pad_id in self.scratchpads:
            del self.scratchpads[pad_id]
        
        if pad_id in self.sections:
            del self.sections[pad_id]
            
        # Clear active if it was this pad
        if self.active_scratchpad_id == pad_id:
            self.active_scratchpad_id = None
            
        # Remove from storage if exists
        if self.storage_dir is not None:
            file_path = self.storage_dir / f"{pad_id}.json"
            if file_path.exists():
                file_path.unlink()
                    
        return True 