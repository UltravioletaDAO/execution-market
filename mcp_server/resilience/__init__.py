"""
Network Resilience Module for Chamba

Handles network connectivity, timeouts, and push notifications
for reliable task execution in unstable network conditions.

NOW-171: Network connectivity handling with 30-minute grace period
NOW-172: Submission timeout handling (4 hours default)
NOW-173: Push notifications integration (FCM, OneSignal)
"""

from .connectivity import (
    ConnectionState,
    WorkerConnection,
    ConnectivityManager,
    GracePeriodExpired,
    ConnectionLost,
)

from .timeouts import (
    TimeoutType,
    TimeoutConfig,
    TaskTimeout,
    TimeoutManager,
    TimeoutExpired,
    TimeoutWarning,
)

from .notifications import (
    NotificationProvider,
    NotificationPriority,
    NotificationPayload,
    PushNotificationManager,
    FirebaseProvider,
    OneSignalProvider,
)

__all__ = [
    # Connectivity
    "ConnectionState",
    "WorkerConnection",
    "ConnectivityManager",
    "GracePeriodExpired",
    "ConnectionLost",
    # Timeouts
    "TimeoutType",
    "TimeoutConfig",
    "TaskTimeout",
    "TimeoutManager",
    "TimeoutExpired",
    "TimeoutWarning",
    # Notifications
    "NotificationProvider",
    "NotificationPriority",
    "NotificationPayload",
    "PushNotificationManager",
    "FirebaseProvider",
    "OneSignalProvider",
]
