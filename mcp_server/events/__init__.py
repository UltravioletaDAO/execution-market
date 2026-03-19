"""
Event Bus — Universal pub/sub for Execution Market.

MVP: asyncio-based in-process pub/sub.
Scale: Redis Streams with consumer groups.
"""

from .models import EMEvent, EventSource
from .bus import EventBus, get_event_bus

__all__ = ["EMEvent", "EventSource", "EventBus", "get_event_bus"]
