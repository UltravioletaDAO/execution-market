"""
ChatRelay — WebSocket endpoint bridging mobile clients to IRC task channels.

Endpoint: ``/ws/chat/{task_id}``

Flow:
1. Client opens WebSocket with ``?token=JWT``
2. Server verifies JWT and extracts executor_id
3. Server verifies executor is assigned to the task
4. Server subscribes to ``#task-{task_id[:8]}`` on IRCPool
5. Messages flow bidirectionally until disconnect

Guardrails (Phase 4):
- Layer 1: Slash-command blocking (``/approve``, ``/cancel``, etc.)
- Layer 2: NLP pattern matching for natural-language action requests (EN/ES)
- Rate limiting: 1 msg/sec per user, 100 msg/hour per user per task
- All blocked attempts and join/leave events logged to ``task_chat_log``
"""

import asyncio
import logging
import secrets
import time
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from .models import (
    ChatMessageIn,
    ChatMessageOut,
    ChatError,
    ChatHistory,
)
from .guardrail import GuardrailFilter
from .log_service import get_log_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat"])

# Module-level guardrail filter (shared across connections)
_guardrail = GuardrailFilter()


# ---------------------------------------------------------------------------
# Rate limiter (in-memory, resets on process restart)
# ---------------------------------------------------------------------------


class _RateLimiter:
    """Per-user rate limiter for chat messages.

    - Max ``per_second`` messages per second (default 1)
    - Max ``per_hour`` messages per hour per task (default 100)
    """

    def __init__(self, per_second: int = 1, per_hour: int = 100):
        self._per_second = per_second
        self._per_hour = per_hour
        # {user_key: last_message_timestamp}
        self._last_msg: dict[str, float] = {}
        # {user_key:task_id: [timestamps_this_hour]}
        self._hourly: dict[str, list[float]] = defaultdict(list)

    def check(self, user_key: str, task_id: str) -> Optional[str]:
        """Return an error message if rate limited, else None."""
        now = time.monotonic()

        # Per-second check
        last = self._last_msg.get(user_key, 0.0)
        if now - last < (1.0 / self._per_second):
            return "Too many messages. Please wait a moment before sending again."

        # Per-hour check
        hourly_key = f"{user_key}:{task_id}"
        window = self._hourly[hourly_key]
        cutoff = now - 3600.0
        # Prune old entries
        self._hourly[hourly_key] = [t for t in window if t > cutoff]
        if len(self._hourly[hourly_key]) >= self._per_hour:
            return f"Message limit reached ({self._per_hour}/hour for this task). Try again later."

        # Record
        self._last_msg[user_key] = now
        self._hourly[hourly_key].append(now)
        return None


_rate_limiter = _RateLimiter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task_channel(task_id: str) -> str:
    """Derive the IRC channel name from a task ID."""
    return f"#task-{task_id[:8].lower()}"


