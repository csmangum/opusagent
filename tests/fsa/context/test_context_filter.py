import pytest

from opusagent.fsa.context.context_filter import ContextFilter
from opusagent.fsa.context.context_item import ContextItem, ExpirationPolicy
from opusagent.fsa.context.state_context import StateContext


class TestContextFilter:
    def test_init(self):
        # Test default initialization
        filter1 = ContextFilter()
        assert filter1.default_min_relevance == 0.3
        assert filter1.excluded_categories == {"session"}
        assert filter1.state_relevance_map == {}

        # Test custom initialization
        filter2 = ContextFilter(
            default_min_relevance=0.5, excluded_categories={"session", "custom"}
        )
        assert filter2.default_min_relevance == 0.5
        assert filter2.excluded_categories == {"session", "custom"}

    def test_set_state_relevance(self):
        filter = ContextFilter()

        # Set relevance for new state
        filter.set_state_relevance("state1", "category1", 0.2)
        assert "state1" in filter.state_relevance_map
        assert filter.state_relevance_map["state1"]["category1"] == 0.2

        # Set relevance for existing state with new category
        filter.set_state_relevance("state1", "category2", 0.3)
        assert filter.state_relevance_map["state1"]["category2"] == 0.3

        # Update existing state and category
        filter.set_state_relevance("state1", "category1", 0.4)
        assert filter.state_relevance_map["state1"]["category1"] == 0.4

    def test_get_relevance_modifier(self):
        filter = ContextFilter()

        # Set some relevance modifiers
        filter.set_state_relevance("state1", "category1", 0.2)
        filter.set_state_relevance("state1", "category2", 0.3)
        filter.set_state_relevance("state2", "category1", 0.4)

        # Test existing state and category
        assert filter.get_relevance_modifier("state1", "category1") == 0.2
        assert filter.get_relevance_modifier("state1", "category2") == 0.3
        assert filter.get_relevance_modifier("state2", "category1") == 0.4

        # Test non-existent state
        assert filter.get_relevance_modifier("state3", "category1") == 0.0

        # Test non-existent category
        assert filter.get_relevance_modifier("state1", "category3") == 0.0

    def test_filter_items(self):
        filter = ContextFilter(default_min_relevance=0.5)
        context = StateContext(session_id="test_session")

        # Add items to session category (should be excluded)
        context.add_to_category(
            "session", ContextItem(content="session item", relevance_score=0.2)
        )

        # Add items to other categories with different relevance scores
        low_item = ContextItem(content="low relevance", relevance_score=0.3)
        mid_item = ContextItem(content="mid relevance", relevance_score=0.6)
        high_item = ContextItem(content="high relevance", relevance_score=0.8)

        context.add_to_category("category1", low_item)
        context.add_to_category("category1", mid_item)
        context.add_to_category("category2", high_item)

        # Define modifiers
        filter.set_state_relevance("target_state", "category1", 0.1)

        # Filter with default min_relevance
        filtered_items = filter.filter_items(context, "target_state")

        # low_item relevance: 0.3 + 0.1 = 0.4 (below min of 0.5)
        # mid_item relevance: 0.6 + 0.1 = 0.7 (above min)
        # high_item relevance: 0.8 + 0.0 = 0.8 (above min)
        assert len(filtered_items) == 2
        assert low_item not in filtered_items
        assert mid_item in filtered_items
        assert high_item in filtered_items

        # Filter with custom min_relevance
        filtered_items = filter.filter_items(context, "target_state", min_relevance=0.7)
        assert len(filtered_items) == 2
        assert low_item not in filtered_items
        assert mid_item in filtered_items  # 0.6 + 0.1 = 0.7 (equal to min)
        assert high_item in filtered_items

    def test_apply_to_context(self):
        filter = ContextFilter()
        context = StateContext(session_id="test_session")

        # Make sure we're starting with the right state
        assert context.current_state is None
        assert context.prev_state is None

        # Add a persistent item and an expiring item
        persistent_item = context.add_to_category(
            "category1",
            ContextItem(
                content="persistent",
                expiration_policy=ExpirationPolicy.NEVER,
                relevance_score=0.6,
            ),
        )

        expiring_item = context.add_to_category(
            "category1",
            ContextItem(
                content="expiring",
                expiration_policy=ExpirationPolicy.AFTER_TRANSITION,
                relevance_score=0.6,
            ),
        )

        # Verify initial state
        assert len(context.categories["category1"].items) == 2
        assert persistent_item.relevance_score == 0.6
        assert expiring_item.relevance_score == 0.6

        # Apply the filter for a state transition
        filter.apply_to_context(context, "from_state", "to_state")

        # Check that state was updated
        assert context.current_state == "to_state"
        assert context.prev_state == "from_state"

        # Expiring item should be removed
        assert len(context.categories["category1"].items) == 1
        assert context.categories["category1"].items[0] == persistent_item

        # Persistent item should have its relevance decayed
        # Default decay is 0.9 (it loses 10% on transition)
        assert round(persistent_item.relevance_score, 2) == 0.54  # 0.6 * 0.9

    def test_update_relevance_scores(self):
        filter = ContextFilter()
        context = StateContext(session_id="test_session")

        # Add items to different categories
        item1 = context.add_to_category(
            "category1", ContextItem(content="item1", relevance_score=0.6)
        )

        item2 = context.add_to_category(
            "category2", ContextItem(content="item2", relevance_score=0.8)
        )

        # Add an item to an excluded category
        session_item = context.add_to_category(
            "session", ContextItem(content="session item", relevance_score=0.9)
        )

        # Set up relevance modifiers
        filter.set_state_relevance("target_state", "category1", 0.1)
        filter.set_state_relevance("target_state", "category2", -0.2)

        # Call the private method to update relevance scores
        filter._update_relevance_scores(context, "target_state")

        # category1 item: (0.6 * 0.9) + 0.1 = 0.64
        assert round(item1.relevance_score, 2) == 0.64

        # category2 item: (0.8 * 0.9) - 0.2 = 0.52
        assert round(item2.relevance_score, 2) == 0.52

        # session item: should be unchanged (excluded category)
        assert session_item.relevance_score == 0.9
