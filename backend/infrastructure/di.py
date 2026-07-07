"""Dependency injection container for hexagonal architecture."""
import os
from functools import lru_cache
from typing import Optional


class Container:
    """DI container with lazy singleton resolution."""
    
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
        from adapters.sandbox.mock import MockSandboxAdapter
        return MockSandboxAdapter
    
    def set_llm_provider(self, provider):
        self._singletons["llm"] = provider
    
    def set_cache(self, cache):
        self._singletons["cache"] = cache
    
    def reset(self):
        self._singletons.clear()
    
    def health(self) -> dict:
        return {
            "llm_provider": type(self.llm_provider).__name__,
            "cache": type(self.cache).__name__,
            "sandbox_factory": self.sandbox_factory.__name__,
        }


@lru_cache()
def get_container() -> Container:
    return Container()


def get_container_dependency():
    """FastAPI dependency that returns the global container."""
    return get_container()
