#!/usr/bin/env python3
"""Provider certification prerequisite gate."""
import os
from packages.agent_runtime.provider_factory import build_gateway_from_env

def main() -> int:
    build_gateway_from_env()
    providers = [x.strip() for x in os.getenv("PROVIDER_CERT_PROVIDERS", "").split(",") if x.strip()]
    missing = []
    for provider in providers:
        key = f"PROVIDER_CERT_{provider.upper().replace('-', '_')}"
        if not os.getenv(key):
            missing.append(f"{provider}: missing {key}")
    if missing:
        print("\n".join(missing))
        return 1
    print(f"provider certification prerequisites satisfied: {', '.join(providers) or 'none'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
