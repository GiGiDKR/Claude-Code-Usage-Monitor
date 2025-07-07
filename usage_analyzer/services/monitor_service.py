"""
MonitorService - High-level service for usage monitoring.

This service orchestrates data loading, calculations, and formatting
to provide a clean interface for both console and web applications.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ..core.calculator import BurnRateCalculator
from ..core.data_source import DataSourceManager, default_data_source_manager
from ..core.events import UsageEventEmitter, global_event_bus


class MonitorService:
    """High-level service for orchestrating usage monitoring functionality."""

    def __init__(self, data_source_manager: Optional[DataSourceManager] = None):
        """
        Initialize monitor service.

        Args:
            data_source_manager: Optional custom data source manager
        """
        self.calculator = BurnRateCalculator()
        self.data_source_manager = data_source_manager or default_data_source_manager
        self.event_emitter = UsageEventEmitter(global_event_bus)
        self._last_status = None

    def get_current_status(self, plan: str = "pro") -> Dict[str, Any]:
        """
        Get comprehensive current usage status.

        Args:
            plan: Claude plan type (pro, max5, max20, custom_max)

        Returns:
            Dictionary with complete status information
        """
        # Get raw data using data source manager
        data = self.data_source_manager.get_usage_data()
        if not data or "blocks" not in data:
            return {
                "status": "no_data",
                "error": "Failed to get usage data",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data_source_available": (self.data_source_manager.is_available()),
            }

        # Find active block
        active_block = None
        for block in data["blocks"]:
            if block.get("isActive", False):
                active_block = block
                break

        if not active_block:
            return {
                "status": "no_active_session",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "plan": plan,
                "token_limit": self._get_token_limit(plan),
            }

        # Calculate comprehensive metrics
        tokens_used = active_block.get("totalTokens", 0)
        blocks_for_custom = data["blocks"] if plan == "custom_max" else None
        token_limit = self._get_token_limit(plan, blocks_for_custom)

        # Auto-switch logic for exceeded limits
        original_limit = self._get_token_limit(plan)
        if tokens_used > token_limit and plan != "custom_max":
            new_limit = self._get_token_limit("custom_max", data["blocks"])
            if new_limit > token_limit:
                token_limit = new_limit
                plan = "custom_max"  # Auto-switched

        # Time calculations
        start_time_str = active_block.get("startTime")
        end_time_str = active_block.get("endTime")

        current_time = datetime.now(timezone.utc)

        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
            if start_time.tzinfo is None:
                start_time = timezone.utc.localize(start_time)
            else:
                start_time = start_time.astimezone(timezone.utc)
        else:
            start_time = current_time

        if end_time_str:
            reset_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
            if reset_time.tzinfo is None:
                reset_time = timezone.utc.localize(reset_time)
            else:
                reset_time = reset_time.astimezone(timezone.utc)
        else:
            reset_time = start_time + timedelta(hours=5)

        # Calculate burn rate
        burn_rate = self._calculate_hourly_burn_rate(data["blocks"], current_time)

        # Calculate projections
        usage_percentage = (tokens_used / token_limit) * 100 if token_limit > 0 else 0
        tokens_left = token_limit - tokens_used
        time_to_reset = reset_time - current_time

        # Predict when tokens will run out
        if burn_rate > 0 and tokens_left > 0:
            minutes_to_depletion = tokens_left / burn_rate
            predicted_end_time = current_time + timedelta(minutes=minutes_to_depletion)
        else:
            predicted_end_time = reset_time

        # Build notification conditions
        notifications = self._get_notification_conditions(
            tokens_used,
            token_limit,
            original_limit,
            predicted_end_time,
            reset_time,
            plan,
        )

        duration_minutes = (current_time - start_time).total_seconds() / 60
        time_to_reset_minutes = time_to_reset.total_seconds() / 60

        tokens_will_run_out = predicted_end_time < reset_time
        minutes_to_depletion = (
            (predicted_end_time - current_time).total_seconds() / 60
            if predicted_end_time > current_time
            else 0
        )

        result = {
            "status": "active",
            "timestamp": current_time.isoformat(),
            "plan": plan,
            "session": {
                "start_time": start_time.isoformat(),
                "reset_time": reset_time.isoformat(),
                "duration_minutes": duration_minutes,
                "time_to_reset_minutes": time_to_reset_minutes,
            },
            "usage": {
                "tokens_used": tokens_used,
                "token_limit": token_limit,
                "tokens_left": tokens_left,
                "usage_percentage": usage_percentage,
                "burn_rate_tokens_per_minute": burn_rate,
            },
            "predictions": {
                "predicted_end_time": predicted_end_time.isoformat(),
                "tokens_will_run_out_before_reset": tokens_will_run_out,
                "minutes_to_depletion": minutes_to_depletion,
            },
            "notifications": notifications,
            "raw_blocks": data["blocks"],  # For debugging/advanced features
        }

        # Emit events for state changes (async, non-blocking)
        self._emit_events_if_needed(result)

        # Store last status for comparison
        self._last_status = result

        return result

    def _get_token_limit(self, plan: str, blocks: Optional[List[Dict]] = None) -> int:
        """Get token limit for a plan."""
        limits = {"pro": 7000, "max5": 35000, "max20": 140000}

        if plan == "custom_max" and blocks:
            # Find highest token count from previous sessions
            max_tokens = 0
            for block in blocks:
                tokens = block.get("totalTokens", 0)
                if tokens > max_tokens:
                    max_tokens = tokens
            # Add 10% buffer to the highest found
            return int(max_tokens * 1.1) if max_tokens > 0 else limits["pro"]

        return limits.get(plan, limits["pro"])

    def _calculate_hourly_burn_rate(
        self, blocks: List[Dict], current_time: datetime
    ) -> float:
        """Calculate burn rate from blocks in the last hour."""
        one_hour_ago = current_time - timedelta(hours=1)

        total_tokens = 0
        earliest_time = current_time

        for block in blocks:
            if not block.get("isActive", False):
                continue

            start_time_str = block.get("startTime")
            if not start_time_str:
                continue

            start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
            if start_time.tzinfo is None:
                start_time = timezone.utc.localize(start_time)
            else:
                start_time = start_time.astimezone(timezone.utc)

            # Only include blocks that have activity in the last hour
            if start_time >= one_hour_ago:
                total_tokens += block.get("totalTokens", 0)
                if start_time < earliest_time:
                    earliest_time = start_time

        if total_tokens == 0 or earliest_time >= current_time:
            return 0.0

        # Calculate rate based on actual time elapsed
        elapsed_minutes = (current_time - earliest_time).total_seconds() / 60
        return total_tokens / elapsed_minutes if elapsed_minutes > 0 else 0.0

    def _get_notification_conditions(
        self,
        tokens_used: int,
        token_limit: int,
        original_limit: int,
        predicted_end_time: datetime,
        reset_time: datetime,
        current_plan: str,
    ) -> Dict[str, Any]:
        """Calculate notification conditions."""
        return {
            "plan_auto_switched": token_limit > original_limit,
            "tokens_exceeded_limit": tokens_used > token_limit,
            "tokens_will_run_out_before_reset": predicted_end_time < reset_time,
            "usage_warning_level": self._get_usage_warning_level(
                tokens_used, token_limit
            ),
            "current_plan": current_plan,
            "auto_switched_to_custom": current_plan == "custom_max"
            and token_limit > original_limit,
        }

    def _get_usage_warning_level(self, tokens_used: int, token_limit: int) -> str:
        """Get warning level based on usage percentage."""
        if token_limit == 0:
            return "safe"

        percentage = (tokens_used / token_limit) * 100

        if percentage >= 90:
            return "critical"
        elif percentage >= 70:
            return "warning"
        elif percentage >= 50:
            return "moderate"
        else:
            return "safe"

    def _emit_events_if_needed(self, current_status: Dict[str, Any]) -> None:
        """
        Emit events based on status changes.

        Args:
            current_status: Current status data
        """
        import asyncio

        try:
            # Check for usage updates
            if self._last_status is None or current_status.get("usage", {}).get(
                "tokens_used"
            ) != self._last_status.get("usage", {}).get("tokens_used"):
                # Emit usage updated event
                asyncio.create_task(
                    self.event_emitter.emit_usage_updated(current_status)
                )

            # Check for token limit exceeded
            notifications = current_status.get("notifications", {})
            if notifications.get("tokens_exceeded_limit"):
                usage = current_status.get("usage", {})
                asyncio.create_task(
                    self.event_emitter.emit_token_limit_exceeded(
                        usage.get("tokens_used", 0), usage.get("token_limit", 0)
                    )
                )

            # Check for plan switches
            if self._last_status is not None and current_status.get(
                "plan"
            ) != self._last_status.get("plan"):
                last_usage = self._last_status.get("usage", {})
                current_usage = current_status.get("usage", {})
                last_limit = last_usage.get("token_limit", 0)
                current_limit = current_usage.get("token_limit", 0)

                asyncio.create_task(
                    self.event_emitter.emit_plan_switched(
                        self._last_status.get("plan", "unknown"),
                        current_status.get("plan", "unknown"),
                        last_limit,
                        current_limit,
                    )
                )

        except Exception:
            # Don't let event emission errors break the main functionality
            pass
