# FastAgent Architecture for Real-Time Voice Bots

## Overview

The FastAgent Architecture, built with FastAPI, powers a high-performance conversational voice bot that delivers seamless, low-latency interactions. Integrating the AudioCodes VoiceAI Connect API for voice input and the OpenAI Realtime API for dialogue and voice generation, FastAgent combines a dynamic, Stateful LLM Layer conversational core with finite state machine (FSM) agents for complex tasks, such as booking appointments. This hybrid design ensures rapid, context-aware voice interactions optimized for enterprise applications.

## How It Works

### High-Speed Dialogue Core:
- FastAgent streams audio from AudioCodes to OpenAI, leveraging OpenAI's neural model for context-aware, natural dialogue without rigid states.
- Responses are streamed back to the user via AudioCodes, ensuring real-time performance.

### Agentic Finite State Machines (AFSM):
- When a task is triggered (e.g., "Book an appointment"), OpenAI initiates a function call, and FastAgent deploys an AFSM agent to manage structured steps (e.g., collecting date, time, confirmation).
- Agents operate efficiently, ensuring precise task execution.
- For detailed documentation on the Agentic Finite State Machine (AFSM) architecture, see [AFSM Documentation](app/afsm/README.md).

### Concurrent Execution:
- The conversation flows uninterrupted while FSM agents handle tasks, allowing users to ask questions or pivot topics.
- Agents prompt users (e.g., "What time?") through OpenAI, integrating seamlessly into the dialogue.

### Rapid Result Integration:
- Upon task completion, the FSM agent returns results (e.g., "Appointment booked for 2025-04-29 at 10 AM") to OpenAI.
- OpenAI generates a natural voice response, streamed instantly to the user.

## Key Features

- **Dynamic Dialogue**: OpenAI's AI drives fluid, multi-turn conversations.
- **Structured Tasks**: FSM agents ensure reliable, step-by-step task handling.
- **Ultra-Low Latency**: FastAPI-powered audio passthrough and real-time processing.
- **Modular Design**: Easily add new FSM-based tasks (e.g., payments, queries).

## Benefits

- **User Experience**: Fast, natural conversations with seamless task completion.
- **Efficiency**: Simplifies development by leveraging OpenAI's dialogue capabilities.
- **Scalability**: Supports diverse use cases, from support to scheduling.
- **Reliability**: FSMs guarantee robust task workflows.

## Example

User: "Book an appointment for tomorrow."  

OpenAI triggers book_appointment, and a FastAgent FSM prompts: "What time?"  
User says: "10 AM," while the conversation remains live for other queries.  
The agent confirms: "Book for tomorrow at 10 AM?" User agrees, task completes.  
OpenAI responds: "Appointment booked!"—delivered instantly via FastAgent.

Before ending the interaction, the bot asks: "Is there anything else I can help you with today?"  
User responds: "No, that's all I needed."  
Bot confirms: "I'm glad I could help. Your appointment is confirmed for tomorrow at 10 AM. Have a great day!"—ensuring problem resolution before disconnecting.

### Call Continuity Scenario

During an appointment booking, if the call disconnects unexpectedly:  
FastAgent detects the abrupt termination and automatically sends an SMS: "Our call was disconnected. Your appointment request was saved. Reply CALL to continue where we left off."  
When the user replies or calls back, the system retrieves the conversation context and FSM state.  
Bot greets: "Welcome back! We were booking an appointment for tomorrow at 10 AM. Would you like to continue or start over?"  
User confirms, and the conversation resumes from the saved state, ensuring no information is lost.

## Why FastAgent?

Built on FastAPI, FastAgent delivers unparalleled speed and precision. Its hybrid design—pairing an AI-driven conversational core with structured FSM agents—ensures dynamic, task-heavy voice interactions, making it ideal for real-time enterprise voice bots.
