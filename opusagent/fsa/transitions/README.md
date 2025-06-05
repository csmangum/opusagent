# Transitions Module

The Transitions module provides a flexible framework for defining and managing state transitions in a state machine architecture. It's designed to handle complex transition logic with various evaluation strategies.

## Core Components

### Transition Types

- **BaseTransition**: Abstract base class for all transition types with common functionality.
- **RuleBasedTransition**: Deterministic transitions triggered by explicit conditions.
- **IntentBasedTransition**: Transitions based on user intent detection.
- **ReasoningBasedTransition**: Transitions determined through reasoning over context.
- **HybridTransition**: Combines multiple transition strategies.

### Management Tools

- **TransitionRegistry**: Central registry for managing available transitions.
- **TransitionEvaluator**: Evaluates and selects the best available transition based on context.

### Conditions

- **PreCondition**: Conditions that must be satisfied before a transition.
- **PostCondition**: Effects that occur after a transition is executed.

## Usage Example

```python
# Creating a rule-based transition
from opusagent.fsa.transitions import RuleBasedTransition, Condition, TransitionRegistry

# Define conditions
has_error = Condition(
    predicate=lambda ctx: ctx.get('error') is not None,
    description="Error exists in context"
)

# Create transition
error_transition = RuleBasedTransition(
    source_state="processing",
    target_state="error_handling",
    conditions=[has_error],
    priority=10,
    description="Transition to error state when an error occurs"
)

# Register in a registry
registry = TransitionRegistry()
registry.register(error_transition)
```

## Key Features

- Priority-based transition selection
- Confidence scoring for non-deterministic transitions
- Pre and post-condition handling
- Flexible evaluation strategies
- Registry for centralized transition management
- Validation for detecting potential issues

## Architecture

Transitions connect states in a state machine and determine when and how the system should move between states. Each transition type provides a different strategy for evaluating when a transition should occur, allowing for both simple rule-based logic and complex AI-driven decision making. 