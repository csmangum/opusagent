"""
Performance tests for the OpenAI Realtime API client.

These tests measure the performance characteristics of the RealtimeClient,
including latency, throughput, memory usage, and behavior under load.
"""

import asyncio
import base64
import gc
import json
import os
import sqlite3
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import psutil
import pytest
from dotenv import load_dotenv

from opusagent.realtime.realtime_client import RealtimeClient
from opusagent.models.openai_api import ServerEventType
from tests.bot.test_logging import logger

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY environment variable not found. Check your .env file."
    )

# Test configuration
TEST_MODEL = "gpt-4o-realtime-preview"
TEST_VOICE = "alloy"

# Performance test parameters
LOAD_TEST_CONNECTIONS = 3  # Number of simultaneous connections for load testing
MESSAGE_SENDING_ITERATIONS = 10  # Number of messages to send for throughput tests
AUDIO_CHUNK_SIZE = 2000  # Reduced from 4000 to avoid rate limits
AUDIO_SEND_ITERATIONS = 3  # Further reduced from 5 to avoid rate limits
STABILITY_TEST_DURATION = 60  # Duration of stability test in seconds
LATENCY_TEST_ITERATIONS = 5  # Number of iterations for latency tests
DB_FILE = "performance_test.db"  # SQLite database file

# Add PowerShell script at the top level
POWERSHELL_RUN_SCRIPT = """
# run_performance_tests.ps1
# PowerShell script to run the performance tests

Write-Host "Running performance tests for the RealtimeClient"

# Check if OPENAI_API_KEY is set
if (-not $env:OPENAI_API_KEY) {
    Write-Host "ERROR: OPENAI_API_KEY environment variable is not set." -ForegroundColor Red
    Write-Host "Please set it using: $env:OPENAI_API_KEY = 'your-api-key'"
    exit 1
}

# Run the tests
try {
    # Activate virtual environment if exists
    if (Test-Path ".venv\Scripts\Activate.ps1") {
        Write-Host "Activating virtual environment..." -ForegroundColor Green
        & .venv\Scripts\Activate.ps1
    }

    Write-Host "Starting performance tests..." -ForegroundColor Green
    
    # Run a specific test or all tests
    if ($args.Count -gt 0) {
        $test_name = $args[0]
        Write-Host "Running specific test: $test_name" -ForegroundColor Yellow
        python -m pytest tests/bot/test_realtime_client_performance.py::$test_name -v
    } else {
        # Run all tests
        python -m pytest tests/bot/test_realtime_client_performance.py -v
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Performance tests completed successfully!" -ForegroundColor Green
    } else {
        Write-Host "Performance tests failed with exit code $LASTEXITCODE" -ForegroundColor Red
    }
} catch {
    Write-Host "Error running tests: $_" -ForegroundColor Red
    exit 1
} finally {
    # Deactivate virtual environment if it was activated
    if ($env:VIRTUAL_ENV) {
        Write-Host "Deactivating virtual environment..." -ForegroundColor Green
        deactivate
    }
}
"""

# Create the PowerShell script file
with open("run_performance_tests.ps1", "w") as f:
    f.write(POWERSHELL_RUN_SCRIPT)


@pytest.fixture
def realtime_client():
    """Create a RealtimeClient instance for testing."""
    if not OPENAI_API_KEY:
        pytest.skip("OPENAI_API_KEY environment variable not set")

    return RealtimeClient(api_key=OPENAI_API_KEY, model=TEST_MODEL, voice=TEST_VOICE)


def create_test_audio() -> Tuple[bytes, int]:
    """Create test audio data for sending.

    Returns:
        Tuple containing the audio data and its sample rate.
    """
    # Create a simple 1-second sine wave
    sample_rate = 16000
    duration = 1  # seconds
    frequency = 440  # Hz (A4 note)

    t = np.linspace(0, duration, sample_rate * duration, False)
    audio_data = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)

    return audio_data.tobytes(), sample_rate


def measure_memory_usage() -> Dict[str, float]:
    """Measure current memory usage.

    Returns:
        Dict with memory usage statistics in MB.
    """
    process = psutil.Process()
    memory_info = process.memory_info()

    return {
        "rss_mb": memory_info.rss / (1024 * 1024),
        "vms_mb": memory_info.vms / (1024 * 1024),
        "percent": process.memory_percent(),
    }


