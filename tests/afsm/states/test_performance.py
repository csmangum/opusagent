import asyncio
import time
import unittest

import pytest

from app.afsm.states import AFSMState, StateManager, StateTransition


class FastMockState(AFSMState):
    """A very fast mock state for performance testing"""

    def __init__(self, name, transitions=None):
        super().__init__(
            name=name,
            description=f"Fast mock state {name}",
            allowed_transitions=transitions or [],
        )

    async def process(self, input_text, context):
        # Just return immediately with no processing
        return f"Response from {self.name}", None, {}


class SlowMockState(AFSMState):
    """A deliberately slow mock state for performance testing"""

    def __init__(self, name, delay_ms=50, transitions=None):
        super().__init__(
            name=name,
            description=f"Slow mock state {name} with {delay_ms}ms delay",
            allowed_transitions=transitions or [],
        )
        self.delay_seconds = delay_ms / 1000

    async def process(self, input_text, context):
        # Simulate some processing time
        await asyncio.sleep(self.delay_seconds)
        return f"Response from {self.name} after {self.delay_seconds}s", None, {}


class TestStatePerformance(unittest.TestCase):
    """Performance tests for the State system"""

    def setUp(self):
        """Set up the state manager with test states"""
        self.manager = StateManager("start")

        # Create a network of states for testing
        states = []

        # Create 10 fast states with transitions between them
        for i in range(10):
            name = f"fast_{i}"
            # Each state can transition to the next (cycling back to 0 at the end)
            transitions = [StateTransition(target_state=f"fast_{(i+1) % 10}")]
            states.append(FastMockState(name, transitions))

        # Create 5 slow states with varying delays
        for i in range(5):
            name = f"slow_{i}"
            # Each slow state gets progressively slower
            delay = 10 * (i + 1)  # 10ms, 20ms, 30ms, etc.
            transitions = [StateTransition(target_state=f"slow_{(i+1) % 5}")]
            states.append(SlowMockState(name, delay, transitions))

        # Register all states
        self.manager.register_states(states)

        # Initialize context
        self.manager.initialize_context("perf_test_session")

    @pytest.mark.asyncio
    async def test_fast_state_processing_time(self):
        """Test the processing time of fast states"""
        self.manager.current_state_name = "fast_0"

        # Measure time for a single process
        start_time = time.time()
        await self.manager.process_input("test")
        elapsed = time.time() - start_time

        # Fast state should process very quickly
        self.assertLess(elapsed, 0.01)  # Less than 10ms

        # Measure time for 100 sequential processes
        start_time = time.time()
        for _ in range(100):
            await self.manager.process_input("test")
        elapsed = time.time() - start_time

        # 100 fast processes should still be relatively quick
        self.assertLess(elapsed, 0.5)  # Less than 500ms for 100 iterations
        print(
            f"100 fast state processes took {elapsed:.3f} seconds ({elapsed*10:.1f}ms per process)"
        )

    @pytest.mark.asyncio
    async def test_slow_state_processing_time(self):
        """Test the processing time of slow states with artificial delays"""
        self.manager.current_state_name = "slow_0"

        # Process once to establish baseline
        start_time = time.time()
        await self.manager.process_input("test")
        elapsed = time.time() - start_time

        # Should be approximately the delay time (10ms) plus minimal overhead
        self.assertGreater(
            elapsed, 0.008
        )  # At least 8ms (allowing for slight timing variations)
        self.assertLess(elapsed, 0.030)  # Not more than 30ms (10ms delay + overhead)

        # Try the slowest state
        self.manager.current_state_name = "slow_4"

        start_time = time.time()
        await self.manager.process_input("test")
        elapsed = time.time() - start_time

        # Should be approximately the delay time (50ms) plus minimal overhead
        self.assertGreater(elapsed, 0.045)  # At least 45ms
        self.assertLess(elapsed, 0.080)  # Not more than 80ms (50ms delay + overhead)
        print(f"Slow state process (50ms delay) took {elapsed:.3f} seconds")

    @pytest.mark.asyncio
    async def test_state_transition_chain_performance(self):
        """Test the performance of a chain of state transitions"""
        # Create a state that forces a transition to the next
        transitions = []
        for i in range(20):
            transitions.append(StateTransition(target_state=f"chain_{i+1}"))
            self.manager.register_state(
                FastMockState(
                    f"chain_{i}", [StateTransition(target_state=f"chain_{i+1}")]
                )
            )

        # Add the final state
        self.manager.register_state(FastMockState(f"chain_20", []))

        # Set up a special first state that will immediately transition
        first_state = FastMockState(
            "chain_start", [StateTransition(target_state="chain_0")]
        )
        first_state.process = lambda input_text, context: ("Start", "chain_0", {})
        self.manager.register_state(first_state)

        # Measure the time to process through the entire chain
        self.manager.current_state_name = "chain_start"

        start_time = time.time()
        # This should trigger a cascade of 20 transitions
        response = await self.manager.process_input("trigger chain")
        elapsed = time.time() - start_time

        # Verify we ended up at the final state
        self.assertEqual(self.manager.current_state_name, "chain_0")

        # The chain should be relatively fast
        self.assertLess(elapsed, 0.2)  # Less than 200ms for the entire chain
        print(
            f"Chain of 20 state transitions took {elapsed:.3f} seconds ({(elapsed*1000)/20:.2f}ms per transition)"
        )

    @pytest.mark.asyncio
    async def test_concurrent_state_processes(self):
        """Test performance with many concurrent state processes"""
        # Register 5 workers states with different delays
        for i in range(5):
            name = f"worker_{i}"
            delay = 10 * (i + 1)  # 10ms to 50ms delays
            self.manager.register_state(SlowMockState(name, delay))

        # Process 50 inputs concurrently across the 5 worker states
        tasks = []
        for i in range(50):
            # Distribute tasks evenly among the worker states
            self.manager.current_state_name = f"worker_{i % 5}"
            tasks.append(self.manager.process_input(f"concurrent input {i}"))

        start_time = time.time()
        # Run all tasks concurrently
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time

        # Check that we got all the expected results
        self.assertEqual(len(results), 50)

        # The time should be dominated by the slowest worker (50ms)
        # but significantly less than sequential execution (50 * avg_delay = 50 * 30ms = 1.5s)
        self.assertLess(elapsed, 0.2)  # Should take less than 200ms total
        print(f"50 concurrent processes took {elapsed:.3f} seconds")


# Fixture for async tests
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
