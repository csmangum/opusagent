#!/usr/bin/env python3
"""
Caller Agent Utilities

Helper functions for audio processing, conversation analysis, and test utilities.
"""

import asyncio
import base64
import io
import json
import logging
import os
import tempfile
import wave
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """Represents an audio chunk with metadata."""
    data: bytes
    sample_rate: int
    channels: int
    bit_depth: int
    timestamp: datetime
    duration_ms: float
    
    @property
    def size_bytes(self) -> int:
        """Get the size of the audio data in bytes."""
        return len(self.data)
        
    @property
    def duration_seconds(self) -> float:
        """Get the duration in seconds."""
        return self.duration_ms / 1000.0


class AudioProcessor:
    """Handles audio processing tasks for caller agents."""
    
    @staticmethod
    def pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, bit_depth: int = 16) -> bytes:
        """Convert PCM audio data to WAV format."""
        output = io.BytesIO()
        
        with wave.open(output, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(bit_depth // 8)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
            
        return output.getvalue()
        
    @staticmethod
    def wav_to_pcm(wav_data: bytes) -> Tuple[bytes, int, int, int]:
        """Convert WAV data to PCM and extract audio parameters."""
        input_buffer = io.BytesIO(wav_data)
        
        with wave.open(input_buffer, 'rb') as wav_file:
            channels = wav_file.getnchannels()
            sample_rate = wav_file.getframerate()
            bit_depth = wav_file.getsampwidth() * 8
            pcm_data = wav_file.readframes(wav_file.getnframes())
            
        return pcm_data, sample_rate, channels, bit_depth
        
    @staticmethod
    def create_silence(duration_ms: int, sample_rate: int = 16000, channels: int = 1) -> bytes:
        """Create silence audio data."""
        num_samples = int((duration_ms / 1000.0) * sample_rate * channels)
        silence = np.zeros(num_samples, dtype=np.int16)
        return silence.tobytes()
        
    @staticmethod
    def calculate_audio_duration(data: bytes, sample_rate: int = 16000, channels: int = 1, bit_depth: int = 16) -> float:
        """Calculate the duration of audio data in seconds."""
        bytes_per_sample = (bit_depth // 8) * channels
        num_samples = len(data) // bytes_per_sample
        return num_samples / sample_rate
        
    @staticmethod
    def resample_audio(data: bytes, from_rate: int, to_rate: int, channels: int = 1) -> bytes:
        """Resample audio data to a different sample rate."""
        # Convert bytes to numpy array
        dtype = np.int16 if len(data) % 2 == 0 else np.int8
        audio_array = np.frombuffer(data, dtype=dtype)
        
        # Calculate resampling ratio
        ratio = to_rate / from_rate
        
        # Simple linear interpolation resampling
        new_length = int(len(audio_array) * ratio)
        resampled = np.interp(
            np.linspace(0, len(audio_array) - 1, new_length),
            np.arange(len(audio_array)),
            audio_array
        ).astype(dtype)
        
        return resampled.tobytes()
        
    @staticmethod
    def mix_audio_chunks(chunks: List[AudioChunk], normalize: bool = True) -> AudioChunk:
        """Mix multiple audio chunks together."""
        if not chunks:
            raise ValueError("Cannot mix empty list of audio chunks")
            
        # Assume all chunks have the same format
        sample_rate = chunks[0].sample_rate
        channels = chunks[0].channels
        bit_depth = chunks[0].bit_depth
        
        # Convert all chunks to numpy arrays
        arrays = []
        for chunk in chunks:
            audio_array = np.frombuffer(chunk.data, dtype=np.int16)
            arrays.append(audio_array)
            
        # Pad arrays to the same length
        max_length = max(len(arr) for arr in arrays)
        padded_arrays = []
        for arr in arrays:
            if len(arr) < max_length:
                padded = np.pad(arr, (0, max_length - len(arr)), mode='constant')
                padded_arrays.append(padded)
            else:
                padded_arrays.append(arr)
                
        # Mix by summing
        mixed = np.sum(padded_arrays, axis=0)
        
        # Normalize to prevent clipping
        if normalize and mixed.max() > 0:
            mixed = mixed * (32767 / mixed.max())
            
        mixed_data = mixed.astype(np.int16).tobytes()
        duration_ms = AudioProcessor.calculate_audio_duration(mixed_data, sample_rate, channels, bit_depth) * 1000
        
        return AudioChunk(
            data=mixed_data,
            sample_rate=sample_rate,
            channels=channels,
            bit_depth=bit_depth,
            timestamp=datetime.now(),
            duration_ms=duration_ms
        )


class ConversationAnalyzer:
    """Analyzes conversation patterns and performance."""
    
    @staticmethod
    def analyze_conversation_flow(conversation_log: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze conversation flow and patterns."""
        if not conversation_log:
            return {"error": "Empty conversation log"}
            
        total_turns = len(conversation_log)
        caller_turns = sum(1 for turn in conversation_log if turn.get("speaker") == "caller")
        agent_turns = sum(1 for turn in conversation_log if turn.get("speaker") == "agent")
        
        # Calculate timing statistics
        durations = [turn.get("duration", 0) for turn in conversation_log if "duration" in turn]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Analyze interruptions
        interruptions = sum(1 for turn in conversation_log if turn.get("interrupted", False))
        
        # Analyze sentiment/tone changes
        sentiment_changes = 0
        prev_sentiment = None
        for turn in conversation_log:
            current_sentiment = turn.get("sentiment")
            if prev_sentiment and current_sentiment and prev_sentiment != current_sentiment:
                sentiment_changes += 1
            prev_sentiment = current_sentiment
            
        return {
            "total_turns": total_turns,
            "caller_turns": caller_turns,
            "agent_turns": agent_turns,
            "turn_ratio": caller_turns / agent_turns if agent_turns > 0 else float('inf'),
            "average_turn_duration": avg_duration,
            "interruptions": interruptions,
            "interruption_rate": interruptions / total_turns if total_turns > 0 else 0,
            "sentiment_changes": sentiment_changes,
            "conversation_length_seconds": sum(durations)
        }
        
    @staticmethod
    def extract_key_phrases(conversation_log: List[Dict[str, Any]], speaker: str = "caller") -> List[str]:
        """Extract key phrases from conversation for a specific speaker."""
        phrases = []
        
        for turn in conversation_log:
            if turn.get("speaker") == speaker and "text" in turn:
                text = turn["text"].lower()
                
                # Look for common banking keywords
                keywords = [
                    "card replacement", "lost card", "stolen card", "new card",
                    "account balance", "transaction", "deposit", "withdrawal",
                    "loan", "application", "interest rate", "credit",
                    "problem", "issue", "complaint", "help", "assistance",
                    "frustrated", "angry", "confused", "understand",
                    "transfer", "manager", "supervisor", "escalate"
                ]
                
                for keyword in keywords:
                    if keyword in text:
                        phrases.append(keyword)
                        
        return list(set(phrases))  # Remove duplicates
        
    @staticmethod
    def calculate_goal_achievement_score(goals: List[str], conversation_log: List[Dict[str, Any]]) -> float:
        """Calculate how well goals were achieved based on conversation content."""
        if not goals:
            return 1.0
            
        achieved_goals = 0
        conversation_text = " ".join([
            turn.get("text", "") for turn in conversation_log 
            if turn.get("speaker") == "agent"
        ]).lower()
        
        for goal in goals:
            goal_keywords = goal.lower().split()
            if any(keyword in conversation_text for keyword in goal_keywords):
                achieved_goals += 1
                
        return achieved_goals / len(goals)


class TestDataGenerator:
    """Generates test data and scenarios for caller agents."""
    
    @staticmethod
    def generate_phone_number(area_code: str = "555") -> str:
        """Generate a test phone number."""
        import random
        exchange = random.randint(100, 999)
        number = random.randint(1000, 9999)
        return f"+1{area_code}{exchange}{number:04d}"
        
    @staticmethod
    def generate_caller_names(count: int = 10) -> List[str]:
        """Generate list of test caller names."""
        first_names = [
            "Alice", "Bob", "Carol", "David", "Emma", "Frank", "Grace", "Henry",
            "Irene", "Jack", "Karen", "Louis", "Mary", "Nathan", "Olivia", "Peter",
            "Quinn", "Rachel", "Steve", "Tina", "Ulrich", "Victoria", "Walter",
            "Xenia", "Yves", "Zoe"
        ]
        
        last_names = [
            "Anderson", "Brown", "Clark", "Davis", "Evans", "Fisher", "Garcia",
            "Harris", "Johnson", "Kelly", "Lopez", "Miller", "Nelson", "O'Connor",
            "Parker", "Quinn", "Roberts", "Smith", "Taylor", "Underwood",
            "Valdez", "Williams", "Xavier", "Young", "Zhang"
        ]
        
        import random
        names = []
        for _ in range(count):
            first = random.choice(first_names)
            last = random.choice(last_names)
            names.append(f"{first} {last}")
            
        return names
        
    @staticmethod
    def generate_test_scenarios(
        personality_types: List[str], 
        scenario_types: List[str], 
        goals_per_scenario: int = 3
    ) -> List[Dict[str, Any]]:
        """Generate test scenarios for all combinations of personalities and scenario types."""
        scenarios = []
        
        goal_templates = {
            "card_replacement": [
                "Replace lost credit card",
                "Get emergency card replacement",
                "Update delivery address for new card"
            ],
            "account_inquiry": [
                "Check account balance",
                "Review recent transactions", 
                "Understand account fees"
            ],
            "loan_application": [
                "Learn about mortgage rates",
                "Apply for personal loan",
                "Understand loan requirements"
            ],
            "complaint": [
                "Resolve billing dispute",
                "Get charges reversed",
                "Escalate service complaint"
            ],
            "general_inquiry": [
                "Learn about bank services",
                "Update contact information",
                "Ask about branch hours"
            ]
        }
        
        for personality in personality_types:
            for scenario_type in scenario_types:
                goals = goal_templates.get(scenario_type, ["Complete request"])[:goals_per_scenario]
                
                scenario = {
                    "name": f"{personality.title()} {scenario_type.replace('_', ' ').title()}",
                    "type": "custom",
                    "personality": personality,
                    "scenario_type": scenario_type,
                    "goal": goals[0] if goals else "Complete request",
                    "timeout": 90.0,
                    "description": f"{personality.title()} customer with {scenario_type.replace('_', ' ')} request"
                }
                
                scenarios.append(scenario)
                
        return scenarios


class PerformanceMonitor:
    """Monitors performance metrics during testing."""
    
    def __init__(self):
        self.start_time = None
        self.metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_duration": 0.0,
            "openai_api_calls": 0,
            "audio_processing_time": 0.0,
            "conversation_turns": []
        }
        
    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_time = datetime.now()
        logger.info("Performance monitoring started")
        
    def record_call_start(self, caller_name: str):
        """Record the start of a call."""
        self.metrics["total_calls"] += 1
        logger.debug(f"Call started: {caller_name}")
        
    def record_call_success(self, duration: float, turns: int):
        """Record a successful call."""
        self.metrics["successful_calls"] += 1
        self.metrics["total_duration"] += duration
        self.metrics["conversation_turns"].append(turns)
        logger.debug(f"Call succeeded: {duration:.1f}s, {turns} turns")
        
    def record_call_failure(self, duration: float):
        """Record a failed call."""
        self.metrics["failed_calls"] += 1
        self.metrics["total_duration"] += duration
        logger.debug(f"Call failed: {duration:.1f}s")
        
    def record_openai_api_call(self):
        """Record an OpenAI API call."""
        self.metrics["openai_api_calls"] += 1
        
    def record_audio_processing_time(self, processing_time: float):
        """Record audio processing time."""
        self.metrics["audio_processing_time"] += processing_time
        
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report."""
        if not self.start_time:
            return {"error": "Monitoring not started"}
            
        total_time = (datetime.now() - self.start_time).total_seconds()
        total_calls = self.metrics["total_calls"]
        
        if total_calls == 0:
            return {"error": "No calls recorded"}
            
        avg_call_duration = self.metrics["total_duration"] / total_calls
        success_rate = self.metrics["successful_calls"] / total_calls
        
        avg_turns = 0
        if self.metrics["conversation_turns"]:
            avg_turns = sum(self.metrics["conversation_turns"]) / len(self.metrics["conversation_turns"])
            
        calls_per_minute = total_calls / (total_time / 60) if total_time > 0 else 0
        
        return {
            "monitoring_duration": total_time,
            "total_calls": total_calls,
            "successful_calls": self.metrics["successful_calls"],
            "failed_calls": self.metrics["failed_calls"],
            "success_rate": success_rate,
            "average_call_duration": avg_call_duration,
            "average_conversation_turns": avg_turns,
            "total_conversation_time": self.metrics["total_duration"],
            "openai_api_calls": self.metrics["openai_api_calls"],
            "audio_processing_time": self.metrics["audio_processing_time"],
            "calls_per_minute": calls_per_minute,
            "efficiency_ratio": self.metrics["total_duration"] / total_time if total_time > 0 else 0
        }


class ConfigManager:
    """Manages configuration files and settings."""
    
    @staticmethod
    def load_config(config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_file}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            return {}
            
    @staticmethod
    def save_config(config: Dict[str, Any], config_file: str):
        """Save configuration to JSON file."""
        try:
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Configuration saved to: {config_file}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            
    @staticmethod
    def validate_scenario_config(scenario: Dict[str, Any]) -> List[str]:
        """Validate scenario configuration and return list of errors."""
        errors = []
        
        required_fields = ["name", "type"]
        for field in required_fields:
            if field not in scenario:
                errors.append(f"Missing required field: {field}")
                
        if scenario.get("type") == "custom":
            custom_required = ["personality", "scenario_type", "goal"]
            for field in custom_required:
                if field not in scenario:
                    errors.append(f"Custom scenario missing required field: {field}")
                    
        elif scenario.get("type") == "predefined":
            if "scenario" not in scenario:
                errors.append("Predefined scenario missing 'scenario' field")
                
        return errors
        
    @staticmethod
    def create_default_config() -> Dict[str, Any]:
        """Create default configuration."""
        return {
            "description": "Default Caller Agent Configuration",
            "version": "1.0",
            "bridge_url": "ws://localhost:8000/ws/telephony",
            "openai_settings": {
                "model": "gpt-4o-realtime-preview-2025-06-03",
                "temperature": 0.8,
                "max_tokens": 4096
            },
            "audio_settings": {
                "sample_rate": 16000,
                "channels": 1,
                "bit_depth": 16,
                "chunk_size": 1024
            },
            "test_settings": {
                "default_timeout": 60.0,
                "max_conversation_turns": 20,
                "delay_between_tests": 2.0,
                "max_concurrent_tests": 3
            },
            "personalities": {
                "normal": {
                    "patience_level": 7,
                    "tech_comfort": 6,
                    "tendency_to_interrupt": 0.2
                },
                "difficult": {
                    "patience_level": 3,
                    "tech_comfort": 5,
                    "tendency_to_interrupt": 0.7
                }
            }
        }


def create_temp_audio_file(audio_data: bytes, prefix: str = "caller_audio_", suffix: str = ".wav") -> str:
    """Create a temporary audio file and return the path."""
    temp_fd, temp_path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
    try:
        with os.fdopen(temp_fd, 'wb') as temp_file:
            temp_file.write(audio_data)
    except Exception:
        os.close(temp_fd)
        raise
    return temp_path


def cleanup_temp_files(file_paths: List[str]):
    """Clean up temporary files."""
    for file_path in file_paths:
        try:
            os.unlink(file_path)
            logger.debug(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp file {file_path}: {e}")


async def wait_with_timeout(coro, timeout: float, timeout_message: str = "Operation timed out"):
    """Wait for a coroutine with timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(timeout_message)


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"
    else:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        return f"{hours}h {remaining_minutes}m"


def generate_test_report_html(results: Dict[str, Any], output_file: str):
    """Generate an HTML test report."""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Caller Agent Test Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .header { background-color: #f0f0f0; padding: 10px; margin-bottom: 20px; }
            .summary { background-color: #e8f4fd; padding: 15px; margin-bottom: 20px; }
            .success { color: green; }
            .failure { color: red; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Caller Agent Test Report</h1>
            <p>Generated: {timestamp}</p>
        </div>
        
        <div class="summary">
            <h2>Summary</h2>
            <p>Total Tests: {total_tests}</p>
            <p>Successful: <span class="success">{successful_tests}</span></p>
            <p>Failed: <span class="failure">{failed_tests}</span></p>
            <p>Success Rate: {success_rate:.1%}</p>
            <p>Total Duration: {total_duration}</p>
        </div>
        
        <h2>Individual Results</h2>
        <table>
            <tr>
                <th>Scenario</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Turns</th>
                <th>Goals</th>
            </tr>
            {test_rows}
        </table>
    </body>
    </html>
    """
    
    # Generate table rows
    test_rows = ""
    for result in results.get("results", []):
        status_class = "success" if result.get("success") else "failure"
        status_text = "✅ PASS" if result.get("success") else "❌ FAIL"
        
        test_rows += f"""
        <tr>
            <td>{result.get('scenario_name', 'Unknown')}</td>
            <td class="{status_class}">{status_text}</td>
            <td>{format_duration(result.get('duration', 0))}</td>
            <td>{result.get('conversation_turns', 0)}</td>
            <td>{len(result.get('goals_achieved', []))}/{result.get('goals_total', 0)}</td>
        </tr>
        """
    
    # Fill in template
    html_content = html_template.format(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_tests=results.get("summary", {}).get("total_tests", 0),
        successful_tests=results.get("summary", {}).get("successful_tests", 0),
        failed_tests=results.get("summary", {}).get("failed_tests", 0),
        success_rate=results.get("summary", {}).get("success_rate", 0),
        total_duration=format_duration(results.get("summary", {}).get("total_duration", 0)),
        test_rows=test_rows
    )
    
    # Save HTML file
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    logger.info(f"HTML report saved to: {output_file}")


# Example usage functions
def example_audio_processing():
    """Example of using audio processing utilities."""
    # Create some test audio data
    silence = AudioProcessor.create_silence(1000)  # 1 second of silence
    print(f"Created {len(silence)} bytes of silence")
    
    # Convert to WAV
    wav_data = AudioProcessor.pcm_to_wav(silence)
    print(f"WAV data: {len(wav_data)} bytes")
    
    # Convert back to PCM
    pcm_data, rate, channels, depth = AudioProcessor.wav_to_pcm(wav_data)
    print(f"PCM: {len(pcm_data)} bytes, {rate}Hz, {channels}ch, {depth}bit")


def example_test_data_generation():
    """Example of generating test data."""
    generator = TestDataGenerator()
    
    # Generate phone numbers
    phones = [generator.generate_phone_number() for _ in range(5)]
    print(f"Phone numbers: {phones}")
    
    # Generate caller names
    names = generator.generate_caller_names(5)
    print(f"Caller names: {names}")
    
    # Generate test scenarios
    personalities = ["normal", "difficult", "angry"]
    scenarios = ["card_replacement", "account_inquiry"]
    test_scenarios = generator.generate_test_scenarios(personalities, scenarios)
    print(f"Generated {len(test_scenarios)} test scenarios")


if __name__ == "__main__":
    # Run examples
    print("Audio Processing Example:")
    example_audio_processing()
    
    print("\nTest Data Generation Example:")
    example_test_data_generation()
    
    print("\nUtilities module ready for import") 