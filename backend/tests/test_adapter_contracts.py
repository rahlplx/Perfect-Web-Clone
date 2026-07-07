"""Contract tests - verify adapters comply with port interfaces."""
import pytest
from typing import get_type_hints


class TestCachePortContract:
    """Verify InMemoryCacheAdapter satisfies CachePort protocol."""

    @pytest.fixture
    def cache(self):
        from adapters.cache.memory import InMemoryCacheAdapter
        return InMemoryCacheAdapter(max_size=10, default_ttl=60)

    @pytest.mark.asyncio
    async def test_has_get_method(self, cache):
        assert hasattr(cache, "get")
        assert callable(cache.get)

    @pytest.mark.asyncio
    async def test_has_set_method(self, cache):
        assert hasattr(cache, "set")
        assert callable(cache.set)

    @pytest.mark.asyncio
    async def test_has_delete_method(self, cache):
        assert hasattr(cache, "delete")
        assert callable(cache.delete)

    @pytest.mark.asyncio
    async def test_has_exists_method(self, cache):
        assert hasattr(cache, "exists")
        assert callable(cache.exists)

    @pytest.mark.asyncio
    async def test_has_clear_method(self, cache):
        assert hasattr(cache, "clear")
        assert callable(cache.clear)

    @pytest.mark.asyncio
    async def test_has_keys_method(self, cache):
        assert hasattr(cache, "keys")
        assert callable(cache.keys)

    @pytest.mark.asyncio
    async def test_set_get_roundtrip(self, cache):
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_missing_key_returns_none(self, cache):
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing_key(self, cache):
        await cache.set("key1", "value1")
        result = await cache.delete("key1")
        assert result is True
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete_missing_key(self, cache):
        result = await cache.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_returns_true_for_live_key(self, cache):
        await cache.set("key1", "value1")
        assert await cache.exists("key1") is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_missing_key(self, cache):
        assert await cache.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_clear_returns_count(self, cache):
        await cache.set("k1", "v1")
        await cache.set("k2", "v2")
        count = await cache.clear()
        assert count == 2

    @pytest.mark.asyncio
    async def test_keys_returns_matching_keys(self, cache):
        await cache.set("prefix:a", 1)
        await cache.set("prefix:b", 2)
        await cache.set("other:c", 3)
        keys = await cache.keys("prefix:*")
        assert len(keys) == 2


class TestLLMProviderContract:
    """Verify AnthropicAdapter satisfies LLMProviderPort protocol."""

    def test_has_complete_method(self):
        from adapters.llm.anthropic import AnthropicAdapter
        adapter = AnthropicAdapter(api_key="test-key")
        assert hasattr(adapter, "complete")
        assert callable(adapter.complete)

    def test_has_stream_method(self):
        from adapters.llm.anthropic import AnthropicAdapter
        adapter = AnthropicAdapter(api_key="test-key")
        assert hasattr(adapter, "stream")
        assert callable(adapter.stream)

    def test_uses_async_client(self):
        from adapters.llm.anthropic import AnthropicAdapter
        adapter = AnthropicAdapter(api_key="test-key")
        import anthropic
        assert isinstance(adapter._client, anthropic.AsyncAnthropic)


class TestMockLLMAdapterContract:
    """Verify MockLLMAdapter satisfies LLMProviderPort protocol."""

    @pytest.mark.asyncio
    async def test_complete_returns_response(self):
        from adapters.llm.mock import MockLLMAdapter
        from ports.llm import LLMMessage
        adapter = MockLLMAdapter()
        messages = [LLMMessage(role="user", content="test")]
        response = await adapter.complete(messages)
        assert hasattr(response, "content")
        assert hasattr(response, "model")

    @pytest.mark.asyncio
    async def test_stream_yields_text(self):
        from adapters.llm.mock import MockLLMAdapter
        from ports.llm import LLMMessage
        adapter = MockLLMAdapter()
        messages = [LLMMessage(role="user", content="test")]
        chunks = []
        async for chunk in adapter.stream(messages):
            chunks.append(chunk)
        assert len(chunks) > 0


class TestSandboxAdapterContract:
    """Verify MockSandboxAdapter satisfies SandboxPort protocol."""

    def test_has_required_methods(self):
        from adapters.sandbox.mock import MockSandboxAdapter
        adapter = MockSandboxAdapter()
        required = ["initialize", "cleanup", "write_file", "read_file",
                     "delete_file", "list_files", "run_command",
                     "start_dev_server", "stop_dev_server", "get_state"]
        for method in required:
            assert hasattr(adapter, method), f"Missing method: {method}"
