# Call Review Interface - Feature Request

## Overview
Create a comprehensive call review interface that allows users to analyze phone calls in detail, including audio playback, transcript review, log analysis, function call tracking, and state machine visualization.

## Problem Statement
Currently, there's no unified way to review completed calls with all their associated data. Users need to manually piece together information from multiple sources (audio files, logs, transcripts, etc.) to understand what happened during a call.

## Proposed Solution
Build a dedicated call review interface that consolidates all call-related data into a single, interactive dashboard.

## Core Review Tasks & Required Views

A reviewer typically wants to:

1. **Scan call metadata** (who, when, duration, result, sentiment, etc.)
2. **Scrub through the stereo recording** and listen to either channel or the mix
3. **Read the synced transcript** with speaker labels
4. **Inspect real-time logs** (INFO, WARN, ERROR) and filter by module
5. **Inspect function calls / tool invocations** issued by the agent
6. **Inspect the conversation state machine timeline** and transitions
7. **Jump to any event** (audio, transcript line, state change, error) and have every other panel stay in sync

## Re-usable Components

### Existing TUI Panels to Repurpose
- `audio_panel.py` – already handles waveform + playback controls
- `transcript_panel.py` – prints timestamped transcript lines
- `events_panel.py` – generic event list; good for log records
- `function_calls_panel.py` – lists function calls with args/return
- `status_bar.py` – bottom hints + global status
- `connection_panel.py` – can be adapted to house metadata
- `controls_panel.py` – can be adapted for "Review Mode" shortcuts

### Existing Code to Leverage
- `call_recorder.py` – has audio + event capture logic
- `transcript_manager.py` and `models/conversation.py` – transcript & messages
- `fsa/*` – state machine objects that can expose transition history
- Log files already written under `logs/`

## New Components Required

### 1. MetadataPanel
- Static table displaying: call ID, caller number, scenario, duration, result, scores
- Read-only view of call summary information

### 2. StateTimelinePanel
- Horizontal bar chart or list view showing FSA states over time
- Visual representation of state transitions with timestamps

### 3. WaveformPanel (Enhanced Audio Visualization)
- Dual-channel waveform with markers for key events
- Optional enhancement to existing AudioPanel

### 4. Search/FilterBox
- One-line input that filters transcript, logs, and function calls simultaneously
- Real-time filtering across all panels

## Proposed Screen Layout

```
┌───────────────────────────────────────────────────────────────────────────┐
│ MetadataPanel (top row, full width)                                       │
├───────────────┬───────────────────────┬───────────────────────────────────┤
│ Transcript    │ AudioPanel           │ StateTimelinePanel                │
│ Panel         │ (waveform + player)  │                                   │
│ (scrollable)  │                       │                                   │
│               │                       │                                   │
├───────────────┴─────────┬─────────────┴───────────────────────────────────┤
│ FunctionCallsPanel      │ EventsPanel / LogPanel                         │
│ (list, selectable)      │ (filterable, color-coded)                      │
├─────────────────────────┴─────────────────────────────────────────────────┤
│ StatusBar (keyboard hints, file path, current playback time, etc.)       │
└───────────────────────────────────────────────────────────────────────────┘
```

## Key Interactions

- **Synchronized Navigation**: Selecting any row in Transcript, Function Calls, or Logs seeks the AudioPanel and highlights the corresponding timestamp in every view
- **Playback Controls**: Space/Enter toggles play/pause
- **Scrubbing**: Left/Right arrows scrub ±5s; Shift+ arrows ±30s
- **Search**: `/` focuses the SearchBox; typing filters panels live
- **Panel Focus**: Tab/Ctrl+Tab to cycle between panels

## Data Synchronization Architecture

### 1. ReviewSession Model
A central "ReviewSession" model (new) that owns:
- `metadata` dict
- `AudioBuffer` (numpy array or WAV path)
- `transcript` (list of Message objects)
- `event_list` (LogEvent objects)
- `fsa_transitions` (state, start_ts, end_ts)

### 2. Message Bus Integration
Every panel subscribes to a shared `MessageBus` (already used in TUI) so that:
- `SEEK(ts)` broadcasts → all panels jump to nearest item ≥ ts
- `FILTER(q)` → panels update their local datasets
- `STATE_CHANGE(state)` → StateTimelinePanel updates

## Implementation Phases

