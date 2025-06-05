# How To: Flow System

This guide provides step-by-step instructions for common tasks with the flow system.

## 🚀 Quick Start: Using the Card Replacement Flow

### 1. Basic Integration (5 minutes)

Replace your existing session initialization:

```python
# OLD: In telephony_realtime_bridge.py
from opusagent.function_handler import FunctionHandler

# Initialize function handler
self.function_handler = FunctionHandler(realtime_websocket)

# NEW: With flows
from opusagent.flows import create_default_flow_manager

# Create flow manager and activate card replacement
self.flow_manager = create_default_flow_manager()
self.flow_manager.activate_flow("card_replacement")

# Create function handler and register flow functions
self.function_handler = FunctionHandler(realtime_websocket)
self.flow_manager.register_with_function_handler(self.function_handler)
```

### 2. Update Session Configuration

Replace the tools array in `initialize_session()`:

```python
# OLD: Hard-coded tools
tools = [
    {
        "type": "function",
        "name": "get_balance",
        "description": "Get the user's account balance.",
        "parameters": {"type": "object", "properties": {}},
    },
    # ... many more tools
]

# NEW: From flows
tools = self.flow_manager.get_all_tools()
instructions = self.flow_manager.get_combined_system_instruction()

session_config = SessionConfig(
    # ... other config ...
    tools=tools,
    instructions=instructions,
)
```

## 🎯 Creating a New Flow: Complete Example

Let's create a "Balance Inquiry" flow step-by-step:

### Step 1: Create Directory Structure
```bash
mkdir opusagent/flows/balance_inquiry
touch opusagent/flows/balance_inquiry/__init__.py
touch opusagent/flows/balance_inquiry/prompts.py
touch opusagent/flows/balance_inquiry/tools.py
touch opusagent/flows/balance_inquiry/functions.py
touch opusagent/flows/balance_inquiry/flow.py
```

### Step 2: Define Prompts (`prompts.py`)
```python
"""Balance Inquiry Flow Prompts"""

SYSTEM_INSTRUCTION = """
You are a customer service agent helping customers check their account balance.

When a customer asks about their balance:
1. Call verify_identity to confirm their identity
2. Call get_account_balance to retrieve their balance
3. Present the balance clearly and ask if they need anything else
"""

IDENTITY_VERIFICATION_PROMPT = """
To help you with your account balance, I need to verify your identity.
Can you please provide your account number or the last 4 digits of your SSN?
"""

BALANCE_PRESENTATION_PROMPT = """
Your current account balance is ${balance:.2f}.
Is there anything else I can help you with today?
"""
```

### Step 3: Define Tools (`tools.py`)
```python
"""Balance Inquiry Flow Tools"""

VERIFY_IDENTITY_TOOL = {
    "type": "function",
    "name": "verify_identity",
    "description": "Verify customer identity for balance inquiry",
    "parameters": {
        "type": "object",
        "properties": {
            "account_number": {"type": "string"},
            "ssn_last_four": {"type": "string"},
        },
    },
}

GET_ACCOUNT_BALANCE_TOOL = {
    "type": "function",
    "name": "get_account_balance",
    "description": "Get the customer's current account balance",
    "parameters": {
        "type": "object",
        "properties": {
            "account_id": {"type": "string"},
        },
        "required": ["account_id"],
    },
}

def get_balance_inquiry_tools():
    return [VERIFY_IDENTITY_TOOL, GET_ACCOUNT_BALANCE_TOOL]
```

