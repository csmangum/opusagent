"""
Function Call Handler for OpenAI Realtime API Integration

This module provides a comprehensive function call management system for OpenAI's Realtime API,
enabling seamless integration between AI conversations and backend function execution. The handler
manages the complete lifecycle of function calls including streaming argument accumulation,
function execution, and response delivery.

Architecture Overview:
    The FunctionHandler class serves as the central orchestrator for all function call operations,
    providing a clean separation between conversation flow and business logic. It handles both
    synchronous and asynchronous function execution while maintaining state for streaming calls.

Key Features:
    - **Streaming Support**: Accumulates function arguments delivered across multiple delta events
    - **Function Registry**: Dynamic registration/unregistration of callable functions
    - **Async/Sync Compatibility**: Supports both synchronous and asynchronous function implementations
    - **Error Handling**: Comprehensive error handling with detailed logging for debugging
    - **Response Management**: Automatic response generation triggering after function execution
    - **State Management**: Tracks active function calls and manages cleanup

Supported Function Flows:
    1. **Card Replacement Flow**: Complete end-to-end card replacement process
       - Member account confirmation
       - Replacement reason collection
       - Address verification
       - Replacement processing and completion

    2. **Loan Application Flow**: Comprehensive loan application processing
       - Loan type selection and information
       - Amount collection with type-specific guidance
       - Income and employment verification
       - Credit check consent and application submission
       - Pre-approval processing

    3. **Banking Operations**: Basic banking function simulations
       - Balance inquiries
       - Fund transfers
       - Intent classification

Usage Example:
    ```python
    # Initialize handler with WebSocket connection
    handler = FunctionHandler(realtime_websocket)

    # Register custom function
    def my_custom_function(args):
        return {"status": "success", "data": args}

    handler.register_function("my_function", my_custom_function)

    # Handle incoming function call events
    await handler.handle_function_call_arguments_delta(delta_event)
    await handler.handle_function_call_arguments_done(done_event)
    ```

Event Processing Workflow:
    1. **Delta Events**: Incremental argument data is accumulated in active_function_calls
    2. **Done Events**: Complete arguments trigger function lookup and execution
    3. **Function Execution**: Registered functions are called with parsed arguments
    4. **Result Delivery**: Function results are sent back to OpenAI via WebSocket
    5. **Response Generation**: AI response generation is automatically triggered
    6. **Cleanup**: Function call state is cleaned up after completion

Dependencies:
    - asyncio: For asynchronous function execution and task management
    - json: For argument parsing and result serialization
    - logging: For comprehensive operation logging
    - uuid: For generating unique identifiers
    - OpenAI Realtime API: For WebSocket communication

Thread Safety:
    This module is designed for use in asyncio environments and maintains thread-safe
    operation through proper async/await patterns and state management.

Note:
    Function implementations should follow the pattern of accepting a dictionary of
    arguments and returning a dictionary result. The handler automatically manages
    JSON serialization/deserialization for OpenAI API compatibility.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Callable, Dict, Optional

from opusagent.config.logging_config import configure_logging

logger = configure_logging("function_handler")


class FunctionHandler:
    """
    Handles function call events from the OpenAI Realtime API.

    This class manages:
    - A registry of available functions
    - Accumulation of streaming function call arguments
    - Execution of functions (sync/async)
    - Sending results back to the OpenAI Realtime API
    - Detection of hang-up conditions and session termination

    Attributes:
        function_registry: Dictionary mapping function names to callable implementations
        active_function_calls: Dictionary tracking ongoing function calls by call_id
        realtime_websocket: WebSocket connection to OpenAI Realtime API for sending responses
        hang_up_callback: Optional callback function to trigger hang-up from bridge
    """

    def __init__(
        self,
        realtime_websocket,
        call_recorder=None,
        voice="verse",
        hang_up_callback=None,
    ):
        """
        Initialize the function handler.

        Args:
            realtime_websocket: WebSocket connection to OpenAI Realtime API
            call_recorder: Optional CallRecorder instance for logging function calls
            voice: Voice to use for responses
            hang_up_callback: Optional callback to trigger hang-up from bridge
        """
        self.realtime_websocket = realtime_websocket
        self.call_recorder = call_recorder
        self.hang_up_callback = hang_up_callback
        self.function_registry: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self.active_function_calls: Dict[str, Dict[str, Any]] = (
            {}
        )  # call_id -> {function_name, arguments_buffer, item_id, etc.}
        self.voice = voice
        # Note: Functions should be registered by specific agents using register_function()

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
        call_id: Optional[str] = None,
        item_id: Optional[str] = None,
        output_index: Optional[int] = 0,
        response_id: Optional[str] = None,
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

            # Log function call to call recorder if available
            if self.call_recorder:
                try:
                    await self.call_recorder.log_function_call(
                        function_name=function_name,
                        arguments=arguments,
                        result=result,
                        call_id=call_id,
                    )
                except Exception as e:
                    logger.error(f"Error logging function call to recorder: {e}")

        except Exception as e:
            logger.error(f"🚨 Function execution failed: {e}")
            import traceback

            logger.error(f"🚨 Function execution traceback: {traceback.format_exc()}")
            result = {"error": str(e)}

            # Log failed function call to call recorder if available
            if self.call_recorder:
                try:
                    await self.call_recorder.log_function_call(
                        function_name=function_name,
                        arguments=arguments,
                        result=result,
                        call_id=call_id,
                    )
                except Exception as e:
                    logger.error(f"Error logging failed function call to recorder: {e}")

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

            # Check if this function indicates the call should end
            should_hang_up = self._should_trigger_hang_up(function_name, result)

            if should_hang_up:
                logger.info(f"🔚 Function {function_name} indicates call should end")
                # Schedule hang-up after a brief delay to allow final response
                asyncio.create_task(self._schedule_hang_up(result))
            else:
                # After sending function result, trigger response generation
                # This ensures the AI continues the conversation
                logger.info(
                    "🚀 Triggering response generation after function execution..."
                )
                response_create = {
                    "type": "response.create",
                    "response": {
                        "modalities": ["text", "audio"],
                        "output_audio_format": "pcm16",
                        "temperature": 0.8,
                        "max_output_tokens": 4096,
                        "voice": self.voice,
                    },
                }
                await self.realtime_websocket.send(json.dumps(response_create))
                logger.info("✅ Response generation triggered successfully")

        except Exception as e:
            logger.error(f"❌ Error sending function result: {e}")
            raise

    def _should_trigger_hang_up(
        self, function_name: str, result: Dict[str, Any]
    ) -> bool:
        """
        Determine if a function result indicates the call should be ended.

        Args:
            function_name: Name of the function that was executed
            result: The result returned by the function

        Returns:
            True if the call should be ended, False otherwise
        """
        # Check if the function explicitly indicates call should end
        next_action = result.get("next_action", "")
        if next_action == "end_call":
            logger.info(f"Function {function_name} returned next_action: end_call")
            return True

        # Check for specific functions that typically end calls
        end_call_functions = ["wrap_up", "transfer_to_human"]
        if function_name in end_call_functions:
            logger.info(f"Function {function_name} is a call-ending function")
            return True

        # Check if the result context indicates call completion
        context = result.get("context", {})
        stage = context.get("stage", "")
        if stage in ["call_complete", "human_transfer"]:
            logger.info(f"Function {function_name} reached completion stage: {stage}")
            return True

        return False

    async def _schedule_hang_up(self, result: Dict[str, Any]):
        """
        Schedule a hang-up after allowing time for the final AI response.

        Args:
            result: The function result that triggered the hang-up
        """
        try:
            # Give the AI time to generate and play its final response
            hang_up_delay = 8.0  # 8 seconds should be enough for most responses
            logger.info(f"⏰ Scheduling hang-up in {hang_up_delay} seconds...")

            await asyncio.sleep(hang_up_delay)

            # Determine hang-up reason from the function result
            reason = self._get_hang_up_reason(result)

            if self.hang_up_callback:
                logger.info(f"🔚 Triggering hang-up: {reason}")
                await self.hang_up_callback(reason)
            else:
                logger.warning("🚨 No hang-up callback available - cannot end call")

        except Exception as e:
            logger.error(f"❌ Error scheduling hang-up: {e}")

    def _get_hang_up_reason(self, result: Dict[str, Any]) -> str:
        """
        Determine the appropriate hang-up reason from function result.

        Args:
            result: The function result that triggered the hang-up

        Returns:
            A descriptive reason for the hang-up
        """
        function_name = result.get("function_name", "unknown")
        context = result.get("context", {})
        stage = context.get("stage", "")

        if function_name == "wrap_up" or stage == "call_complete":
            return "Call completed successfully - all tasks finished"
        elif function_name == "transfer_to_human" or stage == "human_transfer":
            transfer_id = result.get("transfer_id", "")
            return f"Transferred to human agent - Reference: {transfer_id}"
        else:
            return f"Call ended after {function_name} completion"

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
