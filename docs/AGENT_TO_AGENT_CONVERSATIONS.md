# Agent-to-Agent Conversations

This document describes how to set up and use direct conversations between the caller agent and customer service agent without external telephony platforms.

## Overview

The agent-to-agent conversation feature enables:
- **Direct Communication**: Caller agent talks directly to CS agent via OpenAI Realtime API
- **Bidirectional Audio Routing**: Audio from each agent is routed to the other agent as input
- **Autonomous Conversation**: Both agents respond to each other naturally
- **Tool Function Execution**: CS agent can still execute banking functions during conversation
- **Real-time Transcription**: Full conversation transcripts are logged
- **Comprehensive Recording**: Complete audio recordings and conversation logs saved to disk

## Architecture

```
┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────┐
│   Caller Agent  │    │  Dual Agent Bridge  │    │   CS Agent      │
│   (GPT-4o)      │◄──►│                     │◄──►│   (GPT-4o)      │
│                 │    │  Audio Router       │    │                 │
│  - Caller tools│    │  - Routes audio     │    │  - CS tools     │
│  - Personality  │    │  - Manages sessions │    │  - Banking      │
└─────────────────┘    └─────────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────┐
│ OpenAI Realtime │    │   Conversation      │    │ OpenAI Realtime │
│ Session #1      │    │   Management        │    │ Session #2      │
└─────────────────┘    └─────────────────────┘    └─────────────────┘
```

## Components

### DualAgentBridge
- **Purpose**: Manages two OpenAI Realtime sessions simultaneously
- **Features**:
  - Initializes both caller and CS agent sessions
  - Routes audio bidirectionally between agents
  - Handles conversation flow and timing
  - Manages session lifecycle

### Audio Routing
- **Caller → CS**: Caller's audio output becomes CS agent's audio input
- **CS → Caller**: CS agent's audio output becomes caller's audio input
- **Buffering**: Small audio buffers prevent timing issues
- **Transcription**: Both directions are transcribed and logged

### Recording Features
All agent-to-agent conversations are automatically recorded with:
- **Separate Audio Files**: Individual audio files for caller and CS agent
- **Stereo Recording**: Combined stereo file (caller=left, CS=right)  
- **Transcripts**: Real-time transcription of both agents with timestamps
- **Function Calls**: Log of all functions called by the CS agent
- **Metadata**: Call duration, audio statistics, and conversation summary
- **Output Directory**: Recordings saved to `agent_conversations/` with timestamps

Recording files include:
```
agent_conversations/
├── {conversation_id}_{timestamp}/
│   ├── caller_audio.wav          # Caller agent audio only
│   ├── bot_audio.wav             # CS agent audio only  
│   ├── stereo_recording.wav      # Combined stereo (L=caller, R=CS)
│   ├── final_stereo_recording.wav # Final processed stereo file
│   ├── transcript.json           # Full conversation transcript
│   ├── call_metadata.json        # Statistics and metadata
│   └── session_events.json       # Detailed event log
```

## Usage

### Starting a Conversation

#### Method 1: Using the Test Script
```bash
# Start the server
python -m opusagent.main

# In another terminal, run the test
python scripts/test_agent_conversation.py
```

#### Method 2: Direct WebSocket Connection
```python
import asyncio
import websockets

async def start_conversation():
    async with websockets.connect("ws://localhost:8000/agent-conversation") as ws:
        # Connection triggers automatic conversation start
        await ws.wait_closed()

asyncio.run(start_conversation())
```

### Configuration

#### Caller Agent Configuration
Located in `opusagent/caller_agent.py`:
```python
# Personality configuration
personality = CallerPersonality(
    type=PersonalityType.NORMAL,
    traits=["cooperative", "patient", "polite"],
    communication_style="Friendly and cooperative",
    patience_level=8,
    tech_comfort=6
)

# Scenario configuration  
scenario = CallerScenario(
    scenario_type=ScenarioType.CARD_REPLACEMENT,
    goal=goal,
    context={"card_type": "gold card", "reason": "lost"}
)
```

