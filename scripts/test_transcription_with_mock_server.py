#!/usr/bin/env python3
"""
Test Transcription with Mock WebSocket Server

This script tests the transcription functionality of the LocalRealtimeClient
by setting up a mock WebSocket server and simulating a complete transcription
flow with audio data.

Features:
- Sets up a mock WebSocket server
- Tests transcription with real audio data
- Validates transcription events
- Tests both PocketSphinx and Whisper backends
- Simulates real-time audio streaming

Usage:
    python scripts/test_transcription_with_mock_server.py [options]

Options:
    --backend pocketsphinx|whisper    Test specific backend
    --audio-file path/to/audio.wav    Use specific audio file
    --generate-test-audio             Generate test audio
    --verbose                         Enable verbose logging
"""

import asyncio
import argparse
import base64
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import websockets
from websockets.server import WebSocketServerProtocol

from opusagent.mock.realtime import (
    LocalRealtimeClient,
    TranscriptionConfig,
    TranscriptionFactory
)
from opusagent.models.openai_api import SessionConfig


class MockWebSocketServer:
    """Mock WebSocket server for testing transcription."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.clients: List[WebSocketServerProtocol] = []
        self.received_messages: List[Dict[str, Any]] = []
        self.transcription_events: List[Dict[str, Any]] = []
        
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle WebSocket client connection."""
        self.clients.append(websocket)
        self.logger.info(f"Client connected: {websocket.remote_address}")
        
        try:
            async for message in websocket:
                # Parse message
                try:
                    data = json.loads(message)
                    self.received_messages.append(data)
                    
                    # Handle different message types
                    await self.handle_message(websocket, data)
                    
                except json.JSONDecodeError:
                    self.logger.warning(f"Received non-JSON message: {message}")
                    
        except websockets.ConnectionClosed:
            self.logger.info(f"Client disconnected: {websocket.remote_address}")
        finally:
            if websocket in self.clients:
                self.clients.remove(websocket)
    
    async def handle_message(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle incoming WebSocket messages."""
        message_type = data.get("type")
        
        if message_type == "session.update":
            # Send session.updated event
            response = {
                "type": "session.updated",
                "session": data.get("session", {})
            }
            await websocket.send(json.dumps(response))
            
        elif message_type == "input_audio_buffer.append":
            # Acknowledge audio append
            response = {
                "type": "input_audio_buffer.appended"
            }
            await websocket.send(json.dumps(response))
            
        elif message_type == "input_audio_buffer.commit":
            # Acknowledge audio commit
            item_id = data.get("item_id", "test_item_123")
            response = {
                "type": "input_audio_buffer.committed",
                "item_id": item_id
            }
            await websocket.send(json.dumps(response))
            
        elif message_type == "response.create":
            # Acknowledge response creation
            response_id = data.get("response", {}).get("id", "test_response_123")
            response = {
                "type": "response.created",
                "response": {
                    "id": response_id,
                    "created_at": int(time.time() * 1000)
                }
            }
            await websocket.send(json.dumps(response))
    
    async def send_transcription_event(self, event: Dict[str, Any]):
        """Send transcription event to all connected clients."""
        for client in self.clients:
            try:
                await client.send(json.dumps(event))
                self.transcription_events.append(event)
            except websockets.ConnectionClosed:
                self.logger.warning("Failed to send transcription event to disconnected client")
    
    def get_transcription_events(self) -> List[Dict[str, Any]]:
        """Get all transcription events sent."""
        return self.transcription_events.copy()
    
    def get_received_messages(self) -> List[Dict[str, Any]]:
        """Get all received messages."""
        return self.received_messages.copy()


class TranscriptionTester:
    """Tester for transcription functionality."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.server = MockWebSocketServer(logger)
        self.server_task = None
        self.client = None
        
    async def start_server(self, host: str = "localhost", port: int = 8080):
        """Start the mock WebSocket server."""
        self.server_task = await websockets.serve(
            self.server.handle_client,
            host,
            port
        )
        self.logger.info(f"Mock WebSocket server started on ws://{host}:{port}")
    
    async def stop_server(self):
        """Stop the mock WebSocket server."""
        if self.server_task:
            self.server_task.close()
            await self.server_task.wait_closed()
            self.logger.info("Mock WebSocket server stopped")
    
    async def create_client(self, backend: str = "pocketsphinx") -> LocalRealtimeClient:
        """Create and configure LocalRealtimeClient with transcription."""
        # Configure transcription
        transcription_config = {
            "backend": backend,
            "language": "en",
            "chunk_duration": 1.0,
            "confidence_threshold": 0.5
        }
        
        # Configure session
        session_config = SessionConfig(
            model="gpt-4o-realtime-preview-2025-06-03",
            modalities=["text", "audio"],
            voice="alloy",
            input_audio_transcription={"model": "local"}
        )
        
        # Create client
        self.client = LocalRealtimeClient(
            session_config=session_config,
            enable_transcription=True,
            transcription_config=transcription_config
        )
        
        return self.client
    
    async def test_transcription_flow(self, audio_file: Optional[str] = None) -> bool:
        """Test complete transcription flow."""
        self.logger.info("Testing transcription flow...")
        
        try:
            # Connect client to server
            if self.client:
                await self.client.connect("ws://localhost:8080")
                self.logger.info("Client connected to server")
                
                # Wait for session creation
                await asyncio.sleep(0.1)
                
                # Generate or load test audio
                if audio_file and os.path.exists(audio_file):
                    with open(audio_file, 'rb') as f:
                        audio_data = f.read()
                    self.logger.info(f"Loaded audio file: {audio_file} ({len(audio_data)} bytes)")
                else:
                    # Generate test audio (1 second of 440Hz sine wave)
                    audio_data = self.generate_test_audio()
                    self.logger.info(f"Generated test audio ({len(audio_data)} bytes)")
                
                # Split audio into chunks
                chunk_size = 3200  # 200ms at 16kHz 16-bit
                chunks = [audio_data[i:i + chunk_size] for i in range(0, len(audio_data), chunk_size)]
                
                self.logger.info(f"Processing {len(chunks)} audio chunks...")
                
                # Send audio chunks
                for i, chunk in enumerate(chunks):
                    # Encode chunk as base64
                    chunk_b64 = base64.b64encode(chunk).decode('utf-8')
                    
                    # Send audio append event
                    append_event = {
                        "type": "input_audio_buffer.append",
                        "audio": chunk_b64
                    }
                    
                    # Simulate sending to client (in real scenario, this would come from client)
                    await self.client.handle_audio_append(append_event)
                    
                    # Small delay between chunks
                    await asyncio.sleep(0.1)
                
                # Commit audio buffer
                commit_event = {
                    "type": "input_audio_buffer.commit"
                }
                await self.client.handle_audio_commit(commit_event)
            else:
                self.logger.error("Client not initialized")
                return False
            
            # Wait for transcription to complete
            await asyncio.sleep(2.0)
            
            # Check transcription events
            transcription_events = self.server.get_transcription_events()
            
            if transcription_events:
                self.logger.info(f"Received {len(transcription_events)} transcription events:")
                for event in transcription_events:
                    self.logger.info(f"  {event['type']}: {event.get('delta', event.get('transcript', ''))}")
                return True
            else:
                self.logger.warning("No transcription events received")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during transcription flow: {e}")
            return False
    
    def generate_test_audio(self) -> bytes:
        """Generate test audio data (1 second of 440Hz sine wave)."""
        try:
            import numpy as np
            
            # Generate 1 second of 440Hz sine wave at 16kHz
            sample_rate = 16000
            duration = 1.0
            frequency = 440.0
            
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            audio_data = np.sin(2 * np.pi * frequency * t)
            
            # Convert to 16-bit PCM
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            return audio_int16.tobytes()
            
        except ImportError:
            # Fallback: generate silence
            self.logger.warning("NumPy not available, generating silence")
            return bytes([0] * 32000)  # 1 second of silence
    
    async def test_backend_availability(self, backend: str) -> bool:
        """Test if transcription backend is available."""
        try:
            available_backends = TranscriptionFactory.get_available_backends()
            if backend in available_backends:
                self.logger.info(f"Backend {backend} is available")
                return True
            else:
                self.logger.warning(f"Backend {backend} is not available")
                return False
        except Exception as e:
            self.logger.error(f"Error checking backend availability: {e}")
            return False
    
    async def run_tests(self, backend: str, audio_file: Optional[str] = None) -> Dict[str, Any]:
        """Run comprehensive transcription tests."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "backend": backend,
            "tests": [],
            "success": False
        }
        
        try:
            # Test backend availability
            if not await self.test_backend_availability(backend):
                results["tests"].append({
                    "name": "Backend Availability",
                    "passed": False,
                    "details": f"Backend {backend} not available"
                })
                return results
            
            results["tests"].append({
                "name": "Backend Availability",
                "passed": True,
                "details": f"Backend {backend} is available"
            })
            
            # Start server
            await self.start_server()
            
            # Create client
            client = await self.create_client(backend)
            
            # Test transcription flow
            flow_success = await self.test_transcription_flow(audio_file)
            
            results["tests"].append({
                "name": "Transcription Flow",
                "passed": flow_success,
                "details": "Complete transcription flow test"
            })
            
            # Check transcription events
            transcription_events = self.server.get_transcription_events()
            events_success = len(transcription_events) > 0
            
            results["tests"].append({
                "name": "Transcription Events",
                "passed": events_success,
                "details": f"Received {len(transcription_events)} transcription events"
            })
            
            # Overall success
            results["success"] = all(test["passed"] for test in results["tests"])
            
            # Cleanup
            if client:
                await client.disconnect()
            await self.stop_server()
            
        except Exception as e:
            self.logger.error(f"Error during testing: {e}")
            results["tests"].append({
                "name": "Test Execution",
                "passed": False,
                "details": f"Test execution error: {e}"
            })
            results["success"] = False
        
        return results


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


async def main():
    """Main entry point for the transcription test."""
    parser = argparse.ArgumentParser(description="Test transcription with mock WebSocket server")
    parser.add_argument("--backend", choices=["pocketsphinx", "whisper"], 
                       default="pocketsphinx", help="Test specific backend")
    parser.add_argument("--audio-file", help="Path to audio file for testing")
    parser.add_argument("--generate-test-audio", action="store_true", 
                       help="Generate test audio files")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    # Create tester and run tests
    tester = TranscriptionTester(logger)
    
    try:
        results = await tester.run_tests(
            backend=args.backend,
            audio_file=args.audio_file
        )
        
        # Print results
        logger.info("\n=== Test Results ===")
        for test in results["tests"]:
            status = "PASSED" if test["passed"] else "FAILED"
            logger.info(f"{status}: {test['name']} - {test['details']}")
        
        logger.info(f"\nOverall: {'SUCCESS' if results['success'] else 'FAILED'}")
        
        # Exit with appropriate code
        sys.exit(0 if results["success"] else 1)
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 