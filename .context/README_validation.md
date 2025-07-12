# LocalRealtimeClient Validation

This directory contains comprehensive validation scripts for testing the `LocalRealtimeClient` implementation. The validation ensures that all aspects of the mock client work correctly and behave as expected.

## 📋 Overview

The `LocalRealtimeClient` is a sophisticated mock implementation of the OpenAI Realtime API that provides:

- **Complete API Simulation**: Drop-in replacement for OpenAI Realtime API
- **Smart Response Selection**: Context-aware response selection based on conversation
- **Audio Processing**: Real audio file streaming and caching
- **Function Call Simulation**: Mock function calls with custom arguments
- **Performance Metrics**: Timing and performance tracking
- **Error Handling**: Graceful error handling and fallbacks

## 🚀 Quick Start

### Basic Validation

```bash
# Run the complete validation suite
python scripts/run_validation.py

# Run with verbose output
python scripts/validate_local_realtime_client.py --verbose

# Save results to JSON file
python scripts/validate_local_realtime_client.py --output validation_results.json
```

### Advanced Usage

```bash
# Run specific validation aspects
python scripts/validate_local_realtime_client.py --test initialization
python scripts/validate_local_realtime_client.py --test response-selection
python scripts/validate_local_realtime_client.py --test websocket

# Run with custom configuration
python scripts/validate_local_realtime_client.py --verbose --output detailed_results.json
```

## 🧪 What Gets Tested

### 1. **Client Initialization** ✅
- Basic client creation with defaults
- Custom logger configuration
- Custom session configuration
- Pre-configured response configurations
- Custom default response configuration

### 2. **Response Configuration Management** ✅
- Adding response configurations
- Retrieving existing configurations
- Handling non-existent configurations
- Configuration validation

### 3. **Intent Detection** ✅
- Greeting intent detection
- Help request detection
- Question detection
- Complaint detection
- Gratitude detection
- Confirmation/denial detection
- Multiple intent detection

### 4. **Keyword Matching** ✅
- Required keyword matching
- Excluded keyword matching
- Case-insensitive matching
- Edge cases (None, empty strings)

### 5. **Intent Matching** ✅
- Single intent matching
- Multiple intent matching
- Empty intent lists
- Intent validation

### 6. **Modality Matching** ✅
- Text modality matching
- Audio modality matching
- Multiple modality matching
- Modality validation

### 7. **Context Pattern Matching** ✅
- Regex pattern matching
- Context-aware patterns
- Pattern validation
- Edge case handling

### 8. **Conversation Context Management** ✅
- Context creation and updates
- Conversation history tracking
- Turn count management
- Intent detection integration

### 9. **Smart Response Examples** ✅
- Example configuration setup
- Response selection criteria
- Priority scoring
- Complex scenario handling

### 10. **Response Selection Logic** ✅
- Context-aware selection
- Priority-based scoring
- Multiple criteria evaluation
- Fallback handling

### 11. **Session State Management** ✅
- Session state retrieval
- Audio buffer management
- Active response ID tracking
- State persistence

### 12. **WebSocket Connection Lifecycle** ✅
- Connection establishment
- Connection failure handling
- Graceful disconnection
- Error recovery

### 13. **Performance Metrics** ✅
- Response timing tracking
- Performance data collection
- Metrics retrieval
- Timing validation

### 14. **Error Handling** ✅
- Invalid configuration handling
- Edge case validation
- Exception handling
- Graceful degradation

### 15. **Integration Scenarios** ✅
- Complete conversation flows
- Complex response configurations
- Multi-turn interactions
- Real-world usage patterns

## 📊 Understanding Results

### Success Indicators

✅ **PASSED**: Test completed successfully
❌ **FAILED**: Test failed with specific error details
💥 **ERROR**: Unexpected error occurred during test

### Sample Output

```
🔍 LocalRealtimeClient Validation
==================================================
This will test all aspects of the LocalRealtimeClient including:
• Client initialization and configuration
• Response configuration management
• Intent detection and keyword matching
• Conversation context management
• WebSocket connection lifecycle
• Performance metrics and timing
• Error handling and edge cases
• Smart response selection algorithms
• Session state management
==================================================

2024-01-15 10:30:00 - INFO - Testing client initialization...
2024-01-15 10:30:00 - INFO - ✅ Basic Initialization: PASSED
2024-01-15 10:30:00 - INFO - ✅ Custom Logger: PASSED
2024-01-15 10:30:00 - INFO - ✅ Custom Session Config: PASSED
...

============================================================
VALIDATION SUMMARY
============================================================
Total Tests: 45
Passed: 45 ✅
Failed: 0 ❌
Errors: 0 💥
Success Rate: 100.0%
============================================================

🎉 Validation completed successfully!
All tests passed - LocalRealtimeClient is working correctly.
```

