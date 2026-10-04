from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class EvalCase:
    name: str
    input: Any
    expected: Any
    tags: tuple[str, ...] = ()

@dataclass
class EvalResult:
    case: str
    passed: bool
    score: float
    details: dict[str, Any]

class Evaluator:
    def run(self, cases: list[EvalCase], fn) -> list[EvalResult]:
        results = []
        for case in cases:
            actual = fn(case.input)
            passed = actual == case.expected
            results.append(EvalResult(case.name, passed, 1.0 if passed else 0.0, {"actual": actual}))
        return results
