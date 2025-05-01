import os
import asyncio
import random
import json

# Import the necessary components from the agents SDK
from agents import Agent, function_tool

# Set your OpenAI API key
os.environ["OPENAI_API_KEY"] = "your-api-key-here"  # Replace with your actual key

# Define a simple weather tool
@function_tool
def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    print(f"[debug] get_weather called with city: {city}")
    choices = ["sunny", "cloudy", "rainy", "snowy"]
    return f"The weather in {city} is {random.choice(choices)}."

# Create a simple agent
agent = Agent(
    name="Assistant",
    instructions="You're a helpful assistant. You can provide weather information.",
    model="gpt-4o-mini",  # You can change this to the model you prefer
    tools=[get_weather],
)

# Test the agent
async def test_agent():
    result = await agent.run("What's the weather like in Seattle?")
    print("\nAgent response:")
    print(result.content)
    
    # Print the full result structure for reference
    print("\nFull result structure:")
    print(json.dumps(result.model_dump(), indent=2))

# Run the test
if __name__ == "__main__":
    asyncio.run(test_agent()) 