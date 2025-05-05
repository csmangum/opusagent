import pyaudio
import wave
import sys
import os
from datetime import datetime

def record_audio(filename=None, seconds=5, sample_rate=44100, channels=1, format_type=pyaudio.paInt16, chunk=1024):
    """
    Record audio from the microphone and save it to a WAV file.
    
    Args:
        filename (str, optional): Path to save the WAV file. If None, a timestamped filename will be used.
        seconds (int, optional): Duration of recording in seconds. Defaults to 5.
        sample_rate (int, optional): Sample rate. Defaults to 44100 Hz.
        channels (int, optional): Number of audio channels. Defaults to 1 (mono).
        format_type (int, optional): Audio format type. Defaults to pyaudio.paInt16.
        chunk (int, optional): Frames per buffer. Defaults to 1024.
        
    Returns:
        str: Path to the saved WAV file
    """
    # Generate filename if not provided
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.wav"
    
    # Initialize PyAudio
    p = pyaudio.PyAudio()
    
    try:
        print(f"Recording for {seconds} seconds...")
        
        # Open stream
        stream = p.open(
            format=format_type,
            channels=channels,
            rate=sample_rate,
            input=True,
            frames_per_buffer=chunk
        )
        
        # Record audio
        frames = []
        for i in range(0, int(sample_rate / chunk * seconds)):
            data = stream.read(chunk)
            frames.append(data)
            
            # Show recording progress
            progress = (i + 1) / int(sample_rate / chunk * seconds) * 100
            sys.stdout.write(f"\rProgress: {progress:.1f}%")
            sys.stdout.flush()
            
        print("\nFinished recording.")
        
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        
        # Save as WAV file
        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(format_type))
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        print(f"Audio saved to: {os.path.abspath(filename)}")
        return filename
        
    finally:
        # Terminate PyAudio
        p.terminate()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Record audio from microphone and save as WAV file")
    parser.add_argument("-o", "--output", type=str, help="Output WAV filename")
    parser.add_argument("-d", "--duration", type=int, default=3, help="Recording duration in seconds (default: 5)")
    parser.add_argument("-r", "--rate", type=int, default=44100, help="Sample rate (default: 44100)")
    parser.add_argument("-c", "--channels", type=int, default=1, help="Number of channels (default: 1)")
    
    args = parser.parse_args()
    
    try:
        record_audio(
            filename=args.output,
            seconds=args.duration,
            sample_rate=args.rate,
            channels=args.channels
        )
    except KeyboardInterrupt:
        print("\nRecording stopped by user")
    except Exception as e:
        print(f"\nError: {e}")
        print("\nIf you get an error about PyAudio, you may need to install it first:")
        print("pip install pyaudio")
        print("\nOn Windows, if you have issues installing PyAudio, try:")
        print("pip install pipwin")
        print("pipwin install pyaudio") 