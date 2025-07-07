"""
Event System - Event-driven architecture for real-time updates.

This module provides an event system for broadcasting usage updates
and other changes to multiple subscribers in real-time.
"""

import asyncio
import json
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union


class EventType(Enum):
    """Types of events that can be broadcast."""

    USAGE_UPDATED = "usage_updated"
    TOKEN_LIMIT_EXCEEDED = "token_limit_exceeded"
    PLAN_SWITCHED = "plan_switched"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    NOTIFICATION_TRIGGERED = "notification_triggered"
    DATA_SOURCE_CHANGED = "data_source_changed"
    CACHE_INVALIDATED = "cache_invalidated"


class Event:
    """Event data structure."""

    def __init__(
        self, event_type: EventType, data: Dict[str, Any], source: str = "unknown"
    ):
        """
        Initialize event.

        Args:
            event_type: Type of event
            data: Event data payload
            source: Source component that triggered the event
        """
        self.event_type = event_type
        self.data = data
        self.source = source
        self.timestamp = datetime.now()
        self.event_id = f"{event_type.value}_{self.timestamp.timestamp()}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())


class EventSubscriber(ABC):
    """Abstract base class for event subscribers."""

    @abstractmethod
    async def handle_event(self, event: Event) -> None:
        """
        Handle an event.

        Args:
            event: Event to handle
        """
        pass

    @property
    @abstractmethod
    def subscriber_id(self) -> str:
        """Get unique subscriber ID."""
        pass


class CallableSubscriber(EventSubscriber):
    """Subscriber that wraps a callable function."""

    def __init__(self, callback: Callable[[Event], None], subscriber_id: str):
        """
        Initialize callable subscriber.

        Args:
            callback: Function to call when event occurs
            subscriber_id: Unique identifier for this subscriber
        """
        self.callback = callback
        self._subscriber_id = subscriber_id

    async def handle_event(self, event: Event) -> None:
        """Handle event by calling the callback."""
        try:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(event)
            else:
                self.callback(event)
        except Exception as e:
            # Log error but don't propagate to avoid breaking other subscribers
            print(f"Error in subscriber {self.subscriber_id}: {e}")

    @property
    def subscriber_id(self) -> str:
        """Get subscriber ID."""
        return self._subscriber_id


