# Intelligent Caller Agent System

The Caller Agent system creates realistic AI-powered callers that interact with your telephony bridge for testing purposes. Each caller connects through a dedicated WebSocket endpoint and can simulate different personalities and scenarios to thoroughly test your agent's capabilities.

## Features

- **Multiple Personalities**: Typical, frustrated, elderly, and hurried callers
- **Various Scenarios**: Card replacement, account inquiry, loan application, complaints, and general inquiries
- **OpenAI Integration**: Each caller uses its own OpenAI Realtime API connection for natural conversation
- **Dual Agent Testing**: Run conversations between two AI agents using DualAgentBridge
- **WebSocket Integration**: Dedicated `/caller-agent` endpoint for caller connections
- **Comprehensive Testing**: Built-in test scenarios and validation tools

## Quick Start

### 1. Basic Usage

Run a dual agent conversation (caller vs customer service agent):
```bash
python simulate_agent_conversation.py --caller-type typical
```

Run with a specific caller personality:
```bash
python simulate_agent_conversation.py --caller-type frustrated
```

### 2. Available Caller Types

The system supports four caller personality types:

- **Typical** (`typical`): Cooperative, patient, clear communicator
- **Frustrated** (`frustrated`): Impatient, demanding, easily frustrated
- **Elderly** (`elderly`): Patient, polite, needs guidance, low tech comfort
- **Hurried** (`hurried`): In a rush, wants quick service, may interrupt

### 3. WebSocket Connection

Connect a caller to the system via WebSocket:
```bash
# Connect to the caller-agent endpoint
ws://localhost:8080/caller-agent
```

## System Architecture

### Core Components

1. **CallAgentBridge**: Caller-side bridge that extends AudioCodesBridge for caller connections
2. **DualAgentBridge**: Manages conversations between two AI agents (caller + customer service)
3. **CallerPersonality**: Defines behavioral characteristics (patience, tech comfort, communication style)
4. **ScenarioType**: Defines what the caller wants to accomplish
5. **CallerGoal**: Specific objectives and success criteria
6. **CallerScenario**: Combines scenario type, goals, and context

### Audio Flow

```
OpenAI Realtime API → CallAgentBridge → WebSocket → Your Agent
                  ←              ←           ←        ←
```

Each caller:
1. Connects to `/caller-agent` WebSocket endpoint
2. Uses CallAgentBridge to route audio and events
3. Receives audio from your agent and converts to text for processing
4. Generates contextually appropriate responses via OpenAI
5. Converts responses back to audio and sends to bridge

### Dual Agent Flow

```
Caller Agent (OpenAI) ←→ DualAgentBridge ←→ Customer Service Agent (OpenAI)
```

For dual agent testing:
1. DualAgentBridge creates two OpenAI Realtime connections
2. Routes audio bidirectionally between caller and customer service agents
3. Manages turn-taking and conversation flow
4. Records the entire conversation for analysis

## Caller Types

### Typical Caller
- **Traits**: Cooperative, patient, provides information willingly, polite and respectful, clear communicator
- **Use Case**: Baseline testing, happy path scenarios
- **Patience**: High (8/10)
- **Tech Comfort**: High (7/10)
- **Tendency to Interrupt**: Low (0.2)

### Frustrated Caller
- **Traits**: Impatient, easily frustrated, skeptical of automated systems, demanding, interrupts frequently
- **Use Case**: Testing agent patience and escalation handling
- **Patience**: Low (3/10)
- **Tech Comfort**: Medium (4/10)
- **Tendency to Interrupt**: High (0.7)

### Elderly Caller
- **Traits**: Patient, polite, appreciates clear explanations, may need things repeated, concerned about security
- **Use Case**: Testing accessibility and patience with slower interactions
- **Patience**: Very High (9/10)
- **Tech Comfort**: Very Low (2/10)
- **Tendency to Interrupt**: Low (0.1)

### Hurried Caller
- **Traits**: In a hurry, wants quick service, efficient communicator, interrupts to speed things up, focused on getting to the point
- **Use Case**: Testing efficiency and rapid problem resolution
- **Patience**: Low (4/10)
- **Tech Comfort**: High (8/10)
- **Tendency to Interrupt**: High (0.6)

## Scenario Types

### Card Replacement
Caller needs to replace a lost, stolen, or damaged card:
- **Goals**: Complete replacement process, confirm delivery
- **Challenges**: Security verification, urgency handling
- **Success Criteria**: Card ordered, delivery confirmed

### Account Inquiry
Caller wants to check balances, transactions, or account status:
- **Goals**: Get account information, understand transactions
- **Challenges**: Security verification, complex requests
- **Success Criteria**: Information provided, questions answered

### Loan Application
Caller interested in applying for a loan:
- **Goals**: Learn about loan options, start application process
- **Challenges**: Complex requirements, documentation needs
- **Success Criteria**: Application started, requirements explained

### Complaint
Caller has an issue that needs resolution:
- **Goals**: Get problem resolved, receive compensation if applicable
- **Challenges**: Emotional management, complex problem solving
- **Success Criteria**: Issue acknowledged, resolution plan provided

