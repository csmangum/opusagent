"""
Integration tests for the transcription module.
"""
import pytest
import numpy as np
import asyncio
import os
from unittest.mock import patch, MagicMock
import tempfile

from opusagent.local.transcription import (
    TranscriptionFactory,
    load_transcription_config,
    TranscriptionConfig,
    TranscriptionResult
)


class TestTranscriptionIntegration:
    """Integration tests for the transcription module."""

    @pytest.mark.asyncio
    async def test_end_to_end_pocketsphinx_workflow(self):
        """Test complete workflow with PocketSphinx backend."""
        # Mock PocketSphinx module
        mock_pocketsphinx = MagicMock()
        mock_decoder = MagicMock()
        mock_config = MagicMock()
        mock_hyp = MagicMock()
        
        mock_pocketsphinx.Decoder.default_config.return_value = mock_config
        mock_pocketsphinx.Decoder.return_value = mock_decoder
        mock_hyp.hypstr = "hello world"
        mock_hyp.prob = 0.9
        mock_decoder.hyp.return_value = mock_hyp
        
        # Set up configuration
        config = TranscriptionConfig(
            backend="pocketsphinx",
            chunk_duration=1.0,
            sample_rate=16000
        )
        
        with patch.dict('sys.modules', {'pocketsphinx': mock_pocketsphinx}):
            # Create transcriber
            transcriber = TranscriptionFactory.create_transcriber(config)
            
            # Initialize
            success = await transcriber.initialize()
            assert success == True
            
            # Start session
            transcriber.start_session()
            
            # Create test audio data
            audio_samples = np.random.randint(-1000, 1000, 16000, dtype=np.int16)  # 1 second
            audio_data = audio_samples.tobytes()
            
            # Process chunk
            result = await transcriber.transcribe_chunk(audio_data)
            assert isinstance(result, TranscriptionResult)
            
            # Finalize
            final_result = await transcriber.finalize()
            assert isinstance(final_result, TranscriptionResult)
            assert final_result.is_final == True
            
            # End session and cleanup
            transcriber.end_session()
            await transcriber.cleanup()

    @pytest.mark.asyncio
    async def test_end_to_end_whisper_workflow(self):
        """Test complete workflow with Whisper backend."""
        # Mock Whisper module
        mock_whisper = MagicMock()
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model
        mock_model.transcribe.return_value = {
            "text": "transcribed text",
            "segments": [{"start": 0.0, "end": 2.0, "text": "transcribed text", "avg_logprob": -0.1}]
        }
        
        # Set up configuration
        config = TranscriptionConfig(
            backend="whisper",
            model_size="base",
            chunk_duration=2.0,
            device="cpu"
        )
        
        with patch.dict('sys.modules', {'whisper': mock_whisper}):
            with patch('tempfile.mkdtemp', return_value='/tmp/test_whisper'):
                with patch('asyncio.get_event_loop') as mock_loop:
                    # Mock async executor
                    from unittest.mock import AsyncMock
                    mock_executor = AsyncMock()
                    mock_executor.return_value = TranscriptionResult(
                        text="transcribed text",
                        confidence=0.8,
                        is_final=False
                    )
                    mock_loop.return_value.run_in_executor = mock_executor
                    
                    # Create transcriber
                    transcriber = TranscriptionFactory.create_transcriber(config)
                    
                    # Initialize
                    success = await transcriber.initialize()
                    assert success == True
                    
                    # Start session
                    transcriber.start_session()
                    
                    # Create test audio data (enough to trigger processing)
                    samples_needed = int(config.sample_rate * config.chunk_duration * 2)
                    audio_samples = np.random.randint(-1000, 1000, samples_needed, dtype=np.int16)
                    audio_data = audio_samples.tobytes()
                    
                    # Process chunk
                    result = await transcriber.transcribe_chunk(audio_data)
                    assert isinstance(result, TranscriptionResult)
                    
                    # Finalize
                    final_result = await transcriber.finalize()
                    assert isinstance(final_result, TranscriptionResult)
                    assert final_result.is_final == True
                    
                    # End session and cleanup
                    transcriber.end_session()
                    await transcriber.cleanup()

    def test_config_factory_integration(self):
        """Test integration between config loading and factory."""
        # Test environment-based configuration
        env_vars = {
            "TRANSCRIPTION_BACKEND": "whisper",
            "WHISPER_MODEL_SIZE": "large",
            "TRANSCRIPTION_CHUNK_DURATION": "3.0",
            "TRANSCRIPTION_CONFIDENCE_THRESHOLD": "0.8"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_transcription_config()
            transcriber = TranscriptionFactory.create_transcriber(config)
            
            assert transcriber.config.backend == "whisper"
            assert transcriber.config.model_size == "large"
            assert transcriber.config.chunk_duration == 3.0
            assert transcriber.config.confidence_threshold == 0.8

    def test_factory_backend_switching(self):
        """Test switching between backends using factory."""
        # Test PocketSphinx
        config_ps = TranscriptionConfig(backend="pocketsphinx")
        transcriber_ps = TranscriptionFactory.create_transcriber(config_ps)
        assert transcriber_ps.__class__.__name__ == "PocketSphinxTranscriber"
        
        # Test Whisper
        config_whisper = TranscriptionConfig(backend="whisper")
        transcriber_whisper = TranscriptionFactory.create_transcriber(config_whisper)
        assert transcriber_whisper.__class__.__name__ == "WhisperTranscriber"

    @pytest.mark.asyncio
    async def test_session_management_integration(self):
        """Test session management across the system."""
        config = TranscriptionConfig(backend="pocketsphinx")
        
        # Mock PocketSphinx
        mock_pocketsphinx = MagicMock()
        mock_decoder = MagicMock()
        mock_config = MagicMock()
        mock_pocketsphinx.Decoder.default_config.return_value = mock_config
        mock_pocketsphinx.Decoder.return_value = mock_decoder
        
        with patch.dict('sys.modules', {'pocketsphinx': mock_pocketsphinx}):
            transcriber = TranscriptionFactory.create_transcriber(config)
            await transcriber.initialize()
            
            # Test session lifecycle
            assert transcriber._session_active == False
            
            transcriber.start_session()
            assert transcriber._session_active == True
            
            # Add some data
            transcriber._audio_buffer = [1, 2, 3]
            transcriber._accumulated_text = "test"
            
            # Reset should clear everything
            transcriber.reset_session()
            assert transcriber._session_active == False
            assert len(transcriber._audio_buffer) == 0
            
            # Start new session
            transcriber.start_session()
            assert transcriber._session_active == True
            
            transcriber.end_session()
            assert transcriber._session_active == False
            
            await transcriber.cleanup()

    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling across the system."""
        config = TranscriptionConfig(backend="pocketsphinx")
        
        # Mock PocketSphinx with errors
        mock_pocketsphinx = MagicMock()
        mock_decoder = MagicMock()
        mock_config = MagicMock()
        
        mock_pocketsphinx.Decoder.default_config.return_value = mock_config
        mock_pocketsphinx.Decoder.return_value = mock_decoder
        
        # Mock decoder operations to raise errors
        mock_decoder.start_utt.side_effect = Exception("Start error")
        mock_decoder.process_raw.side_effect = Exception("Process error")
        mock_decoder.end_utt.side_effect = Exception("End error")
        
        with patch.dict('sys.modules', {'pocketsphinx': mock_pocketsphinx}):
            transcriber = TranscriptionFactory.create_transcriber(config)
            await transcriber.initialize()
            
            # Should handle session errors gracefully
            transcriber.start_session()  # Should not raise
            assert transcriber._session_active == True
            
            # Should handle processing errors
            # Create extra audio data to account for processing losses (1.5 seconds at 16kHz, 16-bit)
            audio_samples = np.random.randint(-1000, 1000, 24000, dtype=np.int16)
            audio_data = audio_samples.tobytes()
            result = await transcriber.transcribe_chunk(audio_data)
            assert isinstance(result, TranscriptionResult)
            assert result.error is not None
            
            # Should handle cleanup errors
            transcriber.end_session()  # Should not raise
            transcriber.reset_session()  # Should not raise
            await transcriber.cleanup()  # Should not raise

    def test_multiple_transcriber_instances(self):
        """Test creating and managing multiple transcriber instances."""
        configs = [
            TranscriptionConfig(backend="pocketsphinx", chunk_duration=1.0),
            TranscriptionConfig(backend="whisper", chunk_duration=2.0),
            TranscriptionConfig(backend="pocketsphinx", chunk_duration=3.0)
        ]
        
        transcribers = []
        for config in configs:
            transcriber = TranscriptionFactory.create_transcriber(config)
            transcribers.append(transcriber)
        
        # Verify each transcriber has correct configuration
        assert transcribers[0].config.backend == "pocketsphinx"
        assert transcribers[0].config.chunk_duration == 1.0
        
        assert transcribers[1].config.backend == "whisper"
        assert transcribers[1].config.chunk_duration == 2.0
        
        assert transcribers[2].config.backend == "pocketsphinx"
        assert transcribers[2].config.chunk_duration == 3.0
        
        # Verify they are independent instances
        assert transcribers[0] is not transcribers[2]

    @pytest.mark.asyncio
    async def test_audio_processing_pipeline_integration(self):
        """Test the complete audio processing pipeline."""
        config = TranscriptionConfig(
            backend="pocketsphinx",
            pocketsphinx_auto_resample=True,
            pocketsphinx_input_sample_rate=24000,
            pocketsphinx_audio_preprocessing="normalize"
        )
        
        # Mock PocketSphinx
        mock_pocketsphinx = MagicMock()
        mock_decoder = MagicMock()
        mock_config = MagicMock()
        mock_hyp = MagicMock()
        
        mock_pocketsphinx.Decoder.default_config.return_value = mock_config
        mock_pocketsphinx.Decoder.return_value = mock_decoder
        mock_hyp.hypstr = "processed audio"
        mock_hyp.prob = 0.85
        mock_decoder.hyp.return_value = mock_hyp
        
        with patch.dict('sys.modules', {'pocketsphinx': mock_pocketsphinx}):
            transcriber = TranscriptionFactory.create_transcriber(config)
            await transcriber.initialize()
            
            # Create 24kHz audio data (will be resampled to 16kHz)
            samples_24k = np.random.randint(-1000, 1000, 24000, dtype=np.int16)  # 1 second at 24kHz
            audio_data = samples_24k.tobytes()
            
            # Process through the pipeline
            # This should: resample 24k->16k, normalize, then transcribe
            transcriber._audio_buffer = [0.0] * 16000  # Pre-fill to trigger processing
            result = await transcriber.transcribe_chunk(audio_data)
            
            assert isinstance(result, TranscriptionResult)
            # Verify decoder was called (meaning audio made it through pipeline)
            mock_decoder.process_raw.assert_called()
            
            await transcriber.cleanup()

    def test_backend_availability_integration(self):
        """Test backend availability checking."""
        # Test with PocketSphinx available
        mock_pocketsphinx = MagicMock()
        with patch.dict('sys.modules', {'pocketsphinx': mock_pocketsphinx}):
            available = TranscriptionFactory.get_available_backends()
            assert "pocketsphinx" in available
            assert "whisper" in available  # Always listed

    @pytest.mark.asyncio
    async def test_config_validation_integration(self):
        """Test configuration validation in the complete system."""
        # Valid configuration should work
        valid_config = TranscriptionConfig(
            backend="whisper",
            confidence_threshold=0.8,
            chunk_duration=2.0,
            sample_rate=48000
        )
        
        transcriber = TranscriptionFactory.create_transcriber(valid_config)
        assert transcriber.config.confidence_threshold == 0.8
        
        # Invalid configuration should raise errors
        with pytest.raises(ValueError):
            invalid_config = TranscriptionConfig(
                backend="invalid_backend"
            )

    def test_module_exports_integration(self):
        """Test that all expected exports are available from the main module."""
        from opusagent.local.transcription import (
            TranscriptionResult,
            TranscriptionConfig,
            TranscriptionFactory,
            load_transcription_config,
            BaseTranscriber
        )
        
        # Verify all expected classes/functions are importable
        assert TranscriptionResult is not None
        assert TranscriptionConfig is not None
        assert TranscriptionFactory is not None
        assert load_transcription_config is not None
        assert BaseTranscriber is not None
        
        # Test that they work together
        config = load_transcription_config()
        assert isinstance(config, TranscriptionConfig)
        
        transcriber = TranscriptionFactory.create_transcriber(config)
        assert isinstance(transcriber, BaseTranscriber)

    @pytest.mark.asyncio
    async def test_concurrent_transcription_sessions(self):
        """Test multiple concurrent transcription sessions."""
        # Create multiple transcribers
        configs = [
            TranscriptionConfig(backend="pocketsphinx", chunk_duration=1.0),
            TranscriptionConfig(backend="pocketsphinx", chunk_duration=1.5)
        ]
        
        mock_pocketsphinx = MagicMock()
        mock_decoder = MagicMock()
        mock_config = MagicMock()
        mock_pocketsphinx.Decoder.default_config.return_value = mock_config
        mock_pocketsphinx.Decoder.return_value = mock_decoder
        
        with patch.dict('sys.modules', {'pocketsphinx': mock_pocketsphinx}):
            transcribers = [TranscriptionFactory.create_transcriber(config) for config in configs]
            
            # Initialize all
            init_results = await asyncio.gather(*[t.initialize() for t in transcribers], return_exceptions=False)
            assert all(init_results)
            
            # Start sessions
            for t in transcribers:
                t.start_session()
                assert t._session_active == True
            
            # Verify independence - each should have its own state
            transcribers[0]._accumulated_text = "first"
            transcribers[1]._accumulated_text = "second"
            
            assert transcribers[0]._accumulated_text == "first"
            assert transcribers[1]._accumulated_text == "second"
            
            # Cleanup all
            cleanup_tasks = [t.cleanup() for t in transcribers]
            await asyncio.gather(*cleanup_tasks, return_exceptions=False) 

    @pytest.mark.asyncio
    async def test_debug_process_raw_call(self):
        """Debug test to understand if process_raw is being called."""
        config = TranscriptionConfig(backend="pocketsphinx")
        
        # Mock PocketSphinx with tracking
        mock_pocketsphinx = MagicMock()
        mock_decoder = MagicMock()
        mock_config = MagicMock()
        
        mock_pocketsphinx.Decoder.default_config.return_value = mock_config
        mock_pocketsphinx.Decoder.return_value = mock_decoder
        
        # Track if process_raw is called
        process_raw_called = []
        def track_process_raw(*args, **kwargs):
            process_raw_called.append(True)
            raise Exception("Process error")
        
        mock_decoder.process_raw.side_effect = track_process_raw
        
        with patch.dict('sys.modules', {'pocketsphinx': mock_pocketsphinx}):
            transcriber = TranscriptionFactory.create_transcriber(config)
            await transcriber.initialize()
            transcriber.start_session()
            
            # Create enough audio data to trigger processing (account for processing losses)
            audio_samples = np.random.randint(-1000, 1000, 24000, dtype=np.int16)
            audio_data = audio_samples.tobytes()
            
            result = await transcriber.transcribe_chunk(audio_data)
            
            # Check if process_raw was actually called
            print(f"process_raw called: {len(process_raw_called) > 0}")
            print(f"Audio buffer length after processing: {len(transcriber._audio_buffer)}")
            print(f"Result: {result}")
            
            # If process_raw was called, error should be set
            if len(process_raw_called) > 0:
                assert result.error is not None, f"process_raw was called but error is None: {result}"
            
            await transcriber.cleanup() 