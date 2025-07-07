"""
Health service for system monitoring.

This module provides health checking and system monitoring functionality.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from ...usage_analyzer.core.cache import global_usage_cache
from ...usage_analyzer.core.data_source import default_data_source_manager


class HealthService:
    """Service for health checks and system monitoring."""

    def __init__(self):
        """Initialize health service."""
        self.data_source_manager = default_data_source_manager
        self.cache = global_usage_cache

    async def check_data_source(self) -> str:
        """
        Check data source availability.

        Returns:
            Status string: 'healthy', 'degraded', or 'unhealthy'
        """
        try:
            if self.data_source_manager.is_available():
                # Try to get actual data
                data = self.data_source_manager.get_usage_data()
                if data and "blocks" in data:
                    return "healthy"
                else:
                    return "degraded"
            else:
                return "unhealthy"
        except Exception:
            return "unhealthy"

    async def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get cache statistics.

        Returns:
            Cache statistics or None if not available
        """
        try:
            return self.cache.get_stats()
        except Exception:
            return None

    async def check_dependencies(self) -> Dict[str, str]:
        """
        Check all system dependencies.

        Returns:
            Dictionary with dependency statuses
        """
        dependencies = {}

        # Check data source
        dependencies["data_source"] = await self.check_data_source()

        # Check cache
        try:
            cache_stats = await self.get_cache_stats()
            dependencies["cache"] = "healthy" if cache_stats else "unhealthy"
        except Exception:
            dependencies["cache"] = "unhealthy"

        # Check file system access
        try:
            import tempfile

            # Try to create a temporary file
            with tempfile.NamedTemporaryFile(delete=True):
                dependencies["filesystem"] = "healthy"
        except Exception:
            dependencies["filesystem"] = "unhealthy"

        return dependencies

    async def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get system performance metrics.

        Returns:
            System metrics
        """
        metrics = {}

        try:
            import psutil

            # CPU usage
            metrics["cpu_percent"] = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            metrics["memory"] = {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
            }

            # Disk usage
            disk = psutil.disk_usage("/")
            metrics["disk"] = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100,
            }

        except ImportError:
            # psutil not available, return basic metrics
            metrics["note"] = "psutil not installed - limited metrics available"
        except Exception as e:
            metrics["error"] = f"Failed to get system metrics: {str(e)}"

        return metrics

    async def run_health_checks(self) -> Dict[str, Any]:
        """
        Run comprehensive health checks.

        Returns:
            Complete health check results
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "checks": {},
        }

        # Check dependencies
        dependencies = await self.check_dependencies()
        results["checks"]["dependencies"] = dependencies

        # Check system metrics
        system_metrics = await self.get_system_metrics()
        results["checks"]["system"] = system_metrics

        # Determine overall status
        unhealthy_deps = [k for k, v in dependencies.items() if v == "unhealthy"]
        if unhealthy_deps:
            if len(unhealthy_deps) > 1 or "data_source" in unhealthy_deps:
                results["overall_status"] = "unhealthy"
            else:
                results["overall_status"] = "degraded"

        return results
