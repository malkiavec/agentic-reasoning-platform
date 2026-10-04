from typing import Any
from packages.tools.contracts import ToolAdapter,ToolContext,ToolSecurity

class ExternalBoundaryAdapter(ToolAdapter):
    """Safe placeholder boundary: real integrations must implement credentials, egress, schema and policy checks."""
    def __init__(self,name:str,security:ToolSecurity|None=None): self.name=name; self.security=security or ToolSecurity(risk="medium")
    async def invoke(self,arguments:dict[str,Any],context:ToolContext)->Any:
        raise RuntimeError(f"external_adapter_not_configured:{self.name}")

EXTERNAL_TOOL_REGISTRY={
    "web.search":"Web / Search","browser":"Browser","computer_use":"Computer Use","github":"GitHub","gitlab":"GitLab",
    "slack":"Slack","discord":"Discord","gmail":"Gmail","google_drive":"Google Drive","notion":"Notion",
    "linear":"Linear","jira":"Jira","databases":"Databases","http.rest":"HTTP / REST APIs","webhooks":"Webhooks","mcp":"Custom MCP / API tools",
}

def register_external_boundaries(registry):
    for name,label in EXTERNAL_TOOL_REGISTRY.items():
        registry.register_external(name,label,ExternalBoundaryAdapter(name))
