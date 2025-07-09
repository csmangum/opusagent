#!/usr/bin/env python3
"""
Test script for the enhanced MockRealtimeClient.

This script demonstrates how to use the mock client with saved audio phrases
and different response configurations.
"""

import asyncio
import logging
from pathlib import Path

from opusagent.mock.mock_factory import (
    create_customer_service_mock,
    create_sales_mock,
    create_simple_mock,
    create_function_testing_mock,
    create_audio_testing_mock,
    create_test_audio_files
)
from opusagent.mock.realtime import MockRealtimeClient, MockResponseConfig


async def test_customer_service_mock():
    """Test the customer service mock client."""
    print("\n=== Testing Customer Service Mock ===")
    
    # Create test audio files
    create_test_audio_files()
    
    # Create the mock client
    mock_client = create_customer_service_mock()
    
    print("Customer service mock created with scenarios:")
    for key in mock_client.response_configs.keys():
        print(f"  - {key}")
    
    # Test a specific response
    config = mock_client.get_response_config("greeting")
    print(f"\nGreeting response: {config.text}")
    print(f"Audio file: {config.audio_file}")
    
    return mock_client


async def test_sales_mock():
    """Test the sales mock client."""
    print("\n=== Testing Sales Mock ===")
    
    # Create the mock client
    mock_client = create_sales_mock()
    
    print("Sales mock created with scenarios:")
    for key in mock_client.response_configs.keys():
        print(f"  - {key}")
    
    # Test a specific response
    config = mock_client.get_response_config("product_pitch")
    print(f"\nProduct pitch: {config.text}")
    print(f"Audio file: {config.audio_file}")
    
    return mock_client


async def test_simple_mock():
    """Test the simple mock client with custom responses."""
    print("\n=== Testing Simple Mock ===")
    
    # Define custom responses
    responses = {
        "hello": "Hi there! How are you doing today?",
        "help": "I'm here to help you with any questions you might have.",
        "thanks": "You're welcome! Is there anything else I can help you with?",
        "goodbye": "Goodbye! Have a great day!"
    }
    
    # Create the mock client
    mock_client = create_simple_mock(responses, audio_dir="demo/audio")
    
    print("Simple mock created with custom responses:")
    for key, text in responses.items():
        print(f"  - {key}: {text}")
    
    return mock_client


async def test_function_mock():
    """Test the function testing mock client."""
    print("\n=== Testing Function Mock ===")
    
    # Create the mock client
    mock_client = create_function_testing_mock()
    
    print("Function testing mock created with scenarios:")
    for key in mock_client.response_configs.keys():
        print(f"  - {key}")
    
    # Test a function call response
    config = mock_client.get_response_config("weather_function")
    print(f"\nWeather function call:")
    print(f"  Text: {config.text}")
    print(f"  Function: {config.function_call}")
    
    return mock_client


async def test_audio_mock():
    """Test the audio testing mock client."""
    print("\n=== Testing Audio Mock ===")
    
    # Define audio files for testing
    audio_files = {
        "test1": "demo/audio/greeting.wav",
        "test2": "demo/audio/goodbye.wav",
        "test3": "demo/audio/error.wav"
    }
    
    # Create the mock client
    mock_client = create_audio_testing_mock(audio_files)
    
    print("Audio testing mock created with audio files:")
    for key, audio_file in audio_files.items():
        print(f"  - {key}: {audio_file}")
    
    return mock_client


async def test_custom_mock():
    """Test creating a custom mock client."""
    print("\n=== Testing Custom Mock ===")
    
    # Create a custom mock client with specific configurations
    mock_client = MockRealtimeClient()
    
    # Add custom response configurations
    mock_client.add_response_config(
        "custom_greeting",
        MockResponseConfig(
            text="Welcome to our custom service!",
            audio_file="demo/audio/greeting.wav",
            delay_seconds=0.02,
            audio_chunk_delay=0.1
        )
    )
    
    mock_client.add_response_config(
        "custom_help",
        MockResponseConfig(
            text="I'm here to help with your custom needs.",
            delay_seconds=0.03
        )
    )
    
    print("Custom mock created with scenarios:")
    for key in mock_client.response_configs.keys():
        print(f"  - {key}")
    
    return mock_client


async def test_response_selection():
    """Test how response selection works."""
    print("\n=== Testing Response Selection ===")
    
    # Create a mock client with multiple responses
    mock_client = create_customer_service_mock()
    
    # Test different response selection scenarios
    scenarios = [
        "greeting",
        "account_help", 
        "billing_help",
        "nonexistent_key"
    ]
    
    for scenario in scenarios:
        config = mock_client.get_response_config(scenario)
        print(f"Scenario '{scenario}': {config.text}")
    
    return mock_client


async def test_audio_loading():
    """Test audio file loading functionality."""
    print("\n=== Testing Audio Loading ===")
    
    # Create test audio files
    create_test_audio_files()
    
    # Create a mock client
    mock_client = create_customer_service_mock()
    
    # Test loading an audio file
    audio_file = "demo/audio/greeting.wav"
    try:
        audio_data = await mock_client.load_audio_file(audio_file)
        print(f"Successfully loaded audio file: {audio_file}")
        print(f"Audio data size: {len(audio_data)} bytes")
    except Exception as e:
        print(f"Error loading audio file: {e}")
    
    # Test loading a non-existent file
    try:
        audio_data = await mock_client.load_audio_file("nonexistent.wav")
        print(f"Fallback audio data size: {len(audio_data)} bytes")
    except Exception as e:
        print(f"Error with fallback: {e}")
    
    return mock_client


async def main():
    """Run all tests."""
    print("Testing Enhanced MockRealtimeClient")
    print("=" * 50)
    
    # Create test audio files first
    create_test_audio_files()
    
    # Run all tests
    tests = [
        test_customer_service_mock,
        test_sales_mock,
        test_simple_mock,
        test_function_mock,
        test_audio_mock,
        test_custom_mock,
        test_response_selection,
        test_audio_loading
    ]
    
    for test in tests:
        try:
            await test()
        except Exception as e:
            print(f"Error in {test.__name__}: {e}")
    
    print("\n" + "=" * 50)
    print("All tests completed!")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the tests
    asyncio.run(main()) 