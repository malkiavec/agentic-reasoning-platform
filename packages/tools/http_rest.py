import os
from typing import Any

import httpx

from packages.security.ssrf import SSRFViolation, validate_url
from packages.tools.contracts import ToolAdapter, ToolContext, ToolSecurity

class HttpRestAdapter(ToolAdapter):
    name = "http.rest"
    security = ToolSecurity(
        risk="medium",
        requires_approval=False,
        timeout_seconds=20.0,
        idempotent=True,
    )

    def __init__(self, allowed_domains: set[str] | None = None):
        raw = os.getenv("HTTP_ALLOWED_DOMAINS", "")
        self.allowed_domains = allowed_domains or {
            domain.strip().lower().lstrip(".")
            for domain in raw.split(",")
            if domain.strip()
        }

    def is_idempotent(self, arguments: dict[str, Any]) -> bool:
        return str(arguments.get("method", "GET")).upper() in {"GET", "HEAD"}

    def _allowed(self, url: str) -> bool:
        from urllib.parse import urlparse
        host = (urlparse(url).hostname or "").lower().rstrip(".")
        return bool(self.allowed_domains) and any(
            host == domain or host.endswith("." + domain)
            for domain in self.allowed_domains
        )

    async def invoke(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> dict[str, Any]:
        method = str(arguments.get("method", "GET")).upper()
        url = validate_url(str(arguments["url"]))
        if not self._allowed(url):
            raise SSRFViolation("http_domain_not_allowlisted")
        if method not in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError("unsupported_http_method")

        headers = {
            str(key): str(value)
            for key, value in (arguments.get("headers") or {}).items()
            if str(key).lower() not in {
                "authorization", "proxy-authorization", "cookie", "set-cookie"
            }
        }
        payload = arguments.get("json")
        timeout = min(float(arguments.get("timeout_seconds", 20)), 20.0)

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            max_redirects=0,
        ) as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                json=payload,
            )

        body = response.content[:1_000_000]
        return {
            "status_code": response.status_code,
            "headers": {
                key: value
                for key, value in response.headers.items()
                if key.lower() not in {"set-cookie", "authorization"}
            },
            "body": body.decode(response.encoding or "utf-8", errors="replace"),
            "tenant_id": context.tenant_id,
        }
