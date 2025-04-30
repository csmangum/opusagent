"""
Scratchpad module for agent reasoning and thought tracking.

This module provides a structured system for agent reasoning and thought tracking within the Agentic 
Finite State Machine (AFSM) architecture. It enables states to maintain structured reasoning, 
tracking of partial conclusions, and preservation of critical context across state transitions.

Key components:
- ScratchpadContent: Fundamental container for reasoning data with timestamps and metadata
- ReasoningSection: Specialized containers for different types of reasoning (facts, hypotheses, etc.)
- ScratchpadManager: Central orchestrator for managing multiple scratchpads and their sections
- StateScratchpadIntegration: Integration layer connecting the scratchpad system with AFSM states

The scratchpad module enhances the AFSM architecture by providing explicit memory and reasoning 
capabilities to states, allowing for more complex decision-making patterns and transparency into
the agent's thought processes.

Usage examples:
```python
# Basic scratchpad usage
from app.scratchpad import ScratchpadContent, ReasoningSection
from app.scratchpad.section import SectionType

# Create a simple reasoning container
content = ScratchpadContent(name="reasoning_process")
content.append("The user seems to be asking about product pricing.")
content.append("Their tone indicates urgency.")
print(content.get_content())

# Use specialized sections for structured reasoning
facts = ReasoningSection(SectionType.FACTS)
facts.add("User requested information about the premium plan.")
facts.add("User mentioned a budget constraint of $50/month.")

# Create a manager to handle multiple scratchpads
from app.scratchpad import ScratchpadManager
from pathlib import Path

manager = ScratchpadManager(storage_dir=Path("./scratchpad_data"))
pad_id = manager.create_scratchpad(name="conversation_123")
manager.write("Starting a new conversation about product features")

# Integrate with AFSM states
from app.states import AFSMState
from app.afsm.scratchpad.integration import ScratchpadStateMixin

class ReasoningState(AFSMState, ScratchpadStateMixin):
    async def process(self, input_text, context):
        # Record the reasoning process
        self.write_to_scratchpad("Analyzing user input...")
        self.write_fact("User mentioned product X")
        self.write_hypothesis("User might be interested in comparing products")
        self.write_conclusion("Should present a comparison table")
        
        # Logic to determine response and next state
        # ...
        
        return response, next_state, context
```
"""

from fastagent.afsm.scratchpad.content import ScratchpadContent
from fastagent.afsm.scratchpad.manager import ScratchpadManager
from fastagent.afsm.scratchpad.section import ReasoningSection

__all__ = [
    "ScratchpadContent",
    "ScratchpadManager",
    "ReasoningSection",
] 