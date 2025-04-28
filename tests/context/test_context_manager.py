import pytest
import os
import json
import tempfile
import shutil
from app.context.context_manager import ContextManager
from app.context.state_context import StateContext
from app.context.context_item import ContextItem


class TestContextManager:
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing file storage"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_init(self):
        # Test default initialization
        manager = ContextManager()
        assert manager.contexts == {}
        assert manager.storage_dir is None
        assert manager.context_filter.default_min_relevance == 0.3
        
        # Test with custom parameters
        manager = ContextManager(
            storage_dir="/tmp/test",
            default_min_relevance=0.5
        )
        assert manager.storage_dir == "/tmp/test"
        assert manager.context_filter.default_min_relevance == 0.5

    def test_create_context(self):
        manager = ContextManager()
        
        # Create without user_id
        context1 = manager.create_context()
        assert isinstance(context1, StateContext)
        assert context1.user_id is None
        assert context1.session_id in manager.contexts
        assert manager.contexts[context1.session_id] == context1
        
        # Create with user_id
        context2 = manager.create_context(user_id="test_user")
        assert context2.user_id == "test_user"
        assert context2.session_id in manager.contexts
        assert context2.session_id != context1.session_id
    
    def test_get_context(self):
        manager = ContextManager()
        
        # Test getting non-existent context
        assert manager.get_context("non_existent") is None
        
        # Create and retrieve context
        context = manager.create_context()
        retrieved = manager.get_context(context.session_id)
        assert retrieved == context
    
    def test_get_or_create_context(self):
        manager = ContextManager()
        
        # Test creating new context
        session_id = "test_session"
        context1 = manager.get_or_create_context(session_id, user_id="test_user")
        assert context1.session_id == session_id
        assert context1.user_id == "test_user"
        assert session_id in manager.contexts
        
        # Test retrieving existing context
        context2 = manager.get_or_create_context(session_id)
        assert context2 == context1
    
    def test_handle_state_transition(self, monkeypatch):
        manager = ContextManager()
        
        # Create a mock context
        context = manager.create_context()
        session_id = context.session_id
        
        # Mock the context filter's apply_to_context method
        called_with = {}
        def mock_apply(self, context, from_state, to_state):
            called_with["context"] = context
            called_with["from_state"] = from_state
            called_with["to_state"] = to_state
            context.on_state_transition(from_state, to_state)
        
        monkeypatch.setattr("app.context.context_filter.ContextFilter.apply_to_context", mock_apply)
        
        # Test with non-existent context
        result = manager.handle_state_transition("non_existent", "state1", "state2")
        assert result is None
        
        # Test with existing context
        result = manager.handle_state_transition(session_id, "state1", "state2")
        assert result == context
        assert called_with["context"] == context
        assert called_with["from_state"] == "state1"
        assert called_with["to_state"] == "state2"
        assert context.current_state == "state2"
        assert context.prev_state == "state1"
    
    def test_add_context_item(self):
        manager = ContextManager()
        
        # Create a test context
        context = manager.create_context()
        session_id = context.session_id
        
        # Test with non-existent context
        result = manager.add_context_item("non_existent", "category", "content")
        assert result is None
        
        # Test with existing context
        result = manager.add_context_item(session_id, "test_category", "test_content", {"key": "value"})
        assert isinstance(result, ContextItem)
        assert result.content == "test_content"
        assert result.source == "test_category"
        assert result.metadata == {"key": "value"}
        assert result in context.categories["test_category"].items
    
    def test_get_context_for_state(self, monkeypatch):
        manager = ContextManager()
        
        # Create a test context
        context = manager.create_context(user_id="test_user")
        session_id = context.session_id
        context.current_state = "current_state"
        context.prev_state = "prev_state"
        
        # Add various context items
        context.add_salient("salient item")
        context.add_history("history item")
        context.add_session_data("key1", "value1")
        context.add_state_data("key2", "value2", state_name="test_state")
        
        # Mock the context filter's filter_items method
        relevant_items = [
            ContextItem(content="relevant1", source="cat1", relevance_score=0.8),
            ContextItem(content="relevant2", source="cat2", relevance_score=0.7)
        ]
        
        def mock_filter_items(self, context, state_name, min_relevance=None):
            return relevant_items
        
        monkeypatch.setattr("app.context.context_filter.ContextFilter.filter_items", mock_filter_items)
        
        # Test with non-existent context
        result = manager.get_context_for_state("non_existent", "test_state")
        assert result == {}
        
        # Test with existing context
        result = manager.get_context_for_state(session_id, "test_state", min_relevance=0.5)
        
        # Check metadata in result
        assert result["session_id"] == session_id
        assert result["user_id"] == "test_user"
        assert result["current_state"] == "current_state"
        assert result["prev_state"] == "prev_state"
        
        # Check category content
        assert "salient item" in result["salient"]
        assert "history item" in result["history"]
        
        # Check session data
        assert result["session_data"] == {"key1": "value1"}
        
        # Check state-specific data
        assert "state_data" in result
        
        # Check relevant items (from mocked filter_items)
        assert len(result["relevant_items"]) == 2
        assert result["relevant_items"][0]["content"] == "relevant1"
        assert result["relevant_items"][0]["source"] == "cat1"
        assert result["relevant_items"][0]["relevance"] == 0.8
        assert result["relevant_items"][1]["content"] == "relevant2"
    
    def test_save_context(self, temp_dir):
        # Create manager with storage directory
        manager = ContextManager(storage_dir=temp_dir)
        
        # Create a test context
        context = manager.create_context(user_id="test_user")
        session_id = context.session_id
        
        # Add some data
        context.add_salient("test content")
        
        # Save the context
        result = manager.save_context(session_id)
        assert result is True
        
        # Check if file was created
        filename = os.path.join(temp_dir, f"{session_id}.json")
        assert os.path.exists(filename)
        
        # Verify file content
        with open(filename, 'r') as f:
            data = json.load(f)
            assert data["session_id"] == session_id
            assert data["user_id"] == "test_user"
            assert "categories" in data
            assert "salient" in data["categories"]
            assert data["categories"]["salient"]["items"][0]["content"] == "test content"
        
        # Test with non-existent session
        result = manager.save_context("non_existent")
        assert result is False
        
        # Test without storage directory
        manager_no_storage = ContextManager()
        result = manager_no_storage.save_context(session_id)
        assert result is False
    
    def test_load_context(self, temp_dir):
        # Create manager with storage directory
        manager = ContextManager(storage_dir=temp_dir)
        
        # Create test data
        session_id = "test_session"
        context_data = {
            "session_id": session_id,
            "user_id": "test_user",
            "current_state": "current",
            "prev_state": "previous",
            "categories": {
                "salient": {
                    "description": "Salient info",
                    "priority_weight": 0.9,
                    "items": [
                        {
                            "content": "test content",
                            "source": "test",
                            "timestamp": 1234567890,
                            "confidence": 1.0,
                            "relevance_score": 0.8,
                            "metadata": {}
                        }
                    ]
                }
            }
        }
        
        # Write test file
        filename = os.path.join(temp_dir, f"{session_id}.json")
        with open(filename, 'w') as f:
            json.dump(context_data, f)
        
        # Load the context
        loaded_context = manager.load_context(session_id)
        
        # Verify data
        assert loaded_context.session_id == session_id
        assert loaded_context.user_id == "test_user"
        assert loaded_context.current_state == "current"
        assert loaded_context.prev_state == "previous"
        assert "salient" in loaded_context.categories
        assert len(loaded_context.categories["salient"].items) == 1
        assert loaded_context.categories["salient"].items[0].content == "test content"
        
        # Test with non-existent file
        result = manager.load_context("non_existent")
        assert result is None
        
        # Test without storage directory
        manager_no_storage = ContextManager()
        result = manager_no_storage.load_context(session_id)
        assert result is None
    
    def test_end_session(self):
        manager = ContextManager()
        
        # Create a test context
        context = manager.create_context()
        session_id = context.session_id
        
        assert session_id in manager.contexts
        
        # End the session
        result = manager.end_session(session_id)
        assert result is True
        assert session_id not in manager.contexts
        
        # Test with non-existent session
        result = manager.end_session("non_existent")
        assert result is False 