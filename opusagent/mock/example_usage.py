#!/usr/bin/env python3
"""
Example usage of the enhanced LocalRealtimeClient with saved audio phrases.

This example shows how to configure the mock client to return different
responses based on scenarios, including saved audio files.
"""

import asyncio
import logging
from pathlib import Path

from opusagent.mock.realtime import LocalRealtimeClient, LocalResponseConfig
from opusagent.models.openai_api import SessionConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Example of using the enhanced LocalRealtimeClient."""
    
    # Create session configuration
    session_config = SessionConfig(
        model="gpt-4o-realtime-preview-2025-06-03",
        modalities=["text", "audio"],
        voice="alloy",
        input_audio_format="pcm16",
        output_audio_format="pcm16"
    )
    
    # Create response configurations for different scenarios
    response_configs = {
        "greeting": LocalResponseConfig(
            text="Hello! Welcome to our customer service. How can I help you today?",
            audio_file="demo/audio/greeting.wav",  # Path to saved audio file
            delay_seconds=0.03,
            audio_chunk_delay=0.15
        ),
        
        "help": LocalResponseConfig(
            text="I'd be happy to help you with that. Let me look into your account.",
            audio_file="demo/audio/help_response.wav",
            delay_seconds=0.04,
            audio_chunk_delay=0.2
        ),
        
        "goodbye": LocalResponseConfig(
            text="Thank you for calling. Have a great day!",
            audio_file="demo/audio/goodbye.wav",
            delay_seconds=0.05,
            audio_chunk_delay=0.25
        ),
        
        "function_call": LocalResponseConfig(
            text="I'll check your account balance for you.",
            function_call={
                "name": "get_account_balance",
                "arguments": {
                    "account_id": "12345",
                    "include_transactions": True
                }
            },
            delay_seconds=0.03
        ),
        
        "error": LocalResponseConfig(
            text="I'm sorry, I'm having trouble processing your request right now.",
            audio_file="demo/audio/error_response.wav",
            delay_seconds=0.06,
            audio_chunk_delay=0.3
        )
    }
    
    # Create default response configuration
    default_config = LocalResponseConfig(
        text="I understand your request. Let me process that for you.",
        audio_file="demo/audio/default_response.wav",
        delay_seconds=0.04,
        audio_chunk_delay=0.2
    )
    
    # Create the mock client
    mock_client = LocalRealtimeClient(
        logger=logger,
        session_config=session_config,
        response_configs=response_configs,
        default_response_config=default_config
    )
    
    # Example: Add a custom response configuration at runtime
    mock_client.add_response_config(
        "custom",
        LocalResponseConfig(
            text="This is a custom response that was added dynamically.",
            audio_file="demo/audio/custom_response.wav",
            delay_seconds=0.02,
            audio_chunk_delay=0.1
        )
    )
    
    # Example: Create a response config with raw audio data
    # You can also provide raw audio bytes instead of a file path
    raw_audio_data = b'\x00\x00\x00\x00' * 16000  # 1 second of silence at 16kHz
    mock_client.add_response_config(
        "raw_audio",
        LocalResponseConfig(
            text="This response uses raw audio data.",
            audio_data=raw_audio_data,
            delay_seconds=0.03,
            audio_chunk_delay=0.15
        )
    )
    
    logger.info("LocalRealtimeClient configured with multiple response scenarios")
    logger.info(f"Available response keys: {list(response_configs.keys())}")
    
    # Example: Simulate connecting to a mock server
    try:
        await mock_client.connect("ws://localhost:8080")
        logger.info("Connected to mock server")
        
        # Simulate some interactions
        await simulate_interactions(mock_client)
        
    except Exception as e:
        logger.warning(f"Could not connect to mock server: {e}")
        logger.info("Mock client is ready for use with WebSocket manager")
    
    finally:
        await mock_client.disconnect()


async def simulate_interactions(mock_client: LocalRealtimeClient):
    """Simulate some interactions with the mock client."""
    logger.info("Simulating interactions...")
    
    # Note: The internal methods are now in the handlers module
    # For real usage, you would connect to a WebSocket server and send events
    # This is just a demonstration of the mock client setup
    
    logger.info("Mock client configured and ready for use")
    logger.info("To test with WebSocket, use create_mock_websocket_manager()")
    
    # Wait a moment to show the setup is complete
    await asyncio.sleep(1)
    logger.info("Simulation complete")


def create_audio_files():
    """Create example audio files for testing."""
    demo_dir = Path("demo/audio")
    demo_dir.mkdir(parents=True, exist_ok=True)
    
    # Create simple WAV files (silence for demo purposes)
    audio_files = [
        "greeting.wav",
        "help_response.wav", 
        "goodbye.wav",
        "error_response.wav",
        "default_response.wav",
        "custom_response.wav"
    ]
    
    for filename in audio_files:
        file_path = demo_dir / filename
        if not file_path.exists():
            # Create a simple WAV file with silence
            create_simple_wav(file_path, duration=2.0)
            print(f"Created {file_path}")


def create_simple_wav(file_path: Path, duration: float = 2.0, sample_rate: int = 16000):
    """Create a simple WAV file with silence."""
    import struct
    
    # WAV file header
    num_samples = int(sample_rate * duration)
    data_size = num_samples * 2  # 16-bit samples
    
    with open(file_path, 'wb') as f:
        # RIFF header
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + data_size))  # File size
        f.write(b'WAVE')
        
        # fmt chunk
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))  # Chunk size
        f.write(struct.pack('<H', 1))   # Audio format (PCM)
        f.write(struct.pack('<H', 1))   # Number of channels
        f.write(struct.pack('<I', sample_rate))  # Sample rate
        f.write(struct.pack('<I', sample_rate * 2))  # Byte rate
        f.write(struct.pack('<H', 2))   # Block align
        f.write(struct.pack('<H', 16))  # Bits per sample
        
        # data chunk
        f.write(b'data')
        f.write(struct.pack('<I', data_size))
        
        # Audio data (silence)
        f.write(b'\x00\x00' * num_samples)


if __name__ == "__main__":
    # Create example audio files
    create_audio_files()
    
    # Run the example
    asyncio.run(main()) 