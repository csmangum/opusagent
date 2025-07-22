# Silero VAD Implementation

This document describes the Silero Voice Activity Detection (VAD) implementation in OpusAgent, which provides real-time speech detection capabilities for telephony and conversational AI applications.

## What is Silero VAD?

Silero VAD is a pre-trained enterprise-grade Voice Activity Detector that can accurately detect speech in audio streams. It's fast, lightweight, and works well with various audio qualities and background noise levels.

**Key Features:**
- Stellar accuracy on speech detection tasks
- Fast processing (< 1ms per audio chunk)
- Lightweight (~2MB model size)
- Supports 8000 Hz and 16000 Hz sampling rates
- Works on CPU and GPU
- No strings attached (MIT license)
- Enhanced state management with speech start/stop detection
- Hysteresis implementation to prevent rapid state changes
- Timeout handling for long speech segments

## Installation

### Automatic Setup

The Silero VAD is automatically installed as part of the OpusAgent dependencies:

```bash
pip install -r requirements.txt
```

### Manual Installation

If you need to install Silero VAD separately:

```bash
pip install silero-vad
```

Or from GitHub:
```bash
pip install git+https://github.com/snakers4/silero-vad.git
```

## Usage

### Basic Integration

The Silero VAD is integrated into OpusAgent through the VAD factory pattern:

```python
from opusagent.vad.vad_factory import VADFactory
from opusagent.vad.vad_config import load_vad_config

# Load configuration from environment variables
config = load_vad_config()

# Create VAD instance
vad = VADFactory.create_vad(config)

# Process audio data
audio_data = np.random.randn(512).astype(np.float32)  # Your audio data
result = vad.process_audio(audio_data)

print(f"Speech detected: {result['is_speech']}")
print(f"Speech probability: {result['speech_prob']:.3f}")
print(f"Speech state: {result['speech_state']}")
```

### Configuration

VAD configuration is managed through environment variables:

```bash
# VAD Backend
export VAD_BACKEND=silero

# Audio Settings
export VAD_SAMPLE_RATE=16000
export VAD_CHUNK_SIZE=512

# Detection Thresholds
export VAD_CONFIDENCE_THRESHOLD=0.5
export VAD_SILENCE_THRESHOLD=0.6

# Timing Settings
export VAD_MIN_SPEECH_DURATION_MS=500
export VAD_FORCE_STOP_TIMEOUT_MS=2000

# Device Settings
export VAD_DEVICE=cpu
```

### Configuration Parameters

| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| Backend | `VAD_BACKEND` | `silero` | VAD backend to use |
| Sample Rate | `VAD_SAMPLE_RATE` | `16000` | Audio sample rate (8000 or 16000) |
| Chunk Size | `VAD_CHUNK_SIZE` | `512` | Audio chunk size (auto-adjusted for sample rate) |
| Speech Threshold | `VAD_CONFIDENCE_THRESHOLD` | `0.5` | Speech detection threshold (0.0-1.0) |
| Silence Threshold | `VAD_SILENCE_THRESHOLD` | `0.6` | Silence detection threshold (0.0-1.0) |
| Min Speech Duration | `VAD_MIN_SPEECH_DURATION_MS` | `500` | Minimum speech duration in milliseconds |
| Force Stop Timeout | `VAD_FORCE_STOP_TIMEOUT_MS` | `2000` | Timeout to force speech stop in milliseconds |
| Device | `VAD_DEVICE` | `cpu` | Device to run inference on (`cpu` or `cuda`) |

## Understanding VAD Thresholds

The VAD threshold controls how sensitive the speech detection is:

- **Lower thresholds (0.1-0.3)**: More sensitive, detects more speech but may have false positives
- **Medium thresholds (0.4-0.6)**: Balanced detection, good for most use cases
- **Higher thresholds (0.7-0.9)**: Less sensitive, fewer false positives but may miss quiet speech

## Speech State Machine

The VAD implements a sophisticated state machine:

1. **Idle** - No speech detected
2. **Started** - Speech just began (requires 2 consecutive detections)
3. **Active** - Speech is ongoing
4. **Stopped** - Speech ended (3 consecutive silence detections OR timeout)

### State Transitions

