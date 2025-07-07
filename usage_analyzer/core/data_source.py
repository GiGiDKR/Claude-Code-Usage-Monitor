"""
DataSource - Abstract data source interface for usage data.

This module provides an abstraction layer for accessing usage data from
different sources like files, APIs, or databases.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional


class DataSource(ABC):
    """Abstract base class for data sources."""

    @abstractmethod
    def get_usage_data(self) -> Optional[Dict[str, Any]]:
        """
        Get usage data from the source.

        Returns:
            Dictionary with usage data or None if unavailable
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the data source is available.

        Returns:
            True if data source is accessible, False otherwise
        """
        pass

    @abstractmethod
    def get_last_updated(self) -> Optional[datetime]:
        """
        Get timestamp of last data update.

        Returns:
            DateTime of last update or None if unknown
        """
        pass


class FileDataSource(DataSource):
    """Data source that reads from Claude usage files."""

    def __init__(self):
        """Initialize file-based data source."""
        # Import here to avoid circular imports
        from ..api import analyze_usage

        self._analyze_usage = analyze_usage

    def get_usage_data(self) -> Optional[Dict[str, Any]]:
        """Get usage data from Claude files."""
        try:
            return self._analyze_usage()
        except Exception:
            return None

    def is_available(self) -> bool:
        """Check if Claude files are accessible."""
        try:
            data = self.get_usage_data()
            return data is not None and "blocks" in data
        except Exception:
            return False

    def get_last_updated(self) -> Optional[datetime]:
        """Get last update time from the most recent block."""
        try:
            data = self.get_usage_data()
            if not data or "blocks" not in data:
                return None

            latest_time = None
            for block in data["blocks"]:
                # Check both start and end times
                for time_key in ["startTime", "endTime"]:
                    time_str = block.get(time_key)
                    if time_str:
                        try:
                            block_time = datetime.fromisoformat(
                                time_str.replace("Z", "+00:00")
                            )
                            if latest_time is None or block_time > latest_time:
                                latest_time = block_time
                        except (ValueError, TypeError):
                            continue

            return latest_time
        except Exception:
            return None


class ApiDataSource(DataSource):
    """Data source that reads from a REST API."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """
        Initialize API-based data source.

        Args:
            base_url: Base URL of the API
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._last_data = None
        self._last_updated = None

    def get_usage_data(self) -> Optional[Dict[str, Any]]:
        """Get usage data from API."""
        try:
            import requests

            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = requests.get(
                f"{self.base_url}/api/v1/usage/current", headers=headers, timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self._last_data = data
                self._last_updated = datetime.now()
                return data
            else:
                return None

        except Exception:
            return None

    def is_available(self) -> bool:
        """Check if API is accessible."""
        try:
            import requests

            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = requests.get(
                f"{self.base_url}/api/v1/status", headers=headers, timeout=5
            )

            return response.status_code == 200

        except Exception:
            return False

    def get_last_updated(self) -> Optional[datetime]:
        """Get last update time."""
        return self._last_updated


class CachedDataSource(DataSource):
    """Wrapper that adds caching to any data source."""

    def __init__(self, source: DataSource, cache_duration_seconds: int = 30):
        """
        Initialize cached data source.

        Args:
            source: Underlying data source
            cache_duration_seconds: How long to cache data
        """
        self.source = source
        self.cache_duration_seconds = cache_duration_seconds
        self._cached_data = None
        self._cache_time = None

    def get_usage_data(self) -> Optional[Dict[str, Any]]:
        """Get usage data with caching."""
        now = datetime.now()

        # Check if cache is still valid
        if (
            self._cached_data is not None
            and self._cache_time is not None
            and (now - self._cache_time).total_seconds() < self.cache_duration_seconds
        ):
            return self._cached_data

        # Cache is invalid, fetch new data
        data = self.source.get_usage_data()
        if data is not None:
            self._cached_data = data
            self._cache_time = now

        return data

    def is_available(self) -> bool:
        """Check if underlying source is available."""
        return self.source.is_available()

    def get_last_updated(self) -> Optional[datetime]:
        """Get last update time from underlying source."""
        return self.source.get_last_updated()

    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cached_data = None
        self._cache_time = None


class DataSourceManager:
    """Manager for multiple data sources with fallback."""

    def __init__(self):
        """Initialize data source manager."""
        self.sources: List[DataSource] = []
        self.primary_source_index = 0

    def add_source(self, source: DataSource, is_primary: bool = False) -> None:
        """
        Add a data source.

        Args:
            source: Data source to add
            is_primary: Whether this should be the primary source
        """
        if is_primary:
            self.sources.insert(0, source)
            self.primary_source_index = 0
        else:
            self.sources.append(source)

    def get_usage_data(self) -> Optional[Dict[str, Any]]:
        """Get usage data from the first available source."""
        for i, source in enumerate(self.sources):
            try:
                if source.is_available():
                    data = source.get_usage_data()
                    if data is not None:
                        # Update primary source if this one worked
                        if i != self.primary_source_index:
                            self.primary_source_index = i
                        return data
            except Exception:
                continue

        return None

    def get_primary_source(self) -> Optional[DataSource]:
        """Get the current primary source."""
        if 0 <= self.primary_source_index < len(self.sources):
            return self.sources[self.primary_source_index]
        return None

    def is_available(self) -> bool:
        """Check if any source is available."""
        return any(source.is_available() for source in self.sources)

    def get_available_sources(self) -> List[DataSource]:
        """Get list of currently available sources."""
        return [source for source in self.sources if source.is_available()]


# Default data source manager instance with intelligent caching
default_data_source_manager = DataSourceManager()

# Add cached file source as default primary
cached_file_source = CachedDataSource(FileDataSource(), cache_duration_seconds=30)
default_data_source_manager.add_source(cached_file_source, is_primary=True)
