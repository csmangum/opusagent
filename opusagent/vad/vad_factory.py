from .silero_vad import SileroVAD

class VADFactory:
    @staticmethod
    def create_vad(config):
        backend = config.get('backend', 'silero')
        if backend == 'silero':
            vad = SileroVAD()
            vad.initialize(config)
            return vad
        else:
            raise ValueError(f'Unsupported VAD backend: {backend}') 