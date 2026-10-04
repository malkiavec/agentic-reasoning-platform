from dataclasses import dataclass
from typing import Any, Callable

@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    risk: str = "low"
    requires_approval: bool = False

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolSpec, Callable[..., Any]]] = {}

    def register(self, spec: ToolSpec, handler: Callable[..., Any]) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = (spec, handler)

    def get(self, name: str) -> ToolSpec:
        return self._tools[name][0]

    def list(self) -> list[ToolSpec]:
        return [x[0] for x in self._tools.values()]
