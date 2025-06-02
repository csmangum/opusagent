"""
Unit tests for ScratchpadContent class.
"""

import time
import pytest
from fastagent.fsa.scratchpad.content import ScratchpadContent, Entry


class TestScratchpadContent:
    """Test suite for ScratchpadContent class."""

    def test_init(self):
        """Test initialization of ScratchpadContent."""
        content = ScratchpadContent(max_entries=100, name="test")
        assert content.name == "test"
        assert content.max_entries == 100
        assert content.entries == []
        assert content.metadata == {}

    def test_append(self):
        """Test appending entries to the scratchpad."""
        content = ScratchpadContent()
        content.append("First entry")
        assert len(content.entries) == 1
        assert content.entries[0].content == "First entry"
        assert content.entries[0].metadata == {}

    def test_append_with_metadata(self):
        """Test appending entries with metadata."""
        content = ScratchpadContent()
        metadata = {"source": "test", "importance": "high"}
        content.append("Entry with metadata", metadata)
        assert len(content.entries) == 1
        assert content.entries[0].content == "Entry with metadata"
        assert content.entries[0].metadata == metadata

    def test_max_entries_limit(self):
        """Test that the max_entries limit is enforced."""
        content = ScratchpadContent(max_entries=3)
        content.append("Entry 1")
        content.append("Entry 2")
        content.append("Entry 3")
        content.append("Entry 4")  # This should remove Entry 1
        assert len(content.entries) == 3
        assert content.entries[0].content == "Entry 2"
        assert content.entries[1].content == "Entry 3"
        assert content.entries[2].content == "Entry 4"

    def test_clear(self):
        """Test clearing all entries."""
        content = ScratchpadContent()
        content.append("Entry 1")
        content.append("Entry 2")
        assert len(content.entries) == 2
        
        content.clear()
        assert len(content.entries) == 0

    def test_get_content(self):
        """Test getting all content as a string."""
        content = ScratchpadContent()
        content.append("Entry 1")
        content.append("Entry 2")
        content.append("Entry 3")
        
        expected = "Entry 1\nEntry 2\nEntry 3"
        assert content.get_content() == expected

    def test_get_content_with_last_n(self):
        """Test getting the last N entries as a string."""
        content = ScratchpadContent()
        content.append("Entry 1")
        content.append("Entry 2")
        content.append("Entry 3")
        
        expected = "Entry 2\nEntry 3"
        assert content.get_content(last_n=2) == expected

    def test_get_entries(self):
        """Test getting all raw entries."""
        content = ScratchpadContent()
        content.append("Entry 1")
        content.append("Entry 2")
        
        entries = content.get_entries()
        assert len(entries) == 2
        assert entries[0].content == "Entry 1"
        assert entries[1].content == "Entry 2"

    def test_get_entries_with_last_n(self):
        """Test getting the last N raw entries."""
        content = ScratchpadContent()
        content.append("Entry 1")
        content.append("Entry 2")
        content.append("Entry 3")
        
        entries = content.get_entries(last_n=2)
        assert len(entries) == 2
        assert entries[0].content == "Entry 2"
        assert entries[1].content == "Entry 3"

    def test_search(self):
        """Test searching for entries containing a query string."""
        content = ScratchpadContent()
        content.append("Apple pie recipe")
        content.append("Banana bread recipe")
        content.append("Apple crumble recipe")
        
        results = content.search("Apple")
        assert len(results) == 2
        assert results[0].content == "Apple pie recipe"
        assert results[1].content == "Apple crumble recipe"
        
        # Case insensitive search
        results = content.search("apple")
        assert len(results) == 2

        # No results
        results = content.search("Orange")
        assert len(results) == 0

    def test_metadata(self):
        """Test setting and getting metadata for the entire scratchpad."""
        content = ScratchpadContent()
        
        content.set_metadata("category", "recipes")
        assert content.get_metadata("category") == "recipes"
        
        content.set_metadata("priority", "high")
        assert content.get_metadata("priority") == "high"
        
        # Test default value for missing key
        assert content.get_metadata("missing_key") is None
        assert content.get_metadata("missing_key", "default") == "default"

    def test_len(self):
        """Test the __len__ method."""
        content = ScratchpadContent()
        assert len(content) == 0
        
        content.append("Entry 1")
        content.append("Entry 2")
        assert len(content) == 2
        
        content.clear()
        assert len(content) == 0

    def test_str(self):
        """Test the __str__ method."""
        content = ScratchpadContent(name="test_pad")
        content.append("Entry 1")
        content.append("Entry 2")
        
        expected = "ScratchpadContent('test_pad', 2 entries)"
        assert str(content) == expected

    def test_timestamp(self):
        """Test that entries are timestamped correctly."""
        content = ScratchpadContent()
        before = time.time()
        content.append("Test entry")
        after = time.time()
        
        # The timestamp should be between before and after
        assert before <= content.entries[0].timestamp <= after 