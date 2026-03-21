"""
EMEvent — Universal event model for Execution Market.

All events flowing through the Event Bus use this schema.
Designed for anti-echo (source-based filtering) and correlation tracking.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EventSource(str, Enum):
    """Origin of an event — used for anti-echo filtering."""

    MCP_TOOL = "mcp_tool"
    REST_API = "rest_api"
    WEBHOOK = "webhook"
    MESHRELAY = "meshrelay"
    XMTP = "xmtp"
    DASHBOARD = "dashboard"
    SYSTEM = "system"


class EMEvent(BaseModel):
    """
    Universal event model.

    Every event in the system is an EMEvent. Adapters subscribe to event
    patterns and skip events from their own source (anti-echo).
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str = Field(..., description="Dotted event type, e.g. 'task.created'")
    version: str = "1.0"
    task_id: Optional[str] = None
    source: EventSource = EventSource.SYSTEM
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    target_rooms: List[str] = Field(default_factory=list)
    target_users: List[str] = Field(default_factory=list)
    broadcast: bool = False

    def matches(self, pattern: str) -> bool:
        """Check if event_type matches a subscription pattern.

        Supports:
          - Exact: "task.created"
          - Wildcard: "task.*"
          - All: "*"
        """
        if pattern == "*":
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return self.event_type.startswith(prefix + ".")
        return self.event_type == pattern
