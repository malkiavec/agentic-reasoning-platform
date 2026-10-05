#!/usr/bin/env python3
"""Live provider certification gate.

Each configured provider receives one minimal structured-output request. This proves
credential validity, request construction, response parsing, and the provider
contract without invoking the planner or external tools.
"""
import asyncio
import os
import sys

from packages.agent_runtime.models import ContentPart, ModelRequest
from packages.agent_runtime.providers.anthropic import AnthropicProvider
from packages.agent_runtime.providers.gemini import GeminiProvider
from packages.agent_runtime.providers.openai import OpenAIProvider

PROVIDERS = {
    "openai": (OpenAIProvider, "OPENAI_API_KEY", "OPENAI_MODEL"),
    "anthropic": (AnthropicProvider, "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"),
    "gemini": (GeminiProvider, "GEMINI_API_KEY", "GEMINI_MODEL"),
}

SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}


async def certify(provider_name: str) -> None:
    provider_cls, key_name, model_name = PROVIDERS[provider_name]
    key = os.getenv(key_name)
    if not key:
        raise RuntimeError(f"{provider_name}: missing {key_name}")
    model = os.getenv(model_name)
    if not model:
        raise RuntimeError(f"{provider_name}: missing {model_name}")
    provider = provider_cls(key)
    response = await provider.generate(
        ModelRequest(
            model=model,
            input=[ContentPart(type="text", data="Return JSON with ok=true.")],
            reasoning_effort="low",
            response_schema=SCHEMA,
            max_output_tokens=64,
        )
    )
    if response.structured_output != {"ok": True}:
        raise RuntimeError(
            f"{provider_name}: structured-output contract failed: {response.structured_output!r}"
        )
    if not response.provider_request_id:
        raise RuntimeError(f"{provider_name}: missing provider request id")


async def main() -> int:
    requested = [x.strip().lower() for x in os.getenv("PROVIDER_CERT_PROVIDERS", "").split(",") if x.strip()]
    if not requested:
        print("provider certification failed: no providers configured")
        return 1
    unknown = sorted(set(requested) - set(PROVIDERS))
    if unknown:
        print(f"provider certification failed: unsupported providers: {', '.join(unknown)}")
        return 1
    failures = []
    for provider in requested:
        try:
            await certify(provider)
            print(f"{provider}: live certification passed")
        except Exception as exc:
            failures.append(f"{provider}: {type(exc).__name__}: {exc}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
