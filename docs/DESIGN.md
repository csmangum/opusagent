### Conversational Bot Design: Hybrid Stateful LLM Layer and FSM Architecture

**Overview**  
This design outlines a real-time conversational bot that integrates the **AudioCodes VoiceAI Connect (VAIC) API** for voice input and the **OpenAI Realtime API** for voice generation and dialogue management. The bot facilitates seamless voice interactions by passing base64-encoded audio chunks between the two APIs, maintaining conversational state, and executing complex tasks via function calls. It employs a **hybrid architecture**: a **Stateful LLM Layer** main conversational flow for natural dialogue and **finite state machine (FSM)** agents for structured, multi-step functions, ensuring low latency and robust task execution.

**Core Components**  
1. **Main Conversational Flow (Stateful LLM Layer)**:
   - **Purpose**: Manages the primary dialogue by acting as a lightweight intermediary between AudioCodes and OpenAI APIs.
   - **Functionality**:
     - Forwards audio input from AudioCodes (`userStream.chunk`) to OpenAI (`input_audio_buffer.append`).
     - Streams OpenAI's audio responses (`response.audio.delta`) to AudioCodes (`playStream.chunk`).
     - Leverages OpenAI's stateful context for natural language understanding, intent recognition, and conversation continuity.
     - Detects and delegates function calls from OpenAI to specialized agents.
   - **Rationale**: OpenAI's built-in state management eliminates the need for an explicit FSM, reducing latency and simplifying dialogue handling.

2. **FSM Agents for Complex Functions**:
   - **Purpose**: Handles multi-step tasks (e.g., booking an appointment) triggered by OpenAI function calls.
   - **Functionality**:
     - Instantiated when OpenAI triggers a function (e.g., `book_appointment`).
     - Uses a finite state machine with defined states (e.g., `CollectDate`, `CollectTime`, `Confirm`, `Execute`) to manage task-specific workflows.
     - Interacts with OpenAI to prompt users for additional input and processes responses.
     - Returns results to OpenAI via `conversation.item.create` (type `function_call_output`) for integration into the dialogue.
   - **Rationale**: FSMs provide structured control for complex tasks, ensuring all required data is collected and tasks are executed reliably.
   - **Implementation**: Based on the Finite State Agent (FSA) architecture, providing structured, controllable, and dynamic conversational agents. See [FSA Documentation](opusagent/fsa/README.md) for details.

3. **WebSocket Managers**:
   - **AudioCodes Connection**: Handles incoming audio streams and sends audio responses.
   - **OpenAI Connection**: Manages audio input/output and function call events.

**Interaction Flow**  
1. **Voice Input**: AudioCodes sends base64-encoded audio chunks (`userStream.chunk`), which the bot forwards to OpenAI.
2. **Dialogue Processing**: OpenAI processes audio, maintains context, and generates responses or function calls.
3. **Response Handling**:
   - For audio responses, the bot streams OpenAI's output to AudioCodes.
   - For function calls, the bot spins off an FSM agent to manage the task, collecting data and executing the function.
4. **Function Completion**: FSM agents return results to OpenAI, which resumes the main conversational flow.

**Key Features**  
- **Statefulness**: OpenAI's internal context ensures seamless multi-turn conversations without bot-side state management.
- **Low Latency**: Direct audio passthrough and minimal bot processing optimize real-time performance.
- **Modularity**: FSM agents are isolated for specific functions, enabling easy addition of new tasks.
- **Robustness**: Structured FSMs ensure reliable execution of complex tasks, while OpenAI handles dynamic dialogue.

**Design Rationale**  
- **Stateful LLM Layer Main Flow**: Using OpenAI's stateful API avoids the complexity and potential latency of an FSM for general conversation, leveraging advanced natural language capabilities.
- **FSM Agents**: Dedicated FSMs for functions provide clarity and control for structured tasks, complementing OpenAI's flexibility.
- **Hybrid Approach**: Combines the strengths of OpenAI's dynamic dialogue management with the precision of FSMs for task execution, balancing simplicity and functionality.

**Benefits**  
- **User Experience**: Natural, responsive conversations with seamless task execution.
- **Scalability**: Easily extendable with new FSM-based functions.
- **Maintainability**: Clear separation of concerns between dialogue and task management.
- **Performance**: Optimized for low-latency voice interactions.

**Use Case Example**  
When a user says, "Book an appointment for tomorrow," the bot forwards the audio to OpenAI, which triggers the `book_appointment` function. An FSM agent collects the date, time, and confirmation, executes the booking, and returns the result. OpenAI then generates a voice response, "Appointment booked for tomorrow at 10 AM," streamed to the user via AudioCodes.
