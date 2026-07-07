"""Tests for DI Container - hexagonal architecture wiring."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestContainerInit:
    """Container initialization tests."""

    def test_creates_instance(self):
        from infrastructure.di import Container
        container = Container()
        assert container is not None

    def test_singletons_dict_initialized(self):
        from infrastructure.di import Container
        container = Container()
        assert hasattr(container, "_singletons")
        assert isinstance(container._singletons, dict)

    def test_singleton_starts_empty(self):
        from infrastructure.di import Container
        container = Container()
        assert len(container._singletons) == 0


class TestContainerLLMProvider:
    """LLM provider resolution tests."""

    def test_llm_provider_returns_anthropic_adapter(self):
        from infrastructure.di import Container
        container = Container()
        provider = container.llm_provider
        from adapters.llm.anthropic import AnthropicAdapter
        assert isinstance(provider, AnthropicAdapter)

    def test_llm_provider_is_singleton(self):
        from infrastructure.di import Container
        container = Container()
        provider1 = container.llm_provider
        provider2 = container.llm_provider
        assert provider1 is provider2

    def test_set_llm_provider_override(self):
        from infrastructure.di import Container
        container = Container()
        mock_provider = MagicMock()
        container.set_llm_provider(mock_provider)
        assert container.llm_provider is mock_provider


class TestContainerCache:
    """Cache resolution tests."""

    def test_cache_returns_in_memory_by_default(self):
        from infrastructure.di import Container
        container = Container()
        cache = container.cache
        from adapters.cache.memory import InMemoryCacheAdapter
        assert isinstance(cache, InMemoryCacheAdapter)

    def test_cache_is_singleton(self):
        from infrastructure.di import Container
        container = Container()
        cache1 = container.cache
        cache2 = container.cache
        assert cache1 is cache2

    def test_set_cache_override(self):
        from infrastructure.di import Container
        container = Container()
        mock_cache = MagicMock()
        container.set_cache(mock_cache)
        assert container.cache is mock_cache

    @patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379"})
    @patch("adapters.cache.redis.RedisCacheAdapter")
    def test_cache_returns_redis_when_env_set(self, mock_redis_cls):
        from infrastructure.di import Container
        container = Container()
        cache = container.cache
        mock_redis_cls.assert_called_once_with("redis://localhost:6379")


class TestContainerSandboxFactory:
    """Sandbox factory tests."""

    def test_sandbox_factory_returns_mock_adapter_class(self):
        from infrastructure.di import Container
        container = Container()
        factory = container.sandbox_factory
        from adapters.sandbox.mock import MockSandboxAdapter
        assert factory is MockSandboxAdapter

    def test_sandbox_factory_creates_instance(self):
        from infrastructure.di import Container
        container = Container()
        sandbox = container.sandbox_factory()
        from adapters.sandbox.mock import MockSandboxAdapter
        assert isinstance(sandbox, MockSandboxAdapter)


class TestGetContainer:
    """Global container accessor tests."""

    def test_get_container_returns_container(self):
        from infrastructure.di import get_container, Container
        container = get_container()
        assert isinstance(container, Container)

    def test_get_container_is_singleton(self):
        from infrastructure.di import get_container
        container1 = get_container()
        container2 = get_container()
        assert container1 is container2


class TestContainerReset:
    """Container reset for testing."""

    def test_set_llm_clears_singleton(self):
        from infrastructure.di import Container
        container = Container()
        _ = container.llm_provider  # Initialize
        mock = MagicMock()
        container.set_llm_provider(mock)
        assert container.llm_provider is mock

    def test_set_cache_clears_singleton(self):
        from infrastructure.di import Container
        container = Container()
        _ = container.cache  # Initialize
        mock = MagicMock()
        container.set_cache(mock)
        assert container.cache is mock
