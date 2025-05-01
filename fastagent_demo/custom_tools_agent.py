import os
import asyncio
import random
import json
import datetime

from agents import Agent, function_tool

# Set your OpenAI API key
os.environ["OPENAI_API_KEY"] = "your-api-key-here"  # Replace with your actual key

# Basic weather tool
@function_tool
def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    print(f"[debug] get_weather called with city: {city}")
    choices = ["sunny", "cloudy", "rainy", "snowy"]
    return f"The weather in {city} is {random.choice(choices)}."

# Custom tool to get the current time
@function_tool
def get_current_time(timezone: str = "local") -> str:
    """
    Get the current time in the specified timezone.
    If timezone is "local", returns the local time.
    """
    print(f"[debug] get_current_time called with timezone: {timezone}")
    if timezone.lower() == "local":
        current_time = datetime.datetime.now()
    else:
        # This is a simplified example - in a real app, you'd use pytz
        # to handle different timezones properly
        current_time = datetime.datetime.now()
        return f"Current time in {timezone} is {current_time.strftime('%H:%M:%S')} (note: this is actually local time, timezone support is simulated)"
    
    return f"Current local time is {current_time.strftime('%H:%M:%S')}"

# Custom tool to perform simple calculations
@function_tool
def calculate(expression: str) -> str:
    """
    Perform a simple calculation.
    Examples: "2+2", "5*10", "20/4"
    """
    print(f"[debug] calculate called with expression: {expression}")
    try:
        # WARNING: In production code, never use eval() with unsanitized input
        # This is just for demonstration purposes
        result = eval(expression)
        return f"The result of {expression} is {result}"
    except Exception as e:
        return f"Error calculating {expression}: {str(e)}"

# Custom tool to store and retrieve notes
notes_db = {}

@function_tool
def save_note(title: str, content: str) -> str:
    """Save a note with the given title and content."""
    print(f"[debug] save_note called with title: {title}")
    notes_db[title] = content
    return f"Note '{title}' saved successfully"

@function_tool
def get_note(title: str) -> str:
    """Retrieve a note by its title."""
    print(f"[debug] get_note called with title: {title}")
    if title in notes_db:
        return f"Note '{title}': {notes_db[title]}"
    else:
        return f"Note '{title}' not found"

@function_tool
def list_notes() -> str:
    """List all saved notes."""
    print(f"[debug] list_notes called")
    if not notes_db:
        return "No notes saved yet"
    note_list = "\n".join([f"- {title}" for title in notes_db.keys()])
    return f"Saved notes:\n{note_list}"

# Create an agent with all our custom tools
agent = Agent(
    name="Assistant",
    instructions="You're a helpful assistant with various capabilities including weather, time, calculations, and note-taking.",
    model="gpt-4o-mini",
    tools=[
        get_weather,
        get_current_time,
        calculate,
        save_note,
        get_note,
        list_notes
    ],
)

# Test the agent with different queries
async def test_agent():
    queries = [
        "What's the weather like in Tokyo?",
        "What time is it now?",
        "Calculate 15 * 7",
        "Save a note titled 'Meeting' with content 'Team meeting at 3pm tomorrow'",
        "What notes do I have?",
        "Show me the Meeting note",
        "What's the weather in Paris and what's 25 + 17?"
    ]
    
    for i, query in enumerate(queries):
        print(f"\n=== Query {i+1}: {query} ===")
        result = await agent.run(query)
        print("Agent response:")
        print(result.content)
        
        # For certain queries, print the full result to see the tool calls
        if i == 6:  # The last query that uses multiple tools
            print("\nFull result structure for multi-tool query:")
            print(json.dumps(result.model_dump(), indent=2))

# Run the test
if __name__ == "__main__":
    asyncio.run(test_agent()) 