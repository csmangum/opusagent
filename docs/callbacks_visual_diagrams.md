# Callbacks Visual Diagrams

This document contains additional visual diagrams to help understand callback patterns in the OpusAgent codebase.

## Callback Lifecycle

```mermaid
graph TD
    A[Define Callback Function] --> B[Register with Manager]
    B --> C[Wait for Event]
    C --> D[Event Occurs]
    D --> E[Manager Triggers Callback]
    E --> F[Callback Executes]
    F --> G[Handle Result]
    G --> H[Continue or Cleanup]
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#fff3e0
    style D fill:#e8f5e8
    style E fill:#fff8e1
    style F fill:#fce4ec
    style G fill:#f1f8e9
    style H fill:#e0f2f1
```

## Callback Registration Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant Registry as Callback Registry
    participant Event as Event System
    participant Callback as Callback Function
    
    App->>Registry: register_callback("event_type", callback_func)
    Registry->>Registry: Store in callbacks[event_type]
    Note over Registry: Callback now registered
    
    Event->>Registry: trigger_event("event_type", data)
    Registry->>Registry: Lookup callbacks for event_type
    Registry->>Callback: execute_callback(data)
    Callback->>App: perform_action(result)
    
    Note over App,Callback: Callback completes
```

## Multiple Callback Execution

```mermaid
graph TD
    A[Event Triggered] --> B[Callback Manager]
    B --> C[Get All Registered Callbacks]
    C --> D[Callback 1]
    C --> E[Callback 2]
    C --> F[Callback 3]
    C --> G[Callback N]
    
    D --> H[Action 1]
    E --> I[Action 2]
    F --> J[Action 3]
    G --> K[Action N]
    
    H --> L[Continue Processing]
    I --> L
    J --> L
    K --> L
    
    style A fill:#ffebee
    style B fill:#e3f2fd
    style C fill:#f3e5f5
    style D fill:#e8f5e8
    style E fill:#e8f5e8
    style F fill:#e8f5e8
    style G fill:#e8f5e8
    style H fill:#fff3e0
    style I fill:#fff3e0
    style J fill:#fff3e0
    style K fill:#fff3e0
    style L fill:#f1f8e9
```

## Error Handling in Callbacks

```mermaid
graph TD
    A[Callback Execution] --> B{Try Block}
    B --> C[Execute Callback Logic]
    B --> D[Exception Occurs]
    
    C --> E[Success - Continue]
    D --> F[Catch Exception]
    F --> G[Log Error]
    G --> H[Execute Error Callbacks]
    H --> I[Recovery Actions]
    I --> J[Continue or Fail]
    
    E --> K[Return Result]
    J --> K
    
    style A fill:#e3f2fd
    style B fill:#fff3e0
    style C fill:#e8f5e8
    style D fill:#ffebee
    style E fill:#e8f5e8
    style F fill:#fff8e1
    style G fill:#ffebee
    style H fill:#fff8e1
    style I fill:#e8f5e8
    style J fill:#fff3e0
    style K fill:#f1f8e9
```

## Callback Chain Execution

```mermaid
graph LR
    A[Initial Data] --> B[Callback 1]
    B --> C[Processed Data 1]
    C --> D[Callback 2]
    D --> E[Processed Data 2]
    E --> F[Callback 3]
    F --> G[Final Result]
    
    style A fill:#e3f2fd
    style B fill:#e8f5e8
    style C fill:#fff3e0
    style D fill:#e8f5e8
    style E fill:#fff3e0
    style F fill:#e8f5e8
    style G fill:#f1f8e9
```

## State Change Callback Flow

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Connecting : initiate_connection()
    Connecting --> Connected : connection_established()
    Connected --> Active : session_started()
    Active --> Ending : end_session()
    Ending --> Ended : cleanup_complete()
    Active --> Error : error_occurred()
    Error --> Ended : cleanup_complete()
    
    note right of Idle : Callbacks: on_idle()
    note right of Connecting : Callbacks: on_connecting()
    note right of Connected : Callbacks: on_connected()
    note right of Active : Callbacks: on_active()
    note right of Ending : Callbacks: on_ending()
    note right of Ended : Callbacks: on_ended()
    note right of Error : Callbacks: on_error()
```

