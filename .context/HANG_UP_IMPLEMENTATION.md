# Hang-Up Functionality Implementation

This document describes the enhanced hang-up functionality implemented for both the caller agent and voice agent (AudioCodes bridge) systems.

## Overview

The hang-up functionality enables both the caller agent and voice agent to intelligently infer when a call should end and properly terminate sessions with appropriate reasons. This ensures clean call termination and proper resource cleanup.

## Key Features

✅ **Voice Agent Hang-Up Detection**: Automatically detects when functions indicate call completion  
✅ **Caller Agent Hang-Up Detection**: Recognizes hang-up signals in agent responses  
✅ **Session Termination**: Properly ends sessions with descriptive reasons  
✅ **Multiple Hang-Up Scenarios**: Handles different completion and transfer scenarios  
✅ **Resource Cleanup**: Ensures proper cleanup of connections and recordings  

## Implementation Details

### 1. Voice Agent (AudioCodes Bridge) Hang-Up

The voice agent can infer when to hang up based on function call results:

#### Function Handler Enhancements (`opusagent/function_handler.py`)

- **Hang-Up Detection**: Added `_should_trigger_hang_up()` method that checks:
  - Functions with `next_action: "end_call"`
  - Specific end-call functions: `wrap_up`, `transfer_to_human`
  - Completion stages: `call_complete`, `human_transfer`

- **Scheduled Hang-Up**: Added `_schedule_hang_up()` method that:
  - Allows time for final AI response (8 seconds)
  - Triggers hang-up callback with appropriate reason
  - Handles errors gracefully

- **Hang-Up Reasons**: Added `_get_hang_up_reason()` method that generates:
  - "Call completed successfully - all tasks finished" (for wrap_up)
  - "Transferred to human agent - Reference: {transfer_id}" (for transfers)
  - Generic completion messages for other functions

#### Base Bridge Enhancements (`opusagent/bridges/base_bridge.py`)

- **Hang-Up Method**: Added `hang_up()` method that:
  - Sends platform-specific session end message
  - Closes bridge connections
  - Handles errors and ensures cleanup

- **Session End Interface**: Added `send_session_end()` abstract method for platforms

#### AudioCodes Bridge (`opusagent/bridges/audiocodes_bridge.py`)

- **Session End Implementation**: Added `send_session_end()` method that:
  - Sends AudioCodes-specific session end message
  - Uses proper message format and reason codes
  - Handles connection errors gracefully

### 2. Caller Agent Hang-Up Detection

The caller agent can detect when the voice agent is indicating the call should end:

#### Hang-Up Detection Logic (`caller_agent.py`)

- **Signal Detection**: Added `_should_hang_up()` method that detects:
  - **Direct indicators**: "thank you for calling", "have a great day", "goodbye"
  - **Completion phrases**: "within 5-7 business days", "we're all set"
  - **Transfer indicators**: "transferring you now", "please hold while i connect"
  - **Wrap-up combinations**: combinations like ("thank", "call"), ("anything else", "today")

- **Scenario-Specific Detection**: Card replacement completion phrases
- **Conversation Loop Integration**: Checks for hang-up signals in the main conversation loop

#### Enhanced Call Flow

```python
# In conversation loop
if self._should_hang_up(agent_text):
    self.logger.info("Agent indicated call should end - ending call politely")
    await self._end_call_successfully()
    break
```

## Usage Examples

### Voice Agent Function-Triggered Hang-Up

```python
# When wrap_up function is called
result = {
    "function_name": "wrap_up",
    "next_action": "end_call",
    "context": {"stage": "call_complete"}
}

# Function handler detects hang-up condition
should_hang_up = function_handler._should_trigger_hang_up("wrap_up", result)
# Returns: True

# Hang-up is triggered with reason
reason = function_handler._get_hang_up_reason(result)  
# Returns: "Call completed successfully - all tasks finished"
```

### Caller Agent Hang-Up Detection

