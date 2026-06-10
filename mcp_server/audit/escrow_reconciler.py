"""Background job that reconciles DB escrow state vs on-chain balances."""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

RECONCILE_INTERVAL = int(os.environ.get("EM_RECONCILE_INTERVAL", "900"))  # 15 min

# How old a 'releasing'/'refunding' claim must be (seconds) before it is
# considered stranded by a crash between the atomic DB claim and the on-chain
# TX (see PaymentDispatcher._claim_escrow_operation).
STUCK_CLAIM_THRESHOLD = int(os.environ.get("EM_STUCK_CLAIM_THRESHOLD", "900"))  # 15 min

# Transitional claim status → terminal status it advances to when the
# settlement is confirmed on-chain.
_TRANSITIONAL_TERMINAL = {"releasing": "released", "refunding": "refunded"}


async def reconcile_escrows() -> dict:
    """
    Compare DB escrow records against on-chain state.
    Returns summary dict with pass/fail counts.
    """
    from audit import audit_log

    try:
        import supabase_client as db

        client = db.get_client()

        result = (
            client.table("escrows")
            .select("id, task_id, status, total_amount_usdc, metadata, funding_tx")
            .in_("status", ["deposited", "pending", "locked"])
            .execute()
        )

        escrows = result.data or []
        if not escrows:
            return {"checked": 0, "pass": 0, "fail": 0, "errors": []}

        passed = 0
        failed = 0
        errors = []

        for escrow in escrows:
            task_id = escrow.get("task_id", "?")
            db_status = escrow.get("status", "unknown")
            db_amount = float(escrow.get("total_amount_usdc") or 0)
            esc_meta = escrow.get("metadata") or {}
            if isinstance(esc_meta, str):
                import json

                esc_meta = json.loads(esc_meta)
            chain_id = esc_meta.get("chain_id", 8453)

            issues = []
            if db_status == "deposited" and db_amount <= 0:
                issues.append("deposited_but_zero_amount")
            if db_status == "deposited" and not escrow.get("funding_tx"):
                issues.append("deposited_but_no_funding_tx")

            if issues:
                failed += 1
                errors.append(
                    {"task_id": task_id, "issues": issues, "status": db_status}
                )
                audit_log(
                    "AUDIT_ESCROW_MISMATCH",
                    task_id=task_id,
                    db_status=db_status,
                    db_amount=db_amount,
                    chain_id=chain_id,
                    issues=issues,
                    severity="WARNING",
                )

                # Corrective action: mark phantom escrows as failed
                if "deposited_but_zero_amount" in issues:
                    try:
                        client.table("escrows").update(
                            {
                                "status": "failed",
                                "metadata": {
                                    **(esc_meta or {}),
                                    "reconciler_action": "auto_failed",
                                    "reconciler_reason": "deposited_but_zero_amount",
                                },
                            }
                        ).eq("task_id", task_id).execute()
                        audit_log(
                            "AUDIT_ESCROW_AUTO_CORRECTED",
                            task_id=task_id,
                            action="status_set_to_failed",
                            reason="deposited_but_zero_amount",
                        )
                    except Exception as fix_err:
                        logger.warning(
                            "Escrow auto-correction failed for task %s: %s",
                            task_id,
                            fix_err,
                        )
            else:
                passed += 1

        summary = {
            "checked": len(escrows),
            "pass": passed,
            "fail": failed,
            "errors": errors,
        }
        audit_log("escrow_reconciliation", **summary)
        return summary

    except Exception as e:
        logger.error("Escrow reconciliation failed: %s", e)
        audit_log("escrow_reconciliation_error", error=str(e), severity="ERROR")
        return {"checked": 0, "pass": 0, "fail": 0, "errors": [str(e)]}


def _parse_ts(value) -> "datetime | None":
    """Parse an ISO timestamp (Supabase or claim metadata) to aware UTC."""
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
    except (ValueError, TypeError):
        return None


def _claim_age_seconds(escrow: dict, meta: dict, now: datetime) -> "float | None":
    """Age of a transitional claim: claim_claimed_at, else updated/created_at."""
    for value in (
        meta.get("claim_claimed_at"),
        escrow.get("updated_at"),
        escrow.get("created_at"),
    ):
        ts = _parse_ts(value)
        if ts is not None:
            return (now - ts).total_seconds()
    return None


def _rollback_stuck_claim(
    client,
    task_id: str,
    transitional: str,
    previous_status: str,
    meta: dict,
    reason: str,
) -> str:
    """Roll a stranded claim back to its captured pre-claim status (CAS)."""
    from audit import audit_log

    client.table("escrows").update(
        {
            "status": previous_status,
            "metadata": {
                **meta,
                "reconciler_action": "stuck_claim_rolled_back",
                "reconciler_reason": reason,
            },
        }
    ).eq("task_id", task_id).eq("status", transitional).execute()
    audit_log(
        "AUDIT_ESCROW_AUTO_CORRECTED",
        task_id=task_id,
        action=f"status_rolled_back_to_{previous_status}",
        reason=reason,
    )
    logger.info(
        "Stuck escrow claim for task %s rolled back (%s -> %s): %s",
        task_id,
        transitional,
        previous_status,
        reason,
    )
    return "rolled_back"


