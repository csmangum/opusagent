# VAD Integration Validation

This directory contains comprehensive validation tools for the Voice Activity Detection (VAD) integration in the LocalRealtimeClient system.

## 📋 Overview

The VAD validation tools ensure that all aspects of the VAD integration work correctly and meet the requirements outlined in the [VAD Integration Summary](VAD_INTEGRATION_SUMMARY.md).

## 🚀 Quick Start

### Simple Validation (Recommended)

```bash
# Run the complete validation suite with a nice interface
python scripts/run_vad_validation.py
```

### Advanced Validation

```bash
# Run all validation tests with detailed output
python scripts/validate_vad_integration.py --all --verbose

# Run specific category of tests
python scripts/validate_vad_integration.py --category init --verbose

# Run with performance benchmarks and save results
python scripts/validate_vad_integration.py --performance --output vad_results.json

# Quick validation (essential tests only)
python scripts/validate_vad_integration.py --quick
```

## 📊 Validation Categories

### 1. **Initialization Tests** (`--category init`)
- Basic VAD initialization with default configuration
- VAD initialization with custom configuration
- VAD auto-enabled by session configuration
- VAD explicitly disabled
- VAD initialization failure fallback
- VAD initialization with invalid configuration

### 2. **Audio Processing Tests** (`--category audio`)
- PCM16 audio format conversion and processing
- PCM24 audio format conversion and processing
- Multi-format audio support validation
- Real-time audio chunk processing
- Audio format detection and automatic conversion
- Invalid audio format handling

### 3. **Speech Detection Tests** (`--category speech`)
- Speech detection with clear speech audio
- Silence detection with background noise
- Speech start/stop event generation
- Hysteresis implementation (2 speech, 3 silence)
- Confidence smoothing (5-value history)
- Speech detection with varying confidence levels

### 4. **Runtime Control Tests** (`--category control`)
- Runtime VAD enabling
- Runtime VAD disabling
- VAD configuration updates
- VAD state inspection
- Multiple enable/disable cycles
- Configuration immutability validation

### 5. **Performance Tests** (`--category performance`)
- Audio processing latency measurement
- Memory usage during VAD processing
- CPU usage under continuous processing
- Processing throughput measurement
- Resource usage with multiple audio formats

### 6. **Error Handling Tests** (`--category error`)
- VAD processing exception handling
- Audio conversion error handling
- VAD initialization failure recovery
- Resource cleanup on errors
- Fallback to simple speech detection

## 🛠️ Command Line Options

```bash
python scripts/validate_vad_integration.py [OPTIONS]
```

### Options:
- `--category CATEGORY` - Run specific test category (init, audio, speech, control, performance, error)
- `--scenario SCENARIO` - Run specific test scenario (e.g., VAD_INIT_001)
- `--verbose` - Enable verbose logging
- `--output FILE` - Save results to JSON file
- `--generate-audio` - Generate test audio files
- `--performance` - Include performance benchmarks
- `--integration` - Include integration tests
- `--quick` - Run quick validation (subset of tests)
- `--all` - Run all validation tests (default)

## 📈 Usage Examples

### Basic Usage

```bash
# Run all tests
python scripts/validate_vad_integration.py --all

# Run with verbose output
python scripts/validate_vad_integration.py --verbose

# Save results to file
python scripts/validate_vad_integration.py --output validation_results.json
```

### Category-Specific Testing

```bash
# Test VAD initialization
python scripts/validate_vad_integration.py --category init --verbose

# Test audio processing
python scripts/validate_vad_integration.py --category audio --verbose

# Test speech detection
python scripts/validate_vad_integration.py --category speech --verbose

# Test runtime control
python scripts/validate_vad_integration.py --category control --verbose
```

### Performance Testing

```bash
# Run performance benchmarks
python scripts/validate_vad_integration.py --performance --verbose

# Performance with results saved
python scripts/validate_vad_integration.py --performance --output perf_results.json
```

### Development and Debugging

```bash
# Generate test audio files
python scripts/validate_vad_integration.py --generate-audio

# Quick validation during development
python scripts/validate_vad_integration.py --quick --verbose

# Test specific scenario
python scripts/validate_vad_integration.py --scenario VAD_INIT_001 --verbose
```

## 📊 Understanding Results

### Console Output

The validation provides detailed console output including:
- Test progress with emoji indicators (✅ ❌ 💥 ⏭️)
- Test execution times
- Error details and debugging information
- Summary statistics

### JSON Reports

When using `--output`, a comprehensive JSON report is generated containing:
- Test results and statistics
- Performance metrics
- Error details and warnings
- Complete test execution history

### Success Criteria

- **Functional**: All VAD features work as designed
- **Performance**: Audio processing latency < 50ms
- **Integration**: No breaking changes to existing functionality
- **Error Handling**: Graceful degradation on failures

## 🔧 Prerequisites

### Required Dependencies

```bash
# Core dependencies (already in requirements.txt)
pip install torch torchaudio
pip install silero-vad
pip install numpy scipy

# Optional for audio generation
pip install soundfile
```

### Environment Setup

```bash
# Ensure you're in the project root
cd /path/to/fastagent

# Install dependencies
pip install -r requirements.txt

# Run validation
python scripts/run_vad_validation.py
```

## 📋 Test Scenarios

### VAD Initialization Tests
- **VAD_INIT_001**: Basic VAD initialization with default configuration
- **VAD_INIT_002**: VAD initialization with custom configuration
- **VAD_INIT_003**: VAD auto-enabled by session configuration
- **VAD_INIT_004**: VAD explicitly disabled
- **VAD_INIT_005**: VAD initialization failure fallback
- **VAD_INIT_006**: VAD initialization with invalid configuration

