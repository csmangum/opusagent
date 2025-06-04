"""
Function call handler for the OpenAI Realtime API integration.

This module provides a centralized handler for managing function calls from the OpenAI Realtime API,
including accumulating streaming function arguments, executing functions, and sending results back.
This design separates function call logic from the main bridge implementation for better modularity
and testability.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional

from fastagent.config.constants import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


class FunctionHandler:
    """
    Handles function call events from the OpenAI Realtime API.

    This class manages:
    - A registry of available functions
    - Accumulation of streaming function call arguments
    - Execution of functions (sync/async)
    - Sending results back to the OpenAI Realtime API

    Attributes:
        function_registry: Dictionary mapping function names to callable implementations
        active_function_calls: Dictionary tracking ongoing function calls by call_id
        realtime_websocket: WebSocket connection to OpenAI Realtime API for sending responses
    """

    def __init__(self, realtime_websocket):
        """
        Initialize the function handler.

        Args:
            realtime_websocket: WebSocket connection to OpenAI Realtime API
        """
        self.realtime_websocket = realtime_websocket
        self.function_registry: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self.active_function_calls: Dict[str, Dict[str, Any]] = (
            {}
        )  # call_id -> {function_name, arguments_buffer, item_id, etc.}

        # Register default functions
        self._register_default_functions()

    def _register_default_functions(self):
        """Register the default function implementations."""
        self.register_function("get_balance", self._func_get_balance)
        self.register_function("transfer_funds", self._func_transfer_funds)
        self.register_function("call_intent", self._func_call_intent)

    def register_function(
        self, name: str, func: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """
        Register a function in the function registry.

        Args:
            name: The name of the function as it will be called by OpenAI
            func: The callable function implementation (can be sync or async)
        """
        self.function_registry[name] = func
        logger.info(f"Registered function: {name}")

    def unregister_function(self, name: str) -> bool:
        """
        Unregister a function from the registry.

        Args:
            name: The name of the function to remove

        Returns:
            True if function was removed, False if it didn't exist
        """
        if name in self.function_registry:
            del self.function_registry[name]
            logger.info(f"Unregistered function: {name}")
            return True
        return False

    def get_registered_functions(self) -> list[str]:
        """
        Get a list of all registered function names.

        Returns:
            List of function names
        """
        return list(self.function_registry.keys())

    async def handle_function_call(self, response_dict: Dict[str, Any]) -> None:
        """
        Handle function call event from OpenAI (out-of-band).

        Args:
            response_dict: The function call event data from OpenAI
        """
        logger.info(f"Function call event received: {response_dict}")

        try:
            # Arguments are a JSON string
            arguments_str = response_dict.get("arguments", "{}")
            call_id = response_dict.get("call_id")
            item_id = response_dict.get("item_id")
            output_index = response_dict.get("output_index")
            response_id = response_dict.get("response_id")

            # The function name is typically in the parent response or item, but for demo, assume it's in arguments
            # You may need to adjust this based on your OpenAI payloads
            args = json.loads(arguments_str)
            function_name = (
                args.get("function_name") or args.get("name") or args.get("tool_name")
            )
            if not function_name:
                logger.error(f"No function name found in arguments: {arguments_str}")
                return

            logger.info(f"Dispatching function: {function_name} with args: {args}")

            # Run function out-of-band
            asyncio.create_task(
                self._execute_and_respond_to_function(
                    function_name, args, call_id, item_id, output_index, response_id
                )
            )
        except Exception as e:
            logger.error(f"Error parsing function call: {e}")

    async def handle_function_call_arguments_delta(
        self, response_dict: Dict[str, Any]
    ) -> None:
        """
        Handle function call arguments delta events from OpenAI.

        These events contain incremental pieces of the function call arguments
        that need to be accumulated until the function call is complete.

        Args:
            response_dict: The function call arguments delta event data
        """
        call_id = response_dict.get("call_id")
        delta = response_dict.get("delta", "")
        item_id = response_dict.get("item_id")
        output_index = response_dict.get("output_index", 0)
        response_id = response_dict.get("response_id")

        if not call_id:
            logger.warning(
                f"Function call delta received without call_id: {response_dict}"
            )
            return

        # Initialize or update the function call state
        if call_id not in self.active_function_calls:
            self.active_function_calls[call_id] = {
                "arguments_buffer": "",
                "item_id": item_id,
                "output_index": output_index,
                "response_id": response_id,
                "function_name": None,  # Will be determined from the arguments
            }

        # Accumulate the arguments
        self.active_function_calls[call_id]["arguments_buffer"] += delta

        logger.debug(
            f"Function call arguments delta for {call_id}: '{delta}' (total: {len(self.active_function_calls[call_id]['arguments_buffer'])} chars)"
        )

    async def handle_function_call_arguments_done(
        self, response_dict: Dict[str, Any]
    ) -> None:
        """
        Handle function call arguments completion events from OpenAI.

        This event indicates that all arguments for a function call have been received
        and the function can now be executed.

        Args:
            response_dict: The function call arguments done event data
        """
        logger.info(f"🔧 FUNCTION CALL ARGUMENTS DONE HANDLER CALLED")
        logger.info(f"🔧 Full response_dict: {response_dict}")

        call_id = response_dict.get("call_id")
        final_arguments = response_dict.get("arguments", "")
        item_id = response_dict.get("item_id")
        output_index = response_dict.get("output_index", 0)
        response_id = response_dict.get("response_id")

        logger.info(f"🔧 Extracted values:")
        logger.info(f"   call_id: {call_id}")
        logger.info(f"   final_arguments: {final_arguments}")
        logger.info(f"   item_id: {item_id}")
        logger.info(f"   output_index: {output_index}")
        logger.info(f"   response_id: {response_id}")

        if not call_id:
            logger.warning(
                f"🚨 Function call done received without call_id: {response_dict}"
            )
            return

        logger.info(
            f"🔧 Active function calls: {list(self.active_function_calls.keys())}"
        )

        # Use the final arguments from the done event, or fall back to accumulated buffer
        if final_arguments:
            arguments_str = final_arguments
            logger.info(f"🔧 Using final_arguments from done event: {arguments_str}")
        elif call_id in self.active_function_calls:
            arguments_str = self.active_function_calls[call_id]["arguments_buffer"]
            logger.info(f"🔧 Using accumulated buffer: {arguments_str}")
        else:
            logger.error(f"🚨 Function call done for unknown call_id: {call_id}")
            logger.error(
                f"🚨 Known call_ids: {list(self.active_function_calls.keys())}"
            )
            return

        logger.info(
            f"🔧 Function call arguments complete for {call_id}: {arguments_str}"
        )

        try:
            # Parse the JSON arguments
            args = json.loads(arguments_str) if arguments_str else {}
            logger.info(f"🔧 Parsed arguments: {args}")

            # Get the function name from the captured function call state
            function_name = None
            if call_id in self.active_function_calls:
                function_name = self.active_function_calls[call_id].get("function_name")
                logger.info(f"🔧 Found function_name in active calls: {function_name}")
            else:
                logger.error(f"🚨 call_id {call_id} not found in active_function_calls")

            if not function_name:
                logger.error(f"🚨 No function name found for call_id: {call_id}")
                logger.error(f"🚨 Arguments string: {arguments_str}")
                logger.error(
                    f"🚨 Active function calls state: {self.active_function_calls}"
                )
                # Clean up the active function call
                if call_id in self.active_function_calls:
                    del self.active_function_calls[call_id]
                return

            logger.info(f"🚀 Executing function: {function_name} with args: {args}")

            # Execute the function
            asyncio.create_task(
                self._execute_and_respond_to_function(
                    function_name, args, call_id, item_id, output_index, response_id
                )
            )
            logger.info(f"🚀 Function execution task created for {function_name}")

        except json.JSONDecodeError as e:
            logger.error(f"🚨 Failed to parse function arguments JSON: {e}")
            logger.error(f"🚨 Arguments string: {arguments_str}")
        except Exception as e:
            logger.error(f"🚨 Error processing function call: {e}")
            import traceback

            logger.error(f"🚨 Traceback: {traceback.format_exc()}")
        finally:
            # Clean up the active function call
            if call_id in self.active_function_calls:
                logger.info(f"🔧 Cleaning up active function call for {call_id}")
                del self.active_function_calls[call_id]

    async def _execute_and_respond_to_function(
        self,
        function_name: str,
        arguments: Dict[str, Any],
        call_id: str,
        item_id: str,
        output_index: int,
        response_id: str,
    ) -> None:
        """
        Execute a function and send the result back to OpenAI.

        Args:
            function_name: Name of the function to execute
            arguments: Function arguments
            call_id: Unique call identifier
            item_id: Item identifier
            output_index: Output index
            response_id: Response identifier
        """
        logger.info(f"🔥 _execute_and_respond_to_function called:")
        logger.info(f"   function_name: {function_name}")
        logger.info(f"   arguments: {arguments}")
        logger.info(f"   call_id: {call_id}")
        logger.info(f"   item_id: {item_id}")
        logger.info(f"   output_index: {output_index}")
        logger.info(f"   response_id: {response_id}")

        # Execute the function
        try:
            logger.info(f"🔥 Looking up function '{function_name}' in registry...")
            logger.info(
                f"🔥 Available functions: {list(self.function_registry.keys())}"
            )

            func = self.function_registry.get(function_name)
            if not func:
                logger.error(f"🚨 Function '{function_name}' not implemented.")
                raise NotImplementedError(
                    f"Function '{function_name}' not implemented."
                )

            logger.info(f"🔥 Found function '{function_name}', executing...")

            result = (
                await func(arguments)
                if asyncio.iscoroutinefunction(func)
                else func(arguments)
            )
            logger.info(f"✅ Function {function_name} executed successfully: {result}")
        except Exception as e:
            logger.error(f"🚨 Function execution failed: {e}")
            import traceback

            logger.error(f"🚨 Function execution traceback: {traceback.format_exc()}")
            result = {"error": str(e)}

        # Send result back to OpenAI as a conversation item
        function_result_event = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result),
            },
        }
        logger.info(f"📤 Sending function result for {function_name}: {result}")
        logger.info(
            f"📤 Function result event: {json.dumps(function_result_event, indent=2)}"
        )

        try:
            await self.realtime_websocket.send(json.dumps(function_result_event))
            logger.info(f"✅ Function result sent successfully to OpenAI")

            # After sending function result, trigger response generation
            # This ensures the AI continues the conversation
            logger.info("🚀 Triggering response generation after function execution...")
            response_create = {
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"],
                    "output_audio_format": "pcm16",
                    "temperature": 0.8,
                    "max_output_tokens": 4096,
                    "voice": "alloy",  # TODO: Make this configurable
                },
            }
            await self.realtime_websocket.send(json.dumps(response_create))
            logger.info("✅ Response generation triggered successfully")

        except Exception as e:
            logger.error(f"🚨 Failed to send function result or trigger response: {e}")
            import traceback

            logger.error(f"🚨 Send result traceback: {traceback.format_exc()}")

    def clear_active_function_calls(self) -> None:
        """Clear all active function call state."""
        self.active_function_calls.clear()
        logger.info("Cleared all active function calls")

    def get_active_function_calls(self) -> Dict[str, Dict[str, Any]]:
        """
        Get a copy of the active function calls state.

        Returns:
            Dictionary of active function calls
        """
        return self.active_function_calls.copy()

    # Default function implementations
    def _func_get_balance(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate a balance lookup.

        Args:
            arguments: Function arguments (unused for this example)

        Returns:
            Simulated balance information
        """
        return {"balance": 1234.56, "currency": "USD"}

    def _func_transfer_funds(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate a fund transfer.

        Args:
            arguments: Function arguments containing amount and to_account

        Returns:
            Transfer status information
        """
        amount = arguments.get("amount", 0)
        to_account = arguments.get("to_account", "unknown")
        return {"status": "success", "amount": amount, "to_account": to_account}

    def _func_call_intent(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user intent identification.

        Args:
            arguments: Function arguments containing intent

        Returns:
            Intent processing results with guidance for next actions
        """
        intent = arguments.get("intent", "")
        if intent == "card_replacement":
            logger.info(
                f"!!!!!!!!!!!!!!!!! Function call intent received: {arguments} !!!!!!!!!!!!!"
            )
            # Return data that guides the AI's next response
            return {
                "status": "success",
                "intent": intent,
                "next_action": "ask_card_type",
                "available_cards": ["Gold card", "Silver card", "Basic card"],
                "prompt_guidance": "Ask the customer which type of card they need to replace: Gold card, Silver card, or Basic card.",
            }
        else:
            return {
                "status": "success",
                "intent": intent,
                "next_action": "continue_conversation",
            }