#### CS Agent Configuration
Located in `opusagent/customer_service_agent.py`:
```python
SESSION_PROMPT = """
You are a customer service agent handling a call from a customer.
Start by greeting the customer: "Thank you for calling, how can I help you today?"
"""

# Available tools: process_replacement, get_balance, transfer_funds, human_handoff
```

## Conversation Flow

1. **Initialization**
   - DualAgentBridge creates two OpenAI Realtime connections
   - Both agent sessions are configured with their respective prompts and tools
   - Caller agent receives initial context and begins speaking

2. **Audio Routing**
   - Caller agent generates audio → routed to CS agent as input
   - CS agent processes audio and generates response → routed back to caller
   - Process continues until conversation naturally ends

3. **Function Execution**
   - CS agent can call banking functions (e.g., `process_replacement`)
   - Caller agent can call `hang_up` when satisfied
   - Function results influence conversation flow

4. **Conversation End**
   - Automatic timeout (5 minutes max)
   - Caller agent calls `hang_up` function
   - Manual termination via connection close

## Monitoring and Debugging

### Logs
- **Bridge Logs**: `DualAgentBridge` logs conversation flow
- **Agent Logs**: Individual agent activities and responses
- **Audio Routing**: Audio transfer and buffering events
- **Transcripts**: Real-time conversation transcription

### Key Log Messages
```
DualAgentBridge created for conversation: abc123
Caller session initialized
CS session initialized  
Both agents ready, conversation can begin
Caller transcript: I need to replace my lost card
CS transcript: I can help you with that card replacement
```

### Debugging Tips
1. **Check Connection Status**: Ensure OpenAI API key is valid
2. **Monitor Audio Flow**: Look for "audio delta" and "commit" messages
3. **Function Calls**: Watch for tool execution in CS agent
4. **Session Timeouts**: Default 5-minute maximum duration

## Limitations

### Current Limitations
- **No External Audio**: Conversations are purely agent-to-agent
- **Fixed Conversation Length**: 5-minute maximum duration
- **No Mid-Conversation Configuration**: Settings cannot be changed during conversation
- **Single Conversation**: One conversation per connection

### Future Enhancements
- **Multiple Concurrent Conversations**: Support several agent pairs
- **Real-time Audio Export**: Save conversation audio files
- **Dynamic Configuration**: Change agent behavior during conversation
- **External Integration**: Connect to real telephony systems

## Troubleshooting

### Common Issues

#### Connection Refused
```
Error: Could not connect to ws://localhost:8000/agent-conversation
```
**Solution**: Ensure the main server is running with `python -m opusagent.main`

#### OpenAI API Errors
```
Error: WebSocket connection failed to wss://api.openai.com
```
**Solution**: Check `OPENAI_API_KEY` environment variable

#### Conversation Doesn't Start
```
Caller session initialized
CS session initialized
(No further activity)
```
**Solution**: Check OpenAI API quota and rate limits

#### Audio Routing Issues
```
Warning: No audio delta received from caller
```
**Solution**: Verify both agents are configured for audio output

### Environment Variables
```bash
# Required
export OPENAI_API_KEY="your-api-key"

# Optional  
export LOG_LEVEL="DEBUG"  # For detailed logging
export OPUSAGENT_USE_MOCK="true"  # Use mock OpenAI for testing
```

## Example Conversation

### Typical Flow
```
[DualAgentBridge] Both agents ready, conversation can begin

[Caller] Hi, I need to replace my lost gold card.

[CS Agent] Thank you for calling, how can I help you today? I understand you need to replace your lost gold card. I can definitely help you with that.

[Caller] Yes, that's right. How long will it take to get a new one?

[CS Agent] I'll process that replacement for you right away. Your new gold card will be delivered to your address on file within 5-7 business days.

[Caller] Perfect, thank you for your help!

[CS Agent] You're welcome! Is there anything else I can help you with today?

[Caller] No, that's everything. Thank you!

[DualAgentBridge] Conversation completed - connection closed
```

This demonstrates the natural flow between a customer caller agent and the customer service agent, with the CS agent successfully handling the card replacement request. 