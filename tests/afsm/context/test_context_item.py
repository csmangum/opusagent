import time

import pytest

from app.afsm.context.context_item import ContextCategory, ContextItem, ExpirationPolicy


class TestContextItem:
    def test_create_context_item(self):
        item = ContextItem(content="test content", source="test source")
        assert item.content == "test content"
        assert item.source == "test source"
        assert item.confidence == 1.0
        assert item.relevance_score == 0.5
        assert item.expiration_policy == ExpirationPolicy.NEVER
        assert item.expiration_time is None
        assert item.metadata == {}

    def test_context_item_with_metadata(self):
        metadata = {"key": "value", "another_key": 123}
        item = ContextItem(content="test", source="test", metadata=metadata)
        assert item.metadata == metadata

    def test_is_expired_never(self):
        item = ContextItem(content="test", expiration_policy=ExpirationPolicy.NEVER)
        assert not item.is_expired()

    def test_is_expired_after_time(self):
        current_time = time.time()
        # Set expiration 1 second in the past
        item = ContextItem(
            content="test",
            expiration_policy=ExpirationPolicy.AFTER_TIME,
            expiration_time=current_time - 1,
        )
        assert item.is_expired(current_time)

        # Set expiration 10 seconds in the future
        item = ContextItem(
            content="test",
            expiration_policy=ExpirationPolicy.AFTER_TIME,
            expiration_time=current_time + 10,
        )
        assert not item.is_expired(current_time)

    def test_is_expired_missing_time(self):
        item = ContextItem(
            content="test",
            expiration_policy=ExpirationPolicy.AFTER_TIME,
            expiration_time=None,
        )
        assert not item.is_expired()

    def test_update_relevance(self):
        item = ContextItem(content="test")
        assert item.relevance_score == 0.5
        item.update_relevance(0.8)
        assert item.relevance_score == 0.8


class TestContextCategory:
    def test_create_category(self):
        category = ContextCategory(
            name="test_category",
            description="Test description",
            priority_weight=0.7,
            max_items=5,
        )
        assert category.name == "test_category"
        assert category.description == "Test description"
        assert category.priority_weight == 0.7
        assert category.max_items == 5
        assert category.items == []
        assert category.default_expiration == ExpirationPolicy.NEVER

    def test_add_raw_content(self):
        category = ContextCategory(name="test_category", priority_weight=0.6)
        item = category.add_item("raw content")

        assert len(category.items) == 1
        assert category.items[0] == item
        assert item.content == "raw content"
        assert item.source == "test_category"
        assert item.relevance_score == 0.6
        assert item.expiration_policy == ExpirationPolicy.NEVER

    def test_add_context_item(self):
        category = ContextCategory(name="test_category")
        context_item = ContextItem(content="test content", source="original source")
        item = category.add_item(context_item)

        assert len(category.items) == 1
        assert category.items[0] == item
        assert item == context_item
        assert item.source == "original source"  # Source shouldn't change

    def test_max_items_limit(self):
        category = ContextCategory(name="test_category", max_items=3)
        item1 = category.add_item("item1")
        item2 = category.add_item("item2")
        item3 = category.add_item("item3")
        item4 = category.add_item("item4")

        assert len(category.items) == 3
        assert item1 not in category.items  # Oldest item removed
        assert item2 in category.items
        assert item3 in category.items
        assert item4 in category.items

    def test_get_items_relevance_filter(self):
        category = ContextCategory(name="test_category")
        item1 = ContextItem(content="low relevance", relevance_score=0.2)
        item2 = ContextItem(content="medium relevance", relevance_score=0.5)
        item3 = ContextItem(content="high relevance", relevance_score=0.8)

        category.add_item(item1)
        category.add_item(item2)
        category.add_item(item3)

        filtered_items = category.get_items(min_relevance=0.5)
        assert len(filtered_items) == 2
        assert item1 not in filtered_items
        assert item2 in filtered_items
        assert item3 in filtered_items

    def test_clear(self):
        category = ContextCategory(name="test_category")
        category.add_item("item1")
        category.add_item("item2")
        assert len(category.items) == 2

        category.clear()
        assert len(category.items) == 0

    def test_prune_expired(self):
        category = ContextCategory(name="test_category")
        current_time = time.time()

        # Add non-expiring item
        item1 = ContextItem(
            content="never expires", expiration_policy=ExpirationPolicy.NEVER
        )

        # Add expired item
        item2 = ContextItem(
            content="expired",
            expiration_policy=ExpirationPolicy.AFTER_TIME,
            expiration_time=current_time - 10,
        )

        # Add non-expired item
        item3 = ContextItem(
            content="not expired yet",
            expiration_policy=ExpirationPolicy.AFTER_TIME,
            expiration_time=current_time + 10,
        )

        category.add_item(item1)
        category.add_item(item2)
        category.add_item(item3)
        assert len(category.items) == 3

        removed = category.prune_expired()
        assert removed == 1
        assert len(category.items) == 2
        assert item1 in category.items
        assert item2 not in category.items
        assert item3 in category.items
