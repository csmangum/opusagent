# Telephony Mock Validation

This directory contains comprehensive validation scripts for testing the `/ws/telephony` endpoint with the mock realtime implementation. These scripts act like AudioCodes telephony and validate that all events and messages are handled correctly.

## Overview

The validation system consists of two main scripts:

1. **`validate_telephony_mock.py`** - The main validation script that acts like AudioCodes telephony
2. **`run_validation.py`** - A convenient test runner that handles environment setup and server management

## Quick Start

### Prerequisites

1. **Mock Mode Enabled**: The validation requires mock mode to be enabled
2. **Server Running**: The OpusAgent server should be running (or the runner will start it)
3. **Dependencies**: All required Python packages should be installed

### Basic Usage

```bash
# Run full validation (recommended)
python scripts/run_validation.py

# Run with verbose logging
python scripts/run_validation.py --verbose

# Run specific test scenarios
python scripts/run_validation.py --test session-flow
python scripts/run_validation.py --test audio-streaming
python scripts/run_validation.py --test conversation-flow
```

### Advanced Usage

```bash
# Run validation directly (manual setup required)
OPUSAGENT_USE_MOCK=true python scripts/validate_telephony_mock.py

# Custom server URL
python scripts/run_validation.py --server-url ws://localhost:9000/ws/telephony

# Save validation report
python scripts/run_validation.py --output validation_report.json

# Skip server check (if server is already running)
python scripts/run_validation.py --no-server-check
```

## Test Scenarios

### 1. Session Flow (`session-flow`)
Tests the basic session initiation and acceptance:
- `session.initiate` → `session.accepted`
- Validates message structure and required fields
- Tests session state management

### 2. Audio Streaming (`audio-streaming`)
Tests audio streaming in both directions:
- User audio streaming (`userStream.start/chunk/stop`)
- AI response streaming (`playStream.start/chunk/stop`)
- Audio chunk validation and timing
- Tests audio format handling

### 3. Conversation Flow (`conversation-flow`)
Tests a complete conversation from start to finish:
- Session initiation
- User audio streaming
- AI response generation
- Speech detection events (VAD)
- Error handling
- Session termination

### 4. Full Validation (`all`)
Runs all test scenarios in sequence, providing comprehensive validation of the entire system.

## Validation Features

### Message Validation
- **Structure Validation**: Ensures all messages have correct fields and types
- **Protocol Compliance**: Validates against AudioCodes Bot API specification
- **Response Timing**: Checks that responses are received within expected timeouts

### Audio Testing
- **Test Audio Generation**: Creates realistic audio chunks for testing
- **Format Validation**: Ensures audio is properly encoded and formatted
- **Streaming Validation**: Tests bidirectional audio streaming

### Error Handling
- **Invalid Messages**: Tests server response to malformed messages
- **Missing Fields**: Validates error handling for incomplete messages
- **Connection Issues**: Tests graceful handling of connection problems

### State Management
- **Session State**: Tracks conversation state throughout the test
- **Stream State**: Monitors audio stream status
- **Message Flow**: Records complete message exchange for analysis

## Output and Reporting

### Console Output
The validation provides detailed console output including:
- Test progress and status
- Message exchange logs
- Error and warning messages
- Summary statistics

### JSON Reports
When using `--output`, a comprehensive JSON report is generated containing:
- Test results and statistics
- Complete message flow
- Error details and warnings
- Performance metrics
- Message type analysis

Example report structure:
```json
{
  "start_time": "2024-01-15T10:30:00",
  "end_time": "2024-01-15T10:30:45",
  "tests_passed": 5,
  "tests_failed": 0,
  "success_rate": 100.0,
  "message_statistics": {
    "sent": {"session.initiate": 1, "userStream.start": 2},
    "received": {"session.accepted": 1, "userStream.started": 2},
    "total_sent": 10,
    "total_received": 8
  },
  "errors": [],
  "warnings": [],
  "message_flow": [...]
}
```

## Environment Variables

The validation scripts use these environment variables:

- `OPUSAGENT_USE_MOCK=true` - Enables mock mode
- `OPUSAGENT_MOCK_SERVER_URL=ws://localhost:8080` - Mock server URL
- `LOG_LEVEL=INFO` - Logging level

## Troubleshooting

### Common Issues

1. **Server Not Running**
   ```
   ❌ Cannot proceed without server running
   ```
   Solution: The runner will attempt to start the server automatically, or start it manually with `python run_opus_server.py`

2. **Mock Mode Not Enabled**
   ```
   ⚠️  Warning: OPUSAGENT_USE_MOCK is not set to 'true'
   ```
   Solution: Use the `run_validation.py` script which sets this automatically

3. **Connection Timeout**
   ```
   Timeout waiting for message after 10s
   ```
   Solution: Check if the server is responding, increase timeout, or check network connectivity

4. **Import Errors**
   ```
   ImportError: No module named 'opusagent'
   ```
   Solution: Ensure you're running from the project root directory

### Debug Mode

For detailed debugging, use verbose mode:
```bash
python scripts/run_validation.py --verbose
```

This will show:
- All sent and received messages
- Detailed timing information
- Internal state changes
- WebSocket connection details

## Integration with CI/CD

The validation scripts can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Telephony Validation
  run: |
    python scripts/run_validation.py --output validation_report.json
    python scripts/run_validation.py --test session-flow --output session_test.json
```

## Extending the Validation

### Adding New Tests

To add new test scenarios, extend the `TelephonyValidator` class:

```python
async def test_custom_scenario(self) -> bool:
    """Test a custom scenario."""
    try:
        # Your test logic here
        await self.send_message(custom_message)
        response = await self.wait_for_message_type("expected.response")
        
        if self.validate_message_structure(response, "expected.response"):
            self.validation_results["tests_passed"] += 1
            return True
        else:
            self.validation_results["tests_failed"] += 1
            return False
    except Exception as e:
        self.validation_results["errors"].append(f"Custom scenario: {e}")
        return False
```

### Custom Message Validation

Add custom validation logic:

```python
def validate_custom_message(self, message: Dict[str, Any]) -> bool:
    """Validate custom message structure."""
    if message.get("type") != "custom.type":
        return False
    
    # Add your validation logic here
    required_fields = ["field1", "field2"]
    return all(field in message for field in required_fields)
```

## Performance Considerations

- **Audio Chunk Size**: Default is 3200 bytes (100ms at 16kHz)
- **Timeout Values**: Adjustable per test scenario
- **Memory Usage**: Audio chunks are kept in memory during validation
- **Network Latency**: Consider local testing for consistent results

## Security Notes

- The validation scripts are for testing only
- No sensitive data is transmitted
- Test audio contains only silence
- All connections are local by default

## Contributing

When adding new validation features:

1. Follow the existing code structure
2. Add comprehensive error handling
3. Include detailed logging
4. Update this documentation
5. Add tests for new functionality 