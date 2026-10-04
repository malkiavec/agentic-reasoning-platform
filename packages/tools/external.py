from typing import Any
import os
from packages.tools.contracts import ToolAdapter,ToolContext,ToolSecurity

class ExternalBoundaryAdapter(ToolAdapter):
    """Safe placeholder boundary: real integrations must implement credentials, egress, schema and policy checks."""
    def __init__(self,name:str,security:ToolSecurity|None=None): self.name=name; self.security=security or ToolSecurity(risk="medium")
    async def invoke(self,arguments:dict[str,Any],context:ToolContext)->Any:
        raise RuntimeError(f"external_adapter_not_configured:{self.name}")

EXTERNAL_TOOL_REGISTRY={
    "web.search":"Web / Search","browser":"Browser","computer_use":"Computer Use","github":"GitHub","gitlab":"GitLab",
    "slack":"Slack","discord":"Discord","gmail":"Gmail","google_drive":"Google Drive","notion":"Notion",
    "linear":"Linear","jira":"Jira","databases":"Databases","webhooks":"Webhooks","mcp":"Custom MCP / API tools",
}

def register_external_boundaries(registry, *, exclude: set[str] | None = None):
    exclude = exclude or set()
    # Placeholder boundaries are intentionally not executable. Production agents must
    # only see adapters with a real implementation and credential boundary.
    if os.getenv("ENABLE_PLACEHOLDER_TOOLS", "false").lower() not in {"1", "true", "yes"}:
        return
    for name,label in EXTERNAL_TOOL_REGISTRY.items():
        if name in exclude:
            continue
        registry.register_external(name,label,ExternalBoundaryAdapter(name))
