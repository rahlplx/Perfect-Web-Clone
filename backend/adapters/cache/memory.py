import time
from typing import Any, Dict, List, Optional
from ports.cache import CachePort


class InMemoryCacheAdapter:
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self._store: Dict[str, tuple[Any, float]] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl

    async def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        expires_at = time.time() + (ttl or self._default_ttl)
        self._store[key] = (value, expires_at)
        # LRU eviction if over capacity
        if len(self._store) > self._max_size:
            oldest_key = min(self._store, key=lambda k: self._store[k][1])
            del self._store[oldest_key]
        return True

    async def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    async def exists(self, key: str) -> bool:
        return key in self._store

    async def clear(self) -> int:
        count = len(self._store)
        self._store.clear()
        return count

    async def keys(self, pattern: str = "*") -> List[str]:
        import fnmatch

        return [k for k in self._store.keys() if fnmatch.fnmatch(k, pattern)]
