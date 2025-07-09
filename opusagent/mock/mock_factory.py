#!/usr/bin/env python3
"""
Factory functions for creating MockRealtimeClient instances with common configurations.

This module provides convenient factory functions to create mock clients
with pre-configured responses and audio files for different testing scenarios.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

from opusagent.mock.mock_realtime_client import MockRealtimeClient, MockResponseConfig
from opusagent.models.openai_api import SessionConfig


def create_customer_service_mock(
    audio_dir: str = "demo/audio",
    logger: Optional[logging.Logger] = None
) -> MockRealtimeClient:
    """
    Create a mock client configured for customer service scenarios.
    
    Args:
        audio_dir: Directory containing audio files
        logger: Optional logger instance
        
    Returns:
        Configured MockRealtimeClient for customer service testing
    """
    
    # Create session configuration
    session_config = SessionConfig(
        model="gpt-4o-realtime-preview-2025-06-03",
        modalities=["text", "audio"],
        voice="alloy",
        input_audio_format="pcm16",
        output_audio_format="pcm16"
    )
    
    # Define customer service response configurations
    response_configs = {
        "greeting": MockResponseConfig(
            text="Hello! Welcome to our customer service. How can I help you today?",
            audio_file=f"{audio_dir}/greeting.wav",
            delay_seconds=0.03,
            audio_chunk_delay=0.15
        ),
        
        "account_help": MockResponseConfig(
            text="I'd be happy to help you with your account. Let me look that up for you.",
            audio_file=f"{audio_dir}/account_help.wav",
            delay_seconds=0.04,
            audio_chunk_delay=0.2
        ),
        
        "billing_help": MockResponseConfig(
            text="I can help you with your billing questions. Let me check your account.",
            audio_file=f"{audio_dir}/billing_help.wav",
            delay_seconds=0.04,
            audio_chunk_delay=0.2
        ),
        
        "technical_support": MockResponseConfig(
            text="I understand you're having technical issues. Let me help you troubleshoot.",
            audio_file=f"{audio_dir}/tech_support.wav",
            delay_seconds=0.05,
            audio_chunk_delay=0.25
        ),
        
        "transfer": MockResponseConfig(
            text="I'll transfer you to a specialist who can better assist you.",
            audio_file=f"{audio_dir}/transfer.wav",
            delay_seconds=0.04,
            audio_chunk_delay=0.2
        ),
        
        "goodbye": MockResponseConfig(
            text="Thank you for calling. Have a great day!",
            audio_file=f"{audio_dir}/goodbye.wav",
            delay_seconds=0.05,
            audio_chunk_delay=0.25
        ),
        
        "error": MockResponseConfig(
            text="I'm sorry, I'm having trouble processing your request right now. Please try again.",
            audio_file=f"{audio_dir}/error.wav",
            delay_seconds=0.06,
            audio_chunk_delay=0.3
        )
    }
    
    # Default response
    default_config = MockResponseConfig(
        text="I understand your request. Let me process that for you.",
        audio_file=f"{audio_dir}/default_response.wav",
        delay_seconds=0.04,
        audio_chunk_delay=0.2
    )
    
    return MockRealtimeClient(
        logger=logger,
        session_config=session_config,
        response_configs=response_configs,
        default_response_config=default_config
    )


def create_sales_mock(
    audio_dir: str = "demo/audio",
    logger: Optional[logging.Logger] = None
) -> MockRealtimeClient:
    """
    Create a mock client configured for sales scenarios.
    
    Args:
        audio_dir: Directory containing audio files
        logger: Optional logger instance
        
    Returns:
        Configured MockRealtimeClient for sales testing
    """
    
    session_config = SessionConfig(
        model="gpt-4o-realtime-preview-2025-06-03",
        modalities=["text", "audio"],
        voice="alloy",
        input_audio_format="pcm16",
        output_audio_format="pcm16"
    )
    
    response_configs = {
        "sales_greeting": MockResponseConfig(
            text="Hi there! I'm calling about our special offer today. Are you interested?",
            audio_file=f"{audio_dir}/sales_greeting.wav",
            delay_seconds=0.03,
            audio_chunk_delay=0.15
        ),
        
        "product_pitch": MockResponseConfig(
            text="Our product offers amazing benefits that can save you money and time.",
            audio_file=f"{audio_dir}/product_pitch.wav",
            delay_seconds=0.04,
            audio_chunk_delay=0.2
        ),
        
        "price_quote": MockResponseConfig(
            text="The special price today is just $99.99. That's a 50% discount!",
            audio_file=f"{audio_dir}/price_quote.wav",
            delay_seconds=0.05,
            audio_chunk_delay=0.25
        ),
        
        "objection_handling": MockResponseConfig(
            text="I understand your concern. Let me explain how this actually saves you money.",
            audio_file=f"{audio_dir}/objection_handling.wav",
            delay_seconds=0.04,
            audio_chunk_delay=0.2
        ),
        
        "closing": MockResponseConfig(
            text="Would you like to take advantage of this offer today?",
            audio_file=f"{audio_dir}/closing.wav",
            delay_seconds=0.04,
            audio_chunk_delay=0.2
        ),
        
        "thank_you": MockResponseConfig(
            text="Thank you for your time today. Have a wonderful day!",
            audio_file=f"{audio_dir}/thank_you.wav",
            delay_seconds=0.05,
            audio_chunk_delay=0.25
        )
    }
    
    default_config = MockResponseConfig(
        text="Thank you for your interest. Let me tell you more about our offer.",
        audio_file=f"{audio_dir}/sales_default.wav",
        delay_seconds=0.04,
        audio_chunk_delay=0.2
    )
    
    return MockRealtimeClient(
        logger=logger,
        session_config=session_config,
        response_configs=response_configs,
        default_response_config=default_config
    )


def create_simple_mock(
    responses: Dict[str, str],
    audio_dir: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> MockRealtimeClient:
    """
    Create a simple mock client with custom text responses.
    
    Args:
        responses: Dictionary mapping scenario keys to response text
        audio_dir: Optional directory for audio files (if None, uses silence)
        logger: Optional logger instance
        
    Returns:
        Configured MockRealtimeClient with custom responses
    """
    
    session_config = SessionConfig(
        model="gpt-4o-realtime-preview-2025-06-03",
        modalities=["text", "audio"],
        voice="alloy"
    )
    
    # Create response configs from the provided responses
    response_configs = {}
    for key, text in responses.items():
        audio_file = None
        if audio_dir:
            audio_file = f"{audio_dir}/{key}.wav"
        
        response_configs[key] = MockResponseConfig(
            text=text,
            audio_file=audio_file,
            delay_seconds=0.03,
            audio_chunk_delay=0.2
        )
    
    default_config = MockResponseConfig(
        text="I understand. Let me help you with that.",
        audio_file=f"{audio_dir}/default.wav" if audio_dir else None,
        delay_seconds=0.04,
        audio_chunk_delay=0.2
    )
    
    return MockRealtimeClient(
        logger=logger,
        session_config=session_config,
        response_configs=response_configs,
        default_response_config=default_config
    )


def create_function_testing_mock(
    logger: Optional[logging.Logger] = None
) -> MockRealtimeClient:
    """
    Create a mock client configured for testing function calls.
    
    Args:
        logger: Optional logger instance
        
    Returns:
        Configured MockRealtimeClient for function call testing
    """
    
    session_config = SessionConfig(
        model="gpt-4o-realtime-preview-2025-06-03",
        modalities=["text"],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather information for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"},
                            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                        },
                        "required": ["location"]
                    }
                }
            },
            {
                "type": "function", 
                "function": {
                    "name": "get_account_balance",
                    "description": "Get account balance information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_id": {"type": "string"},
                            "include_transactions": {"type": "boolean"}
                        },
                        "required": ["account_id"]
                    }
                }
            }
        ]
    )
    
    response_configs = {
        "weather_function": MockResponseConfig(
            text="I'll check the weather for you.",
            function_call={
                "name": "get_weather",
                "arguments": {
                    "location": "New York",
                    "unit": "fahrenheit"
                }
            },
            delay_seconds=0.03
        ),
        
        "account_function": MockResponseConfig(
            text="Let me look up your account information.",
            function_call={
                "name": "get_account_balance",
                "arguments": {
                    "account_id": "12345",
                    "include_transactions": True
                }
            },
            delay_seconds=0.03
        )
    }
    
    default_config = MockResponseConfig(
        text="I can help you with that. What would you like me to do?",
        delay_seconds=0.04
    )
    
    return MockRealtimeClient(
        logger=logger,
        session_config=session_config,
        response_configs=response_configs,
        default_response_config=default_config
    )


def create_audio_testing_mock(
    audio_files: Dict[str, str],
    logger: Optional[logging.Logger] = None
) -> MockRealtimeClient:
    """
    Create a mock client specifically for testing audio responses.
    
    Args:
        audio_files: Dictionary mapping scenario keys to audio file paths
        logger: Optional logger instance
        
    Returns:
        Configured MockRealtimeClient for audio testing
    """
    
    session_config = SessionConfig(
        model="gpt-4o-realtime-preview-2025-06-03",
        modalities=["text", "audio"],
        voice="alloy",
        input_audio_format="pcm16",
        output_audio_format="pcm16"
    )
    
    response_configs = {}
    for key, audio_file in audio_files.items():
        response_configs[key] = MockResponseConfig(
            text=f"Playing audio for scenario: {key}",
            audio_file=audio_file,
            delay_seconds=0.02,
            audio_chunk_delay=0.1
        )
    
    default_config = MockResponseConfig(
        text="Default audio response",
        delay_seconds=0.03,
        audio_chunk_delay=0.2
    )
    
    return MockRealtimeClient(
        logger=logger,
        session_config=session_config,
        response_configs=response_configs,
        default_response_config=default_config
    )


# Convenience function to create audio files for testing
def create_test_audio_files(base_dir: str = "demo/audio"):
    """Create test audio files for the mock clients."""
    audio_dir = Path(base_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    # Define audio files for different scenarios
    audio_files = {
        # Customer service
        "greeting.wav": 2.0,
        "account_help.wav": 3.0,
        "billing_help.wav": 3.0,
        "tech_support.wav": 3.0,
        "transfer.wav": 2.5,
        "goodbye.wav": 2.0,
        "error.wav": 2.5,
        "default_response.wav": 2.5,
        
        # Sales
        "sales_greeting.wav": 2.5,
        "product_pitch.wav": 4.0,
        "price_quote.wav": 3.0,
        "objection_handling.wav": 3.5,
        "closing.wav": 2.0,
        "thank_you.wav": 2.0,
        "sales_default.wav": 2.5,
        
        # General
        "default.wav": 2.0
    }
    
    for filename, duration in audio_files.items():
        file_path = audio_dir / filename
        if not file_path.exists():
            create_simple_wav(file_path, duration)
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