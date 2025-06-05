import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from opusagent.function_handler import FunctionHandler


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    return AsyncMock()


@pytest.fixture
def function_handler(mock_websocket):
    """Create a FunctionHandler instance with a mock WebSocket."""
    return FunctionHandler(mock_websocket)


def test_initialization(function_handler, mock_websocket):
    """Test that FunctionHandler initializes correctly."""
    assert function_handler.realtime_websocket == mock_websocket
    assert isinstance(function_handler.function_registry, dict)
    assert isinstance(function_handler.active_function_calls, dict)
    assert "get_balance" in function_handler.function_registry
    assert "transfer_funds" in function_handler.function_registry
    assert "call_intent" in function_handler.function_registry


def test_register_function(function_handler):
    """Test registering a new function."""

    def test_func(args):
        return {"result": "test"}

    function_handler.register_function("test_func", test_func)
    assert "test_func" in function_handler.function_registry
    assert function_handler.function_registry["test_func"] == test_func


def test_unregister_function(function_handler):
    """Test unregistering a function."""

    # First register a function
    def test_func(args):
        return {"result": "test"}

    function_handler.register_function("test_func", test_func)

    # Test successful unregistration
    assert function_handler.unregister_function("test_func") is True
    assert "test_func" not in function_handler.function_registry

    # Test unregistering non-existent function
    assert function_handler.unregister_function("non_existent") is False


def test_get_registered_functions(function_handler):
    """Test getting list of registered functions."""
    functions = function_handler.get_registered_functions()
    assert isinstance(functions, list)
    assert "get_balance" in functions
    assert "transfer_funds" in functions
    assert "call_intent" in functions


@pytest.mark.asyncio
async def test_handle_function_call(function_handler):
    """Test handling a function call event."""
    test_args = {
        "arguments": json.dumps({"function_name": "get_balance", "account_id": "123"}),
        "call_id": "test_call_1",
        "item_id": "test_item_1",
        "output_index": 0,
        "response_id": "test_response_1",
    }

    await function_handler.handle_function_call(test_args)

    # Verify that the function execution task was created
    # Note: We can't directly test the task execution since it's created asynchronously
    assert len(function_handler.active_function_calls) == 0


@pytest.mark.asyncio
async def test_handle_function_call_arguments_delta(function_handler):
    """Test handling function call arguments delta events."""
    # First delta
    delta1 = {
        "call_id": "test_call_1",
        "delta": '{"function_name": "get_balance", "account_id": "',
        "item_id": "test_item_1",
        "output_index": 0,
        "response_id": "test_response_1",
    }
    await function_handler.handle_function_call_arguments_delta(delta1)

    # Second delta
    delta2 = {
        "call_id": "test_call_1",
        "delta": '123"}',
        "item_id": "test_item_1",
        "output_index": 0,
        "response_id": "test_response_1",
    }
    await function_handler.handle_function_call_arguments_delta(delta2)

    # Verify the arguments were accumulated correctly
    assert "test_call_1" in function_handler.active_function_calls
    accumulated = function_handler.active_function_calls["test_call_1"][
        "arguments_buffer"
    ]
    assert accumulated == '{"function_name": "get_balance", "account_id": "123"}'


@pytest.mark.asyncio
async def test_handle_function_call_arguments_done(function_handler):
    """Test handling function call arguments completion."""
    # First set up some accumulated arguments
    call_id = "test_call_1"
    function_handler.active_function_calls[call_id] = {
        "arguments_buffer": '{"function_name": "get_balance", "account_id": "123"}',
        "item_id": "test_item_1",
        "output_index": 0,
        "response_id": "test_response_1",
        "function_name": "get_balance",
    }

    # Send the done event
    done_event = {
        "call_id": call_id,
        "item_id": "test_item_1",
        "output_index": 0,
        "response_id": "test_response_1",
    }

    await function_handler.handle_function_call_arguments_done(done_event)

    # Verify the function execution task was created
    # Note: We can't directly test the task execution since it's created asynchronously
    assert len(function_handler.active_function_calls) == 0


def test_clear_active_function_calls(function_handler):
    """Test clearing active function calls."""
    # Add some test data
    function_handler.active_function_calls["test_call_1"] = {"data": "test"}
    function_handler.active_function_calls["test_call_2"] = {"data": "test"}

    function_handler.clear_active_function_calls()
    assert len(function_handler.active_function_calls) == 0


def test_get_active_function_calls(function_handler):
    """Test getting active function calls."""
    # Add some test data
    test_data = {"test_call_1": {"data": "test"}}
    function_handler.active_function_calls = test_data.copy()

    active_calls = function_handler.get_active_function_calls()
    assert active_calls == test_data


def test_default_functions(function_handler):
    """Test the default function implementations."""
    # Test get_balance
    balance_result = function_handler._func_get_balance({"account_id": "123"})
    assert isinstance(balance_result, dict)
    assert "balance" in balance_result

    # Test transfer_funds
    transfer_result = function_handler._func_transfer_funds(
        {"from_account": "123", "to_account": "456", "amount": 100}
    )
    assert isinstance(transfer_result, dict)
    assert "status" in transfer_result
    assert transfer_result["status"] == "success"

    # Test call_intent
    intent_result = function_handler._func_call_intent(
        {"intent": "test_intent", "parameters": {"param1": "value1"}}
    )
    assert isinstance(intent_result, dict)
    assert "status" in intent_result
    assert intent_result["status"] == "success"
