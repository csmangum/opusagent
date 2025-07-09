#!/usr/bin/env python3
"""
Generate Mock Audio Files for Testing

This script generates audio files for use with the MockRealtimeClient.
It creates various scenarios including customer service, sales, technical support,
and general conversation audio files.

Usage:
    python scripts/generate_mock_audio.py [--scenario SCENARIO] [--voice VOICE] [--output-dir DIR]

Examples:
    # Generate all scenarios
    python scripts/generate_mock_audio.py
    
    # Generate only customer service audio
    python scripts/generate_mock_audio.py --scenario customer_service
    
    # Generate with specific voice
    python scripts/generate_mock_audio.py --voice alloy
    
    # Generate to custom directory
    python scripts/generate_mock_audio.py --output-dir demo/audio/mock
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment. Please set it in your .env file.")

openai.api_key = OPENAI_API_KEY

# Available voices
AVAILABLE_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

# Audio scenarios with phrases and context
AUDIO_SCENARIOS = {
    "customer_service": {
        "description": "Customer service representative responses",
        "voice_instructions": "You are a helpful customer service representative. Be professional, friendly, and patient.",
        "phrases": [
            "Hello, welcome to our customer service. How can I help you today?",
            "I understand you're having an issue. Let me help you with that.",
            "I can definitely help you with your card replacement.",
            "Let me verify your information to ensure we get this right.",
            "I'll process your request right away. Is there anything else you need?",
            "Thank you for calling us today. Have a great day!",
            "I apologize for the inconvenience. Let me fix that for you.",
            "Your request has been submitted successfully.",
            "Is there anything else I can assist you with today?",
            "I'm here to help you resolve this issue.",
        ]
    },
    "card_replacement": {
        "description": "Card replacement specific responses",
        "voice_instructions": "You are a bank representative helping with card replacement. Be professional and reassuring.",
        "phrases": [
            "I can help you replace your lost card right away.",
            "Let me verify your identity before processing the replacement.",
            "Your new card will be mailed to your address on file.",
            "The replacement card will arrive in 5-7 business days.",
            "There's a $10 replacement fee for lost cards.",
            "Your old card has been deactivated for security.",
            "You can track your new card delivery online.",
            "Is the address on file still current?",
            "Your replacement card will have the same benefits.",
            "I've processed your card replacement request.",
        ]
    },
    "technical_support": {
        "description": "Technical support responses",
        "voice_instructions": "You are a technical support specialist. Be knowledgeable, patient, and clear in your explanations.",
        "phrases": [
            "I can help you troubleshoot this technical issue.",
            "Let me walk you through the solution step by step.",
            "This is a common issue that we can resolve quickly.",
            "Have you tried restarting your device?",
            "Let me check your account settings for you.",
            "I'll escalate this to our technical team if needed.",
            "The issue should be resolved now. Can you test it?",
            "I'm transferring you to our specialized technical team.",
            "This might take a few minutes to process.",
            "Your account has been updated with the fix.",
        ]
    },
    "sales": {
        "description": "Sales representative responses",
        "voice_instructions": "You are a sales representative. Be enthusiastic, helpful, and focused on customer needs.",
        "phrases": [
            "I'd love to tell you about our special offers today.",
            "This product would be perfect for your needs.",
            "Let me show you the benefits of upgrading.",
            "We have a limited-time promotion available.",
            "This solution will save you time and money.",
            "Would you like to hear about our premium features?",
            "I can offer you a special discount today.",
            "This upgrade includes additional security features.",
            "Let me explain the value proposition.",
            "I'm confident this will meet your requirements.",
        ]
    },
    "greetings": {
        "description": "General greeting and introduction responses",
        "voice_instructions": "You are a friendly AI assistant. Be warm, welcoming, and helpful.",
        "phrases": [
            "Hello! How can I assist you today?",
            "Welcome! I'm here to help you.",
            "Good day! What can I do for you?",
            "Hi there! How may I be of service?",
            "Greetings! I'm ready to help you.",
            "Hello and welcome! What brings you here today?",
            "Good morning! How can I make your day better?",
            "Hi! I'm here to answer your questions.",
            "Welcome! Let me know how I can help.",
            "Hello! I'm your AI assistant, ready to assist.",
        ]
    },
    "farewells": {
        "description": "Farewell and closing responses",
        "voice_instructions": "You are a polite AI assistant ending conversations. Be courteous and professional.",
        "phrases": [
            "Thank you for your time. Have a great day!",
            "Is there anything else I can help you with?",
            "Thank you for choosing our service.",
            "Have a wonderful day ahead!",
            "Thank you for the conversation. Take care!",
            "I'm glad I could help. Goodbye!",
            "Thank you for your patience. Have a good day!",
            "Is there anything else you need assistance with?",
            "Thank you for reaching out. Stay well!",
            "I appreciate your time. Have a great day!",
        ]
    },
    "confirmations": {
        "description": "Confirmation and verification responses",
        "voice_instructions": "You are confirming information. Be clear, precise, and reassuring.",
        "phrases": [
            "I've confirmed your information is correct.",
            "Your request has been processed successfully.",
            "I can confirm that your account has been updated.",
            "Yes, that's correct. Your changes have been saved.",
            "I've verified your identity. You're all set.",
            "Confirmed. Your order has been placed.",
            "I can confirm the transaction was successful.",
            "Your information has been verified and updated.",
            "Yes, I've processed your request as requested.",
            "Confirmed. Everything is in order.",
        ]
    },
    "errors": {
        "description": "Error and problem resolution responses",
        "voice_instructions": "You are handling errors professionally. Be apologetic, helpful, and solution-oriented.",
        "phrases": [
            "I apologize for the inconvenience. Let me fix that.",
            "I understand your frustration. Let me help resolve this.",
            "I'm sorry for the error. Let me correct it right away.",
            "I apologize for the confusion. Let me clarify.",
            "I'm sorry this happened. Let me make it right.",
            "I understand this is frustrating. Let me help.",
            "I apologize for the delay. Let me expedite this.",
            "I'm sorry for the inconvenience. Let me assist you.",
            "I understand your concern. Let me address it.",
            "I apologize for the error. Let me resolve it quickly.",
        ]
    },
    "default": {
        "description": "Default and placeholder responses for unsupported requests",
        "voice_instructions": "You are a helpful AI assistant. Be apologetic but professional when you cannot help with a request.",
        "phrases": [
            "I'm sorry, I don't have the capability to help you with that yet.",
            "I apologize, but I'm not able to assist with that request at the moment.",
            "I'm sorry, that's not something I can help you with right now.",
            "I apologize, but I don't have the functionality to handle that request.",
            "I'm sorry, I'm not equipped to help you with that particular issue.",
            "I apologize, but that's outside of my current capabilities.",
            "I'm sorry, I don't have access to that information or functionality.",
            "I apologize, but I'm not able to process that type of request.",
            "I'm sorry, that's not within my scope of assistance at this time.",
            "I apologize, but I don't have the tools needed to help with that.",
        ]
    }
}


def create_directory_structure(output_dir: str) -> None:
    """Create the directory structure for audio files."""
    base_dir = Path(output_dir)
    
    # Create main directory
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories for each scenario
    for scenario in AUDIO_SCENARIOS.keys():
        scenario_dir = base_dir / scenario
        scenario_dir.mkdir(exist_ok=True)
    
    print(f"Created directory structure in: {base_dir}")


def generate_audio_file(
    text: str,
    output_path: str,
    voice: str,
    instructions: str,
    model: str = "gpt-4o-mini-tts"
) -> bool:
    """
    Generate a single audio file using OpenAI's TTS API.
    
    Args:
        text: The text to synthesize
        output_path: Where to save the audio file
        voice: The voice to use
        instructions: Voice instructions for the TTS model
        model: The TTS model to use
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"  Generating: {text[:50]}...")
        
        response = openai.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            instructions=instructions,
            response_format="wav"
        )
        
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        file_size = len(response.content)
        print(f"  ✓ Saved: {output_path} ({file_size} bytes)")
        return True
        
    except Exception as e:
        print(f"  ✗ Error generating {output_path}: {e}")
        return False


