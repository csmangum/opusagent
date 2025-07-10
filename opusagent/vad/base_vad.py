from abc import ABC, abstractmethod

class BaseVAD(ABC):
    """Abstract base class for Voice Activity Detection (VAD) backends."""

    @abstractmethod
    def initialize(self, config):
        """Initialize the VAD system with the given configuration."""
        pass

    @abstractmethod
    def process_audio(self, audio_data: bytes) -> dict:
        """Process audio data and return VAD result (e.g., speech probability, is_speech)."""
        pass

    @abstractmethod
    def reset(self):
        """Reset VAD state."""
        pass

    @abstractmethod
    def cleanup(self):
        """Cleanup VAD resources."""
        pass 