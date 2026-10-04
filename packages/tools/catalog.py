from packages.tools.builtins import ApprovalProbeAdapter, EchoAdapter
from packages.tools.external import register_external_boundaries
from packages.tools.registry import ToolRegistry, ToolSpec

def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            "echo",
            "Return text without external side effects",
            {
                "type": "object",
                "properties": {"text": {"type": "string", "maxLength": 10000}},
                "required": ["text"],
                "additionalProperties": False,
            },
        ),
        EchoAdapter(),
    )
    registry.register(
        ToolSpec(
            "approval_probe",
            "Test an approval-gated action",
            {
                "type": "object",
                "properties": {"action": {"type": "string", "maxLength": 10000}},
                "required": ["action"],
                "additionalProperties": False,
            },
        ),
        ApprovalProbeAdapter(),
    )
    register_external_boundaries(registry)
    return registry

EXTERNAL_TOOL_FAMILIES = (
    "web.search", "browser", "computer_use", "github", "gitlab",
    "slack", "discord", "gmail", "google_drive", "notion", "linear",
    "jira", "databases", "http.rest", "webhooks", "mcp",
)
