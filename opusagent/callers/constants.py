from enum import Enum

class FailureConditions(Enum):
    """Enumeration of failure conditions for caller scenarios."""
    TRANSFERRED_TO_HUMAN = "transferred to human"
    CALL_TERMINATED = "call terminated"
    UNABLE_TO_VERIFY_IDENTITY = "unable to verify identity"
    AGENT_UNAVAILABLE = "agent unavailable"
    TECHNICAL_ISSUE = "technical issue"
    INSUFFICIENT_INFORMATION = "insufficient information" 