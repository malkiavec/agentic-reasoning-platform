import json
from typing import Any, AsyncIterator

class RedisEventStream:
    """Redis pub/sub transport for low-latency run events."""
    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def publish(self, run_id: str, event: dict[str, Any]) -> None:
        await self.redis.publish(f"run:{run_id}", json.dumps(event, separators=(",", ":")))

    async def subscribe(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        channel = self.redis.pubsub()
        await channel.subscribe(f"run:{run_id}")
        try:
            async for message in channel.listen():
                if message.get("type") != "message":
                    continue
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                yield json.loads(data)
        finally:
            await channel.unsubscribe(f"run:{run_id}")
            await channel.aclose()
