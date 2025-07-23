# TextAudioAgent

A specialized agent that connects to the real OpenAI Realtime API using **text modality only** but can trigger **local audio file playback** through function calls. This enables AI assistants to "speak" by choosing appropriate audio files rather than generating audio directly.

## 🎯 Key Features

- **Text-Only Communication**: Uses only text modality with OpenAI API for reduced latency and costs
- **Local Audio Control**: AI can trigger local audio playback through function calls  
- **Smart Audio Selection**: AI chooses appropriate audio files based on conversation context
- **Real-time Response**: Maintains conversational flow while controlling audio output
- **Flexible Audio Library**: Supports any audio files in the configured directory
- **Function Call Integration**: Uses OpenAI's function calling to control audio playback
- **Audio Streaming**: Implements chunked audio streaming for smooth playback
- **Categorized Audio Files**: Organized audio files by category with numbered variants

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
5. Manages audio file discovery and playback with streaming support
6. Uses categorized audio files with numbered variants for better organization

## 📋 Requirements

### Environment Variables
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### Python Dependencies
```bash
pip install sounddevice scipy librosa numpy
```

The implementation also requires the TUI audio utilities:
- `tui.utils.audio_utils.AudioUtils`
- `tui.models.audio_manager.AudioManager`

### Audio Files
Place audio files in organized categories (default: `opusagent/local/audio/`):
```
opusagent/local/audio/
├── greetings/
│   ├── greetings_01.wav
│   ├── greetings_02.wav
│   └── ... (up to greetings_10.wav)
├── farewells/
│   ├── farewells_01.wav
│   ├── farewells_02.wav
│   └── ... (up to farewells_10.wav)
├── thank_you/
│   ├── thank_you_01.wav
│   └── ... (up to thank_you_10.wav)
├── errors/
│   ├── errors_01.wav
│   └── ... (up to errors_10.wav)
├── default/
│   ├── default_01.wav
│   └── ... (up to default_10.wav)
├── confirmations/
│   ├── confirmations_01.wav
│   └── ... (up to confirmations_10.wav)
├── sales/
│   ├── sales_01.wav
│   └── ... (up to sales_10.wav)
├── customer_service/
│   ├── customer_service_01.wav
│   └── ... (up to customer_service_10.wav)
├── technical_support/
│   ├── technical_support_01.wav
│   └── ... (up to technical_support_10.wav)
└── card_replacement/
    ├── card_replacement_01.wav
    └── ... (up to card_replacement_10.wav)
```

## 🚀 Quick Start

### Basic Usage

```python
import asyncio
from opusagent.text_audio_agent import TextAudioAgent

async def main():
    # Initialize the agent
    agent = TextAudioAgent(
        audio_directory="opusagent/local/audio/",
        system_prompt="You are a helpful assistant that can play audio files.",
        temperature=0.7
    )
    
    # Connect to OpenAI API
    if await agent.connect():
        print("Connected!")
        
        # Send a message
        await agent.send_text_message("Hello, can you greet me?")
        
        # The AI will respond with text and may call play_audio("greetings/greetings_01.wav")
        await asyncio.sleep(3)  # Wait for response
        
        # Disconnect
        await agent.disconnect()

asyncio.run(main())
```

### Interactive Example

```python
# Run the built-in example
python opusagent/text_audio_agent.py
```

## 🛠️ Configuration

### TextAudioAgent Parameters

```python
agent = TextAudioAgent(
    audio_directory="opusagent/local/audio/",  # Directory containing audio files
    system_prompt="Custom prompt...",          # AI system prompt
    temperature=0.7                            # AI response temperature (0.0-1.0)
)
```

### Session Configuration

The agent automatically configures the OpenAI session with:
- **Modalities**: `["text"]` (text only)
- **Tools**: `play_audio` function
- **Model**: `gpt-4o-realtime-preview-2025-06-03`
- **Tool Choice**: `auto` (AI decides when to use functions)

### Default System Prompt

The agent uses a comprehensive system prompt that includes:

```
You are a helpful voice assistant that communicates through text but can play audio files for responses.

You have access to a play_audio function that allows you to play audio files to respond to the user.
When you want to "speak" to the user, call the play_audio function with an appropriate filename.

Available audio files are organized in categories with numbered files:
- greetings/greetings_01.wav through greetings_10.wav - for welcoming users
- farewells/farewells_01.wav through farewells_10.wav - for farewells  
- thank_you/thank_you_01.wav through thank_you_10.wav - for expressing gratitude
- errors/errors_01.wav through errors_10.wav - for error situations
- default/default_01.wav through default_10.wav - for general responses
- confirmations/confirmations_01.wav through confirmations_10.wav - for confirmations
- sales/sales_01.wav through sales_10.wav - for sales interactions
- customer_service/customer_service_01.wav through customer_service_10.wav - for customer service
- technical_support/technical_support_01.wav through technical_support_10.wav - for technical support
- card_replacement/card_replacement_01.wav through card_replacement_10.wav - for card replacement

IMPORTANT: Use the exact filename including the category folder and number, for example:
- play_audio("greetings/greetings_01.wav") for a greeting
- play_audio("farewells/farewells_03.wav") for a farewell
- play_audio("default/default_05.wav") for a general response

Choose the most appropriate audio file based on the context of the conversation.
You should use text responses to provide detailed information and audio files to add personality and engagement.

Always be helpful, friendly, and engaging in your responses.
```

