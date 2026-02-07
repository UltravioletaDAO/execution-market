"""
Webhook Sender with Retry Logic (NOW-087)

Handles reliable delivery of webhook events with:
- HMAC-SHA256 signature verification
- Exponential backoff retry logic
- Configurable timeout and max retries
- Dead letter queue for failed deliveries
"""

import asyncio
import hashlib
import hmac
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
import uuid

import aiohttp

from .events import WebhookEvent


logger = logging.getLogger(__name__)


class DeliveryStatus(str, Enum):
    """Status of a webhook delivery attempt."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


@dataclass
class DeliveryAttempt:
    """Record of a single delivery attempt."""

    attempt_number: int
    timestamp: str
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    latency_ms: Optional[int] = None


@dataclass
class DeliveryResult:
    """Result of webhook delivery (possibly after retries)."""

    delivery_id: str
    webhook_id: str
    endpoint_url: str
    event_type: str
    status: DeliveryStatus
    attempts: List[DeliveryAttempt] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None
    next_retry_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "delivery_id": self.delivery_id,
            "webhook_id": self.webhook_id,
            "endpoint_url": self.endpoint_url,
            "event_type": self.event_type,
            "status": self.status.value,
            "attempts": [
                {
                    "attempt": a.attempt_number,
                    "timestamp": a.timestamp,
                    "status_code": a.status_code,
                    "error": a.error,
                    "latency_ms": a.latency_ms,
                }
                for a in self.attempts
            ],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "next_retry_at": self.next_retry_at,
        }


@dataclass
class WebhookConfig:
    """Configuration for webhook delivery."""

    # Retry settings
    max_retries: int = 5
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 300.0  # 5 minutes
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1  # Add up to 10% random jitter

    # Request settings
    timeout_seconds: float = 30.0
    max_response_size: int = 1024 * 10  # 10KB

    # Validation settings
    require_2xx_response: bool = True
    allowed_status_codes: List[int] = field(
        default_factory=lambda: [200, 201, 202, 204]
    )

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given retry attempt with exponential backoff."""
        delay = min(
            self.initial_delay_seconds * (self.backoff_multiplier**attempt),
            self.max_delay_seconds,
        )
        # Add jitter
        import random

        jitter = delay * self.jitter_factor * random.random()
        return delay + jitter


