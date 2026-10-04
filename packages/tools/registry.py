import inspect
from dataclasses import dataclass, field
from typing import Any

from packages.tools.contracts import ToolAdapter, ToolContext, ToolSecurity

class CallableAdapter(ToolAdapter):
    def __init__(self, name: str, handler: Any, security: ToolSecurity):
        self.name = name
        self.security = security
        self._handler = handler

    async def invoke(self, arguments: dict[str, Any], context: ToolContext) -> Any:
        value = self._handler(**arguments)
        if inspect.isawaitable(value):
            return await value
        return value

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
    output_schema: dict[str, Any] | None = None

    @property
    def risk(self) -> str:
        return self.security.risk

    @property
    def requires_approval(self) -> bool:
        return self.security.requires_approval

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolSpec, ToolAdapter]] = {}

    def register(self, spec: ToolSpec, adapter: ToolAdapter | Any) -> None:
        name = spec.name.strip()
        if not name or name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        if not hasattr(adapter, "invoke"):
            adapter = CallableAdapter(name, adapter, spec.security)
        elif getattr(adapter, "name", None) != name:
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
        output_schema: dict[str, Any] | None = None,
    ) -> None:
        schema = input_schema or {"type": "object", "additionalProperties": True}
        self.register(
            ToolSpec(
                name=name,
                description=description,
                input_schema=schema,
                security=adapter.security,
                permissions=permissions,
                auth_requirements=auth_requirements,
                rate_limit_per_minute=rate_limit_per_minute,
                output_schema=output_schema,
            ),
            adapter,
        )
