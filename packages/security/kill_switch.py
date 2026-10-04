import os

from redis.asyncio import Redis

class KillSwitch:
    """Distributed emergency stop backed by Redis; fails closed if Redis is unavailable."""

    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379/0")

    async def is_active(self, tenant_id: str) -> bool:
        redis = Redis.from_url(self.redis_url, decode_responses=True)
        try:
            values = await redis.mget("agent:kill:global", f"agent:kill:tenant:{tenant_id}")
            return any(values)
        finally:
            await redis.aclose()

    async def activate(self, tenant_id: str | None = None) -> None:
        redis = Redis.from_url(self.redis_url, decode_responses=True)
        try:
            key = "agent:kill:global" if tenant_id is None else f"agent:kill:tenant:{tenant_id}"
            await redis.set(key, "1")
        finally:
            await redis.aclose()

    async def deactivate(self, tenant_id: str | None = None) -> None:
        redis = Redis.from_url(self.redis_url, decode_responses=True)
        try:
            key = "agent:kill:global" if tenant_id is None else f"agent:kill:tenant:{tenant_id}"
            await redis.delete(key)
        finally:
            await redis.aclose()