async def _verify_token(token: str) -> Optional[dict]:
    """Verify a JWT token and return user info.

    Returns dict with ``executor_id``, ``wallet``, ``nick`` or None.
    For MVP, we accept Supabase anon tokens and Dynamic.xyz JWTs.
    """
    if not token:
        return None

    try:
        # Try Supabase JWT first
        import supabase_client as db

        client = db.get_supabase_client()
        # Supabase auth.getUser with the JWT
        user_resp = client.auth.get_user(token)
        if user_resp and user_resp.user:
            user_id = user_resp.user.id
            # Look up executor
            result = (
                client.table("executors")
                .select("id, wallet_address, name")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            if result.data:
                row = result.data[0]
                return {
                    "executor_id": row["id"],
                    "wallet": row.get("wallet_address", ""),
                    "nick": row.get("name", "worker"),
                    "user_id": user_id,
                }
            # User exists but no executor profile — still allow with user_id
            return {
                "executor_id": None,
                "wallet": "",
                "nick": "user",
                "user_id": user_id,
            }
    except Exception as e:
        logger.debug("Chat token verification failed: %s", e)

    return None


async def _is_task_participant(task_id: str, user_info: dict) -> bool:
    """Check if the user is the assigned executor or the publishing agent."""
    try:
        import supabase_client as db

        client = db.get_supabase_client()
        result = (
            client.table("tasks")
            .select("executor_id, agent_wallet, status")
            .eq("id", task_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            return False

        task = result.data[0]

        # Must be in an active state
        if task["status"] not in (
            "accepted",
            "in_progress",
            "submitted",
            "verifying",
        ):
            return False

        # Executor match
        if user_info.get("executor_id") and task.get("executor_id"):
            if str(user_info["executor_id"]) == str(task["executor_id"]):
                return True

        # Wallet match (agent or worker)
        if user_info.get("wallet") and task.get("agent_wallet"):
            if user_info["wallet"].lower() == task["agent_wallet"].lower():
                return True

        return False
    except Exception:
        logger.exception("Error checking task participant for %s", task_id)
        return False


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/ws/chat/{task_id}")
async def chat_websocket(
    websocket: WebSocket,
    task_id: str,
    token: str = Query(default=""),
):
    """WebSocket endpoint for per-task chat, bridged to IRC."""
    log_svc = get_log_service()

    # ---- Auth ----
    user_info = await _verify_token(token)
    if not user_info:
        await websocket.close(code=4001, reason="Authentication required")
        return

    # ---- Authorization ----
    is_participant = await _is_task_participant(task_id, user_info)
    if not is_participant:
        await websocket.close(code=4003, reason="Not authorized for this task")
        return

    # ---- Feature flag check ----
    try:
        from config.platform_config import PlatformConfig

        enabled = await PlatformConfig.get("feature.task_chat_enabled", False)
        if not enabled:
            await websocket.close(code=4004, reason="Task chat is not enabled")
            return
    except Exception:
        pass  # If config unavailable, allow (fail open for dev)

    await websocket.accept()

    subscriber_id = secrets.token_hex(8)
    channel = _task_channel(task_id)
    nick = user_info.get("nick", "worker")[:16]
    user_key = user_info.get("user_id", subscriber_id)
    irc_pool = None

    try:
        # ---- Send history ----
        history_messages = await log_svc.get_history(task_id)
        history = ChatHistory(
            messages=history_messages,
            channel=channel,
            task_id=task_id,
            connected_users=0,  # will be updated by pool
        )
        await websocket.send_json(history.model_dump(mode="json"))

        # ---- Subscribe to IRC channel ----
        from .irc_pool import IRCPool

        irc_pool = IRCPool.get_instance()

        async def on_irc_message(ch: str, irc_nick: str, text: str) -> None:
            """Forward IRC message to this WebSocket client."""
            msg = ChatMessageOut(
                type="message",
                nick=irc_nick,
                text=text,
                source="irc",
                task_id=task_id,
            )
            try:
                await websocket.send_json(msg.model_dump(mode="json"))
            except Exception:
                pass  # Client disconnected

        await irc_pool.subscribe(channel, subscriber_id, on_irc_message)

        # Announce join + persist
        await irc_pool.send_message(
            channel,
            f"<mobile:{nick}> joined the chat",
        )
        asyncio.create_task(
            log_svc.log_message(
                task_id, nick, "joined the chat", source="mobile", msg_type="join"
            )
        )

        # ---- Message loop ----
        while True:
            raw = await websocket.receive_json()
            try:
                msg_in = ChatMessageIn.model_validate(raw)
            except Exception:
                err = ChatError(code="invalid_message", text="Invalid message format")
                await websocket.send_json(err.model_dump(mode="json"))
                continue

            # Rate limit check
            rate_err = _rate_limiter.check(user_key, task_id)
            if rate_err:
                err = ChatError(code="rate_limited", text=rate_err)
                await websocket.send_json(err.model_dump(mode="json"))
                continue

            # Guardrail: block action commands + NLP patterns
            result = _guardrail.check(msg_in.text)
            if not result.allowed:
                err = ChatError(code="action_blocked", text=result.reason)
                await websocket.send_json(err.model_dump(mode="json"))
                # Log blocked attempt for audit
                asyncio.create_task(
                    log_svc.log_message(
                        task_id,
                        nick,
                        f"[BLOCKED:{result.matched_pattern}] {msg_in.text}",
                        source="mobile",
                        msg_type="blocked_action",
                    )
                )
                continue

            # Forward to IRC
            irc_text = f"<mobile:{nick}> {msg_in.text}"
            await irc_pool.send_message(channel, irc_text)

            # Persist
            asyncio.create_task(
                log_svc.log_message(task_id, nick, msg_in.text, source="mobile")
            )

            # Echo back to sender (so they see their own message)
            echo = ChatMessageOut(
                type="message",
                nick=nick,
                text=msg_in.text,
                source="mobile",
                task_id=task_id,
            )
            await websocket.send_json(echo.model_dump(mode="json"))

    except WebSocketDisconnect:
        logger.debug(
            "Chat client disconnected: %s for task %s", subscriber_id[:8], task_id[:8]
        )
    except Exception:
        logger.exception("Chat relay error for task %s", task_id[:8])
    finally:
        # Log leave event
        asyncio.create_task(
            log_svc.log_message(
                task_id, nick, "left the chat", source="mobile", msg_type="leave"
            )
        )
        # Cleanup IRC
        if irc_pool:
            await irc_pool.unsubscribe(channel, subscriber_id)
            try:
                await irc_pool.send_message(
                    channel,
                    f"<mobile:{nick}> left the chat",
                )
            except Exception:
                pass
