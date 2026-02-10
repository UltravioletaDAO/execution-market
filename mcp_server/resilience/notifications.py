"""
Push Notifications Integration (NOW-173)

Firebase Cloud Messaging (FCM) and OneSignal integration
for real-time worker notifications.

Key features:
- Multi-provider support (FCM, OneSignal)
- Priority-based delivery
- Batch notifications
- Delivery tracking
- Template-based messages
"""

import logging
import httpx
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationPriority(str, Enum):
    """Notification priority levels."""

    LOW = "low"  # Background updates
    NORMAL = "normal"  # Standard notifications
    HIGH = "high"  # Time-sensitive (timeout warnings)
    CRITICAL = "critical"  # Requires immediate attention


class NotificationType(str, Enum):
    """Types of notifications."""

    TASK_AVAILABLE = "task_available"
    TASK_ASSIGNED = "task_assigned"
    TASK_REMINDER = "task_reminder"
    TIMEOUT_WARNING = "timeout_warning"
    TIMEOUT_EXPIRED = "timeout_expired"
    SUBMISSION_RECEIVED = "submission_received"
    SUBMISSION_APPROVED = "submission_approved"
    SUBMISSION_REJECTED = "submission_rejected"
    PAYMENT_SENT = "payment_sent"
    DISPUTE_OPENED = "dispute_opened"
    GRACE_PERIOD_WARNING = "grace_period_warning"
    RECONNECTION_NEEDED = "reconnection_needed"


@dataclass
class NotificationPayload:
    """
    Push notification payload.

    Attributes:
        notification_id: Unique notification identifier
        notification_type: Type of notification
        recipient_id: Recipient worker/agent ID
        title: Notification title
        body: Notification body text
        priority: Delivery priority
        data: Additional data payload
        action_url: Deep link or action URL
        image_url: Optional image URL
        ttl_seconds: Time-to-live in seconds
        collapse_key: Key for collapsing similar notifications
        created_at: When notification was created
    """

    notification_id: str
    notification_type: NotificationType
    recipient_id: str
    title: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    data: Dict[str, Any] = field(default_factory=dict)
    action_url: Optional[str] = None
    image_url: Optional[str] = None
    ttl_seconds: int = 86400  # 24 hours
    collapse_key: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DeliveryResult:
    """Result of notification delivery."""

    notification_id: str
    provider: str
    success: bool
    provider_message_id: Optional[str] = None
    error: Optional[str] = None
    delivered_at: Optional[datetime] = None


