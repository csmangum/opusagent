### 🎯 Purpose

Integrate **GPT-4o's structured function calling** into our voice-enabled customer support agent, using a purpose-built architecture. This should allow for a natural conversation flow with reliable back-end execution, and provide a modular, scalable way to automate multistep support flows (e.g., card replacement, address confirmation, etc.).

---

### 🏗️ Architecture Summary

**User Input (Voice or Text)** →
**FastAgent (GPT-4o)** →
**Tool Calls (Structured JSON)** →
**MCP Handler executes logic / triggers services** →
**FastAgent resumes dialog with output**

---

### 💡 Why This Matters

GPT-4o enables:

* **Natural language understanding** and decision-making
* **Deterministic execution** through function calls
* A **clean separation** between conversational logic and execution logic

MCP makes it easy to:

* Route tool calls to internal services (CRM, billing, etc.)
* Test, debug, and log each action independently
* Compose workflows across agents and tasks

---

### 🧩 Simple Path: Card Replacement Flow

| Step                         | Agent State             | Tool Called          | State Update (LLM)                        | Bot Response                                      |
| ---------------------------- | -------------------------- | -------------------- | ------------------------------ | -------------------------------------------------- |
| User: "I need a new card."   | Determine intent           | `call_intent`        | "card_replacement"            | "Which card would you like to replace?"           |
| User: "My Platinum card."    | Confirm account            | `replace_card`       | `"member_account": "Platinum"` | "Can you tell me the reason you need a replacement?" |
| User: "It was stolen."       | Ask reason for replacement | `replacement_reason` | `"reason": "stolen"`           | "Thank you. Would you like to use the address we have on file for delivery?" |
| User: "Yes, that address."   | Confirm address on file    | `confirm_address`    | `"address_correct": true`      | "Great, your new card will be sent to your address on file." |
|  | Finish flow                | `wrap_up`            | polite closure                 | "Your card will arrive in 3-5 business days. Is there anything else I can help you with today?" |

Each tool call is received via MCP and handled independently of the conversation.

---

### 🧩 Edge Path: Card Replacement Flow

| Step                         | Agent State             | Tool Called          | LLM Result                         | Bot Response                                      |
| ---------------------------- | -------------------------- | -------------------- | ------------------------------ | -------------------------------------------------- |
| User: "I need a new card."   | Determine intent           | `call_intent`        | "card_replacement"            | "Which card would you like to replace?"           |
| User: "My Platinum card."    | Confirm account            | `replace_card`       | `"member_account": "Platinum"` | "Can you tell me the reason you need a replacement?" |
| User: "It was stolen."       | Ask reason for replacement | `replacement_reason` | `"reason": "stolen"`           | "Thank you. Would you like to use the address we have on file for delivery?" |
| User: "No, use a different address."   | Confirm address on file    | `confirm_address`    | `"address_correct": false`      | "Thank you. We'll use the address you provided." |
| | Finish flow                | `wrap_up`            | polite closure                 | "Your card will arrive in 3-5 business days. Is there anything else I can help you with today?" |

### 🛠 Technical Details

* We define all callable functions (tools) using [OpenAI function schema format](https://platform.openai.com/docs/guides/function-calling).
* `FastAgent` manages the GPT-4o loop and handles tool\_call output.
* Each function (e.g., `replacement_reason`) is registered in MCP using `@register_handler(...)`.
* Optional tool logic can be async, trigger microservices, or simulate internal responses.

---

### 🔄 Sample Function Definition

```python
{
  "type": "function",
  "function": {
    "name": "replacement_reason",
    "description": "Determine reason for card replacement",
    "parameters": {
      "type": "object",
      "properties": {
        "reason": {
          "type": "string",
          "enum": ["lost_or_damaged", "stolen", "other"]
        }
      },
      "required": ["reason"]
    }
  }
}
```

---

### ✅ Benefits

* **Modular**: Each function is an isolated, testable unit.
* **Scalable**: We can define dozens of flows this way.
* **Voice-compatible**: Works with Whisper → GPT-4o → TTS pipelines.
* **Audit-friendly**: Function calls can be logged, replayed, or debugged in full.

---

### 🔜 Next Steps

1. Implement base tools (`call_intent`, `replace_card`, `confirm_address`, etc.) in MCP.
2. Define the agent using FastAgent with GPT-4o and `tools=[...]`.
3. Wrap tool execution in mock/stub logic initially; connect to services later.
4. Add logging and monitoring for each tool call.