### Step 4: Implement Functions (`functions.py`)
```python
"""Balance Inquiry Flow Functions"""

import logging
from typing import Any, Dict
from .prompts import IDENTITY_VERIFICATION_PROMPT, BALANCE_PRESENTATION_PROMPT

logger = logging.getLogger(__name__)

def verify_identity(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Verify customer identity"""
    account_number = arguments.get("account_number", "")
    ssn_last_four = arguments.get("ssn_last_four", "")
    
    # Simulate identity verification
    if account_number or ssn_last_four:
        logger.info(f"Identity verification attempted")
        return {
            "status": "success",
            "verified": True,
            "account_id": "12345",  # Simulated account ID
            "prompt_guidance": "Identity verified. Now checking balance...",
            "next_action": "get_balance"
        }
    else:
        return {
            "status": "pending",
            "verified": False,
            "prompt_guidance": IDENTITY_VERIFICATION_PROMPT,
            "next_action": "retry_verification"
        }

def get_account_balance(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Get account balance"""
    account_id = arguments.get("account_id", "")
    
    # Simulate balance lookup
    balance = 2547.83  # Simulated balance
    
    formatted_prompt = BALANCE_PRESENTATION_PROMPT.format(balance=balance)
    
    logger.info(f"Balance retrieved for account {account_id}: ${balance}")
    
    return {
        "status": "success",
        "balance": balance,
        "account_id": account_id,
        "prompt_guidance": formatted_prompt,
        "next_action": "offer_additional_help"
    }

BALANCE_INQUIRY_FUNCTIONS = {
    "verify_identity": verify_identity,
    "get_account_balance": get_account_balance,
}

def get_balance_inquiry_functions():
    return BALANCE_INQUIRY_FUNCTIONS.copy()
```

### Step 5: Create Flow Class (`flow.py`)
```python
"""Balance Inquiry Flow"""

from typing import Any, Callable, Dict, List
from ..base_flow import BaseFlow
from .tools import get_balance_inquiry_tools
from .functions import get_balance_inquiry_functions
from .prompts import SYSTEM_INSTRUCTION

class BalanceInquiryFlow(BaseFlow):
    def __init__(self):
        super().__init__("balance_inquiry")

    def get_tools(self) -> List[Dict[str, Any]]:
        return get_balance_inquiry_tools()

    def get_functions(self) -> Dict[str, Callable]:
        return get_balance_inquiry_functions()

    def get_prompts(self) -> Dict[str, str]:
        return {
            "system_instruction": SYSTEM_INSTRUCTION,
        }

    def get_system_instruction(self) -> str:
        return SYSTEM_INSTRUCTION
```

### Step 6: Update Package Init (`__init__.py`)
```python
"""Balance Inquiry Flow Package"""

from .flow import BalanceInquiryFlow

__all__ = ["BalanceInquiryFlow"]
```

### Step 7: Register and Use the Flow
```python
from opusagent.flows.balance_inquiry import BalanceInquiryFlow

# Add to your flow manager
flow_manager.register_flow(BalanceInquiryFlow())
flow_manager.activate_flow("balance_inquiry")

# Or activate multiple flows
flow_manager.activate_flow("card_replacement")
flow_manager.activate_flow("balance_inquiry")
```

## 🔧 Integration Patterns

### Pattern 1: Single Flow Application
```python
# For apps that only need one flow at a time
class SingleFlowApp:
    def __init__(self, flow_name="card_replacement"):
        self.flow_manager = create_default_flow_manager()
        self.flow_manager.activate_flow(flow_name)
        
    def switch_flow(self, new_flow):
        # Deactivate all flows
        for flow in self.flow_manager.active_flows.copy():
            self.flow_manager.deactivate_flow(flow)
        # Activate new flow
        self.flow_manager.activate_flow(new_flow)
```

### Pattern 2: Multi-Flow Application
```python
# For apps that need multiple flows active simultaneously
class MultiFlowApp:
    def __init__(self):
        self.flow_manager = create_default_flow_manager()
        # Activate multiple flows
        self.flow_manager.activate_flow("card_replacement")
        self.flow_manager.activate_flow("balance_inquiry")
        
    def get_session_config(self):
        return {
            "tools": self.flow_manager.get_all_tools(),
            "instructions": self.flow_manager.get_combined_system_instruction(),
        }
```

### Pattern 3: Dynamic Flow Loading
```python
# For apps that determine flows based on user context
class DynamicFlowApp:
    def __init__(self):
        self.flow_manager = create_default_flow_manager()
        
    def setup_for_user(self, user_type):
        if user_type == "premium":
            self.flow_manager.activate_flow("card_replacement")
            self.flow_manager.activate_flow("loan_application")
        elif user_type == "basic":
            self.flow_manager.activate_flow("balance_inquiry")
```

