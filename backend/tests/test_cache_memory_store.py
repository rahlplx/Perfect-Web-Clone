"""
Tests for cache.memory_store: MemoryStore and CacheEntry.
"""

import time
import json
import threading
import pytest

from cache.memory_store import MemoryStore, CacheEntry


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def store():
    return MemoryStore(max_entries=50, default_ttl=86400.0)


@pytest.fixture
def small_store():
    return MemoryStore(max_entries=3, default_ttl=86400.0)


@pytest.fixture
def fast_expiry_store():
    return MemoryStore(max_entries=50, default_ttl=0.1)


def _sample_data(title="Test Page", **extra):
    return {"metadata": {"title": title}, **extra}


# ============================================
# 1. Basic CRUD Operations
# ============================================

class TestBasicCRUD:
    def test_store_returns_id(self, store):
        entry_id = store.store("https://example.com", _sample_data())
        assert isinstance(entry_id, str)
        assert len(entry_id) == 8

    def test_get_returns_entry(self, store):
        entry_id = store.store("https://example.com", _sample_data("My Title"))
        entry = store.get(entry_id)
        assert entry is not None
        assert entry.url == "https://example.com"
        assert entry.title == "My Title"
        assert entry.data["metadata"]["title"] == "My Title"

    def test_get_nonexistent_returns_none(self, store):
        assert store.get("nonexistent") is None

    def test_delete_existing(self, store):
        entry_id = store.store("https://example.com", _sample_data())
        assert store.delete(entry_id) is True
        assert store.get(entry_id) is None

    def test_delete_nonexistent(self, store):
        assert store.delete("nonexistent") is False

    def test_store_generates_unique_ids(self, store):
        ids = {store.store("https://example.com", _sample_data()) for _ in range(10)}
        assert len(ids) == 10

    def test_store_with_custom_ttl(self, store):
        entry_id = store.store("https://example.com", _sample_data(), ttl=60.0)
        entry = store.get(entry_id)
        assert entry.ttl == 60.0

    def test_store_with_title_override(self, store):
        entry_id = store.store("https://example.com", _sample_data("Auto Title"), title="Override")
        entry = store.get(entry_id)
        assert entry.title == "Override"

    def test_store_title_from_data_when_no_override(self, store):
        entry_id = store.store("https://example.com", _sample_data("Extracted"))
        entry = store.get(entry_id)
        assert entry.title == "Extracted"

    def test_store_title_none_when_no_metadata(self, store):
        entry_id = store.store("https://example.com", {"key": "value"})
        entry = store.get(entry_id)
        assert entry.title is None

    def test_get_by_url_returns_newest(self, store):
        id1 = store.store("https://example.com", _sample_data("First"))
        time.sleep(0.01)
        id2 = store.store("https://example.com", _sample_data("Second"))
        entry = store.get_by_url("https://example.com")
        assert entry.id == id2
        assert entry.title == "Second"

    def test_get_by_url_returns_none_for_unknown(self, store):
        assert store.get_by_url("https://unknown.com") is None

    def test_get_by_url_ignores_expired(self, store):
        id1 = store.store("https://example.com", _sample_data(), ttl=0.001)
        time.sleep(0.02)
        assert store.get_by_url("https://example.com") is None


# ============================================
# 2. TTL Expiry
# ============================================

class TestTTLExpiry:
    def test_entry_expires(self, fast_expiry_store):
        entry_id = fast_expiry_store.store("https://example.com", _sample_data())
        time.sleep(0.15)
        assert fast_expiry_store.get(entry_id) is None

    def test_get_cleans_expired(self, fast_expiry_store):
        entry_id = fast_expiry_store.store("https://example.com", _sample_data())
        time.sleep(0.15)
        fast_expiry_store.get(entry_id)
        assert entry_id not in fast_expiry_store._store

    def test_list_all_excludes_expired(self, fast_expiry_store):
        fast_expiry_store.store("https://a.com", _sample_data(), ttl=86400.0)
        fast_expiry_store.store("https://b.com", _sample_data(), ttl=0.001)
        time.sleep(0.15)
        entries = fast_expiry_store.list_all()
        assert len(entries) == 1
        assert entries[0].url == "https://a.com"

    def test_cleanup_removes_multiple_expired(self, fast_expiry_store):
        for i in range(5):
            fast_expiry_store.store(f"https://{i}.com", _sample_data(), ttl=0.001)
        time.sleep(0.15)
        fast_expiry_store._cleanup_expired()
        assert len(fast_expiry_store._store) == 0

    def test_not_expired_within_ttl(self, store):
        entry_id = store.store("https://example.com", _sample_data(), ttl=86400.0)
        entry = store.get(entry_id)
        assert entry is not None

    def test_is_expired_property(self):
        entry = CacheEntry(id="a", url="https://x.com", title=None,
                           data={}, timestamp=time.time() - 100, ttl=10.0)
        assert entry.is_expired is True

    def test_is_not_expired_property(self):
        entry = CacheEntry(id="a", url="https://x.com", title=None,
                           data={}, timestamp=time.time(), ttl=86400.0)
        assert entry.is_expired is False


