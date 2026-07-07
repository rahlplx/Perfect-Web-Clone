import logging
from typing import Any, List, Optional, TYPE_CHECKING
from ports.cache import CachePort

if TYPE_CHECKING:
    import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisCacheAdapter:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self._redis_url = redis_url
        self._client: Optional["redis.Redis"] = None
        self._connected = False

    async def _get_client(self) -> "redis.Redis":
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                )
                await self._client.ping()  # type: ignore
                self._connected = True
                logger.info(f"Connected to Redis at {self._redis_url}")
            except ImportError:
                logger.warning("redis.asyncio not installed. Run: pip install redis")
                raise
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._connected = False
                raise
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        import json

        try:
            client = await self._get_client()
            data = await client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning(f"Redis GET failed for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        import json

        try:
            client = await self._get_client()
            await client.set(key, json.dumps(value), ex=ttl)
            return True
        except Exception as e:
            logger.warning(f"Redis SET failed for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        try:
            client = await self._get_client()
            return await client.delete(key) > 0
        except Exception as e:
            logger.warning(f"Redis DELETE failed for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        try:
            client = await self._get_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Redis EXISTS failed for key {key}: {e}")
            return False

    async def clear(self) -> int:
        try:
            client = await self._get_client()
            return await client.flushdb()
        except Exception as e:
            logger.warning(f"Redis CLEAR failed: {e}")
            return 0

    async def keys(self, pattern: str = "*") -> List[str]:
        try:
            client = await self._get_client()
            return [k async for k in client.scan_iter(match=pattern)]
        except Exception as e:
            logger.warning(f"Redis KEYS failed: {e}")
            return []

    async def close(self):
        """Close Redis connection"""
        if self._client:
            try:
                await self._client.close()
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")
            finally:
                self._client = None
                self._connected = False