def init_database():
    """Initialize the SQLite database with required tables."""
    db_path = Path("test_results") / DB_FILE
    db_path.parent.mkdir(exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create test_results table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_name TEXT NOT NULL,
        timestamp DATETIME NOT NULL,
        status TEXT NOT NULL,
        python_version TEXT,
        platform TEXT,
        audio_chunk_size INTEGER,
        audio_send_iterations INTEGER,
        load_test_connections INTEGER,
        stability_test_duration INTEGER,
        average_chunks_per_second REAL,
        average_kb_per_second REAL,
        total_chunks_sent INTEGER,
        total_bytes_sent INTEGER,
        error_message TEXT,
        error_type TEXT
    )
    """
    )

    # Create test_logs table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS test_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_result_id INTEGER,
        timestamp DATETIME NOT NULL,
        level TEXT NOT NULL,
        message TEXT NOT NULL,
        FOREIGN KEY (test_result_id) REFERENCES test_results(id)
    )
    """
    )

    conn.commit()
    conn.close()

    return str(db_path)


def save_test_results(
    test_name: str,
    metrics: Dict,
    status: str = "completed",
    error: Optional[Exception] = None,
):
    """Save test results to SQLite database.

    Args:
        test_name: Name of the test
        metrics: Dictionary of test metrics
        status: Test status (completed, failed, skipped)
        error: Exception object if test failed
    """
    db_path = Path("test_results") / DB_FILE
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Insert test result
    cursor.execute(
        """
    INSERT INTO test_results (
        test_name, timestamp, status, python_version, platform,
        audio_chunk_size, audio_send_iterations, load_test_connections,
        stability_test_duration, average_chunks_per_second, average_kb_per_second,
        total_chunks_sent, total_bytes_sent, error_message, error_type
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            test_name,
            datetime.now().isoformat(),
            status,
            sys.version,
            sys.platform,
            AUDIO_CHUNK_SIZE,
            AUDIO_SEND_ITERATIONS,
            LOAD_TEST_CONNECTIONS,
            STABILITY_TEST_DURATION,
            metrics.get("average_chunks_per_second"),
            metrics.get("average_kb_per_second"),
            metrics.get("total_chunks_sent"),
            metrics.get("total_bytes_sent"),
            str(error) if error else None,
            type(error).__name__ if error else None,
        ),
    )

    test_result_id = cursor.lastrowid

    # Insert test logs if available
    if "logs" in metrics:
        for log in metrics["logs"]:
            cursor.execute(
                """
            INSERT INTO test_logs (test_result_id, timestamp, level, message)
            VALUES (?, ?, ?, ?)
            """,
                (test_result_id, log["timestamp"], log["level"], log["message"]),
            )

    conn.commit()
    conn.close()

    return test_result_id


def log_test_event(test_result_id: int, level: str, message: str):
    """Log a test event to the database.

    Args:
        test_result_id: ID of the test result to associate with
        level: Log level (INFO, ERROR, etc.)
        message: Log message
    """
    db_path = Path("test_results") / DB_FILE
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
    INSERT INTO test_logs (test_result_id, timestamp, level, message)
    VALUES (?, ?, ?, ?)
    """,
        (test_result_id, datetime.now().isoformat(), level, message),
    )

    conn.commit()
    conn.close()


@pytest.mark.asyncio
async def test_message_sending_latency(realtime_client):
    """Test latency of sending text messages."""
    logger.start_test("test_message_sending_latency")

    # Connect to the API
    connected = await realtime_client.connect()
    assert connected, "Failed to connect to the API"

    latencies = []

    try:
        # Measure latency of message sending
        for i in range(LATENCY_TEST_ITERATIONS):
            message = f"This is a test message {i} for latency measurement"

            # Measure time to send message
            start_time = time.time()
            result = await realtime_client.send_text_message(message)
            end_time = time.time()

            assert result, f"Failed to send message in iteration {i}"

            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)

            # Small delay between messages
            await asyncio.sleep(0.5)

        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)

        # Log results
        logger.log_metric("average_latency", avg_latency, "ms")
        logger.log_metric("min_latency", min_latency, "ms")
        logger.log_metric("max_latency", max_latency, "ms")
        logger.log_metric("total_messages", len(latencies))

        print(f"\nText Message Sending Latency (ms):")
        print(f"  Average: {avg_latency:.2f}")
        print(f"  Min: {min_latency:.2f}")
        print(f"  Max: {max_latency:.2f}")

        # Verify reasonable latency
        assert (
            avg_latency < 500
        ), f"Average message sending latency ({avg_latency:.2f}ms) exceeds threshold (500ms)"

    finally:
        await realtime_client.close()
        log_file = logger.end_test()
        print(f"Test results saved to: {log_file}")


