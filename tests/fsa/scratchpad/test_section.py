"""
Unit tests for ReasoningSection class.
"""

import pytest

from opusagent.fsa.scratchpad.section import ReasoningSection, SectionType


class TestReasoningSection:
    """Test suite for ReasoningSection class."""

    def test_init(self):
        """Test initialization of ReasoningSection."""
        section = ReasoningSection(SectionType.FACTS)
        
        assert section.section_type == SectionType.FACTS
        assert section.name == SectionType.FACTS.value
        assert section.references == {}
        assert section.content is not None

    def test_init_with_custom_name(self):
        """Test initialization with a custom name."""
        section = ReasoningSection(SectionType.FACTS, name="important_facts")
        
        assert section.section_type == SectionType.FACTS
        assert section.name == "important_facts"

    def test_add(self):
        """Test adding content to the section."""
        section = ReasoningSection(SectionType.HYPOTHESES)
        entry_id = section.add("Test hypothesis")
        
        # Check if entry was added to content
        assert len(section.content.entries) == 1
        assert section.content.entries[0].content == "Test hypothesis"
        
        # Check if entry ID was created and tracked in references
        assert entry_id in section.references
        assert isinstance(entry_id, str)
        assert section.references[entry_id] == set()

    def test_add_with_metadata(self):
        """Test adding content with metadata."""
        section = ReasoningSection(SectionType.CALCULATIONS)
        metadata = {"confidence": 0.8, "source": "calculation"}
        entry_id = section.add("2 + 2 = 4", metadata)
        
        assert section.content.entries[0].content == "2 + 2 = 4"
        assert section.content.entries[0].metadata == metadata

    def test_relate(self):
        """Test establishing relationships between entries."""
        section = ReasoningSection(SectionType.FACTS)
        fact_id = section.add("The sky is blue")
        hypothesis_id = section.add("The sky color is due to Rayleigh scattering")
        
        # Relate hypothesis to fact
        section.relate(hypothesis_id, fact_id)
        
        # Check if relationship was established
        assert fact_id in section.references[hypothesis_id]

    def test_get_related(self):
        """Test getting entries related to a specified entry."""
        section = ReasoningSection(SectionType.CONCLUSIONS)
        premise1_id = section.add("Premise 1")
        premise2_id = section.add("Premise 2")
        conclusion_id = section.add("Conclusion")
        
        print(f"Premise1 ID: {premise1_id}")
        print(f"Premise2 ID: {premise2_id}")
        print(f"Conclusion ID: {conclusion_id}")
        
        # Relate the conclusion to both premises
        section.relate(conclusion_id, premise1_id)
        section.relate(conclusion_id, premise2_id)
        
        print(f"References after relating: {section.references}")
        
        # Test getting related entries
        related = section.get_related(conclusion_id)
        print(f"Related entries: {related}")
        
        assert len(related) == 2
        assert premise1_id in related
        assert premise2_id in related
        
        # Test getting related entries for entry with no relations
        assert section.get_related(premise1_id) == []

    def test_get_all_content(self):
        """Test getting all content in the section as a string."""
        section = ReasoningSection(SectionType.NOTES)
        section.add("Note 1")
        section.add("Note 2")
        section.add("Note 3")
        
        content = section.get_all_content()
        expected = "Note 1\nNote 2\nNote 3"
        assert content == expected

    def test_search(self):
        """Test searching for entries containing the query string."""
        section = ReasoningSection(SectionType.FACTS)
        section.add("The Earth orbits the Sun")
        section.add("The Moon orbits the Earth")
        section.add("Venus orbits the Sun")
        
        # Search for entries containing "Earth"
        results = section.search("Earth")
        assert len(results) == 2
        assert any(r["content"] == "The Earth orbits the Sun" for r in results)
        assert any(r["content"] == "The Moon orbits the Earth" for r in results)
        
        # Verify result structure
        for result in results:
            assert "id" in result
            assert "content" in result
            assert "metadata" in result
            assert "timestamp" in result

    def test_clear(self):
        """Test clearing all content and references."""
        section = ReasoningSection(SectionType.QUESTIONS)
        id1 = section.add("Question 1")
        id2 = section.add("Question 2")
        section.relate(id2, id1)
        
        # Verify data is present
        assert len(section.content.entries) == 2
        assert len(section.references) == 2
        
        # Clear the section
        section.clear()
        
        # Verify data is cleared
        assert len(section.content.entries) == 0
        assert len(section.references) == 0

    def test_str(self):
        """Test the __str__ method."""
        section = ReasoningSection(SectionType.HYPOTHESES)
        section.add("Hypothesis 1")
        section.add("Hypothesis 2")
        
        expected = f"ReasoningSection({SectionType.HYPOTHESES.value}, 2 entries)"
        assert str(section) == expected

    def test_all_section_types(self):
        """Test creating sections for all available section types."""
        # Create a section for each type and verify it works
        for section_type in SectionType:
            section = ReasoningSection(section_type)
            assert section.section_type == section_type
            assert section.name == section_type.value
            
            # Add some content to each
            section.add(f"Test content for {section_type.value}")
            assert len(section.content.entries) == 1

    def test_custom_section_type(self):
        """Test using the CUSTOM section type with a custom name."""
        section = ReasoningSection(SectionType.CUSTOM, name="my_custom_section")
        assert section.section_type == SectionType.CUSTOM
        assert section.name == "my_custom_section"
        
        # Should work the same as other section types
        section.add("Custom content")
        assert len(section.content.entries) == 1 