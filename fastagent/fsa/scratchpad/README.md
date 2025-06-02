# Scratchpad Module

## Overview

The Scratchpad module provides a structured system for agent reasoning and thought tracking within the Finite State Agent (FSA) architecture. It enables states to maintain structured reasoning, tracking of partial conclusions, and preservation of critical context across state transitions.

## Core Components

### ScratchpadContent

The fundamental container for reasoning data, providing mechanisms to add, retrieve, and manage timestamped entries.

```python
from fastagent.fsa.scratchpad import ScratchpadContent

content = ScratchpadContent(name="reasoning_process")
content.append("The user seems to be asking about product pricing.")
content.append("Their tone indicates urgency.")
print(content.get_content())
```

### ReasoningSection

Specialized containers for different types of reasoning content, allowing for structured categorization of thoughts.

```python
from fastagent.fsa.scratchpad import ReasoningSection
from fastagent.fsa.scratchpad.section import SectionType

facts = ReasoningSection(SectionType.FACTS)
facts.add("User requested information about the premium plan.")
facts.add("User mentioned a budget constraint of $50/month.")
```

### ScratchpadManager

Central orchestrator that manages multiple scratchpads and their sections, handling persistence and retrieval.

```python
from fastagent.fsa.scratchpad import ScratchpadManager
from pathlib import Path

manager = ScratchpadManager(storage_dir=Path("./scratchpad_data"))
pad_id = manager.create_scratchpad(name="conversation_123")
manager.write("Starting a new conversation about product features")
```

### StateScratchpadIntegration

Integration layer connecting the scratchpad system with the FSA state architecture.

```python
from fastagent.fsa.scratchpad.integration import StateScratchpadIntegration

integration = StateScratchpadIntegration()
integration.write_to_state_scratchpad("greeting_state", "User has initiated conversation")
```

## State Integration

The module integrates with FSA states through the `ScratchpadStateMixin` class:

```python
from fastagent.fsa.states import FSAState
from fastagent.fsa.scratchpad.integration import ScratchpadStateMixin

class ReasoningState(FSAState, ScratchpadStateMixin):
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

## Reasoning Workflow

The scratchpad supports a structured reasoning workflow:

1. **Fact Extraction**: Record objective observations from input
2. **Hypothesis Formation**: Develop potential interpretations based on facts
3. **Calculation/Analysis**: Perform intermediate reasoning steps
4. **Conclusion Drawing**: Formulate actionable insights
5. **Decision Making**: Determine appropriate responses and state transitions

## Key Features

- **Structured Reasoning**: Dedicated sections for different types of thoughts
- **Context Preservation**: Transfer important insights between states
- **Persistence**: Optional storage of reasoning processes for later analysis
- **Relationship Tracking**: Maintain connections between related thoughts
- **Metadata Support**: Annotate entries with additional context

## Transition Support

The scratchpad system supports reasoning across state transitions:

```python
# In a source state
self.transfer_reasoning_to("target_state_name")

# Custom selection of what to transfer
self._scratchpad_integration.transfer_selected_content(
    self.name,
    "target_state_name",
    [SectionType.FACTS, SectionType.CONCLUSIONS]
)
```

## Example Usage

See the complete example in `app/scratchpad/examples/reasoning_state.py` showing how to implement a reasoning-enhanced state that uses the scratchpad system to track product recommendation logic.

## Best Practices

1. **Structured Thought Process**: Use appropriate sections for different types of reasoning
2. **Clear Transitions**: Transfer only relevant insights between states
3. **Incremental Recording**: Document reasoning steps as they occur
4. **Relationship Tracking**: Connect related facts, hypotheses, and conclusions
5. **Periodic Summarization**: Summarize lengthy reasoning chains for efficiency