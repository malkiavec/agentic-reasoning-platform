#!/usr/bin/env python3
"""Authenticated staging smoke test.

The script intentionally performs only read-safe control-plane operations.
"""
import os
import sys

import httpx


def main() -> int:
    base = os.environ["CONTROL_PLANE_URL"].rstrip("/")
    token = os.environ["CONTROL_PLANE_TOKEN"]
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=base, headers=headers, timeout=15.0) as client:
        checks = [
            ("health", "/health", 200),
            ("ready", "/ready", 200),
            ("tools", "/v1/tools", 200),
            ("runs", "/v1/runs?limit=1", 200),
        ]
        for name, path, expected in checks:
            response = client.get(path)
            if response.status_code != expected:
                print(f"{name}: expected {expected}, got {response.status_code}: {response.text[:500]}", file=sys.stderr)
                return 1
        print("staging smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
