#!/usr/bin/env python3
"""Bounded control-plane load test with explicit pass/fail thresholds."""
import asyncio
import os
import statistics
import time

import httpx


async def worker(client: httpx.AsyncClient, count: int, latencies: list[float], failures: list[int]) -> None:
    for _ in range(count):
        started = time.perf_counter()
        response = await client.get("/v1/tools")
        latencies.append(time.perf_counter() - started)
        if response.status_code != 200:
            failures.append(response.status_code)


async def main() -> int:
    base = os.environ["CONTROL_PLANE_URL"].rstrip("/")
    token = os.environ["CONTROL_PLANE_TOKEN"]
    concurrency = int(os.getenv("LOAD_CONCURRENCY", "10"))
    requests_per_worker = int(os.getenv("LOAD_REQUESTS_PER_WORKER", "25"))
    max_failure_rate = float(os.getenv("LOAD_MAX_FAILURE_RATE", "0.01"))
    max_p95_seconds = float(os.getenv("LOAD_MAX_P95_SECONDS", "1.5"))

    latencies: list[float] = []
    failures: list[int] = []
    limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(
        base_url=base,
        headers={"Authorization": f"Bearer {token}"},
        timeout=15.0,
        limits=limits,
    ) as client:
        started = time.perf_counter()
        await asyncio.gather(*(worker(client, requests_per_worker, latencies, failures) for _ in range(concurrency)))
    elapsed = time.perf_counter() - started
    p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies, default=0)
    total = len(latencies)
    failure_rate = len(failures) / total if total else 1.0
    print(f"requests={total} elapsed={elapsed:.2f}s p95={p95:.3f}s failures={len(failures)} rate={failure_rate:.4f}")
    return int(total == 0 or failure_rate > max_failure_rate or p95 > max_p95_seconds)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
