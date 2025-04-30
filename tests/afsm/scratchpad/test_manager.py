"""
Unit tests for ScratchpadManager class.
"""

import os
import uuid
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from fastagent.afsm.scratchpad.manager import ScratchpadManager
from fastagent.afsm.scratchpad.content import ScratchpadContent
from fastagent.afsm.scratchpad.section import SectionType, ReasoningSection


class TestScratchpadManager:
    """Test suite for ScratchpadManager class."""

    def test_init(self):
        """Test initialization of ScratchpadManager."""
        # Test without storage directory
        manager = ScratchpadManager()
        assert manager.storage_dir is None
        assert manager.scratchpads == {}
        assert manager.sections == {}
        assert manager.active_scratchpad_id is None
        
        # Test with storage directory
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            storage_dir = Path("/test/storage")
            manager = ScratchpadManager(storage_dir=storage_dir)
            assert manager.storage_dir == storage_dir
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_create_scratchpad(self):
        """Test creating a new scratchpad."""
        manager = ScratchpadManager()
        
        # Test with default name
        with patch('uuid.uuid4', return_value=uuid.UUID('12345678-1234-5678-1234-567812345678')):
            pad_id = manager.create_scratchpad()
            assert pad_id == '12345678-1234-5678-1234-567812345678'
            assert pad_id in manager.scratchpads
            assert pad_id in manager.sections
            assert manager.scratchpads[pad_id].name == 'scratchpad_12345678'
            
            # Should be set as active if no active scratchpad exists
            assert manager.active_scratchpad_id == pad_id
        
        # Test with custom name
        custom_name = "test_pad"
        pad_id = manager.create_scratchpad(name=custom_name)
        assert pad_id in manager.scratchpads
        assert manager.scratchpads[pad_id].name == custom_name
        
        # First pad should still be active
        assert manager.active_scratchpad_id != pad_id

    def test_set_active_scratchpad(self):
        """Test setting the active scratchpad."""
        manager = ScratchpadManager()
        pad_id1 = manager.create_scratchpad(name="pad1")
        pad_id2 = manager.create_scratchpad(name="pad2")
        
        # Set second pad as active
        manager.set_active_scratchpad(pad_id2)
        assert manager.active_scratchpad_id == pad_id2
        
        # Set first pad as active
        manager.set_active_scratchpad(pad_id1)
        assert manager.active_scratchpad_id == pad_id1
        
        # Test with nonexistent pad ID
        with pytest.raises(ValueError, match="does not exist"):
            manager.set_active_scratchpad("nonexistent_id")

    def test_get_active_scratchpad(self):
        """Test getting the active scratchpad."""
        manager = ScratchpadManager()
        
        # No active scratchpad
        manager.active_scratchpad_id = None
        assert manager.get_active_scratchpad() is None
        
        # With active scratchpad
        pad_id = manager.create_scratchpad()
        assert manager.get_active_scratchpad() == manager.scratchpads[pad_id]

    def test_write(self):
        """Test writing to the active scratchpad."""
        manager = ScratchpadManager()
        
        # Test with no active scratchpad
        manager.active_scratchpad_id = None
        with pytest.raises(ValueError, match="No active scratchpad"):
            manager.write("Test content")
        
        # Test with active scratchpad
        pad_id = manager.create_scratchpad()
        manager.write("Test content")
        manager.write("More content", {"metadata": "value"})
        
        # Verify content was written
        pad = manager.scratchpads[pad_id]
        assert len(pad.entries) == 2
        assert pad.entries[0].content == "Test content"
        assert pad.entries[1].content == "More content"
        assert pad.entries[1].metadata == {"metadata": "value"}

    def test_read(self):
        """Test reading from a scratchpad."""
        manager = ScratchpadManager()
        
        # Test with no active scratchpad
        with pytest.raises(ValueError, match="No active scratchpad"):
            manager.read()
        
        # Create and write to scratchpad
        pad_id = manager.create_scratchpad()
        manager.write("Line 1")
        manager.write("Line 2")
        manager.write("Line 3")
        
        # Test reading all content
        content = manager.read()
        assert content == "Line 1\nLine 2\nLine 3"
        
        # Test reading with explicit pad ID
        content = manager.read(pad_id=pad_id)
        assert content == "Line 1\nLine 2\nLine 3"
        
        # Test reading last N entries
        content = manager.read(last_n=2)
        assert content == "Line 2\nLine 3"
        
        # Test with nonexistent pad ID
        with pytest.raises(ValueError, match="does not exist"):
            manager.read(pad_id="nonexistent_id")

    def test_create_section(self):
        """Test creating a new reasoning section."""
        manager = ScratchpadManager()
        
        # Test with no active scratchpad
        with pytest.raises(ValueError, match="No active scratchpad"):
            manager.create_section(SectionType.FACTS)
        
        # Create a scratchpad and section
        pad_id = manager.create_scratchpad()
        section_name = manager.create_section(SectionType.FACTS)
        
        # Verify section was created
        assert section_name == SectionType.FACTS.value
        assert section_name in manager.sections[pad_id]
        assert isinstance(manager.sections[pad_id][section_name], ReasoningSection)
        assert manager.sections[pad_id][section_name].section_type == SectionType.FACTS
        
        # Test with custom name
        custom_name = "important_facts"
        section_name = manager.create_section(SectionType.FACTS, name=custom_name)
        assert section_name == custom_name
        assert custom_name in manager.sections[pad_id]
        
        # Test with explicit pad ID
        pad_id2 = manager.create_scratchpad()
        section_name = manager.create_section(SectionType.HYPOTHESES, pad_id=pad_id2)
        assert section_name in manager.sections[pad_id2]
        
        # Test creating a section that already exists (should return existing name)
        existing_name = manager.create_section(SectionType.FACTS, name=custom_name)
        assert existing_name == custom_name

    def test_get_section(self):
        """Test getting a reasoning section."""
        manager = ScratchpadManager()
        
        # Test with no active scratchpad
        with pytest.raises(ValueError, match="No active scratchpad"):
            manager.get_section("facts")
        
        # Create a scratchpad and sections
        pad_id = manager.create_scratchpad()
        facts_name = manager.create_section(SectionType.FACTS)
        hypo_name = manager.create_section(SectionType.HYPOTHESES)
        
        # Test getting sections
        facts_section = manager.get_section(facts_name)
        assert isinstance(facts_section, ReasoningSection)
        assert facts_section.section_type == SectionType.FACTS
        
        hypo_section = manager.get_section(hypo_name)
        assert hypo_section.section_type == SectionType.HYPOTHESES
        
        # Test with explicit pad ID
        pad_id2 = manager.create_scratchpad()
        calc_name = manager.create_section(SectionType.CALCULATIONS, pad_id=pad_id2)
        calc_section = manager.get_section(calc_name, pad_id=pad_id2)
        assert calc_section.section_type == SectionType.CALCULATIONS
        
        # Test with nonexistent section
        with pytest.raises(ValueError, match="does not exist in scratchpad"):
            manager.get_section("nonexistent_section")
        
        # Test with nonexistent pad ID
        with pytest.raises(ValueError, match="does not exist"):
            manager.get_section(facts_name, pad_id="nonexistent_id")

    def test_write_to_section(self):
        """Test writing to a specific reasoning section."""
        manager = ScratchpadManager()
        pad_id = manager.create_scratchpad()
        facts_name = manager.create_section(SectionType.FACTS)
        
        # Write to section
        entry_id = manager.write_to_section(facts_name, "This is a fact")
        assert isinstance(entry_id, str)
        
        # Verify content was written
        section = manager.get_section(facts_name)
        assert len(section.content.entries) == 1
        assert section.content.entries[0].content == "This is a fact"
        
        # Write with metadata
        metadata = {"confidence": 0.9}
        entry_id = manager.write_to_section(facts_name, "Another fact", metadata)
        assert section.content.entries[1].metadata == metadata
        
        # Write to explicit pad ID
        pad_id2 = manager.create_scratchpad()
        hypo_name = manager.create_section(SectionType.HYPOTHESES, pad_id=pad_id2)
        entry_id = manager.write_to_section(hypo_name, "A hypothesis", pad_id=pad_id2)
        section2 = manager.get_section(hypo_name, pad_id=pad_id2)
        assert len(section2.content.entries) == 1

    def test_get_all_sections(self):
        """Test getting all sections for a scratchpad."""
        manager = ScratchpadManager()
        
        # Test with no active scratchpad
        with pytest.raises(ValueError, match="No active scratchpad"):
            manager.get_all_sections()
        
        # Create a scratchpad and sections
        pad_id = manager.create_scratchpad()
        facts_name = manager.create_section(SectionType.FACTS)
        hypo_name = manager.create_section(SectionType.HYPOTHESES)
        
        # Get all sections
        sections = manager.get_all_sections()
        assert len(sections) == 2
        assert facts_name in sections
        assert hypo_name in sections
        assert isinstance(sections[facts_name], ReasoningSection)
        
        # Test with explicit pad ID
        pad_id2 = manager.create_scratchpad()
        calc_name = manager.create_section(SectionType.CALCULATIONS, pad_id=pad_id2)
        sections = manager.get_all_sections(pad_id=pad_id2)
        assert len(sections) == 1
        assert calc_name in sections
        
        # Test with nonexistent pad ID
        with pytest.raises(ValueError, match="does not exist"):
            manager.get_all_sections(pad_id="nonexistent_id")

    @patch('json.dump')
    @patch('builtins.open', new_callable=mock_open)
    def test_persist(self, mock_file, mock_json_dump):
        """Test persisting a scratchpad to storage."""
        # Create manager with storage dir
        with patch('pathlib.Path.mkdir'):
            manager = ScratchpadManager(storage_dir=Path("/test/storage"))
        
        # Create and populate a scratchpad
        pad_id = manager.create_scratchpad(name="test_pad")
        manager.write("Test content")
        manager.create_section(SectionType.FACTS)
        manager.write_to_section("facts", "This is a fact")
        
        # Test persist with storage_dir
        result = manager.persist(pad_id)
        assert result is True
        mock_file.assert_called()
        mock_json_dump.assert_called()
        
        # Test persist without storage_dir
        manager.storage_dir = None
        result = manager.persist(pad_id)
        assert result is False
        
        # Test with nonexistent pad ID
        with pytest.raises(ValueError, match="does not exist"):
            manager.persist("nonexistent_id")

    @patch('json.load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists', return_value=True)
    def test_load(self, mock_exists, mock_file, mock_json_load):
        """Test loading a scratchpad from storage."""
        # Mock JSON data for loading
        mock_json_load.return_value = {
            "name": "loaded_pad",
            "entries": [
                {"content": "Loaded content", "timestamp": 1234567890.0, "metadata": {}}
            ],
            "metadata": {"source": "test"},
            "sections": {
                "facts": {
                    "type": "facts",
                    "name": "facts",
                    "entries": [
                        {"content": "Loaded fact", "timestamp": 1234567891.0, "metadata": {}}
                    ],
                    "references": {}
                }
            }
        }
        
        # Create manager with storage dir
        with patch('pathlib.Path.mkdir'):
            manager = ScratchpadManager(storage_dir=Path("/test/storage"))
        
        # Test load
        pad_id = "test_id"
        result = manager.load(pad_id)
        assert result is True
        assert pad_id in manager.scratchpads
        assert pad_id in manager.sections
        assert manager.scratchpads[pad_id].name == "loaded_pad"
        assert "facts" in manager.sections[pad_id]
        
        # Test load without storage_dir
        manager.storage_dir = None
        result = manager.load("another_id")
        assert result is False
        
        # Test load with file not found
        mock_exists.return_value = False
        manager.storage_dir = Path("/test/storage")  # Restore storage_dir
        result = manager.load("nonexistent_id")
        assert result is False

    @patch('pathlib.Path.unlink')
    @patch('pathlib.Path.exists', return_value=True)
    def test_delete(self, mock_exists, mock_unlink):
        """Test deleting a scratchpad."""
        # Create manager with storage dir
        with patch('pathlib.Path.mkdir'):
            manager = ScratchpadManager(storage_dir=Path("/test/storage"))
        
        # Create scratchpads
        pad_id1 = manager.create_scratchpad(name="pad1")
        pad_id2 = manager.create_scratchpad(name="pad2")
        manager.set_active_scratchpad(pad_id1)
        
        # Test delete
        result = manager.delete(pad_id2)
        assert result is True
        assert pad_id2 not in manager.scratchpads
        assert pad_id2 not in manager.sections
        mock_unlink.assert_called_once()
        
        # Reset the mock to clear the call count
        mock_unlink.reset_mock()
        
        # Test delete active scratchpad
        result = manager.delete(pad_id1)
        assert result is True
        assert pad_id1 not in manager.scratchpads
        assert pad_id1 not in manager.sections
        assert manager.active_scratchpad_id is None
        mock_unlink.assert_called_once()
        
        # Reset the mock again
        mock_unlink.reset_mock()
        
        # Test delete without storage_dir
        manager.storage_dir = None
        pad_id3 = manager.create_scratchpad()
        result = manager.delete(pad_id3)
        assert result is True
        mock_unlink.assert_not_called()
        
        # Test delete nonexistent pad
        with pytest.raises(ValueError, match="does not exist"):
            manager.delete("nonexistent_id") 