class EventBus:
    """Central event bus for managing events and subscribers."""

    def __init__(self):
        """Initialize event bus."""
        self._subscribers: Dict[EventType, List[EventSubscriber]] = {}
        self._all_subscribers: List[EventSubscriber] = []
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._lock = threading.RLock()

    def subscribe(
        self, event_type: Union[EventType, List[EventType]], subscriber: EventSubscriber
    ) -> None:
        """
        Subscribe to events.

        Args:
            event_type: Event type(s) to subscribe to
            subscriber: Subscriber to add
        """
        with self._lock:
            if isinstance(event_type, list):
                for et in event_type:
                    self._subscribe_single(et, subscriber)
            else:
                self._subscribe_single(event_type, subscriber)

    def subscribe_all(self, subscriber: EventSubscriber) -> None:
        """
        Subscribe to all events.

        Args:
            subscriber: Subscriber to add
        """
        with self._lock:
            if subscriber not in self._all_subscribers:
                self._all_subscribers.append(subscriber)

    def unsubscribe(
        self, subscriber: EventSubscriber, event_type: Optional[EventType] = None
    ) -> None:
        """
        Unsubscribe from events.

        Args:
            subscriber: Subscriber to remove
            event_type: Specific event type to unsubscribe from (None for all)
        """
        with self._lock:
            if event_type is None:
                # Remove from all event types
                for subscribers in self._subscribers.values():
                    if subscriber in subscribers:
                        subscribers.remove(subscriber)

                # Remove from all subscribers
                if subscriber in self._all_subscribers:
                    self._all_subscribers.remove(subscriber)
            else:
                # Remove from specific event type
                if event_type in self._subscribers:
                    if subscriber in self._subscribers[event_type]:
                        self._subscribers[event_type].remove(subscriber)

    async def emit(self, event: Event) -> None:
        """
        Emit an event to all subscribers.

        Args:
            event: Event to emit
        """
        with self._lock:
            # Add to history
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)

            # Get subscribers for this event type
            subscribers = []

            # Add specific subscribers
            if event.event_type in self._subscribers:
                subscribers.extend(self._subscribers[event.event_type])

            # Add global subscribers
            subscribers.extend(self._all_subscribers)

        # Notify subscribers (outside of lock to avoid deadlock)
        await self._notify_subscribers(subscribers, event)

    def emit_sync(self, event: Event) -> None:
        """
        Emit an event synchronously.

        Args:
            event: Event to emit
        """
        asyncio.create_task(self.emit(event))

    def get_event_history(self, limit: int = 100) -> List[Event]:
        """
        Get recent event history.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of recent events
        """
        with self._lock:
            return (
                self._event_history[-limit:]
                if limit > 0
                else self._event_history.copy()
            )

    def get_subscribers_count(self) -> Dict[str, int]:
        """Get count of subscribers by event type."""
        with self._lock:
            counts = {}
            for event_type, subscribers in self._subscribers.items():
                counts[event_type.value] = len(subscribers)
            counts["all_events"] = len(self._all_subscribers)
            return counts

    def clear_history(self) -> None:
        """Clear event history."""
        with self._lock:
            self._event_history.clear()

    def _subscribe_single(
        self, event_type: EventType, subscriber: EventSubscriber
    ) -> None:
        """Subscribe to a single event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        if subscriber not in self._subscribers[event_type]:
            self._subscribers[event_type].append(subscriber)

    async def _notify_subscribers(
        self, subscribers: List[EventSubscriber], event: Event
    ) -> None:
        """Notify all subscribers of an event."""
        if not subscribers:
            return

        # Create tasks for all subscribers
        tasks = []
        for subscriber in subscribers:
            task = asyncio.create_task(subscriber.handle_event(event))
            tasks.append(task)

        # Wait for all subscribers to process the event
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


class UsageEventEmitter:
    """Helper class for emitting usage-related events."""

    def __init__(self, event_bus: EventBus):
        """
        Initialize usage event emitter.

        Args:
            event_bus: Event bus to emit events to
        """
        self.event_bus = event_bus

    async def emit_usage_updated(self, usage_data: Dict[str, Any]) -> None:
        """Emit usage updated event."""
        event = Event(EventType.USAGE_UPDATED, {"usage": usage_data}, "usage_monitor")
        await self.event_bus.emit(event)

    async def emit_token_limit_exceeded(
        self, tokens_used: int, token_limit: int
    ) -> None:
        """Emit token limit exceeded event."""
        event = Event(
            EventType.TOKEN_LIMIT_EXCEEDED,
            {
                "tokens_used": tokens_used,
                "token_limit": token_limit,
                "excess": tokens_used - token_limit,
            },
            "usage_monitor",
        )
        await self.event_bus.emit(event)

    async def emit_plan_switched(
        self, old_plan: str, new_plan: str, old_limit: int, new_limit: int
    ) -> None:
        """Emit plan switched event."""
        event = Event(
            EventType.PLAN_SWITCHED,
            {
                "old_plan": old_plan,
                "new_plan": new_plan,
                "old_limit": old_limit,
                "new_limit": new_limit,
            },
            "usage_monitor",
        )
        await self.event_bus.emit(event)

    async def emit_notification_triggered(
        self, notification_type: str, data: Dict[str, Any]
    ) -> None:
        """Emit notification triggered event."""
        event = Event(
            EventType.NOTIFICATION_TRIGGERED,
            {"notification_type": notification_type, "notification_data": data},
            "notification_manager",
        )
        await self.event_bus.emit(event)


# Global event bus instance
global_event_bus = EventBus()
global_usage_emitter = UsageEventEmitter(global_event_bus)


def create_subscriber(
    callback: Callable[[Event], None], subscriber_id: str
) -> CallableSubscriber:
    """
    Create a subscriber from a callback function.

    Args:
        callback: Function to call when event occurs
        subscriber_id: Unique identifier for subscriber

    Returns:
        CallableSubscriber instance
    """
    return CallableSubscriber(callback, subscriber_id)


def subscribe_to_usage_events(
    callback: Callable[[Event], None], subscriber_id: str
) -> CallableSubscriber:
    """
    Subscribe to usage-related events.

    Args:
        callback: Function to call when usage events occur
        subscriber_id: Unique identifier for subscriber

    Returns:
        Subscriber instance
    """
    subscriber = create_subscriber(callback, subscriber_id)

    usage_events = [
        EventType.USAGE_UPDATED,
        EventType.TOKEN_LIMIT_EXCEEDED,
        EventType.PLAN_SWITCHED,
    ]

    global_event_bus.subscribe(usage_events, subscriber)
    return subscriber
