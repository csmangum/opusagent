"""
Tests for the FlowIntegrationExample class.
"""

import pytest
from typing import Dict, List
from unittest.mock import MagicMock

from opusagent.flows.integration_example import FlowIntegrationExample


class MockWebSocket:
    """Mock WebSocket for testing."""
    def __init__(self):
        self.sent_messages = []
    
    async def send(self, message):
        self.sent_messages.append(message)


@pytest.fixture
def mock_realtime_websocket():
    """Fixture providing a mock realtime WebSocket."""
    return MockWebSocket()


@pytest.fixture
def flow_integration(mock_realtime_websocket):
    """Fixture providing a FlowIntegrationExample instance."""
    return FlowIntegrationExample(mock_realtime_websocket)


def test_flow_integration_initialization(mock_realtime_websocket):
    """Test that FlowIntegrationExample initializes correctly."""
    integration = FlowIntegrationExample(mock_realtime_websocket)
    assert integration.realtime_websocket == mock_realtime_websocket
    assert integration.flow_manager is not None
    assert integration.function_handler is not None


def test_setup_flows_default(flow_integration):
    """Test setup_flows with default flow."""
    flow_integration.setup_flows()
    assert "card_replacement" in flow_integration.flow_manager.active_flows


def test_setup_flows_custom(flow_integration):
    """Test setup_flows with custom flows."""
    flow_integration.setup_flows(["card_replacement", "loan_application"])
    assert "card_replacement" in flow_integration.flow_manager.active_flows
    assert "loan_application" in flow_integration.flow_manager.active_flows


def test_setup_flows_invalid(flow_integration):
    """Test setup_flows with invalid flow."""
    flow_integration.setup_flows(["invalid_flow"])
    assert "invalid_flow" not in flow_integration.flow_manager.active_flows


def test_get_session_config(flow_integration):
    """Test that get_session_config returns correct configuration."""
    flow_integration.setup_flows()
    config = flow_integration.get_session_config()
    
    assert isinstance(config, dict)
    assert "tools" in config
    assert "instructions" in config
    assert "input_audio_format" in config
    assert "output_audio_format" in config
    assert "voice" in config
    assert "modalities" in config
    assert "temperature" in config
    assert "input_audio_noise_reduction" in config
    assert "input_audio_transcription" in config
    assert "max_response_output_tokens" in config
    assert "tool_choice" in config


def test_switch_flow(flow_integration):
    """Test switching between flows."""
    # Setup initial flow
    flow_integration.setup_flows(["card_replacement"])
    assert "card_replacement" in flow_integration.flow_manager.active_flows
    
    # Switch to new flow
    flow_integration.switch_flow("loan_application")
    assert "card_replacement" not in flow_integration.flow_manager.active_flows
    assert "loan_application" in flow_integration.flow_manager.active_flows


def test_get_flow_status(flow_integration):
    """Test that get_flow_status returns correct information."""
    flow_integration.setup_flows()
    status = flow_integration.get_flow_status()
    
    assert isinstance(status, dict)
    assert "active_flows" in status
    assert "total_tools" in status
    assert "total_functions" in status
    assert "flow_info" in status


@pytest.mark.asyncio
async def test_telephony_bridge_modification():
    """Test the example telephony bridge modification."""
    from opusagent.flows.integration_example import modify_telephony_bridge_for_flows
    
    # This is just a demonstration of the modification
    # In a real test, we would need to mock the TelephonyRealtimeBridge
    modify_telephony_bridge_for_flows()
    
    # The function should not raise any exceptions
    assert True


def test_example_usage():
    """Test the example usage function."""
    from opusagent.flows.integration_example import example_usage
    
    # This is just a demonstration of the usage
    # In a real test, we would need to capture and verify the output
    example_usage()
    
    # The function should not raise any exceptions
    assert True 