# ============================================
# 3. LRU Eviction
# ============================================

class TestLRUEviction:
    def test_evicts_oldest_when_full(self, small_store):
        ids = []
        for i in range(3):
            ids.append(small_store.store(f"https://{i}.com", _sample_data()))
        small_store.store("https://new.com", _sample_data())
        assert small_store.get(ids[0]) is None
        assert small_store.get(ids[1]) is not None
        assert small_store.get(ids[2]) is not None

    def test_eviction_uses_oldest_timestamp(self, small_store):
        id1 = small_store.store("https://1.com", _sample_data())
        time.sleep(0.01)
        id2 = small_store.store("https://2.com", _sample_data())
        time.sleep(0.01)
        id3 = small_store.store("https://3.com", _sample_data())
        small_store.store("https://4.com", _sample_data())
        assert small_store.get(id1) is None
        assert small_store.get(id2) is not None
        assert small_store.get(id3) is not None

    def test_multiple_evictions_at_capacity(self, small_store):
        for i in range(5):
            small_store.store(f"https://{i}.com", _sample_data())
        assert len(small_store._store) == 3

    def test_no_eviction_below_capacity(self, small_store):
        for i in range(2):
            small_store.store(f"https://{i}.com", _sample_data())
        assert len(small_store._store) == 2


# ============================================
# 4. clear() Operation
# ============================================

class TestClear:
    def test_clear_returns_count(self, store):
        for i in range(5):
            store.store(f"https://{i}.com", _sample_data())
        assert store.clear() == 5

    def test_clear_removes_all(self, store):
        for i in range(5):
            store.store(f"https://{i}.com", _sample_data())
        store.clear()
        assert len(store._store) == 0
        assert store.list_all() == []

    def test_clear_empty_store(self, store):
        assert store.clear() == 0

    def test_list_all_after_clear(self, store):
        store.store("https://example.com", _sample_data())
        store.clear()
        assert store.list_all() == []


# ============================================
# 5. Stats/Metrics
# ============================================

class TestStats:
    def test_stats_initial(self, store):
        stats = store.stats()
        assert stats["total_entries"] == 0
        assert stats["max_entries"] == 50
        assert stats["total_size_bytes"] == 0
        assert stats["default_ttl_hours"] == 24.0

    def test_stats_after_storing(self, store):
        store.store("https://example.com", _sample_data("Test"))
        stats = store.stats()
        assert stats["total_entries"] == 1
        assert stats["total_size_bytes"] > 0

    def test_stats_after_clear(self, store):
        store.store("https://example.com", _sample_data())
        store.clear()
        stats = store.stats()
        assert stats["total_entries"] == 0
        assert stats["total_size_bytes"] == 0

    def test_stats_total_size_mb(self, store):
        store.store("https://example.com", _sample_data("x" * 2000000))
        stats = store.stats()
        assert stats["total_size_mb"] > 0


# ============================================
# 6. Thread Safety
# ============================================

