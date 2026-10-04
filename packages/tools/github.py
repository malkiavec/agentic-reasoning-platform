import os
from typing import Any

import httpx

from packages.tools.contracts import ToolAdapter, ToolContext, ToolSecurity

class GitHubAdapter(ToolAdapter):
    name = "github"
    security = ToolSecurity(risk="medium", timeout_seconds=20.0, idempotent=True)

    async def invoke(self, arguments: dict[str, Any], context: ToolContext) -> Any:
        token = os.getenv("GITHUB_TOOL_TOKEN", "")
        if not token:
            raise RuntimeError("github_tool_token_not_configured")
        action = arguments["action"]
        owner = arguments.get("owner")
        repo = arguments.get("repo")
        if action in {"get_repository", "list_issues", "get_file"} and (not owner or not repo):
            raise ValueError("owner_and_repo_required")
        base = "https://api.github.com"
        if action == "get_repository":
            method, path, params, body = "GET", f"/repos/{owner}/{repo}", None, None
        elif action == "list_issues":
            method, path, params, body = "GET", f"/repos/{owner}/{repo}/issues", {"state": arguments.get("state", "open"), "per_page": min(int(arguments.get("per_page", 30)), 100)}, None
        elif action == "get_file":
            method, path, params, body = "GET", f"/repos/{owner}/{repo}/contents/{arguments['path'].lstrip('/')}", {"ref": arguments.get("ref")} if arguments.get("ref") else None, None
        elif action == "search_code":
            method, path, params, body = "GET", "/search/code", {"q": arguments["query"], "per_page": min(int(arguments.get("per_page", 30)), 100)}, None
        else:
            raise ValueError("unsupported_github_action")
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(timeout=self.security.timeout_seconds) as client:
            response = await client.request(method, base + path, params=params, json=body, headers=headers)
            response.raise_for_status()
            return response.json()

class GitHubWriteAdapter(GitHubAdapter):
    name = "github.write"
    security = ToolSecurity(risk="high", requires_approval=True, timeout_seconds=20.0, idempotent=False)

    async def invoke(self, arguments: dict[str, Any], context: ToolContext) -> Any:
        token = os.getenv("GITHUB_TOOL_TOKEN", "")
        if not token:
            raise RuntimeError("github_tool_token_not_configured")
        owner, repo = arguments["owner"], arguments["repo"]
        method = arguments.get("method", "POST").upper()
        allowed = {"POST", "PATCH", "PUT", "DELETE"}
        if method not in allowed:
            raise ValueError("github_write_method_not_allowed")
        path = arguments["path"].lstrip("/")
        body = arguments.get("body")
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(timeout=self.security.timeout_seconds) as client:
            response = await client.request(method, f"https://api.github.com/repos/{owner}/{repo}/{path}", json=body, headers=headers)
            response.raise_for_status()
            return response.json() if response.content else {"status": response.status_code}
