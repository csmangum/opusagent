"""
Unit tests for opusagent.mock.realtime.__init__ module.
"""

import pytest
from unittest.mock import patch

from opusagent.local.realtime import (
    LocalRealtimeClient,
    LocalResponseConfig,
    ResponseSelectionCriteria,
    ConversationContext,
    __version__
)


class TestModuleImports:
    """Test module imports and exports."""

    def test_version_export(self):
        """Test that version is properly exported."""
        assert __version__ == "3.0.0"

    def test_local_realtime_client_import(self):
        """Test LocalRealtimeClient import."""
        from opusagent.local.realtime import LocalRealtimeClient
        assert LocalRealtimeClient is not None
        assert hasattr(LocalRealtimeClient, '__init__')

    def test_local_response_config_import(self):
        """Test LocalResponseConfig import."""
        from opusagent.local.realtime import LocalResponseConfig
        assert LocalResponseConfig is not None
        assert hasattr(LocalResponseConfig, '__init__')

    def test_response_selection_criteria_import(self):
        """Test ResponseSelectionCriteria import."""
        from opusagent.local.realtime import ResponseSelectionCriteria
        assert ResponseSelectionCriteria is not None
        assert hasattr(ResponseSelectionCriteria, '__init__')

    def test_conversation_context_import(self):
        """Test ConversationContext import."""
        from opusagent.local.realtime import ConversationContext
        assert ConversationContext is not None
        assert hasattr(ConversationContext, '__init__')

    def test_all_exports(self):
        """Test that all expected exports are available."""
        from opusagent.local.realtime import __all__
        
        expected_exports = [
            "LocalRealtimeClient",
            "LocalResponseConfig", 
            "ResponseSelectionCriteria",
            "ConversationContext"
        ]
        
        for export in expected_exports:
            assert export in __all__

    def test_import_all(self):
        """Test importing all exported items."""
        # This should not raise any import errors
        # Note: Wildcard imports are generally discouraged, but we test them here
        # for completeness of the module interface
        import opusagent.local.realtime as realtime_module
        
        # Verify that all expected classes are available in the module
        assert hasattr(realtime_module, 'LocalRealtimeClient')
        assert hasattr(realtime_module, 'LocalResponseConfig')
        assert hasattr(realtime_module, 'ResponseSelectionCriteria')
        assert hasattr(realtime_module, 'ConversationContext')


