import os
from dotenv import load_dotenv
import openai

# Load environment variables from .env
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment. Please set it in your .env file.")

openai.api_key = OPENAI_API_KEY

# List of phrases to synthesize
phrases = [
    "I need to replace my card.",
    "It's my gold card.",
    "Yeah, I lost it.",
    "Yes, send it to the address on file.",
    "Thanks, that's all I need.",
    "I lost my gold card and need a new one",
    "I'm not supposed to be here"
]

VOICE = "nova"
OUTPUT_DIR = "output_audio"

os.makedirs(OUTPUT_DIR, exist_ok=True)

for idx, phrase in enumerate(phrases, 1):
    print(f"Synthesizing phrase {idx}: {phrase}")
    response = openai.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=VOICE,
        input=phrase,
        instructions="You are a customer of a bank looking to get your card replaced. You are speaking to a customer service representative. Be as normal as possible.",
        response_format="wav"
    )
    out_path = os.path.join(OUTPUT_DIR, f"replacement_card_{idx}.wav")
    with open(out_path, "wb") as f:
        f.write(response.content)
    print(f"Saved: {out_path}") 