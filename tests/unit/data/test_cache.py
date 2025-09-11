"""Comprehensive unit tests for cache module."""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import json
import time

from fazztv.data.cache import *


class TestCache:
    """Test suite for cache functionality."""
    
    @pytest.fixture
    def cache(self, tmp_path):
        """Create cache instance."""
        return Cache(cache_dir=tmp_path)
    
    def test_initialization(self, tmp_path):
        """Test cache initialization."""
        cache = Cache(cache_dir=tmp_path)
        assert cache.cache_dir == tmp_path
        assert tmp_path.exists()
    
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
        
        result = cache.get("nonexistent", default="default")
        assert result == "default"
    
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
        cache.set("key", "value", ttl=0.1)
        assert cache.get("key") == "value"
        
        time.sleep(0.2)
        assert cache.get("key") is None
    
    def test_file_cache(self, cache, tmp_path):
        """Test file-based caching."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        cache.cache_file(test_file, "file_key")
        cached = cache.get_file("file_key")
        assert cached is not None
    
    def test_decorator(self, cache):
        """Test cache decorator."""
        @cache.memoize(ttl=60)
        def expensive_func(x):
            return x * 2
        
        result1 = expensive_func(5)
        result2 = expensive_func(5)
        assert result1 == result2 == 10