async def _resolve_stuck_claim(client, escrow: dict, meta: dict) -> str:
    """Remediate one escrow stuck in 'releasing'/'refunding'.

    Returns "advanced" (TX confirmed on-chain → terminal status),
    "rolled_back" (TX never landed → pre-claim status restored), or
    "skipped" (on-chain state unknown → retry next cycle, fail-safe).
    """
    from audit import audit_log

    task_id = escrow.get("task_id", "?")
    transitional = escrow.get("status")
    terminal = _TRANSITIONAL_TERMINAL[transitional]
    previous_status = meta.get("claim_previous_status") or "locked"

    # No fase2 payment_info stored → the dispatcher could not have fired an
    # on-chain TX for this escrow (it rolls back when reconstruction fails).
    # The claim is pure DB state and is safe to roll back blind.
    if not meta.get("payment_info"):
        return _rollback_stuck_claim(
            client, task_id, transitional, previous_status, meta, "no_payment_info"
        )

    # On-chain check via the same SDK + Facilitator path the dispatcher uses
    # (em_check_escrow_state / timeout fallbacks). NEVER direct contract calls.
    from integrations.x402.payment_dispatcher import get_dispatcher

    dispatcher = get_dispatcher()
    pi, pi_meta = await dispatcher._reconstruct_fase2_state(task_id)
    if pi is None:
        # payment_info exists but reconstruction failed (possibly transient).
        # Do NOT guess about on-chain state — retry next cycle.
        logger.warning(
            "Stuck claim for task %s: cannot reconstruct PaymentInfo — skipping",
            task_id,
        )
        return "skipped"

    network = pi_meta.get("network", "base")
    try:
        fase2_client = dispatcher._get_fase2_client(network)
    except Exception as e:
        logger.warning(
            "Stuck claim for task %s: cannot query on-chain state (%s) — "
            "manual verification needed",
            task_id,
            e,
        )
        return "skipped"

    state = await asyncio.to_thread(fase2_client.query_escrow_state, pi)
    cap_raw = state.get("capturableAmount")
    if cap_raw is None:
        logger.warning(
            "Stuck claim for task %s: escrow state has no capturableAmount — skipping",
            task_id,
        )
        return "skipped"

    if int(cap_raw) == 0:
        # Funds left the escrow → the release/refund DID complete on-chain
        # before the crash. Advance to the terminal status (CAS on the
        # transitional state so concurrent progress is never clobbered).
        client.table("escrows").update(
            {
                "status": terminal,
                "metadata": {
                    **meta,
                    "reconciler_action": "stuck_claim_advanced",
                    "reconciler_reason": "onchain_capturable_zero",
                },
            }
        ).eq("task_id", task_id).eq("status", transitional).execute()
        audit_log(
            "AUDIT_ESCROW_AUTO_CORRECTED",
            task_id=task_id,
            action=f"status_set_to_{terminal}",
            reason="stuck_claim_onchain_settled",
        )
        logger.info(
            "Stuck escrow claim for task %s advanced (%s -> %s): settled on-chain",
            task_id,
            transitional,
            terminal,
        )
        return "advanced"

    # Funds still capturable → the on-chain TX never landed. Unblock retries.
    return _rollback_stuck_claim(
        client, task_id, transitional, previous_status, meta, "onchain_not_settled"
    )


async def reconcile_stuck_claims() -> dict:
    """
    Remediate escrows stranded in 'releasing'/'refunding' by a crash between
    the atomic claim (PaymentDispatcher._claim_escrow_operation) and the
    on-chain TX. Without this, such rows block all retries forever.

    Returns summary dict with checked/advanced/rolled_back/skipped counts.
    """
    from audit import audit_log

    summary: dict = {
        "checked": 0,
        "advanced": 0,
        "rolled_back": 0,
        "skipped": 0,
        "errors": [],
    }
    try:
        import supabase_client as db

        client = db.get_client()
        result = (
            client.table("escrows")
            .select("id, task_id, status, metadata, updated_at, created_at")
            .in_("status", list(_TRANSITIONAL_TERMINAL))
            .execute()
        )
        rows = result.data or []
        if not rows:
            return summary

        now = datetime.now(timezone.utc)
        for escrow in rows:
            task_id = escrow.get("task_id", "?")
            meta = escrow.get("metadata") or {}
            if isinstance(meta, str):
                meta = json.loads(meta)

            age = _claim_age_seconds(escrow, meta, now)
            if age is None or age < STUCK_CLAIM_THRESHOLD:
                continue
            summary["checked"] += 1

            audit_log(
                "AUDIT_ESCROW_STUCK_CLAIM",
                task_id=task_id,
                db_status=escrow.get("status"),
                age_seconds=int(age),
                threshold_seconds=STUCK_CLAIM_THRESHOLD,
                severity="WARNING",
            )
            try:
                action = await _resolve_stuck_claim(client, escrow, meta)
                summary[action] += 1
            except Exception as fix_err:
                logger.error(
                    "Stuck-claim remediation failed for task %s: %s",
                    task_id,
                    fix_err,
                )
                summary["errors"].append({"task_id": task_id, "error": str(fix_err)})

        if summary["checked"]:
            audit_log("escrow_stuck_claim_reconciliation", **summary)
        return summary

    except Exception as e:
        logger.error("Stuck-claim reconciliation failed: %s", e)
        audit_log(
            "escrow_stuck_claim_reconciliation_error", error=str(e), severity="ERROR"
        )
        summary["errors"].append(str(e))
        return summary


async def run_escrow_reconciliation_loop():
    """Background loop that runs reconciliation every RECONCILE_INTERVAL seconds."""
    await asyncio.sleep(60)  # Wait for server to stabilize
    while True:
        try:
            await reconcile_escrows()
        except Exception as e:
            logger.error("Escrow reconciliation loop error: %s", e)
        try:
            await reconcile_stuck_claims()
        except Exception as e:
            logger.error("Stuck-claim reconciliation loop error: %s", e)
        await asyncio.sleep(RECONCILE_INTERVAL)
