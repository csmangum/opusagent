# Call Recording System

The OpusAgent telephony bridge now includes comprehensive call recording functionality that captures both audio and transcripts from conversations between callers and the AI bot.

## 📁 What Gets Recorded

When a call is made, the system automatically creates a recording directory with the following structure:

```
call_recordings/
└── {session_id}_{timestamp}/
    ├── caller_audio.wav          # Caller's audio only (mono)
    ├── bot_audio.wav             # Bot's audio only (mono)  
    ├── stereo_recording.wav      # Real-time stereo recording
    ├── final_stereo_recording.wav # Final combined stereo (Left=Caller, Right=Bot)
    ├── transcript.json           # Complete transcript with timestamps
    ├── call_metadata.json        # Call statistics and metadata
    └── session_events.json       # Detailed session events log
```

## 🎵 Audio Format

- **Sample Rate**: 16kHz (target rate for all recordings)
- **Bit Depth**: 16-bit PCM
- **Caller Audio**: Left channel in stereo files (typically 16kHz input)
- **Bot Audio**: Right channel in stereo files (24kHz input resampled to 16kHz)
- **Format**: WAV (uncompressed)
- **Processing**: Bot audio is resampled from 24kHz (OpenAI Realtime API) to 16kHz for consistency

## 📝 Transcript Format

The `transcript.json` file contains:

```json
{
  "conversation_id": "12345",
  "session_id": "session_456", 
  "start_time": "2024-12-01T14:30:22.123456Z",
  "end_time": "2024-12-01T14:32:15.789012Z",
  "entries": [
    {
      "timestamp": "2024-12-01T14:30:25.123456Z",
      "channel": "caller",
      "type": "input", 
      "text": "Hello, I need help with my card",
      "confidence": 0.95,
      "duration_ms": 2500
    },
    {
      "timestamp": "2024-12-01T14:30:27.654321Z",
      "channel": "bot",
      "type": "output",
      "text": "Hello! I'd be happy to help you with your card. What seems to be the issue?",
      "confidence": null,
      "duration_ms": 3200
    }
  ]
}
```

## 📊 Call Metadata

The `call_metadata.json` includes comprehensive statistics:

```json
{
  "conversation_id": "12345",
  "session_id": "session_456",
  "start_time": "2024-12-01T14:30:22.123456Z", 
  "end_time": "2024-12-01T14:32:15.789012Z",
  "duration_seconds": 113.5,
  "caller_audio_chunks": 45,
  "bot_audio_chunks": 38,
  "caller_audio_bytes": 144000,
  "bot_audio_bytes": 121600,
  "caller_audio_duration_seconds": 4.5,
  "bot_audio_duration_seconds": 3.8,
  "transcript_entries": 12,
  "function_calls": [
    {
      "timestamp": "2024-12-01T14:30:35.123456Z",
      "function_name": "call_intent",
      "arguments": {"intent": "card_replacement"},
      "result": {"status": "success", "available_cards": ["Gold", "Silver"]},
      "call_id": "call_789"
    }
  ]
}
```

## 🛠️ Viewing Recordings

Recordings can be analyzed by examining the files directly:

### Audio Playback
- Use any audio player that supports WAV files
- `caller_audio.wav` and `bot_audio.wav` for individual channels
- `stereo_recording.wav` or `final_stereo_recording.wav` for combined audio

### Transcript Analysis
- Open `transcript.json` in any text editor or JSON viewer
- Entries are chronologically ordered with timestamps
- Channel and type information helps distinguish caller vs bot speech

### Metadata Review
- `call_metadata.json` contains call statistics and function call history
- `session_events.json` provides detailed event timeline
- Both files are in JSON format for easy parsing

### Programmatic Access
```python
import json
from pathlib import Path

# Load recording data
recording_dir = Path("call_recordings/session_123_20241201_143022")

# Load metadata
with open(recording_dir / "call_metadata.json") as f:
    metadata = json.load(f)

# Load transcript
with open(recording_dir / "transcript.json") as f:
    transcript = json.load(f)

# Load session events
with open(recording_dir / "session_events.json") as f:
    events = json.load(f)
```

