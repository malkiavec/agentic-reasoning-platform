from dataclasses import dataclass
from enum import IntEnum
from typing import Any

class Risk(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass(frozen=True)
class Action:
    tool: str
    arguments: dict[str, Any]
    actor: str
    tenant_id: str

@dataclass(frozen=True)
class Decision:
    allowed: bool
    risk: Risk
    requires_approval: bool
    reason: str

class PolicyEngine:
    """Authorization boundary. Models never grant themselves permission."""
    def evaluate(self, action: Action) -> Decision:
        if not action.tool or not action.tenant_id:
            return Decision(False, Risk.CRITICAL, False, "invalid security context")
        risk = Risk.HIGH if action.tool in {"shell", "computer_use"} else Risk.LOW
        return Decision(True, risk, risk >= Risk.HIGH, "policy evaluated")