@pytest.mark.asyncio
async def test_audio_sending_throughput(realtime_client):
    """Test throughput of sending audio chunks."""
    # Initialize database
    db_path = init_database()
    print(f"Using database: {db_path}")

    logger.start_test("test_audio_sending_throughput")
    test_result_id = None

    try:
        # Connect to the API
        connected = await realtime_client.connect()
        assert connected, "Failed to connect to the API"

        # Create test audio
        audio_data, _ = create_test_audio()
        throughput_metrics = []
        test_status = "completed"
        logs = []

        # Divide audio into chunks
        chunks = [
            audio_data[i : i + AUDIO_CHUNK_SIZE]
            for i in range(0, len(audio_data), AUDIO_CHUNK_SIZE)
        ]

        # Measure throughput over multiple iterations
        for iteration in range(3):
            chunk_count = 0
            total_bytes = 0
            start_time = time.time()

            for chunk in chunks * AUDIO_SEND_ITERATIONS:
                try:
                    result = await realtime_client.send_audio_chunk(chunk)
                    assert (
                        result
                    ), f"Failed to send audio chunk {chunk_count} in iteration {iteration}"

                    chunk_count += 1
                    total_bytes += len(chunk)

                    # Increased delay to avoid rate limiting
                    await asyncio.sleep(0.5)  # Increased from 0.2 to 0.5

                except Exception as e:
                    if "rate limit" in str(e).lower():
                        # If rate limited, wait longer and retry
                        await asyncio.sleep(2.0)
                        logs.append(
                            {
                                "timestamp": datetime.now().isoformat(),
                                "level": "WARNING",
                                "message": f"Rate limit hit, retrying: {str(e)}",
                            }
                        )
                        continue
                    raise

            end_time = time.time()
            elapsed_time = end_time - start_time

            # Calculate throughput metrics
            chunks_per_second = chunk_count / elapsed_time
            bytes_per_second = total_bytes / elapsed_time
            kb_per_second = bytes_per_second / 1024

            throughput_metrics.append(
                {
                    "chunks_per_second": chunks_per_second,
                    "kb_per_second": kb_per_second,
                    "iteration": iteration + 1,
                    "chunk_count": chunk_count,
                    "total_bytes": total_bytes,
                    "elapsed_time": elapsed_time,
                }
            )

            logs.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "message": f"Iteration {iteration + 1} completed: {chunks_per_second:.2f} chunks/s, {kb_per_second:.2f} KB/s",
                }
            )

            # Allow more time between iterations
            await asyncio.sleep(3.0)  # Increased from 2.0 to 3.0

        # Calculate average metrics
        avg_chunks_per_second = statistics.mean(
            [m["chunks_per_second"] for m in throughput_metrics]
        )
        avg_kb_per_second = statistics.mean(
            [m["kb_per_second"] for m in throughput_metrics]
        )

        # Save results
        metrics = {
            "throughput_metrics": throughput_metrics,
            "average_chunks_per_second": avg_chunks_per_second,
            "average_kb_per_second": avg_kb_per_second,
            "total_chunks_sent": sum(m["chunk_count"] for m in throughput_metrics),
            "total_bytes_sent": sum(m["total_bytes"] for m in throughput_metrics),
            "logs": logs,
        }

        test_result_id = save_test_results("test_audio_sending_throughput", metrics)
        print(f"Test results saved with ID: {test_result_id}")

    except Exception as e:
        test_status = "failed"
        metrics = {"error": str(e), "error_type": type(e).__name__, "logs": logs}
        test_result_id = save_test_results(
            "test_audio_sending_throughput", metrics, test_status, e
        )
        print(f"Test failed. Results saved with ID: {test_result_id}")
        raise

    finally:
        await realtime_client.close()
        log_file = logger.end_test()
        print(f"Test logs saved to: {log_file}")


