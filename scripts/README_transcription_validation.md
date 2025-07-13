# Transcription Validation Scripts

This directory contains scripts to validate the transcription capabilities of the LocalRealtimeClient, which simulates the OpenAI Realtime API with local transcription support.

## Overview

The LocalRealtimeClient supports two transcription backends:
- **PocketSphinx**: Lightweight, offline transcription (recommended for testing)
- **Whisper**: High-accuracy transcription (requires more resources)

## Available Scripts

### 1. Simple Transcription Test (`simple_transcription_test.py`)

A straightforward script that tests transcription functionality directly without complex WebSocket server setup.

**Features:**
- Tests transcription backends directly
- Validates audio processing and format conversion
- Tests transcription configuration loading
- Tests client integration
- Generates detailed test reports

**Usage:**
```bash
# Test PocketSphinx backend (default)
python scripts/simple_transcription_test.py

# Test Whisper backend
python scripts/simple_transcription_test.py --backend whisper

# Test with specific audio file
python scripts/simple_transcription_test.py --audio-file path/to/audio.wav

# Generate test audio and run tests
python scripts/simple_transcription_test.py --generate-test-audio

# Enable verbose logging
python scripts/simple_transcription_test.py --verbose
```

**Example Output:**
```
2024-01-15 10:30:00 - INFO - Starting transcription tests for pocketsphinx backend...
2024-01-15 10:30:01 - INFO - PASSED: Configuration Loading - Loaded config: pocketsphinx, en, 16000Hz
2024-01-15 10:30:01 - INFO - PASSED: Backend Availability: pocketsphinx - Backend pocketsphinx is available
2024-01-15 10:30:02 - INFO - PASSED: Transcriber Initialization: pocketsphinx - Successfully initialized pocketsphinx transcriber
2024-01-15 10:30:02 - INFO - PASSED: Audio Conversion: pocketsphinx - Converted 16000 samples
2024-01-15 10:30:03 - INFO - PASSED: Chunk Transcription: pocketsphinx - Final text: '' (confidence: 0.000)
2024-01-15 10:30:03 - INFO - PASSED: Client Integration: pocketsphinx - Transcription enabled with pocketsphinx

=== Test Results ===
Results saved to: transcription_test_results_pocketsphinx_20240115_103003.json
Summary: 6/6 tests passed
```

### 2. Comprehensive Validation (`validate_transcription_capability.py`)

A comprehensive validation script that tests all aspects of transcription functionality.

**Features:**
- Tests both PocketSphinx and Whisper backends
- Validates audio processing and format conversion
- Tests real-time transcription with chunked audio
- Verifies transcription event generation
- Tests error handling and fallback scenarios
- Generates detailed validation reports

**Usage:**
```bash
# Test both backends
python scripts/validate_transcription_capability.py

# Test specific backend
python scripts/validate_transcription_capability.py --backend pocketsphinx

# Test with audio file
python scripts/validate_transcription_capability.py --audio-file path/to/audio.wav

# Generate test audio
python scripts/validate_transcription_capability.py --generate-test-audio

# Custom output directory
python scripts/validate_transcription_capability.py --output-dir my_results
```

## Prerequisites

### For PocketSphinx Backend
```bash
pip install pocketsphinx
```

### For Whisper Backend
```bash
pip install openai-whisper
# or
pip install whisper
```

### Additional Dependencies
```bash
pip install numpy websockets
```

## Test Audio Files

The scripts can work with any WAV file, but for best results:
- Use 16kHz sample rate
- Use 16-bit PCM format
- Use mono channel
- Keep files under 30 seconds for testing

### Generating Test Audio

The scripts can generate test audio files automatically:
```bash
python scripts/simple_transcription_test.py --generate-test-audio
```

This creates a 1-second 440Hz sine wave file for testing.

## Configuration

Transcription behavior can be configured through environment variables:

```bash
# Backend selection
export TRANSCRIPTION_BACKEND=pocketsphinx  # or whisper

# Language settings
export TRANSCRIPTION_LANGUAGE=en

# Whisper-specific settings
export WHISPER_MODEL_SIZE=base  # tiny, base, small, medium, large
export WHISPER_DEVICE=cpu       # cpu or cuda

# Processing settings
export TRANSCRIPTION_CHUNK_DURATION=1.0
export TRANSCRIPTION_CONFIDENCE_THRESHOLD=0.5
export TRANSCRIPTION_SAMPLE_RATE=16000
```