class NotificationProvider(ABC):
    """
    Abstract base class for notification providers.

    Implement this to add new push notification services.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    async def send(
        self, device_token: str, payload: NotificationPayload
    ) -> DeliveryResult:
        """
        Send notification to a single device.

        Args:
            device_token: Device push token
            payload: Notification payload

        Returns:
            DeliveryResult
        """
        pass

    @abstractmethod
    async def send_batch(
        self, device_tokens: List[str], payload: NotificationPayload
    ) -> List[DeliveryResult]:
        """
        Send notification to multiple devices.

        Args:
            device_tokens: List of device tokens
            payload: Notification payload

        Returns:
            List of DeliveryResults
        """
        pass

    @abstractmethod
    async def validate_token(self, device_token: str) -> bool:
        """
        Validate a device token.

        Args:
            device_token: Device push token

        Returns:
            True if valid
        """
        pass


class FirebaseProvider(NotificationProvider):
    """
    Firebase Cloud Messaging (FCM) provider.

    Uses FCM HTTP v1 API for sending push notifications.
    """

    def __init__(
        self,
        project_id: str,
        service_account_key: Optional[Dict] = None,
        credentials_path: Optional[str] = None,
    ):
        """
        Initialize Firebase provider.

        Args:
            project_id: Firebase project ID
            service_account_key: Service account credentials dict
            credentials_path: Path to service account JSON file
        """
        self.project_id = project_id
        self._service_account_key = service_account_key
        self._credentials_path = credentials_path
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        return "firebase"

    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=30.0, headers={"Content-Type": "application/json"}
            )

    async def _get_access_token(self) -> str:
        """
        Get OAuth2 access token for FCM.

        In production, use google-auth library.
        This is a simplified placeholder.
        """
        # TODO: Implement proper OAuth2 token fetch using google-auth
        # For now, return placeholder
        if self._access_token and self._token_expires:
            if datetime.now(timezone.utc) < self._token_expires:
                return self._access_token

        logger.warning(
            "FCM access token generation not implemented. "
            "Use google-auth library in production."
        )
        return "placeholder_token"

    def _build_fcm_message(
        self, device_token: str, payload: NotificationPayload
    ) -> Dict:
        """Build FCM message format."""
        # Map priority
        android_priority = (
            "high"
            if payload.priority
            in (NotificationPriority.HIGH, NotificationPriority.CRITICAL)
            else "normal"
        )

        apns_priority = (
            "10"
            if payload.priority
            in (NotificationPriority.HIGH, NotificationPriority.CRITICAL)
            else "5"
        )

        message = {
            "message": {
                "token": device_token,
                "notification": {"title": payload.title, "body": payload.body},
                "data": {
                    "notification_id": payload.notification_id,
                    "notification_type": payload.notification_type.value,
                    "recipient_id": payload.recipient_id,
                    **{k: str(v) for k, v in payload.data.items()},
                },
                "android": {
                    "priority": android_priority,
                    "ttl": f"{payload.ttl_seconds}s",
                    "notification": {"click_action": "FLUTTER_NOTIFICATION_CLICK"},
                },
                "apns": {
                    "headers": {
                        "apns-priority": apns_priority,
                        "apns-expiration": str(
                            int(datetime.now(timezone.utc).timestamp()) + payload.ttl_seconds
                        ),
                    },
                    "payload": {
                        "aps": {
                            "alert": {"title": payload.title, "body": payload.body},
                            "sound": "default",
                        }
                    },
                },
            }
        }

        if payload.image_url:
            message["message"]["notification"]["image"] = payload.image_url

        if payload.collapse_key:
            message["message"]["android"]["collapse_key"] = payload.collapse_key
            message["message"]["apns"]["headers"]["apns-collapse-id"] = (
                payload.collapse_key
            )

        return message

    async def send(
        self, device_token: str, payload: NotificationPayload
    ) -> DeliveryResult:
        """Send notification via FCM."""
        await self._ensure_client()

        try:
            access_token = await self._get_access_token()
            message = self._build_fcm_message(device_token, payload)

            url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"

            response = await self._client.post(
                url, json=message, headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code == 200:
                result = response.json()
                return DeliveryResult(
                    notification_id=payload.notification_id,
                    provider=self.name,
                    success=True,
                    provider_message_id=result.get("name"),
                    delivered_at=datetime.now(timezone.utc),
                )
            else:
                error_data = response.json() if response.content else {}
                return DeliveryResult(
                    notification_id=payload.notification_id,
                    provider=self.name,
                    success=False,
                    error=f"FCM error {response.status_code}: {error_data}",
                )

        except Exception as e:
            logger.error(f"FCM send error: {e}")
            return DeliveryResult(
                notification_id=payload.notification_id,
                provider=self.name,
                success=False,
                error=str(e),
            )

    async def send_batch(
        self, device_tokens: List[str], payload: NotificationPayload
    ) -> List[DeliveryResult]:
        """Send notification to multiple devices via FCM."""
        # FCM HTTP v1 API doesn't support native batch, send individually
        # For high volume, consider using FCM topics or FCM batch API
        results = []
        for token in device_tokens:
            result = await self.send(token, payload)
            results.append(result)
        return results

    async def validate_token(self, device_token: str) -> bool:
        """Validate FCM token by sending a dry-run message."""
        # FCM validates tokens on send
        # Could implement dry_run=true parameter
        return len(device_token) > 100  # Basic length check


class OneSignalProvider(NotificationProvider):
    """
    OneSignal push notification provider.

    Uses OneSignal REST API for sending notifications.
    """

    def __init__(self, app_id: str, rest_api_key: str):
        """
        Initialize OneSignal provider.

        Args:
            app_id: OneSignal App ID
            rest_api_key: OneSignal REST API key
        """
        self.app_id = app_id
        self._rest_api_key = rest_api_key
        self._client: Optional[httpx.AsyncClient] = None
        self._base_url = "https://onesignal.com/api/v1"

    @property
    def name(self) -> str:
        return "onesignal"

    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {self._rest_api_key}",
                },
            )

    def _build_onesignal_message(
        self, player_ids: List[str], payload: NotificationPayload
    ) -> Dict:
        """Build OneSignal message format."""
        # Map priority to OneSignal priority (1-10)
        priority_map = {
            NotificationPriority.LOW: 1,
            NotificationPriority.NORMAL: 5,
            NotificationPriority.HIGH: 8,
            NotificationPriority.CRITICAL: 10,
        }

        message = {
            "app_id": self.app_id,
            "include_player_ids": player_ids,
            "headings": {"en": payload.title},
            "contents": {"en": payload.body},
            "data": {
                "notification_id": payload.notification_id,
                "notification_type": payload.notification_type.value,
                "recipient_id": payload.recipient_id,
                **payload.data,
            },
            "priority": priority_map.get(payload.priority, 5),
            "ttl": payload.ttl_seconds,
        }

        if payload.image_url:
            message["big_picture"] = payload.image_url
            message["ios_attachments"] = {"image": payload.image_url}

        if payload.action_url:
            message["url"] = payload.action_url

        if payload.collapse_key:
            message["collapse_id"] = payload.collapse_key
            message["android_group"] = payload.collapse_key

        return message

    async def send(
        self, device_token: str, payload: NotificationPayload
    ) -> DeliveryResult:
        """Send notification via OneSignal."""
        return (await self.send_batch([device_token], payload))[0]

    async def send_batch(
        self, device_tokens: List[str], payload: NotificationPayload
    ) -> List[DeliveryResult]:
        """Send notification to multiple devices via OneSignal."""
        await self._ensure_client()

        try:
            message = self._build_onesignal_message(device_tokens, payload)

            response = await self._client.post(
                f"{self._base_url}/notifications", json=message
            )

            if response.status_code in (200, 201):
                result = response.json()
                notification_id = result.get("id")

                # OneSignal returns single response for batch
                return [
                    DeliveryResult(
                        notification_id=payload.notification_id,
                        provider=self.name,
                        success=True,
                        provider_message_id=notification_id,
                        delivered_at=datetime.now(timezone.utc),
                    )
                    for _ in device_tokens
                ]
            else:
                error_data = response.json() if response.content else {}
                return [
                    DeliveryResult(
                        notification_id=payload.notification_id,
                        provider=self.name,
                        success=False,
                        error=f"OneSignal error {response.status_code}: {error_data}",
                    )
                    for _ in device_tokens
                ]

        except Exception as e:
            logger.error(f"OneSignal send error: {e}")
            return [
                DeliveryResult(
                    notification_id=payload.notification_id,
                    provider=self.name,
                    success=False,
                    error=str(e),
                )
                for _ in device_tokens
            ]

    async def validate_token(self, device_token: str) -> bool:
        """
        Validate OneSignal player ID.

        OneSignal uses player IDs which are UUIDs.
        """
        # Basic UUID format check
        import re

        uuid_pattern = re.compile(
            r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
            re.IGNORECASE,
        )
        return bool(uuid_pattern.match(device_token))


# Notification templates

NOTIFICATION_TEMPLATES = {
    NotificationType.TASK_AVAILABLE: {
        "title": "New Task Available",
        "body": "A new {category} task is available for ${bounty}",
        "priority": NotificationPriority.NORMAL,
    },
    NotificationType.TASK_ASSIGNED: {
        "title": "Task Assigned",
        "body": "You've been assigned: {task_title}",
        "priority": NotificationPriority.HIGH,
    },
    NotificationType.TASK_REMINDER: {
        "title": "Task Reminder",
        "body": "Don't forget: {task_title} - {time_remaining} remaining",
        "priority": NotificationPriority.NORMAL,
    },
    NotificationType.TIMEOUT_WARNING: {
        "title": "Submission Deadline Approaching",
        "body": "Only {time_remaining} left to submit: {task_title}",
        "priority": NotificationPriority.HIGH,
    },
    NotificationType.TIMEOUT_EXPIRED: {
        "title": "Submission Deadline Passed",
        "body": "Time expired for: {task_title}",
        "priority": NotificationPriority.CRITICAL,
    },
    NotificationType.SUBMISSION_RECEIVED: {
        "title": "Submission Received",
        "body": "Your submission for {task_title} is under review",
        "priority": NotificationPriority.NORMAL,
    },
    NotificationType.SUBMISSION_APPROVED: {
        "title": "Submission Approved!",
        "body": "Great work! Your submission for {task_title} was approved. Payment: ${amount}",
        "priority": NotificationPriority.HIGH,
    },
    NotificationType.SUBMISSION_REJECTED: {
        "title": "Submission Needs Revision",
        "body": "Your submission for {task_title} requires changes: {reason}",
        "priority": NotificationPriority.HIGH,
    },
    NotificationType.PAYMENT_SENT: {
        "title": "Payment Sent",
        "body": "You've received ${amount} for {task_title}",
        "priority": NotificationPriority.HIGH,
    },
    NotificationType.DISPUTE_OPENED: {
        "title": "Dispute Opened",
        "body": "A dispute has been opened for: {task_title}",
        "priority": NotificationPriority.CRITICAL,
    },
    NotificationType.GRACE_PERIOD_WARNING: {
        "title": "Connection Issue Detected",
        "body": "Reconnect within {time_remaining} to keep your tasks",
        "priority": NotificationPriority.CRITICAL,
    },
    NotificationType.RECONNECTION_NEEDED: {
        "title": "Reconnection Required",
        "body": "Your session expired. Reconnect to continue working",
        "priority": NotificationPriority.CRITICAL,
    },
}


class PushNotificationManager:
    """
    Manages push notifications across providers.

    Handles:
    - Provider registration and selection
    - Device token management
    - Notification routing
    - Delivery tracking
    - Template-based notifications

    Example:
        manager = PushNotificationManager()

        # Register providers
        manager.register_provider(FirebaseProvider(project_id="my-project"))
        manager.register_provider(OneSignalProvider(app_id="xxx", rest_api_key="yyy"))

        # Register device
        await manager.register_device(
            user_id="worker-123",
            device_token="fcm_token_here",
            provider="firebase"
        )

        # Send notification
        await manager.send_notification(
            notification_type=NotificationType.TASK_ASSIGNED,
            recipient_id="worker-123",
            data={"task_title": "Verify store inventory", "bounty": "5.00"}
        )
    """

    def __init__(self):
        """Initialize notification manager."""
        self._providers: Dict[str, NotificationProvider] = {}
        self._devices: Dict[str, List[Dict]] = {}  # user_id -> list of devices
        self._delivery_history: List[DeliveryResult] = []
        self._notification_counter = 0

    def register_provider(self, provider: NotificationProvider):
        """
        Register a notification provider.

        Args:
            provider: NotificationProvider implementation
        """
        self._providers[provider.name] = provider
        logger.info(f"Notification provider registered: {provider.name}")

    def get_provider(self, name: str) -> Optional[NotificationProvider]:
        """Get registered provider by name."""
        return self._providers.get(name)

    async def register_device(
        self,
        user_id: str,
        device_token: str,
        provider: str,
        device_info: Optional[Dict] = None,
    ) -> bool:
        """
        Register a device for push notifications.

        Args:
            user_id: User/worker ID
            device_token: Push notification token
            provider: Provider name (firebase, onesignal)
            device_info: Optional device metadata

        Returns:
            True if registered successfully
        """
        provider_impl = self._providers.get(provider)
        if not provider_impl:
            logger.error(f"Provider not found: {provider}")
            return False

        # Validate token
        if not await provider_impl.validate_token(device_token):
            logger.warning(
                f"Invalid device token for {provider}: {device_token[:20]}..."
            )
            return False

        if user_id not in self._devices:
            self._devices[user_id] = []

        # Check for duplicate
        for device in self._devices[user_id]:
            if device["token"] == device_token:
                # Update existing
                device["provider"] = provider
                device["info"] = device_info or {}
                device["updated_at"] = datetime.now(timezone.utc)
                return True

        # Add new device
        self._devices[user_id].append(
            {
                "token": device_token,
                "provider": provider,
                "info": device_info or {},
                "registered_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        )

        logger.info(f"Device registered for {user_id} via {provider}")
        return True

    async def unregister_device(self, user_id: str, device_token: str) -> bool:
        """
        Unregister a device.

        Args:
            user_id: User/worker ID
            device_token: Push notification token

        Returns:
            True if unregistered
        """
        if user_id not in self._devices:
            return False

        original_count = len(self._devices[user_id])
        self._devices[user_id] = [
            d for d in self._devices[user_id] if d["token"] != device_token
        ]

        if len(self._devices[user_id]) < original_count:
            logger.info(f"Device unregistered for {user_id}")
            return True
        return False

    def _generate_notification_id(self) -> str:
        """Generate unique notification ID."""
        self._notification_counter += 1
        return f"notif_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{self._notification_counter}"

    def _build_payload_from_template(
        self,
        notification_type: NotificationType,
        recipient_id: str,
        data: Dict[str, Any],
    ) -> NotificationPayload:
        """Build notification payload from template."""
        template = NOTIFICATION_TEMPLATES.get(
            notification_type,
            {
                "title": "Notification",
                "body": "You have a new notification",
                "priority": NotificationPriority.NORMAL,
            },
        )

        # Format title and body with data
        title = template["title"]
        body = template["body"]

        for key, value in data.items():
            title = title.replace(f"{{{key}}}", str(value))
            body = body.replace(f"{{{key}}}", str(value))

        return NotificationPayload(
            notification_id=self._generate_notification_id(),
            notification_type=notification_type,
            recipient_id=recipient_id,
            title=title,
            body=body,
            priority=template["priority"],
            data=data,
        )

    async def send_notification(
        self,
        notification_type: NotificationType,
        recipient_id: str,
        data: Optional[Dict[str, Any]] = None,
        custom_payload: Optional[NotificationPayload] = None,
    ) -> List[DeliveryResult]:
        """
        Send notification to a user.

        Args:
            notification_type: Type of notification
            recipient_id: Recipient user/worker ID
            data: Data for template formatting
            custom_payload: Override template with custom payload

        Returns:
            List of DeliveryResults (one per device)
        """
        if custom_payload:
            payload = custom_payload
        else:
            payload = self._build_payload_from_template(
                notification_type, recipient_id, data or {}
            )

        devices = self._devices.get(recipient_id, [])
        if not devices:
            logger.warning(f"No devices registered for {recipient_id}")
            return []

        results = []
        for device in devices:
            provider = self._providers.get(device["provider"])
            if not provider:
                continue

            result = await provider.send(device["token"], payload)
            results.append(result)
            self._delivery_history.append(result)

        success_count = sum(1 for r in results if r.success)
        logger.info(
            f"Notification sent to {recipient_id}: "
            f"{success_count}/{len(results)} successful"
        )

        return results

    async def send_to_multiple(
        self,
        notification_type: NotificationType,
        recipient_ids: List[str],
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[DeliveryResult]]:
        """
        Send notification to multiple users.

        Args:
            notification_type: Type of notification
            recipient_ids: List of recipient IDs
            data: Data for template formatting

        Returns:
            Dict mapping recipient_id to DeliveryResults
        """
        results = {}
        for recipient_id in recipient_ids:
            results[recipient_id] = await self.send_notification(
                notification_type, recipient_id, data
            )
        return results

    async def send_timeout_warning(
        self, recipient_id: str, task_id: str, task_title: str, time_remaining: str
    ) -> List[DeliveryResult]:
        """
        Send timeout warning notification.

        Convenience method for timeout warnings.
        """
        return await self.send_notification(
            NotificationType.TIMEOUT_WARNING,
            recipient_id,
            {
                "task_id": task_id,
                "task_title": task_title,
                "time_remaining": time_remaining,
            },
        )

    async def send_grace_period_warning(
        self, recipient_id: str, time_remaining: str
    ) -> List[DeliveryResult]:
        """
        Send grace period warning notification.

        Convenience method for connectivity grace period warnings.
        """
        return await self.send_notification(
            NotificationType.GRACE_PERIOD_WARNING,
            recipient_id,
            {"time_remaining": time_remaining},
        )

    def get_user_devices(self, user_id: str) -> List[Dict]:
        """Get all registered devices for a user."""
        return self._devices.get(user_id, [])

    def get_delivery_history(
        self, limit: int = 100, notification_id: Optional[str] = None
    ) -> List[DeliveryResult]:
        """Get delivery history."""
        history = self._delivery_history

        if notification_id:
            history = [r for r in history if r.notification_id == notification_id]

        return history[-limit:]

    def get_stats(self) -> Dict:
        """Get notification statistics."""
        total_sent = len(self._delivery_history)
        successful = sum(1 for r in self._delivery_history if r.success)
        failed = total_sent - successful

        by_provider = {}
        for provider_name in self._providers.keys():
            provider_results = [
                r for r in self._delivery_history if r.provider == provider_name
            ]
            by_provider[provider_name] = {
                "total": len(provider_results),
                "success": sum(1 for r in provider_results if r.success),
            }

        total_devices = sum(len(devices) for devices in self._devices.values())

        return {
            "providers": list(self._providers.keys()),
            "total_users": len(self._devices),
            "total_devices": total_devices,
            "delivery": {
                "total": total_sent,
                "successful": successful,
                "failed": failed,
                "success_rate": (successful / total_sent * 100)
                if total_sent > 0
                else 0,
            },
            "by_provider": by_provider,
        }
