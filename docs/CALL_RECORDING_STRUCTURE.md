# Call Recording Structure

This document explains the structure and contents of call recordings in the system. Each call recording is stored in a directory named with the format `{conversation_id}_{timestamp}`.

## Directory Structure

```
{conversation_id}_{timestamp}/
├── call_metadata.json     # Call metadata and statistics
├── session_events.json    # Session events and function calls
├── transcript.json        # Conversation transcript
├── caller_audio.wav      # Caller's audio recording
├── bot_audio.wav         # Bot's audio recording
└── combined_audio.wav    # Combined stereo audio recording
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
- `caller_audio.wav`: Raw audio from the caller
- `bot_audio.wav`: Raw audio from the bot
- `combined_audio.wav`: Stereo recording combining both channels

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

Use the `view_call_recording.py` script to view and analyze recordings:
```bash
python scripts/view_call_recording.py {recording_directory}
```

This will open a viewer that allows you to:
- Play the combined audio
- View synchronized transcripts
- See function calls and their timing
- Navigate through the conversation 