from packages.tools.registry import ToolRegistry,ToolSpec
from packages.tools.builtins import EchoAdapter,ApprovalProbeAdapter

def build_default_registry()->ToolRegistry:
    r=ToolRegistry()
    r.register(ToolSpec("echo","Return text without external side effects",{"type":"object","properties":{"text":{"type":"string"}},"required":["text"],"additionalProperties":False}),EchoAdapter())
    r.register(ToolSpec("approval_probe","Test an approval-gated action",{"type":"object","properties":{"action":{"type":"string"}},"required":["action"],"additionalProperties":False}),ApprovalProbeAdapter())
    return r

EXTERNAL_TOOL_FAMILIES=("web.search","browser","computer_use","github","gitlab","slack","discord","gmail","google_drive","notion","linear","jira","databases","http.rest","webhooks","mcp")
