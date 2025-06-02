import json
import time

import pytest

from fastagent.fsa.context.context_item import ContextCategory, ContextItem, ExpirationPolicy
from fastagent.fsa.context.state_context import StateContext


class TestStateContext:
    def test_init(self):
        context = StateContext(session_id="test_session", user_id="test_user")
        assert context.session_id == "test_session"
        assert context.user_id == "test_user"
        assert context.current_state is None
        assert context.prev_state is None

        # Check standard categories were initialized
        assert "salient" in context.categories
        assert "history" in context.categories
        assert "session" in context.categories
        assert "state_data" in context.categories

    def test_add_category(self):
        context = StateContext(session_id="test_session")

        # Add new category with constructor args
        category = context.add_category(
            name="custom_category", description="A custom category", priority_weight=0.7
        )

        assert "custom_category" in context.categories
        assert context.categories["custom_category"] == category
        assert category.description == "A custom category"
        assert category.priority_weight == 0.7

        # Add existing category instance
        new_category = ContextCategory(name="another_category")
        added_category = context.add_category("another_category", new_category)
        assert added_category == new_category
        assert context.categories["another_category"] == new_category

        # Test duplicate category error
        with pytest.raises(ValueError):
            context.add_category("custom_category")

    def test_get_category(self):
        context = StateContext(session_id="test_session")

        # Get existing category
        salient_category = context.get_category("salient")
        assert salient_category.name == "salient"

        # Get non-existent category (should create it)
        custom_category = context.get_category("custom")
        assert custom_category.name == "custom"
        assert "custom" in context.categories

    def test_add_to_category(self):
        context = StateContext(session_id="test_session")

        # Add raw content
        item = context.add_to_category("salient", "test content")
        assert item.content == "test content"
        assert item in context.categories["salient"].items

        # Add context item
        context_item = ContextItem(content="item content", source="test")
        added_item = context.add_to_category("history", context_item)
        assert added_item == context_item
        assert context_item in context.categories["history"].items

    def test_add_salient(self):
        context = StateContext(session_id="test_session")
        item = context.add_salient("salient info")
        assert item.content == "salient info"
        assert item in context.categories["salient"].items

    def test_add_history(self):
        context = StateContext(session_id="test_session")
        item = context.add_history("history item")
        assert item.content == "history item"
        assert item in context.categories["history"].items

    def test_add_session_data(self):
        context = StateContext(session_id="test_session")
        item = context.add_session_data("key1", "value1")

        assert item.content == {"key": "key1", "value": "value1"}
        assert item in context.categories["session"].items

    def test_add_state_data(self):
        context = StateContext(session_id="test_session")

        # Test with explicit state
        item1 = context.add_state_data("key1", "value1", state_name="state1")
        assert item1.content == {"key": "key1", "value": "value1"}
        assert "state_state1" in context.categories
        assert item1 in context.categories["state_state1"].items

        # Set current state and use default
        context.current_state = "current_state"
        item2 = context.add_state_data("key2", "value2")
        assert item2.content == {"key": "key2", "value": "value2"}
        assert "state_current_state" in context.categories
        assert item2 in context.categories["state_current_state"].items

        # Test with no current state (should use "global")
        context.current_state = None
        item3 = context.add_state_data("key3", "value3")
        assert "state_global" in context.categories
        assert item3 in context.categories["state_global"].items

    def test_get_all_items(self):
        context = StateContext(session_id="test_session")

        # Add items with different relevance scores
        item1 = ContextItem(content="low", relevance_score=0.2)
        item2 = ContextItem(content="medium", relevance_score=0.5)
        item3 = ContextItem(content="high", relevance_score=0.8)

        context.add_to_category("category1", item1)
        context.add_to_category("category2", item2)
        context.add_to_category("category3", item3)

        # Test with default min_relevance
        all_items = context.get_all_items()
        assert len(all_items) == 3
        assert all_items[0] == item3  # Should be sorted by relevance (highest first)
        assert all_items[1] == item2
        assert all_items[2] == item1

        # Test with min_relevance filter
        filtered_items = context.get_all_items(min_relevance=0.5)
        assert len(filtered_items) == 2
        assert filtered_items[0] == item3
        assert filtered_items[1] == item2

    def test_get_all_by_category(self):
        context = StateContext(session_id="test_session")

        # Add items to different categories
        item1 = context.add_to_category("category1", "item1")
        item2 = context.add_to_category("category1", "item2")
        item3 = context.add_to_category("category2", "item3")

        result = context.get_all_by_category()
        assert set(result.keys()) >= {"category1", "category2"}
        assert result["category1"] == [item1, item2]
        assert result["category2"] == [item3]

    def test_on_state_transition(self):
        context = StateContext(session_id="test_session")

        # Add items with different expiration policies
        never_expire = ContextItem(
            content="never expires", expiration_policy=ExpirationPolicy.NEVER
        )

        after_transition = ContextItem(
            content="expires after transition",
            expiration_policy=ExpirationPolicy.AFTER_TRANSITION,
        )

        context.add_to_category("category1", never_expire)
        context.add_to_category("category1", after_transition)

        # Verify both items exist
        assert len(context.categories["category1"].items) == 2

        # Perform state transition
        context.on_state_transition("state1", "state2")

        # Check state was updated
        assert context.prev_state == "state1"
        assert context.current_state == "state2"

        # The AFTER_TRANSITION item should be removed
        assert len(context.categories["category1"].items) == 1
        assert context.categories["category1"].items[0] == never_expire

    def test_to_dict(self):
        context = StateContext(session_id="test_session", user_id="test_user")
        context.current_state = "current"
        context.prev_state = "previous"

        # Add some items
        context.add_salient("salient info")
        context.add_session_data("user_name", "John Doe")

        result = context.to_dict()

        assert result["session_id"] == "test_session"
        assert result["user_id"] == "test_user"
        assert result["current_state"] == "current"
        assert result["prev_state"] == "previous"
        assert "categories" in result
        assert "salient" in result["categories"]
        assert "session" in result["categories"]

        # Check items in categories
        assert len(result["categories"]["salient"]["items"]) == 1
        assert result["categories"]["salient"]["items"][0]["content"] == "salient info"

        assert len(result["categories"]["session"]["items"]) == 1
        assert result["categories"]["session"]["items"][0]["content"] == {
            "key": "user_name",
            "value": "John Doe",
        }

    def test_to_json(self):
        context = StateContext(session_id="test_session")
        context.add_salient("test content")

        # Convert to JSON
        json_str = context.to_json()

        # Parse and validate
        parsed = json.loads(json_str)
        assert parsed["session_id"] == "test_session"
        assert "categories" in parsed
        assert "salient" in parsed["categories"]

    def test_from_dict(self):
        # Create a dictionary representation
        data = {
            "session_id": "test_session",
            "user_id": "test_user",
            "current_state": "current",
            "prev_state": "previous",
            "categories": {
                "custom": {
                    "description": "Custom category",
                    "priority_weight": 0.6,
                    "items": [
                        {
                            "content": "test content",
                            "source": "test source",
                            "timestamp": time.time(),
                            "confidence": 0.9,
                            "relevance_score": 0.7,
                            "metadata": {"key": "value"},
                        }
                    ],
                }
            },
        }

        # Create context from dictionary
        context = StateContext.from_dict(data)

        # Verify context properties
        assert context.session_id == "test_session"
        assert context.user_id == "test_user"
        assert context.current_state == "current"
        assert context.prev_state == "previous"

        # Verify categories and items
        assert "custom" in context.categories
        custom_category = context.categories["custom"]
        assert custom_category.description == "Custom category"
        assert custom_category.priority_weight == 0.6
        assert len(custom_category.items) == 1

        item = custom_category.items[0]
        assert item.content == "test content"
        assert item.source == "test source"
        assert item.confidence == 0.9
        assert item.relevance_score == 0.7
        assert item.metadata == {"key": "value"}
