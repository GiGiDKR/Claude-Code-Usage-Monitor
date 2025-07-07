"""
Pydantic models for API responses.

This module defines all the data models used for API requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class PlanType(str, Enum):
    """Claude subscription plan types."""

    PRO = "pro"
    MAX5 = "max5"
    MAX20 = "max20"
    CUSTOM_MAX = "custom_max"


class WarningLevel(str, Enum):
    """Usage warning levels."""

    SAFE = "safe"
    MODERATE = "moderate"
    WARNING = "warning"
    CRITICAL = "critical"


class SessionInfo(BaseModel):
    """Session timing information."""

    start_time: datetime = Field(..., description="Session start time in ISO format")
    reset_time: datetime = Field(..., description="Token reset time in ISO format")
    duration_minutes: float = Field(..., description="Session duration in minutes")
    time_to_reset_minutes: float = Field(..., description="Time until reset in minutes")


class UsageInfo(BaseModel):
    """Token usage information."""

    tokens_used: int = Field(..., description="Number of tokens used")
    token_limit: int = Field(..., description="Token limit for current plan")
    tokens_left: int = Field(..., description="Tokens remaining")
    usage_percentage: float = Field(..., description="Usage percentage (0-100)")
    burn_rate_tokens_per_minute: float = Field(..., description="Current burn rate")


class PredictionInfo(BaseModel):
    """Usage predictions."""

    predicted_end_time: datetime = Field(
        ..., description="Predicted token depletion time"
    )
    tokens_will_run_out_before_reset: bool = Field(
        ..., description="Whether tokens will run out before reset"
    )
    minutes_to_depletion: float = Field(..., description="Minutes until depletion")


class NotificationInfo(BaseModel):
    """Notification conditions."""

    plan_auto_switched: bool = Field(..., description="Whether plan was auto-switched")
    tokens_exceeded_limit: bool = Field(
        ..., description="Whether tokens exceeded limit"
    )
    tokens_will_run_out_before_reset: bool = Field(
        ..., description="Whether tokens will run out"
    )
    usage_warning_level: WarningLevel = Field(..., description="Current warning level")
    current_plan: PlanType = Field(..., description="Current active plan")
    auto_switched_to_custom: bool = Field(
        ..., description="Whether auto-switched to custom plan"
    )


class UsageStatus(BaseModel):
    """Complete usage status response."""

    status: str = Field(..., description="Status of the monitoring system")
    timestamp: datetime = Field(..., description="Response timestamp")
    plan: PlanType = Field(..., description="Current plan type")
    session: SessionInfo = Field(..., description="Session information")
    usage: UsageInfo = Field(..., description="Token usage information")
    predictions: PredictionInfo = Field(..., description="Usage predictions")
    notifications: NotificationInfo = Field(..., description="Notification conditions")
    data_source_available: Optional[bool] = Field(
        None, description="Whether data source is available"
    )


class HealthStatus(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status (healthy/unhealthy)")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Application version")
    uptime_seconds: float = Field(..., description="Uptime in seconds")
    data_source_status: str = Field(..., description="Data source availability")
    cache_stats: Optional[Dict[str, Any]] = Field(None, description="Cache statistics")


class UsageHistoryItem(BaseModel):
    """Historical usage data point."""

    timestamp: datetime = Field(..., description="Data point timestamp")
    tokens_used: int = Field(..., description="Tokens used at this point")
    burn_rate: float = Field(..., description="Burn rate at this point")
    plan: PlanType = Field(..., description="Plan active at this point")
    session_id: Optional[str] = Field(None, description="Session identifier")


class PaginationInfo(BaseModel):
    """Pagination metadata."""

    page: int = Field(..., description="Current page number (1-based)")
    page_size: int = Field(..., description="Number of items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")


class UsageHistoryResponse(BaseModel):
    """Historical usage data with pagination."""

    items: List[UsageHistoryItem] = Field(..., description="Historical usage data")
    pagination: PaginationInfo = Field(..., description="Pagination information")


class MetricsSummary(BaseModel):
    """Aggregated metrics summary."""

    total_tokens_used_today: int = Field(..., description="Total tokens used today")
    total_sessions_today: int = Field(..., description="Number of sessions today")
    average_burn_rate: float = Field(..., description="Average burn rate")
    peak_usage_time: Optional[datetime] = Field(None, description="Time of peak usage")
    efficiency_score: float = Field(..., description="Usage efficiency score (0-100)")
    cost_estimate: Optional[float] = Field(None, description="Estimated cost")


class ConfigurationSettings(BaseModel):
    """User configuration settings."""

    plan: PlanType = Field(..., description="Selected Claude plan")
    timezone: str = Field(..., description="User timezone")
    theme: str = Field(..., description="UI theme preference")
    notifications_enabled: bool = Field(
        ..., description="Whether notifications are enabled"
    )
    refresh_interval: int = Field(..., description="Data refresh interval in seconds")
    custom_token_limit: Optional[int] = Field(None, description="Custom token limit")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: datetime = Field(..., description="Error timestamp")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )


class WebSocketMessage(BaseModel):
    """WebSocket message model."""

    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(..., description="Message timestamp")


class EventMessage(BaseModel):
    """Event system message model."""

    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Type of event")
    source: str = Field(..., description="Event source component")
    timestamp: datetime = Field(..., description="Event timestamp")
    data: Dict[str, Any] = Field(..., description="Event data payload")


# Request models


class ConfigurationUpdate(BaseModel):
    """Configuration update request."""

    plan: Optional[PlanType] = Field(None, description="Plan to update to")
    timezone: Optional[str] = Field(None, description="Timezone to set")
    theme: Optional[str] = Field(None, description="Theme to set")
    notifications_enabled: Optional[bool] = Field(
        None, description="Enable/disable notifications"
    )
    refresh_interval: Optional[int] = Field(
        None, description="Refresh interval in seconds"
    )
    custom_token_limit: Optional[int] = Field(None, description="Custom token limit")


class HistoryQueryParams(BaseModel):
    """Query parameters for history endpoint."""

    page: int = Field(1, ge=1, description="Page number (1-based)")
    page_size: int = Field(50, ge=1, le=1000, description="Items per page")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    plan_filter: Optional[PlanType] = Field(None, description="Filter by plan type")


# Response wrapper for consistent API responses
class APIResponse(BaseModel):
    """Generic API response wrapper."""

    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[
        Union[
            UsageStatus,
            HealthStatus,
            UsageHistoryResponse,
            MetricsSummary,
            ConfigurationSettings,
            Dict[str, Any],
        ]
    ] = Field(None, description="Response data")
    error: Optional[ErrorResponse] = Field(
        None, description="Error information if request failed"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
