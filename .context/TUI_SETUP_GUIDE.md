# 🎵 Enhanced TUI Validator with Soundboard

## Quick Start Guide

Your TUI now includes a **soundboard feature** for rapid call flow testing! Here's how to use it:

### 🚀 Setup and Launch

1. **Install dependencies** (if not already done):
```bash
pip install textual sounddevice rich scipy librosa
```

2. **Start your TelephonyRealtimeBridge server** (in another terminal):
```bash
python run_opus_server.py
```

3. **Launch the enhanced TUI**:
```bash
python -m tui.main
```

### 🎯 Your Use Case: Live Call Testing

The TUI is now perfectly set up for your specific needs:

#### 1. **Connect and Start Session**
- Press `c` to connect to WebSocket endpoint
- Press `s` to start a session
- ✅ Connection status shows in top panel

#### 2. **Soundboard for Caller Phrases**
- **12 predefined phrases** ready to send:
  - `1` - "Hello" greeting
  - `2` - "Bank Info" request  
  - `3` - "Card Lost" report
  - `4` - "Balance" inquiry
  - Plus 8 more accessible via buttons

#### 3. **Live Audio Playback**
- **Automatic bot response playback** through speakers
- **Real-time audio visualization** shows levels
- **Audio format**: 16kHz PCM for optimal quality

#### 4. **Call State Monitoring**
- **Function Calls**: See every AI function call in real-time
- **Call Flow**: Monitor session state transitions
- **Events**: All WebSocket events logged
- **Transcripts**: Live conversation display

### 🎛️ TUI Layout

```
┌─────────────────────────────────────┬───────────────────┐
│ 🔗 Connection Status & Controls     │ 📋 Session Events│
├─────────────────────────────────────┤                   │
│ 🎮 Call Controls (Start/End/DTMF)   │                   │
├─────────────────────────────────────┤                   │
│ 🔊 Audio Controls & Visualization   │                   │
├─────────────────────────────────────├───────────────────┤
│ 🎵 SOUNDBOARD - Quick Phrases       │ 💬 Live Transcript│
│ [Hello] [Bank Info] [Card Lost]     │                   │
│ [Balance] [Transfer] [Loan]         │                   │
│ [Thank You] [Goodbye] [Yes] [No]    │                   │
│ [Help] [Repeat]                     │                   │
└─────────────────────────────────────┴───────────────────┘
│ ⚡ Status Bar: Connection • Audio • Latency • Stats     │
└─────────────────────────────────────────────────────────┘
```

### 🎮 Controls Reference

| Key | Action | Description |
|-----|--------|-------------|
| `c` | Connect | Connect to WebSocket endpoint |
| `s` | Start Session | Begin call session |
| `1-4` | Quick Phrases | Send common phrases instantly |
| `h` | Help | Show full help |
| `q` | Quit | Exit application |

### 🎵 Soundboard Features

#### Pre-configured Phrases:
1. **"Hello"** - Friendly greeting
2. **"Bank Info"** - Service inquiry  
3. **"Card Lost"** - Card replacement
4. **"Balance"** - Account balance check
5. **"Transfer"** - Money transfer request
6. **"Loan"** - Loan application inquiry
7. **"Thank You"** - Polite closing
8. **"Goodbye"** - Call ending
9. **"Yes/No"** - Quick responses
10. **"Help"** - Assistance request
11. **"Repeat"** - Clarification request

#### Audio File Support:
- **WAV files**: Best quality (16kHz recommended)
- **MP3/FLAC**: Supported with librosa
- **Custom phrases**: Add your own audio files to `static/` folder

### 🔧 Function Call Monitoring

The TUI shows detailed information about AI function calls:

- **Real-time display** of function calls
- **Arguments and results** clearly shown
- **Call flow visualization** 
- **Success/failure tracking**
- **Export capabilities** for analysis

### 🎧 Audio Pipeline

Your complete audio experience:

1. **Caller Audio**: Send phrases via soundboard → WebSocket → AI
2. **Bot Audio**: AI response → WebSocket → Your speakers
3. **Live Monitoring**: See audio levels, format, latency
4. **Recording**: Optional call recording for playback

### 📋 Function Call Flow Example

When you send "Bank Info" phrase:
```
🎤 Caller → "Can you tell me about your bank services?"
🔧 AI → call_intent(intent="account_inquiry") 
📋 Result → {"status": "success", "next_action": "ask_specifics"}
🤖 Bot → "I'd be happy to help! What specific information..."
🔊 Audio → Plays through your speakers
```

### 🛠️ Troubleshooting

**No audio playback?**
- Check speaker volume
- Verify audio device in system settings
- Try pressing `r` to start audio recording/playback

**Connection issues?**
- Ensure TelephonyRealtimeBridge server is running
- Check port 8000 is available
- Verify WebSocket endpoint in config

**Soundboard not working?**
- Check session is active (green status)
- Verify audio files exist in `static/` folder
- Look for errors in Events panel

### 🎯 Perfect for Your Testing Workflow

This setup gives you exactly what you need:

✅ **WebSocket connection** to your bridge
✅ **Session management** with visual feedback  
✅ **Soundboard** for rapid phrase testing
✅ **Live audio playback** of bot responses
✅ **Detailed function call monitoring**
✅ **Call state visualization**

Happy testing! 🚀

### 📞 Example Test Session

1. Launch TUI → Press `c` to connect
2. Press `s` to start session  
3. Press `1` to send "Hello" → Listen to bot greeting
4. Press `2` to ask about bank → Monitor function calls
5. Press `3` to report lost card → Watch call flow
6. Press `7` to say "Thank you" → Complete call
7. Press `e` to end session → Review logs

The TUI provides everything you need for comprehensive call flow testing! 