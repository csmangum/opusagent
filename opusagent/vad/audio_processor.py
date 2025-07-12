import numpy as np
import struct

def to_float32_mono(audio_data, sample_width, channels):
    """
    Convert raw audio bytes to float32 mono numpy array (-1 to 1).
    Supports PCM16, PCM24, and float32 formats.
    """
    # 16-bit PCM mono
    if sample_width == 2 and channels == 1:
        arr = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        return arr
    
    # 24-bit PCM mono
    elif sample_width == 3 and channels == 1:
        # Unpack 24-bit little-endian signed integers
        samples = []
        for i in range(0, len(audio_data), 3):
            if i + 2 < len(audio_data):
                # Extract 24-bit value and sign-extend to 32-bit
                sample_bytes = audio_data[i:i+3]
                # Convert to signed 32-bit integer
                # Check if the highest bit is set (negative number)
                if sample_bytes[2] & 0x80:
                    # Negative number - sign extend with 0xFF
                    sample = struct.unpack('<i', sample_bytes + b'\xff')[0]
                else:
                    # Positive number - sign extend with 0x00
                    sample = struct.unpack('<i', sample_bytes + b'\x00')[0]
                samples.append(sample)
        
        if samples:
            arr = np.array(samples, dtype=np.float32) / 8388608.0  # 2^23 for 24-bit
            return arr
        else:
            raise ValueError("Invalid PCM24 data: no samples found")
    
    # 32-bit float mono
    elif sample_width == 4 and channels == 1:
        # Check if this is actually float32 data by trying to interpret as float32
        # If it's int32 data, this will likely result in NaN values or very small values
        arr = np.frombuffer(audio_data, dtype=np.float32)
        
        # If the data contains NaN values, it's likely int32 data and we should raise an error
        if np.any(np.isnan(arr)):
            # This looks like int32 data, not float32 audio data
            raise NotImplementedError('Audio conversion for this format is not implemented.')
        
        return arr
    
    # Add more conversions as needed
    raise NotImplementedError(f'Audio conversion for sample_width={sample_width}, channels={channels} is not implemented.') 