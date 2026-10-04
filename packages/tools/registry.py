from dataclasses import dataclass, field
from typing import Any

from packages.tools.contracts import ToolAdapter, ToolSecurity

@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    security: ToolSecurity = field(default_factory=ToolSecurity)
    permissions: frozenset[str] = frozenset()
    auth_requirements: frozenset[str] = frozenset()
    allowed_agents: frozenset[str] | None = None
    rate_limit_per_minute: int = 60

    @property
    def risk(self) -> str:
        return self.security.risk

    @property
    def requires_approval(self) -> bool:
        return self.security.requires_approval

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolSpec, ToolAdapter]] = {}

    def register(self, spec: ToolSpec, adapter: ToolAdapter) -> None:
        name = spec.name.strip()
        if not name or name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        if getattr(adapter, "name", None) != name:
            raise ValueError("adapter_name_mismatch")
        if spec.rate_limit_per_minute < 1:
            raise ValueError("invalid_tool_rate_limit")
        self._tools[name] = (spec, adapter)

    def get(self, name: str) -> ToolSpec | None:
        item = self._tools.get(name)
        return item[0] if item else None

    def adapter(self, name: str) -> ToolAdapter | None:
        item = self._tools.get(name)
        return item[1] if item else None

    def list(self) -> list[ToolSpec]:
        return [item[0] for item in self._tools.values()]

    def register_external(
        self,
        name: str,
        description: str,
        adapter: ToolAdapter,
        *,
        input_schema: dict[str, Any] | None = None,
        permissions: frozenset[str] = frozenset(),
        auth_requirements: frozenset[str] = frozenset(),
        rate_limit_per_minute: int = 60,
    ) -> None:
        schema = input_schema or {
            "type": "object",
            "additionalProperties": True,
        }
        self.register(
            ToolSpec(
                name=name,
                description=description,
                input_schema=schema,
                security=adapter.security,
                permissions=permissions,
                auth_requirements=auth_requirements,
                rate_limit_per_minute=rate_limit_per_minute,
            ),
            adapter,
        )
