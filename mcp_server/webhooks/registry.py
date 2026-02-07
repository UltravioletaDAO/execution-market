"""
Webhook Registry (NOW-087)

Manages webhook endpoint registration, storage, and retrieval.
Supports filtering webhooks by event type and owner.
"""

import secrets
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Set
from enum import Enum
import uuid

from .events import WebhookEventType


logger = logging.getLogger(__name__)


class WebhookStatus(str, Enum):
    """Status of a registered webhook."""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    FAILED = "failed"  # Too many failures, auto-disabled


@dataclass
class WebhookEndpoint:
    """
    A registered webhook endpoint.

    Attributes:
        webhook_id: Unique identifier
        owner_id: Agent or entity that owns this webhook
        url: HTTPS endpoint URL
        secret: HMAC signing secret (stored hashed, original returned on creation)
        events: Set of event types to receive
        description: Human-readable description
        status: Current status
        metadata: Additional metadata
        created_at: Creation timestamp
        updated_at: Last update timestamp
        last_triggered_at: Last successful delivery
        failure_count: Consecutive failures (resets on success)
        total_deliveries: Total delivery attempts
        successful_deliveries: Successful deliveries
    """

    webhook_id: str
    owner_id: str
    url: str
    secret_hash: str  # Hashed secret for storage
    events: Set[WebhookEventType]
    description: str = ""
    status: WebhookStatus = WebhookStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_triggered_at: Optional[str] = None
    failure_count: int = 0
    total_deliveries: int = 0
    successful_deliveries: int = 0

    def to_dict(self, include_secret: bool = False) -> Dict[str, Any]:
        """Convert to dictionary, optionally excluding secret."""
        data = {
            "webhook_id": self.webhook_id,
            "owner_id": self.owner_id,
            "url": self.url,
            "events": [e.value for e in self.events],
            "description": self.description,
            "status": self.status.value,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_triggered_at": self.last_triggered_at,
            "failure_count": self.failure_count,
            "total_deliveries": self.total_deliveries,
            "successful_deliveries": self.successful_deliveries,
        }
        if include_secret:
            data["secret_hash"] = self.secret_hash
        return data

    @property
    def success_rate(self) -> float:
        """Calculate delivery success rate."""
        if self.total_deliveries == 0:
            return 1.0
        return self.successful_deliveries / self.total_deliveries

    def is_subscribed_to(self, event_type: WebhookEventType) -> bool:
        """Check if webhook is subscribed to an event type."""
        return event_type in self.events


@dataclass
class WebhookRegistration:
    """Result of webhook registration with the plain secret."""

    webhook: WebhookEndpoint
    secret: str  # Plain secret, only available at registration time


