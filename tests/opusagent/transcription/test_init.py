"""
Unit tests for transcription module initialization and exports.
"""
import pytest
from unittest.mock import patch, MagicMock

def test_module_imports():
    """Test that all expected classes/functions can be imported."""
    # This should not raise any ImportError
    from opusagent.local.transcription import (
        TranscriptionResult,
        TranscriptionConfig,
        TranscriptionFactory,
        load_transcription_config,
        BaseTranscriber
    )
    
    # Verify they are the correct types
    assert hasattr(TranscriptionResult, '__annotations__')  # Pydantic model
    assert hasattr(TranscriptionConfig, '__annotations__')  # Pydantic model
    assert hasattr(TranscriptionFactory, 'create_transcriber')  # Factory method
    assert callable(load_transcription_config)  # Function
    assert hasattr(BaseTranscriber, '__init__')  # Class


def test_all_exports_defined():
    """Test that __all__ is properly defined."""
    import opusagent.local.transcription as transcription_module
    
    # Check that __all__ exists and contains expected exports
    assert hasattr(transcription_module, '__all__')
    
    expected_exports = {
        "TranscriptionResult",
        "TranscriptionConfig", 
        "TranscriptionFactory",
        "load_transcription_config",
        "BaseTranscriber"
    }
    
    actual_exports = set(transcription_module.__all__)
    assert actual_exports == expected_exports


def test_public_api_functionality():
    """Test that the public API works as expected."""
    from opusagent.local.transcription import (
        TranscriptionResult,
        TranscriptionConfig,
        TranscriptionFactory,
        load_transcription_config,
        BaseTranscriber
    )
    
    # Test TranscriptionResult creation
    result = TranscriptionResult(text="test")
    assert result.text == "test"
    assert result.confidence == 0.0
    
    # Test TranscriptionConfig creation
    config = TranscriptionConfig(backend="pocketsphinx")
    assert config.backend == "pocketsphinx"
    
    # Test load_transcription_config function
    with patch.dict('os.environ', {}, clear=True):
        loaded_config = load_transcription_config()
        assert isinstance(loaded_config, TranscriptionConfig)
    
    # Test TranscriptionFactory
    transcriber = TranscriptionFactory.create_transcriber(config)
    assert isinstance(transcriber, BaseTranscriber)
    assert transcriber.config == config


def test_module_docstring():
    """Test that the module has proper documentation."""
    import opusagent.local.transcription as transcription_module
    
    assert hasattr(transcription_module, '__doc__')
    assert transcription_module.__doc__ is not None
    assert len(transcription_module.__doc__.strip()) > 0
    
    # Check that docstring contains key information
    docstring = transcription_module.__doc__
    assert "transcription" in docstring.lower()
    assert "backend" in docstring.lower()


def test_star_import():
    """Test that star import works correctly."""
    # Import everything from the module
    import opusagent.local.transcription as transcription_module
    
    # Get all public names (those in __all__)
    public_names = transcription_module.__all__
    
    # Verify each public name exists in the module
    for name in public_names:
        assert hasattr(transcription_module, name), f"Missing export: {name}"
        
        # Verify the export is not None
        export = getattr(transcription_module, name)
        assert export is not None, f"Export {name} is None"


def test_no_private_exports():
    """Test that private/internal modules are not exported."""
    import opusagent.local.transcription as transcription_module
    
    # These should not be in __all__
    private_items = [
        "models",      # Internal module
        "factory",     # Internal module
        "config",      # Internal module
        "base",        # Internal module
        "backends"     # Internal module
    ]
    
    for item in private_items:
        assert item not in transcription_module.__all__, f"Private item {item} should not be exported"


def test_backwards_compatibility():
    """Test backwards compatibility with existing imports."""
    # Test that old-style imports still work (if any were documented)
    from opusagent.local.transcription import TranscriptionFactory
    from opusagent.local.transcription.models import TranscriptionConfig
    
    # These should work together
    config = TranscriptionConfig(backend="pocketsphinx")
    transcriber = TranscriptionFactory.create_transcriber(config)
    
    assert transcriber is not None


def test_import_error_handling():
    """Test that import errors are handled gracefully."""
    # This should not raise an exception even if backends are not available
    from opusagent.local.transcription import TranscriptionFactory
    
    # Getting available backends should not crash
    available = TranscriptionFactory.get_available_backends()
    assert isinstance(available, list)


def test_quick_start_example():
    """Test the quick start example from the module docstring."""
    from opusagent.local.transcription import TranscriptionFactory, load_transcription_config
    
    # Load configuration (from docstring example)
    config = load_transcription_config()
    
    # Create transcriber (from docstring example)
    transcriber = TranscriptionFactory.create_transcriber(config)
    
    # Verify basic functionality
    assert transcriber is not None
    assert hasattr(transcriber, 'initialize')
    assert hasattr(transcriber, 'transcribe_chunk')
    assert hasattr(transcriber, 'cleanup')


def test_module_structure():
    """Test the internal module structure is correct."""
    import opusagent.local.transcription as transcription_module
    
    # Test that internal modules exist (but are not exported)
    assert hasattr(transcription_module, 'models')
    assert hasattr(transcription_module, 'factory')
    assert hasattr(transcription_module, 'config')
    assert hasattr(transcription_module, 'base')
    
    # But they should not be in __all__
    assert 'models' not in transcription_module.__all__
    assert 'factory' not in transcription_module.__all__
    assert 'config' not in transcription_module.__all__
    assert 'base' not in transcription_module.__all__


def test_type_availability():
    """Test that imported types work correctly for type hints."""
    from opusagent.local.transcription import TranscriptionResult, TranscriptionConfig, BaseTranscriber
    
    # These should be usable as type hints
    def example_function(result: TranscriptionResult, config: TranscriptionConfig) -> None:
        # This is just for type checking - verify the types can be used
        assert isinstance(result, TranscriptionResult)
        assert isinstance(config, TranscriptionConfig)
    
    # Verify the function signature is valid
    import inspect
    sig = inspect.signature(example_function)
    assert 'result' in sig.parameters
    assert 'config' in sig.parameters
    
    # Test that the types are available for type hints
    assert TranscriptionResult is not None
    assert TranscriptionConfig is not None
    assert BaseTranscriber is not None 