### Phase 1: Static Review (MVP)
- [ ] Build MetadataPanel + hook AudioPanel to a pre-recorded `.wav`
- [ ] Load transcript JSON and display in TranscriptPanel
- [ ] Allow transcript row click → audio seek
- [ ] Basic keyboard navigation

### Phase 2: Event Deep-dive
- [ ] Populate EventsPanel from `logs/*.log` or DB
- [ ] Add FunctionCallsPanel (reuse existing)
- [ ] Keyboard shortcuts for filtering
- [ ] Cross-panel synchronization

### Phase 3: State Visualization
- [ ] Generate `fsa_transitions` from `states.Manager` history
- [ ] Render as timeline; clicking a bar jumps to that period
- [ ] State transition details on hover/click

### Phase 4: Polish & Enhancement
- [ ] Add search box, theme switcher
- [ ] Export to CSV / HTML functionality
- [ ] Performance optimizations for large calls
- [ ] Possibly split into standalone web React app

## Technical Considerations

### Technology Stack
- **Primary**: Stay with Rich/Textual for fastest path—repo is already set up
- **Future**: For web version, reuse layouts but implement with React + Chakra/Material-UI; audio waveform via wavesurfer.js

### Data Persistence
- Persist review sessions as JSON alongside `.wav` in `demo/` or S3 bucket
- Load on demand based on call ID
- Cache frequently accessed data

### Performance
- Lazy load large transcript/log files
- Virtual scrolling for long lists
- Audio streaming for large files

## Files to Create/Modify

### New Files
- `tui/review_main.py` - Main review interface application
- `tui/components/metadata_panel.py` - Call metadata display
- `tui/components/state_timeline_panel.py` - State machine visualization
- `tui/components/search_filter_box.py` - Global search/filter
- `tui/models/review_session.py` - Review session data model
- `tui/models/review_session_loader.py` - Data loading utilities

### Modified Files
- `tui/main.py` - Add review mode entry point
- `tui/components/audio_panel.py` - Enhance with event markers
- `tui/components/transcript_panel.py` - Add click-to-seek functionality
- `tui/components/events_panel.py` - Add filtering capabilities
- `tui/components/function_calls_panel.py` - Add timestamp synchronization

## Acceptance Criteria

### Functional Requirements
- [ ] Load and display call metadata from JSON files
- [ ] Play audio files with scrubbing controls
- [ ] Display synchronized transcript with speaker labels
- [ ] Show function calls with timestamps and parameters
- [ ] Display log events with filtering by level/module
- [ ] Visualize state machine transitions over time
- [ ] Synchronized navigation across all panels
- [ ] Keyboard shortcuts for common actions

### Non-Functional Requirements
- [ ] Load review session in < 2 seconds
- [ ] Smooth audio playback without stuttering
- [ ] Responsive UI that handles large datasets
- [ ] Memory efficient for calls > 1 hour
- [ ] Accessible keyboard navigation

### Testing Requirements
- [ ] Unit tests for ReviewSession model
- [ ] Integration tests for panel synchronization
- [ ] Performance tests for large call files
- [ ] UI tests for keyboard interactions

## Dependencies

### Internal Dependencies
- Existing TUI framework and components
- Call recording and transcript systems
- FSA state management
- Logging infrastructure

### External Dependencies
- Rich/Textual (already in use)
- Audio processing libraries (already in use)
- JSON parsing (standard library)

## Risks & Mitigation

### Technical Risks
- **Large file handling**: Implement streaming and lazy loading
- **Memory usage**: Profile and optimize data structures
- **Audio synchronization**: Use precise timestamp matching

### UX Risks
- **Complex interface**: Start with MVP and iterate based on feedback
- **Performance issues**: Implement loading states and progress indicators

## Success Metrics
- Time to review a 10-minute call < 5 minutes
- User satisfaction score > 4.0/5.0
- Zero data synchronization bugs
- < 100ms response time for panel interactions

## Future Enhancements
- Web-based version for remote access
- Collaborative review features
- AI-powered call analysis and insights
- Integration with call center analytics
- Export to various formats (PDF, video, etc.)

## Related Issues
- Link to any existing call analysis features
- Link to performance optimization tickets
- Link to UI/UX improvement tickets

---

**Labels**: `enhancement`, `ui/ux`, `call-analysis`, `tui`
**Milestone**: v2.0.0
**Priority**: High
**Estimated Story Points**: 21 