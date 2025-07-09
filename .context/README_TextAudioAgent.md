# TextAudioAgent

A specialized agent that connects to the real OpenAI Realtime API using **text modality only** but can trigger **local audio file playback** through function calls. This enables AI assistants to "speak" by choosing appropriate audio files rather than generating audio directly.

## 🎯 Key Features

- **Text-Only Communication**: Uses only text modality with OpenAI API for reduced latency and costs
- **Local Audio Control**: AI can trigger local audio playback through function calls  
- **Smart Audio Selection**: AI chooses appropriate audio files based on conversation context
- **Real-time Response**: Maintains conversational flow while controlling audio output
- **Flexible Audio Library**: Supports any audio files in the configured directory
- **Function Call Integration**: Uses OpenAI's function calling to control audio playback

## 🏗️ Architecture

```
User Input (Text) → OpenAI Realtime API (Text Only) → AI Response + play_audio() call
                                                           ↓
Local Audio System ← Audio File Selection ← Function Call Handler
```

The TextAudioAgent:
1. Maintains a real WebSocket connection to OpenAI's Realtime API
2. Configures the session for text-only communication  
3. Provides a `play_audio` function tool that the AI can call
4. Handles function calls to play specified audio files locally
5. Manages audio file discovery and playback

## 📋 Requirements

### Environment Variables
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### Python Dependencies
```bash
pip install sounddevice scipy librosa numpy
```

### Audio Files
Place audio files in a directory (default: `demo/audio/`):
```
demo/audio/
├── greeting.wav
├── goodbye.wav
├── thank_you.wav
├── error.wav
├── default.wav
└── ... (any other audio files)
```

## 🚀 Quick Start

### Basic Usage

```python
import asyncio
from opusagent.text_audio_agent import TextAudioAgent

async def main():
    # Initialize the agent
    agent = TextAudioAgent(
        audio_directory="demo/audio/",
        system_prompt="You are a helpful assistant that can play audio files.",
        temperature=0.7
    )
    
    # Connect to OpenAI API
    if await agent.connect():
        print("Connected!")
        
        # Send a message
        await agent.send_text_message("Hello, can you greet me?")
        
        # The AI will respond with text and may call play_audio("greeting.wav")
        await asyncio.sleep(3)  # Wait for response
        
        # Disconnect
        await agent.disconnect()

asyncio.run(main())
```

### Interactive Test Script

```bash
# Check requirements
python test_text_audio_agent.py --check

# Run interactive session
python test_text_audio_agent.py --interactive

# Run automated tests
python test_text_audio_agent.py --automated
```

## 🛠️ Configuration

### TextAudioAgent Parameters

```python
agent = TextAudioAgent(
    audio_directory="demo/audio/",     # Directory containing audio files
    system_prompt="Custom prompt...",  # AI system prompt
    temperature=0.7                    # AI response temperature (0.0-1.0)
)
```

### Session Configuration

The agent automatically configures the OpenAI session with:
- **Modalities**: `["text"]` (text only)
- **Tools**: `play_audio` function
- **Model**: `gpt-4o-realtime-preview-2025-06-03`
- **Tool Choice**: `auto` (AI decides when to use functions)

### play_audio Function

The AI has access to a `play_audio` function with this schema:

```json
{
  "name": "play_audio",
  "description": "Play a specified audio file to respond to the user",
  "parameters": {
    "type": "object",
    "properties": {
      "filename": {
        "type": "string",
        "description": "Name of the audio file to play (e.g., 'greeting.wav')"
      },
      "context": {
        "type": "string", 
        "description": "Optional context for why this file was chosen"
      }
    },
    "required": ["filename"]
  }
}
```

## 💡 Example Conversations

### Greeting Interaction
```
User: "Hello there!"
AI: *calls play_audio("greeting.wav")* 
AI: "Hello! I just played a warm greeting for you. How can I help you today?"
🔊 [greeting.wav plays locally]
```

### Gratitude Response  
```
User: "Thank you for your help!"
AI: *calls play_audio("thank_you.wav")*
AI: "You're very welcome! I played a thank you message to express my appreciation."
🔊 [thank_you.wav plays locally]
```

### Error Handling
```
User: "I'm having trouble with something complicated"
AI: *calls play_audio("error.wav")*
AI: "I understand you're facing difficulties. Let me help you work through this step by step."
🔊 [error.wav plays locally]
```

## 🎵 Audio File Management

### Supported Formats
- **WAV** (recommended for best quality)
- **MP3** (requires librosa) 
- **FLAC** (requires librosa)
- **Other formats** supported by librosa

