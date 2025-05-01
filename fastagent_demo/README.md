# OpenAI Agents SDK Demo

A simple demonstration of the OpenAI Agents SDK capabilities, including basic agents, agent handoffs, voice capabilities, and custom tools.

## Setup

1. Create a virtual environment and install dependencies:
   ```powershell
   py -m venv venv
   .\venv\Scripts\activate
   pip install "openai-agents[voice]" numpy sounddevice
   ```

2. Set your OpenAI API key in each script:
   Edit the line `os.environ["OPENAI_API_KEY"] = "your-api-key-here"` in each script to include your actual OpenAI API key.

## Scripts

### 1. Simple Agent (`simple_agent.py`)
A basic demonstration of an agent with a weather tool.

Run:
```powershell
python simple_agent.py
```

### 2. Handoff Agent (`handoff_agent.py`)
Demonstrates agent handoffs between a main agent and a Spanish-speaking agent.

Run:
```powershell
python handoff_agent.py
```

### 3. Voice Agent (`voice_agent.py`)
Demonstrates the voice pipeline capabilities for handling audio input and output with simulated audio.

Run:
```powershell
python voice_agent.py
```

### 4. Microphone Voice Agent (`mic_voice_agent.py`)
Demonstrates capturing audio from your microphone, processing it with the agent, and playing back the response.

Run:
```powershell
python mic_voice_agent.py
```
This script will:
- Record audio from your microphone for 5 seconds
- Process the audio through the voice pipeline
- Play back the agent's response

### 5. Custom Tools Agent (`custom_tools_agent.py`)
Demonstrates how to create and use custom tools with an agent, including weather, time, calculations, and note-taking tools.

Run:
```powershell
python custom_tools_agent.py
```

## Features Demonstrated

- Basic agent setup
- Function tools and custom tools
- Agent handoffs
- Voice pipelines
- Audio input/output handling
- Microphone recording
- Stateful tools (note-taking)
- Multi-tool usage in a single query

## Requirements

- Python 3.8+
- OpenAI API key
- Numpy
- Sounddevice (for audio recording and playback)

## Troubleshooting

If you encounter audio device issues:
- Check your microphone and speaker settings
- Make sure you have appropriate permissions for audio devices
- If you get an "Input overflow" warning, try reducing the recording duration 