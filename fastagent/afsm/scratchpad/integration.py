"""
Integration - Connect the scratchpad system with the AFSM state system
"""

from typing import Dict, Optional, Any

from fastagent.afsm.scratchpad.manager import ScratchpadManager
from fastagent.afsm.scratchpad.section import SectionType


class StateScratchpadIntegration:
    """
    Integration between the scratchpad system and the AFSM state system.
    
    Provides methods for state classes to interact with scratchpads in a consistent manner.
    """
    
    def __init__(self, manager: Optional[ScratchpadManager] = None):
        """
        Initialize the integration.
        
        Args:
            manager: Optional existing scratchpad manager to use
        """
        self.manager = manager or ScratchpadManager()
        self._state_mappings: Dict[str, str] = {}  # Maps state names to scratchpad IDs
    
    def get_scratchpad_for_state(self, state_name: str, create_if_missing: bool = True) -> str:
        """
        Get the scratchpad ID associated with a state.
        
        Args:
            state_name: Name of the state
            create_if_missing: Whether to create a new scratchpad if one doesn't exist
            
        Returns:
            ID of the scratchpad
            
        Raises:
            ValueError: If no scratchpad exists and create_if_missing is False
        """
        if state_name in self._state_mappings:
            return self._state_mappings[state_name]
            
        if not create_if_missing:
            raise ValueError(f"No scratchpad exists for state {state_name}")
            
        # Create a new scratchpad for this state
        pad_id = self.manager.create_scratchpad(name=f"state_{state_name}")
        self._state_mappings[state_name] = pad_id
        
        # Create standard sections
        self.manager.create_section(SectionType.FACTS, pad_id=pad_id)
        self.manager.create_section(SectionType.HYPOTHESES, pad_id=pad_id)
        self.manager.create_section(SectionType.CALCULATIONS, pad_id=pad_id)
        self.manager.create_section(SectionType.CONCLUSIONS, pad_id=pad_id)
        
        return pad_id
    
    def write_to_state_scratchpad(
        self, 
        state_name: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Write to a state's scratchpad.
        
        Args:
            state_name: Name of the state
            content: Content to write
            metadata: Optional metadata
        """
        pad_id = self.get_scratchpad_for_state(state_name)
        self.manager.set_active_scratchpad(pad_id)
        self.manager.write(content, metadata)
    
    def read_state_scratchpad(self, state_name: str, last_n: Optional[int] = None) -> str:
        """
        Read content from a state's scratchpad.
        
        Args:
            state_name: Name of the state
            last_n: Optional limit to only read the last N entries
            
        Returns:
            Content of the scratchpad as a string
        """
        pad_id = self.get_scratchpad_for_state(state_name)
        return self.manager.read(pad_id, last_n)
    
    def write_to_state_section(
        self,
        state_name: str,
        section_type: SectionType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Write to a specific section in a state's scratchpad.
        
        Args:
            state_name: Name of the state
            section_type: Type of section to write to
            content: Content to write
            metadata: Optional metadata
            
        Returns:
            ID of the new entry
        """
        pad_id = self.get_scratchpad_for_state(state_name)
        section_name = section_type.value
        
        # Ensure section exists
        if section_name not in self.manager.get_all_sections(pad_id):
            self.manager.create_section(section_type, pad_id=pad_id)
            
        return self.manager.write_to_section(section_name, content, metadata, pad_id)
    
    def transfer_selected_content(
        self, 
        source_state: str, 
        target_state: str,
        section_types: Optional[list[SectionType]] = None
    ) -> None:
        """
        Transfer selected content from one state's scratchpad to another.
        
        Args:
            source_state: Name of the source state
            target_state: Name of the target state
            section_types: Optional list of section types to transfer (all if None)
        """
        source_pad_id = self.get_scratchpad_for_state(source_state, create_if_missing=False)
        target_pad_id = self.get_scratchpad_for_state(target_state)
        
        # Get all sections from source
        source_sections = self.manager.get_all_sections(source_pad_id)
        
        # Filter to specified section types if provided
        if section_types:
            section_names = [section_type.value for section_type in section_types]
            source_sections = {name: section for name, section in source_sections.items() 
                             if name in section_names}
        
        # Copy content from each section
        for section_name, section in source_sections.items():
            # Ensure section exists in target
            if section_name not in self.manager.get_all_sections(target_pad_id):
                self.manager.create_section(section.section_type, pad_id=target_pad_id)
                
            # Copy all entries
            for entry in section.content.entries:
                self.manager.write_to_section(
                    section_name,
                    entry.content,
                    entry.metadata,
                    target_pad_id
                )
                
    def clear_state_scratchpad(self, state_name: str) -> None:
        """
        Clear a state's scratchpad.
        
        Args:
            state_name: Name of the state
        """
        if state_name in self._state_mappings:
            pad_id = self._state_mappings[state_name]
            
            # Clear all sections
            for section in self.manager.get_all_sections(pad_id).values():
                section.clear()
                
            # Clear main scratchpad
            self.manager.scratchpads[pad_id].clear()


# Example AFSMState mixin
class ScratchpadStateMixin:
    """
    Mixin class for AFSMState to add scratchpad functionality.
    
    This can be used by state classes to easily interact with the scratchpad system.
    """
    
    def __init__(self, scratchpad_integration: Optional[StateScratchpadIntegration] = None):
        """
        Initialize the mixin.
        
        Args:
            scratchpad_integration: Optional integration instance to use
        """
        self._scratchpad_integration = scratchpad_integration or StateScratchpadIntegration()
        
    def write_to_scratchpad(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Write to this state's scratchpad.
        
        Args:
            content: Content to write
            metadata: Optional metadata
        """
        self._scratchpad_integration.write_to_state_scratchpad(
            self.name,  # Assumes state has a name attribute
            content,
            metadata
        )
        
    def get_scratchpad(self, last_n: Optional[int] = None) -> str:
        """
        Get content from this state's scratchpad.
        
        Args:
            last_n: Optional limit to only get the last N entries
            
        Returns:
            Content of the scratchpad as a string
        """
        return self._scratchpad_integration.read_state_scratchpad(self.name, last_n)
        
    def write_fact(self, content: str) -> str:
        """
        Write a fact to this state's scratchpad.
        
        Args:
            content: The fact to write
            
        Returns:
            ID of the new entry
        """
        return self._scratchpad_integration.write_to_state_section(
            self.name,
            SectionType.FACTS,
            content
        )
        
    def write_hypothesis(self, content: str) -> str:
        """
        Write a hypothesis to this state's scratchpad.
        
        Args:
            content: The hypothesis to write
            
        Returns:
            ID of the new entry
        """
        return self._scratchpad_integration.write_to_state_section(
            self.name,
            SectionType.HYPOTHESES,
            content
        )
        
    def write_conclusion(self, content: str) -> str:
        """
        Write a conclusion to this state's scratchpad.
        
        Args:
            content: The conclusion to write
            
        Returns:
            ID of the new entry
        """
        return self._scratchpad_integration.write_to_state_section(
            self.name,
            SectionType.CONCLUSIONS,
            content
        )
        
    def transfer_reasoning_to(self, target_state_name: str) -> None:
        """
        Transfer reasoning from this state to another.
        
        Args:
            target_state_name: Name of the target state
        """
        self._scratchpad_integration.transfer_selected_content(
            self.name,
            target_state_name,
            [SectionType.FACTS, SectionType.CONCLUSIONS]
        ) 