## Audio Processing Callback Flow

```mermaid
graph TD
    A[Microphone Input] --> B[Audio System]
    B --> C[Audio Callback Triggered]
    C --> D[Process Audio Data]
    D --> E{Callback Registered?}
    E -->|Yes| F[Execute Audio Callback]
    E -->|No| G[Continue Processing]
    
    F --> H[Audio Analysis]
    F --> I[Audio Recording]
    F --> J[Audio Streaming]
    F --> K[VAD Processing]
    
    H --> L[Update UI]
    I --> M[Save to File]
    J --> N[Send to Server]
    K --> O[Speech Detection]
    
    style A fill:#e3f2fd
    style B fill:#e8f5e8
    style C fill:#fff3e0
    style D fill:#e8f5e8
    style E fill:#fff8e1
    style F fill:#e8f5e8
    style G fill:#fff3e0
    style H fill:#fff3e0
    style I fill:#fff3e0
    style J fill:#fff3e0
    style K fill:#fff3e0
    style L fill:#f1f8e9
    style M fill:#f1f8e9
    style N fill:#f1f8e9
    style O fill:#f1f8e9
```

## WebSocket Message Callback Flow

```mermaid
graph TD
    A[WebSocket Message] --> B[Message Handler]
    B --> C[Parse Message Type]
    C --> D{Message Type}
    
    D -->|Session| E[Session Callbacks]
    D -->|Audio| F[Audio Callbacks]
    D -->|Error| G[Error Callbacks]
    D -->|General| H[General Callbacks]
    
    E --> I[Update Session State]
    F --> J[Process Audio]
    G --> K[Handle Error]
    H --> L[Log Message]
    
    I --> M[Notify UI]
    J --> N[Play Audio]
    K --> O[Show Error]
    L --> P[Continue]
    
    style A fill:#e3f2fd
    style B fill:#e8f5e8
    style C fill:#fff3e0
    style D fill:#fff8e1
    style E fill:#e8f5e8
    style F fill:#e8f5e8
    style G fill:#e8f5e8
    style H fill:#e8f5e8
    style I fill:#fff3e0
    style J fill:#fff3e0
    style K fill:#fff3e0
    style L fill:#fff3e0
    style M fill:#f1f8e9
    style N fill:#f1f8e9
    style O fill:#f1f8e9
    style P fill:#f1f8e9
```

## Function Call Callback Flow

```mermaid
graph TD
    A[AI Function Call] --> B[Function Handler]
    B --> C[Parse Function Name]
    C --> D{Function Registered?}
    
    D -->|Yes| E[Execute Function]
    D -->|No| F[Error: Not Implemented]
    
    E --> G[Get Function Result]
    G --> H{Check Result Type}
    
    H -->|Success| I[Send Result to AI]
    H -->|Hang Up| J[Trigger Hang Up Callback]
    H -->|Error| K[Handle Error]
    
    I --> L[Continue Conversation]
    J --> M[End Call]
    K --> N[Log Error]
    
    F --> O[Log Warning]
    N --> P[Continue or Fail]
    O --> P
    
    style A fill:#e3f2fd
    style B fill:#e8f5e8
    style C fill:#fff3e0
    style D fill:#fff8e1
    style E fill:#e8f5e8
    style F fill:#ffebee
    style G fill:#fff3e0
    style H fill:#fff8e1
    style I fill:#e8f5e8
    style J fill:#ffebee
    style K fill:#ffebee
    style L fill:#f1f8e9
    style M fill:#f1f8e9
    style N fill:#fff8e1
    style O fill:#fff8e1
    style P fill:#f1f8e9
```

## Callback Performance Monitoring

```mermaid
graph TD
    A[Callback Triggered] --> B[Start Timer]
    B --> C[Execute Callback]
    C --> D[Stop Timer]
    D --> E[Calculate Duration]
    E --> F{Duration Threshold}
    
    F -->|Under Threshold| G[Log Debug]
    F -->|Over Threshold| H[Log Warning]
    
    G --> I[Continue Processing]
    H --> I
    
    style A fill:#e3f2fd
    style B fill:#fff3e0
    style C fill:#e8f5e8
    style D fill:#fff3e0
    style E fill:#fff8e1
    style F fill:#fff8e1
    style G fill:#e8f5e8
    style H fill:#ffebee
    style I fill:#f1f8e9
```

