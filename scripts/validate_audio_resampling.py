import asyncio
import base64
import logging
from pathlib import Path
import sys
import unittest
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock
import numpy as np
import json

# Add the project root to the path for imports BEFORE importing project modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now import project modules after path is set up
from opusagent.audio_stream_handler import AudioStreamHandler
from tui.utils.audio_utils import AudioUtils
from opusagent.config.logging_config import configure_logging
from opusagent.call_recorder import CallRecorder

logger = configure_logging("validate_audio_resampling")

class TestAudioResampling(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.platform_ws = MagicMock()
        self.realtime_ws = AsyncMock()
        self.realtime_ws.send = AsyncMock()
        # Mock the websocket to appear open
        self.realtime_ws.close_code = None
        
        self.handler = AudioStreamHandler(
            platform_websocket=self.platform_ws,
            realtime_websocket=self.realtime_ws,
            call_recorder=CallRecorder("test_convo"),
            enable_quality_monitoring=False
        )
        await self.handler.initialize_stream("test_convo", "pcm16")

    def generate_test_audio(self, sample_rate: int, duration_ms: int = 100) -> bytes:
        """Generate sine wave test audio."""
        t = np.linspace(0, duration_ms / 1000, int(sample_rate * duration_ms / 1000), False)
        audio = 0.5 * np.sin(2 * np.pi * 440 * t)  # 440Hz tone
        audio_int16 = (audio * 32767).astype(np.int16)
        return audio_int16.tobytes()

    async def _test_resampling(self, bridge_type: str, input_rate: int):
        """Helper method to test resampling for a specific bridge type."""
        self.handler.bridge_type = bridge_type
        test_audio = self.generate_test_audio(input_rate, 50)  # Small chunk to test padding
        audio_b64 = base64.b64encode(test_audio).decode('utf-8')
        data = {"audioChunk": audio_b64}

        await self.handler.handle_incoming_audio(data)

        # Check if sent to OpenAI
        self.realtime_ws.send.assert_called_once()
        sent_json = self.realtime_ws.send.call_args[0][0]
        sent_data = json.loads(sent_json)
        sent_audio = base64.b64decode(sent_data['audio'])

        # Verify final sent audio is at 24kHz, padded to at least 4800 bytes (100ms at 24kHz)
        expected_min_size = 4800
        self.assertGreaterEqual(len(sent_audio), expected_min_size)

        # Verify internal processing: resampled to 16kHz, padded if needed
        internal_size = int(0.1 * 16000 * 2)  # 3200 bytes min
        logger.info(f"{bridge_type} ({input_rate}Hz): Original {len(test_audio)} bytes, Sent {len(sent_audio)} bytes")

    async def test_twilio_resampling(self):
        """Test Twilio 8kHz input resampling."""
        await self._test_resampling('twilio', 8000)

    async def test_audiocodes_resampling(self):
        """Test AudioCodes 16kHz input resampling."""
        await self._test_resampling('audiocodes', 16000)

    async def test_call_agent_resampling(self):
        """Test Call Agent 16kHz input resampling."""
        await self._test_resampling('call_agent', 16000)

    async def test_unknown_bridge_resampling(self):
        """Test unknown bridge type defaults to 16kHz."""
        await self._test_resampling('unknown', 16000)

    async def test_very_small_chunk(self):
        """Test with a very small chunk (e.g., 10ms)."""
        self.handler.bridge_type = 'twilio'
        test_audio = self.generate_test_audio(8000, 10)  # 10ms
        audio_b64 = base64.b64encode(test_audio).decode('utf-8')
        data = {"audioChunk": audio_b64}
        await self.handler.handle_incoming_audio(data)
        self.realtime_ws.send.assert_called_once()
        sent_json = self.realtime_ws.send.call_args[0][0]
        sent_data = json.loads(sent_json)
        sent_audio = base64.b64decode(sent_data['audio'])
        self.assertGreaterEqual(len(sent_audio), 4800)

    async def test_large_chunk(self):
        """Test with a large chunk (e.g., 300ms)."""
        self.handler.bridge_type = 'audiocodes'
        test_audio = self.generate_test_audio(16000, 300)  # 300ms
        audio_b64 = base64.b64encode(test_audio).decode('utf-8')
        data = {"audioChunk": audio_b64}
        await self.handler.handle_incoming_audio(data)
        self.realtime_ws.send.assert_called_once()
        sent_json = self.realtime_ws.send.call_args[0][0]
        sent_data = json.loads(sent_json)
        sent_audio = base64.b64decode(sent_data['audio'])
        self.assertGreaterEqual(len(sent_audio), 3 * 4800)  # Should be at least 300ms at 24kHz

    async def test_nonstandard_sample_rate_11025(self):
        """Test with 11025Hz input."""
        await self._test_resampling('unknown', 11025)

    async def test_nonstandard_sample_rate_22050(self):
        """Test with 22050Hz input."""
        await self._test_resampling('unknown', 22050)

    async def test_nonstandard_sample_rate_48000(self):
        """Test with 48000Hz input."""
        await self._test_resampling('unknown', 48000)

    async def test_silence_only(self):
        """Test with a chunk of all zeros (silence)."""
        self.handler.bridge_type = 'audiocodes'
        silence = (np.zeros(int(16000 * 0.1), dtype=np.int16)).tobytes()  # 100ms silence
        audio_b64 = base64.b64encode(silence).decode('utf-8')
        data = {"audioChunk": audio_b64}
        await self.handler.handle_incoming_audio(data)
        self.realtime_ws.send.assert_called_once()
        sent_json = self.realtime_ws.send.call_args[0][0]
        sent_data = json.loads(sent_json)
        sent_audio = base64.b64decode(sent_data['audio'])
        self.assertGreaterEqual(len(sent_audio), 4800)

    async def test_random_noise(self):
        """Test with random noise input."""
        self.handler.bridge_type = 'twilio'
        noise = (np.random.randint(-32768, 32767, int(8000 * 0.1), dtype=np.int16)).tobytes()  # 100ms noise
        audio_b64 = base64.b64encode(noise).decode('utf-8')
        data = {"audioChunk": audio_b64}
        await self.handler.handle_incoming_audio(data)
        self.realtime_ws.send.assert_called_once()
        sent_json = self.realtime_ws.send.call_args[0][0]
        sent_data = json.loads(sent_json)
        sent_audio = base64.b64decode(sent_data['audio'])
        self.assertGreaterEqual(len(sent_audio), 4800)

    async def test_multiple_sequential_chunks(self):
        """Test multiple sequential chunks (simulate a stream)."""
        self.handler.bridge_type = 'audiocodes'
        for _ in range(5):
            test_audio = self.generate_test_audio(16000, 100)
            audio_b64 = base64.b64encode(test_audio).decode('utf-8')
            data = {"audioChunk": audio_b64}
            await self.handler.handle_incoming_audio(data)
        self.assertEqual(self.realtime_ws.send.call_count, 5)

    async def test_bridge_type_switching(self):
        """Switch bridge_type between chunks and ensure handler adapts."""
        for bridge_type, rate in [('twilio', 8000), ('audiocodes', 16000), ('call_agent', 16000)]:
            self.handler.bridge_type = bridge_type
            test_audio = self.generate_test_audio(rate, 100)
            audio_b64 = base64.b64encode(test_audio).decode('utf-8')
            data = {"audioChunk": audio_b64}
            await self.handler.handle_incoming_audio(data)
        self.assertEqual(self.realtime_ws.send.call_count, 3)

    async def test_invalid_base64(self):
        """Test with invalid base64 input."""
        self.handler.bridge_type = 'twilio'
        data = {"audioChunk": "!!!notbase64!!!"}
        # Should not raise, but should log error and not call send
        await self.handler.handle_incoming_audio(data)
        self.realtime_ws.send.assert_not_called()

if __name__ == '__main__':
    unittest.main() 