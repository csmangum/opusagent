import torch
from .base_vad import BaseVAD
import numpy as np

class SileroVAD(BaseVAD):
    def __init__(self):
        self.model = None
        self.sample_rate = 16000
        self.threshold = 0.5
        self.device = 'cpu'
        self.chunk_size = 512  # Default chunk size for 16kHz

    def initialize(self, config):
        self.sample_rate = config.get('sample_rate', 16000)
        self.threshold = config.get('threshold', 0.5)
        self.device = config.get('device', 'cpu')
        self.chunk_size = config.get('chunk_size', 512)
        
        # Validate chunk size for sample rate
        if self.sample_rate == 16000 and self.chunk_size != 512:
            self.chunk_size = 512
        elif self.sample_rate == 8000 and self.chunk_size != 256:
            self.chunk_size = 256
            
        try:
            from silero_vad import load_silero_vad
            # load_silero_vad does not accept a device argument; model will use default device
            self.model = load_silero_vad()
        except ImportError:
            raise RuntimeError('silero-vad not installed. Please install with: pip install silero-vad')

    def process_audio(self, audio_data: np.ndarray) -> dict:
        if self.model is None:
            raise RuntimeError('Silero VAD model not initialized.')
        
        # audio_data is a numpy float32 array, -1 to 1, mono
        # Handle variable-length input by splitting into chunks
        if len(audio_data) != self.chunk_size:
            # Split audio into chunks of the correct size
            chunks = []
            for i in range(0, len(audio_data), self.chunk_size):
                chunk = audio_data[i:i + self.chunk_size]
                if len(chunk) == self.chunk_size:
                    chunks.append(chunk)
            
            if not chunks:
                # Audio is too short, pad with zeros
                padded_audio = np.zeros(self.chunk_size, dtype=np.float32)
                padded_audio[:len(audio_data)] = audio_data
                chunks = [padded_audio]
            
            # Process each chunk and aggregate results
            speech_probs = []
            for chunk in chunks:
                audio_tensor = torch.from_numpy(chunk).float()
                speech_prob = self.model(audio_tensor, self.sample_rate).item()
                speech_probs.append(speech_prob)
            
            # Use the maximum probability as the overall result
            max_speech_prob = max(speech_probs) if speech_probs else 0.0
            is_speech = max_speech_prob > self.threshold
            
            return {
                'speech_prob': max_speech_prob,
                'is_speech': is_speech
            }
        else:
            # Audio is already the correct size
            audio_tensor = torch.from_numpy(audio_data).float()
            speech_prob = self.model(audio_tensor, self.sample_rate).item()
            is_speech = speech_prob > self.threshold
            return {
                'speech_prob': speech_prob,
                'is_speech': is_speech
            }

    def reset(self):
        pass  # No state to reset for Silero VAD

    def cleanup(self):
        self.model = None 