### Audio Requirements
- **Sample Rate**: Files are automatically converted to 16kHz
- **Channels**: Converted to mono
- **Bit Depth**: Converted to 16-bit PCM

### File Discovery
The agent automatically scans the audio directory and updates the AI's system prompt with available files:

```python
agent = TextAudioAgent(audio_directory="demo/audio/")
# AI will know about all .wav, .mp3, .flac files in demo/audio/
```

## 📊 Monitoring & Debugging

### Status Information
```python
status = agent.get_status()
print(status)
# {
#     "connected": True,
#     "audio_directory": "demo/audio",
#     "available_files": ["greeting.wav", "goodbye.wav", ...],
#     "file_count": 5
# }
```

### Logging
The agent provides detailed logging:
```python
import logging
logging.basicConfig(level=logging.INFO)

# Logs include:
# - Connection status
# - Audio file discovery  
# - Function call execution
# - Audio playback status
# - Error handling
```

## 🔧 Advanced Usage

### Custom System Prompts

```python
custom_prompt = """
You are a bank customer service agent that can play audio responses.

When greeting customers, use greeting.wav
When apologizing, use apologetic.wav  
When explaining policies, use informative.wav
When ending calls, use goodbye.wav

Be professional and use audio files to enhance the customer experience.
"""

agent = TextAudioAgent(
    audio_directory="bank_audio/",
    system_prompt=custom_prompt
)
```

### Multiple Audio Directories

```python
# Business hours agent
day_agent = TextAudioAgent(audio_directory="audio/business_hours/")

# After hours agent  
night_agent = TextAudioAgent(audio_directory="audio/after_hours/")
```

### Error Handling

```python
async def robust_agent():
    agent = TextAudioAgent(audio_directory="demo/audio/")
    
    try:
        if not await agent.connect():
            print("Failed to connect to OpenAI")
            return
            
        await agent.send_text_message("Hello!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await agent.disconnect()
```

## 🧪 Testing

### Unit Tests
```bash
python -m pytest tests/test_text_audio_agent.py
```

### Integration Tests
```bash
# Test with real OpenAI API
python test_text_audio_agent.py --automated

# Interactive testing
python test_text_audio_agent.py --interactive
```

### Audio System Tests
```bash
# Check audio dependencies
python test_text_audio_agent.py --check

# Test audio playback directly
python -c "
from opusagent.text_audio_agent import func_play_audio
result = func_play_audio({'filename': 'greeting.wav'})
print(result)
"
```

## 🔍 Troubleshooting

### Common Issues

**"Audio playback not available"**
```bash
pip install sounddevice scipy librosa numpy
```

**"No audio files found"**
```bash
# Check directory exists
ls demo/audio/

# Add some audio files
cp your_audio_files/*.wav demo/audio/
```

**"OpenAI connection failed"**
```bash
# Check API key
echo $OPENAI_API_KEY

# Check internet connection
curl -I https://api.openai.com
```

**"Function calls not working"**
- Ensure `tool_choice: "auto"` is set
- Check that the AI's system prompt mentions the play_audio function
- Verify function is registered correctly

### Debug Mode
```python
import logging
logging.getLogger("text_audio_agent").setLevel(logging.DEBUG)

agent = TextAudioAgent(audio_directory="demo/audio/")
# Will show detailed debug information
```

## 🔮 Future Enhancements

### Planned Features
- [ ] **Audio Mixing**: Combine multiple audio files
- [ ] **Dynamic Audio**: Generate audio based on parameters
- [ ] **Voice Cloning**: Use different voices for different contexts
- [ ] **Audio Effects**: Add reverb, echo, speed changes
- [ ] **Playlist Support**: Play sequences of audio files
- [ ] **Volume Control**: Adjust playback volume per file
- [ ] **Audio Streaming**: Stream long audio files in chunks

### Integration Ideas
- **Telephony Integration**: Use with Twilio/AudioCodes for phone systems
- **Voice UI**: Build voice interfaces with rich audio feedback
- **Gaming**: Create audio-reactive game characters
- **Education**: Build interactive learning experiences
- **Accessibility**: Enhance applications for visually impaired users

## 📄 License

This project is part of the FastAgent framework. See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Submit a pull request

## 📞 Support

For questions and support:
- Create an issue in the repository
- Check existing documentation
- Review test examples

---

**Note**: This agent requires a valid OpenAI API key and uses the Realtime API which has usage costs. Monitor your usage to avoid unexpected charges. 