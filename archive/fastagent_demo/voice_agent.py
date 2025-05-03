import os
import asyncio
import random
import numpy as np
import sounddevice as sd
import time

from agents import Agent, function_tool
from agents.voice import AudioInput, SingleAgentVoiceWorkflow, VoicePipeline
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
from dotenv import load_dotenv

print("Starting voice agent script...")
load_dotenv()
print("Environment variables loaded")

# Define our weather tool
@function_tool
def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    print(f"[debug] get_weather called with city: {city}")
    choices = ["sunny", "cloudy", "rainy", "snowy"]
    return f"The weather in {city} is {random.choice(choices)}."

# Add a debug function to print the full response
def print_response_details(response_text):
    """Print detailed information about the response."""
    print(f"[DEBUG] Response text: {response_text}")
    print(f"[DEBUG] Response length: {len(response_text)}")
    print(f"[DEBUG] Response language characters check: {[ord(c) for c in response_text[:20] if ord(c) > 127]}")

print("Creating agent...")
# Create a simple assistant agent
agent = Agent(
    name="Assistant",
    instructions=prompt_with_handoff_instructions(
        "You're speaking to a human, so be polite and concise. You can provide weather information.",
    ),
    model="gpt-4o-mini",
    tools=[get_weather],
)
print("Agent created")

# Set up the voice pipeline
async def run_voice_pipeline():
    print("Setting up voice pipeline...")
    # Create the voice pipeline with our agent
    pipeline = VoicePipeline(workflow=SingleAgentVoiceWorkflow(agent))
    print("Voice pipeline created")
    
    # For demo purposes, we'll create a simple audio input
    # In a real application, you would get this from a microphone
    sample_rate = 24000
    duration = 3  # seconds
    print(f"Creating audio buffer with {sample_rate} sample rate and {duration} seconds duration")
    buffer = np.zeros(sample_rate * duration, dtype=np.int16)
    print(f"Buffer created with shape {buffer.shape}")
    audio_input = AudioInput(buffer=buffer)
    print("Audio input created")
    
    print("Running voice pipeline with simulated audio input...")
    start_time = time.time()
    result = await pipeline.run(audio_input)
    print(f"Pipeline run completed in {time.time() - start_time:.2f} seconds")
    
    # Set up an audio player for the output
    try:
        print("Setting up audio player...")
        player = sd.OutputStream(samplerate=sample_rate, channels=1, dtype=np.int16)
        player.start()
        
        print("Starting to stream audio output...")
        count = 0
        async for event in result.stream():
            count += 1
            print(f"Received event {count} of type: {event.type}")
            if event.type == "voice_stream_event_audio":
                print(f"Received audio data of size {len(event.data)}, playing...")
                player.write(event.data)
            elif event.type == "voice_stream_event_transcript":
                print(f"Transcript: {event.data}")
                print_response_details(event.data)
            elif event.type == "voice_stream_event_result":
                print(f"Result: {event.data}")
                if isinstance(event.data, str):
                    print_response_details(event.data)
            
        player.stop()
        print("Voice pipeline completed")
        
    except Exception as e:
        print(f"Error during audio playback: {e}")

# Run the voice pipeline
if __name__ == "__main__":
    print("Starting main function...")
    try:
        asyncio.run(run_voice_pipeline())
    except Exception as e:
        print(f"Error in main function: {e}")
    print("Script completed") 