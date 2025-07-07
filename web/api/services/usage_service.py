"""
Usage service for handling usage data operations.

This module provides business logic for usage data retrieval and processing.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

from ...usage_analyzer.services.monitor_service import MonitorService
from ..models.schemas import (
    HistoryQueryParams,
    MetricsSummary,
    PaginationInfo,
    UsageHistoryItem,
    UsageHistoryResponse,
)


class UsageService:
    """Service for usage data operations."""

    def __init__(self):
        """Initialize usage service."""
        self.monitor_service = MonitorService()

    async def get_current_status(self, plan: str = "pro") -> Dict[str, Any]:
        """
        Get current usage status.

        Args:
            plan: Claude plan type

        Returns:
            Current usage status data
        """
        return self.monitor_service.get_current_status(plan)

    async def get_usage_history(
        self, query_params: HistoryQueryParams
    ) -> UsageHistoryResponse:
        """
        Get historical usage data with pagination.

        Args:
            query_params: Query parameters for filtering and pagination

        Returns:
            Paginated historical usage data
        """
        # This is a simplified implementation
        # In a real application, this would query a database

        # For now, we'll return mock data
        # TODO: Implement actual historical data storage and retrieval

        items = self._generate_mock_history_items(query_params)

        # Calculate pagination
        total_items = 150  # Mock total
        total_pages = (
            total_items + query_params.page_size - 1
        ) // query_params.page_size
        has_next = query_params.page < total_pages
        has_previous = query_params.page > 1

        pagination = PaginationInfo(
            page=query_params.page,
            page_size=query_params.page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
        )

        return UsageHistoryResponse(items=items, pagination=pagination)

    async def get_usage_summary(self) -> MetricsSummary:
        """
        Get aggregated usage summary.

        Returns:
            Usage summary with aggregated metrics
        """
        # This is a simplified implementation
        # In a real application, this would aggregate data from storage

        # Get current status to derive some metrics
        current_status = await self.get_current_status()

        # Calculate mock summary data
        total_tokens_today = 2500
        total_sessions_today = 3
        average_burn_rate = 15.5
        peak_usage_time = datetime.now().replace(hour=14, minute=30, second=0)
        efficiency_score = 85.0

        return MetricsSummary(
            total_tokens_used_today=total_tokens_today,
            total_sessions_today=total_sessions_today,
            average_burn_rate=average_burn_rate,
            peak_usage_time=peak_usage_time,
            efficiency_score=efficiency_score,
            cost_estimate=0.025,  # Mock cost estimate
        )

    def _generate_mock_history_items(
        self, query_params: HistoryQueryParams
    ) -> List[UsageHistoryItem]:
        """
        Generate mock historical data items.

        Args:
            query_params: Query parameters

        Returns:
            List of mock history items
        """
        items = []

        # Generate mock data for the requested page
        start_index = (query_params.page - 1) * query_params.page_size

        for i in range(query_params.page_size):
            timestamp = datetime.now() - timedelta(minutes=i * 5 + start_index * 5)

            # Apply date filters if specified
            if query_params.start_date and timestamp < query_params.start_date:
                continue
            if query_params.end_date and timestamp > query_params.end_date:
                continue

            # Mock data
            tokens_used = min(7000, 100 + i * 150 + start_index * 50)
            burn_rate = 10.0 + (i % 5) * 2.5
            plan = query_params.plan_filter or "pro"

            items.append(
                UsageHistoryItem(
                    timestamp=timestamp,
                    tokens_used=tokens_used,
                    burn_rate=burn_rate,
                    plan=plan,
                    session_id=f"session_{start_index + i:03d}",
                )
            )

        return items

    async def invalidate_cache(self) -> Dict[str, str]:
        """
        Invalidate usage data cache.

        Returns:
            Status of cache invalidation
        """
        try:
            # Access the cache from the data source manager
            from ...usage_analyzer.core.cache import global_usage_cache

            global_usage_cache.invalidate()

            return {
                "status": "success",
                "message": "Usage data cache invalidated",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to invalidate cache: {str(e)}",
                "timestamp": datetime.now().isoformat(),
            }
