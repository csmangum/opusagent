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
        self.p = pyaudio.PyAudio()
        
        # Create UI
        self.create_widgets()
        
        # Start audio thread
        self.audio_thread = threading.Thread(target=self._audio_thread, daemon=True)
        self.audio_thread.start()
        
        
        print("[DEBUG] AudioInterface initialized", file=sys.stderr)
        
    def create_widgets(self):
        print("[DEBUG] Creating widgets", file=sys.stderr)
        # Connection frame
        conn_frame = ttk.LabelFrame(self.root, text="Connection", padding=10)
        conn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Hardcoded URL, no entry
        self.url_var = tk.StringVar(value="ws://localhost:8000/voice-agent")
        ttk.Label(conn_frame, text="ws://localhost:8000/voice-agent").pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side=tk.RIGHT, padx=5)
        
        # Talk button
        self.talk_btn = ttk.Button(self.root, text="Hold to Talk", state=tk.DISABLED)
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
            
    async def _send_user_stream_start(self):
        print("[DEBUG] _send_user_stream_start() called", file=sys.stderr)
        if self.ws and self.conversation_id:
            msg = {
                "type": "userStream.start",
                "conversationId": self.conversation_id
            }
            await self.ws.send(json.dumps(msg))
            
    async def _send_user_stream_stop(self):
        print("[DEBUG] _send_user_stream_stop() called", file=sys.stderr)
        if self.ws and self.conversation_id:
            msg = {
                "type": "userStream.stop",
                "conversationId": self.conversation_id
            }
            await self.ws.send(json.dumps(msg))
            
    async def _send_audio_chunk(self, audio_chunk):
        print(f"[DEBUG] _send_audio_chunk() called, chunk size: {len(audio_chunk)}", file=sys.stderr)
        if self.ws and self.conversation_id:
            msg = {
                "type": "userStream.chunk",
                "conversationId": self.conversation_id,
                "audioChunk": audio_chunk
            }
            await self.ws.send(json.dumps(msg))
            
    def _message_handler(self):
        print("[DEBUG] _message_handler() called", file=sys.stderr)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_message_handler())
        except Exception as e:
            print(f"[DEBUG] Message handler error: {e}", file=sys.stderr)
            self.root.after(0, self.disconnect)
        finally:
            try:
                loop.close()
            except Exception as e:
                print(f"[DEBUG] Error closing message handler loop: {e}", file=sys.stderr)
            
    async def _async_message_handler(self):
        print("[DEBUG] _async_message_handler() called", file=sys.stderr)
        try:
            while self.connected:
                message = await self.ws.recv()
                print(f"[DEBUG] Received message from server: {message}", file=sys.stderr)
                data = json.loads(message)
                
                if data.get("type") == "playStream.chunk":
                    audio_chunk = data.get("audioChunk")
                    if audio_chunk:
                        print(f"[DEBUG] Queuing audio chunk for playback, size: {len(audio_chunk)}", file=sys.stderr)
                        self.audio_queue.put(audio_chunk)
                        
        except Exception as e:
            print(f"[DEBUG] Message handler error: {e}", file=sys.stderr)
            self.root.after(0, self.disconnect)
            
    def _audio_thread(self):
        print("[DEBUG] _audio_thread() started", file=sys.stderr)
        stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            output=True,
            frames_per_buffer=self.CHUNK
        )
        print("[DEBUG] Audio output stream opened", file=sys.stderr)
        
        while True:
            try:
                # Get audio chunk from queue
                audio_chunk = self.audio_queue.get()
                print(f"[DEBUG] Playing audio chunk of size {len(audio_chunk)}", file=sys.stderr)
                
                # Decode and play
                audio_data = base64.b64decode(audio_chunk)
                stream.write(audio_data)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[DEBUG] Audio playback error: {e}", file=sys.stderr)
                
    def __del__(self):
        print("[DEBUG] __del__ called, terminating PyAudio", file=sys.stderr)
        if hasattr(self, 'p'):
            self.p.terminate()

    async def _async_connect(self):
        print("[DEBUG] _async_connect() called", file=sys.stderr)
        try:
            print(f"[DEBUG] Connecting to ws://localhost:8000/voice-agent", file=sys.stderr)
            self.ws = await websockets.connect(
                "ws://localhost:8000/voice-agent"
            )
            print("[DEBUG] WebSocket connection established", file=sys.stderr)
            self.conversation_id = str(uuid.uuid4())
            print(f"[DEBUG] Generated conversation_id: {self.conversation_id}", file=sys.stderr)
            
            # Send session initiate
            session_initiate = {
                "type": "session.initiate",
                "conversationId": self.conversation_id,
                "expectAudioMessages": True,
                "botName": "TestBot",
                "caller": "+15551234567",
                "supportedMediaFormats": ["raw/lpcm16"]
            }
            print(f"[DEBUG] Sending session.initiate: {session_initiate}", file=sys.stderr)
            await self.ws.send(json.dumps(session_initiate))
            
            # Wait for session.accepted
            response = await self.ws.recv()
            print(f"[DEBUG] Received from server: {response}", file=sys.stderr)
            data = json.loads(response)
            
            if data.get("type") == "session.accepted":
                print("[DEBUG] Session accepted", file=sys.stderr)
                self.connected = True
                self.root.after(0, lambda: self.status_var.set("Connected"))
                self.root.after(0, lambda: self.connect_btn.configure(text="Disconnect"))
                self.root.after(0, lambda: self.talk_btn.state(['!disabled']))
                self.root.after(0, lambda: self.connect_btn.state(['!disabled']))
            else:
                print(f"[DEBUG] Session not accepted: {data}", file=sys.stderr)
                raise Exception("Session not accepted")
                
        except Exception as e:
            print(f"[DEBUG] Exception in _async_connect: {e}", file=sys.stderr)
            self.root.after(0, lambda: self.status_var.set(f"Connection failed: {str(e)}"))
            self.root.after(0, lambda: self.connect_btn.state(['!disabled']))
            raise  # Re-raise the exception to be caught by _ws_thread

if __name__ == "__main__":
    root = tk.Tk()
    app = AudioInterface(root)
    root.mainloop()