## Understanding Test Results

### Test Categories

1. **Configuration Loading**: Verifies that transcription configuration can be loaded properly
2. **Backend Availability**: Checks if the requested transcription backend is available
3. **Transcriber Initialization**: Tests that the transcriber can be initialized successfully
4. **Audio Conversion**: Validates audio format conversion for processing
5. **Chunk Transcription**: Tests transcription of audio chunks
6. **Client Integration**: Verifies that transcription works with LocalRealtimeClient
7. **Audio File Transcription**: Tests transcription of complete audio files

### Success Criteria

- **PASSED**: Test completed successfully
- **FAILED**: Test encountered an error or unexpected behavior
- **SKIPPED**: Test was skipped due to missing dependencies or configuration

### Output Files

The scripts generate JSON result files with detailed test information:
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "tests": [
    {
      "name": "Backend Availability: pocketsphinx",
      "passed": true,
      "details": "Backend pocketsphinx is available",
      "timestamp": "2024-01-15T10:30:01"
    }
  ],
  "summary": {
    "total_tests": 6,
    "passed": 6,
    "failed": 0
  }
}
```

## Troubleshooting

### Common Issues

1. **Backend Not Available**
   ```
   FAILED: Backend Availability: whisper - Backend whisper is not available
   ```
   **Solution**: Install the required backend package (`pip install openai-whisper`)

2. **PocketSphinx Initialization Failed (Windows)**
   ```
   FAILED: Transcriber Initialization: pocketsphinx - Failed to initialize pocketsphinx transcriber
   ERROR: "pocketsphinx.c", line 261: Cannot redirect log output
   ```
   **Solution**: This issue has been fixed in the latest version. The transcriber now handles Windows log redirection properly. If you still encounter issues, try using Whisper backend instead.

3. **General Initialization Failed**
   ```
   FAILED: Transcriber Initialization: pocketsphinx - Failed to initialize pocketsphinx transcriber
   ```
   **Solution**: Check that all dependencies are installed and system has required audio libraries

4. **Audio Conversion Error**
   ```
   FAILED: Audio Conversion: pocketsphinx - Audio conversion returned empty result
   ```
   **Solution**: Verify audio file format and ensure it's valid 16-bit PCM

5. **Client Integration Failed**
   ```
   FAILED: Client Integration: pocketsphinx - Transcription not properly initialized
   ```
   **Solution**: Check session configuration and transcription settings

### Debug Mode

Enable verbose logging to see detailed information:
```bash
python scripts/simple_transcription_test.py --verbose
```

### Manual Testing

For manual testing of transcription functionality:

```python
from opusagent.mock.realtime import LocalRealtimeClient, TranscriptionConfig

# Create client with transcription
client = LocalRealtimeClient(
    enable_transcription=True,
    transcription_config={"backend": "pocketsphinx"}
)

# Check transcription state
state = client.get_transcription_state()
print(f"Transcription enabled: {state['enabled']}")
print(f"Backend: {state['backend']}")
```

### Testing PocketSphinx Fix

To test if the PocketSphinx Windows fix is working:

```bash
python scripts/test_pocketsphinx_fix.py
```

This script specifically tests PocketSphinx initialization on Windows and will show:
- ✅ SUCCESS: If the fix is working
- ❌ FAILED: If there are still issues

## Performance Considerations

- **PocketSphinx**: Fast, lightweight, good for real-time applications
- **Whisper**: More accurate but requires more computational resources
- **Chunk Size**: Smaller chunks (3200 bytes = 200ms) provide more responsive transcription
- **Sample Rate**: 16kHz is optimal for most transcription tasks

## Integration with Main Application

The transcription functionality is automatically enabled when:
1. Session configuration includes `input_audio_transcription`
2. LocalRealtimeClient is initialized with `enable_transcription=True`
3. Valid transcription backend is available

The client will automatically:
- Process incoming audio chunks
- Generate transcription events
- Send transcription results via WebSocket
- Handle transcription errors gracefully 