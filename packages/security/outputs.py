from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class OutputPolicy:
    max_chars: int = 200_000
    allow_html: bool = False

class OutputValidator:
    def __init__(self, policy: OutputPolicy | None = None):
        self.policy = policy or OutputPolicy()

    def validate(self, value: Any) -> Any:
        if isinstance(value, str):
            if len(value) > self.policy.max_chars:
                raise ValueError("output_too_large")
            if not self.policy.allow_html and ("<script" in value.lower() or "javascript:" in value.lower()):
                raise ValueError("unsafe_output")
        return value
