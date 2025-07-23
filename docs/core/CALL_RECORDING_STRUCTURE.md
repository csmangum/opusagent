# Call Recording Structure

This document explains the structure and contents of call recordings in the system. Each call recording is stored in a directory named with the format `{conversation_id}_{timestamp}`.

## Directory Structure

```
{conversation_id}_{timestamp}/
├── call_metadata.json           # Call metadata and statistics
├── session_events.json          # Session events and function calls
├── transcript.json              # Conversation transcript
├── caller_audio.wav            # Caller's audio recording
├── bot_audio.wav               # Bot's audio recording
├── stereo_recording.wav        # Real-time stereo recording
└── final_stereo_recording.wav  # Final combined stereo recording
```

## File Contents

### 1. call_metadata.json
Contains metadata about the call including:
- Conversation and session IDs
- Start and end times
- Duration
- Audio statistics:
  - Number of audio chunks
  - Total audio bytes
  - Audio duration for both caller and bot
- Number of transcript entries
- List of function calls with their:
  - Timestamps
  - Function names
  - Arguments
  - Results
  - Call IDs

### 2. session_events.json
Records all session events including:
- Recording start/end events
- Function calls with:
  - Timestamps
  - Function names
  - Arguments
  - Results
  - Call IDs
- Event types and their associated data

### 3. transcript.json
Contains the complete conversation transcript with:
- Conversation and session IDs
- Start and end times
- Individual transcript entries with:
  - Timestamps
  - Channel (caller/bot)
  - Type (input/output)
  - Text content
  - Confidence scores (if available)
  - Duration (if available)

### 4. Audio Files
- `caller_audio.wav`: Raw audio from the caller (16kHz, mono)
- `bot_audio.wav`: Raw audio from the bot (16kHz, mono)
- `stereo_recording.wav`: Real-time stereo recording (16kHz, 2 channels)
- `final_stereo_recording.wav`: Final combined stereo recording (Left=Caller, Right=Bot)

## Audio Processing Details

### Sample Rate Handling
- **Caller Audio**: Typically 16kHz (telephony standard)
- **Bot Audio**: Originally 24kHz (OpenAI Realtime API), resampled to 16kHz for consistency
- **Target Rate**: 16kHz for all final recordings
- **Format**: 16-bit PCM, WAV files

### Stereo Recording Process
1. **Real-time Recording**: `stereo_recording.wav` is created during the call
2. **Final Processing**: `final_stereo_recording.wav` is created after the call ends
3. **Channel Assignment**: Left channel = Caller, Right channel = Bot
4. **Resampling**: Bot audio is resampled from 24kHz to 16kHz for consistency

## Synchronization

The recording system maintains synchronization between different components:

1. **Timestamp-based Alignment**
   - All events, transcripts, and audio chunks are timestamped
   - Timestamps are in UTC format for consistency
   - Events can be replayed in chronological order

2. **Channel Separation**
   - Caller and bot audio are recorded separately
   - Transcripts are tagged with their source (caller/bot)
   - Function calls are linked to specific points in the conversation

3. **Event Tracking**
   - Function calls are recorded with their exact timing
   - Transcript entries are linked to their corresponding audio
   - Session events provide context for the conversation flow

## Example Usage

The recording structure allows for:
- Replaying the entire conversation with synchronized audio and transcripts
- Analyzing function calls and their timing
- Reviewing the conversation flow
- Extracting specific parts of the conversation
- Analyzing call duration and audio statistics
- Tracking the progression of the conversation through function calls

## Viewing Recordings

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