## 🔧 Configuration Options

### Command Line Arguments

- `--verbose, -v`: Enable verbose logging with detailed test information
- `--output, -o`: Save validation results to JSON file
- `--test`: Run specific test categories (initialization, response-selection, etc.)

### Environment Variables

```bash
# Set log level
export LOG_LEVEL=DEBUG

# Enable mock mode
export OPUSAGENT_USE_MOCK=true

# Set mock server URL
export OPUSAGENT_MOCK_SERVER_URL=ws://localhost:8080
```

## 📁 Output Files

### JSON Results Format

```json
{
  "timestamp": "2024-01-15T10:30:00.123456",
  "tests": {
    "Basic Initialization": {
      "status": "PASSED",
      "details": "",
      "timestamp": "2024-01-15T10:30:00.123456"
    },
    "Custom Logger": {
      "status": "PASSED",
      "details": "",
      "timestamp": "2024-01-15T10:30:00.124567"
    }
  },
  "summary": {
    "total_tests": 45,
    "passed": 45,
    "failed": 0,
    "errors": 0
  }
}
```

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure you're in the project root
   cd /path/to/fastagent
   python scripts/run_validation.py
   ```

2. **Missing Dependencies**
   ```bash
   # Install required packages
   pip install websockets pydantic asyncio
   ```

3. **WebSocket Connection Issues**
   ```bash
   # Check if mock server is running
   # The validation uses mocked WebSocket connections by default
   ```

4. **Test Failures**
   - Review the specific error messages
   - Check the verbose output for details
   - Ensure all dependencies are properly installed

### Debug Mode

```bash
# Run with maximum verbosity
python scripts/validate_local_realtime_client.py --verbose

# Check individual components
python -c "
from opusagent.mock.realtime.client import LocalRealtimeClient
client = LocalRealtimeClient()
print('Client created successfully')
"
```

## 🔄 Continuous Integration

### GitHub Actions Example

```yaml
name: Validate LocalRealtimeClient

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run validation
        run: python scripts/run_validation.py
      - name: Upload results
        uses: actions/upload-artifact@v2
        if: always()
        with:
          name: validation-results
          path: validation_results.json
```

## 📈 Performance Benchmarks

The validation script includes performance testing:

- **Response Generation Time**: Measures time to generate responses
- **Audio Processing Speed**: Tests audio file loading and streaming
- **Memory Usage**: Monitors memory consumption during operations
- **Connection Latency**: Tests WebSocket connection performance

### Benchmark Results

Typical performance metrics:
- Response generation: < 100ms
- Audio file loading: < 50ms
- WebSocket connection: < 200ms
- Memory usage: < 50MB for typical usage

## 🤝 Contributing

When adding new features to `LocalRealtimeClient`:

1. **Add corresponding tests** to the validation script
2. **Update this documentation** with new test descriptions
3. **Run the full validation suite** before submitting changes
4. **Include performance benchmarks** for new features

### Adding New Tests

```python
def test_new_feature(self):
    """Test new feature functionality."""
    try:
        # Test implementation
        client = LocalRealtimeClient()
        # ... test logic ...
        self.log_test("New Feature Test", "PASSED")
    except Exception as e:
        self.log_test("New Feature Test", "FAILED", str(e))
```

## 📚 Related Documentation

- [LocalRealtimeClient API Documentation](../opusagent/mock/realtime/client.py)
- [Mock Models Documentation](../opusagent/mock/realtime/models.py)
- [OpenAI Realtime API Reference](https://platform.openai.com/docs/api-reference/realtime)
- [WebSocket Protocol Documentation](../docs/websocket_protocol.md)

## 📞 Support

For issues with the validation script:

1. Check the troubleshooting section above
2. Review the verbose output for detailed error information
3. Create an issue with the validation results JSON file
4. Include system information and Python version

---

**Last Updated**: January 2024
**Version**: 1.0.0
**Compatibility**: Python 3.8+, LocalRealtimeClient 1.0+ 