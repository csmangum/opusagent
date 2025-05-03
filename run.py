"""
Run script for starting the Real-Time Voice Agent server with optimal latency settings.

This script configures and starts the FastAPI server with optimized WebSocket settings
for minimal latency in real-time audio streaming between AudioCodes and OpenAI.

Usage:
    python run.py [--port PORT] [--host HOST]
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

from fastagent.config.logging_config import configure_logging

# Configure logging
logger = configure_logging()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Start the Real-Time Voice Agent server"
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
    return parser.parse_args()


def main():
    """Main entry point for starting the server with optimized settings."""
    args = parse_args()

    # Verify OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable not set")
        print("\nError: OPENAI_API_KEY environment variable is required")
        print("\nTo set the API key in PowerShell:")
        print("$env:OPENAI_API_KEY = 'your-api-key'")
        print("\nTo set the API key in Command Prompt:")
        print("set OPENAI_API_KEY=your-api-key")
        print("\nMake sure to replace 'your-api-key' with your actual OpenAI API key.")
        sys.exit(1)

    # Log server configuration
    logger.info("=== Server Configuration ===")
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Log level: {args.log_level}")
    logger.info(f"Environment: {os.getenv('ENV', 'production')}")
    logger.info(f"OpenAI API key configured: {bool(os.getenv('OPENAI_API_KEY'))}")
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
            "fastagent.main:app",
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

        logger.info("Starting server with uvicorn...")
        server = uvicorn.Server(config)
        server.run()

    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        print(f"\nError: Failed to start server: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
