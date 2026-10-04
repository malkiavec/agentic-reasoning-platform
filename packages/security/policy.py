from dataclasses import dataclass
from enum import IntEnum

class Risk(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass(frozen=True)
class Action:
    tool: str
    arguments: dict
    actor: str
    tenant_id: str

@dataclass(frozen=True)
class Decision:
    allowed: bool
    risk: Risk
    requires_approval: bool
    reason: str

class PolicyEngine:
    """Authorization boundary. Model output never grants permission."""
    def evaluate(self, action: Action) -> Decision:
        if not action.tool or not action.tenant_id or not action.actor:
            return Decision(False, Risk.CRITICAL, False, "missing_security_context")
        tool = action.tool.lower()
        if tool in {"shell", "computer_use", "browser_write"}:
            return Decision(True, Risk.HIGH, True, "high_risk_action_requires_approval")
        if tool.startswith("admin.") or tool.startswith("secrets."):
            return Decision(False, Risk.CRITICAL, False, "restricted_tool")
        return Decision(True, Risk.LOW, False, "allowed")
