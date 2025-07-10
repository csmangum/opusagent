# Voice Activity Detection (VAD) Configuration

This document explains how to configure and use Voice Activity Detection (VAD) functionality in the AudioCodes bridge.

## Overview

Voice Activity Detection (VAD) allows the bot to handle speech detection locally instead of relying on the AudioCodes platform. When enabled, the bot will:

1. Receive VAD events from the OpenAI Realtime API
2. Process and forward these events to AudioCodes
3. Provide better control over speech detection timing

## Configuration

### Environment Variables

VAD functionality can be configured using the following environment variables:

#### Main Service Configuration
- `VAD_ENABLED`: Enable/disable VAD in the main service (default: `true`)
  - `true`, `1`, `yes`, `on` - Enable VAD
  - `false`, `0`, `no`, `off` - Disable VAD

#### TUI Configuration
- `TUI_VAD_ENABLED`: Enable/disable VAD in the TUI (default: `true`)
- `TUI_SHOW_VAD_EVENTS`: Show VAD events in the TUI (default: `true`)

### Example Configuration

```bash
# Enable VAD (default)
export VAD_ENABLED=true
export TUI_VAD_ENABLED=true
export TUI_SHOW_VAD_EVENTS=true

# Disable VAD
export VAD_ENABLED=false
export TUI_VAD_ENABLED=false
export TUI_SHOW_VAD_EVENTS=false
```

## How VAD Works

### When VAD is Enabled

1. **Speech Started**: OpenAI Realtime API detects speech start
   - Event: `input_audio_buffer.speech_started`
   - Action: Send `userStream.speech.started` to AudioCodes

2. **Speech Stopped**: OpenAI Realtime API detects speech end
   - Event: `input_audio_buffer.speech_stopped`
   - Action: Send `userStream.speech.stopped` to AudioCodes

3. **Speech Committed**: OpenAI Realtime API commits speech for processing
   - Event: `input_audio_buffer.committed`
   - Action: Send `userStream.speech.committed` to AudioCodes

### When VAD is Disabled

- VAD event handlers are not registered
- VAD events from OpenAI are ignored
- AudioCodes handles speech detection natively

## VAD Message Types

The following AudioCodes message types are used for VAD:

### userStream.speech.started
```json
{
  "type": "userStream.speech.started",
  "conversationId": "conversation-id",
  "participantId": "caller" // Optional, for agent-assist calls
}
```

### userStream.speech.stopped
```json
{
  "type": "userStream.speech.stopped",
  "conversationId": "conversation-id",
  "participantId": "caller" // Optional, for agent-assist calls
}
```

### userStream.speech.committed
```json
{
  "type": "userStream.speech.committed",
  "conversationId": "conversation-id",
  "participantId": "caller" // Optional, for agent-assist calls
}
```

## Implementation Details

### Bridge Configuration

The VAD configuration is passed to the bridge during initialization:

```python
# Create bridge with VAD enabled
bridge = AudioCodesBridge(
    websocket, 
    connection.websocket, 
    session_config,
    vad_enabled=True  # Enable VAD
)
```

### Event Handler Registration

VAD event handlers are registered conditionally:

```python
# Register handlers only if VAD is enabled
if self.vad_enabled:
    self.event_router.register_realtime_handler(
        "input_audio_buffer.speech_started", 
        self.handle_speech_started
    )
    # ... other handlers
```

### Event Processing

VAD events are processed with safety checks:

```python
async def handle_speech_started(self, data: dict):
    if not self.vad_enabled:
        logger.warning("VAD disabled - ignoring speech started event")
        return
    
    await self.send_speech_started()
```

## Testing and Validation

### Running VAD Tests

Run the VAD validation script to test the configuration:

```bash
python scripts/validate_vad_config.py
```

### Unit Tests

Run the AudioCodes bridge tests to validate VAD functionality:

```bash
pytest tests/opusagent/bridges/test_audiocodes_bridge.py -v
```

### Test Coverage

The VAD implementation includes tests for:
- Configuration loading from environment variables
- Event handler registration (enabled/disabled)
- Event processing behavior
- Message generation and serialization
- Model validation

## Benefits of VAD

### When to Enable VAD

- **Better timing control**: More precise speech detection
- **Reduced latency**: Faster response to speech events
- **Enhanced barge-in**: Better interrupt handling
- **Improved user experience**: More natural conversation flow

### When to Disable VAD

- **AudioCodes native VAD**: When AudioCodes platform handles VAD better
- **Debugging**: To isolate speech detection issues
- **Compatibility**: When VAD causes issues with certain deployments

## Troubleshooting

### Common Issues

1. **VAD events not working**
   - Check `VAD_ENABLED` environment variable
   - Verify OpenAI Realtime API connection
   - Check logs for VAD event registration

2. **Unexpected speech detection**
   - Disable VAD temporarily: `VAD_ENABLED=false`
   - Check audio quality and noise levels
   - Review AudioCodes VAD settings

3. **Missing VAD events in TUI**
   - Set `TUI_SHOW_VAD_EVENTS=true`
   - Check TUI event filtering settings

### Debug Logging

Enable debug logging to see VAD events:

```python
logger.setLevel(logging.DEBUG)
```

Look for log messages like:
- `VAD handling enabled/disabled`
- `Registering VAD event handlers`
- `Speech started/stopped/committed detected`

## Migration Guide

### From AudioCodes VAD to Bot VAD

1. Set `VAD_ENABLED=true` in environment
2. Test with validation script
3. Monitor logs for VAD events
4. Adjust AudioCodes configuration if needed

### From Bot VAD to AudioCodes VAD

1. Set `VAD_ENABLED=false` in environment
2. Configure AudioCodes VAD settings
3. Test speech detection behavior
4. Monitor for timing differences

## Best Practices

1. **Test thoroughly**: Use the validation script before deployment
2. **Monitor performance**: Watch for latency changes
3. **Environment consistency**: Use same VAD settings across environments
4. **Documentation**: Document your VAD configuration choices
5. **Fallback planning**: Have AudioCodes VAD as backup option 