def generate_scenario_audio(
    scenario: str,
    output_dir: str,
    voice: str,
    model: str = "gpt-4o-mini-tts"
) -> Dict[str, int]:
    """
    Generate audio files for a specific scenario.
    
    Args:
        scenario: The scenario name
        output_dir: Base output directory
        voice: The voice to use
        model: The TTS model to use
    
    Returns:
        Dict with success and failure counts
    """
    if scenario not in AUDIO_SCENARIOS:
        print(f"Unknown scenario: {scenario}")
        return {"success": 0, "failed": 0}
    
    scenario_config = AUDIO_SCENARIOS[scenario]
    scenario_dir = Path(output_dir) / scenario
    
    print(f"\nGenerating {scenario} audio files...")
    print(f"Description: {scenario_config['description']}")
    print(f"Voice: {voice}")
    print(f"Output directory: {scenario_dir}")
    
    success_count = 0
    failed_count = 0
    
    for idx, phrase in enumerate(scenario_config["phrases"], 1):
        # Create filename
        filename = f"{scenario}_{idx:02d}.wav"
        output_path = scenario_dir / filename
        
        # Generate audio
        success = generate_audio_file(
            text=phrase,
            output_path=str(output_path),
            voice=voice,
            instructions=scenario_config["voice_instructions"],
            model=model
        )
        
        if success:
            success_count += 1
        else:
            failed_count += 1
    
    return {"success": success_count, "failed": failed_count}