### General Inquiry
Caller has questions about bank services:
- **Goals**: Get information about services, hours, policies
- **Challenges**: Broad topic range, information accuracy
- **Success Criteria**: Questions answered, additional resources provided

## Configuration Files

### scenarios.json
Defines predefined test scenarios:

```json
{
  "scenarios": [
    {
      "name": "Difficult Card Replacement - Lost Debit Card",
      "type": "predefined",
      "scenario": "difficult_card_replacement",
      "timeout": 90.0
    },
    {
      "name": "Custom Angry Customer",
      "type": "custom", 
      "personality": "angry",
      "scenario_type": "complaint",
      "goal": "Get charges reversed",
      "timeout": 60.0
    }
  ],
  "test_configurations": {
    "quick_test": {
      "scenarios": [0, 6, 1],
      "parallel": false
    }
  }
}
```

### Test Configurations
Predefined test suites:
- **quick_test**: Basic smoke test with 3 scenarios
- **personality_test**: Tests all personality types
- **stress_test**: Comprehensive testing with all scenarios
- **difficult_customers**: Focus on challenging interactions

## Usage Examples

### 1. Dual Agent Testing
```bash
# Run typical caller vs customer service agent
python simulate_agent_conversation.py --caller-type typical

# Run frustrated caller
python simulate_agent_conversation.py --caller-type frustrated

# Run elderly caller with longer timeout
python simulate_agent_conversation.py --caller-type elderly --timeout 120
```

### 2. WebSocket Connection
```python
import websockets
import asyncio

async def connect_caller():
    uri = "ws://localhost:8080/caller-agent"
    async with websockets.connect(uri) as websocket:
        # Send caller audio and receive agent responses
        await websocket.send(audio_data)
        response = await websocket.recv()
```

### 3. Custom Caller Configuration
```python
from opusagent.callers import get_caller_config, CallerType

# Get configuration for typical caller
config = get_caller_config(CallerType.TYPICAL)

# Use in your application
caller_session_config = config
```

## API Reference

### CallAgentBridge
Caller-side bridge for intelligent caller agents:

```python
from opusagent.bridges.call_agent_bridge import CallAgentBridge

bridge = CallAgentBridge(
    platform_websocket, 
    realtime_websocket, 
    session_config, 
    vad_enabled=True
)
```

### DualAgentBridge
Bridge that manages two AI agents and routes audio between them:

```python
from opusagent.bridges.dual_agent_bridge import DualAgentBridge

bridge = DualAgentBridge(
    caller_type="typical",
    conversation_id="unique-id"
)
```

### Caller Factory Functions
Get caller configurations:

```python
from opusagent.callers import (
    CallerType,
    get_caller_config,
    register_caller_functions
)

# Get caller configuration
config = get_caller_config(CallerType.TYPICAL)

# Register caller functions
register_caller_functions(function_handler)
```

## Testing and Validation

### Running Tests
```bash
# Run all caller agent tests
python -m pytest tests/opusagent/test_caller_agent.py

# Run specific test file
python -m pytest tests/opusagent/bridges/test_call_agent_bridge.py
```

### Validation Tools
The system includes comprehensive validation tools:
- Call recording and analysis
- Transcript generation
- Audio quality monitoring
- Session event tracking

## Troubleshooting

### Common Issues

1. **Connection Failures**
   - Verify server is running on port 8080
   - Ensure `/caller-agent` endpoint is available
   - Check OpenAI API key is set

2. **Audio Processing Errors**
   - Verify audio file formats (16kHz PCM expected)
   - Check temporary file permissions
   - Monitor disk space for audio files

3. **Timeout Issues**
   - Increase timeout values for slow scenarios
   - Check bridge response times
   - Monitor OpenAI API latency

### Debugging

Enable verbose logging:
```bash
python simulate_agent_conversation.py --caller-type typical --verbose
```

Monitor logs in real-time:
```bash
tail -f logs/caller_agent.log
```

## Best Practices

### Test Design
1. **Start Simple**: Begin with typical caller scenarios
2. **Increase Complexity**: Gradually add frustrated and elderly callers
3. **Test Edge Cases**: Use hurried caller for efficiency testing
4. **Validate Results**: Manually review a sample of conversations

### Performance Monitoring
1. **Response Times**: Monitor average conversation duration
2. **Success Rates**: Track goal achievement across scenarios
3. **Error Patterns**: Identify common failure points
4. **Resource Usage**: Monitor CPU, memory, and API costs

## Integration with CI/CD

Include caller agent tests in your continuous integration:

```yaml
# GitHub Actions example
- name: Run Caller Agent Tests
  run: |
    python -m pytest tests/opusagent/test_caller_agent.py
    python simulate_agent_conversation.py --caller-type typical --timeout 60
```

## Support and Contributing

### Getting Help
1. Check the logs for detailed error information
2. Review caller configurations for correct parameters
3. Verify WebSocket connectivity
4. Check the troubleshooting section above

### Contributing
1. Add new caller types in the `CallerType` enum
2. Create new scenario templates in `CallerScenario`
3. Implement custom conversation flows
4. Add new reporting metrics

### Future Enhancements
- Voice cloning for consistent caller identities
- Multi-language support
- Advanced conversation memory
- Integration with speech-to-text services
- Real-time performance dashboards 