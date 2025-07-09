#!/usr/bin/env python3
"""
Simple test runner for telephony validation.

This script makes it easy to run the telephony validation with proper environment setup.
It ensures the server is running and mock mode is enabled before running validation.

Usage:
    python scripts/run_validation.py
    
    # Run with specific options
    python scripts/run_validation.py --server-url ws://localhost:8000/ws/telephony --verbose
    
    # Run specific tests
    python scripts/run_validation.py --test session-flow
"""

import os
import subprocess
import sys
import time
from pathlib import Path

def check_server_running(server_url: str) -> bool:
    """Check if the server is running by attempting to connect."""
    try:
        import websockets
        import asyncio
        
        async def test_connection():
            try:
                # Convert WebSocket URL to HTTP URL for health check
                if server_url.startswith("ws://"):
                    http_url = server_url.replace("ws://", "http://")
                elif server_url.startswith("wss://"):
                    http_url = server_url.replace("wss://", "https://")
                else:
                    return False
                
                # Try to connect to the health endpoint
                import aiohttp
                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(f"{http_url.replace('/ws/telephony', '')}/health") as response:
                        return response.status == 200
            except Exception:
                return False
        
        return asyncio.run(test_connection())
    except ImportError:
        # If aiohttp is not available, just assume server is running
        return True

def setup_environment():
    """Set up environment variables for mock mode."""
    print("🔧 Setting up environment for mock mode...")
    
    # Set mock mode environment variables
    os.environ["OPUSAGENT_USE_MOCK"] = "true"
    os.environ["OPUSAGENT_MOCK_SERVER_URL"] = "ws://localhost:8080"
    
    # Set other useful environment variables
    os.environ["LOG_LEVEL"] = "INFO"
    
    print("✓ Environment variables set:")
    print(f"   OPUSAGENT_USE_MOCK: {os.environ.get('OPUSAGENT_USE_MOCK')}")
    print(f"   OPUSAGENT_MOCK_SERVER_URL: {os.environ.get('OPUSAGENT_MOCK_SERVER_URL')}")
    print(f"   LOG_LEVEL: {os.environ.get('LOG_LEVEL')}")

def start_server_if_needed(server_url: str):
    """Start the server if it's not already running."""
    print(f"🔍 Checking if server is running at {server_url}...")
    
    if check_server_running(server_url):
        print("✓ Server is already running")
        return True
    
    print("⚠️  Server is not running. Starting server...")
    
    try:
        # Start the server in the background
        server_process = subprocess.Popen(
            [sys.executable, "run_opus_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy()
        )
        
        # Wait a moment for server to start
        time.sleep(3)
        
        # Check if server started successfully
        if server_process.poll() is None:
            print("✓ Server started successfully")
            return True
        else:
            print("❌ Failed to start server")
            stdout, stderr = server_process.communicate()
            print(f"Server output: {stdout.decode()}")
            print(f"Server errors: {stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False

def main():
    """Main function to run validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run telephony validation with proper setup")
    parser.add_argument(
        "--server-url",
        default="ws://localhost:8000/ws/telephony",
        help="Telephony endpoint URL"
    )
    parser.add_argument(
        "--test",
        choices=["session-flow", "audio-streaming", "conversation-flow", "all"],
        default="all",
        help="Specific test to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--output",
        help="Output file for validation report (JSON)"
    )
    parser.add_argument(
        "--no-server-check",
        action="store_true",
        help="Skip server availability check"
    )
    
    args = parser.parse_args()
    
    print("🚀 Telephony Validation Runner")
    print("=" * 50)
    
    # Set up environment
    setup_environment()
    
    # Check/start server if needed
    if not args.no_server_check:
        if not start_server_if_needed(args.server_url):
            print("❌ Cannot proceed without server running")
            sys.exit(1)
    
    # Build validation command
    cmd = [
        sys.executable,
        "scripts/validate_telephony_mock.py",
        "--server-url", args.server_url,
        "--test", args.test
    ]
    
    if args.verbose:
        cmd.append("--verbose")
    
    if args.output:
        cmd.extend(["--output", args.output])
    
    print(f"\n🎯 Running validation: {' '.join(cmd)}")
    print("=" * 50)
    
    # Run validation
    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ Validation completed successfully")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Validation failed with exit code {e.returncode}")
        return e.returncode
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 