class WebhookRegistry:
    """
    In-memory webhook registry with Supabase persistence.

    For production, this should be backed by a database.
    The in-memory cache provides fast lookups.
    """

    # Max consecutive failures before auto-disable
    MAX_FAILURE_COUNT = 10

    # Secret length in bytes (32 bytes = 256 bits)
    SECRET_LENGTH = 32

    def __init__(self, supabase_client=None):
        """
        Initialize registry.

        Args:
            supabase_client: Optional Supabase client for persistence
        """
        self._webhooks: Dict[str, WebhookEndpoint] = {}
        self._secrets: Dict[
            str, str
        ] = {}  # webhook_id -> plain secret (in-memory only)
        self._by_owner: Dict[str, Set[str]] = {}  # owner_id -> set of webhook_ids
        self._by_event: Dict[
            WebhookEventType, Set[str]
        ] = {}  # event -> set of webhook_ids
        self._supabase = supabase_client

    def _generate_secret(self) -> tuple[str, str]:
        """Generate a new webhook secret and its hash."""
        secret = secrets.token_urlsafe(self.SECRET_LENGTH)
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()
        return secret, secret_hash

    def _hash_secret(self, secret: str) -> str:
        """Hash a secret for comparison."""
        return hashlib.sha256(secret.encode()).hexdigest()

    def _validate_url(self, url: str) -> None:
        """Validate webhook URL."""
        if not url:
            raise ValueError("URL is required")
        if not url.startswith("https://"):
            raise ValueError("Webhook URL must use HTTPS")
        # Additional validation could be added here

    def register(
        self,
        owner_id: str,
        url: str,
        events: List[WebhookEventType],
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WebhookRegistration:
        """
        Register a new webhook endpoint.

        Args:
            owner_id: ID of the agent/entity registering the webhook
            url: HTTPS endpoint URL
            events: List of event types to subscribe to
            description: Human-readable description
            metadata: Additional metadata

        Returns:
            WebhookRegistration with webhook details and plain secret

        Raises:
            ValueError: If validation fails
        """
        self._validate_url(url)

        if not events:
            raise ValueError("At least one event type is required")

        # Check for duplicate URL for same owner
        existing = self.get_by_owner(owner_id)
        for webhook in existing:
            if webhook.url == url:
                raise ValueError(f"Webhook already registered for URL: {url}")

        # Generate IDs and secret
        webhook_id = str(uuid.uuid4())
        secret, secret_hash = self._generate_secret()

        # Create webhook
        webhook = WebhookEndpoint(
            webhook_id=webhook_id,
            owner_id=owner_id,
            url=url,
            secret_hash=secret_hash,
            events=set(events),
            description=description,
            metadata=metadata or {},
        )

        # Store in memory
        self._webhooks[webhook_id] = webhook
        self._secrets[webhook_id] = secret

        # Update indexes
        if owner_id not in self._by_owner:
            self._by_owner[owner_id] = set()
        self._by_owner[owner_id].add(webhook_id)

        for event in events:
            if event not in self._by_event:
                self._by_event[event] = set()
            self._by_event[event].add(webhook_id)

        # Persist to Supabase if available
        self._persist_webhook(webhook)

        logger.info(f"Registered webhook {webhook_id} for owner {owner_id}")

        return WebhookRegistration(webhook=webhook, secret=secret)

    def get(self, webhook_id: str) -> Optional[WebhookEndpoint]:
        """Get webhook by ID."""
        return self._webhooks.get(webhook_id)

    def get_secret(self, webhook_id: str) -> Optional[str]:
        """
        Get plain secret for webhook (for signing outgoing requests).

        Note: This is only available for webhooks registered in this session.
        For persistence, secrets should be stored encrypted in the database.
        """
        return self._secrets.get(webhook_id)

    def get_by_owner(self, owner_id: str) -> List[WebhookEndpoint]:
        """Get all webhooks for an owner."""
        webhook_ids = self._by_owner.get(owner_id, set())
        return [
            self._webhooks[wh_id] for wh_id in webhook_ids if wh_id in self._webhooks
        ]

    def get_by_event(self, event_type: WebhookEventType) -> List[WebhookEndpoint]:
        """Get all active webhooks subscribed to an event type."""
        webhook_ids = self._by_event.get(event_type, set())
        return [
            self._webhooks[wh_id]
            for wh_id in webhook_ids
            if wh_id in self._webhooks
            and self._webhooks[wh_id].status == WebhookStatus.ACTIVE
        ]

    def update(
        self,
        webhook_id: str,
        owner_id: str,
        url: Optional[str] = None,
        events: Optional[List[WebhookEventType]] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: Optional[WebhookStatus] = None,
    ) -> Optional[WebhookEndpoint]:
        """
        Update a webhook endpoint.

        Args:
            webhook_id: ID of webhook to update
            owner_id: Owner ID (for authorization)
            url: New URL (optional)
            events: New event list (optional)
            description: New description (optional)
            metadata: New metadata (optional)
            status: New status (optional)

        Returns:
            Updated webhook or None if not found/unauthorized

        Raises:
            ValueError: If validation fails
        """
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return None

        if webhook.owner_id != owner_id:
            raise ValueError("Not authorized to update this webhook")

        # Update URL
        if url is not None:
            self._validate_url(url)
            webhook.url = url

        # Update events
        if events is not None:
            if not events:
                raise ValueError("At least one event type is required")

            # Remove from old event indexes
            for event in webhook.events:
                if event in self._by_event:
                    self._by_event[event].discard(webhook_id)

            # Update events
            webhook.events = set(events)

            # Add to new event indexes
            for event in events:
                if event not in self._by_event:
                    self._by_event[event] = set()
                self._by_event[event].add(webhook_id)

        # Update other fields
        if description is not None:
            webhook.description = description
        if metadata is not None:
            webhook.metadata = metadata
        if status is not None:
            webhook.status = status

        webhook.updated_at = datetime.now(timezone.utc).isoformat()

        # Persist update
        self._persist_webhook(webhook)

        logger.info(f"Updated webhook {webhook_id}")

        return webhook

    def delete(self, webhook_id: str, owner_id: str) -> bool:
        """
        Delete a webhook endpoint.

        Args:
            webhook_id: ID of webhook to delete
            owner_id: Owner ID (for authorization)

        Returns:
            True if deleted, False if not found/unauthorized
        """
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return False

        if webhook.owner_id != owner_id:
            return False

        # Remove from indexes
        if webhook.owner_id in self._by_owner:
            self._by_owner[webhook.owner_id].discard(webhook_id)

        for event in webhook.events:
            if event in self._by_event:
                self._by_event[event].discard(webhook_id)

        # Remove from storage
        del self._webhooks[webhook_id]
        self._secrets.pop(webhook_id, None)

        # Delete from Supabase
        self._delete_webhook(webhook_id)

        logger.info(f"Deleted webhook {webhook_id}")

        return True

    def rotate_secret(self, webhook_id: str, owner_id: str) -> Optional[str]:
        """
        Rotate webhook secret.

        Args:
            webhook_id: ID of webhook
            owner_id: Owner ID (for authorization)

        Returns:
            New plain secret or None if not found/unauthorized
        """
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return None

        if webhook.owner_id != owner_id:
            return None

        # Generate new secret
        secret, secret_hash = self._generate_secret()

        # Update webhook
        webhook.secret_hash = secret_hash
        webhook.updated_at = datetime.now(timezone.utc).isoformat()
        self._secrets[webhook_id] = secret

        # Persist update
        self._persist_webhook(webhook)

        logger.info(f"Rotated secret for webhook {webhook_id}")

        return secret

    def record_delivery(
        self,
        webhook_id: str,
        success: bool,
    ) -> None:
        """
        Record a delivery attempt for metrics and auto-disable.

        Args:
            webhook_id: ID of webhook
            success: Whether delivery was successful
        """
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return

        webhook.total_deliveries += 1

        if success:
            webhook.successful_deliveries += 1
            webhook.failure_count = 0
            webhook.last_triggered_at = datetime.now(timezone.utc).isoformat()
        else:
            webhook.failure_count += 1

            # Auto-disable after too many failures
            if webhook.failure_count >= self.MAX_FAILURE_COUNT:
                webhook.status = WebhookStatus.FAILED
                logger.warning(
                    f"Auto-disabled webhook {webhook_id} after {webhook.failure_count} failures"
                )

        webhook.updated_at = datetime.now(timezone.utc).isoformat()

        # Persist update
        self._persist_webhook(webhook)

    def pause(self, webhook_id: str, owner_id: str) -> bool:
        """Pause a webhook (stop receiving events)."""
        return (
            self.update(webhook_id, owner_id, status=WebhookStatus.PAUSED) is not None
        )

    def resume(self, webhook_id: str, owner_id: str) -> bool:
        """Resume a paused webhook."""
        webhook = self._webhooks.get(webhook_id)
        if not webhook or webhook.owner_id != owner_id:
            return False

        if webhook.status == WebhookStatus.PAUSED:
            return (
                self.update(webhook_id, owner_id, status=WebhookStatus.ACTIVE)
                is not None
            )

        return False

    def list_all(self, limit: int = 100, offset: int = 0) -> List[WebhookEndpoint]:
        """List all webhooks (admin function)."""
        all_webhooks = list(self._webhooks.values())
        return all_webhooks[offset : offset + limit]

    def _persist_webhook(self, webhook: WebhookEndpoint) -> None:
        """Persist webhook to Supabase."""
        if not self._supabase:
            return

        try:
            data = webhook.to_dict(include_secret=True)
            data["events"] = [e.value for e in webhook.events]

            self._supabase.table("webhooks").upsert(data).execute()
        except Exception as e:
            logger.error(f"Failed to persist webhook {webhook.webhook_id}: {e}")

    def _delete_webhook(self, webhook_id: str) -> None:
        """Delete webhook from Supabase."""
        if not self._supabase:
            return

        try:
            self._supabase.table("webhooks").delete().eq(
                "webhook_id", webhook_id
            ).execute()
        except Exception as e:
            logger.error(f"Failed to delete webhook {webhook_id}: {e}")

    def load_from_database(self) -> int:
        """
        Load webhooks from Supabase into memory.

        Returns:
            Number of webhooks loaded
        """
        if not self._supabase:
            return 0

        try:
            result = self._supabase.table("webhooks").select("*").execute()
            count = 0

            for row in result.data:
                webhook = WebhookEndpoint(
                    webhook_id=row["webhook_id"],
                    owner_id=row["owner_id"],
                    url=row["url"],
                    secret_hash=row["secret_hash"],
                    events={WebhookEventType(e) for e in row["events"]},
                    description=row.get("description", ""),
                    status=WebhookStatus(row.get("status", "active")),
                    metadata=row.get("metadata", {}),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    last_triggered_at=row.get("last_triggered_at"),
                    failure_count=row.get("failure_count", 0),
                    total_deliveries=row.get("total_deliveries", 0),
                    successful_deliveries=row.get("successful_deliveries", 0),
                )

                self._webhooks[webhook.webhook_id] = webhook

                # Update indexes
                if webhook.owner_id not in self._by_owner:
                    self._by_owner[webhook.owner_id] = set()
                self._by_owner[webhook.owner_id].add(webhook.webhook_id)

                for event in webhook.events:
                    if event not in self._by_event:
                        self._by_event[event] = set()
                    self._by_event[event].add(webhook.webhook_id)

                count += 1

            logger.info(f"Loaded {count} webhooks from database")
            return count

        except Exception as e:
            logger.error(f"Failed to load webhooks from database: {e}")
            return 0


# Singleton instance
_default_registry: Optional[WebhookRegistry] = None


def get_webhook_registry(supabase_client=None) -> WebhookRegistry:
    """Get or create the global webhook registry instance."""
    global _default_registry
    if _default_registry is None:
        _default_registry = WebhookRegistry(supabase_client)
    return _default_registry
