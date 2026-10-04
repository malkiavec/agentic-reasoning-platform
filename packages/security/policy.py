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
    """Authorization boundary. Model output never grants permission."""

    _approval_tools = frozenset({"shell", "computer_use", "browser_write"})
    _blocked_prefixes = ("admin.", "secrets.", "credential.", "identity.")
    _medium_prefixes = ("http.", "webhook", "database.", "git.", "slack.", "gmail.", "drive.")
    _max_argument_bytes = 256 * 1024

    def evaluate(
        self,
        action: Action,
        *,
        registered_tools: frozenset[str] = frozenset(),
    ) -> Decision:
        if not action.tool or not action.tenant_id or not action.actor:
            return Decision(False, Risk.CRITICAL, False, "missing_security_context")

        tool = action.tool.strip().lower()
        if not tool:
            return Decision(False, Risk.CRITICAL, False, "invalid_tool")

        if registered_tools is not None and tool not in registered_tools:
            return Decision(False, Risk.CRITICAL, False, "tool_not_registered")

        if tool.startswith(self._blocked_prefixes):
            return Decision(False, Risk.CRITICAL, False, "restricted_tool")

        if len(repr(action.arguments).encode("utf-8")) > self._max_argument_bytes:
            return Decision(False, Risk.HIGH, False, "arguments_too_large")

        if tool in self._approval_tools or tool.startswith(("computer.", "browser.write")):
            return Decision(True, Risk.HIGH, True, "high_risk_action_requires_approval")

        if tool == "http.rest" and str(action.arguments.get("method", "GET")).upper() not in {"GET", "HEAD"}:
            return Decision(True, Risk.HIGH, True, "http_write_requires_approval")

        if tool.startswith(self._medium_prefixes):
            return Decision(True, Risk.MEDIUM, False, "external_side_effect_possible")

        return Decision(True, Risk.LOW, False, "allowed")
