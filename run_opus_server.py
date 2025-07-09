"""
Run script for starting the Real-Time Voice Agent server with optimal latency settings.

This script configures and starts the FastAPI server with optimized WebSocket settings
for minimal latency in real-time audio streaming between AudioCodes and OpenAI.
Supports both real OpenAI API and mock mode via environment variables.

Usage:
    python run_opus_server.py [--port PORT] [--host HOST] [--mock] [--mock-server-url URL]

Environment Variables:
    OPUSAGENT_USE_MOCK=true          - Enable mock mode (default: false)
    OPUSAGENT_MOCK_SERVER_URL=URL    - Mock server URL (default: ws://localhost:8080)
    OPENAI_API_KEY=key               - OpenAI API key (required for real mode)
    PORT=port                        - Server port (default: 8000)
    HOST=host                        - Server host (default: 0.0.0.0)
    LOG_LEVEL=level                  - Logging level (default: INFO)

Examples:
    # Run with real OpenAI API
    python run_opus_server.py
    
    # Run with mock mode
    OPUSAGENT_USE_MOCK=true python run_opus_server.py
    
    # Run with custom mock server
    OPUSAGENT_USE_MOCK=true OPUSAGENT_MOCK_SERVER_URL=ws://localhost:9000 python run_opus_server.py
    
    # Run with command line flags
    python run_opus_server.py --mock --port 9000
"""

import argparse
import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

load_dotenv()

# Import constants from app (will also load environment variables)
sys.path.append(str(Path(__file__).parent))

from opusagent.config.logging_config import configure_logging

# Configure logging
logger = configure_logging("run")


def validate_mock_setup():
    """Validate mock mode setup and provide helpful information."""
    try:
        from opusagent.mock.mock_realtime_client import MockRealtimeClient
        from opusagent.websocket_manager import create_mock_websocket_manager
        
        # Test creating a mock client
        mock_client = MockRealtimeClient()
        logger.info("✓ MockRealtimeClient imported successfully")
        
        # Test creating a mock WebSocket manager
        mock_manager = create_mock_websocket_manager()
        logger.info("✓ Mock WebSocket manager created successfully")
        
        return True
        
    except ImportError as e:
        logger.error(f"✗ Mock client import failed: {e}")
        print(f"\nError: Mock client not available: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install -r requirements.txt")
        return False
    except Exception as e:
        logger.error(f"✗ Mock setup validation failed: {e}")
        print(f"\nError: Mock setup validation failed: {e}")
        return False


def show_mock_help():
    """Show helpful information about mock mode."""
    print("\n📚 Mock Mode Help:")
    print("==================")
    print("Mock mode allows you to test the server without using the real OpenAI API.")
    print("This is useful for development, testing, and when you don't have API credits.")
    print()
    print("Features available in mock mode:")
    print("  ✓ WebSocket connections and event handling")
    print("  ✓ Audio streaming (with generated audio files)")
    print("  ✓ Text responses (configurable)")
    print("  ✓ Function call simulation")
    print("  ✓ Session management")
    print()
    print("To generate audio files for mock mode:")
    print("  python scripts/generate_mock_audio.py")
    print()
    print("For more information:")
    print("  - Mock client docs: opusagent/mock/README.md")
    print("  - Environment variables: opusagent/mock/ENVIRONMENT_VARIABLES.md")
    print("  - Audio generation: scripts/README_audio_generation.md")
    print()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Start the Real-Time Voice Agent server with support for mock mode"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port to run the server on (default: 8000 or PORT env var)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "0.0.0.0"),
        help="Host to bind the server to (default: 0.0.0.0 or HOST env var)",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO or LOG_LEVEL env var)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Enable mock mode (overrides OPUSAGENT_USE_MOCK env var)",
    )
    parser.add_argument(
        "--mock-server-url",
        default=os.getenv("OPUSAGENT_MOCK_SERVER_URL", "ws://localhost:8080"),
        help="Mock server URL (default: ws://localhost:8080 or OPUSAGENT_MOCK_SERVER_URL env var)",
    )
    return parser.parse_args()