class TestThreadSafety:
    def test_concurrent_stores(self, store):
        errors = []

        def store_entry(i):
            try:
                store.store(f"https://{i}.com", _sample_data())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=store_entry, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(store._store) == 50

    def test_concurrent_get_and_store(self, store):
        errors = []

        def writer(i):
            try:
                store.store(f"https://{i}.com", _sample_data())
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(10):
                    store.list_all()
                    store.stats()
            except Exception as e:
                errors.append(e)

        threads = (
            [threading.Thread(target=writer, args=(i,)) for i in range(20)]
            + [threading.Thread(target=reader) for _ in range(5)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors

    def test_concurrent_deletes(self, store):
        ids = [store.store(f"https://{i}.com", _sample_data()) for i in range(20)]
        errors = []

        def delete_entry(entry_id):
            try:
                store.delete(entry_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=delete_entry, args=(eid,)) for eid in ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(store._store) == 0

    def test_concurrent_clear_and_store(self, store):
        errors = []

        def writer():
            try:
                for i in range(10):
                    store.store(f"https://{i}.com", _sample_data())
            except Exception as e:
                errors.append(e)

        def clearer():
            try:
                for _ in range(10):
                    store.clear()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(3)] + \
                  [threading.Thread(target=clearer) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(store._store) <= 30


# ============================================
# 7. Edge Cases
# ============================================

class TestEdgeCases:
    def test_empty_url(self, store):
        entry_id = store.store("", _sample_data())
        entry = store.get(entry_id)
        assert entry.url == ""

    def test_none_title(self, store):
        entry_id = store.store("https://example.com", {"content": "no metadata"})
        entry = store.get(entry_id)
        assert entry.title is None

    def test_empty_data(self, store):
        entry_id = store.store("https://example.com", {})
        entry = store.get(entry_id)
        assert entry.data == {}

    def test_large_value(self, store):
        large_data = {"content": "x" * 1_000_000}
        entry_id = store.store("https://example.com", large_data)
        entry = store.get(entry_id)
        assert len(entry.data["content"]) == 1_000_000

    def test_nested_data(self, store):
        nested = {"a": {"b": {"c": {"d": [1, 2, 3]}}}}
        entry_id = store.store("https://example.com", nested)
        entry = store.get(entry_id)
        assert entry.data["a"]["b"]["c"]["d"] == [1, 2, 3]

    def test_special_characters_in_url(self, store):
        url = "https://example.com/path?a=1&b=2#frag 中文"
        entry_id = store.store(url, _sample_data())
        entry = store.get(entry_id)
        assert entry.url == url

    def test_non_string_keys_in_data(self, store):
        data = {"key": "value", 42: "int key", 3.14: "float key"}
        entry_id = store.store("https://example.com", data)
        entry = store.get(entry_id)
        assert entry.data[42] == "int key"
        assert entry.data[3.14] == "float key"

    def test_title_none_when_data_has_non_dict_metadata(self, store):
        entry_id = store.store("https://example.com", {"metadata": "not a dict"})
        entry = store.get(entry_id)
        assert entry.title is None

    def test_title_none_when_metadata_title_empty(self, store):
        entry_id = store.store("https://example.com", {"metadata": {"title": ""}})
        entry = store.get(entry_id)
        assert entry.title is None

    def test_title_none_when_metadata_title_falsy(self, store):
        entry_id = store.store("https://example.com", {"metadata": {"title": 0}})
        entry = store.get(entry_id)
        assert entry.title is None

    def test_to_summary(self, store):
        entry_id = store.store("https://example.com", _sample_data("T"))
        entry = store.get(entry_id)
        summary = entry.to_summary()
        assert summary["id"] == entry_id
        assert summary["url"] == "https://example.com"
        assert "data" not in summary

    def test_to_dict(self, store):
        entry_id = store.store("https://example.com", _sample_data("T"))
        entry = store.get(entry_id)
        d = entry.to_dict()
        assert "data" in d
        assert d["data"]["metadata"]["title"] == "T"

    def test_created_at_and_expires_at(self, store):
        entry_id = store.store("https://example.com", _sample_data(), ttl=3600.0)
        entry = store.get(entry_id)
        assert entry.created_at
        assert entry.expires_at

    def test_size_bytes(self, store):
        entry_id = store.store("https://example.com", _sample_data("Hello"))
        entry = store.get(entry_id)
        assert entry.size_bytes > 0

    def test_list_all_sorted_newest_first(self, store):
        id1 = store.store("https://a.com", _sample_data())
        time.sleep(0.01)
        id2 = store.store("https://b.com", _sample_data())
        entries = store.list_all()
        assert entries[0].id == id2
        assert entries[1].id == id1


# ============================================
# 8. Singleton
# ============================================

class TestSingleton:
    def test_singleton_exists(self):
        from cache.memory_store import extraction_cache
        assert isinstance(extraction_cache, MemoryStore)
        assert extraction_cache._max_entries == 50
        assert extraction_cache._default_ttl == 86400.0


# ============================================
# 9. Cleanup Integration
# ============================================

class TestCleanupIntegration:
    def test_store_triggers_cleanup(self, fast_expiry_store):
        fast_expiry_store.store("https://expired.com", _sample_data(), ttl=0.001)
        time.sleep(0.15)
        fast_expiry_store.store("https://new.com", _sample_data())
        assert len(fast_expiry_store._store) == 1

    def test_cleanup_handles_all_expired(self, fast_expiry_store):
        for i in range(10):
            fast_expiry_store.store(f"https://{i}.com", _sample_data(), ttl=0.001)
        time.sleep(0.15)
        fast_expiry_store.store("https://alive.com", _sample_data(), ttl=86400.0)
        assert len(fast_expiry_store._store) == 1
