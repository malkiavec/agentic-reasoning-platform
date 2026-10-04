import json
import os
from typing import Any

class CredentialResolver:
    """Tenant-scoped credential boundary.

    Production should provide TOOL_CREDENTIALS_JSON through a secret manager.
    The resolver never exposes credentials to model prompts or tool arguments.
    """

    def __init__(self) -> None:
        raw = os.getenv("TOOL_CREDENTIALS_JSON", "{}")
        try:
            self._credentials: dict[str, dict[str, str]] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("invalid_tool_credentials_config") from exc

    def get(self, tenant_id: str, tool: str) -> str | None:
        tenant = self._credentials.get(tenant_id, {})
        if isinstance(tenant, dict) and tenant.get(tool):
            return str(tenant[tool])
        # Explicitly scoped environment fallback for development/legacy deployments.
        safe = "".join(ch if ch.isalnum() else "_" for ch in tenant_id).upper()
        return os.getenv(f"{tool.replace('.', '_').upper()}_TOKEN_{safe}")

credentials = CredentialResolver()
