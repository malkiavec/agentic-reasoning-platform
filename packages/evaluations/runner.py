from dataclasses import dataclass
from typing import Any, Awaitable, Callable

@dataclass(frozen=True)
class EvaluationCase:
    name: str
    prompt: str
    expected: Any = None
    metadata: dict[str, Any] | None = None

@dataclass(frozen=True)
class EvaluationResult:
    case: str
    passed: bool
    score: float
    output: Any = None
    error: str | None = None

class EvaluationRunner:
    """Deterministic regression runner for model, tool, memory, and agent changes."""

    def __init__(self, executor: Callable[[EvaluationCase], Awaitable[Any]]):
        self.executor = executor

    async def run(self, cases: list[EvaluationCase], scorer: Callable[[EvaluationCase, Any], float]) -> list[EvaluationResult]:
        results: list[EvaluationResult] = []
        for case in cases:
            try:
                output = await self.executor(case)
                score = max(0.0, min(1.0, float(scorer(case, output))))
                results.append(EvaluationResult(case.name, score >= 1.0, score, output))
            except Exception as exc:
                results.append(EvaluationResult(case.name, False, 0.0, error=f"{type(exc).__name__}:{exc}"))
        return results

BENCHMARK_SUITES = (
    "Terminal-Bench 2.1",
    "Agentic terminal coding",
    "Agentic IF Index",
    "SWEAtlas CodeBase QnA",
    "DeepSearchQA",
    "GDPVal-AA v2",
    "JobBench",
    "AutomationBench",
    "MRCR 256K-512K",
    "MRCR 512K-1M",
)
