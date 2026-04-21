"""
CloudWatch custom-metric emitter for the verification pipeline.

Currently emits Magika accept/reject counters that feed the
`em-production-magika-high-rejection-rate` alarm declared in
`infrastructure/terraform/monitoring.tf`.

Design notes
------------
- Counters live in `verification.magika_validator.METRICS` (thread-safe).
- Emission runs on a background asyncio loop (see ``run_magika_metrics_loop``)
  every ``EM_MAGIKA_METRIC_INTERVAL`` seconds (default 300).
- PutMetricData is invoked via ``asyncio.to_thread`` so the event loop is not
  blocked on network I/O.
- Counters are drained BEFORE the network call; if the call fails, counts are
  restored so the next cycle retries them. This protects us against transient
  throttling / network blips without double-counting.
- Boto3 import is lazy: local / test environments without boto3 installed
  simply log a debug line and keep running.  Same applies when the task lacks
  ``cloudwatch:PutMetricData`` (IAM) — we log and continue rather than crash.
- No private keys, secrets, or wallet addresses are ever logged here.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time as _time
from typing import Optional

from .magika_validator import METRICS as _MAGIKA_METRICS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CLOUDWATCH_NAMESPACE = "ExecutionMarket/Verification"
MAGIKA_RATE_METRIC = "MagikaRejectionRate"
MAGIKA_COUNT_METRIC = "MagikaRejectionCount"

# Default cadence: every 5 minutes. Matches the alarm's period=300 window.
MAGIKA_METRIC_INTERVAL = int(os.environ.get("EM_MAGIKA_METRIC_INTERVAL", "300"))

# Dimension: environment name (production | staging | dev | test).
# Allows future multi-env alarms on the same namespace.
DEFAULT_ENVIRONMENT = os.environ.get("EM_ENVIRONMENT", "production")

# Kill switch — useful for local dev so we do not try to reach CloudWatch.
METRICS_ENABLED = os.environ.get("EM_MAGIKA_METRICS_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
)

# AWS region follows the standard env-var chain. If unset, boto3 derives it.
AWS_REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")

# Health pulse — exposed via /health debug if needed.
_last_emit_time: float = 0.0
_last_emit_status: str = "not_started"
_last_emit_error: Optional[str] = None


# ---------------------------------------------------------------------------
# Boto3 client (lazy)
# ---------------------------------------------------------------------------


_cloudwatch_client = None  # boto3 client cached at module level


def _get_cloudwatch_client():
    """Return a cached boto3 CloudWatch client, or None if unavailable."""
    global _cloudwatch_client
    if _cloudwatch_client is not None:
        return _cloudwatch_client

    try:
        import boto3  # type: ignore[import]
    except ImportError:
        logger.debug("[MAGIKA-METRICS] boto3 not installed; emission disabled")
        return None

    try:
        if AWS_REGION:
            _cloudwatch_client = boto3.client("cloudwatch", region_name=AWS_REGION)
        else:
            _cloudwatch_client = boto3.client("cloudwatch")
        return _cloudwatch_client
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("[MAGIKA-METRICS] cloudwatch client init failed: %s", exc)
        return None


def _reset_cloudwatch_client() -> None:
    """Reset the cached client. Tests only."""
    global _cloudwatch_client
    _cloudwatch_client = None


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------


def _build_metric_data(accepted: int, rejected: int, environment: str) -> list[dict]:
    """Build the MetricData list for PutMetricData.

    Emits both the absolute count and the percentage. The rate metric is
    computed in-process so the alarm can use a simple Average statistic.
    """
    total = accepted + rejected
    rate_pct = (rejected / total * 100.0) if total > 0 else 0.0
    dimensions = [{"Name": "Environment", "Value": environment}]
    return [
        {
            "MetricName": MAGIKA_COUNT_METRIC,
            "Value": float(rejected),
            "Unit": "Count",
            "Dimensions": dimensions,
        },
        {
            "MetricName": MAGIKA_RATE_METRIC,
            "Value": float(round(rate_pct, 4)),
            "Unit": "Percent",
            "Dimensions": dimensions,
        },
    ]


def _put_metric_data_sync(client, metric_data: list[dict]) -> None:
    """Blocking call — must be wrapped in ``asyncio.to_thread`` by callers."""
    client.put_metric_data(Namespace=CLOUDWATCH_NAMESPACE, MetricData=metric_data)


async def emit_magika_metrics(environment: str = DEFAULT_ENVIRONMENT) -> bool:
    """
    Drain the Magika metrics collector and publish to CloudWatch.

    Returns True on success, False otherwise. On failure, the counters are
    restored so they will be retried on the next cycle.
    """
    global _last_emit_time, _last_emit_status, _last_emit_error

    if not METRICS_ENABLED:
        logger.debug("[MAGIKA-METRICS] disabled via EM_MAGIKA_METRICS_ENABLED")
        return False

    # Drain BEFORE the network call so concurrent validator calls increment
    # the next cycle, not the one we are about to emit.
    accepted, rejected = _MAGIKA_METRICS.drain()
    total = accepted + rejected

    if total == 0:
        # Emit a zero-sample so the alarm keeps receiving datapoints during
        # quiet periods. Otherwise the metric goes INSUFFICIENT_DATA and the
        # alarm cannot detect a surge when traffic returns.
        logger.debug("[MAGIKA-METRICS] no samples this window — emitting zero")

    client = _get_cloudwatch_client()
    if client is None:
        # Cannot emit — preserve counts for a future cycle that might have
        # a working client.
        _MAGIKA_METRICS.restore(accepted, rejected)
        _last_emit_status = "no_client"
        _last_emit_error = "cloudwatch_client_unavailable"
        return False

    metric_data = _build_metric_data(accepted, rejected, environment)
    try:
        await asyncio.to_thread(_put_metric_data_sync, client, metric_data)
    except Exception as exc:
        # Transient failure — restore counters so the next cycle retries.
        _MAGIKA_METRICS.restore(accepted, rejected)
        _last_emit_status = "error"
        _last_emit_error = f"{type(exc).__name__}: {str(exc)[:200]}"
        logger.warning(
            "[MAGIKA-METRICS] put_metric_data failed, counts preserved: %s",
            _last_emit_error,
        )
        return False

    _last_emit_time = _time.time()
    _last_emit_status = "ok"
    _last_emit_error = None
    total = accepted + rejected
    if total > 0:
        rate_pct = rejected / total * 100.0
        logger.info(
            "[MAGIKA-METRICS] emitted accepted=%d rejected=%d rate=%.2f%% env=%s",
            accepted,
            rejected,
            rate_pct,
            environment,
        )
    else:
        logger.debug("[MAGIKA-METRICS] emitted idle window env=%s", environment)
    return True


def get_magika_metrics_health() -> dict:
    """Health probe for /health debug view."""
    if _last_emit_time == 0.0:
        return {"status": _last_emit_status}
    age = _time.time() - _last_emit_time
    return {
        "status": _last_emit_status,
        "last_emit_age_s": round(age),
        "interval_s": MAGIKA_METRIC_INTERVAL,
        "last_error": _last_emit_error,
    }


# ---------------------------------------------------------------------------
# Background loop
# ---------------------------------------------------------------------------


async def run_magika_metrics_loop() -> None:
    """Background loop that emits Magika CloudWatch metrics every N seconds.

    Crash-safe: any exception in a single cycle is logged; the loop keeps
    running so a flaky CloudWatch endpoint cannot take the container down.
    """
    logger.info(
        "[MAGIKA-METRICS] loop started interval=%ds namespace=%s env=%s",
        MAGIKA_METRIC_INTERVAL,
        CLOUDWATCH_NAMESPACE,
        DEFAULT_ENVIRONMENT,
    )

    # Stagger a bit behind startup so other boot-time work can settle.
    await asyncio.sleep(min(30, MAGIKA_METRIC_INTERVAL))

    while True:
        try:
            await emit_magika_metrics(DEFAULT_ENVIRONMENT)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - belt and braces
            logger.error("[MAGIKA-METRICS] unexpected error in loop: %s", exc)
        await asyncio.sleep(MAGIKA_METRIC_INTERVAL)
