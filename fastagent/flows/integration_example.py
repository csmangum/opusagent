"""
Integration Example

Example of how to integrate the flow system with the existing telephony bridge
and function handler.
"""

import logging
from typing import Dict, List

from .flow_manager import create_default_flow_manager
from ..function_handler import FunctionHandler

logger = logging.getLogger(__name__)


class FlowIntegrationExample:
    """
    Example showing how to integrate flows with the existing system.
    """

    def __init__(self, realtime_websocket):
        """
        Initialize with WebSocket connection.
        
        Args:
            realtime_websocket: WebSocket connection to OpenAI Realtime API
        """
        self.realtime_websocket = realtime_websocket
        self.flow_manager = create_default_flow_manager()
        self.function_handler = FunctionHandler(realtime_websocket)

    def setup_flows(self, active_flows: List[str] = None):
        """
        Set up flows for the session.
        
        Args:
            active_flows: List of flow names to activate, defaults to ['card_replacement']
        """
        if active_flows is None:
            active_flows = ['card_replacement']

        # Activate the specified flows
        for flow_name in active_flows:
            try:
                self.flow_manager.activate_flow(flow_name)
                logger.info(f"Activated flow: {flow_name}")
            except ValueError as e:
                logger.error(f"Failed to activate flow {flow_name}: {e}")

        # Register flow functions with the function handler
        self.flow_manager.register_with_function_handler(self.function_handler)

    def get_session_config(self) -> Dict:
        """
        Get the session configuration with flow-based tools and instructions.
        
        Returns:
            Session configuration dictionary
        """
        tools = self.flow_manager.get_all_tools()
        system_instruction = self.flow_manager.get_combined_system_instruction()

        return {
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "voice": "alloy",
            "instructions": system_instruction,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
            "tools": tools,
            "input_audio_noise_reduction": {"type": "near_field"},
            "input_audio_transcription": {"model": "whisper-1"},
            "max_response_output_tokens": 4096,
            "tool_choice": "auto",
        }

    def switch_flow(self, new_flow: str):
        """
        Switch to a different flow during the session.
        
        Args:
            new_flow: Name of the flow to switch to
        """
        # Deactivate all current flows
        for flow_name in self.flow_manager.active_flows.copy():
            self.flow_manager.deactivate_flow(flow_name)

        # Activate the new flow
        self.flow_manager.activate_flow(new_flow)

        # Re-register functions
        self.flow_manager.register_with_function_handler(self.function_handler)

        logger.info(f"Switched to flow: {new_flow}")

    def get_flow_status(self) -> Dict:
        """
        Get current flow status and information.
        
        Returns:
            Flow status dictionary
        """
        return {
            "active_flows": self.flow_manager.active_flows,
            "total_tools": len(self.flow_manager.get_all_tools()),
            "total_functions": len(self.flow_manager.get_all_functions()),
            "flow_info": self.flow_manager.get_flow_info()
        }


def modify_telephony_bridge_for_flows():
    """
    Example of how to modify the TelephonyRealtimeBridge to use flows.
    
    This shows the changes you would make to the existing bridge class.
    """
    
    # Example modifications to TelephonyRealtimeBridge.__init__():
    def modified_init_example(self, telephony_websocket, realtime_websocket):
        # ... existing initialization code ...
        
        # Add flow integration
        self.flow_integration = FlowIntegrationExample(realtime_websocket)
        self.flow_integration.setup_flows(['card_replacement'])  # or other flows
        
        # Replace the existing function handler
        self.function_handler = self.flow_integration.function_handler

    # Example modifications to initialize_session():
    async def modified_initialize_session_example(realtime_websocket):
        # Create flow integration
        flow_integration = FlowIntegrationExample(realtime_websocket)
        flow_integration.setup_flows(['card_replacement'])
        
        # Get session config from flows
        session_config = flow_integration.get_session_config()
        
        # Create session update event
        session_update = {
            "type": "session.update",
            "session": session_config
        }
        
        # Send to OpenAI
        await realtime_websocket.send(json.dumps(session_update))

    logger.info("Example modifications for telephony bridge integration shown")


# Example usage in main application:
def example_usage():
    """
    Example of how to use the flow system in your main application.
    """
    
    # Create a flow manager
    flow_manager = create_default_flow_manager()
    
    # Check available flows
    print("Available flows:", flow_manager.get_flow_info())
    
    # Activate specific flows
    flow_manager.activate_flow("card_replacement")
    
    # Get tools for OpenAI session
    tools = flow_manager.get_all_tools()
    print(f"Total tools: {len(tools)}")
    
    # Get system instruction
    instruction = flow_manager.get_combined_system_instruction()
    print(f"System instruction length: {len(instruction)} characters")
    
    # Validate flows
    validation = flow_manager.validate_all_flows()
    print("Validation results:", validation)


if __name__ == "__main__":
    example_usage() 