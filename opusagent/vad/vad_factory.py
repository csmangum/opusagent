from .silero_vad import SileroVAD

class VADFactory:
    """Factory class for creating VAD instances."""
    
    def __init__(self):
        """VADFactory should not be instantiated."""
        raise TypeError("VADFactory cannot be instantiated. Use static methods instead.")
    
    @staticmethod
    def create_vad(config=None):
        """
        Create a VAD instance based on the configuration.
        
        Args:
            config (dict, optional): Configuration dictionary. If None, uses defaults.
            
        Returns:
            BaseVAD: Configured VAD instance
            
        Raises:
            ValueError: If backend is not supported
        """
        # Handle None config
        if config is None:
            config = {}
            
        backend = config.get('backend', 'silero')
        if backend == 'silero':
            vad = SileroVAD()
            vad.initialize(config)
            return vad
        else:
            raise ValueError(f'Unsupported VAD backend: {backend}') 