## 🎧 Audio Playback

The viewer attempts to use system audio players in this order:
- **macOS**: `afplay`, then system `open`
- **Linux**: `aplay`, `paplay`, `play`, then `xdg-open`  
- **Windows**: `start` (shell command)

If no player is found, it will attempt to open the file with the system's default audio application.

## 🔧 Configuration

### Recording Directory
By default, recordings are saved to `call_recordings/`. You can change this by modifying the `CallRecorder` initialization in `telephony_realtime_bridge.py`:

```python
self.call_recorder = CallRecorder(
    conversation_id=self.conversation_id,
    session_id=self.conversation_id,
    base_output_dir="custom_recordings_path"  # Change this
)
```

### Disable Recording
To disable call recording, comment out the recorder initialization in the `handle_session_initiate` method:

```python
# # Initialize call recorder
# if self.conversation_id:
#     self.call_recorder = CallRecorder(...)
```

## 📈 Use Cases

### Quality Assurance
- Review call transcripts for AI response quality
- Analyze conversation flow and function calls
- Identify areas for improvement in bot responses

### Debugging
- Compare audio timing with transcript timestamps
- Review function call sequences and results
- Debug audio processing issues

### Analytics  
- Measure conversation duration and speech time ratios
- Analyze most common function calls and intents
- Track conversation success rates

### Compliance
- Maintain records of customer interactions
- Export transcripts for regulatory requirements
- Archive conversations with full metadata

## 🚀 Advanced Usage

### Programmatic Access
You can also access recordings programmatically:

```python
from opusagent.models.call_recorder import CallRecorder
from pathlib import Path
import json

# Load a recording
recording_dir = Path("call_recordings/session_123_20241201_143022")

# Load metadata
with open(recording_dir / "call_metadata.json") as f:
    metadata = json.load(f)

# Load transcript  
with open(recording_dir / "transcript.json") as f:
    transcript = json.load(f)

print(f"Call duration: {metadata['duration_seconds']} seconds")
print(f"Transcript entries: {len(transcript['entries'])}")
```

### Custom Analysis
Build custom analysis tools using the structured JSON data:

```python
import json
from pathlib import Path
from datetime import datetime

def analyze_conversation_patterns(recording_dir):
    """Analyze patterns in a recorded conversation."""
    transcript_file = recording_dir / "transcript.json"
    
    with open(transcript_file) as f:
        data = json.load(f)
    
    # Calculate response times
    entries = data['entries']
    response_times = []
    
    for i in range(1, len(entries)):
        if entries[i-1]['channel'] == 'caller' and entries[i]['channel'] == 'bot':
            prev_time = datetime.fromisoformat(entries[i-1]['timestamp'].replace('Z', '+00:00'))
            curr_time = datetime.fromisoformat(entries[i]['timestamp'].replace('Z', '+00:00'))
            response_time = (curr_time - prev_time).total_seconds()
            response_times.append(response_time)
    
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    print(f"Average bot response time: {avg_response_time:.2f} seconds")
    
    return {
        'response_times': response_times,
        'avg_response_time': avg_response_time
    }
```

## 🛡️ Privacy & Security

- Recordings contain sensitive customer audio and conversation data
- Ensure appropriate access controls are in place for the `call_recordings/` directory
- Consider encryption for long-term storage
- Implement data retention policies as required by your organization
- Be mindful of privacy regulations (GDPR, CCPA, etc.) when storing recordings

## 🔍 Troubleshooting

### No Audio Files Created
- Check that the telephony bridge is receiving audio chunks
- Verify the `call_recordings/` directory is writable
- Look for errors in the bridge logs related to `CallRecorder`

### Empty Transcripts
- Ensure OpenAI Realtime API is returning transcription events
- Check that `input_audio_transcription` is enabled in session config
- Verify transcript events are being handled properly

### Playback Issues
- Install a compatible audio player (`sox`, `alsa-utils`, etc.)
- Check that audio files aren't corrupted
- Try opening files manually with your preferred audio application

### Corrupted Stereo Files
- This usually indicates audio timing/synchronization issues
- Check for errors during audio buffer processing
- Verify both caller and bot audio are being recorded properly 