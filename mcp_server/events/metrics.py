"""
Event Bus Metrics — observability for event delivery health.

Tracks:
- events_published_total: Total events published to the bus
- events_delivered_total: Total successful deliveries to subscribers
- adapter_errors_total: Errors in adapter handlers (by adapter)
- delivery_latency_ms: Per-adapter delivery latency

Exposed via GET /api/v1/admin/metrics/meshrelay (admin auth).
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class EventBusMetrics:
    """Collect and expose Event Bus health metrics."""

    def __init__(self) -> None:
        self._counters: Dict[str, int] = {
            "events_published_total": 0,
            "events_delivered_total": 0,
            "adapter_errors_total": 0,
        }
        self._adapter_errors: Dict[str, int] = {}
        self._adapter_latency: Dict[str, list[float]] = {}
        self._identity_metrics: Dict[str, int] = {
            "verifications_total": 0,
            "trust_upgrades_total": 0,
            "identity_syncs_total": 0,
        }

    def record_publish(self) -> None:
        self._counters["events_published_total"] += 1

    def record_delivery(self, adapter_name: str = "default") -> None:
        self._counters["events_delivered_total"] += 1

    def record_error(self, adapter_name: str = "default") -> None:
        self._counters["adapter_errors_total"] += 1
        self._adapter_errors[adapter_name] = (
            self._adapter_errors.get(adapter_name, 0) + 1
        )

    def record_latency(self, adapter_name: str, latency_ms: float) -> None:
        if adapter_name not in self._adapter_latency:
            self._adapter_latency[adapter_name] = []
        buf = self._adapter_latency[adapter_name]
        buf.append(latency_ms)
        # Keep last 100 samples
        if len(buf) > 100:
            self._adapter_latency[adapter_name] = buf[-100:]

    def record_verification(self) -> None:
        self._identity_metrics["verifications_total"] += 1

    def record_trust_upgrade(self) -> None:
        self._identity_metrics["trust_upgrades_total"] += 1

    def record_identity_sync(self) -> None:
        self._identity_metrics["identity_syncs_total"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Return all metrics as a dict for JSON serialization."""
        # Compute average latencies
        avg_latency = {}
        for adapter, samples in self._adapter_latency.items():
            if samples:
                avg_latency[adapter] = round(sum(samples) / len(samples), 2)

        return {
            **self._counters,
            "adapter_errors_by_name": dict(self._adapter_errors),
            "avg_delivery_latency_ms": avg_latency,
            "identity": dict(self._identity_metrics),
        }

    def reset(self) -> None:
        """Reset all counters (testing only)."""
        for key in self._counters:
            self._counters[key] = 0
        self._adapter_errors.clear()
        self._adapter_latency.clear()
        for key in self._identity_metrics:
            self._identity_metrics[key] = 0


# Singleton
_metrics: Optional[EventBusMetrics] = None


def get_event_bus_metrics() -> EventBusMetrics:
    """Get or create the global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = EventBusMetrics()
    return _metrics
