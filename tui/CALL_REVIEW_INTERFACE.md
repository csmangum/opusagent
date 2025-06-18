# Call Review Interface Implementation

This document describes the implemented Call Review Interface feature for analyzing completed phone calls in the OpusAgent TUI system.

## Overview

The Call Review Interface provides a comprehensive TUI-based system for reviewing completed calls with synchronized navigation across multiple data sources including audio recordings, transcripts, logs, function calls, and state machine transitions.

## Architecture

### Core Components

#### 1. Data Models (`tui/models/`)

**`review_session.py`** - Central data model
- `ReviewSession`: Main class managing all call review data
- `CallMetadata`: Call metadata (duration, caller, result, etc.)
- `TranscriptEntry`: Individual transcript entries with timestamps
- `LogEntry`: Log entries with levels and modules
- `FunctionCall`: Function call records with arguments and results
- `StateTransition`: State machine transition records

**`review_session_loader.py`** - Data loading utilities
- `ReviewSessionLoader`: Loads review sessions from various sources
- Scans demo directories for available sessions
- Creates demo sessions with sample data
- Handles multiple file formats and structures

#### 2. UI Components (`tui/components/`)

**`metadata_panel.py`** - Call metadata display
- Shows call ID, caller, scenario, duration, result, sentiment
- Color-coded display based on call outcome
- Compact 3-line layout at top of interface

**`state_timeline_panel.py`** - State machine visualization
- Visual timeline of state transitions
- Clickable state blocks for seeking
- Color-coded states (idle, active, processing, error)
- Navigation controls for previous/next state

**`search_filter_box.py`** - Global search and filtering
- Real-time filtering across all panels
- Search statistics display
- Keyboard shortcuts (Enter to apply, Esc to clear)
- Results counters for transcript, logs, and functions

#### 3. Main Application (`tui/review_main.py`)

**`CallReviewInterface`** - Main review application
- Session selector interface
- Synchronized panel management
- Keyboard navigation and shortcuts
- Integration with existing TUI components

## Features Implemented

### ✅ Core Functionality

1. **Session Loading**
   - Automatic discovery of call sessions in demo directories
   - Manual session directory loading
   - Demo session generation with sample data
   - Multiple file format support (JSON, WAV, log files)

2. **Data Synchronization**
   - Timestamp-based navigation across all panels
   - Click-to-seek functionality on timeline states
   - Global filtering with real-time updates
   - Event-driven architecture for panel communication

3. **UI Layout**
   - Metadata panel (top, 3 lines)
   - Search/filter box (top, 3 lines) 
   - State timeline (left panel, 8-12 lines)
   - Transcript panel (left panel, expandable)
   - Audio controls (left panel, 8-12 lines)
   - Events/logs panel (right panel, 40%)
   - Function calls panel (right panel, 30%)

4. **Navigation Controls**
   - Arrow keys for seeking (±5s, ±30s with Shift)
   - Home/End for start/end seeking
   - Space for play/pause (placeholder)
   - Tab navigation between panels

5. **Search and Filtering**
   - Case-insensitive text search
   - Filters across transcript, logs, and function calls
   - Real-time result counts
   - Clear and apply controls

### ✅ Keyboard Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| `q` | Quit | Exit application |
| `l` | Load Session | Load selected session or show selector |
| `d` | Demo Session | Load demo session with sample data |
| `/` | Focus Filter | Focus search/filter box |
| `h` | Help | Show help information |
| `Space` | Play/Pause | Toggle audio playback (placeholder) |
| `←/→` | Seek ±5s | Navigate forward/backward 5 seconds |
| `Shift+←/→` | Seek ±30s | Navigate forward/backward 30 seconds |
| `Home/End` | Start/End | Seek to beginning/end |
| `Ctrl+R` | Reload | Reload current session |
| `Ctrl+C` | Clear | Clear all filters |

### ✅ Data Loading

The system supports loading from:
- **Demo directories**: `demo/`, `demo/no_hang_up/`, `validation_output/`
- **Expected file structure**:
  ```
  call_directory/
  ├── call_metadata.json       # Call metadata
  ├── transcript.json          # Conversation transcript
  ├── session_events.json      # Function calls and state transitions
  ├── final_stereo_recording.wav # Audio file
  └── [call_id].log           # Log file (optional)
  ```

### ✅ Demo Data

The system includes a built-in demo session with:
- 13 transcript entries (user/bot conversation)
- 3 function calls (account lookup, card cancellation, replacement order)
- 10 log entries (session events, function execution)
- 8 state transitions (greeting → listening → processing → closing)
- Sample metadata (card replacement scenario)

## Integration Points

### With Existing TUI

The review interface integrates with the existing TUI system:

1. **Main TUI Integration** (`tui/main.py`)
   - Added `Ctrl+M` shortcut to launch review mode
   - Review interface runs as separate process
   - Notification system for launch status

