# Intelligent Caller Agent System

The Caller Agent system creates realistic AI-powered callers that interact with your telephony bridge for testing purposes. Each caller has its own OpenAI Realtime connection and can simulate different personalities and scenarios to thoroughly test your agent's capabilities.

## Features

- **Multiple Personalities**: Normal, difficult, confused, angry, elderly, tech-savvy, impatient, and suspicious callers
- **Various Scenarios**: Card replacement, account inquiry, loan application, complaints, and general inquiries
- **OpenAI Integration**: Each caller uses its own OpenAI Realtime API connection for natural conversation
- **Batch Testing**: Run multiple scenarios in sequence or parallel
- **Comprehensive Reporting**: Detailed test results with statistics and analysis
- **Interactive Mode**: Test scenarios interactively from the command line

## Quick Start

### 1. Basic Usage

Run a predefined difficult caller:
```bash
python caller_cli.py --scenario difficult_card_replacement
```

Run an interactive session:
```bash
python caller_cli.py --interactive
```

### 2. Custom Scenarios

Create a custom angry customer complaining about fees:
```bash
python caller_cli.py --personality angry --scenario-type complaint --goal "Get overdraft fees removed"
```

### 3. Batch Testing

Run all scenarios from the configuration file:
```bash
python caller_cli.py --batch scenarios.json
```

Run a specific test configuration:
```bash
python batch_caller_test.py --config difficult_customers
```

## System Architecture

### Core Components

1. **CallerAgent**: Main class that combines MockAudioCodesClient with OpenAI Realtime API
2. **PersonalityType**: Defines behavioral characteristics (patience, tech comfort, communication style)
3. **ScenarioType**: Defines what the caller wants to accomplish
4. **CallerGoal**: Specific objectives and success criteria
5. **CallerScenario**: Combines scenario type, goals, and context

### Audio Flow

```
OpenAI Realtime API → CallerAgent → MockAudioCodesClient → Bridge → Your Agent
                  ←              ←                    ←        ←
```

Each caller:
1. Connects to OpenAI Realtime API with personality-specific system prompt
2. Uses MockAudioCodesClient to simulate telephony connection to your bridge
3. Receives audio from your agent and converts to text for processing
4. Generates contextually appropriate responses via OpenAI
5. Converts responses back to audio and sends to bridge

## Personality Types

### Normal
- **Traits**: Polite, cooperative, clear communication
- **Use Case**: Baseline testing, happy path scenarios
- **Patience**: High (7/10)
- **Tech Comfort**: Medium (6/10)

### Difficult  
- **Traits**: Stubborn, argumentative, suspicious of processes
- **Use Case**: Testing agent patience and escalation handling
- **Patience**: Low (3/10)
- **Tendency to Interrupt**: High (0.7)

### Confused
- **Traits**: Uncertain, needs clarification, provides incomplete info
- **Use Case**: Testing agent's ability to guide and educate
- **Tech Comfort**: Low (3/10)
- **Provides Clear Info**: Low (0.3)

### Angry
- **Traits**: Frustrated, demanding, impatient
- **Use Case**: Testing de-escalation and crisis management
- **Patience**: Very Low (2/10)
- **Tendency to Interrupt**: Very High (0.9)

### Elderly
- **Traits**: Polite but slow, uncomfortable with technology
- **Use Case**: Testing accessibility and patience with slower interactions
- **Tech Comfort**: Very Low (2/10)
- **Response Speed**: Slow

### Impatient
- **Traits**: Rushed, wants quick resolution, business-focused
- **Use Case**: Testing efficiency and rapid problem resolution
- **Patience**: Very Low (2/10)
- **Communication**: Direct and fast

### Tech-Savvy
- **Traits**: Knowledgeable, direct, knows what they want
- **Use Case**: Testing agent with sophisticated customers
- **Tech Comfort**: Very High (9/10)
- **Provides Clear Info**: High (0.9)

### Suspicious
- **Traits**: Distrustful, questions everything, security-focused
- **Use Case**: Testing security protocols and trust-building
- **Patience**: Medium (5/10)
- **Verification Requirements**: High

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
      "name": "Difficult Card Replacement",
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

### 1. Single Test
```bash
# Run difficult card replacement
python caller_cli.py --scenario difficult_card_replacement --timeout 120

# Custom scenario
python caller_cli.py --personality elderly --scenario-type card_replacement --goal "Replace stolen card" --caller-name "ElderlyMary"
```

### 2. Batch Testing
```bash
# Run all scenarios
python batch_caller_test.py --scenarios scenarios.json

# Run specific configuration
python batch_caller_test.py --config quick_test

# Parallel execution
python batch_caller_test.py --config stress_test --parallel --output stress_results
```

### 3. Interactive Mode
```bash
python caller_cli.py --interactive
```
Then select from menu options to run different scenarios.

## Test Results and Reporting

### Individual Results
Each test produces:
- **Success/Failure status**
- **Conversation turn count**
- **Goals achieved vs total goals**
- **Duration and timing metrics**
- **Error messages (if failed)**