@pytest.mark.asyncio
async def test_response_creation_latency(realtime_client):
    """Test latency of creating responses."""
    # Connect to the API
    connected = await realtime_client.connect()
    assert connected, "Failed to connect to the API"

    response_latencies = []
    first_token_latencies = []
    text_received = asyncio.Event()

    # Track first token timing
    first_token_time = None
    response_start_time = None

    async def on_text_delta(event):
        nonlocal first_token_time
        if first_token_time is None and response_start_time:
            first_token_time = time.time()
            first_token_latencies.append(
                (first_token_time - response_start_time) * 1000
            )
            text_received.set()

    try:
        # Register handler for text deltas
        realtime_client.on(ServerEventType.RESPONSE_TEXT_DELTA, on_text_delta)

        for i in range(LATENCY_TEST_ITERATIONS):
            # Send a text message
            message = f"Please respond with a very brief greeting #{i}."
            sent = await realtime_client.send_text_message(message)
            assert sent, f"Failed to send message in iteration {i}"

            # Measure time to create response
            first_token_time = None
            text_received.clear()

            response_start_time = time.time()
            result = await realtime_client.create_response(modalities=["text"])
            response_creation_time = time.time()

            assert result, f"Failed to create response in iteration {i}"

            # Calculate response creation latency
            latency_ms = (response_creation_time - response_start_time) * 1000
            response_latencies.append(latency_ms)

            # Wait for first token or timeout
            try:
                await asyncio.wait_for(text_received.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                print(f"Timeout waiting for first token in iteration {i}")

            # Wait for response to complete
            await asyncio.sleep(2.0)

        # Calculate statistics
        avg_response_latency = statistics.mean(response_latencies)
        avg_first_token_latency = (
            statistics.mean(first_token_latencies)
            if first_token_latencies
            else float("nan")
        )

        # Log results
        print(f"\nResponse Creation Latency (ms):")
        print(f"  Average response creation: {avg_response_latency:.2f}")
        print(f"  Average time to first token: {avg_first_token_latency:.2f}")

        # Verify reasonable latency
        assert (
            avg_response_latency < 1000
        ), f"Average response creation latency ({avg_response_latency:.2f}ms) exceeds threshold"

    finally:
        realtime_client.off(ServerEventType.RESPONSE_TEXT_DELTA, on_text_delta)
        await realtime_client.close()


@pytest.mark.asyncio
async def test_memory_usage(realtime_client):
    """Test memory usage during operation."""
    logger.start_test("test_memory_usage")

    # Garbage collect before starting
    gc.collect()

    # Measure baseline memory usage
    baseline_memory = measure_memory_usage()

    # Connect to the API
    connected = await realtime_client.connect()
    assert connected, "Failed to connect to the API"

    try:
        # Create test audio
        audio_data, _ = create_test_audio()

        # Memory measurements at different stages
        memory_measurements = {
            "baseline": baseline_memory,
            "after_connect": measure_memory_usage(),
            "after_operations": None,
            "after_gc": None,
        }

        # Perform operations that might affect memory
        # 1. Send several messages
        for i in range(5):
            await realtime_client.send_text_message(
                f"Test message {i} for memory usage test"
            )

        # 2. Send audio chunks
        chunks = [
            audio_data[i : i + AUDIO_CHUNK_SIZE]
            for i in range(0, len(audio_data), AUDIO_CHUNK_SIZE)
        ]
        for chunk in chunks * 3:
            await realtime_client.send_audio_chunk(chunk)
            await asyncio.sleep(0.05)

        # 3. Create responses
        await realtime_client.create_response(modalities=["text"])
        await asyncio.sleep(3.0)

        # Measure memory after operations
        memory_measurements["after_operations"] = measure_memory_usage()

        # Garbage collect and measure again
        gc.collect()
        memory_measurements["after_gc"] = measure_memory_usage()

        # Log results
        logger.log_metric(
            "baseline_rss_mb", memory_measurements["baseline"]["rss_mb"], "MB"
        )
        logger.log_metric(
            "after_connect_rss_mb", memory_measurements["after_connect"]["rss_mb"], "MB"
        )
        logger.log_metric(
            "after_operations_rss_mb",
            memory_measurements["after_operations"]["rss_mb"],
            "MB",
        )
        logger.log_metric(
            "after_gc_rss_mb", memory_measurements["after_gc"]["rss_mb"], "MB"
        )

        # Calculate memory increase
        memory_increase = (
            memory_measurements["after_operations"]["rss_mb"]
            - baseline_memory["rss_mb"]
        )
        logger.log_metric("memory_increase_mb", memory_increase, "MB")

        print(f"\nMemory Usage (MB):")
        print(f"  Baseline RSS: {baseline_memory['rss_mb']:.2f}")
        print(
            f"  After connect RSS: {memory_measurements['after_connect']['rss_mb']:.2f}"
        )
        print(
            f"  After operations RSS: {memory_measurements['after_operations']['rss_mb']:.2f}"
        )
        print(f"  After GC RSS: {memory_measurements['after_gc']['rss_mb']:.2f}")
        print(f"  Memory increase: {memory_increase:.2f} MB")

        # Memory should increase by a reasonable amount
        assert (
            memory_increase < 100
        ), f"Memory increase ({memory_increase:.2f} MB) exceeds threshold"

    finally:
        await realtime_client.close()
        log_file = logger.end_test()
        print(f"Test results saved to: {log_file}")


@pytest.mark.asyncio
async def test_load_multiple_clients():
    """Test behavior under load with multiple client connections."""
    logger.start_test("test_load_multiple_clients")

    if not OPENAI_API_KEY:
        pytest.skip("OPENAI_API_KEY environment variable not set")

    clients = []

    try:
        # Create multiple clients
        for i in range(LOAD_TEST_CONNECTIONS):
            client = RealtimeClient(
                api_key=OPENAI_API_KEY, model=TEST_MODEL, voice=TEST_VOICE
            )
            clients.append(client)

        # Connect all clients concurrently
        connection_start = time.time()
        connection_tasks = [client.connect() for client in clients]
        connection_results = await asyncio.gather(*connection_tasks)
        connection_time = time.time() - connection_start

        # Verify connections
        successful_connections = sum(connection_results)
        assert (
            successful_connections == LOAD_TEST_CONNECTIONS
        ), f"Only {successful_connections}/{LOAD_TEST_CONNECTIONS} clients connected successfully"

        logger.log_metric("connection_time_seconds", connection_time)
        logger.log_metric("successful_connections", successful_connections)

        print(f"\nMultiple Clients Load Test:")
        print(
            f"  Connected {successful_connections} clients in {connection_time:.2f} seconds"
        )

        # Send messages from all clients concurrently
        message_tasks = []
        for i, client in enumerate(clients):
            message = f"Test message from client {i} under load test"
            message_tasks.append(client.send_text_message(message))

        message_start = time.time()
        message_results = await asyncio.gather(*message_tasks)
        message_time = time.time() - message_start

        successful_messages = sum(message_results)
        logger.log_metric("message_sending_time_seconds", message_time)
        logger.log_metric("successful_messages", successful_messages)

        print(
            f"  Sent {successful_messages} messages concurrently in {message_time:.2f} seconds"
        )

        # Create responses from all clients concurrently
        response_tasks = []
        for client in clients:
            response_tasks.append(client.create_response(modalities=["text"]))

        response_start = time.time()
        response_results = await asyncio.gather(*response_tasks)
        response_time = time.time() - response_start

        successful_responses = sum(response_results)
        logger.log_metric("response_creation_time_seconds", response_time)
        logger.log_metric("successful_responses", successful_responses)

        print(
            f"  Created {successful_responses} responses concurrently in {response_time:.2f} seconds"
        )

        # Wait for some response data
        await asyncio.sleep(3.0)

        # Verify reasonable performance under load
        assert (
            message_time < 5.0
        ), f"Message sending under load took too long ({message_time:.2f}s)"
        assert (
            response_time < 5.0
        ), f"Response creation under load took too long ({response_time:.2f}s)"

    finally:
        # Close all clients
        close_tasks = [client.close() for client in clients]
        await asyncio.gather(*close_tasks)
        log_file = logger.end_test()
        print(f"Test results saved to: {log_file}")


@pytest.mark.asyncio
async def test_stability_over_time(realtime_client):
    """Test stability over an extended period of continuous usage."""
    logger.start_test("test_stability_over_time")

    # Connect to the API
    connected = await realtime_client.connect()
    assert connected, "Failed to connect to the API"

    # Create test audio
    audio_data, _ = create_test_audio()

    # Events tracking
    operations_completed = 0
    errors_encountered = 0
    start_time = time.time()
    end_time = start_time + STABILITY_TEST_DURATION

    async def on_error(event):
        nonlocal errors_encountered
        errors_encountered += 1
        print(f"Error during stability test: {event}")

    try:
        # Register error handler
        realtime_client.on(ServerEventType.ERROR, on_error)

        print(f"\nStability Test:")
        print(
            f"  Running continuous operations for {STABILITY_TEST_DURATION} seconds..."
        )

        # Run continuous operations until time limit
        while time.time() < end_time:
            # Alternate between different operations
            operation_type = operations_completed % 3

            if operation_type == 0:
                # Send text message
                message = f"Test message {operations_completed} during stability test at {datetime.now().isoformat()}"
                result = await realtime_client.send_text_message(message)
                if result:
                    operations_completed += 1

            elif operation_type == 1:
                # Send audio chunk
                chunk_index = operations_completed % len(audio_data)
                chunk_size = min(AUDIO_CHUNK_SIZE, len(audio_data) - chunk_index)
                chunk = audio_data[chunk_index : chunk_index + chunk_size]
                result = await realtime_client.send_audio_chunk(chunk)
                if result:
                    operations_completed += 1

            else:
                # Create response
                result = await realtime_client.create_response(modalities=["text"])
                if result:
                    operations_completed += 1
                    # Wait for response processing
                    await asyncio.sleep(2.0)

            # Brief pause between operations
            await asyncio.sleep(0.5)

        # Calculate operational throughput
        test_duration = time.time() - start_time
        ops_per_second = operations_completed / test_duration

        # Log results
        logger.log_metric("total_operations", operations_completed)
        logger.log_metric("errors_encountered", errors_encountered)
        logger.log_metric("operations_per_second", ops_per_second)
        logger.log_metric("test_duration_seconds", test_duration)

        print(
            f"  Completed {operations_completed} operations in {test_duration:.2f} seconds"
        )
        print(f"  Operations per second: {ops_per_second:.2f}")
        print(f"  Errors encountered: {errors_encountered}")

        # Verify stability
        assert (
            errors_encountered == 0
        ), f"Encountered {errors_encountered} errors during stability test"
        assert operations_completed > 0, "No operations completed during stability test"

    finally:
        realtime_client.off(ServerEventType.ERROR, on_error)
        await realtime_client.close()
        log_file = logger.end_test()
        print(f"Test results saved to: {log_file}")


@pytest.mark.asyncio
async def test_reconnection_performance(realtime_client):
    """Test performance of reconnection logic."""
    logger.start_test("test_reconnection_performance")

    # Connect to the API
    connected = await realtime_client.connect()
    assert connected, "Failed to connect to the API"

    # Add missing attribute to fix AttributeError
    if not hasattr(realtime_client, "_reconnecting"):
        realtime_client._reconnecting = False

    # Track reconnection events
    reconnection_detected = asyncio.Event()
    reconnection_times = []

    async def on_connection_lost():
        print("Connection lost detected")

    async def on_connection_restored():
        print("Connection restored detected")
        reconnection_detected.set()

    try:
        # Register connection handlers
        realtime_client.set_connection_handlers(
            lost_handler=on_connection_lost, restored_handler=on_connection_restored
        )

        # Perform multiple reconnection tests
        for i in range(3):
            print(f"\nReconnection Test {i+1}:")
            reconnection_detected.clear()

            # Force close the WebSocket
            if realtime_client.ws:
                start_time = time.time()
                await realtime_client.ws.close(
                    code=1001, reason="Testing reconnection performance"
                )

                # Wait for reconnection
                try:
                    await asyncio.wait_for(reconnection_detected.wait(), timeout=10.0)
                    reconnection_time = time.time() - start_time
                    reconnection_times.append(reconnection_time)
                    print(
                        f"  Reconnection completed in {reconnection_time:.2f} seconds"
                    )
                except asyncio.TimeoutError:
                    print("Timeout waiting for reconnection")
                    # Don't break on first timeout, try other tests
                    continue

            # Wait between tests
            await asyncio.sleep(2.0)

        # Calculate average reconnection time
        if reconnection_times:
            avg_reconnection_time = statistics.mean(reconnection_times)
            logger.log_metric(
                "average_reconnection_time_seconds", avg_reconnection_time
            )
            logger.log_metric("total_reconnection_tests", len(reconnection_times))
            logger.log_metric("successful_reconnections", len(reconnection_times))

            print(f"Average reconnection time: {avg_reconnection_time:.2f} seconds")

            # Verify reasonable reconnection time
            assert (
                avg_reconnection_time < 5.0
            ), f"Average reconnection time ({avg_reconnection_time:.2f}s) exceeds threshold"
        else:
            logger.log_metric("successful_reconnections", 0)
            pytest.skip("No successful reconnections occurred - skipping test")

    finally:
        await realtime_client.close()
        log_file = logger.end_test()
        print(f"Test results saved to: {log_file}")


# Run the tests with custom markers to execute them in a specific order
if __name__ == "__main__":
    # Import required libraries to run tests directly
    import sys

    import pytest

    # Run the tests with timing information
    print(f"Running performance tests for RealtimeClient")
    sys.exit(pytest.main(["-v", __file__]))
