# Changelog

All notable changes to FastAgent will be documented in this file.

## [v0.1.0] - 2025-04-27

### Added

- **States Module**: New Agentic Finite State Machine (AFSM) architecture
  - Core components for building structured, controllable conversation flows:
    - `AFSMState`: Base class for states with embedded reasoning capabilities
    - `StateTransition`: Represents transitions between states with conditions
    - `StateContext`: Maintains context across state transitions
    - `StateManager`: Orchestrates the state machine and handles transitions
  - Built-in example states for common conversation patterns
  - Comprehensive documentation and usage examples

- **Transitions Module**: Advanced transition framework for state machine navigation
  - Multiple transition evaluation strategies:
    - `RuleBasedTransition`: Deterministic transitions triggered by explicit conditions
    - `IntentBasedTransition`: Transitions based on user intent detection
    - `ReasoningBasedTransition`: Transitions determined through reasoning over context
    - `HybridTransition`: Combines multiple transition strategies
  - Management tools:
    - `TransitionRegistry`: Central registry for managing available transitions
    - `TransitionEvaluator`: Evaluates and selects the best available transition based on context
  - Support for pre/post-conditions, priority-based selection, and confidence scoring
  - Validation tools to detect potential issues in transition configurations

- **Context Module**: Comprehensive context management framework for agent memory
  - Core components for managing conversation context and memory:
    - `ContextItem`: Base unit of context with content and metadata
    - `ContextCategory`: Named collections of related context items with retention policies
    - `StateContext`: Primary container for organizing categorized context data
    - `ContextManager`: Central orchestrator for context operations and persistence
    - `ContextFilter`: Intelligent filtering system for context transitions
  - Specialized context categories for different information types:
    - Salient Context: High-priority, immediately relevant information
    - Historical Memory: Time-ordered interaction history
    - Session Metadata: User information and conversation parameters
    - State-Specific Data: Context relevant only to particular states
  - Advanced features:
    - Configurable expiration policies for context items
    - Relevance scoring with multi-factor prioritization
    - Context pruning to prevent memory pollution
    - State transition handling with selective context preservation
  - Seamless integration with AFSM states and transitions

- **Scratchpad Module**: Structured system for agent reasoning and thought tracking
  - Core components for recording and managing structured reasoning:
    - `ScratchpadContent`: Fundamental container for reasoning data with timestamps and metadata
    - `ReasoningSection`: Specialized containers for different types of reasoning content
    - `ScratchpadManager`: Central orchestrator for managing multiple scratchpads and sections
    - `StateScratchpadIntegration`: Integration layer connecting scratchpads with AFSM states
  - Dedicated section types for structured reasoning workflow:
    - Facts: Objective observations from input
    - Hypotheses: Potential interpretations based on facts
    - Calculations: Intermediate reasoning steps
    - Conclusions: Actionable insights from reasoning
  - Integration with AFSM states through `ScratchpadStateMixin`
  - Support for context preservation across state transitions
  - Optional persistence for storing reasoning processes
