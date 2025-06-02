# FastAgent
![Status](https://img.shields.io/badge/status-In%20Development%20–%20Experimental%20%26%20Aspirational-blue)

FastAgent is a framework for real-time voice bots that delivers seamless, low-latency interactions. Built with FastAPI, it integrates the AudioCodes VoiceAI Connect API for voice input and the OpenAI Realtime API for dialogue and voice generation. FastAgent combines a dynamic, Stateful LLM Layer conversational core with finite state agents(FSA) for complex tasks, ensuring rapid, context-aware voice interactions optimized for enterprise applications.

## Key Features

- **Dynamic Dialogue**: OpenAI's AI drives fluid, multi-turn conversations without rigid states
- **Structured Tasks**: FSA agents ensure reliable, step-by-step task handling
- **Ultra-Low Latency**: FastAPI-powered audio passthrough and real-time processing
- **Call Continuity**: Automatic handling of disconnections with context preservation
- **Modular Design**: Easily add new FSA-based tasks (e.g., payments, queries)
- **Transparent Reasoning**: Track agent decision-making processes through FSA architecture
- **Model Context Protocol (MCP)**: Orchestrates tool/function calls, manages conversational context, and ensures reliable, auditable execution between the LLM and backend services

## Architecture

FastAgent employs a hybrid architecture:

- **Stateful LLM Layer**: Leverages OpenAI's stateful context for natural language understanding and conversation flow
- **FSA Task Agents**: When triggered by specific intents, dedicated Finite State Agents handle structured workflows
- **Concurrent Execution**: Conversation flows uninterrupted while FSA agents handle tasks in parallel

## Model Context Protocol (MCP)

FastAgent uses the **Model Context Protocol (MCP)** as the backbone for orchestrating tool and function calls, managing conversational context, and ensuring reliable execution of complex workflows.

- **What is MCP?**  
  MCP is a protocol layer that connects the conversational AI (LLM) with backend services and the Finite State Agent (FSA) framework. It ensures that every tool/function call (such as validating user input, confirming actions, or triggering external services) is executed deterministically, with full context preservation and traceability.

- **How does it work?**  
  When the LLM determines that an action is needed (e.g., replacing a card, confirming an address), it issues a structured function call. MCP receives this call, manages the relevant context, and routes the request to the appropriate handler or service. MCP also updates the FSA state and context, ensuring that the conversation flow remains coherent and auditable.

- **Why MCP?**  
  MCP provides a clean separation between conversational logic and execution logic, making it easy to test, debug, and extend FastAgent with new tools or workflows. It is designed for reliability, transparency, and modularity in enterprise-grade voice and chat agents.

## Documentation

For detailed documentation on FastAgent concepts and implementation:

- [Architecture Overview](docs/OVERVIEW.md)
- [Design Details](docs/DESIGN.md)
- [Finite State Agents (FSA)](docs/finite_state_agent.md)

## Use Cases

- **Banking**: Secure, real-time account inquiries and transfers
- **Healthcare**: Patient appointment scheduling and triage
- **Retail**: Intelligent order management and support
- **Enterprise**: Internal hotline assistants with compliance-driven behavior

---

*"Fast, natural conversations with seamless task completion."*
