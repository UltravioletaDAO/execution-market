"""
ChatRelay — WebSocket endpoint bridging mobile clients to IRC task channels.

Endpoint: ``/ws/chat/{task_id}``

Flow:
1. Client opens WebSocket with ``?token=JWT``
2. Server verifies JWT and extracts executor_id
3. Server verifies executor is assigned to the task
4. Server subscribes to ``#task-{task_id[:8]}`` on IRCPool
5. Messages flow bidirectionally until disconnect

Guardrails (Layer 1 — relay level):
- Action commands (/approve, /cancel, etc.) are blocked and return ChatError
- Max message length enforced by Pydantic model (2000 chars)
"""

import asyncio
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from .models import (
    ChatMessageIn,
    ChatMessageOut,
    ChatError,
    ChatHistory,
    is_blocked_action,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat"])


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


async def _load_history(task_id: str, limit: int = 50) -> list[ChatMessageOut]:
    """Load recent chat messages from the task_chat_log table."""
    try:
        import supabase_client as db

        client = db.get_supabase_client()
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


async def _persist_message(
    task_id: str,
    nick: str,
    text: str,
    source: str = "mobile",
    msg_type: str = "message",
) -> None:
    """Persist a chat message to task_chat_log (fire and forget)."""
    try:
        import supabase_client as db

        client = db.get_supabase_client()
        client.table("task_chat_log").insert(
            {
                "task_id": task_id,
                "nick": nick,
                "text": text,
                "source": source,
                "type": msg_type,
            }
        ).execute()
    except Exception as e:
        logger.debug("Could not persist chat message: %s", e)


@router.websocket("/ws/chat/{task_id}")
async def chat_websocket(
    websocket: WebSocket,
    task_id: str,
    token: str = Query(default=""),
):
    """WebSocket endpoint for per-task chat, bridged to IRC."""
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
    irc_pool = None

    try:
        # ---- Send history ----
        history_messages = await _load_history(task_id)
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

        # Announce join
        await irc_pool.send_message(
            channel,
            f"<mobile:{nick}> joined the chat",
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

            # Guardrail: block action commands
            blocked = is_blocked_action(msg_in.text)
            if blocked:
                err = ChatError(
                    code="action_blocked",
                    text=f"Action commands ({blocked}) are not allowed in chat. "
                    "Use the app or API to perform task actions.",
                )
                await websocket.send_json(err.model_dump(mode="json"))
                continue

            # Forward to IRC
            irc_text = f"<mobile:{nick}> {msg_in.text}"
            await irc_pool.send_message(channel, irc_text)

            # Persist
            asyncio.create_task(
                _persist_message(task_id, nick, msg_in.text, source="mobile")
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
        # Cleanup
        if irc_pool:
            await irc_pool.unsubscribe(channel, subscriber_id)
            try:
                await irc_pool.send_message(
                    channel,
                    f"<mobile:{nick}> left the chat",
                )
            except Exception:
                pass
