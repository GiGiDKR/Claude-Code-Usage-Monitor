"""
Usage router for token usage endpoints.

This module provides endpoints for accessing usage data and metrics.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..exceptions import DataSourceException, ValidationException
from ..models.schemas import (
    APIResponse,
    HistoryQueryParams,
    PlanType,
    UsageStatus,
)
from ..services.usage_service import UsageService

router = APIRouter()


def get_usage_service() -> UsageService:
    """Dependency to get usage service instance."""
    return UsageService()


@router.get(
    "/usage/current", response_model=APIResponse, summary="Current Usage Status"
)
async def get_current_usage(
    plan: Optional[PlanType] = Query(
        PlanType.PRO, description="Claude plan type to use for calculations"
    ),
    usage_service: UsageService = Depends(get_usage_service),
) -> APIResponse:
    """
    Get current token usage status and predictions.

    Provides comprehensive information about:
    - Current session status
    - Token usage and limits
    - Burn rate calculations
    - Time predictions
    - Notification conditions

    Args:
        plan: Claude plan type (pro, max5, max20, custom_max)
        usage_service: Usage service dependency

    Returns:
        APIResponse with current usage status
    """
    try:
        # Get current status from the monitor service
        status_data = await usage_service.get_current_status(plan.value)

        if status_data.get("status") == "no_data":
            raise DataSourceException("No usage data available")

        if status_data.get("status") == "no_active_session":
            # Return empty but valid response for no active session
            return APIResponse(
                success=True,
                data={
                    "status": "no_active_session",
                    "timestamp": datetime.now(),
                    "message": "No active Claude session found",
                },
                metadata={
                    "plan_requested": plan.value,
                    "data_source_available": status_data.get(
                        "data_source_available", False
                    ),
                },
            )

        # Convert to UsageStatus model
        usage_status = UsageStatus(**status_data)

        return APIResponse(
            success=True,
            data=usage_status,
            metadata={"plan_requested": plan.value, "response_source": "real_time"},
        )

    except DataSourceException:
        raise
    except Exception as e:
        raise DataSourceException(f"Failed to get current usage: {str(e)}")


@router.get("/usage/history", response_model=APIResponse, summary="Usage History")
async def get_usage_history(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    plan_filter: Optional[PlanType] = Query(None, description="Filter by plan type"),
    usage_service: UsageService = Depends(get_usage_service),
) -> APIResponse:
    """
    Get historical usage data with pagination and filtering.

    Args:
        page: Page number (starting from 1)
        page_size: Number of items per page (1-1000)
        start_date: Optional start date filter
        end_date: Optional end date filter
        plan_filter: Optional plan type filter
        usage_service: Usage service dependency

    Returns:
        APIResponse with paginated historical usage data
    """
    try:
        # Validate parameters
        from ..exceptions import validate_date_range, validate_pagination

        validate_pagination(page, page_size)
        validate_date_range(start_date, end_date)

        # Create query params
        query_params = HistoryQueryParams(
            page=page,
            page_size=page_size,
            start_date=start_date,
            end_date=end_date,
            plan_filter=plan_filter,
        )

        # Get historical data
        history_data = await usage_service.get_usage_history(query_params)

        return APIResponse(
            success=True,
            data=history_data,
            metadata={
                "query_params": query_params.model_dump(),
                "response_source": "historical",
            },
        )

    except ValidationException:
        raise
    except Exception as e:
        raise DataSourceException(f"Failed to get usage history: {str(e)}")


@router.get("/usage/summary", response_model=APIResponse, summary="Usage Summary")
async def get_usage_summary(
    usage_service: UsageService = Depends(get_usage_service),
) -> APIResponse:
    """
    Get aggregated usage summary and statistics.

    Provides:
    - Total tokens used today
    - Number of sessions
    - Average burn rate
    - Peak usage times
    - Efficiency metrics

    Args:
        usage_service: Usage service dependency

    Returns:
        APIResponse with usage summary
    """
    try:
        summary_data = await usage_service.get_usage_summary()

        return APIResponse(
            success=True,
            data=summary_data,
            metadata={
                "summary_date": datetime.now().date().isoformat(),
                "response_source": "aggregated",
            },
        )

    except Exception as e:
        raise DataSourceException(f"Failed to get usage summary: {str(e)}")


@router.get("/usage/live", summary="Live Usage Stream Info")
async def get_live_usage_info() -> APIResponse:
    """
    Get information about live usage streaming capabilities.

    This endpoint provides metadata about WebSocket streaming
    without establishing a WebSocket connection.

    Returns:
        Information about live streaming endpoints and capabilities
    """
    return APIResponse(
        success=True,
        data={
            "websocket_endpoint": "/ws/usage",
            "update_interval_seconds": 3,
            "supported_events": [
                "usage_updated",
                "token_limit_exceeded",
                "plan_switched",
                "session_started",
                "session_ended",
            ],
            "connection_info": {
                "protocol": "WebSocket",
                "message_format": "JSON",
                "heartbeat_interval": 30,
            },
        },
        metadata={"endpoint_type": "stream_info"},
    )
