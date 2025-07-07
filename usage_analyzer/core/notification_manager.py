"""
NotificationManager - Manages notification state and persistence.

This module handles notification triggering, duration tracking, and state
management to provide consistent notification behavior across the application.
"""

from datetime import datetime
from typing import Any, Dict, Optional


class NotificationManager:
    """Manages notification state and persistence logic."""

    # Notification persistence configuration
    NOTIFICATION_MIN_DURATION = 5  # seconds - minimum time to display notifs

    def __init__(self):
        """Initialize notification manager with clean state."""
        self._states = {
            "switch_to_custom": {"triggered": False, "timestamp": None},
            "exceed_max_limit": {"triggered": False, "timestamp": None},
            "tokens_will_run_out": {"triggered": False, "timestamp": None},
        }

    def should_show_notification(
        self,
        notification_type: str,
        condition_met: bool,
        current_time: Optional[datetime] = None,
    ) -> bool:
        """
        Determine whether to show a notification based on condition and state.

        Args:
            notification_type: Type of notification ('switch_to_custom', etc.)
            condition_met: Whether the condition for this notification is true
            current_time: Current timestamp (defaults to datetime.now())

        Returns:
            True if notification should be shown, False otherwise
        """
        if current_time is None:
            current_time = datetime.now()

        if notification_type not in self._states:
            # Unknown notification type - be conservative and don't show
            return False

        state = self._states[notification_type]

        if condition_met:
            if not state["triggered"]:
                # First time triggering - record timestamp
                state["triggered"] = True
                state["timestamp"] = current_time
            return True
        else:
            if state["triggered"]:
                # Check if minimum duration has passed
                elapsed = (current_time - state["timestamp"]).total_seconds()
                if elapsed >= self.NOTIFICATION_MIN_DURATION:
                    # Reset state after minimum duration
                    state["triggered"] = False
                    state["timestamp"] = None
                    return False
                else:
                    # Still within minimum duration - keep showing
                    return True
            return False

    def reset_notification(self, notification_type: str) -> None:
        """
        Manually reset a notification state.

        Args:
            notification_type: Type of notification to reset
        """
        if notification_type in self._states:
            self._states[notification_type] = {"triggered": False, "timestamp": None}

    def reset_all_notifications(self) -> None:
        """Reset all notification states."""
        for notification_type in self._states:
            self.reset_notification(notification_type)

    def get_notification_state(self, notification_type: str) -> Dict[str, Any]:
        """
        Get current state of a notification.

        Args:
            notification_type: Type of notification

        Returns:
            Dictionary with notification state information
        """
        if notification_type not in self._states:
            return {"triggered": False, "timestamp": None, "exists": False}

        state = self._states[notification_type].copy()
        state["exists"] = True
        return state

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get all notification states."""
        return {
            notification_type: self.get_notification_state(notification_type)
            for notification_type in self._states
        }

    def is_notification_active(self, notification_type: str) -> bool:
        """
        Check if a notification is currently active (triggered but not expired).

        Args:
            notification_type: Type of notification

        Returns:
            True if notification is currently active
        """
        if notification_type not in self._states:
            return False

        state = self._states[notification_type]
        return state["triggered"] and state["timestamp"] is not None

    def get_notification_duration(
        self, notification_type: str, current_time: Optional[datetime] = None
    ) -> float:
        """
        Get how long a notification has been active.

        Args:
            notification_type: Type of notification
            current_time: Current timestamp (defaults to datetime.now())

        Returns:
            Duration in seconds, or 0 if notification is not active
        """
        if current_time is None:
            current_time = datetime.now()

        if not self.is_notification_active(notification_type):
            return 0.0

        state = self._states[notification_type]
        return (current_time - state["timestamp"]).total_seconds()


# Global instance for backward compatibility
notification_manager = NotificationManager()


def update_notification_state(
    notification_type: str, condition_met: bool, current_time: datetime
) -> bool:
    """
    Legacy function for backward compatibility.

    Args:
        notification_type: Type of notification
        condition_met: Whether the condition is met
        current_time: Current timestamp

    Returns:
        True if notification should be shown
    """
    return notification_manager.should_show_notification(
        notification_type, condition_met, current_time
    )
