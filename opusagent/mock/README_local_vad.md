# Local VAD Client

A real-time microphone client with local voice activity detection (VAD) that connects to your bridge server. This replaces the file-based mock client with live microphone input.

## 🎯 Features

- **Real-time microphone input** using SoundDevice
- **Local voice activity detection** using energy-based VAD
- **Automatic speech detection** - starts/stops audio streams based on speech
- **Audio playback** of responses from the bridge
- **Configurable VAD sensitivity** and silence duration
- **No external dependencies** - uses libraries you already have

## 🚀 Quick Start

### 1. Start Your Bridge Server

First, make sure your bridge server is running:

```bash
# Start the main server
python opusagent/main.py
```

### 2. Test the Local VAD Client

```bash
# Basic test (30 seconds)
python scripts/test_local_vad.py

# Custom duration and sensitivity
python scripts/test_local_vad.py --duration 60 --sensitivity 0.03

# Test different sensitivity levels
python scripts/test_local_vad.py --test-sensitivity
```

### 3. Use Programmatically

```python
import asyncio
from opusagent.mock.local_vad_client import LocalVADClient

async def main():
    async with LocalVADClient(
        bridge_url="ws://localhost:8000/caller-agent",
        vad_sensitivity=0.05,
        vad_silence_duration=1.5
    ) as client:
        await client.run_conversation(duration=30.0)

asyncio.run(main())
```

## ⚙️ Configuration

### VAD Settings

- **`vad_sensitivity`** (0.0-1.0): Energy threshold for speech detection
  - `0.02`: Very sensitive (detects quiet speech)
  - `0.05`: Normal sensitivity (default)
  - `0.1`: Less sensitive (ignores background noise)
  - `0.2`: Low sensitivity (only loud speech)

- **`vad_silence_duration`** (seconds): How long to wait before ending speech
  - `0.5`: Quick cutoff (good for fast conversations)
  - `1.0`: Normal (default)
  - `1.5`: Slower cutoff (good for pauses in speech)
  - `2.0`: Very slow (good for thinking pauses)

### Audio Settings

- **`sample_rate`**: 16000 Hz (required for bridge compatibility)
- **`chunk_size`**: 1024 samples (adjust for latency vs CPU usage)

## 🔧 How It Works

### 1. **Microphone Input**
```python
# Real-time audio capture using SoundDevice
with sd.InputStream(samplerate=16000, channels=1, callback=audio_callback):
    # Audio is processed in real-time
```

### 2. **Voice Activity Detection**
```python
def _detect_speech(self, audio_bytes: bytes) -> bool:
    # Convert to numpy array
    audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
    
    # Calculate RMS energy
    rms = np.sqrt(np.mean(audio_array ** 2))
    normalized_rms = rms / 32768.0
    
    # Compare to threshold
    return normalized_rms > self.vad_sensitivity
```

### 3. **Automatic Stream Management**
- **Speech detected** → Start `userStream.start` → Send audio chunks
- **Silence detected** → Stop `userStream.stop` → Wait for response

### 4. **Audio Playback**
- Receives `playStream.chunk` messages from bridge
- Decodes base64 audio and plays through speakers
- Handles real-time streaming playback

## 📊 VAD Tuning Guide

### For Quiet Environments
```python
LocalVADClient(
    vad_sensitivity=0.02,      # Very sensitive
    vad_silence_duration=1.0   # Normal silence
)
```

### For Noisy Environments
```python
LocalVADClient(
    vad_sensitivity=0.1,       # Less sensitive
    vad_silence_duration=1.5   # Longer silence
)
```

### For Fast Conversations
```python
LocalVADClient(
    vad_sensitivity=0.05,      # Normal sensitivity
    vad_silence_duration=0.5   # Quick cutoff
)
```

## 🐛 Troubleshooting

### No Audio Input
1. **Check microphone permissions**
2. **Verify audio device selection**
3. **Test with lower sensitivity**: `--sensitivity 0.01`

### Too Much Background Noise
1. **Increase sensitivity**: `--sensitivity 0.1`
2. **Use noise-canceling microphone**
3. **Adjust silence duration**: `--silence 2.0`

### Audio Not Playing
1. **Check speaker/headphone connection**
2. **Verify bridge is sending audio**
3. **Check audio device settings**

### High Latency
1. **Reduce chunk size**: `chunk_size=512`
2. **Use USB audio interface**
3. **Close other audio applications**

## 🔄 Comparison with File-Based Client

| Feature | File-Based Client | Local VAD Client |
|---------|------------------|------------------|
| **Input Source** | Pre-recorded WAV files | Real-time microphone |
| **VAD** | None (sends all audio) | Energy-based VAD |
| **Latency** | File processing time | Real-time |
| **Use Case** | Testing with known audio | Live conversations |
| **Setup** | Requires audio files | Just microphone |

## 🎵 Advanced Usage

### Custom Audio Processing
```python
class CustomVADClient(LocalVADClient):
    def _detect_speech(self, audio_bytes: bytes) -> bool:
        # Add your custom VAD logic here
        # e.g., frequency analysis, machine learning model
        return super()._detect_speech(audio_bytes)
```

### Multiple Microphone Support
```python
# Select specific audio device
import sounddevice as sd
print(sd.query_devices())  # List available devices

# Use device ID in your client
client = LocalVADClient(
    bridge_url="ws://localhost:8000/caller-agent",
    # Add device selection to constructor if needed
)
```

### Integration with PocketSphinx
```python
# You can combine with your existing PocketSphinx setup
from scripts.transcribe_with_pocketsphinx import PocketSphinxTranscriber

class HybridVADClient(LocalVADClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transcriber = PocketSphinxTranscriber()
    
    def _detect_speech(self, audio_bytes: bytes) -> bool:
        # Use PocketSphinx for more accurate VAD
        # This is more complex but potentially more accurate
        return super()._detect_speech(audio_bytes)
```

## 📝 Example Session

```
🎤 Local VAD Client Test
==================================================
🔗 Connecting to bridge: ws://localhost:8000/caller-agent
🎙️  Speak into your microphone to test VAD
⏱️  Test will run for 30 seconds
--------------------------------------------------
[LOCAL VAD] Connected to bridge server
[LOCAL VAD] Sent session.initiate for conversation: abc123...
[LOCAL VAD] Session accepted with format: raw/lpcm16
[LOCAL VAD] Speech detected - starting stream
[LOCAL VAD] User stream started
[LOCAL VAD] Received from bridge: playStream.start
[LOCAL VAD] Play stream started: 1
[LOCAL VAD] Speech ended - stopping stream
[LOCAL VAD] User stream stopped
[LOCAL VAD] Play stream stopped: 1
✅ Test completed successfully
```

## 🔗 Related Files

- `opusagent/mock/local_vad_client.py` - Main VAD client implementation
- `scripts/test_local_vad.py` - Test script
- `opusagent/mock/mock_audiocodes_client.py` - Original file-based client
- `opusagent/main.py` - Bridge server
- `requirements.txt` - Dependencies (SoundDevice, NumPy, etc.) 