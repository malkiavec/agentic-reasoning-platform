from dataclasses import dataclass, field
from time import monotonic
from threading import Lock

@dataclass
class RunMetrics:
    started: float = field(default_factory=monotonic)
    completed: int = 0
    failed: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record(self, *, input_tokens=0, output_tokens=0, tool_calls=0, ok=True) -> None:
        with self._lock:
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.tool_calls += tool_calls
            if ok: self.completed += 1
            else: self.failed += 1

    def snapshot(self) -> dict:
        with self._lock:
            total=self.completed+self.failed
            return {"uptime_seconds": round(monotonic()-self.started,2),
                    "completed_runs":self.completed,"failed_runs":self.failed,
                    "success_rate": round(self.completed/total,4) if total else 1.0,
                    "input_tokens":self.input_tokens,"output_tokens":self.output_tokens,
                    "tool_calls":self.tool_calls}
