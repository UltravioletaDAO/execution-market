"""Webhooks resource — client.webhooks.create(), .list(), .verify_signature()."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, TYPE_CHECKING

from ..models import Webhook, WebhookList

if TYPE_CHECKING:
    from ..client import EMClient


class WebhooksResource:
    """Webhook CRUD and signature verification.

    Usage::

        wh = await client.webhooks.create(url="https://my.app/em-hook", events=["task.completed"])
        hooks = await client.webhooks.list()
        await client.webhooks.delete(wh.id)

        # Verify incoming webhook
        is_valid = client.webhooks.verify_signature(body, signature, timestamp, secret)
    """

    def __init__(self, client: EMClient) -> None:
        self._client = client

    async def create(
        self,
        url: str,
        events: list[str],
        *,
        description: str | None = None,
    ) -> Webhook:
        """Register a new webhook endpoint."""
        body: dict[str, Any] = {"url": url, "events": events}
        if description:
            body["description"] = description
        data = await self._client._request("POST", "/webhooks/", json=body)
        return Webhook.model_validate(data)

    async def list(self) -> WebhookList:
        """List all webhooks for the authenticated agent."""
        data = await self._client._request("GET", "/webhooks/")
        return WebhookList.model_validate(data)

    async def get(self, webhook_id: str) -> Webhook:
        """Get a single webhook by ID."""
        data = await self._client._request("GET", f"/webhooks/{webhook_id}")
        return Webhook.model_validate(data)

    async def update(
        self,
        webhook_id: str,
        *,
        url: str | None = None,
        events: list[str] | None = None,
        active: bool | None = None,
    ) -> Webhook:
        """Update a webhook."""
        body: dict[str, Any] = {}
        if url is not None:
            body["url"] = url
        if events is not None:
            body["events"] = events
        if active is not None:
            body["active"] = active
        data = await self._client._request("PUT", f"/webhooks/{webhook_id}", json=body)
        return Webhook.model_validate(data)

    async def delete(self, webhook_id: str) -> dict[str, Any]:
        """Delete a webhook."""
        return await self._client._request("DELETE", f"/webhooks/{webhook_id}")

    async def rotate_secret(self, webhook_id: str) -> dict[str, Any]:
        """Rotate the signing secret for a webhook."""
        return await self._client._request("POST", f"/webhooks/{webhook_id}/rotate-secret")

    async def test(self, webhook_id: str) -> dict[str, Any]:
        """Send a test ping to a webhook endpoint."""
        return await self._client._request("POST", f"/webhooks/{webhook_id}/test")

    @staticmethod
    def verify_signature(
        body: bytes,
        signature: str,
        timestamp: str,
        secret: str,
    ) -> bool:
        """Verify an incoming webhook's HMAC-SHA256 signature.

        Args:
            body: Raw request body bytes.
            signature: Value of X-EM-Signature header.
            timestamp: Value of X-EM-Timestamp header.
            secret: Webhook signing secret.

        Returns:
            True if the signature is valid.
        """
        expected = hmac.new(
            secret.encode(),
            f"{timestamp}.".encode() + body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
