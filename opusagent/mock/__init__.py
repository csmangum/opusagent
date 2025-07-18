"""
Mock modules for testing and development.

This package provides mock implementations of various components for testing
and development purposes.
"""

# Import the new modular audiocodes client
try:
    from .audiocodes import MockAudioCodesClient
    AUDIOCODES_AVAILABLE = True
except ImportError:
    AUDIOCODES_AVAILABLE = False
    MockAudioCodesClient = None

# Import existing mock components
try:
    from .mock_audiocodes_client import MockAudioCodesClient as LegacyMockAudioCodesClient
    LEGACY_AUDIOCODES_AVAILABLE = True
except ImportError:
    LEGACY_AUDIOCODES_AVAILABLE = False
    LegacyMockAudioCodesClient = None

try:
    from .mock_twilio_client import MockTwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    MockTwilioClient = None

try:
    from .local_vad_client import LocalVADClient
    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False
    LocalVADClient = None

# Export available components
__all__ = []

if AUDIOCODES_AVAILABLE:
    __all__.append("MockAudioCodesClient")

if LEGACY_AUDIOCODES_AVAILABLE:
    __all__.append("LegacyMockAudioCodesClient")

if TWILIO_AVAILABLE:
    __all__.append("MockTwilioClient")

if VAD_AVAILABLE:
    __all__.append("LocalVADClient")

# Version info
__version__ = "1.0.0"
