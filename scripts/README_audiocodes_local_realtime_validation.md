# AudioCodes Bridge Local Realtime Validation

This script validates that the AudioCodes bridge works correctly with the local realtime connection when `USE_LOCAL_REALTIME=true`. It connects to the `/ws/telephony` endpoint and tests all message types and conversation flows with the mock WebSocket connection.

## Prerequisites

1. **Environment Setup**: The server must be running with `USE_LOCAL_REALTIME=true`
2. **Dependencies**: All required packages from `requirements.txt` must be installed
3. **Server Running**: The FastAPI server must be running on the specified port (default: 8000)

## Usage

### Basic Usage

```bash
# Run with local realtime enabled
USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py
```

### Advanced Usage

```bash
# Run with custom server URL
USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py --server-url ws://localhost:8000/ws/telephony

# Run with verbose logging
USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py --verbose

# Run with custom bot name and caller
USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py --bot-name "TestBot" --caller "+15551234567"
```

### Running Specific Tests

```bash
# Test only session flow
USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py --test session-flow

# Test only audio streaming
USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py --test audio-streaming

# Test complete conversation flow
USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py --test conversation-flow

# Test VAD integration
USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py --test vad-integration
```

## Test Scenarios

### 1. Session Flow Test
- Sends `session.initiate` message
- Validates `session.accepted` response
- Checks conversation ID and media format handling

### 2. Audio Streaming Test
- Sends `userStream.start` message
- Validates `userStream.started` response
- Streams audio chunks using `userStream.chunk` messages
- Sends `userStream.stop` message
- Validates `userStream.stopped` response

### 3. Local Realtime Response Test
- Waits for `playStream.start` from local realtime
- Receives `playStream.chunk` messages with audio data
- Validates `playStream.stop` completion
- Confirms local realtime is generating responses

### 4. VAD Integration Test
- Checks for VAD events during audio streaming:
  - `userStream.speech.started`
  - `userStream.speech.stopped`
  - `userStream.speech.committed`
- Validates VAD event sequence

### 5. Conversation Flow Test
- Combines all above tests into a complete conversation
- Tests end-to-end integration

### 6. Session Termination Test
- Sends `session.end` message
- Validates proper cleanup

## Environment Variables

The script respects the following environment variables:

- `USE_LOCAL_REALTIME`: Must be set to `true` to enable local realtime mode
- `VAD_ENABLED`: Controls VAD functionality (default: `true`)
- `LOCAL_REALTIME_ENABLE_TRANSCRIPTION`: Enable transcription (default: `false`)
- `LOCAL_REALTIME_SETUP_SMART_RESPONSES`: Setup smart responses (default: `true`)

## Output

### Console Output
The script provides real-time feedback on test progress:
```
Starting AudioCodes Bridge Local Realtime Validation...
Server URL: ws://localhost:8000/ws/telephony
Bot Name: LocalRealtimeBot
Caller: +15551234567

=== Testing Session Initiation with Local Realtime ===
✓ Session initiation successful
=== Testing Audio Streaming with Local Realtime ===
✓ User stream started successfully
Sending audio chunks...
✓ Sent 20 audio chunks
✓ User stream stopped successfully
=== Testing Local Realtime Response Generation ===
✓ Local realtime started audio response
✓ Received 15 audio chunks from local realtime
✓ Local realtime completed audio response
...
```

### Summary Report
At the end, a comprehensive summary is displayed:
```
============================================================
AUDIOCODES BRIDGE LOCAL REALTIME VALIDATION SUMMARY
============================================================
Duration: 12.3 seconds
Tests Passed: 6
Tests Failed: 0
Success Rate: 100.0%
Messages Sent: 25
Messages Received: 42
VAD Events: 3
============================================================
```

### Log Files
- **Console logs**: Real-time progress and debug information
- **Validation log**: Detailed log file in `logs/audiocodes_local_realtime_validation_YYYYMMDD_HHMMSS.log`
- **JSON report**: Detailed validation report in `logs/audiocodes_local_realtime_validation_report_YYYYMMDD_HHMMSS.json`

## Validation Report Structure

The JSON report contains:

```json
{
  "validation_summary": {
    "start_time": "2024-01-15T10:30:00.000000",
    "end_time": "2024-01-15T10:30:12.345000",
    "duration_seconds": 12.345,
    "tests_passed": 6,
    "tests_failed": 0,
    "total_tests": 6,
    "success_rate": 100.0
  },
  "configuration": {
    "server_url": "ws://localhost:8000/ws/telephony",
    "bot_name": "LocalRealtimeBot",
    "caller": "+15551234567",
    "media_format": "raw/lpcm16",
    "conversation_id": "uuid-here"
  },
  "message_statistics": {
    "messages_sent": 25,
    "messages_received": 42,
    "vad_events_received": 3,
    "local_realtime_events": 5
  },
  "errors": [],
  "warnings": [],
  "message_flow": [...],
  "local_realtime_events": [...],
  "vad_events": [...]
}
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   ```
   ERROR: Connection refused
   ```
   - Ensure the server is running: `uvicorn opusagent.main:app --host 0.0.0.0 --port 8000`
   - Check the server URL is correct

2. **USE_LOCAL_REALTIME not set**
   ```
   ERROR: USE_LOCAL_REALTIME must be set to 'true' to run this validation
   ```
   - Set the environment variable: `USE_LOCAL_REALTIME=true`

3. **No VAD Events**
   ```
   WARNING: No VAD events received - VAD might be disabled
   ```
   - This is normal if VAD is disabled via `VAD_ENABLED=false`
   - Check VAD configuration in the server

4. **Timeout Errors**
   ```
   WARNING: Timeout waiting for message after 10.0s
   ```
   - Check server logs for errors
   - Ensure local realtime client is properly configured
   - Verify audio processing is working

### Debug Mode

Run with verbose logging to see detailed message flow:
```bash
USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py --verbose
```

### Manual Testing

For manual testing, you can also use the individual test functions:
```bash
# Test just session initiation
USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py --test session-flow

# Test just audio streaming
USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py --test audio-streaming
```

## Integration with CI/CD

The script exits with code 0 on success and 1 on failure, making it suitable for CI/CD pipelines:

```bash
#!/bin/bash
# CI/CD script example

# Start server in background
USE_LOCAL_REALTIME=true uvicorn opusagent.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

# Wait for server to start
sleep 5

# Run validation
USE_LOCAL_REALTIME=true python scripts/validate_audiocodes_local_realtime.py
VALIDATION_RESULT=$?

# Stop server
kill $SERVER_PID

# Exit with validation result
exit $VALIDATION_RESULT
```

## Related Scripts

- `scripts/validate_twilio_bridge.py`: Validates Twilio bridge integration
- `scripts/validate_telephony_mock.py`: General telephony validation
- `scripts/validate_local_realtime_client.py`: Local realtime client validation
- `examples/mock_websocket_example.py`: Mock WebSocket connection examples 