# Voice Activity Detection (VAD) Module

## Overview
This module provides a pluggable interface for local Voice Activity Detection (VAD) backends, with a default implementation using Silero VAD. It is designed for real-time speech detection in telephony and conversational AI systems.

---

## API Documentation

### Abstract Interface: `BaseVAD`
```
class BaseVAD(ABC):
    def initialize(self, config):
        """Initialize the VAD system with the given configuration."""
        pass
    def process_audio(self, audio_data: np.ndarray) -> dict:
        """Process audio data and return VAD result (e.g., speech probability, is_speech)."""
        pass
    def reset(self):
        """Reset VAD state."""
        pass
    def cleanup(self):
        """Cleanup VAD resources."""
        pass
```

### SileroVAD Implementation
- `initialize(config)`: Loads the Silero VAD model and sets parameters.
- `process_audio(audio_data: np.ndarray) -> dict`: Returns `{ 'speech_prob': float, 'is_speech': bool }`.
- `reset()`, `cleanup()`: No-op for Silero.

### VAD Factory
- `VADFactory.create_vad(config)`: Instantiates the selected backend (currently only 'silero').

---

## Configuration Guide

Configuration is loaded from environment variables (with defaults):
- `VAD_BACKEND` (default: `silero`)
- `VAD_SAMPLE_RATE` (default: `16000`)
- `VAD_CONFIDENCE_THRESHOLD` (default: `0.5`)
- `VAD_DEVICE` (default: `cpu`)
- `VAD_CHUNK_SIZE` (default: `512`)

Example:
```
export VAD_BACKEND=silero
export VAD_CONFIDENCE_THRESHOLD=0.3
```

---

## Integration Steps
1. Import and load config:
   ```python
   from opusagent.vad.vad_config import load_vad_config
   from opusagent.vad.vad_factory import VADFactory
   config = load_vad_config()
   vad = VADFactory.create_vad(config)
   ```
2. For each audio chunk, convert to float32 mono and call `vad.process_audio(...)`.
3. Track speech state and emit events on transitions.

---

## Troubleshooting & Best Practices
- **Model not found**: Ensure `silero-vad` is installed (`pip install silero-vad`).
- **Audio format errors**: Use the provided `to_float32_mono` utility for conversion.
- **Performance**: For high-throughput, batch or stream audio efficiently.
- **Sensitivity**: Tune `VAD_CONFIDENCE_THRESHOLD` for your environment.
- **Testing**: Use the test script in `scripts/test_silero_vad.py` for local validation.

---

## Extending
To add a new backend, implement `BaseVAD` and register it in `vad_factory.py`. 