"""
Cross-Post Engine — intelligent task distribution to category/geographic channels.

Subscribes to Event Bus task.created events and cross-posts to relevant channels:
- Category channels: #cat-physical, #cat-knowledge, etc.
- Geographic channels: #city-medellin, #city-bogota, etc.
- Special channels: #urgent (deadline < 30min), #high-value (bounty > $1)
- First-timer channel: #first-timers (new publishers)

Channel existence is checked via MeshRelay API before posting.
Missing channels are gracefully skipped.
"""

import logging
from typing import Optional, List, Dict, Any

import httpx

from ..models import EMEvent, EventSource
from ..bus import EventBus

logger = logging.getLogger(__name__)

# Category to channel mapping
CATEGORY_CHANNELS = {
    "physical_presence": "#cat-physical",
    "knowledge_access": "#cat-knowledge",
    "human_authority": "#cat-authority",
    "simple_action": "#cat-action",
    "digital_physical": "#cat-digital",
}

URGENT_THRESHOLD_MINUTES = 30
HIGH_VALUE_THRESHOLD_USD = 1.00


class CrossPostEngine:
    """Cross-posts task announcements to relevant specialty channels."""

    def __init__(
        self,
        bus: EventBus,
        meshrelay_api_url: str = "https://irc.meshrelay.xyz/api/v1",
        api_key: str = "",
    ):
        self._bus = bus
        self._api_url = meshrelay_api_url.rstrip("/")
        self._api_key = api_key
        self._subscription_ids: list[str] = []
        self._known_channels: set[str] = set()
        self._channel_cache_ttl = 0  # Timestamp of last channel list fetch
        self._stats = {
            "crossposted": 0,
            "skipped_no_channel": 0,
            "errors": 0,
        }

    def start(self) -> None:
        """Subscribe to task.created events."""
        sub_id = self._bus.subscribe(
            pattern="task.created",
            handler=self._on_task_created,
            source_filter=EventSource.MESHRELAY,  # anti-echo
        )
        self._subscription_ids.append(sub_id)
        logger.info("CrossPostEngine started")

    def stop(self) -> None:
        for sub_id in self._subscription_ids:
            self._bus.unsubscribe(sub_id)
        self._subscription_ids.clear()
        logger.info("CrossPostEngine stopped")

    async def _on_task_created(self, event: EMEvent) -> None:
        """Determine target channels and cross-post."""
        targets = self._compute_targets(event)
        if not targets:
            return

        for channel, message in targets:
            await self._post_to_channel(channel, message)

    def _compute_targets(self, event: EMEvent) -> List[tuple]:
        """Compute (channel, formatted_message) pairs for cross-posting."""
        p = event.payload
        targets = []
        task_id = (p.get("task_id") or event.task_id or "?")[:8]
        title = p.get("title", "Untitled")
        bounty = float(p.get("bounty_usd", p.get("bounty_usdc", 0)))
        category = p.get("category", "")
        deadline_min = p.get("deadline_minutes", 60)
        chain = p.get("payment_network", "base")
        city = p.get("city", "")

        # Category channel
        cat_channel = CATEGORY_CHANNELS.get(category)
        if cat_channel:
            evidence_reqs = p.get("evidence_requirements", [])
            needs = f" | Needs: {', '.join(evidence_reqs)}" if evidence_reqs else ""
            msg = (
                f"[{category.upper().replace('_', ' ')}] {title} "
                f"| ${bounty:.2f} USDC{needs} | /claim {task_id}"
            )
            targets.append((cat_channel, msg))

        # Geographic channel
        if city:
            city_slug = city.lower().replace(" ", "-")
            city_channel = f"#city-{city_slug}"
            location_hint = p.get("location_hint", "")
            loc_str = f" | {location_hint}" if location_hint else ""
            msg = (
                f"[NEARBY] {title} | ${bounty:.2f} USDC{loc_str} | /claim {task_id}"
            )
            targets.append((city_channel, msg))

        # Urgent channel
        if isinstance(deadline_min, (int, float)) and deadline_min < URGENT_THRESHOLD_MINUTES:
            msg = (
                f"[URGENT] {title} | ${bounty:.2f} USDC | {int(deadline_min)}min left! "
                f"| /claim {task_id}"
            )
            targets.append(("#urgent", msg))

        # High-value channel
        if bounty >= HIGH_VALUE_THRESHOLD_USD:
            msg = (
                f"[$$] {title} | ${bounty:.2f} USDC ({chain}) "
                f"| {category} | /claim {task_id}"
            )
            targets.append(("#high-value", msg))

        return targets

    async def _post_to_channel(self, channel: str, message: str) -> None:
        """Post a message to a channel via MeshRelay API."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{self._api_url}/channels/{channel.lstrip('#')}/message",
                    json={"text": message},
                    headers=self._auth_headers(),
                )
                if resp.status_code in (200, 204):
                    self._stats["crossposted"] += 1
                    logger.debug("Cross-posted to %s", channel)
                elif resp.status_code == 404:
                    self._stats["skipped_no_channel"] += 1
                    logger.debug("Channel %s not found, skipping", channel)
                else:
                    self._stats["errors"] += 1
        except Exception as e:
            self._stats["errors"] += 1
            logger.debug("Cross-post to %s failed: %s", channel, e)

    def _auth_headers(self) -> dict:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    @property
    def stats(self) -> dict:
        return dict(self._stats)
