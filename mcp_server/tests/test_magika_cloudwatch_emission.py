"""
Tests for CloudWatch emission of Magika accept/reject counters.

Covers the contract described in MASTER_PLAN_VERIFICATION_OVERHAUL:

  1. Counter increments on reject (fraud_score >= 0.8).
  2. Counter increments on accept (fraud_score < 0.8).
  3. emit_magika_metrics publishes MagikaRejectionRate + MagikaRejectionCount
     to the ExecutionMarket/Verification namespace with an Environment
     dimension, and resets counters AFTER the successful call.
  4. If put_metric_data raises, counters are restored (no data loss).
  5. Rejection-rate calculation: 3 rejected + 7 accepted -> 30%.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from verification import cloudwatch_metrics as cw
from verification.cloudwatch_metrics import (
    CLOUDWATCH_NAMESPACE,
    MAGIKA_COUNT_METRIC,
    MAGIKA_RATE_METRIC,
    _build_metric_data,
    emit_magika_metrics,
)
from verification.magika_validator import (
    METRICS,
    MagikaResult,
    MagikaValidator,
    _record_metric_for_result,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_state():
    """Reset the Magika singleton and counter between tests."""
    MagikaValidator.reset_instance()
    METRICS.reset()
    cw._reset_cloudwatch_client()
    # Snapshot state that the module mutates.
    original_status = cw._last_emit_status
    yield
    MagikaValidator.reset_instance()
    METRICS.reset()
    cw._reset_cloudwatch_client()
    cw._last_emit_status = original_status
    cw._last_emit_time = 0.0
    cw._last_emit_error = None


def _build_validator_with_mock(
    detected_mime: str, score: float = 0.99
) -> MagikaValidator:
    """Return a MagikaValidator whose _magika.identify_bytes() is mocked."""
    v = MagikaValidator.__new__(MagikaValidator)
    output = MagicMock()
    output.mime_type = detected_mime
    output.label = detected_mime.split("/")[-1]
    output.ct_label = output.label
    output.group = detected_mime.split("/")[0]
    output.is_text = False
    magika_out = MagicMock()
    magika_out.output = output
    magika_out.score = score
    mock_magika = MagicMock()
    mock_magika.identify_bytes.return_value = magika_out
    v._magika = mock_magika
    return v


def _reject_result() -> MagikaResult:
    return MagikaResult(
        detected_mime="application/x-executable",
        claimed_mime="image/jpeg",
        confidence=0.99,
        is_mismatch=True,
        is_safe=False,
        fraud_score=1.0,
    )


def _accept_result() -> MagikaResult:
    return MagikaResult(
        detected_mime="image/jpeg",
        claimed_mime="image/jpeg",
        confidence=0.99,
        is_mismatch=False,
        is_safe=True,
        fraud_score=0.0,
    )


# ---------------------------------------------------------------------------
# 1. Counter increments on reject
# ---------------------------------------------------------------------------


def test_counter_increments_on_reject():
    """validate_bytes() on a script disguised as an image increments rejected."""
    # PDF MIME is in the whitelist, but claimed=image/jpeg -> dangerous mismatch
    # (fraud_score = 0.8). Use an unsafe MIME instead to force fraud_score=1.0
    # (outside whitelist). Easiest with a raw _record call — the hook is the
    # atomic unit we are validating.
    _record_metric_for_result(_reject_result())

    accepted, rejected = METRICS.snapshot()
    assert rejected == 1, "reject should increment the rejected counter"
    assert accepted == 0, "reject should NOT increment the accepted counter"


def test_validator_increments_reject_via_validate_bytes():
    """End-to-end: validate_bytes on a non-whitelist type should count as reject."""
    validator = _build_validator_with_mock("application/x-executable", score=0.99)
    validator.validate_bytes(b"\x7fELF" + b"\x00" * 100, "image/png", "payload.png")
    accepted, rejected = METRICS.snapshot()
    assert (accepted, rejected) == (0, 1)


# ---------------------------------------------------------------------------
# 2. Counter increments on accept
# ---------------------------------------------------------------------------


def test_counter_increments_on_accept():
    """A clean JPEG increments the accepted counter, not the rejected one."""
    _record_metric_for_result(_accept_result())
    accepted, rejected = METRICS.snapshot()
    assert accepted == 1
    assert rejected == 0


def test_validator_increments_accept_via_validate_bytes():
    validator = _build_validator_with_mock("image/jpeg", score=0.99)
    validator.validate_bytes(
        b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg", "ok.jpg"
    )
    accepted, rejected = METRICS.snapshot()
    assert (accepted, rejected) == (1, 0)


# ---------------------------------------------------------------------------
# 3. Emit + reset (happy path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_emit_puts_metric_and_resets():
    """emit_magika_metrics calls put_metric_data then zeroes counters."""
    for _ in range(3):
        _record_metric_for_result(_accept_result())
    for _ in range(2):
        _record_metric_for_result(_reject_result())

    mock_client = MagicMock()
    with patch(
        "verification.cloudwatch_metrics._get_cloudwatch_client",
        return_value=mock_client,
    ):
        ok = await emit_magika_metrics(environment="test")

    assert ok is True
    assert mock_client.put_metric_data.called, "boto3 put_metric_data not called"
    kwargs = mock_client.put_metric_data.call_args.kwargs
    assert kwargs["Namespace"] == CLOUDWATCH_NAMESPACE

    metric_names = {m["MetricName"] for m in kwargs["MetricData"]}
    assert metric_names == {MAGIKA_COUNT_METRIC, MAGIKA_RATE_METRIC}

    # Dimension must carry the environment label.
    for m in kwargs["MetricData"]:
        dims = {d["Name"]: d["Value"] for d in m["Dimensions"]}
        assert dims == {"Environment": "test"}

    # Counters must be drained AFTER emission.
    accepted, rejected = METRICS.snapshot()
    assert (accepted, rejected) == (0, 0)


# ---------------------------------------------------------------------------
# 4. Failure does not reset
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_emit_failure_does_not_reset():
    """If put_metric_data raises, counters stay available for the next cycle."""
    _record_metric_for_result(_accept_result())
    _record_metric_for_result(_accept_result())
    _record_metric_for_result(_reject_result())

    mock_client = MagicMock()
    mock_client.put_metric_data.side_effect = RuntimeError("throttled")
    with patch(
        "verification.cloudwatch_metrics._get_cloudwatch_client",
        return_value=mock_client,
    ):
        ok = await emit_magika_metrics(environment="test")

    assert ok is False
    accepted, rejected = METRICS.snapshot()
    # Counters restored identically -- no double-counting on retry.
    assert (accepted, rejected) == (2, 1)


@pytest.mark.asyncio
async def test_emit_without_client_preserves_counts():
    """No boto3 client available -> emission returns False and counts survive."""
    _record_metric_for_result(_reject_result())
    with patch(
        "verification.cloudwatch_metrics._get_cloudwatch_client",
        return_value=None,
    ):
        ok = await emit_magika_metrics(environment="test")
    assert ok is False
    accepted, rejected = METRICS.snapshot()
    assert (accepted, rejected) == (0, 1)


# ---------------------------------------------------------------------------
# 5. Rate math
# ---------------------------------------------------------------------------


def test_rate_calculation_30_percent():
    """3 rejected + 7 accepted -> rate = 30%."""
    metrics = _build_metric_data(accepted=7, rejected=3, environment="production")
    by_name = {m["MetricName"]: m for m in metrics}

    assert by_name[MAGIKA_COUNT_METRIC]["Unit"] == "Count"
    assert by_name[MAGIKA_COUNT_METRIC]["Value"] == 3.0

    assert by_name[MAGIKA_RATE_METRIC]["Unit"] == "Percent"
    assert by_name[MAGIKA_RATE_METRIC]["Value"] == pytest.approx(30.0, rel=1e-4)

    # Environment dimension is propagated.
    for m in metrics:
        assert {"Name": "Environment", "Value": "production"} in m["Dimensions"]


def test_rate_calculation_handles_zero_total():
    """No samples at all -> rate 0% (no ZeroDivision)."""
    metrics = _build_metric_data(accepted=0, rejected=0, environment="production")
    by_name = {m["MetricName"]: m for m in metrics}
    assert by_name[MAGIKA_COUNT_METRIC]["Value"] == 0.0
    assert by_name[MAGIKA_RATE_METRIC]["Value"] == 0.0


def test_rate_calculation_all_rejected():
    """All rejects -> rate = 100%."""
    metrics = _build_metric_data(accepted=0, rejected=4, environment="production")
    by_name = {m["MetricName"]: m for m in metrics}
    assert by_name[MAGIKA_COUNT_METRIC]["Value"] == 4.0
    assert by_name[MAGIKA_RATE_METRIC]["Value"] == pytest.approx(100.0, rel=1e-4)


# ---------------------------------------------------------------------------
# Thread-safety sanity
# ---------------------------------------------------------------------------


def test_collector_is_thread_safe_under_parallel_increments():
    """100 threads each recording 100 events -> exactly 10 000 accepts."""
    import threading

    def worker():
        for _ in range(100):
            METRICS.record_accept()

    threads = [threading.Thread(target=worker) for _ in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    accepted, rejected = METRICS.snapshot()
    assert accepted == 10000
    assert rejected == 0
