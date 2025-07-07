"""
Status router for health checks and system status.

This module provides endpoints for monitoring API health and status.
"""

import time
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..exceptions import DataSourceException
from ..models.schemas import APIResponse, HealthStatus
from ..services.health_service import HealthService

router = APIRouter()

# Global start time for uptime calculation
_start_time = time.time()


def get_health_service() -> HealthService:
    """Dependency to get health service instance."""
    return HealthService()


@router.get("/status", response_model=APIResponse, summary="API Health Check")
async def get_api_status(
    health_service: HealthService = Depends(get_health_service),
) -> APIResponse:
    """
    Get API health status and system information.

    Returns comprehensive health information including:
    - API status (healthy/unhealthy)
    - Uptime
    - Data source availability
    - Cache statistics
    - Version information

    Returns:
        APIResponse with HealthStatus data
    """
    try:
        # Calculate uptime
        uptime_seconds = time.time() - _start_time

        # Check data source status
        data_source_status = await health_service.check_data_source()

        # Get cache statistics
        cache_stats = await health_service.get_cache_stats()

        # Determine overall health
        is_healthy = data_source_status == "healthy"

        health_data = HealthStatus(
            status="healthy" if is_healthy else "unhealthy",
            timestamp=datetime.now(),
            version="1.0.0",
            uptime_seconds=uptime_seconds,
            data_source_status=data_source_status,
            cache_stats=cache_stats,
        )

        return APIResponse(
            success=True,
            data=health_data,
            metadata={
                "response_time_ms": 0,  # Will be calculated by middleware
                "environment": "development",  # Should come from config
            },
        )

    except Exception as e:
        # Log error (middleware will handle this)
        raise DataSourceException(f"Health check failed: {str(e)}")


@router.get("/status/ping", summary="Simple Ping")
async def ping() -> Dict[str, Any]:
    """
    Simple ping endpoint for basic connectivity tests.

    Returns:
        Simple pong response with timestamp
    """
    return {"status": "ok", "message": "pong", "timestamp": datetime.now().isoformat()}


@router.get("/status/version", summary="API Version")
async def get_version() -> Dict[str, str]:
    """
    Get API version information.

    Returns:
        Version information
    """
    return {
        "version": "1.0.0",
        "api_version": "v1",
        "build_date": "2025-01-07",
        "description": "Claude Code Usage Monitor API",
    }
