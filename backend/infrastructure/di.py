import os
from functools import lru_cache
from typing import Optional

class Container:
    """Dependency injection container for hexagonal architecture."""
    
    def __init__(self):
        self._singletons = {}
    
    @property
    def llm_provider(self):
        if "llm" not in self._singletons:
            from adapters.llm.anthropic import AnthropicAdapter
            self._singletons["llm"] = AnthropicAdapter()
        return self._singletons["llm"]
    
    @property
    def cache(self):
        if "cache" not in self._singletons:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                from adapters.cache.redis import RedisCacheAdapter
                self._singletons["cache"] = RedisCacheAdapter(redis_url)
            else:
                from adapters.cache.memory import InMemoryCacheAdapter
                self._singletons["cache"] = InMemoryCacheAdapter()
        return self._singletons["cache"]
    
    @property
    def sandbox_factory(self):
        """Factory for creating sandbox instances."""
        from adapters.sandbox.mock import MockSandboxAdapter
        return MockSandboxAdapter
    
    def set_llm_provider(self, provider):
        """Override LLM provider (for testing)."""
        self._singletons["llm"] = provider
    
    def set_cache(self, cache):
        """Override cache (for testing)."""
        self._singletons["cache"] = cache

@lru_cache()
def get_container() -> Container:
    """Get or create the global DI container."""
    return Container()
