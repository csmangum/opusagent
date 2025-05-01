import os
import asyncio
import random
import numpy as np
import sounddevice as sd

from agents import Agent, function_tool
from agents.voice import AudioInput, SingleAgentVoiceWorkflow, VoicePipeline
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions

# Set your OpenAI API key
os.environ["OPENAI_API_KEY"] = "your-api-key-here"  # Replace with your actual key

# Define our weather tool
@function_tool
def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    print(f"[debug] get_weather called with city: {city}")
    choices = ["sunny", "cloudy", "rainy", "snowy"]
    return f"The weather in {city} is {random.choice(choices)}."

# Create a simple assistant agent
agent = Agent(
    name="Assistant",
    instructions=prompt_with_handoff_instructions(
        "You're speaking to a human, so be polite and concise. You can provide weather information.",
    ),
    model="gpt-4o-mini",
    tools=[get_weather],
)

# Set up the voice pipeline
async def run_voice_pipeline():
    # Create the voice pipeline with our agent
    pipeline = VoicePipeline(workflow=SingleAgentVoiceWorkflow(agent))
    
    # For demo purposes, we'll create a simple audio input
    # In a real application, you would get this from a microphone
    sample_rate = 24000
    duration = 3  # seconds
    buffer = np.zeros(sample_rate * duration, dtype=np.int16)
    audio_input = AudioInput(buffer=buffer)
    
    print("Running voice pipeline with simulated audio input...")
    result = await pipeline.run(audio_input)
    
    # Set up an audio player for the output
    try:
        player = sd.OutputStream(samplerate=sample_rate, channels=1, dtype=np.int16)
        player.start()
        
        print("Streaming audio output...")
        async for event in result.stream():
            if event.type == "voice_stream_event_audio":
                print("Received audio data, playing...")
                player.write(event.data)
            elif event.type == "voice_stream_event_transcript":
                print(f"Transcript: {event.data}")
            elif event.type == "voice_stream_event_result":
                print(f"Result: {event.data}")
            
        player.stop()
        print("Voice pipeline completed")
        
    except Exception as e:
        print(f"Error during audio playback: {e}")

# Run the voice pipeline
if __name__ == "__main__":
    asyncio.run(run_voice_pipeline()) 