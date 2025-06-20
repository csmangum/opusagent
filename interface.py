import asyncio
import base64
import json
import logging
import threading
import tkinter as tk
from tkinter import ttk
import wave
import pyaudio
import websockets
import numpy as np
from scipy import signal
import queue
import uuid
from pathlib import Path
import sys
import time

class AudioInterface:
    def __init__(self, root):
        print("[DEBUG] Initializing AudioInterface", file=sys.stderr)
        self.root = root
        self.root.title("Audio Chat Interface")
        
        # Audio settings
        self.CHUNK = 32000
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        
        # WebSocket state
        self.ws = None
        self.connected = False
        self.conversation_id = None
        self.loop = None
        self.ws_thread = None
        
        # Audio state
        self.recording = False
        self.audio_queue = queue.Queue()
        
        # Initialize PyAudio with error handling
        try:
            self.p = pyaudio.PyAudio()
            # List available devices
            self.input_device = self._select_input_device()
            self.output_device = self._select_output_device()
            print(f"[DEBUG] Selected input device: {self.input_device}", file=sys.stderr)
            print(f"[DEBUG] Selected output device: {self.output_device}", file=sys.stderr)
        except Exception as e:
            print(f"[DEBUG] Error initializing PyAudio: {e}", file=sys.stderr)
            self.p = None
        
        # Create UI
        self.create_widgets()
        
        # Start audio thread
        if self.p:
            self.audio_thread = threading.Thread(target=self._audio_thread, daemon=True)
            self.audio_thread.start()
        
        print("[DEBUG] AudioInterface initialized", file=sys.stderr)
        
    def create_widgets(self):
        print("[DEBUG] Creating widgets", file=sys.stderr)
        # Connection frame
        conn_frame = ttk.LabelFrame(self.root, text="Connection", padding=10)
        conn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Hardcoded URL, no entry
        self.url_var = tk.StringVar(value="ws://localhost:8000/ws/telephony")
        ttk.Label(conn_frame, text="ws://localhost:8000/ws/telephony").pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side=tk.RIGHT, padx=5)
        
        # Talk button
        self.talk_btn = ttk.Button(self.root, text="Hold to Talk", state=tk.DISABLED)
        self.talk_btn.bind('<ButtonPress-1>', self.start_recording)
        self.talk_btn.bind('<ButtonRelease-1>', self.stop_recording)
        self.talk_btn.pack(pady=20)
        
        # Status label
        self.status_var = tk.StringVar(value="Not connected")
        ttk.Label(self.root, textvariable=self.status_var).pack(pady=5)
        
        print("[DEBUG] Widgets created", file=sys.stderr)
        
    def toggle_connection(self):
        print(f"[DEBUG] toggle_connection: connected={self.connected}", file=sys.stderr)
        if not self.connected:
            self.connect()
        else:
            self.disconnect()
            
    def connect(self):
        print("[DEBUG] connect() called", file=sys.stderr)
        self.status_var.set("Connecting...")
        self.connect_btn.state(['disabled'])
        
        # Start WebSocket connection in a separate thread
        self.ws_thread = threading.Thread(target=self._ws_thread, daemon=True)
        self.ws_thread.start()
        
    def _ws_thread(self):
        print("[DEBUG] _ws_thread() started", file=sys.stderr)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._async_connect())
            self.loop.run_until_complete(self._async_message_handler())
        except Exception as e:
            print(f"[DEBUG] WebSocket thread error: {e}", file=sys.stderr)
            self.root.after(0, self.disconnect)
        finally:
            try:
                self.loop.close()
            except Exception as e:
                print(f"[DEBUG] Error closing WebSocket loop: {e}", file=sys.stderr)
                
    def _connect_websocket(self):
        # This method is no longer needed as connection is handled in _ws_thread
        pass
        
    def disconnect(self):
        print("[DEBUG] disconnect() called", file=sys.stderr)
        if self.ws:
            try:
                if self.loop and self.loop.is_running():
                    self.loop.call_soon_threadsafe(self._async_disconnect)
            except Exception as e:
                print(f"[DEBUG] Error during disconnect: {e}", file=sys.stderr)
        self.connected = False
        self.status_var.set("Disconnected")
        self.connect_btn.configure(text="Connect")
        self.talk_btn.state(['disabled'])
        self.connect_btn.state(['!disabled'])
        
    async def _async_connect(self):
        """Establish WebSocket connection"""
        print("[DEBUG] _async_connect() called", file=sys.stderr)
        try:
            self.ws = await websockets.connect(self.url_var.get())
            self.connected = True
            self.conversation_id = str(uuid.uuid4())
            
            # Send session start message
            session_start = {
                "type": "session.start",
                "conversationId": self.conversation_id
            }
            await self.ws.send(json.dumps(session_start))
            
            # Update UI
            self.root.after(0, lambda: self.status_var.set("Connected"))
            self.root.after(0, lambda: self.connect_btn.configure(text="Disconnect"))
            self.root.after(0, lambda: self.talk_btn.state(['!disabled']))
            self.root.after(0, lambda: self.connect_btn.state(['!disabled']))
            
            print("[DEBUG] WebSocket connection established", file=sys.stderr)
        except Exception as e:
            print(f"[DEBUG] WebSocket connection error: {e}", file=sys.stderr)
            raise

    async def _async_message_handler(self):
        """Handle incoming WebSocket messages"""
        print("[DEBUG] _async_message_handler() started", file=sys.stderr)
        try:
            if not self.ws:
                print("[DEBUG] WebSocket is None, cannot handle messages", file=sys.stderr)
                return
                
            while self.connected:
                message = await self.ws.recv()
                try:
                    data = json.loads(message)
                    if data["type"] == "audio":
                        # Handle incoming audio data
                        audio_data = base64.b64decode(data["data"])
                        # Add to queue for playback
                        self.audio_queue.put(audio_data)
                    elif data["type"] == "error":
                        print(f"[DEBUG] Server error: {data.get('message', 'Unknown error')}", file=sys.stderr)
                except json.JSONDecodeError:
                    print("[DEBUG] Received non-JSON message", file=sys.stderr)
                except Exception as e:
                    print(f"[DEBUG] Error processing message: {e}", file=sys.stderr)
        except websockets.exceptions.ConnectionClosed:
            print("[DEBUG] WebSocket connection closed", file=sys.stderr)
        except Exception as e:
            print(f"[DEBUG] Message handler error: {e}", file=sys.stderr)
        finally:
            self.root.after(0, self.disconnect)

    async def _async_disconnect(self):
        print("[DEBUG] _async_disconnect() called", file=sys.stderr)
        if self.conversation_id and self.ws:
            try:
                session_end = {
                    "type": "session.end",
                    "conversationId": self.conversation_id,
                    "reasonCode": "normal",
                    "reason": "User disconnected"
                }
                await self.ws.send(json.dumps(session_end))
            except Exception as e:
                print(f"[DEBUG] Error sending session end: {e}", file=sys.stderr)
            try:
                await self.ws.close()
            except Exception as e:
                print(f"[DEBUG] Error closing websocket: {e}", file=sys.stderr)
            
    def _select_input_device(self):
        """Select the first available input device"""
        if not self.p:
            return None
        try:
            for i in range(self.p.get_device_count()):
                device_info = self.p.get_device_info_by_index(i)
                max_channels = device_info.get('maxInputChannels', 0)
                if isinstance(max_channels, (int, float)) and max_channels > 0:
                    return i
            return None
        except Exception as e:
            print(f"[DEBUG] Error selecting input device: {e}", file=sys.stderr)
            return None

    def _select_output_device(self):
        """Select the first available output device"""
        if not self.p:
            return None
        try:
            for i in range(self.p.get_device_count()):
                device_info = self.p.get_device_info_by_index(i)
                max_channels = device_info.get('maxOutputChannels', 0)
                if isinstance(max_channels, (int, float)) and max_channels > 0:
                    return i
            return None
        except Exception as e:
            print(f"[DEBUG] Error selecting output device: {e}", file=sys.stderr)
            return None

    def start_recording(self, event=None):
        """Start recording audio when talk button is pressed"""
        if not self.recording and self.connected and self.p and self.input_device is not None:
            print("[DEBUG] Starting recording", file=sys.stderr)
            try:
                self.recording = True
                self.talk_btn.configure(text="Recording...")
                self.stream = self.p.open(
                    format=self.FORMAT,
                    channels=self.CHANNELS,
                    rate=self.RATE,
                    input=True,
                    input_device_index=self.input_device,
                    frames_per_buffer=self.CHUNK
                )
                # Start recording thread
                self.record_thread = threading.Thread(target=self._record_audio, daemon=True)
                self.record_thread.start()
            except Exception as e:
                print(f"[DEBUG] Error starting recording: {e}", file=sys.stderr)
                self.recording = False
                self.talk_btn.configure(text="Hold to Talk")
                self.status_var.set(f"Recording error: {str(e)}")

    def stop_recording(self, event=None):
        """Stop recording audio when talk button is released"""
        if self.recording:
            print("[DEBUG] Stopping recording", file=sys.stderr)
            self.recording = False
            self.talk_btn.configure(text="Hold to Talk")
            if hasattr(self, 'stream'):
                self.stream.stop_stream()
                self.stream.close()

    def _record_audio(self):
        """Record audio in a separate thread"""
        print("[DEBUG] Recording thread started", file=sys.stderr)
        try:
            while self.recording:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                # Convert to numpy array for processing
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Apply noise reduction
                audio_data = self._reduce_noise(audio_data)
                
                # Convert back to bytes and add to queue
                processed_data = audio_data.tobytes()
                self.audio_queue.put(processed_data)
                
                # Send audio data through WebSocket if connected
                if self.connected and self.ws and self.loop:
                    try:
                        audio_message = {
                            "type": "audio",
                            "conversationId": self.conversation_id,
                            "data": base64.b64encode(processed_data).decode('utf-8')
                        }
                        asyncio.run_coroutine_threadsafe(
                            self.ws.send(json.dumps(audio_message)),
                            self.loop
                        )
                    except Exception as e:
                        print(f"[DEBUG] Error sending audio: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[DEBUG] Recording error: {e}", file=sys.stderr)
        finally:
            self.recording = False

    def _reduce_noise(self, audio_data):
        """Apply noise reduction to audio data"""
        try:
            # Apply a simple noise gate
            threshold = 500  # Adjust this value based on your needs
            audio_data[abs(audio_data) < threshold] = 0
            
            # Apply a simple low-pass filter
            nyquist = self.RATE / 2
            cutoff = 3000  # 3kHz cutoff
            b, a = signal.butter(4, cutoff/nyquist, btype='low')
            audio_data = signal.filtfilt(b, a, audio_data)
            
            return audio_data
        except Exception as e:
            print(f"[DEBUG] Noise reduction error: {e}", file=sys.stderr)
            return audio_data

    def _audio_thread(self):
        """Background thread for handling audio processing"""
        print("[DEBUG] Audio thread started", file=sys.stderr)
        if not self.p or self.output_device is None:
            print("[DEBUG] No audio output device available", file=sys.stderr)
            return

        try:
            # Create output stream for playback
            self.output_stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                output=True,
                output_device_index=self.output_device,
                frames_per_buffer=self.CHUNK
            )
            
            while True:
                try:
                    # Process audio from queue
                    if not self.audio_queue.empty():
                        audio_data = self.audio_queue.get()
                        # Play the audio
                        self.output_stream.write(audio_data)
                    time.sleep(0.01)  # Reduced sleep time for better responsiveness
                except Exception as e:
                    print(f"[DEBUG] Error in audio thread: {e}", file=sys.stderr)
                    time.sleep(1)  # Wait a bit before retrying
        except Exception as e:
            print(f"[DEBUG] Error creating output stream: {e}", file=sys.stderr)

    def __del__(self):
        """Cleanup when the object is destroyed"""
        try:
            if hasattr(self, 'output_stream'):
                self.output_stream.stop_stream()
                self.output_stream.close()
            if hasattr(self, 'p') and self.p:
                self.p.terminate()
        except Exception as e:
            print(f"[DEBUG] Cleanup error: {e}", file=sys.stderr)

if __name__ == "__main__":
    root = tk.Tk()
    app = AudioInterface(root)
    root.mainloop()
