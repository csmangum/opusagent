# Quick Start: Agent-to-Agent Conversations

Get your caller agent talking to your customer service agent in under 5 minutes!

## Prerequisites

1. **OpenAI API Key**: Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

2. **Install Dependencies**: Make sure you have the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Step 1: Start the Server

```bash
# From the project root directory
python -m opusagent.main
```

You should see:
```
INFO - Starting server on http://0.0.0.0:8000
INFO - Logging configured
```

## 🗣️ Step 2: Start Agent Conversation

Open a new terminal and run:

```bash
python scripts/test_agent_conversation.py
```

You should see:
```
============================================================
AGENT-TO-AGENT CONVERSATION TEST
============================================================
INFO - Starting agent conversation test...
INFO - Connecting to: ws://localhost:8000/agent-conversation
INFO - Connected to agent conversation endpoint
INFO - Conversation started - monitoring for completion...
```

## 📋 What Happens Next

1. **Dual Agent Bridge Creates**: Two OpenAI Realtime sessions
2. **Caller Agent Initializes**: Gets caller personality and scenario
3. **CS Agent Initializes**: Gets customer service tools and prompts
4. **Recording Starts**: Audio and transcripts automatically recorded
5. **Conversation Begins**: Caller starts with their request
6. **Audio Routes**: Each agent's speech becomes the other's input
7. **Natural Flow**: Agents respond to each other autonomously

## 📹 Automatic Recording

Every conversation is automatically recorded with:
- **Audio Files**: Separate files for each agent + combined stereo
- **Transcripts**: Real-time transcription with timestamps  
- **Function Calls**: Log of any banking functions used
- **Metadata**: Call statistics and conversation summary

Files are saved to: `agent_conversations/{conversation_id}_{timestamp}/`

## 🔍 Monitoring the Conversation

In the server terminal, you'll see logs like:
```
INFO - DualAgentBridge created for conversation: abc123
INFO - Caller session initialized  
INFO - CS session initialized
INFO - Both agents ready, conversation can begin
INFO - Caller transcript: I need to replace my lost card
INFO - CS transcript: I can help you with that card replacement
```

## ⏹️ Conversation End

The conversation will end when:
- Caller agent calls the `hang_up()` function (when satisfied)
- 5-minute timeout is reached
- Connection is manually closed

## 🎛️ Customization

### Change Caller Scenario
Edit `opusagent/caller_agent.py`:
```python
scenario = CallerScenario(
    scenario_type=ScenarioType.LOAN_APPLICATION,  # Changed from CARD_REPLACEMENT
    goal=goal,
    context={"loan_amount": "$50000", "purpose": "home improvement"}
)
```

### Change CS Agent Behavior  
Edit `opusagent/customer_service_agent.py`:
```python
SESSION_PROMPT = """
You are a loan specialist at the bank. 
Greet customers warmly and help them with loan applications.
"""
```

## 🐛 Troubleshooting

### "Connection Refused"
- Make sure the server is running: `python -m opusagent.main`
- Check the server is on port 8000

### "OpenAI API Error"
- Verify your API key: `echo $OPENAI_API_KEY`
- Check your OpenAI account has sufficient credits

### "No Audio Activity"
- Check OpenAI API rate limits
- Ensure both agents are configured for audio output
- Try setting `LOG_LEVEL=DEBUG` for more details

## 🎯 Expected Results

A successful conversation looks like:
```
[Caller - "alloy" voice] Hi, I need help with my account
[CS Agent - "verse" voice] Thank you for calling! How can I help you today?
[Caller - "alloy" voice] I lost my debit card and need a replacement
[CS Agent - "verse" voice] I can definitely help you with that card replacement...
```

**Voice Distinction**: The caller uses the "alloy" voice while the CS agent uses the "verse" voice, making it easy to distinguish between the two agents in the audio recordings.

## 📚 Next Steps

- Read the full documentation: `docs/AGENT_TO_AGENT_CONVERSATIONS.md`
- Experiment with different caller personalities
- Try different banking scenarios
- Monitor function calls and tool usage

## 💡 Tips

- Use `Ctrl+C` to stop the server
- Each test creates a new conversation ID
- Conversations are automatically logged
- Both agents use GPT-4o Realtime API for natural speech

Happy agent conversing! 🤖💬🤖 