## Callback Testing Flow

```mermaid
graph TD
    A[Setup Test] --> B[Create Mock Callback]
    B --> C[Register Mock Callback]
    C --> D[Trigger Event]
    D --> E[Execute Callback]
    E --> F[Verify Callback Called]
    F --> G[Check Arguments]
    G --> H[Verify Result]
    H --> I[Test Passes]
    
    style A fill:#e3f2fd
    style B fill:#e8f5e8
    style C fill:#fff3e0
    style D fill:#e8f5e8
    style E fill:#fff3e0
    style F fill:#e8f5e8
    style G fill:#fff3e0
    style H fill:#e8f5e8
    style I fill:#f1f8e9
```

## Callback Cleanup Flow

```mermaid
graph TD
    A[System Shutdown] --> B[Stop Event Processing]
    B --> C[Get All Registered Callbacks]
    C --> D[Execute Cleanup Callbacks]
    D --> E[Unregister Callbacks]
    E --> F[Release Resources]
    F --> G[System Cleaned Up]
    
    style A fill:#e3f2fd
    style B fill:#e8f5e8
    style C fill:#fff3e0
    style D fill:#e8f5e8
    style E fill:#fff3e0
    style F fill:#e8f5e8
    style G fill:#f1f8e9
```

## Callback Memory Management

```mermaid
graph TD
    A[Callback Registration] --> B[Store Function Reference]
    B --> C[Event Occurs]
    C --> D[Execute Callback]
    D --> E[Callback Completes]
    E --> F{Keep Reference?}
    
    F -->|Yes| G[Maintain Reference]
    F -->|No| H[Remove Reference]
    
    G --> I[Memory Retained]
    H --> J[Memory Freed]
    
    I --> K[Continue Processing]
    J --> K
    
    style A fill:#e3f2fd
    style B fill:#e8f5e8
    style C fill:#fff3e0
    style D fill:#e8f5e8
    style E fill:#fff3e0
    style F fill:#fff8e1
    style G fill:#e8f5e8
    style H fill:#ffebee
    style I fill:#fff3e0
    style J fill:#e8f5e8
    style K fill:#f1f8e9
```

## Callback Priority Execution

```mermaid
graph TD
    A[Event Triggered] --> B[Sort Callbacks by Priority]
    B --> C[High Priority Callbacks]
    B --> D[Medium Priority Callbacks]
    B --> E[Low Priority Callbacks]
    
    C --> F[Execute High Priority]
    D --> G[Execute Medium Priority]
    E --> H[Execute Low Priority]
    
    F --> I[Continue Processing]
    G --> I
    H --> I
    
    style A fill:#e3f2fd
    style B fill:#e8f5e8
    style C fill:#ffebee
    style D fill:#fff3e0
    style E fill:#e8f5e8
    style F fill:#ffebee
    style G fill:#fff3e0
    style H fill:#e8f5e8
    style I fill:#f1f8e9
```

## Callback Error Recovery

```mermaid
graph TD
    A[Callback Execution] --> B{Execution Success?}
    B -->|Yes| C[Continue Processing]
    B -->|No| D[Log Error]
    D --> E[Execute Error Recovery Callbacks]
    E --> F{Recovery Successful?}
    
    F -->|Yes| G[Retry Original Callback]
    F -->|No| H[Execute Fallback Callback]
    
    G --> I{Retry Success?}
    H --> J[Log Failure]
    
    I -->|Yes| C
    I -->|No| H
    J --> K[System Error State]
    
    style A fill:#e3f2fd
    style B fill:#fff8e1
    style C fill:#e8f5e8
    style D fill:#ffebee
    style E fill:#fff8e1
    style F fill:#fff8e1
    style G fill:#e8f5e8
    style H fill:#ffebee
    style I fill:#fff8e1
    style J fill:#ffebee
    style K fill:#ffebee
```

These diagrams provide visual representations of how callbacks work in different scenarios within the OpusAgent system. They help illustrate the flow of execution, error handling, and the relationships between different components. 