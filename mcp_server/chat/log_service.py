"""
ChatLogService — Persistence layer for task chat messages.

Provides a clean interface for logging and querying chat messages from
the ``task_chat_log`` table. Used by:
- ``relay.py``: persist user messages and load history on connect
- ``event_injector.py``: persist system messages
- ``guardrail.py`` (via relay): persist blocked action attempts
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .models import ChatMessageOut

logger = logging.getLogger(__name__)


class ChatLogService:
    """Centralized chat message persistence."""

    def __init__(self):
        self._stats = {"logged": 0, "errors": 0}

    @staticmethod
    def _get_client():
        """Get Supabase client (service role for bypass RLS)."""
        import supabase_client as db

        return db.get_supabase_client()

    async def log_message(
        self,
        task_id: str,
        nick: str,
        text: str,
        source: str = "mobile",
        msg_type: str = "message",
    ) -> None:
        """Persist a chat message to task_chat_log.

        Fire-and-forget — errors are logged but never raised.
        """
        try:
            client = self._get_client()
            client.table("task_chat_log").insert(
                {
                    "task_id": task_id,
                    "nick": nick,
                    "text": text,
                    "source": source,
                    "type": msg_type,
                }
            ).execute()
            self._stats["logged"] += 1
        except Exception as e:
            self._stats["errors"] += 1
            logger.debug("Could not persist chat message: %s", e)

    async def get_history(
        self,
        task_id: str,
        limit: int = 50,
    ) -> list[ChatMessageOut]:
        """Load recent chat messages for a task, oldest first."""
        try:
            client = self._get_client()
            result = (
                client.table("task_chat_log")
                .select("nick, text, source, type, created_at")
                .eq("task_id", task_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            if not result.data:
                return []

            messages = []
            for row in reversed(result.data):  # oldest first
                messages.append(
                    ChatMessageOut(
                        type=row.get("type", "message"),
                        nick=row.get("nick", ""),
                        text=row.get("text", ""),
                        source=row.get("source", "system"),
                        timestamp=row.get("created_at", datetime.now(timezone.utc)),
                        task_id=task_id,
                    )
                )
            return messages
        except Exception as e:
            logger.debug("Could not load chat history for %s: %s", task_id, e)
            return []

    async def get_blocked_attempts(
        self,
        task_id: str,
        limit: int = 100,
    ) -> list[ChatMessageOut]:
        """Return blocked action attempts for audit purposes."""
        try:
            client = self._get_client()
            result = (
                client.table("task_chat_log")
                .select("nick, text, source, type, created_at")
                .eq("task_id", task_id)
                .eq("type", "blocked_action")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            if not result.data:
                return []

            return [
                ChatMessageOut(
                    type=row.get("type", "blocked_action"),
                    nick=row.get("nick", ""),
                    text=row.get("text", ""),
                    source=row.get("source", "mobile"),
                    timestamp=row.get("created_at", datetime.now(timezone.utc)),
                    task_id=task_id,
                )
                for row in result.data
            ]
        except Exception as e:
            logger.debug("Could not load blocked attempts for %s: %s", task_id, e)
            return []

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)


# Module-level singleton
_instance: Optional[ChatLogService] = None


def get_log_service() -> ChatLogService:
    """Get or create the ChatLogService singleton."""
    global _instance
    if _instance is None:
        _instance = ChatLogService()
    return _instance
