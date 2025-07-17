# Realtime Transcription Validation

This document describes the comprehensive transcription validation system for the LocalRealtimeClient, which tests transcription capabilities within realistic conversation scenarios.

## Overview

The realtime transcription validation system provides comprehensive testing of transcription integration within the LocalRealtimeClient, including:

- **Backend Testing**: Tests both PocketSphinx and Whisper transcription backends
- **Integration Testing**: Validates transcription within LocalRealtimeClient sessions
- **Event Generation**: Tests transcription event generation and WebSocket communication
- **Conversation Flows**: Tests complete conversation scenarios with transcription
- **Error Handling**: Validates error handling and fallback scenarios
- **Performance Testing**: Measures transcription performance and timing

## Files

### Main Validation Script
- `scripts/validate_realtime_transcription.py` - Main validation script with comprehensive testing

### Test Scripts
- `scripts/test_realtime_transcription_validation.py` - Quick test script for demonstration

### Documentation
- `scripts/README_realtime_transcription_validation.md` - This documentation file

## Usage

### Basic Usage

```bash
# Run with default settings (both backends)
python scripts/validate_realtime_transcription.py

# Test specific backend
python scripts/validate_realtime_transcription.py --backend pocketsphinx
python scripts/validate_realtime_transcription.py --backend whisper

# Quick test
python scripts/test_realtime_transcription_validation.py
```

### Advanced Usage

```bash
# Test with specific audio file
python scripts/validate_realtime_transcription.py --audio-file path/to/audio.wav

# Generate test audio and run validation
python scripts/validate_realtime_transcription.py --generate-test-audio

# Verbose logging
python scripts/validate_realtime_transcription.py --verbose

# Custom output directory
python scripts/validate_realtime_transcription.py --output-dir validation_results
```

### Examples

```bash
# Quick test with PocketSphinx
python scripts/validate_realtime_transcription.py --backend pocketsphinx --verbose

# Full validation with generated audio
python scripts/validate_realtime_transcription.py --generate-test-audio --output-dir test_results

# Test with real audio file
python scripts/validate_realtime_transcription.py --audio-file opusagent/mock/audio/greetings/greetings_01.wav
```

## Test Categories

### 1. Backend Availability
Tests whether transcription backends (PocketSphinx, Whisper) are available and properly installed.

### 2. Client Initialization
Tests transcription initialization within LocalRealtimeClient, including configuration loading and setup.

### 3. Event Generation
Tests transcription event generation during conversation, including:
- Audio append events
- Transcription delta events
- Transcription completion events
- Error events

### 4. Conversation Flow
Tests complete conversation scenarios with transcription enabled, including:
- Real-time audio processing
- Transcription during conversation turns
- Integration with VAD (Voice Activity Detection)
- Response generation with transcription context

### 5. Error Handling
Tests error handling and fallback scenarios:
- Invalid audio data
- Backend failures
- Configuration errors
- Graceful degradation

### 6. Configuration
Tests transcription configuration loading and validation:
- Configuration file loading
- Parameter validation
- Backend-specific settings

### 7. Performance
Tests transcription performance and timing:
- Processing time measurement
- Memory usage
- Real-time performance characteristics

## Output and Results

### Validation Results
The validation generates detailed results including:

- **Test Results**: Individual test pass/fail status with details
- **Conversation Flows**: Complete conversation scenarios with transcription events
- **Transcription Events**: Detailed transcription event logs
- **Performance Metrics**: Timing and performance measurements
- **Summary Statistics**: Overall validation summary

### Output Files
- `validation_results/realtime_transcription_validation_YYYYMMDD_HHMMSS.json` - Detailed results
- `validation_results/test_audio/` - Generated test audio files (if requested)
- `logs/realtime_transcription_validation_YYYYMMDD_HHMMSS.log` - Validation logs

### Sample Output
```
=== Validation Summary ===
Total Tests: 12
Passed: 10
Failed: 1
Skipped: 1
Success Rate: 83.3%
Transcription Events: 45
Successful Transcriptions: 42
Failed Transcriptions: 3
```

## Integration with LocalRealtimeClient

The validation system integrates with the LocalRealtimeClient to test transcription capabilities in realistic scenarios:

### Client Configuration
```python
from opusagent.mock.realtime import LocalRealtimeClient, TranscriptionConfig

# Create client with transcription enabled
client = LocalRealtimeClient(
    enable_transcription=True,
    transcription_config={
        "backend": "pocketsphinx",
        "language": "en",
        "confidence_threshold": 0.5
    }
)
```

### Transcription Events
The validation tests various transcription events:
- `CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_DELTA`
- `CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED`
- `CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_FAILED`

### Conversation Context
Tests transcription integration with conversation context:
- Real-time audio processing
- Transcription during user input
- Integration with response generation
- VAD integration

## Dependencies

### Required Dependencies
- `opusagent.mock.realtime` - LocalRealtimeClient and transcription modules
- `opusagent.models.openai_api` - Session configuration models
- `asyncio` - Asynchronous programming support
- `numpy` - Audio processing (optional, with fallback)

### Optional Dependencies
- `wave` - WAV file handling (optional)
- `pocketsphinx` - PocketSphinx transcription backend
- `whisper` - Whisper transcription backend

## Troubleshooting

### Common Issues

1. **Backend Not Available**
   ```
   FAILED: Backend Availability: pocketsphinx - Backend pocketsphinx is not available
   ```
   Solution: Install the required backend (e.g., `pip install pocketsphinx`)

2. **Audio Processing Errors**
   ```
   FAILED: Audio Conversion: pocketsphinx - Error during audio conversion
   ```
   Solution: Check audio format and ensure numpy is available

3. **Transcription Timeout**
   ```
   FAILED: Transcription Performance: pocketsphinx - Processing took too long
   ```
   Solution: Check system resources and backend configuration

### Debug Mode
Enable verbose logging for detailed debugging:
```bash
python scripts/validate_realtime_transcription.py --verbose
```

## Contributing

To add new test cases or modify existing ones:

1. **Add Test Methods**: Add new test methods to `RealtimeTranscriptionValidator`
2. **Update Validation**: Call new tests in the `run_validation` method
3. **Documentation**: Update this README with new test descriptions
4. **Examples**: Add usage examples for new features

### Test Method Template
```python
async def test_new_feature(self, backend: str) -> bool:
    """Test description."""
    test_name = f"New Feature Test: {backend}"
    
    try:
        # Test implementation
        # ...
        
        self.log_test_result(test_name, True, "Success details")
        return True
        
    except Exception as e:
        self.log_test_result(test_name, False, f"Error: {e}")
        return False
```

## Related Documentation

- [LocalRealtimeClient Documentation](../opusagent/mock/realtime/README.md)
- [Transcription Module Documentation](../opusagent/mock/realtime/transcription.py)
- [General Validation Documentation](./README_transcription_validation.md) 