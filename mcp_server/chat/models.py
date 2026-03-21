"""
Chat Message Models — Pydantic schemas for the WebSocket chat relay.

Defines the wire format for messages between mobile clients and the
MCP server chat relay (which bridges to IRC task channels).
"""

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    """Message sent by a mobile client to the chat relay."""

    type: Literal["message"] = "message"
    text: str = Field(..., max_length=2000)


class ChatMessageOut(BaseModel):
    """Message sent from the chat relay to connected clients."""

    type: Literal["message", "system", "error"] = "message"
    nick: str = ""
    text: str
    source: Literal["irc", "mobile", "xmtp", "system"] = "system"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    task_id: str = ""


class ChatError(BaseModel):
    """Error message sent to a single client."""

    type: Literal["error"] = "error"
    code: str  # "action_blocked", "auth_failed", "task_not_found"
    text: str


class ChatHistory(BaseModel):
    """Initial history payload delivered on WebSocket connect."""

    messages: list[ChatMessageOut] = Field(default_factory=list)
    channel: str
    task_id: str
    connected_users: int = 0


class ChatStatus(BaseModel):
    """Health/status of the chat relay subsystem."""

    enabled: bool = False
    irc_connected: bool = False
    active_channels: int = 0
    connected_clients: int = 0


# ---------------------------------------------------------------------------
# Guardrail: blocked-action patterns
# ---------------------------------------------------------------------------

# Phrases that indicate the user is trying to trigger a platform action
# via chat. The relay MUST reject these and send a ChatError instead.
ACTION_PATTERNS: list[str] = [
    "/approve",
    "/reject",
    "/cancel",
    "/pay",
    "/release",
    "/refund",
    "/dispute",
    "/assign",
    "/claim",
]


def is_blocked_action(text: str) -> Optional[str]:
    """Return the matched action command if text starts with one, else None."""
    lower = text.strip().lower()
    for pattern in ACTION_PATTERNS:
        if lower.startswith(pattern):
            return pattern
    return None
