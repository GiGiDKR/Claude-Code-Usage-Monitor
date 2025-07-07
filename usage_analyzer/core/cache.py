"""
Cache - Intelligent caching system for usage data.

This module provides smart caching with features like TTL, invalidation,
and intelligent refresh strategies.
"""

import threading
from datetime import datetime
from typing import Any, Callable, Dict, Generic, Optional, TypeVar

T = TypeVar("T")


class CacheEntry(Generic[T]):
    """Individual cache entry with metadata."""

    def __init__(self, data: T, ttl_seconds: int):
        """
        Initialize cache entry.

        Args:
            data: Data to cache
            ttl_seconds: Time to live in seconds
        """
        self.data = data
        self.created_at = datetime.now()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0
        self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds

    def access(self) -> T:
        """Access the cached data and update metadata."""
        self.access_count += 1
        self.last_accessed = datetime.now()
        return self.data

    def time_until_expiry(self) -> float:
        """Get seconds until expiry."""
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return max(0, self.ttl_seconds - elapsed)


class IntelligentCache:
    """Intelligent cache with TTL and refresh strategies."""

    def __init__(self, default_ttl: int = 30, max_size: int = 100):
        """
        Initialize intelligent cache.

        Args:
            default_ttl: Default time to live in seconds
            max_size: Maximum number of entries
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0, "refreshes": 0}

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats["misses"] += 1
                return None

            if entry.is_expired():
                del self._cache[key]
                self._stats["misses"] += 1
                return None

            self._stats["hits"] += 1
            return entry.access()

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (defaults to default_ttl)
        """
        with self._lock:
            ttl = ttl or self.default_ttl

            # Evict if at max size and key doesn't exist
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()

            self._cache[key] = CacheEntry(value, ttl)

    def invalidate(self, key: str) -> bool:
        """
        Invalidate a cache entry.

        Args:
            key: Cache key to invalidate

        Returns:
            True if entry was found and removed
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._stats = {"hits": 0, "misses": 0, "evictions": 0, "refreshes": 0}

    def get_or_compute(
        self, key: str, compute_func: Callable[[], T], ttl: Optional[int] = None
    ) -> T:
        """
        Get value from cache or compute if not available.

        Args:
            key: Cache key
            compute_func: Function to compute value if not cached
            ttl: Time to live in seconds

        Returns:
            Cached or computed value
        """
        # Try cache first
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value

        # Compute and cache
        value = compute_func()
        self.set(key, value, ttl)
        return value

    def refresh_if_needed(
        self, key: str, compute_func: Callable[[], T], refresh_threshold: float = 0.8
    ) -> Optional[T]:
        """
        Refresh cache entry if close to expiry.

        Args:
            key: Cache key
            compute_func: Function to compute fresh value
            refresh_threshold: Refresh when TTL remaining < threshold (0.0-1.0)

        Returns:
            Current or refreshed value
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None or entry.is_expired():
                return None

            # Check if refresh is needed
            remaining_ratio = entry.time_until_expiry() / entry.ttl_seconds

            if remaining_ratio < refresh_threshold:
                # Background refresh
                try:
                    fresh_value = compute_func()
                    self._cache[key] = CacheEntry(fresh_value, entry.ttl_seconds)
                    self._stats["refreshes"] += 1
                    return fresh_value
                except Exception:
                    # If refresh fails, return current value
                    pass

            return entry.access()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                self._stats["hits"] / total_requests * 100 if total_requests > 0 else 0
            )

            return {
                **self._stats,
                "total_requests": total_requests,
                "hit_rate_percent": hit_rate,
                "current_size": len(self._cache),
                "max_size": self.max_size,
            }

    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information."""
        with self._lock:
            entries_info = []
            for key, entry in self._cache.items():
                entries_info.append(
                    {
                        "key": key,
                        "created_at": entry.created_at.isoformat(),
                        "last_accessed": entry.last_accessed.isoformat(),
                        "access_count": entry.access_count,
                        "ttl_seconds": entry.ttl_seconds,
                        "time_until_expiry": entry.time_until_expiry(),
                        "is_expired": entry.is_expired(),
                    }
                )

            return {"entries": entries_info, "stats": self.get_stats()}

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Find LRU entry
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)

        del self._cache[lru_key]
        self._stats["evictions"] += 1


class UsageDataCache:
    """Specialized cache for usage data with smart invalidation."""

    def __init__(self, ttl_seconds: int = 30):
        """
        Initialize usage data cache.

        Args:
            ttl_seconds: Cache TTL in seconds
        """
        self.cache = IntelligentCache(default_ttl=ttl_seconds)
        self._last_token_count = 0

    def get_usage_data(
        self, fetch_func: Callable[[], Optional[Dict[str, Any]]]
    ) -> Optional[Dict[str, Any]]:
        """
        Get usage data with intelligent caching.

        Args:
            fetch_func: Function to fetch fresh data

        Returns:
            Usage data or None if unavailable
        """
        # Try to get from cache first
        cached_data = self.cache.get("usage_data")

        if cached_data is not None:
            # Check if data might be stale based on token changes
            current_tokens = self._extract_token_count(cached_data)
            if current_tokens != self._last_token_count:
                # Token count changed, invalidate cache
                self.cache.invalidate("usage_data")
            else:
                return cached_data

        # Fetch fresh data
        fresh_data = fetch_func()
        if fresh_data is not None:
            self._last_token_count = self._extract_token_count(fresh_data)
            self.cache.set("usage_data", fresh_data)

        return fresh_data

    def invalidate(self) -> None:
        """Invalidate usage data cache."""
        self.cache.invalidate("usage_data")
        self._last_token_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()

    def _extract_token_count(self, data: Dict[str, Any]) -> int:
        """Extract total token count from usage data."""
        if not data or "blocks" not in data:
            return 0

        total_tokens = 0
        for block in data["blocks"]:
            if block.get("isActive", False):
                total_tokens += block.get("totalTokens", 0)

        return total_tokens


# Global cache instance
global_usage_cache = UsageDataCache()


def with_cache(ttl_seconds: int = 30):
    """
    Decorator to add caching to functions.

    Args:
        ttl_seconds: Cache TTL in seconds
    """

    def decorator(func):
        cache = IntelligentCache(default_ttl=ttl_seconds)

        def wrapper(*args, **kwargs):
            # Create cache key from function name and args
            key = f"{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"

            return cache.get_or_compute(key, lambda: func(*args, **kwargs))

        # Add cache management methods
        wrapper.cache_clear = cache.clear
        wrapper.cache_stats = cache.get_stats
        wrapper.cache_invalidate = lambda key: cache.invalidate(key)

        return wrapper

    return decorator
