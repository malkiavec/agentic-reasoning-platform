#!/usr/bin/env python3
"""Live integration certification through ToolExecutor.

CERT_ACTIONS_JSON maps tool names to read-safe arguments. Approval-gated tools
may be listed in CERT_EXPECT_APPROVAL_TOOLS; they must return approval_pending
without reaching the adapter. This keeps destructive certification side-effect free.
"""
import asyncio
import json
import os
import sys

from packages.db.session import SessionLocal
from packages.hitl.bridge import PersistentApprovalService
from packages.security.policy import PolicyEngine
from packages.tools.catalog import build_default_registry
from packages.tools.execution import ToolExecutor


async def main() -> int:
    raw = os.getenv("CERT_ACTIONS_JSON", "")
    if not raw:
        print("integration certification failed: CERT_ACTIONS_JSON is required", file=sys.stderr)
        return 1
    try:
        actions = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"integration certification failed: invalid CERT_ACTIONS_JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(actions, dict) or not actions:
        print("integration certification failed: CERT_ACTIONS_JSON must be a non-empty object", file=sys.stderr)
        return 1

    tenant_id = os.getenv("CERT_TENANT_ID")
    actor = os.getenv("CERT_ACTOR", "staging-certifier")
    run_id = os.getenv("CERT_RUN_ID")
    expected_approval = {
        x.strip() for x in os.getenv("CERT_EXPECT_APPROVAL_TOOLS", "").split(",") if x.strip()
    }
    if not tenant_id:
        print("integration certification failed: CERT_TENANT_ID is required", file=sys.stderr)
        return 1

    executor = ToolExecutor(
        build_default_registry(),
        PolicyEngine(),
        PersistentApprovalService(SessionLocal),
    )
    failures = []
    for tool, arguments in actions.items():
        if not isinstance(tool, str) or not isinstance(arguments, dict):
            failures.append(f"{tool}: action must be an object")
            continue
        result = await executor.execute(
            tool,
            arguments,
            actor=actor,
            tenant_id=tenant_id,
            run_id=run_id,
        )
        if tool in expected_approval:
            if result.error != "approval_pending":
                failures.append(f"{tool}: expected approval_pending, got {result.error}")
            else:
                print(f"{tool}: approval gate passed")
        elif not result.ok:
            failures.append(f"{tool}: execution failed: {result.error}")
        else:
            print(f"{tool}: live Tool Registry certification passed")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
