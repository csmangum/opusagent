import os

class VoiceFingerprintConfig:
    def __init__(self):
        self.enabled = os.getenv('VOICE_FINGERPRINTING_ENABLED', 'true').lower() == 'true'
        self.similarity_threshold = float(os.getenv('VOICE_SIMILARITY_THRESHOLD', '0.75'))
        self.enrollment_duration = float(os.getenv('VOICE_ENROLLMENT_DURATION', '5.0'))
        self.storage_backend = os.getenv('VOICE_STORAGE_BACKEND', 'json')
        self.storage_path = os.getenv('VOICE_STORAGE_PATH', 'voiceprints.json')
        self.min_audio_quality = float(os.getenv('VOICE_MIN_AUDIO_QUALITY', '0.6'))
        self.max_voiceprints_per_caller = int(os.getenv('VOICE_MAX_VOICEPRINTS_PER_CALLER', '3')) 