```python
# Speech state transitions
result = vad.process_audio(audio_data)

if result['speech_state'] == 'started':
    # Speech just began
    print("Speech started")
elif result['speech_state'] == 'active':
    # Speech is ongoing
    print(f"Speech duration: {result['speech_duration_ms']}ms")
elif result['speech_state'] == 'stopped':
    # Speech ended
    print("Speech stopped")
    if result['force_stop']:
        print("Stopped due to timeout")
```

## Integration Examples

### With AudioStreamHandler

The VAD is automatically integrated with the `AudioStreamHandler`:

```python
from opusagent.audio_stream_handler import AudioStreamHandler

# VAD is automatically initialized and enabled
handler = AudioStreamHandler(platform_websocket, realtime_websocket)

# Audio processing includes VAD
await handler.handle_incoming_audio(audio_data)
```

### With MockAudioCodesClient

VAD is integrated with the mock client for realistic speech detection:

```python
from opusagent.local.audiocodes.client import MockAudioCodesClient

client = MockAudioCodesClient()
async with client as session:
    # VAD automatically processes audio and generates speech events
    await session.start_conversation()
```

### With LocalRealtimeClient

VAD can be enabled for turn detection:

```python
from opusagent.local.realtime.client import LocalRealtimeClient

config = {
    'turn_detection': {
        'type': 'server_vad'
    }
}

client = LocalRealtimeClient(session_config=config)
# VAD will be automatically enabled for turn detection
```

## Return Values

The `process_audio()` method returns a comprehensive result dictionary:

```python
result = vad.process_audio(audio_data)

# Core detection
speech_prob = result['speech_prob']        # 0.0 to 1.0
is_speech = result['is_speech']           # Boolean

# State information
speech_state = result['speech_state']      # 'idle', 'started', 'active', 'stopped'
force_stop = result['force_stop']         # Boolean (timeout-based stop)
speech_duration_ms = result['speech_duration_ms']  # Current speech duration

# Internal counters
consecutive_speech_count = result['consecutive_speech_count']
consecutive_silence_count = result['consecutive_silence_count']
```

## Testing

### Unit Tests

Run the VAD unit tests:

```bash
pytest tests/opusagent/vad/test_silero_vad.py -v
```

### Integration Testing

Test VAD with the mock client:

```bash
python -m opusagent.local.audiocodes.example_usage
```

## Troubleshooting

### Common Issues

1. **"module 'silero_vad' has no attribute 'load_silero_vad'"**
   - The API has changed. Reinstall Silero VAD: `pip install --upgrade silero-vad`

2. **Import errors**
   - Install dependencies: `pip install silero-vad torch torchaudio`

3. **Poor VAD performance**
   - Try different sensitivity thresholds
   - Ensure good microphone quality
   - Test in a quiet environment first
   - Check audio format (should be float32, -1.0 to 1.0, mono)

4. **High CPU usage**
   - Use GPU if available: `export VAD_DEVICE=cuda`
   - Reduce chunk size for faster processing
   - Consider disabling VAD if not needed

### Performance Tips

- Use GPU if available: `export VAD_DEVICE=cuda`
- Lower chunk sizes for faster response: `export VAD_CHUNK_SIZE=256`
- Test in your actual usage environment for best results
- Monitor consecutive counters for tuning hysteresis

## Advanced Usage

### Custom VAD Configuration

```python
from opusagent.vad.silero_vad import SileroVAD

# Create custom VAD instance
vad = SileroVAD()

# Custom configuration
config = {
    'sample_rate': 16000,
    'threshold': 0.3,                    # More sensitive
    'silence_threshold': 0.4,            # Lower silence threshold
    'min_speech_duration_ms': 300,       # Shorter minimum duration
    'force_stop_timeout_ms': 5000,       # Longer timeout
    'device': 'cuda'                     # Use GPU
}

vad.initialize(config)
```

### State Management

```python
# Reset VAD state for new session
vad.reset()

# Clean up resources when done
vad.cleanup()
```

## Resources

- [Silero VAD GitHub Repository](https://github.com/snakers4/silero-vad)
- [Silero VAD Documentation](https://github.com/snakers4/silero-vad#readme)
- [PyTorch Documentation](https://pytorch.org/docs/)
- [OpusAgent VAD Implementation](opusagent/vad/silero_vad.py)

## License

This implementation is part of the OpusAgent project and follows the same license terms. Silero VAD is licensed under MIT. 