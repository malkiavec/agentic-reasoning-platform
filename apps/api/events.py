import asyncio
from collections import defaultdict
from typing import Any

class RedisEventStream:
    """Redis pub/sub transport contract; persistence belongs to the database event store."""
    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def publish(self, run_id: str, event: dict) -> None:
        import json
        await self.redis.publish(f"run:{run_id}", json.dumps(event))

    async def subscribe(self, run_id: str):
        channel = self.redis.pubsub()
        await channel.subscribe(f"run:{run_id}")
        async for message in channel.listen():
            if message.get("type") == "message":
                yield message["data"]
