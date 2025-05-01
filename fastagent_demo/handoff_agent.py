import os
import asyncio
import random
import json

from agents import Agent, function_tool
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

# Create a Spanish-speaking agent
spanish_agent = Agent(
    name="Spanish",
    handoff_description="A Spanish-speaking agent.",
    instructions=prompt_with_handoff_instructions(
        "You're speaking to a human, so be polite and concise. Always respond in Spanish.",
    ),
    model="gpt-4o-mini",
    tools=[get_weather],  # The Spanish agent can also get weather
)

# Create the main agent with handoff capability
main_agent = Agent(
    name="Assistant",
    instructions=prompt_with_handoff_instructions(
        "You're a helpful assistant. If the user speaks in Spanish, handoff to the Spanish agent.",
    ),
    model="gpt-4o-mini",
    handoffs=[spanish_agent],  # Enable handoff to Spanish agent
    tools=[get_weather],
)

# Test the agent with different queries
async def test_agent():
    # Test with English query
    print("\n=== Testing English Query ===")
    result = await main_agent.run("What's the weather like in New York?")
    print("Agent response:")
    print(result.content)
    
    # Test with Spanish query
    print("\n=== Testing Spanish Query ===")
    result = await main_agent.run("¿Cómo está el clima en Madrid?")
    print("Agent response:")
    print(result.content)
    
    # Print the result structure for the Spanish query
    print("\nFull result structure for Spanish query:")
    print(json.dumps(result.model_dump(), indent=2))

# Run the test
if __name__ == "__main__":
    asyncio.run(test_agent()) 