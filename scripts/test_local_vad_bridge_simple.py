#!/usr/bin/env python3
"""
Simple real-time VAD test script with console visualization.

Usage:
    python scripts/test_local_vad_bridge_simple.py --threshold 0.5

This script captures audio from your microphone in real-time, processes it through VAD,
and displays a simple console-based visualization of your voice and VAD events.
"""
import argparse
import asyncio
import logging
import sys
import threading
import time
import queue
import os
from pathlib import Path
import numpy as np
import sounddevice as sd
from collections import deque

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from opusagent.audio_stream_handler import AudioStreamHandler
from opusagent.bridges.audiocodes_bridge import AudioCodesBridge
from opusagent.models.audiocodes_api import TelephonyEventType
from opusagent.vad.vad_config import load_vad_config

class MockWebSocket:
    def __init__(self):
        self.sent_messages = []
        self.close_code = None
    
    async def send_json(self, payload):
        self.sent_messages.append(payload)
        # Suppress VAD event logging to keep display clean
    
    async def send(self, payload):
        self.sent_messages.append(payload)
        # Suppress VAD event logging to keep display clean
    
    async def close(self):
        pass
    
    # Add WebSocket compatibility methods
    async def receive_text(self):
        return ""
    
    async def receive_bytes(self):
        return b""
    
    async def receive_json(self):
        return {}
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        raise StopAsyncIteration