def main():
    """Main entry point for starting the server with optimized settings."""
    args = parse_args()

    # Handle mock mode configuration
    use_mock = args.mock or os.getenv("OPUSAGENT_USE_MOCK", "false").lower() == "true"
    
    if use_mock:
        # Set environment variables for mock mode
        os.environ["OPUSAGENT_USE_MOCK"] = "true"
        os.environ["OPUSAGENT_MOCK_SERVER_URL"] = args.mock_server_url
        logger.info("Mock mode enabled")
        logger.info(f"Mock server URL: {args.mock_server_url}")
        
        # Validate mock setup
        if not validate_mock_setup():
            print("\n❌ Mock mode setup validation failed")
            print("Please check the errors above and try again.")
            sys.exit(1)
        
        # Show mock help
        show_mock_help()
    else:
        # Verify OpenAI API key is set for real mode
        if not os.getenv("OPENAI_API_KEY"):
            logger.error("OPENAI_API_KEY environment variable not set")
            print("\nError: OPENAI_API_KEY environment variable is required for real mode")
            print("\nTo set the API key in PowerShell:")
            print("$env:OPENAI_API_KEY = 'your-api-key'")
            print("\nTo set the API key in Command Prompt:")
            print("set OPENAI_API_KEY=your-api-key")
            print("\nTo enable mock mode instead:")
            print("OPUSAGENT_USE_MOCK=true python run_opus_server.py")
            print("\nMake sure to replace 'your-api-key' with your actual OpenAI API key.")
            sys.exit(1)

        # Verify OpenAI API key format
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not api_key.startswith("sk-"):
            logger.error("Invalid OpenAI API key format")
            print("\nError: OpenAI API key must start with 'sk-'")
            print("Please check your API key and try again.")
            print("\nTo enable mock mode instead:")
            print("OPUSAGENT_USE_MOCK=true python run_opus_server.py")
            sys.exit(1)

    # Log server configuration
    logger.info("=== Server Configuration ===")
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Log level: {args.log_level}")
    logger.info(f"Environment: {os.getenv('ENV', 'production')}")
    logger.info(f"Mode: {'MOCK' if use_mock else 'REAL'} API")
    
    if use_mock:
        logger.info(f"Mock server URL: {args.mock_server_url}")
        logger.info("OpenAI API key: Not required (mock mode)")
    else:
        logger.info(f"OpenAI API key configured: {bool(os.getenv('OPENAI_API_KEY'))}")
        logger.info(
            f"OpenAI API key format: {'Valid' if api_key and api_key.startswith('sk-') else 'Invalid'}"
        )
    
    logger.info("=========================")

    try:
        # Check if port is available
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((args.host, args.port))
        sock.close()

        if result == 0:
            logger.error(f"Port {args.port} is already in use")
            print(f"\nError: Port {args.port} is already in use")
            print("Please choose a different port or stop the process using that port")
            sys.exit(1)

        # Configure uvicorn with optimized WebSocket settings for low latency
        config = uvicorn.Config(
            "opusagent.main:app",
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower(),
            # Use HTTP/1.1 for lower overhead than HTTP/2
            http="h11",
            # Disable access logs for lower overhead, we have our own logging
            access_log=False,
            # Reload on code changes during development
            reload=os.getenv("ENV", "production").lower() == "development",
            # WebSocket settings
            ws_ping_interval=5,  # Send ping frames every 5 seconds
            ws_ping_timeout=10,  # Wait 10 seconds for pong response
            ws_max_size=16 * 1024 * 1024,  # 16MB max WebSocket message size
            # Performance settings
            workers=1,  # Single worker for WebSocket support
            loop="asyncio",  # Use asyncio event loop
            timeout_keep_alive=5,  # Keep-alive timeout
        )

        # Log startup message
        if use_mock:
            print(f"\n🚀 Starting OpusAgent server in MOCK mode")
            print(f"   Mock server URL: {args.mock_server_url}")
            print(f"   Server URL: http://{args.host}:{args.port}")
            print(f"   Log level: {args.log_level}")
            print(f"\n   The server is using the MockRealtimeClient for testing.")
            print(f"   No OpenAI API calls will be made.")
        else:
            print(f"\n🚀 Starting OpusAgent server in REAL mode")
            print(f"   Server URL: http://{args.host}:{args.port}")
            print(f"   Log level: {args.log_level}")
            print(f"\n   The server is using the real OpenAI API.")
            print(f"   Make sure your API key is valid and has sufficient credits.")

        logger.info("Starting server with uvicorn...")
        server = uvicorn.Server(config)
        server.run()

    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        print(f"\nError: Failed to start server: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
