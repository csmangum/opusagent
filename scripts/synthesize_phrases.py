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
    "Hi, I need to replace my card. ",
    "I lost it.",
    "Its my Gold card.",
    "Yes send it to that address.",
    "Thanks, thats all.",
    "What is my balance?",
    "Transfer funds 100 to 1234567890"
]

VOICE = "nova"
OUTPUT_DIR = "output_audio"

os.makedirs(OUTPUT_DIR, exist_ok=True)

for idx, phrase in enumerate(phrases, 1):
    print(f"Synthesizing phrase {idx}: {phrase}")
    response = openai.audio.speech.create(
        model="tts-1",
        voice=VOICE,
        input=phrase,
        response_format="wav"
    )
    out_path = os.path.join(OUTPUT_DIR, f"replacement_card_{idx}.wav")
    with open(out_path, "wb") as f:
        f.write(response.content)
    print(f"Saved: {out_path}") 