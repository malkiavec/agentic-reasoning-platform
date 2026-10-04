from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class PlanStep:
    id: str
    tool: str
    arguments: dict[str, Any]
    parallel_group: str | None = None

class Planner:
    """Provider-neutral planner boundary. The mock planner is deterministic and safe."""
    def plan(self, prompt: str, max_steps: int = 20) -> list[PlanStep]:
        # No arbitrary tool names are inferred from user text. Real providers must emit
        # structured plans that are subsequently validated against the ToolRegistry.
        return [PlanStep(id="final", tool="__final__", arguments={"prompt": prompt})][:max_steps]