### Audio Processing Tests
- **VAD_AUDIO_001**: PCM16 audio format conversion and processing
- **VAD_AUDIO_002**: PCM24 audio format conversion and processing
- **VAD_AUDIO_003**: Multi-format audio support validation
- **VAD_AUDIO_004**: Real-time audio chunk processing
- **VAD_AUDIO_005**: Audio format detection and automatic conversion
- **VAD_AUDIO_006**: Invalid audio format handling
- **VAD_AUDIO_007**: Audio processing with various sample rates

### Speech Detection Tests
- **VAD_SPEECH_001**: Speech detection with clear speech audio
- **VAD_SPEECH_002**: Silence detection with background noise
- **VAD_SPEECH_003**: Speech start/stop event generation
- **VAD_SPEECH_004**: Hysteresis implementation (2 speech, 3 silence)
- **VAD_SPEECH_005**: Confidence smoothing (5-value history)
- **VAD_SPEECH_006**: Speech detection with varying confidence levels
- **VAD_SPEECH_007**: Continuous speech detection
- **VAD_SPEECH_008**: Intermittent speech detection

### Runtime Control Tests
- **VAD_CONTROL_001**: Runtime VAD enabling
- **VAD_CONTROL_002**: Runtime VAD disabling
- **VAD_CONTROL_003**: VAD configuration updates
- **VAD_CONTROL_004**: VAD state inspection
- **VAD_CONTROL_005**: Multiple enable/disable cycles
- **VAD_CONTROL_006**: Configuration immutability validation
- **VAD_CONTROL_007**: Event handler synchronization with VAD state

### Performance Tests
- **VAD_PERF_001**: Audio processing latency measurement
- **VAD_PERF_002**: Memory usage during VAD processing
- **VAD_PERF_003**: CPU usage under continuous processing
- **VAD_PERF_004**: Processing throughput measurement
- **VAD_PERF_005**: Resource usage with multiple audio formats
- **VAD_PERF_006**: Performance degradation under load
- **VAD_PERF_007**: Memory leak detection

### Error Handling Tests
- **VAD_ERROR_001**: VAD processing exception handling
- **VAD_ERROR_002**: Audio conversion error handling
- **VAD_ERROR_003**: VAD initialization failure recovery
- **VAD_ERROR_004**: Resource cleanup on errors
- **VAD_ERROR_005**: Fallback to simple speech detection
- **VAD_ERROR_006**: Graceful degradation logging
- **VAD_ERROR_007**: Error recovery after temporary failures

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure you're in the project root
   cd /path/to/fastagent
   python scripts/run_vad_validation.py
   ```

2. **Missing Dependencies**
   ```bash
   # Install VAD dependencies
   pip install torch torchaudio silero-vad
   ```

3. **Audio Generation Issues**
   ```bash
   # Install optional audio libraries
   pip install soundfile numpy scipy
   ```

4. **VAD Initialization Failures**
   - Check that VAD backend dependencies are installed
   - Verify system resources (CPU/memory) are available
   - Check for conflicting PyTorch versions

### Debug Mode

```bash
# Run with maximum verbosity
python scripts/validate_vad_integration.py --verbose --all

# Check individual components
python -c "
from opusagent.mock.realtime.client import LocalRealtimeClient
client = LocalRealtimeClient(enable_vad=True)
print('VAD enabled:', client.is_vad_enabled())
print('VAD config:', client.get_vad_config())
"
```

## 📚 Related Documentation

- [VAD Integration Summary](VAD_INTEGRATION_SUMMARY.md) - Complete implementation details
- [VAD Validation Plan](vad_validation_plan.md) - Detailed validation strategy
- [LocalRealtimeClient Documentation](opusagent/mock/realtime/client.py) - Client API reference
- [VAD Configuration Guide](docs/vad_configuration.md) - Configuration options

## 🔄 Continuous Integration

### GitHub Actions Example

```yaml
name: VAD Integration Validation

on: [push, pull_request]

jobs:
  validate-vad:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install soundfile numpy scipy
      - name: Run VAD validation
        run: python scripts/run_vad_validation.py
      - name: Upload results
        uses: actions/upload-artifact@v2
        if: always()
        with:
          name: vad-validation-results
          path: vad_results.json
```

## 🤝 Contributing

When adding new features to the VAD integration:

1. **Add corresponding tests** to the validation script
2. **Update test scenarios** in the validation plan
3. **Run the full validation suite** before submitting changes
4. **Include performance benchmarks** for new features
5. **Update documentation** with new test descriptions

### Adding New Tests

```python
def test_new_vad_feature(self) -> None:
    """Test new VAD feature functionality."""
    category = "new_feature"
    
    start_time = time.time()
    try:
        # Test implementation
        client = LocalRealtimeClient(enable_vad=True)
        # ... test logic ...
        
        self.log_test_result(
            "VAD_NEW_001", category, "New VAD feature test",
            "PASSED", "Feature works correctly",
            time.time() - start_time
        )
    except Exception as e:
        self.log_test_result(
            "VAD_NEW_001", category, "New VAD feature test",
            "ERROR", f"Exception: {e}",
            time.time() - start_time
        )
```

## 📞 Support

For issues with VAD validation:

1. Check the troubleshooting section above
2. Review the validation plan for expected behavior
3. Run with `--verbose` flag for detailed debugging
4. Check the generated JSON results for error details
5. Refer to the VAD Integration Summary for implementation details

The VAD validation tools are designed to be comprehensive and help ensure the quality and reliability of the VAD integration in the LocalRealtimeClient system. 