```python
# Agent response indicating completion
agent_text = "Your replacement card will arrive within 5-7 business days. Thank you for calling!"

# Caller detects hang-up signal
should_hang_up = caller._should_hang_up(agent_text)
# Returns: True (detects "within 5-7 business days" and "thank you for calling")
```

## Function Triggers

### Functions That Trigger Hang-Up

1. **`wrap_up`**: Always triggers hang-up (call completion)
2. **`transfer_to_human`**: Always triggers hang-up (human transfer)
3. **Any function returning `next_action: "end_call"`**

### Functions That Don't Trigger Hang-Up

- `get_balance`
- `transfer_funds`
- `call_intent`
- `member_account_confirmation`
- `replacement_reason`
- `confirm_address`
- `start_card_replacement`
- `finish_card_replacement` (leads to wrap_up but doesn't directly hang up)

## Hang-Up Scenarios

### 1. Successful Call Completion
- **Trigger**: `wrap_up` function called
- **Reason**: "Call completed successfully - all tasks finished"
- **Flow**: AI gives farewell → Function triggers hang-up → Session ends

### 2. Human Transfer
- **Trigger**: `transfer_to_human` function called
- **Reason**: "Transferred to human agent - Reference: {transfer_id}"
- **Flow**: AI announces transfer → Function triggers hang-up → Session ends

### 3. Caller-Initiated Hang-Up
- **Trigger**: Caller detects completion signals in agent response
- **Reason**: Caller ends call politely
- **Flow**: Agent indicates completion → Caller detects signal → Caller ends call

### 4. Error/Timeout Hang-Up
- **Trigger**: Error conditions or timeouts
- **Reason**: Specific error or timeout reason
- **Flow**: Error detected → Session terminated with reason

## Configuration

### Hang-Up Timing
- **Response delay**: 8 seconds (allows final AI response to play)
- **Personality delays**: Varied based on caller personality
- **Cleanup timeout**: Configurable per platform

### Detection Sensitivity
- **Phrase matching**: Case-insensitive substring matching
- **Combination detection**: Multiple phrase combinations for wrap-up detection
- **Scenario-specific**: Different detection logic per call scenario

## Testing

The implementation includes comprehensive testing via `simple_hang_up_demo.py`:

### Test Coverage
- ✅ Function-based hang-up detection (wrap_up, transfer_to_human, normal functions)
- ✅ Caller hang-up signal detection (6 test scenarios)
- ✅ Session end message formatting (3 different scenarios)
- ✅ Hang-up reason generation
- ✅ Error handling and graceful fallbacks

### Demo Results
```
✅ Voice agents can infer hang-up from function results
✅ Caller agents can detect hang-up signals in responses  
✅ Both agents end sessions with descriptive reasons
✅ Different hang-up scenarios are handled appropriately
✅ AudioCodes bridge sends proper session end messages
```

## Benefits

1. **Automated Call Termination**: No manual intervention required
2. **Clean Resource Cleanup**: Proper session termination and recording finalization
3. **Descriptive Logging**: Clear reasons for call termination aid in debugging
4. **Flexible Detection**: Multiple detection methods for different scenarios
5. **Platform Agnostic**: Works with different telephony platforms via bridge pattern
6. **Error Resilient**: Graceful handling of connection errors during hang-up

## Integration

### For New Platforms
1. Extend `BaseRealtimeBridge` 
2. Implement `send_session_end()` method
3. Handle platform-specific session termination messages

### For New Function Types
1. Add function to `end_call_functions` list if it should trigger hang-up
2. Or return `next_action: "end_call"` from function result
3. Add custom hang-up reason logic if needed

### For New Caller Personalities
1. Add personality-specific hang-up phrases to detection logic
2. Customize hang-up behavior in personality configuration
3. Adjust response timing based on personality traits

This implementation provides a robust, extensible foundation for intelligent call termination across the entire voice agent ecosystem.