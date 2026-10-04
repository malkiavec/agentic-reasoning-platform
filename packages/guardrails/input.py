import re
from dataclasses import dataclass

INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all|any|the)\s+previous\s+instructions", re.I),
    re.compile(r"reveal\s+(the\s+)?(system|developer)\s+prompt", re.I),
    re.compile(r"disable\s+(the\s+)?security|guardrails", re.I),
    re.compile(r"follow\s+instructions\s+from\s+(this|the)\s+(webpage|document)", re.I),
]

@dataclass(frozen=True)
class GuardrailVerdict:
    allowed: bool
    findings: list[str]

def inspect_input(text: str) -> tuple[bool, list[str]]:
    findings = [p.pattern for p in INJECTION_PATTERNS if p.search(text)]
    return not findings, findings

class InputGuardrail:
    """Protective boundary for untrusted user and retrieved text."""

    def check(self, text: str) -> GuardrailVerdict:
        allowed, findings = inspect_input(text)
        return GuardrailVerdict(allowed=allowed, findings=findings)
