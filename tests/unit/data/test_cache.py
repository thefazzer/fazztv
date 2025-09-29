"""Comprehensive unit tests for cache module."""

import pytest
import time

from fazztv.data.cache import DataCache


class TestCache:
    """Test suite for cache functionality."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create cache instance."""
        return DataCache()

    def test_initialization(self, tmp_path):
        """Test cache initialization."""
        cache = DataCache(default_ttl=1800)
        assert cache.default_ttl == 1800
        assert cache.hit_count == 0
        assert cache.miss_count == 0
        assert len(cache.cache) == 0
    
    def test_get_set(self, cache):
        """Test getting and setting cache values."""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        cache.set("key2", {"data": "value2"})
        assert cache.get("key2") == {"data": "value2"}
    
    def test_get_nonexistent(self, cache):
        """Test getting nonexistent key."""
        result = cache.get("nonexistent")
        assert result is None
        
        # DataCache.get() doesn't support default parameter
        # so we just check it returns None
        assert result is None
    
    def test_delete(self, cache):
        """Test deleting cache entry."""
        cache.set("key", "value")
        assert cache.get("key") == "value"
        
        cache.delete("key")
        assert cache.get("key") is None
    
    def test_clear(self, cache):
        """Test clearing cache."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_expiration(self, cache):
        """Test cache expiration."""
        cache.set("key", "value", ttl=1)  # 1 second TTL
        assert cache.get("key") == "value"

        time.sleep(1.1)  # Wait for expiration
        assert cache.get("key") is None
    
    def test_get_or_set(self, cache):
        """Test get_or_set functionality."""
        def factory():
            return "computed_value"

        # First call should compute and cache
        result1 = cache.get_or_set("key", factory)
        assert result1 == "computed_value"

        # Second call should get from cache
        result2 = cache.get_or_set("key", lambda: "different_value")
        assert result2 == "computed_value"
    
    def test_decorator(self, cache):
        """Test cache decorator."""
        call_count = 0

        @cache.cache_decorator(ttl=60)
        def expensive_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_func(5)
        result2 = expensive_func(5)
        assert result1 == result2 == 10
        assert call_count == 1  # Should only be called once
