# FastAgent
![Status](https://img.shields.io/badge/status-In%20Development%20–%20Experimental%20%26%20Aspirational-blue)

FastAgent is a high-performance framework for real-time voice bots that delivers seamless, low-latency interactions. Built with FastAPI, it integrates the AudioCodes VoiceAI Connect API for voice input and the OpenAI Realtime API for dialogue and voice generation. FastAgent combines a dynamic, Stateful LLM Layer conversational core with finite state machine (FSM) agents for complex tasks, ensuring rapid, context-aware voice interactions optimized for enterprise applications.

## Key Features

- **Dynamic Dialogue**: OpenAI's AI drives fluid, multi-turn conversations without rigid states
- **Structured Tasks**: FSM agents ensure reliable, step-by-step task handling
- **Ultra-Low Latency**: FastAPI-powered audio passthrough and real-time processing
- **Call Continuity**: Automatic handling of disconnections with context preservation
- **Modular Design**: Easily add new FSM-based tasks (e.g., payments, queries)
- **Transparent Reasoning**: Track agent decision-making processes through AFSM architecture

## Architecture

FastAgent employs a hybrid architecture:

- **Stateful LLM Layer**: Leverages OpenAI's stateful context for natural language understanding and conversation flow
- **AFSM Task Agents**: When triggered by specific intents, dedicated Agentic Finite State Machines handle structured workflows
- **Concurrent Execution**: Conversation flows uninterrupted while FSM agents handle tasks in parallel

## Installation

```bash
# Clone the repository
git clone https://github.com/csmangum/fastagent.git
cd fastagent

# Create and activate virtual environment (optional)
python -m venv venv
# On Windows
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp env.example .env
# Edit .env with your configuration
```

## Quick Start

```bash
# Run the server
python run.py

# For development with debug enabled
python run.py --debug
```

## Docker Support

```bash
# Build and run with Docker Compose
docker-compose up -d
```

## Documentation

For detailed documentation on FastAgent concepts and implementation:

- [Architecture Overview](./OVERVIEW.md)
- [Design Details](./DESIGN.md)
- [Agentic Finite State Machines (AFSM)](./app/afsm/README.md)

## Use Cases

- **Banking**: Secure, real-time account inquiries and transfers
- **Healthcare**: Patient appointment scheduling and triage
- **Retail**: Intelligent order management and support
- **Enterprise**: Internal hotline assistants with compliance-driven behavior

---

*"Fast, natural conversations with seamless task completion."*
