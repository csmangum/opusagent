# Unit Tests for opusagent.mock.realtime

This directory contains comprehensive unit tests for the `opusagent.mock.realtime` module, which provides a complete mock implementation of the OpenAI Realtime API for testing and development purposes.

## Test Structure

The tests are organized to match the module structure:

```
tests/opusagent/realtime/
├── __init__.py                 # Package initialization
├── conftest.py                 # Shared fixtures and configuration
├── test_models.py              # Tests for data models
├── test_audio.py               # Tests for audio management
├── test_generators.py          # Tests for response generation
├── test_handlers.py            # Tests for event handling
├── test_utils.py               # Tests for utility functions
├── test_client.py              # Tests for main client class
├── test_init.py                # Tests for module initialization
└── README.md                   # This file
```

## Test Coverage

### 1. test_models.py
Tests for the data models that define the structure and behavior of the mock system:

- **ConversationContext**: Conversation state tracking and context management
- **ResponseSelectionCriteria**: Criteria for intelligent response selection
- **LocalResponseConfig**: Configuration for mock responses
- **MockSessionState**: Session state management

**Key Test Areas:**
- Model creation and validation
- Field assignment and updates
- Default value handling
- Complex data structures
- Integration between models

### 2. test_audio.py
Tests for the audio management system that handles file loading, caching, and fallback generation:

- **AudioManager**: Audio file loading and caching
- Audio file processing with AudioUtils integration
- Fallback silence generation
- Cache management and performance optimization
- Error handling and edge cases

**Key Test Areas:**
- Audio file loading with caching
- AudioUtils integration and fallback modes
- Cache operations (add, remove, clear, query)
- Error handling for missing files
- Silence generation for fallback scenarios

### 3. test_generators.py
Tests for the response generation system that creates realistic API responses:

- **ResponseGenerator**: Text, audio, and function call response generation
- Streaming simulation with configurable delays
- Event creation and WebSocket communication
- Transcript generation and error reporting

**Key Test Areas:**
- Text response streaming with character delays
- Audio response chunking and streaming
- Function call argument streaming
- Event creation and WebSocket communication
- Error event generation
- Transcript delta and completion events

### 4. test_handlers.py
Tests for the event handling system that processes incoming WebSocket messages:

- **EventHandlerManager**: Event registration and routing
- Session management and state tracking
- Audio buffer operations
- Response lifecycle management

**Key Test Areas:**
- Event handler registration and execution
- Session state management
- Audio buffer operations (append, commit, clear)
- Response creation and cancellation
- Speech detection simulation
- WebSocket event sending

### 5. test_utils.py
Tests for utility functions that provide common operations:

- **Validation Functions**: Response configuration validation
- **Event Creation**: Helper functions for creating WebSocket events
- **Default Configurations**: Pre-built configurations for common scenarios
- **Constants**: Audio and system constants

**Key Test Areas:**
- Configuration validation with various data types
- Event creation with proper structure
- Default configuration generation
- Constant re-exports and values
- Integration between utility functions

### 6. test_client.py
Tests for the main client class that orchestrates all components:

- **LocalRealtimeClient**: Main client implementation
- Response selection logic and scoring
- Intent detection and keyword matching
- Conversation context management
- WebSocket connection management

**Key Test Areas:**
- Client initialization and configuration
- Response configuration management
- Intent detection for various conversation types
- Response selection with scoring algorithms
- WebSocket connection lifecycle
- Session state and audio buffer management
- Performance timing and metrics

### 7. test_init.py
Tests for the module initialization and public interface:

- **Module Exports**: Verification of public API
- **Version Management**: Semantic versioning compliance
- **Import Performance**: Import speed and efficiency
- **Documentation**: Docstring consistency

**Key Test Areas:**
- Module import and export verification
- Version format and compliance
- Import performance and circular import detection
- Class relationships and integration
- Documentation consistency

## Running the Tests

### Run all realtime tests:
```bash
pytest tests/opusagent/realtime/ -v
```

### Run specific test files:
```bash
pytest tests/opusagent/realtime/test_models.py -v
pytest tests/opusagent/realtime/test_client.py -v
```

### Run with coverage:
```bash
pytest tests/opusagent/realtime/ --cov=opusagent.mock.realtime --cov-report=html
```

### Run specific test classes:
```bash
pytest tests/opusagent/realtime/test_client.py::TestLocalRealtimeClient -v
pytest tests/opusagent/realtime/test_models.py::TestConversationContext -v
```

## Test Features

### Comprehensive Coverage
- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing
- **Edge Cases**: Error conditions and boundary testing
- **Performance Tests**: Timing and efficiency validation

### Mocking Strategy
- **WebSocket Connections**: Mocked for isolated testing
- **Audio Files**: Mocked file operations and data
- **External Dependencies**: AudioUtils and other utilities mocked
- **Async Operations**: Proper async/await testing patterns

### Fixtures and Utilities
- **Shared Fixtures**: Common test data and mocks
- **Sample Configurations**: Pre-built test configurations
- **Mock Objects**: Realistic mock implementations
- **Test Utilities**: Helper functions for common test patterns

## Test Quality Standards

### Code Quality
- **Type Safety**: Proper type hints and validation
- **Error Handling**: Comprehensive exception testing
- **Documentation**: Clear test descriptions and docstrings
- **Maintainability**: Clean, readable test code

### Test Reliability
- **Isolation**: Tests don't interfere with each other
- **Deterministic**: Tests produce consistent results
- **Fast Execution**: Tests run quickly for development feedback
- **Comprehensive**: High coverage of functionality and edge cases

### Best Practices
- **Arrange-Act-Assert**: Clear test structure
- **Descriptive Names**: Self-documenting test names
- **Minimal Dependencies**: Tests are self-contained
- **Realistic Data**: Tests use realistic, representative data

## Integration with Main Test Suite

These tests integrate with the main project test suite and follow the same patterns and conventions:

- **Pytest Framework**: Consistent with project testing approach
- **Mock Strategy**: Aligned with project mocking patterns
- **Coverage Goals**: Contribute to overall project coverage
- **CI/CD Integration**: Compatible with automated testing pipelines

## Future Enhancements

### Planned Test Improvements
- **Performance Benchmarks**: Response time and throughput testing
- **Load Testing**: High-volume scenario testing
- **Memory Testing**: Memory usage and leak detection
- **Concurrency Testing**: Multi-threaded and async testing

### Additional Test Scenarios
- **Real-world Usage**: End-to-end conversation flows
- **Error Recovery**: Graceful degradation testing
- **Configuration Validation**: Complex configuration scenarios
- **API Compatibility**: OpenAI Realtime API compliance testing 