# ChangeBlog

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