### play_audio Function

The AI has access to a `play_audio` function with this schema:

```json
{
  "name": "play_audio",
  "description": "Play a specified audio file to respond to the user. Use this to 'speak' by selecting appropriate audio files.",
  "parameters": {
    "type": "object",
    "properties": {
      "filename": {
        "type": "string",
        "description": "Name of the audio file to play (e.g., 'greetings/greetings_01.wav'). Should include the file extension."
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
AI: *calls play_audio("greetings/greetings_01.wav")* 
AI: "Hello! I just played a warm greeting for you. How can I help you today?"
🔊 [greetings_01.wav plays locally]
```

### Gratitude Response  
```
User: "Thank you for your help!"
AI: *calls play_audio("thank_you/thank_you_03.wav")*
AI: "You're very welcome! I played a thank you message to express my appreciation."
🔊 [thank_you_03.wav plays locally]
```

### Error Handling
```
User: "I'm having trouble with something complicated"
AI: *calls play_audio("errors/errors_02.wav")*
AI: "I understand you're facing difficulties. Let me help you work through this step by step."
🔊 [errors_02.wav plays locally]
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
- **Streaming**: Audio is chunked into 200ms segments for smooth playback

### File Discovery
The agent automatically scans the audio directory and updates the AI's system prompt with available files:

```python
agent = TextAudioAgent(audio_directory="opusagent/local/audio/")
# AI will know about all categorized audio files in the directory
```

### Audio Streaming Implementation

The implementation includes sophisticated audio handling:
- **Chunked Playback**: Audio files are split into 200ms chunks
- **Streaming Queue**: Chunks are queued for smooth playback
- **Error Recovery**: Automatic retry and restart mechanisms
- **Format Conversion**: Automatic sample rate and channel conversion
- **Statistics Monitoring**: Real-time playback statistics

## 📊 Monitoring & Debugging

### Status Information
```python
status = agent.get_status()
print(status)
# {
#     "connected": True,
#     "audio_directory": "opusagent/local/audio",
#     "available_files": ["greetings/greetings_01.wav", "farewells/farewells_01.wav", ...],
#     "file_count": 50
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
# - Audio playback status with chunk information
# - Error handling and recovery
# - Audio manager statistics
```

## 🔧 Advanced Usage

### Custom System Prompts

```python
custom_prompt = """
You are a bank customer service agent that can play audio responses.

When greeting customers, use greetings/greetings_01.wav through greetings_10.wav
When apologizing, use errors/errors_01.wav through errors_10.wav  
When explaining policies, use confirmations/confirmations_01.wav through confirmations_10.wav
When ending calls, use farewells/farewells_01.wav through farewells_10.wav

Be professional and use audio files to enhance the customer experience.
"""

agent = TextAudioAgent(
    audio_directory="opusagent/local/audio/",
    system_prompt=custom_prompt
)
```

### Multiple Audio Directories

```python
# Business hours agent
day_agent = TextAudioAgent(audio_directory="opusagent/local/audio/")

# After hours agent  
night_agent = TextAudioAgent(audio_directory="opusagent/local/audio/")
```

### Error Handling

```python
async def robust_agent():
    agent = TextAudioAgent(audio_directory="opusagent/local/audio/")
    
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
python opusagent/text_audio_agent.py
```

### Audio System Tests
```bash
# Check audio dependencies
python -c "
from opusagent.text_audio_agent import func_play_audio
result = func_play_audio({'filename': 'greetings/greetings_01.wav'})
print(result)
"
```

## 🔍 Troubleshooting

### Common Issues

**"Audio playback not available"**
```bash
pip install sounddevice scipy librosa numpy
# Also ensure TUI audio utilities are available
```

**"No audio files found"**
```bash
# Check directory exists
ls opusagent/local/audio/

# Add some audio files in the correct structure
mkdir -p opusagent/local/audio/greetings
cp your_audio_files/*.wav opusagent/local/audio/greetings/
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
- Ensure audio files exist in the expected directory structure

### Debug Mode
```python
import logging
logging.getLogger("text_audio_agent").setLevel(logging.DEBUG)

agent = TextAudioAgent(audio_directory="opusagent/local/audio/")
# Will show detailed debug information including audio chunking
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

This project is part of the OpusAgent framework. See LICENSE file for details.

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