2. **Component Reuse**
   - Leverages existing `TranscriptPanel`
   - Reuses `EventsPanel` for log display
   - Integrates with `FunctionCallsPanel`
   - Uses existing `AudioPanel` framework
   - Maintains `StatusBar` consistency

3. **Shared Models**
   - Compatible with existing session management
   - Follows established logging patterns
   - Uses consistent event handling

## Usage

### Starting the Review Interface

1. **From Main TUI**: Press `Ctrl+M` to launch review mode
2. **Standalone**: Run `python tui/review_main.py`
3. **With Demo**: Run `python tui/review_main.py --demo`
4. **Specific Session**: Run `python tui/review_main.py --session-dir path/to/session`

### Basic Workflow

1. **Session Selection**: Choose from available sessions or load demo
2. **Navigation**: Use keyboard shortcuts to seek through the call
3. **Filtering**: Type in search box to filter content across panels
4. **Analysis**: Click timeline states to jump to specific conversation phases
5. **Review**: Examine transcript, logs, and function calls in sync

### Example Demo Session Review

The demo session simulates a card replacement call:
- **0:00-0:03**: Bot greeting
- **0:03-0:15**: User reports lost card
- **0:15-0:22**: Account number collection
- **0:22-0:30**: Account lookup and card cancellation
- **0:30-0:50**: Replacement card ordering and confirmation

## File Structure

```
tui/
├── components/
│   ├── metadata_panel.py           # NEW: Call metadata display
│   ├── state_timeline_panel.py     # NEW: State transition timeline
│   └── search_filter_box.py        # NEW: Global search/filter
├── models/
│   ├── review_session.py           # NEW: Core review data model
│   └── review_session_loader.py    # NEW: Data loading utilities
├── review_main.py                  # NEW: Main review application
├── main.py                         # MODIFIED: Added review mode shortcut
└── CALL_REVIEW_INTERFACE.md        # NEW: This documentation
```

## Future Enhancements

### Planned Improvements

1. **Audio Integration**
   - Actual audio playback synchronized with timeline
   - Waveform visualization with event markers
   - Audio scrubbing controls

2. **Enhanced Transcript Panel**
   - Click-to-seek on transcript entries
   - Confidence score visualization
   - Speaker diarization display

3. **Function Calls Panel Enhancement**
   - Click-to-seek on function call timestamps
   - Expandable argument/result display
   - Execution time visualization

4. **Export Functionality**
   - Export filtered results to CSV/JSON
   - Generate call analysis reports
   - Save review sessions

5. **Performance Optimizations**
   - Virtual scrolling for large datasets
   - Lazy loading of audio files
   - Caching for frequently accessed sessions

### Web Interface Migration

Future versions could migrate to a web-based interface:
- React/TypeScript frontend
- WebSocket for real-time updates
- Web Audio API for playback
- Canvas/SVG for timeline visualization
- Persistent session storage

## Technical Details

### Data Flow

1. **Loading**: `ReviewSessionLoader` scans directories and creates `ReviewSession`
2. **Filtering**: `ReviewSession` applies filters to create filtered data lists
3. **Navigation**: Seek events propagate through observer pattern
4. **Display**: Each panel subscribes to session events and updates accordingly

### Error Handling

- Graceful degradation when audio files missing
- Fallback to basic display when dependencies unavailable
- Comprehensive logging for debugging
- User-friendly error messages

### Dependencies

- **Required**: `textual` (TUI framework), existing OpusAgent dependencies
- **Optional**: `soundfile` (audio loading), `numpy` (audio processing)
- **Fallback**: Text-only mode when audio dependencies missing

## Testing

### Manual Testing

1. **Demo Session**: `python tui/review_main.py --demo`
2. **Session Discovery**: Place test files in `demo/` directory
3. **Integration**: Launch from main TUI with `Ctrl+M`

### Test Data Format

Create test sessions with this structure:
```json
// call_metadata.json
{
  "caller_number": "+1-555-0123",
  "scenario": "Test Scenario",
  "duration_seconds": 120.0,
  "result": "Success",
  "sentiment": "Positive"
}

// transcript.json
[
  {"timestamp": 0.0, "speaker": "bot", "text": "Hello!"},
  {"timestamp": 3.0, "speaker": "user", "text": "Hi there!"}
]

// session_events.json
{
  "events": [
    {
      "type": "function_call",
      "timestamp": 10.0,
      "function_name": "test_function",
      "arguments": {"param": "value"}
    }
  ]
}
```

## Conclusion

The Call Review Interface provides a comprehensive solution for analyzing completed calls with:
- ✅ Synchronized multi-panel navigation
- ✅ Global search and filtering
- ✅ State machine visualization
- ✅ Comprehensive keyboard controls
- ✅ Integration with existing TUI system
- ✅ Extensible architecture for future enhancements

The implementation follows the original feature request specifications and provides a solid foundation for call analysis workflows.