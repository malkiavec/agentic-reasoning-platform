#!/usr/bin/env python3
"""Integration certification prerequisite gate; never prints secret values."""
import os

REQUIRED = {
    "gitlab": ("GITLAB_CERT_TOKEN",),
    "slack": ("SLACK_CERT_TOKEN",),
    "discord": ("DISCORD_CERT_TOKEN",),
    "gmail": ("GMAIL_CERT_TOKEN",),
    "google_drive": ("GOOGLE_DRIVE_CERT_TOKEN",),
    "notion": ("NOTION_CERT_TOKEN",),
    "linear": ("LINEAR_CERT_TOKEN",),
    "jira": ("JIRA_CERT_TOKEN", "JIRA_CERT_BASE_URL"),
    "databases": ("DATABASE_CERT_DSN",),
    "webhooks": ("WEBHOOK_CERT_TOKEN", "WEBHOOK_CERT_URL"),
    "mcp": ("MCP_CERT_TOKEN", "MCP_CERT_URL"),
}

def main() -> int:
    requested = [x.strip() for x in os.getenv("INTEGRATION_CERT_TOOLS", "").split(",") if x.strip()]
    missing = []
    for tool in requested:
        for key in REQUIRED.get(tool, ()):
            if not os.getenv(key):
                missing.append(f"{tool}: missing {key}")
    if missing:
        print("\n".join(missing))
        return 1
    print(f"integration certification prerequisites satisfied: {', '.join(requested) or 'none'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
