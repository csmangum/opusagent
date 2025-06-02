# Interactive TUI Validator Implementation Plan

## 📋 Overview

This document outlines the complete step-by-step implementation plan for the **Interactive TUI Validator for TelephonyRealtimeBridge Call Flow Testing**, based on [GitHub Issue #52](https://github.com/csmangum/fastagent/issues/52).

The TUI provides a comprehensive interface for testing AudioCodes VoiceAI Connect Enterprise (VAIC) integration with OpenAI Realtime API, featuring real-time audio playback, transcript display, and event monitoring.

## 🏗️ Architecture Overview

```
tui/
├── __init__.py                 # Package initialization
├── main.py                     # Main application entry point ✅
├── README.md                   # This implementation plan
├── components/                 # UI components ✅
│   ├── __init__.py
│   ├── connection_panel.py     # Connection status and controls ✅
│   ├── audio_panel.py          # Audio controls and visualization ✅
│   ├── events_panel.py         # Event log and monitoring ✅
│   ├── transcript_panel.py     # Real-time transcript display ✅
│   ├── controls_panel.py       # Call flow control buttons ✅
│   └── status_bar.py          # Bottom status information ✅
├── models/                     # Data models and state management
│   ├── __init__.py            ✅
│   ├── session_state.py        # Session state management
│   ├── audio_manager.py        # Audio playback/recording
│   └── event_logger.py         # Event logging and filtering
├── websocket/                  # WebSocket client and message handling
│   ├── __init__.py            ✅
│   ├── client.py              # WebSocket client wrapper
│   └── message_handler.py     # Message processing logic
└── utils/                      # Utilities and configuration
    ├── __init__.py            ✅
    ├── config.py              # Configuration management ✅
    ├── audio_utils.py         # Audio file handling
    └── helpers.py             # Utility functions ✅
```

## 📋 Complete Implementation Plan

### ✅ Phase 1: Core Infrastructure & Setup (Week 1)

#### Step 1: Dependencies & Project Structure ✅
- [x] Updated `requirements.txt` with TUI dependencies:
  - `textual>=0.41.0` - TUI framework
  - `sounddevice>=0.4.6` - Audio playback
  - `rich>=13.0.0` - Enhanced text rendering
  - `scipy>=1.11.0` - Audio processing
  - `pyaudio>=0.2.11` - Alternative audio backend
  - `librosa>=0.10.0` - Audio analysis for visualization
- [x] Created complete package structure with submodules
- [x] Implemented configuration management (`config.py`)
- [x] Created utility helpers (`helpers.py`)

#### Step 2: Basic UI Components ✅
- [x] Created main application entry point (`main.py`)
- [x] Implemented basic component stubs:
  - [x] `ConnectionPanel` - WebSocket connection management
  - [x] `ControlsPanel` - Call flow control buttons
  - [x] `AudioPanel` - Audio controls and visualization
  - [x] `EventsPanel` - Session events display
  - [x] `TranscriptPanel` - Live transcript display
  - [x] `StatusBar` - System status information

#### Step 3: Test Basic TUI Structure ✅
```bash
# Install dependencies
pip install -r requirements.txt

# Run basic TUI (should show layout with placeholder components)
python -m tui.main
```

#### Step 4: WebSocket Client Implementation ✅
- [x] Created `websocket/client.py` with `WebSocketClient` class for async connect/disconnect/send/receive
- [x] Integrated with `ConnectionPanel` for real connection management
- [x] Connection status and errors are now logged to the EventsPanel

#### Step 5: Basic Message Logging ✅
- [x] Connection/disconnection events are logged in the EventsPanel

---

### 🔄 Phase 2: WebSocket Connection Management (Week 1-2)

#### Step 6: Message Handler Implementation  
- [ ] Create `websocket/message_handler.py`:
  ```python
  class MessageHandler:
      """Handles WebSocket message processing and routing."""
      
      def handle_telephony_message(self, message: dict) -> None
      def handle_session_event(self, event_type: str, data: dict) -> None
      def handle_audio_event(self, event_type: str, data: dict) -> None
      def handle_error_event(self, error: dict) -> None
  ```

#### Step 7: Integrate WebSocket with ConnectionPanel
- [ ] Update `ConnectionPanel` to use real WebSocket client
- [ ] Implement actual connection/disconnection logic
- [ ] Add connection status monitoring and auto-reconnect
- [ ] Handle connection errors gracefully

---

### 🔄 Phase 3: Session Management (Week 2)

#### Step 8: Session State Management
- [ ] Create `models/session_state.py`:
  ```python
  class SessionState:
      """Manages session state and conversation data."""
      
      conversation_id: Optional[str]
      session_id: Optional[str] 
      media_format: str
      is_active: bool
      start_time: Optional[datetime]
      call_duration: float
  ```

#### Step 9: Session Flow Implementation
- [ ] Implement session initiation workflow:
  - Send `session.initiate` message
  - Wait for `session.accepted` response
  - Update UI with session information
- [ ] Add session termination handling:
  - Send `session.end` message
  - Clean up session state
  - Update UI status

#### Step 10: Update ControlsPanel Integration
- [ ] Connect call control buttons to session management
- [ ] Implement start/end call functionality
- [ ] Add DTMF tone sending capability
- [ ] Handle hangup events

---

### 🔄 Phase 4: Audio System Integration (Week 2-3)

#### Step 11: Audio Manager Implementation
- [ ] Create `models/audio_manager.py`:
  ```python
  class AudioManager:
      """Handles real-time audio playback and recording."""
      
      async def play_audio_chunk(self, audio_data: bytes) -> None
      async def record_audio(self) -> AsyncGenerator[bytes, None]
      def get_volume_level(self) -> float
      def load_audio_file(self, filepath: str) -> List[bytes]
  ```

#### Step 12: Audio Utilities
- [ ] Create `utils/audio_utils.py`:
  ```python
  class AudioUtils:
      """Audio file handling and processing utilities."""
      
      @staticmethod
      def load_wav_file(filepath: str) -> Tuple[bytes, int, int]
      @staticmethod  
      def chunk_audio_data(audio_data: bytes, chunk_size: int) -> List[bytes]
      @staticmethod
      def convert_to_base64(audio_data: bytes) -> str
      @staticmethod
      def visualize_audio_level(audio_data: bytes) -> str
  ```

#### Step 13: Audio Stream Management
- [ ] Implement user audio streaming:
  - Send `userStream.start` message
  - Stream audio chunks with `userStream.chunk`
  - Handle `userStream.stop` when complete
- [ ] Handle bot audio playback:
  - Receive `playStream.start` events
  - Play `playStream.chunk` audio data in real-time
  - Process `playStream.stop` events
- [ ] Add audio visualization to `AudioPanel`

#### Step 14: File Audio Integration
- [ ] Implement audio file browser dialog
- [ ] Add progress tracking for file transmission
- [ ] Support multiple audio formats (WAV, MP3)
- [ ] Integrate with existing validation audio files

---

### 🔄 Phase 5: Event System & Logging (Week 3)

#### Step 15: Event Logger Implementation
- [ ] Create `models/event_logger.py`:
  ```python
  class EventLogger:
      """Manages event logging, filtering, and export."""
      
      def log_event(self, event_type: str, direction: str, data: dict) -> None
      def filter_events(self, event_types: Set[str]) -> List[LogEvent]
      async def export_logs(self, filepath: str) -> None
      def get_statistics(self) -> Dict[str, int]
  ```

#### Step 16: Real-time Event Monitoring
- [ ] Connect EventsPanel to WebSocket message stream
- [ ] Implement event filtering and categorization
- [ ] Add real-time event counters and statistics
- [ ] Create event export functionality

#### Step 17: Message Log Integration
- [ ] Add comprehensive message logging panel
- [ ] Implement message search and filtering
- [ ] Add JSON message inspection capability
- [ ] Create log export functionality

---

### 🔄 Phase 6: Transcript System (Week 3)

#### Step 18: Transcript Processing
- [ ] Integrate with OpenAI transcription events:
  - Handle `conversation.item.input_audio_transcription.completed`
  - Process bot response transcripts
  - Extract text from response content
- [ ] Implement real-time transcript display
- [ ] Add transcript export functionality

#### Step 19: Enhanced Transcript Features
- [ ] Add transcript search capability
- [ ] Implement speaker identification
- [ ] Add timestamp synchronization with audio
- [ ] Create conversation summary generation

---

### 🔄 Phase 7: Advanced Features (Week 4)

#### Step 20: Audio Visualization
- [ ] Implement real-time waveform display using `librosa`
- [ ] Add volume level indicators
- [ ] Create audio quality metrics
- [ ] Add latency measurement and display

#### Step 21: Enhanced UI Features
- [ ] Add keyboard shortcuts and hotkeys
- [ ] Implement help system and documentation overlay
- [ ] Add customizable themes and layouts
- [ ] Create configuration management UI

#### Step 22: Performance Optimization
- [ ] Optimize audio buffer management
- [ ] Implement efficient UI update batching
- [ ] Add memory usage monitoring
- [ ] Profile and optimize critical paths

---

### 🔄 Phase 8: Testing & Polish (Week 4)

#### Step 23: Integration Testing
- [ ] Test against existing `validation_scripts/validate_session_flow.py`
- [ ] Verify compatibility with TelephonyRealtimeBridge
- [ ] Test with various audio file formats
- [ ] Validate session flow sequences

#### Step 24: Error Handling & Recovery
- [ ] Implement comprehensive error handling
- [ ] Add graceful degradation for connection issues
- [ ] Create automatic recovery mechanisms
- [ ] Add user-friendly error messages

#### Step 25: Documentation & Help
- [ ] Create comprehensive user documentation
- [ ] Add in-app help system
- [ ] Write developer documentation
- [ ] Create usage examples and tutorials

---

## 🚀 Quick Start Guide

### Running the TUI

```bash
# Navigate to project root
cd /path/to/fastagent

# Install dependencies
pip install -r requirements.txt

# Run the TUI
python -m tui.main

# Alternative entry point
python tui/main.py
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit application |
| `c` | Connect to server |
| `d` | Disconnect from server |
| `s` | Start call |
| `e` | End call |
| `h` | Show help |
| `Ctrl+R` | Restart application |

### Configuration

Environment variables for customization:

```bash
# WebSocket settings
export TUI_HOST="localhost"
export TUI_PORT="8000"
export TUI_WS_PATH="/voice-bot"

# Audio settings  
export TUI_SAMPLE_RATE="16000"
export TUI_AUDIO_FORMAT="raw/lpcm16"

# UI settings
export TUI_THEME="dark"
export TUI_SHOW_DEBUG="true"
```

## 🎯 Success Criteria

### Functional Requirements ✅
- [x] ✅ **Connection Management**: Connect/disconnect to TelephonyRealtimeBridge
- [ ] 🔄 **Session Management**: Initiate, manage, and end sessions
- [ ] 🔄 **Audio Streaming**: Stream audio to/from the bridge
- [ ] 🔄 **Real-time Playback**: Play bot responses with low latency
- [ ] 🔄 **Event Monitoring**: Display all WebSocket events in real-time
- [ ] 🔄 **Transcript Display**: Show live conversation transcripts
- [ ] 🔄 **Call Flow Controls**: Send DTMF, handle hangups, manage calls

### Non-Functional Requirements
- [ ] 🔄 **Performance**: <200ms audio latency, 60fps UI updates
- [ ] 🔄 **Usability**: Intuitive interface with keyboard shortcuts
- [ ] 🔄 **Reliability**: Graceful error handling and auto-recovery
- [ ] 🔄 **Maintainability**: Clean architecture and comprehensive tests

## 🤝 Integration Points

### Existing Components
- **TelephonyRealtimeBridge**: Main WebSocket endpoint at `/voice-bot`
- **Validation Scripts**: `validation_scripts/validate_session_flow.py`  
- **Audio Files**: `static/tell_me_about_your_bank.wav`
- **Configuration**: Environment variables and `.env` file

### Message Flow Compatibility
- **Session Flow**: `session.initiate` → `session.accepted` → `session.end`
- **Audio Flow**: `userStream.start` → `userStream.chunk` → `userStream.stop`
- **Bot Response**: `playStream.start` → `playStream.chunk` → `playStream.stop`

## 🐛 Current Status

### ✅ Completed
- [x] Project structure and dependencies
- [x] Basic UI layout and component stubs
- [x] Configuration management system
- [x] Utility functions and helpers

### 🔄 In Progress
- [ ] WebSocket client implementation
- [ ] Session management system
- [ ] Audio integration

### 📋 Next Steps
1. **Install dependencies**: `pip install -r requirements.txt`
2. **Test basic TUI**: `python -m tui.main`
3. **Implement WebSocket client** (Step 6)
4. **Add session management** (Step 8)
5. **Integrate audio system** (Step 11)

---

*This TUI will significantly improve the testing workflow for TelephonyRealtimeBridge by providing real-time visual feedback, interactive controls, and comprehensive monitoring capabilities.* 