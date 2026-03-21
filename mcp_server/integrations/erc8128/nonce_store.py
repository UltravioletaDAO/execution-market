"""
ERC-8128 Nonce Store — Single-use nonce management for replay protection.

Provides two implementations:
- DynamoDBNonceStore: Production store using DynamoDB conditional writes + TTL
- InMemoryNonceStore: Development/testing fallback

Nonce key format: erc8128:{chain_id}:{address}:{nonce_value}

DynamoDB table schema:
  PK: nonce_key (String)
  TTL: expires_at (Number, Unix timestamp)
  consumed_at: Number (when first seen)
"""

import asyncio
import logging
import os
import time
import secrets
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------

ERC8128_NONCE_TABLE = os.environ.get("ERC8128_NONCE_TABLE", "em-production-nonce-store")
ERC8128_NONCE_STORE_TYPE = os.environ.get("ERC8128_NONCE_STORE", "memory")

# Nonce generation defaults
NONCE_LENGTH = 24  # 24 bytes → 32 chars base64url
NONCE_DEFAULT_TTL = 300  # 5 minutes


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class NonceStore(ABC):
    """Abstract nonce store interface."""

    @abstractmethod
    async def consume(self, key: str, ttl_seconds: int) -> bool:
        """
        Atomically consume a nonce.

        Returns True if fresh (first use), False if already consumed (replay).
        """
        ...

    @abstractmethod
    async def generate(self) -> str:
        """Generate a fresh nonce value."""
        ...


# ---------------------------------------------------------------------------
# In-Memory Implementation (dev/testing)
# ---------------------------------------------------------------------------


class InMemoryNonceStore(NonceStore):
    """
    In-memory nonce store for development and testing.

    NOT suitable for production (no persistence, no distributed coordination).
    """

    def __init__(self) -> None:
        # key -> expires_at timestamp
        self._store: dict[str, float] = {}

    async def consume(self, key: str, ttl_seconds: int) -> bool:
        now = time.time()
        # Lazy eviction of expired entries
        self._store = {k: v for k, v in self._store.items() if v > now}

        if key in self._store:
            return False  # Replay attempt

        self._store[key] = now + ttl_seconds
        return True

    async def generate(self) -> str:
        return secrets.token_urlsafe(NONCE_LENGTH)

    def __len__(self) -> int:
        """Number of active (non-expired) nonces."""
        now = time.time()
        return sum(1 for v in self._store.values() if v > now)

    def clear(self) -> None:
        """Clear all stored nonces."""
        self._store.clear()


# ---------------------------------------------------------------------------
# DynamoDB Implementation (production)
# ---------------------------------------------------------------------------


class DynamoDBNonceStore(NonceStore):
    """
    DynamoDB-backed nonce store with atomic conditional writes and TTL.

    Uses ConditionExpression to prevent race conditions — two concurrent
    requests with the same nonce will have exactly one succeed.

    DynamoDB TTL handles automatic cleanup (no cron needed).
    """

    def __init__(
        self,
        table_name: Optional[str] = None,
        region: Optional[str] = None,
    ) -> None:
        self._table_name = table_name or ERC8128_NONCE_TABLE
        self._region = region or os.environ.get("AWS_REGION", "us-east-2")
        self._table = None

    def _get_table(self):
        """Lazy-initialize DynamoDB table resource."""
        if self._table is None:
            import boto3

            dynamodb = boto3.resource("dynamodb", region_name=self._region)
            self._table = dynamodb.Table(self._table_name)
        return self._table

    def _sync_put_item(self, key: str, ttl_seconds: int) -> bool:
        """Synchronous DynamoDB put_item — called via asyncio.to_thread()."""
        from botocore.exceptions import ClientError

        table = self._get_table()
        now = int(time.time())

        try:
            table.put_item(
                Item={
                    "nonce_key": key,
                    "expires_at": now + ttl_seconds,
                    "consumed_at": now,
                },
                ConditionExpression="attribute_not_exists(nonce_key)",
            )
            return True  # Fresh nonce

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.warning("Nonce replay attempt: %s", key)
                return False
            logger.error("DynamoDB nonce store error: %s", e)
            raise

    async def consume(self, key: str, ttl_seconds: int) -> bool:
        """
        Atomically consume a nonce using DynamoDB conditional PutItem.

        Returns True if fresh (first use), False if replay attempt.
        Runs the synchronous boto3 call in a thread to avoid blocking
        the async event loop.
        """
        try:
            return await asyncio.to_thread(self._sync_put_item, key, ttl_seconds)
        except ImportError:
            logger.error(
                "boto3/botocore not available — cannot use DynamoDB nonce store"
            )
            raise

    async def generate(self) -> str:
        return secrets.token_urlsafe(NONCE_LENGTH)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_nonce_store: Optional[NonceStore] = None


def get_nonce_store() -> NonceStore:
    """
    Get or create the global nonce store.

    Uses ERC8128_NONCE_STORE env var:
      - "dynamodb" → DynamoDBNonceStore
      - "memory"   → InMemoryNonceStore (default)
    """
    global _nonce_store
    if _nonce_store is not None:
        return _nonce_store

    store_type = ERC8128_NONCE_STORE_TYPE.lower()

    if store_type == "dynamodb":
        logger.info("Initializing DynamoDB nonce store: table=%s", ERC8128_NONCE_TABLE)
        _nonce_store = DynamoDBNonceStore()
    else:
        logger.info("Initializing in-memory nonce store (dev mode)")
        _nonce_store = InMemoryNonceStore()

    return _nonce_store


def reset_nonce_store() -> None:
    """Reset the global nonce store (for testing)."""
    global _nonce_store
    _nonce_store = None
