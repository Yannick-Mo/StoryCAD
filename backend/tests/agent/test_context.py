"""Tests for context builder — LRU cache, _is_meaningful_query."""

import time
from app.agent.context import _LRUCache, _is_meaningful_query


class TestLRUCache:
    def test_get_set(self):
        cache = _LRUCache(ttl=30, maxsize=10)
        cache.set("key1", {"data": 1})
        assert cache.get("key1") == {"data": 1}

    def test_missing_key(self):
        cache = _LRUCache(ttl=30, maxsize=10)
        assert cache.get("nonexistent") is None

    def test_expiry(self):
        import time as time_module
        start = time_module.monotonic()
        cache = _LRUCache(ttl=1, maxsize=10)
        cache.set("key1", {"data": 1})
        cache._store["key1"] = (start - 2, cache._store["key1"][1])
        assert cache.get("key1") is None

    def test_lru_eviction(self):
        cache = _LRUCache(ttl=30, maxsize=2)
        cache.set("a", {"v": 1})
        cache.set("b", {"v": 2})
        cache.get("a")
        cache.set("c", {"v": 3})
        assert cache.get("b") is None
        assert cache.get("a") == {"v": 1}
        assert cache.get("c") == {"v": 3}

    def test_move_to_end_on_get(self):
        cache = _LRUCache(ttl=30, maxsize=2)
        cache.set("a", {"v": 1})
        cache.set("b", {"v": 2})
        cache.get("a")
        cache.set("c", {"v": 3})
        assert cache.get("a") == {"v": 1}
        assert cache.get("b") is None

    def test_overwrite(self):
        cache = _LRUCache(ttl=30, maxsize=10)
        cache.set("key", {"v": 1})
        cache.set("key", {"v": 2})
        assert cache.get("key") == {"v": 2}


class TestIsMeaningfulQuery:
    def test_short_query_not_meaningful(self):
        assert not _is_meaningful_query("hi")

    def test_greetings_not_meaningful(self):
        assert not _is_meaningful_query("你好")
        assert not _is_meaningful_query("hello")
        assert not _is_meaningful_query("hey")

    def test_short_acknowledgments_not_meaningful(self):
        assert not _is_meaningful_query("嗯")
        assert not _is_meaningful_query("好的")
        assert not _is_meaningful_query("ok")

    def test_meaningful_query(self):
        assert _is_meaningful_query("请帮我分析这个角色的性格发展")
        assert _is_meaningful_query("What is the protagonist's motivation?")

    def test_greeting_with_punctuation(self):
        assert not _is_meaningful_query("你好！")
        assert not _is_meaningful_query("hello?")
