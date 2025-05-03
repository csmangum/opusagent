import os
import asyncio
import random
import queue
import threading
import numpy as np
import sounddevice as sd

from agents import Agent, function_tool
from agents.voice import AudioInput, SingleAgentVoiceWorkflow, VoicePipeline

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
    instructions="You're speaking to a human, so be polite and concise. You can provide weather information.",
    model="gpt-4o-mini",
    tools=[get_weather],
)

# Function to record audio from microphone
def record_audio(duration=5, sample_rate=24000):
    """Record audio from the microphone for a specified duration."""
    print(f"Recording audio for {duration} seconds...")
    
    # Create a queue to communicate with the audio callback
    q = queue.Queue()
    
    # This callback function will be called by sounddevice for each audio block
    def callback(indata, frames, time, status):
        if status:
            print(f"Status: {status}")
        q.put(indata.copy())
    
    # Start the recording stream
    try:
        with sd.InputStream(samplerate=sample_rate, channels=1, 
                           callback=callback, dtype=np.int16):
            # Wait for the specified duration
            sd.sleep(int(duration * 1000))
    except Exception as e:
        print(f"Error during recording: {e}")
        return None
    
    # Get all audio data from the queue
    audio_data = []
    while not q.empty():
        audio_data.append(q.get())
    
    # Concatenate all audio blocks
    if audio_data:
        return np.concatenate(audio_data)
    return None

# Run the voice pipeline with microphone input
async def run_mic_voice_pipeline():
    # Record audio from the microphone
    audio_buffer = record_audio(duration=5)
    
    if audio_buffer is None:
        print("Failed to record audio. Exiting.")
        return
    
    print(f"Recorded audio shape: {audio_buffer.shape}")
    
    # Create the voice pipeline with our agent
    pipeline = VoicePipeline(workflow=SingleAgentVoiceWorkflow(agent))
    
    # Create audio input from the recorded buffer
    audio_input = AudioInput(buffer=audio_buffer.flatten())
    
    print("Running voice pipeline with microphone input...")
    result = await pipeline.run(audio_input)
    
    # Set up an audio player for the output
    try:
        player = sd.OutputStream(samplerate=24000, channels=1, dtype=np.int16)
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
    asyncio.run(run_mic_voice_pipeline()) 