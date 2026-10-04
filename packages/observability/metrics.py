from dataclasses import dataclass, field
from time import monotonic

@dataclass
class RunMetrics:
    started: float = field(default_factory=monotonic)
    tokens_in: int = 0
    tokens_out: int = 0
    tool_calls: int = 0
    errors: int = 0

    @property
    def elapsed_seconds(self) -> float:
        return monotonic() - self.started

    def snapshot(self) -> dict:
        return {
            "elapsed_seconds": round(self.elapsed_seconds, 6),
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "tool_calls": self.tool_calls,
            "errors": self.errors,
        }