class WebhookSignature:
    """
    HMAC-SHA256 signature generation and verification.

    Signature format: t=<timestamp>,v1=<signature>
    """

    SIGNATURE_VERSION = "v1"
    TIMESTAMP_TOLERANCE_SECONDS = 300  # 5 minutes

    @staticmethod
    def generate(payload: str, secret: str, timestamp: Optional[int] = None) -> str:
        """
        Generate HMAC-SHA256 signature for payload.

        Args:
            payload: JSON string payload
            secret: Webhook secret key
            timestamp: Unix timestamp (defaults to now)

        Returns:
            Signature header value: t=<timestamp>,v1=<signature>
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Create signed payload: timestamp.payload
        signed_payload = f"{timestamp}.{payload}"

        # Generate HMAC-SHA256
        signature = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return f"t={timestamp},{WebhookSignature.SIGNATURE_VERSION}={signature}"

    @staticmethod
    def verify(
        payload: str,
        signature_header: str,
        secret: str,
        tolerance_seconds: Optional[int] = None,
    ) -> bool:
        """
        Verify HMAC-SHA256 signature.

        Args:
            payload: JSON string payload
            signature_header: Signature header value
            secret: Webhook secret key
            tolerance_seconds: Max age of signature (default: 5 minutes)

        Returns:
            True if signature is valid

        Raises:
            ValueError: If signature format is invalid or timestamp is too old
        """
        if tolerance_seconds is None:
            tolerance_seconds = WebhookSignature.TIMESTAMP_TOLERANCE_SECONDS

        # Parse signature header
        parts = {}
        for part in signature_header.split(","):
            if "=" in part:
                key, value = part.split("=", 1)
                parts[key] = value

        if "t" not in parts or WebhookSignature.SIGNATURE_VERSION not in parts:
            raise ValueError("Invalid signature format")

        timestamp = int(parts["t"])
        signature = parts[WebhookSignature.SIGNATURE_VERSION]

        # Check timestamp freshness
        current_time = int(time.time())
        if abs(current_time - timestamp) > tolerance_seconds:
            raise ValueError(
                f"Signature timestamp too old: {current_time - timestamp}s"
            )

        # Verify signature
        expected_payload = f"{timestamp}.{payload}"
        expected_signature = hmac.new(
            secret.encode("utf-8"),
            expected_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)


class WebhookSender:
    """
    Async webhook sender with retry logic and signature verification.
    """

    def __init__(
        self,
        config: Optional[WebhookConfig] = None,
        dead_letter_callback: Optional[
            Callable[[DeliveryResult, WebhookEvent], None]
        ] = None,
    ):
        """
        Initialize webhook sender.

        Args:
            config: Webhook delivery configuration
            dead_letter_callback: Called when delivery fails after all retries
        """
        self.config = config or WebhookConfig()
        self.dead_letter_callback = dead_letter_callback
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _build_headers(
        self,
        event: WebhookEvent,
        signature: str,
        webhook_id: str,
    ) -> Dict[str, str]:
        """Build HTTP headers for webhook request."""
        return {
            "Content-Type": "application/json",
            "User-Agent": "ExecutionMarket-Webhook/1.0",
            "X-Webhook-Id": webhook_id,
            "X-Webhook-Event": event.event_type.value,
            "X-Webhook-Signature": signature,
            "X-Webhook-Timestamp": str(int(time.time())),
            "X-Idempotency-Key": event.metadata.idempotency_key,
        }

    async def _send_request(
        self,
        url: str,
        payload: str,
        headers: Dict[str, str],
    ) -> tuple[Optional[int], Optional[str], Optional[str], int]:
        """
        Send HTTP POST request.

        Returns:
            (status_code, response_body, error, latency_ms)
        """
        session = await self._get_session()
        start_time = time.monotonic()

        try:
            async with session.post(url, data=payload, headers=headers) as response:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                body = await response.text()

                # Truncate response if too large
                if len(body) > self.config.max_response_size:
                    body = body[: self.config.max_response_size] + "... (truncated)"

                return response.status, body, None, latency_ms

        except asyncio.TimeoutError:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            return None, None, "Request timeout", latency_ms

        except aiohttp.ClientError as e:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            return None, None, f"Connection error: {str(e)}", latency_ms

        except Exception as e:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            return None, None, f"Unexpected error: {str(e)}", latency_ms

    def _is_success(self, status_code: Optional[int]) -> bool:
        """Check if status code indicates success."""
        if status_code is None:
            return False
        if self.config.require_2xx_response:
            return status_code in self.config.allowed_status_codes
        return 200 <= status_code < 300

    async def send(
        self,
        url: str,
        event: WebhookEvent,
        secret: str,
        webhook_id: str,
        retry: bool = True,
    ) -> DeliveryResult:
        """
        Send webhook event to URL with retry logic.

        Args:
            url: Webhook endpoint URL
            event: Event to send
            secret: Signing secret for HMAC
            webhook_id: ID of the registered webhook
            retry: Whether to retry on failure

        Returns:
            DeliveryResult with all attempt details
        """
        delivery_id = str(uuid.uuid4())
        payload = event.to_json()
        timestamp = int(time.time())
        signature = WebhookSignature.generate(payload, secret, timestamp)
        headers = self._build_headers(event, signature, webhook_id)

        result = DeliveryResult(
            delivery_id=delivery_id,
            webhook_id=webhook_id,
            endpoint_url=url,
            event_type=event.event_type.value,
            status=DeliveryStatus.PENDING,
        )

        max_attempts = self.config.max_retries + 1 if retry else 1

        for attempt in range(max_attempts):
            if attempt > 0:
                # Wait before retry
                delay = self.config.calculate_delay(attempt - 1)
                result.status = DeliveryStatus.RETRYING
                result.next_retry_at = datetime.now(timezone.utc).isoformat()
                logger.info(
                    f"Webhook delivery {delivery_id} retry {attempt}/{self.config.max_retries} "
                    f"in {delay:.1f}s"
                )
                await asyncio.sleep(delay)

            # Send request
            status_code, response_body, error, latency_ms = await self._send_request(
                url, payload, headers
            )

            attempt_record = DeliveryAttempt(
                attempt_number=attempt + 1,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status_code=status_code,
                response_body=response_body[:500] if response_body else None,
                error=error,
                latency_ms=latency_ms,
            )
            result.attempts.append(attempt_record)

            if self._is_success(status_code):
                result.status = DeliveryStatus.DELIVERED
                result.completed_at = datetime.now(timezone.utc).isoformat()
                result.next_retry_at = None
                logger.info(
                    f"Webhook delivery {delivery_id} succeeded on attempt {attempt + 1}"
                )
                return result

            # Log failure
            logger.warning(
                f"Webhook delivery {delivery_id} attempt {attempt + 1} failed: "
                f"status={status_code}, error={error}"
            )

        # All retries exhausted
        result.status = DeliveryStatus.DEAD_LETTER
        result.completed_at = datetime.now(timezone.utc).isoformat()
        result.next_retry_at = None

        logger.error(
            f"Webhook delivery {delivery_id} failed after {max_attempts} attempts, "
            f"moving to dead letter queue"
        )

        # Call dead letter callback if registered
        if self.dead_letter_callback:
            try:
                self.dead_letter_callback(result, event)
            except Exception as e:
                logger.error(f"Dead letter callback error: {e}")

        return result

    async def send_batch(
        self,
        deliveries: List[tuple[str, WebhookEvent, str, str]],
        concurrency: int = 5,
    ) -> List[DeliveryResult]:
        """
        Send multiple webhooks concurrently.

        Args:
            deliveries: List of (url, event, secret, webhook_id) tuples
            concurrency: Max concurrent requests

        Returns:
            List of DeliveryResults
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def send_with_semaphore(
            url: str, event: WebhookEvent, secret: str, webhook_id: str
        ) -> DeliveryResult:
            async with semaphore:
                return await self.send(url, event, secret, webhook_id)

        tasks = [
            send_with_semaphore(url, event, secret, wh_id)
            for url, event, secret, wh_id in deliveries
        ]

        return await asyncio.gather(*tasks)


# Singleton instance for global use
_default_sender: Optional[WebhookSender] = None


def get_webhook_sender(
    config: Optional[WebhookConfig] = None,
    dead_letter_callback: Optional[Callable] = None,
) -> WebhookSender:
    """Get or create the global webhook sender instance."""
    global _default_sender
    if _default_sender is None:
        _default_sender = WebhookSender(config, dead_letter_callback)
    return _default_sender


async def send_webhook(
    url: str,
    event: WebhookEvent,
    secret: str,
    webhook_id: str,
    retry: bool = True,
) -> DeliveryResult:
    """
    Convenience function to send a webhook using the global sender.

    Args:
        url: Webhook endpoint URL
        event: Event to send
        secret: Signing secret
        webhook_id: Registered webhook ID
        retry: Whether to retry on failure

    Returns:
        DeliveryResult
    """
    sender = get_webhook_sender()
    return await sender.send(url, event, secret, webhook_id, retry)
