from packages.tools.builtins import ApprovalProbeAdapter, EchoAdapter
from packages.tools.external import register_external_boundaries
from packages.tools.http_rest import HttpRestAdapter
from packages.tools.web_search import WebSearchAdapter
from packages.tools.github import GitHubAdapter, GitHubWriteAdapter
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
    register_external_boundaries(registry, exclude={"web.search", "github"})
    registry.register_external(
        "web.search", "Search the public web through the configured search provider",
        WebSearchAdapter(),
        input_schema={"type": "object", "properties": {
            "query": {"type": "string", "minLength": 1, "maxLength": 2000},
            "count": {"type": "integer", "minimum": 1, "maximum": 20},
        }, "required": ["query"], "additionalProperties": False},
    )
    registry.register_external(
        "github", "Read GitHub repositories, files, issues, and code",
        GitHubAdapter(),
        input_schema={"type": "object", "properties": {
            "action": {"type": "string", "enum": ["get_repository", "list_issues", "get_file", "search_code"]},
            "owner": {"type": "string", "maxLength": 100},
            "repo": {"type": "string", "maxLength": 100},
            "path": {"type": "string", "maxLength": 1000},
            "ref": {"type": "string", "maxLength": 256},
            "query": {"type": "string", "maxLength": 1000},
            "state": {"type": "string", "enum": ["open", "closed", "all"]},
            "per_page": {"type": "integer", "minimum": 1, "maximum": 100},
        }, "required": ["action"], "additionalProperties": False},
    )
    registry.register_external(
        "github.write", "Write to GitHub; always requires human approval",
        GitHubWriteAdapter(),
        input_schema={"type": "object", "properties": {
            "owner": {"type": "string", "maxLength": 100},
            "repo": {"type": "string", "maxLength": 100},
            "method": {"type": "string", "enum": ["POST", "PATCH", "PUT", "DELETE"]},
            "path": {"type": "string", "maxLength": 1000},
            "body": {},
        }, "required": ["owner", "repo", "method", "path"], "additionalProperties": False},
    )
    registry.register_external(
        "http.rest",
        "Perform an outbound HTTP request through the SSRF and egress boundary",
        HttpRestAdapter(),
        input_schema={
            "type": "object",
            "properties": {
                "method": {"type": "string", "enum": ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"]},
                "url": {"type": "string", "maxLength": 2048},
                "headers": {"type": "object", "additionalProperties": {"type": "string"}},
                "json": {},
                "timeout_seconds": {"type": "number", "minimum": 0.1, "maximum": 20},
            },
            "required": ["url"],
            "additionalProperties": False,
        },
        permissions=frozenset({"network.egress"}),
    )
    return registry

EXTERNAL_TOOL_FAMILIES = (
    "web.search", "browser", "computer_use", "github", "gitlab",
    "slack", "discord", "gmail", "google_drive", "notion", "linear",
    "jira", "databases", "http.rest", "webhooks", "mcp",
)