### Batch Results
Comprehensive reporting includes:
- **Overall success rate**
- **Statistics by personality type**
- **Statistics by scenario type**
- **Duration analysis (min, max, median, std dev)**
- **Individual test breakdown**

### Output Formats
- **Console**: Real-time status and summary
- **Text Report**: Human-readable comprehensive report
- **JSON**: Machine-readable detailed results for analysis

Example text report:
```
CALLER AGENT BATCH TEST REPORT
=====================================
Total Tests: 10
Successful: 8 (80.0%)
Failed: 2
Total Duration: 425.3s
Average Duration: 42.5s

PERSONALITY TYPE BREAKDOWN
--------------------------
DIFFICULT
  Success Rate: 60.0%
  Avg Duration: 65.2s
  Avg Turns: 12.3
  
ELDERLY  
  Success Rate: 100.0%
  Avg Duration: 78.1s
  Avg Turns: 15.7
```

## Advanced Features

### Custom Personality Creation
Create your own personality types by extending the CallerPersonality class:

```python
custom_personality = CallerPersonality(
    type=PersonalityType.DIFFICULT,
    traits=["perfectionist", "detail-oriented", "impatient"],
    communication_style="Demanding and specific",
    patience_level=3,
    tech_comfort=8,
    tendency_to_interrupt=0.6,
    provides_clear_info=0.9
)
```

### Custom Scenario Creation
Define your own scenarios:

```python
custom_scenario = CallerScenario(
    scenario_type=ScenarioType.ACCOUNT_INQUIRY,
    goal=CallerGoal(
        primary_goal="Dispute a transaction",
        secondary_goals=["Get temporary credit", "Understand fraud protection"],
        success_criteria=["dispute filed", "timeline provided"],
        failure_conditions=["transferred without resolution"],
        max_conversation_turns=15
    ),
    context={"transaction_amount": "$234.56", "merchant": "Unknown Store"}
)
```

### Performance Testing
Use parallel execution for stress testing:

```python
# Run 20 concurrent callers
python batch_caller_test.py --config stress_test --parallel --max-concurrent 20
```

## Troubleshooting

### Common Issues

1. **Connection Failures**
   - Verify bridge URL is correct
   - Ensure bridge server is running
   - Check OpenAI API key is set

2. **Audio Processing Errors**
   - Verify audio file formats (16kHz PCM expected)
   - Check temporary file permissions
   - Monitor disk space for audio files

3. **Timeout Issues**
   - Increase timeout values for slow scenarios
   - Check bridge response times
   - Monitor OpenAI API latency

4. **Goal Achievement Problems**
   - Review success criteria definitions
   - Check conversation flow logic
   - Verify scenario-to-goal mapping

### Debugging

Enable verbose logging:
```bash
python caller_cli.py --verbose --scenario difficult_card_replacement
```

Monitor logs in real-time:
```bash
tail -f logs/caller_agent.log
```

### Performance Optimization

1. **Reduce Audio Latency**
   - Use smaller audio chunks
   - Optimize audio encoding/decoding
   - Monitor network latency to OpenAI

2. **Improve Success Rates**
   - Refine personality prompts
   - Adjust conversation turn limits
   - Update success criteria

3. **Scale Testing**
   - Use parallel execution judiciously
   - Monitor system resources
   - Implement rate limiting for OpenAI API

## Best Practices

### Test Design
1. **Start Simple**: Begin with normal personality scenarios
2. **Increase Complexity**: Gradually add difficult personalities
3. **Test Edge Cases**: Use extreme personality combinations
4. **Validate Results**: Manually review a sample of conversations

### Scenario Coverage
1. **Happy Path**: Test normal successful interactions
2. **Error Conditions**: Test how agent handles failures
3. **Edge Cases**: Test unusual but valid requests
4. **Stress Testing**: Test with difficult personalities

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
    python batch_caller_test.py --config quick_test --output ci_results
    python -c "
    import json
    with open('ci_results.json') as f:
        results = json.load(f)
    success_rate = results['summary']['success_rate']
    if success_rate < 0.8:
        exit(1)
    "
```

## API Reference

### CallerAgent
Main class for creating intelligent callers.

```python
caller = CallerAgent(
    bridge_url="ws://localhost:8000/ws/telephony",
    personality=personality,
    scenario=scenario,
    caller_name="TestCaller",
    caller_phone="+15551234567"
)

async with caller:
    success = await caller.start_call(timeout=60.0)
```

### Factory Functions
Predefined caller creators:
- `create_difficult_card_replacement_caller(bridge_url)`
- `create_confused_elderly_caller(bridge_url)`
- `create_angry_complaint_caller(bridge_url)`

## Support and Contributing

### Getting Help
1. Check the logs for detailed error information
2. Review scenario configurations for correct parameters
3. Verify bridge and OpenAI connectivity
4. Check the FAQ section above

### Contributing
1. Add new personality types in the PersonalityType enum
2. Create new scenario templates in CallerScenario
3. Implement custom conversation flows
4. Add new reporting metrics

### Future Enhancements
- Voice cloning for consistent caller identities
- Multi-language support
- Advanced conversation memory
- Integration with speech-to-text services
- Real-time performance dashboards 