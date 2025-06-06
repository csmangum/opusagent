#!/usr/bin/env python3
"""
Test script to verify TUI setup and dependencies.
Run this before using the enhanced TUI to ensure everything is working.
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all required imports work."""
    print("🔍 Testing imports...")
    
    try:
        import textual
        print(f"✅ Textual: {textual.__version__}")
    except ImportError as e:
        print(f"❌ Textual import failed: {e}")
        return False
    
    try:
        import sounddevice as sd
        print(f"✅ SoundDevice: {sd.__version__}")
    except ImportError as e:
        print(f"❌ SoundDevice import failed: {e}")
        return False
    
    try:
        import rich
        print(f"✅ Rich: {rich.__version__}")
    except ImportError as e:
        print(f"❌ Rich import failed: {e}")
        return False
    
    try:
        import scipy
        print(f"✅ SciPy: {scipy.__version__}")
    except ImportError as e:
        print(f"❌ SciPy import failed: {e}")
        return False
    
    try:
        import librosa
        print(f"✅ Librosa: {librosa.__version__}")
    except ImportError as e:
        print(f"⚠️  Librosa import failed (optional): {e}")
    
    try:
        import numpy as np
        print(f"✅ NumPy: {np.__version__}")
    except ImportError as e:
        print(f"❌ NumPy import failed: {e}")
        return False
    
    return True

def test_audio_devices():
    """Test audio device availability."""
    print("\n🔊 Testing audio devices...")
    
    try:
        import sounddevice as sd
        
        devices = sd.query_devices()
        print(f"✅ Found {len(devices)} audio devices")
        
        # Check for input devices (microphones)
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        print(f"🎤 Input devices: {len(input_devices)}")
        
        # Check for output devices (speakers)
        output_devices = [d for d in devices if d['max_output_channels'] > 0]
        print(f"🔊 Output devices: {len(output_devices)}")
        
        if len(output_devices) == 0:
            print("⚠️  Warning: No output devices found - you won't hear bot responses!")
            return False
        
        # Test default devices
        try:
            default_input = sd.query_devices(kind='input')
            default_output = sd.query_devices(kind='output')
            print(f"🎤 Default input: {default_input['name']}")
            print(f"🔊 Default output: {default_output['name']}")
        except Exception as e:
            print(f"⚠️  Error getting default devices: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Audio device test failed: {e}")
        return False

def test_audio_files():
    """Test audio file availability."""
    print("\n🎵 Testing audio files...")
    
    audio_dirs = ["static", "test_audio", "audio_samples"]
    audio_extensions = {".wav", ".mp3", ".flac", ".ogg"}
    
    total_files = 0
    for audio_dir in audio_dirs:
        dir_path = Path(audio_dir)
        if dir_path.exists():
            audio_files = [f for f in dir_path.iterdir() 
                          if f.suffix.lower() in audio_extensions]
            if audio_files:
                print(f"📁 {audio_dir}/: {len(audio_files)} audio files")
                for f in audio_files[:3]:  # Show first 3
                    print(f"   📄 {f.name}")
                if len(audio_files) > 3:
                    print(f"   ... and {len(audio_files) - 3} more")
                total_files += len(audio_files)
            else:
                print(f"📁 {audio_dir}/: No audio files")
        else:
            print(f"📁 {audio_dir}/: Directory not found")
    
    if total_files == 0:
        print("⚠️  Warning: No audio files found. Soundboard will use text fallback.")
        return False
    
    print(f"✅ Total audio files available: {total_files}")
    return True

def test_tui_components():
    """Test TUI component imports."""
    print("\n🎛️  Testing TUI components...")
    
    try:
        sys.path.append(str(Path(__file__).parent))
        
        from tui.components.soundboard_panel import SoundboardPanel
        print("✅ SoundboardPanel import successful")
        
        from tui.components.connection_panel import ConnectionPanel
        print("✅ ConnectionPanel import successful")
        
        from tui.components.audio_panel import AudioPanel
        print("✅ AudioPanel import successful")
        
        from tui.main import InteractiveTUIValidator
        print("✅ Main TUI class import successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ TUI component import failed: {e}")
        return False

def test_websocket_dependencies():
    """Test WebSocket related dependencies."""
    print("\n🌐 Testing WebSocket dependencies...")
    
    try:
        import websockets
        print(f"✅ WebSockets: {websockets.__version__}")
    except ImportError as e:
        print(f"❌ WebSockets import failed: {e}")
        return False
    
    try:
        import asyncio
        print("✅ AsyncIO available")
    except ImportError as e:
        print(f"❌ AsyncIO import failed: {e}")
        return False
    
    return True

def create_test_audio_file():
    """Create a simple test audio file if none exist."""
    print("\n🎵 Creating test audio file...")
    
    try:
        import numpy as np
        import soundfile as sf
        
        # Create static directory if it doesn't exist
        static_dir = Path("static")
        static_dir.mkdir(exist_ok=True)
        
        # Generate a simple test tone (440Hz sine wave for 2 seconds)
        sample_rate = 16000
        duration = 2.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = 0.3 * np.sin(2 * np.pi * frequency * t)
        
        # Save as WAV file
        test_file = static_dir / "test_tone.wav"
        sf.write(test_file, audio_data, sample_rate)
        
        print(f"✅ Created test audio file: {test_file}")
        return True
        
    except Exception as e:
        print(f"⚠️  Could not create test audio file: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 TUI Setup Test Script")
    print("=" * 50)
    
    tests = [
        ("Dependencies", test_imports),
        ("Audio Devices", test_audio_devices),
        ("Audio Files", test_audio_files),
        ("TUI Components", test_tui_components),
        ("WebSocket Dependencies", test_websocket_dependencies),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {test_name}")
        if not passed:
            all_passed = False
    
    if not all_passed:
        print("\n⚠️  Some tests failed. Trying to create test audio file...")
        create_test_audio_file()
    
    print("\n🎯 Next Steps:")
    if all_passed:
        print("✅ All tests passed! You're ready to use the TUI.")
        print("🚀 Launch with: python -m tui.main")
    else:
        print("⚠️  Some issues found. Check the following:")
        print("   1. Install missing dependencies: pip install -r requirements.txt")
        print("   2. Check audio device settings")
        print("   3. Add audio files to static/ folder")
        print("   4. Try running the TUI anyway - it may still work!")
    
    print("\n📖 See TUI_SETUP_GUIDE.md for detailed instructions.")

if __name__ == "__main__":
    main() 