class TestModuleFunctionality:
    """Test module functionality and integration."""

    def test_local_realtime_client_creation(self):
        """Test that LocalRealtimeClient can be created."""
        client = LocalRealtimeClient()
        assert client is not None
        assert hasattr(client, 'logger')
        assert hasattr(client, 'session_config')
        assert hasattr(client, 'response_configs')

    def test_local_response_config_creation(self):
        """Test that LocalResponseConfig can be created."""
        config = LocalResponseConfig(
            text="Test response",
            delay_seconds=0.05
        )
        assert config is not None
        assert config.text == "Test response"
        assert config.delay_seconds == 0.05

    def test_response_selection_criteria_creation(self):
        """Test that ResponseSelectionCriteria can be created."""
        criteria = ResponseSelectionCriteria(
            required_keywords=["hello", "hi"],
            priority=15
        )
        assert criteria is not None
        assert criteria.required_keywords == ["hello", "hi"]
        assert criteria.priority == 15

    def test_conversation_context_creation(self):
        """Test that ConversationContext can be created."""
        context = ConversationContext(
            session_id="test_session",
            conversation_id="test_conversation"
        )
        assert context is not None
        assert context.session_id == "test_session"
        assert context.conversation_id == "test_conversation"

    def test_integration_example(self):
        """Test integration example from module docstring."""
        # Create a mock client with smart response selection
        client = LocalRealtimeClient()
        
        # Add context-aware response configuration
        client.add_response_config(
            "greeting",
            LocalResponseConfig(
                text="Hello! How can I help you?",
                audio_file="demo/audio/greeting.wav",
                selection_criteria=ResponseSelectionCriteria(
                    required_keywords=["hello", "hi"],
                    max_turn_count=1,
                    priority=10
                )
            )
        )
        
        # Set up conversation context
        client.update_conversation_context("Hello there!")
        
        # Access session state
        session_state = client.get_session_state()
        audio_buffer = client.get_audio_buffer()
        
        # Verify the integration works
        assert session_state is not None
        assert isinstance(audio_buffer, list)
        assert "greeting" in client.response_configs

    def test_module_docstring(self):
        """Test that module has proper docstring."""
        import opusagent.local.realtime as realtime_module
        
        assert realtime_module.__doc__ is not None
        assert "LocalRealtime Module" in realtime_module.__doc__
        assert "OpenAI Realtime API Simulator" in realtime_module.__doc__

    def test_module_structure(self):
        """Test that module has proper structure."""
        import opusagent.local.realtime as realtime_module
        
        # Check for required attributes
        assert hasattr(realtime_module, '__version__')
        assert hasattr(realtime_module, '__all__')
        assert hasattr(realtime_module, 'LocalRealtimeClient')
        assert hasattr(realtime_module, 'LocalResponseConfig')
        assert hasattr(realtime_module, 'ResponseSelectionCriteria')
        assert hasattr(realtime_module, 'ConversationContext')

    def test_version_format(self):
        """Test that version follows semantic versioning."""
        import re
        
        # Version should follow semantic versioning (x.y.z)
        version_pattern = r'^\d+\.\d+\.\d+$'
        assert re.match(version_pattern, __version__), f"Version {__version__} should follow semantic versioning"

    def test_import_performance(self):
        """Test that imports are reasonably fast."""
        import time
        
        start_time = time.time()
        from opusagent.local.realtime import (
            LocalRealtimeClient,
            LocalResponseConfig,
            ResponseSelectionCriteria,
            ConversationContext
        )
        end_time = time.time()
        
        # Import should take less than 1 second
        assert end_time - start_time < 1.0

    def test_circular_imports(self):
        """Test that there are no circular import issues."""
        # This should not raise any import errors
        try:
            from opusagent.local.realtime import (
                LocalRealtimeClient,
                LocalResponseConfig,
                ResponseSelectionCriteria,
                ConversationContext
            )
        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")

    def test_backward_compatibility(self):
        """Test that the module maintains backward compatibility."""
        # All the main classes should be importable
        from opusagent.local.realtime import LocalRealtimeClient
        from opusagent.local.realtime import LocalResponseConfig
        from opusagent.local.realtime import ResponseSelectionCriteria
        from opusagent.local.realtime import ConversationContext
        
        # All classes should be callable (constructors work)
        client = LocalRealtimeClient()
        config = LocalResponseConfig()
        criteria = ResponseSelectionCriteria()
        context = ConversationContext(session_id="test", conversation_id="test")
        
        assert all([client, config, criteria, context])

    def test_module_attributes(self):
        """Test that module has correct attributes."""
        import opusagent.local.realtime as realtime_module
        
        # Check that __all__ contains the right exports
        expected_exports = [
            "LocalRealtimeClient",
            "LocalResponseConfig",
            "ResponseSelectionCriteria", 
            "ConversationContext"
        ]
        
        for export in expected_exports:
            assert export in realtime_module.__all__
            assert hasattr(realtime_module, export)

    def test_class_relationships(self):
        """Test that classes can work together properly."""
        # Create a conversation context
        context = ConversationContext(
            session_id="test_session",
            conversation_id="test_conversation"
        )
        
        # Create selection criteria
        criteria = ResponseSelectionCriteria(
            required_keywords=["hello"],
            priority=10
        )
        
        # Create response config using the criteria
        config = LocalResponseConfig(
            text="Hello!",
            selection_criteria=criteria
        )
        
        # Create client and add the config
        client = LocalRealtimeClient()
        client.add_response_config("greeting", config)
        
        # Update context with user input
        client.update_conversation_context("Hello there!")
        
        # Verify everything works together
        assert client.response_configs["greeting"] == config
        assert config.selection_criteria == criteria
        assert context.session_id == "test_session"

    def test_error_handling(self):
        """Test that the module handles errors gracefully."""
        # Test with invalid parameters - these should raise appropriate exceptions
        with pytest.raises(Exception):
            context = ConversationContext(
                session_id="",  # Empty string might cause issues
                conversation_id="test"
            )

    def test_documentation_consistency(self):
        """Test that module documentation is consistent."""
        import opusagent.local.realtime as realtime_module
        
        # Check that all exported classes have docstrings
        for export in realtime_module.__all__:
            class_obj = getattr(realtime_module, export)
            assert class_obj.__doc__ is not None, f"{export} should have a docstring"
            assert len(class_obj.__doc__.strip()) > 0, f"{export} should have a non-empty docstring" 