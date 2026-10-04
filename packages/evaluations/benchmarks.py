from dataclasses import dataclass
from typing import Callable, Any

@dataclass(frozen=True)
class BenchmarkSpec:
    name: str
    task_type: str
    evaluator: Callable[[Any, Any], float]

class BenchmarkRunner:
    def run(self, spec: BenchmarkSpec, cases: list[tuple[Any, Any]], solver: Callable[[Any], Any]) -> dict:
        scores = [spec.evaluator(solver(inp), expected) for inp, expected in cases]
        return {"benchmark": spec.name, "cases": len(scores), "score": sum(scores) / len(scores) if scores else 0.0}
