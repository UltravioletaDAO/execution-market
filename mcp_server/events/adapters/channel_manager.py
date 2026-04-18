"""
Channel Lifecycle Manager — Dynamic per-task IRC channels via MeshRelay API.

Subscribes to Event Bus:
- task.assigned  → create #task-{short_id}, invite participants
- task.completed → close channel with summary
- task.cancelled → close channel with reason

MeshRelay provides: POST /api/v1/channels, POST /channels/{name}/invite,
DELETE /channels/{name}. This adapter orchestrates the lifecycle.
"""

import logging
from typing import Optional, Dict, Any

import httpx

from ..models import EMEvent
from ..bus import EventBus
from utils.pii import truncate_wallet

logger = logging.getLogger(__name__)

# Default config — overridden at init
DEFAULT_MESHRELAY_API = "https://irc.meshrelay.xyz/api/v1"
CHANNEL_PREFIX = "#task-"


class ChannelManager:
    """Manages per-task IRC channels via MeshRelay's channel API."""

    def __init__(
        self,
        bus: EventBus,
        meshrelay_api_url: str = DEFAULT_MESHRELAY_API,
        api_key: str = "",
        db_client: Any = None,
    ):
        self._bus = bus
        self._api_url = meshrelay_api_url.rstrip("/")
        self._api_key = api_key
        self._db = db_client
        self._subscription_ids: list[str] = []
        self._active_channels: dict[str, str] = {}  # task_id -> channel_name
        self._stats = {
            "channels_created": 0,
            "channels_closed": 0,
            "invites_sent": 0,
            "errors": 0,
        }

    def start(self) -> None:
        """Subscribe to lifecycle events."""
        mappings = [
            ("task.assigned", self._on_task_assigned),
            ("task.completed", self._on_task_closed),
            ("task.cancelled", self._on_task_closed),
            ("submission.approved", self._on_task_closed),
        ]
        for pattern, handler in mappings:
            sub_id = self._bus.subscribe(pattern=pattern, handler=handler)
            self._subscription_ids.append(sub_id)

        logger.info("ChannelManager started, subscribed to %d events", len(mappings))

    def stop(self) -> None:
        """Unsubscribe from all events."""
        for sub_id in self._subscription_ids:
            self._bus.unsubscribe(sub_id)
        self._subscription_ids.clear()
        logger.info("ChannelManager stopped")

    # -------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------

    async def _on_task_assigned(self, event: EMEvent) -> None:
        """Create task channel and invite participants."""
        task_id = event.task_id or event.payload.get("task_id", "")
        if not task_id:
            return

        task = event.payload
        channel_name = await self.create_task_channel(task_id, task)
        if channel_name:
            await self._invite_participants(channel_name, task)

    async def _on_task_closed(self, event: EMEvent) -> None:
        """Close task channel on completion/cancellation/approval."""
        task_id = event.task_id or event.payload.get("task_id", "")
        if not task_id:
            return

        reason_map = {
            "task.completed": "Task completed",
            "task.cancelled": event.payload.get("reason", "Task cancelled"),
            "submission.approved": "Submission approved — payment released",
        }
        reason = reason_map.get(event.event_type, "Task closed")
        await self.close_task_channel(task_id, reason)

    # -------------------------------------------------------------------
    # Channel operations
    # -------------------------------------------------------------------

    async def create_task_channel(
        self, task_id: str, task: Dict[str, Any]
    ) -> Optional[str]:
        """Create #task-{short_id} channel via MeshRelay API."""
        short_id = task_id[:8]
        channel_name = f"{CHANNEL_PREFIX}{short_id}"

        title = task.get("title", "Task")
        bounty = task.get("bounty_usd", task.get("bounty_usdc", 0))
        deadline_minutes = task.get("deadline_minutes", 60)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self._api_url}/channels",
                    json={
                        "name": channel_name,
                        "topic": f"{title} | ${bounty:.2f} USDC | /help for commands",
                        "mode": "+nt",
                        "auto_expire_minutes": deadline_minutes + 30,
                    },
                    headers=self._auth_headers(),
                )
                resp.raise_for_status()

            self._active_channels[task_id] = channel_name
            self._stats["channels_created"] += 1
            logger.info("Channel created: %s for task %s", channel_name, short_id)
            return channel_name

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                # Channel already exists — that's fine
                self._active_channels[task_id] = channel_name
                logger.info("Channel %s already exists", channel_name)
                return channel_name
            self._stats["errors"] += 1
            logger.error("Failed to create channel %s: %s", channel_name, e)
            return None
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("Failed to create channel %s: %s", channel_name, e)
            return None

    async def close_task_channel(self, task_id: str, reason: str = "") -> None:
        """Archive and close task channel."""
        channel_name = self._active_channels.pop(task_id, None)
        if not channel_name:
            channel_name = f"{CHANNEL_PREFIX}{task_id[:8]}"

        try:
            # Send closing message before removing
            await self._send_to_channel(
                channel_name,
                f"[CLOSED] {reason}. Channel will be archived.",
            )

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.delete(
                    f"{self._api_url}/channels/{channel_name.lstrip('#')}",
                    headers=self._auth_headers(),
                )
                # 404 = already gone, that's fine
                if resp.status_code not in (200, 204, 404):
                    resp.raise_for_status()

            self._stats["channels_closed"] += 1
            logger.info("Channel closed: %s (%s)", channel_name, reason)

        except Exception as e:
            self._stats["errors"] += 1
            logger.error("Failed to close channel %s: %s", channel_name, e)

    # -------------------------------------------------------------------
    # Participant management (Task 3.2)
    # -------------------------------------------------------------------

    async def _invite_participants(
        self, channel_name: str, task: Dict[str, Any]
    ) -> None:
        """Look up IRC nicks for publisher/worker and invite them to the channel."""
        publisher_wallet = task.get("agent_wallet", task.get("publisher_wallet", ""))
        worker_wallet = task.get("worker_wallet", task.get("executor_wallet", ""))

        nicks_invited = []

        for role, wallet in [
            ("Publisher", publisher_wallet),
            ("Worker", worker_wallet),
        ]:
            if not wallet:
                continue
            nick = await self._lookup_nick_by_wallet(wallet)
            if nick:
                await self._invite_to_channel(channel_name, nick)
                nicks_invited.append(f"{role}: {nick}")

        if nicks_invited:
            welcome = (
                f"Task assigned. {' | '.join(nicks_invited)}. "
                f"Discuss here. /help for commands."
            )
            await self._send_to_channel(channel_name, welcome)

    async def _lookup_nick_by_wallet(self, wallet: str) -> Optional[str]:
        """Look up IRC nick from irc_identities table."""
        if not self._db:
            try:
                import supabase_client

                self._db = supabase_client.client
            except Exception:
                return None

        try:
            result = (
                self._db.table("irc_identities")
                .select("irc_nick")
                .eq("wallet_address", wallet.lower())
                .execute()
            )
            if result.data:
                return result.data[0]["irc_nick"]
        except Exception as e:
            logger.debug(
                "Nick lookup failed for wallet %s: %s", truncate_wallet(wallet), e
            )

        return None

    async def _invite_to_channel(self, channel_name: str, nick: str) -> None:
        """Invite a user to a channel via MeshRelay API."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self._api_url}/channels/{channel_name.lstrip('#')}/invite",
                    json={"nick": nick},
                    headers=self._auth_headers(),
                )
                if resp.status_code in (200, 204):
                    self._stats["invites_sent"] += 1
                    logger.debug("Invited %s to %s", nick, channel_name)
        except Exception as e:
            logger.debug("Failed to invite %s to %s: %s", nick, channel_name, e)

    async def _send_to_channel(self, channel_name: str, message: str) -> None:
        """Send a message to a channel via MeshRelay API."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{self._api_url}/channels/{channel_name.lstrip('#')}/message",
                    json={"text": message},
                    headers=self._auth_headers(),
                )
        except Exception:
            pass  # Best-effort

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    def _auth_headers(self) -> dict:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    def get_channel_for_task(self, task_id: str) -> Optional[str]:
        """Get the channel name for a task, if active."""
        return self._active_channels.get(task_id)

    # -------------------------------------------------------------------
    # Chat history logging (Task 3.5)
    # -------------------------------------------------------------------

    async def log_chat_message(
        self,
        task_id: str,
        channel: str,
        nick: str,
        message: str,
        message_type: str = "text",
        wallet_address: str = "",
    ) -> None:
        """Log a task channel message for dispute evidence.

        Only messages from #task-{id} channels should be logged.
        NOT #bounties, NOT DMs, NOT public channels.
        """
        if not channel.startswith(CHANNEL_PREFIX):
            return  # Only log task channel messages

        db = self._db
        if not db:
            try:
                import supabase_client

                db = supabase_client.client
                self._db = db
            except Exception:
                return

        try:
            db.table("task_chat_log").insert(
                {
                    "task_id": task_id,
                    "channel": channel,
                    "nick": nick,
                    "wallet_address": wallet_address or None,
                    "message": message[:4000],  # Truncate to 4K
                    "message_type": message_type,
                }
            ).execute()
        except Exception as e:
            logger.debug("Failed to log chat message: %s", e)

    @property
    def active_channels(self) -> dict[str, str]:
        return dict(self._active_channels)

    @property
    def stats(self) -> dict:
        return dict(self._stats)
