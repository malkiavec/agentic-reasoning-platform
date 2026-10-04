from dataclasses import dataclass,field
from typing import Any
from packages.tools.contracts import ToolAdapter,ToolSecurity
@dataclass(frozen=True)
class ToolSpec:
    name:str; description:str; input_schema:dict[str,Any]
    security:ToolSecurity=field(default_factory=ToolSecurity)
    permissions:frozenset[str]=frozenset(); auth_requirements:frozenset[str]=frozenset()
    allowed_agents:frozenset[str]|None=None; rate_limit_per_minute:int=60
    @property
    def risk(self): return self.security.risk
    @property
    def requires_approval(self): return self.security.requires_approval
class ToolRegistry:
    def __init__(self): self._tools:dict[str,tuple[ToolSpec,ToolAdapter]]={}
    def register(self,spec:ToolSpec,adapter:ToolAdapter):
        if spec.name in self._tools: raise ValueError(f"tool already registered: {spec.name}")
        if getattr(adapter,"name",None)!=spec.name: raise ValueError("adapter_name_mismatch")
        self._tools[spec.name]=(spec,adapter)
    def get(self,name):
        item=self._tools.get(name); return item[0] if item else None
    def adapter(self,name):
        item=self._tools.get(name); return item[1] if item else None
    def list(self): return [x[0] for x in self._tools.values()]
    def register_external(self,name,description,adapter):
        schema={"type":"object","additionalProperties":True}
        self.register(ToolSpec(name,description,schema,security=adapter.security),adapter)