## 🧪 Testing Your Flows

### Test Individual Functions
```python
def test_balance_inquiry_functions():
    from opusagent.flows.balance_inquiry import get_balance_inquiry_functions
    
    functions = get_balance_inquiry_functions()
    
    # Test identity verification
    result = functions["verify_identity"]({"account_number": "12345"})
    assert result["status"] == "success"
    assert result["verified"] == True
    
    # Test balance retrieval
    result = functions["get_account_balance"]({"account_id": "12345"})
    assert result["status"] == "success"
    assert "balance" in result
```

### Test Flow Configuration
```python
def test_flow_validation():
    from opusagent.flows.balance_inquiry import BalanceInquiryFlow
    
    flow = BalanceInquiryFlow()
    validation = flow.validate_flow_configuration()
    
    assert validation["valid"], f"Flow validation failed: {validation}"
    assert validation["tool_count"] > 0
    assert validation["function_count"] > 0
```

### Test Flow Manager Integration
```python
def test_flow_manager():
    manager = create_default_flow_manager()
    manager.activate_flow("balance_inquiry")
    
    tools = manager.get_all_tools()
    functions = manager.get_all_functions()
    
    assert len(tools) > 0
    assert len(functions) > 0
    assert "verify_identity" in functions
```

## 🚨 Common Issues & Solutions

### Issue 1: Function Not Found
```
Error: Function 'my_function' not implemented
```
**Solution**: Make sure the function name in `tools.py` matches the function name in `functions.py`:
```python
# tools.py
"name": "my_function"

# functions.py  
def my_function(arguments):  # ✅ Names match
    pass
```

### Issue 2: Import Errors
```
ImportError: cannot import name 'MyFlow' from 'opusagent.flows.my_flow'
```
**Solution**: Check your `__init__.py` exports:
```python
# flows/my_flow/__init__.py
from .flow import MyFlow
__all__ = ["MyFlow"]
```

### Issue 3: Tools Not Appearing in OpenAI
**Solution**: Make sure the flow is activated:
```python
flow_manager.activate_flow("my_flow")  # Must be called!
tools = flow_manager.get_all_tools()   # Now includes your tools
```

### Issue 4: System Instructions Not Working
**Solution**: Use the combined instructions:
```python
# ❌ Wrong - only gets one flow's instructions
instructions = flow.get_system_instruction()

# ✅ Correct - gets all active flows' instructions
instructions = flow_manager.get_combined_system_instruction()
```

## 📋 Checklist: Adding a New Flow

- [ ] Create flow directory: `opusagent/flows/my_flow/`
- [ ] Add `__init__.py` with exports
- [ ] Create `prompts.py` with all prompts
- [ ] Create `tools.py` with OpenAI tool definitions
- [ ] Create `functions.py` with implementations
- [ ] Create `flow.py` with main flow class
- [ ] Register flow in `flow_manager.py` (optional)
- [ ] Test functions individually
- [ ] Test flow validation
- [ ] Test integration with flow manager
- [ ] Update main application to use the flow

## 💡 Best Practices

1. **Keep Functions Simple**: Each function should do one thing well
2. **Use Descriptive Names**: Function and tool names should be self-explanatory
3. **Consistent Return Format**: All functions should return similar structure
4. **Error Handling**: Always handle missing or invalid arguments
5. **Logging**: Log important events for debugging
6. **Validation**: Use the flow validation methods to catch issues early
7. **Testing**: Test each component individually before integration

## 🔄 Migration from Existing Code

If you have existing functions in `function_handler.py`:

1. **Extract**: Copy function to flow's `functions.py`
2. **Create Tool**: Add OpenAI tool definition in `tools.py`
3. **Add Prompts**: Move any prompts to `prompts.py`
4. **Test**: Verify the function works in the new location
5. **Remove**: Delete old function from `function_handler.py`
6. **Update**: Use flow manager instead of direct registration

This approach lets you migrate one function at a time without breaking existing functionality.