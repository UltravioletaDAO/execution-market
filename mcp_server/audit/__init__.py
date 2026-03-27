"""Structured audit logging for observability."""

import json
import logging
import time

audit_logger = logging.getLogger("em.audit")

PLATFORM_FEE_RATE = 0.13  # 13%


def audit_log(event: str, **kwargs):
    """Emit a structured JSON audit log entry."""
    entry = {
        "event": event,
        "ts": time.time(),
        **kwargs,
    }
    audit_logger.info(json.dumps(entry, default=str))


def verify_fee_split(
    task_id: str,
    gross_usd: float,
    worker_net_usd: float,
    treasury_fee_usd: float,
    protocol_fee_usd: float = 0.0,
) -> bool:
    """Verify the fee math adds up. Returns True if OK, False if mismatch."""
    expected_fee = round(gross_usd * PLATFORM_FEE_RATE, 6)
    expected_worker = gross_usd - expected_fee
    expected_treasury = expected_fee - protocol_fee_usd

    checks = {
        "worker_correct": abs(worker_net_usd - expected_worker) < 0.01,
        "treasury_correct": abs(treasury_fee_usd - expected_treasury) < 0.01,
        "total_balanced": abs(
            (worker_net_usd + treasury_fee_usd + protocol_fee_usd) - gross_usd
        )
        < 0.01,
    }

    if not all(checks.values()):
        audit_log(
            "AUDIT_FAIL_FEE_MATH",
            task_id=task_id,
            gross=gross_usd,
            worker_net=worker_net_usd,
            treasury_fee=treasury_fee_usd,
            protocol_fee=protocol_fee_usd,
            expected_fee=expected_fee,
            expected_worker=expected_worker,
            checks=checks,
            severity="CRITICAL",
        )
        return False

    audit_log(
        "fee_verified",
        task_id=task_id,
        gross=gross_usd,
        worker_net=worker_net_usd,
        treasury_fee=treasury_fee_usd,
        checks="all_pass",
    )
    return True
