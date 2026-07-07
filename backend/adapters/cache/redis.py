from typing import Any, List, Optional
from ports.cache import CachePort


class RedisCacheAdapter:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self._redis_url = redis_url
        self._client = None

    async def _get_client(self):
        if self._client is None:
            import redis.asyncio as redis

            self._client = redis.from_url(self._redis_url)
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        import json

        client = await self._get_client()
        data = await client.get(key)
        return json.loads(data) if data else None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        import json

        client = await self._get_client()
        await client.set(key, json.dumps(value), ex=ttl)
        return True

    async def delete(self, key: str) -> bool:
        client = await self._get_client()
        return await client.delete(key) > 0

    async def exists(self, key: str) -> bool:
        client = await self._get_client()
        return await client.exists(key) > 0

    async def clear(self) -> int:
        client = await self._get_client()
        return await client.flushdb()

    async def keys(self, pattern: str = "*") -> List[str]:
        client = await self._get_client()
        return [k.decode() async for k in client.scan_iter(match=pattern)]