def generate_all_audio(
    output_dir: str,
    voice: str,
    scenarios: Optional[List[str]] = None,
    model: str = "gpt-4o-mini-tts"
) -> None:
    """
    Generate audio files for all or specified scenarios.
    
    Args:
        output_dir: Base output directory
        voice: The voice to use
        scenarios: List of scenarios to generate (None for all)
        model: The TTS model to use
    """
    # Create directory structure
    create_directory_structure(output_dir)
    
    # Determine which scenarios to generate
    if scenarios is None:
        scenarios = list(AUDIO_SCENARIOS.keys())
    
    print(f"\nGenerating audio files for {len(scenarios)} scenario(s)")
    print(f"Voice: {voice}")
    print(f"Model: {model}")
    print(f"Output directory: {output_dir}")
    
    total_success = 0
    total_failed = 0
    
    # Generate audio for each scenario
    for scenario in scenarios:
        if scenario in AUDIO_SCENARIOS:
            result = generate_scenario_audio(scenario, output_dir, voice, model)
            total_success += result["success"]
            total_failed += result["failed"]
        else:
            print(f"Warning: Unknown scenario '{scenario}' skipped")
    
    # Summary
    print(f"\n{'='*50}")
    print(f"GENERATION COMPLETE")
    print(f"{'='*50}")
    print(f"Total successful: {total_success}")
    print(f"Total failed: {total_failed}")
    print(f"Output directory: {output_dir}")
    
    if total_failed == 0:
        print("🎉 All audio files generated successfully!")
    else:
        print(f"⚠️  {total_failed} files failed to generate")


def list_scenarios() -> None:
    """List all available scenarios."""
    print("Available scenarios:")
    print("-" * 50)
    for name, config in AUDIO_SCENARIOS.items():
        print(f"{name:20} - {config['description']}")
        print(f"{'':20}   {len(config['phrases'])} phrases")


def main():
    """Main function to handle command line arguments and execute generation."""
    parser = argparse.ArgumentParser(
        description="Generate mock audio files for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_mock_audio.py
  python scripts/generate_mock_audio.py --scenario customer_service
  python scripts/generate_mock_audio.py --voice alloy --output-dir opusagent/mock/audio
  python scripts/generate_mock_audio.py --list-scenarios
        """
    )
    
    parser.add_argument(
        "--scenario",
        choices=list(AUDIO_SCENARIOS.keys()),
        help="Specific scenario to generate (default: all scenarios)"
    )
    
    parser.add_argument(
        "--voice",
        choices=AVAILABLE_VOICES,
        default="alloy",
        help=f"Voice to use for TTS (default: alloy)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="opusagent/mock/audio",
        help="Output directory for audio files (default: opusagent/mock/audio)"
    )
    
    parser.add_argument(
        "--model",
        default="gpt-4o-mini-tts",
        help="TTS model to use (default: gpt-4o-mini-tts)"
    )
    
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List all available scenarios and exit"
    )
    
    args = parser.parse_args()
    
    # Handle list scenarios
    if args.list_scenarios:
        list_scenarios()
        return
    
    # Validate API key
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not found in environment")
        print("Please set your OpenAI API key in a .env file or environment variable")
        sys.exit(1)
    
    # Generate audio files
    scenarios = [args.scenario] if args.scenario else None
    generate_all_audio(
        output_dir=args.output_dir,
        voice=args.voice,
        scenarios=scenarios,
        model=args.model
    )


if __name__ == "__main__":
    main() 