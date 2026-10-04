from typing import Any

import httpx

from packages.tools.contracts import ToolAdapter, ToolContext, ToolSecurity
from packages.security.credentials import credentials

class WebSearchAdapter(ToolAdapter):
    name = "web.search"
    security = ToolSecurity(risk="medium", timeout_seconds=15.0, idempotent=True)

    async def invoke(self, arguments: dict[str, Any], context: ToolContext) -> Any:
        query = str(arguments["query"]).strip()
        if not query:
            raise ValueError("empty_search_query")
        api_key = credentials.get(context.tenant_id, "web.search")
        if not api_key:
            raise RuntimeError("search_provider_not_configured")
        count = min(max(int(arguments.get("count", 10)), 1), 20)
        async with httpx.AsyncClient(timeout=self.security.timeout_seconds) as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": count},
                headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
        return {
            "query": query,
            "results": [
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                }
                for item in (data.get("web", {}).get("results", []) or [])
            ],
        }