class SimpleVADVisualizer:
    def __init__(self, threshold=0.5, sample_rate=16000, chunk_size=1600):
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size  # 1600 samples = 3200 bytes for 16kHz 16-bit
        
        # Audio processing
        self.audio_queue = queue.Queue(maxsize=100)
        self.recording = False
        self.audio_thread = None
        
        # VAD processing
        self.vad_events = deque(maxlen=1000)  # Store VAD events with timestamps
        self.speech_active = False
        self.last_vad_time = 0
        
        # Visualization data
        self.audio_buffer = deque(maxlen=50)  # Store audio levels for display
        self.vad_buffer = deque(maxlen=50)    # Store VAD confidence for display
        self.time_buffer = deque(maxlen=50)   # Store timestamps for display
        
        # Setup VAD handler
        self._setup_vad_handler()
        
        # Console display
        self.display_width = 60
        self.last_display_time = 0
        self.display_interval = 0.1  # Update display every 100ms
        
    def _setup_vad_handler(self):
        """Initialize the VAD handler with mock websockets."""
        platform_ws = MockWebSocket()
        realtime_ws = MockWebSocket()
        
        # Patch VAD config
        vad_config = load_vad_config()
        vad_config['threshold'] = self.threshold
        
        # Create handler
        self.handler = AudioStreamHandler(platform_ws, realtime_ws)  # type: ignore
        self.handler.vad.threshold = self.threshold
        self.handler.vad_enabled = True
        self.handler._speech_active = False
        self.platform_ws = platform_ws
        
    def audio_callback(self, indata, frames, time_info, status):
        """Callback for sounddevice audio input."""
        if status:
            print(f"Audio callback status: {status}")
        
        if not self.recording:
            return
        
        try:
            # Convert to mono if stereo
            if indata.ndim > 1:
                audio_data = indata[:, 0]
            else:
                audio_data = indata
            
            # Normalize to float32
            audio_data = audio_data.astype(np.float32)
            
            # Calculate RMS level
            rms_level = np.sqrt(np.mean(audio_data ** 2))
            
            # Add to queue for processing
            try:
                self.audio_queue.put_nowait({
                    'audio': audio_data,
                    'rms': rms_level,
                    'timestamp': time.time()
                })
            except queue.Full:
                pass  # Drop oldest data if queue is full
                
        except Exception as e:
            print(f"Error in audio callback: {e}")
    
    def start_recording(self):
        """Start recording from microphone."""
        if self.recording:
            return
        
        self.recording = True
        self.audio_buffer.clear()
        self.vad_buffer.clear()
        self.time_buffer.clear()
        self.vad_events.clear()
        
        # Start audio stream
        self.stream = sd.InputStream(
            callback=self.audio_callback,
            channels=1,
            samplerate=self.sample_rate,
            blocksize=self.chunk_size,
            dtype=np.float32,
            latency='low'
        )
        self.stream.start()
        
        # Start processing thread
        self.audio_thread = threading.Thread(target=self._process_audio, daemon=True)
        self.audio_thread.start()
        
        # Start display thread
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()
        
        print("🎤 Started recording from microphone")
        print("Press Ctrl+C to stop")
        print("\n" + "="*60)
    
    def stop_recording(self):
        """Stop recording."""
        self.recording = False
        
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=2.0)
        
        if self.display_thread and self.display_thread.is_alive():
            self.display_thread.join(timeout=2.0)
        
        print("\n⏹️  Stopped recording")
    
    def _process_audio(self):
        """Process audio data in a separate thread."""
        while self.recording:
            try:
                # Get audio data from queue
                data = self.audio_queue.get(timeout=0.1)
                audio_data = data['audio']
                rms_level = data['rms']
                timestamp = data['timestamp']
                
                # Convert to int16 for VAD processing
                audio_int16 = (audio_data * 32767).astype(np.int16)
                audio_bytes = audio_int16.tobytes()
                
                # Process through VAD
                asyncio.run(self._process_vad(audio_bytes, rms_level, timestamp))
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing audio: {e}")
    
    async def _process_vad(self, audio_bytes, rms_level, timestamp):
        """Process audio through VAD and update visualization."""
        try:
            # Encode as base64 for handler
            import base64
            chunk_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            data = {"audioChunk": chunk_b64}
            
            # Process through VAD handler
            await self.handler.handle_incoming_audio(data)
            
            # Get VAD confidence from the VAD model
            # Convert audio bytes to numpy array for VAD processing
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            vad_result = self.handler.vad.process_audio(audio_array)
            vad_confidence = vad_result['speech_prob']
            
            # Check for VAD events
            current_speech_active = vad_confidence > self.threshold
            
            # Detect speech start/stop events
            if current_speech_active and not self.speech_active:
                # Speech started
                self.vad_events.append({
                    'type': 'speech_start',
                    'timestamp': timestamp,
                    'confidence': vad_confidence
                })
                # Don't print here - will show in display
            
            elif not current_speech_active and self.speech_active:
                # Speech stopped
                self.vad_events.append({
                    'type': 'speech_stop',
                    'timestamp': timestamp,
                    'confidence': vad_confidence
                })
                # Don't print here - will show in display
            
            self.speech_active = current_speech_active
            
            # Update visualization data
            self.audio_buffer.append(rms_level)
            self.vad_buffer.append(vad_confidence)
            self.time_buffer.append(timestamp)
            
        except Exception as e:
            print(f"Error in VAD processing: {e}")
    
    def _display_loop(self):
        """Display loop for console visualization."""
        while self.recording:
            try:
                current_time = time.time()
                if current_time - self.last_display_time >= self.display_interval:
                    self._update_display()
                    self.last_display_time = current_time
                time.sleep(0.05)
            except Exception as e:
                print(f"Error in display loop: {e}")
    
    def _update_display(self):
        """Update the console display."""
        try:
            # Clear screen (works on most terminals)
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # Get current values
            current_audio = self.audio_buffer[-1] if self.audio_buffer else 0.0
            current_vad = self.vad_buffer[-1] if self.vad_buffer else 0.0
            current_time = self.time_buffer[-1] if self.time_buffer else 0.0
            
            # Calculate time elapsed
            start_time = self.time_buffer[0] if self.time_buffer else current_time
            elapsed = current_time - start_time
            
            # Create audio level bar
            audio_bars = self._create_level_bar(current_audio, self.display_width)
            
            # Create VAD confidence bar
            vad_bars = self._create_level_bar(current_vad, self.display_width)
            
            # Create threshold indicator
            threshold_pos = int(self.threshold * self.display_width)
            threshold_line = " " * threshold_pos + "|" + " " * (self.display_width - threshold_pos)
            
            # Display header
            print(f"🎤 Real-time VAD Test (Threshold: {self.threshold})")
            print(f"⏱️  Time: {elapsed:.1f}s")
            print("=" * (self.display_width + 10))
            
            # Audio visualization
            print(f"🔊 Audio Level:    {audio_bars}")
            print(f"🎯 VAD Confidence: {vad_bars}")
            print(f"📊 Threshold:      {threshold_line}")
            print("=" * (self.display_width + 10))
            
            # Status with color coding
            if self.speech_active:
                status = "🟢 SPEECH ACTIVE"
                print(f"Status: {status}")
            else:
                status = "🔴 NO SPEECH"
                print(f"Status: {status}")
            
            # Show current values
            print(f"Audio Level: {current_audio:.3f}")
            print(f"VAD Confidence: {current_vad:.3f}")
            
            # Recent events (last 5)
            recent_events = list(self.vad_events)[-5:]  # Last 5 events
            if recent_events:
                print(f"\n📋 Recent Events (last 5):")
                for event in recent_events:
                    event_type = "🎤 START" if event['type'] == 'speech_start' else "🔇 STOP"
                    elapsed_event = event['timestamp'] - start_time
                    print(f"  {event_type} at {elapsed_event:.1f}s (conf: {event['confidence']:.3f})")
            
            # Instructions
            print(f"\n💡 Speak into your microphone to see VAD events!")
            print(f"   Press Ctrl+C to stop")
            
        except Exception as e:
            print(f"Error updating display: {e}")
    
    def _create_level_bar(self, value, width):
        """Create a visual bar for a value between 0 and 1."""
        if value <= 0:
            return "▁" * width
        elif value >= 1:
            return "█" * width
        else:
            filled = int(value * width)
            bars = "▁▂▃▄▅▆▇█"
            result = ""
            for i in range(width):
                if i < filled:
                    bar_idx = min(i * len(bars) // width, len(bars) - 1)
                    result += bars[bar_idx]
                else:
                    result += "▁"
            return result
    
    def print_summary(self):
        """Print a summary of VAD events."""
        print("\n" + "="*50)
        print("VAD TEST SUMMARY")
        print("="*50)
        
        total_events = len(self.vad_events)
        speech_starts = len([e for e in self.vad_events if e['type'] == 'speech_start'])
        speech_stops = len([e for e in self.vad_events if e['type'] == 'speech_stop'])
        
        print(f"Total VAD events: {total_events}")
        print(f"Speech starts: {speech_starts}")
        print(f"Speech stops: {speech_stops}")
        
        if self.vad_buffer:
            avg_confidence = np.mean(list(self.vad_buffer))
            max_confidence = np.max(list(self.vad_buffer))
            print(f"Average VAD confidence: {avg_confidence:.3f}")
            print(f"Maximum VAD confidence: {max_confidence:.3f}")
        
        print("="*50)

async def run_test(threshold):
    """Run the real-time VAD test."""
    visualizer = SimpleVADVisualizer(threshold=threshold)
    
    try:
        # Start recording
        visualizer.start_recording()
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nStopping...")
        visualizer.stop_recording()
        visualizer.print_summary()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple real-time VAD test with console visualization")
    parser.add_argument('--threshold', type=float, default=0.5, help='VAD threshold (default: 0.5)')
    args = parser.parse_args()
    
    # Suppress logging to keep console display clean
    logging.basicConfig(level=logging.ERROR)
    
    print("🎤 Simple Real-time VAD Test with Microphone Input")
    print(f"Threshold: {args.threshold}")
    print("Speak into your microphone to see VAD events in real-time!")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(run_test(args.threshold)) 