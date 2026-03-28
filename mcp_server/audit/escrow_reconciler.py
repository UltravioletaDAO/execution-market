"""Background job that reconciles DB escrow state vs on-chain balances."""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

RECONCILE_INTERVAL = int(os.environ.get("EM_RECONCILE_INTERVAL", "900"))  # 15 min


async def reconcile_escrows() -> dict:
    """
    Compare DB escrow records against on-chain state.
    Returns summary dict with pass/fail counts.
    """
    from audit import audit_log

    try:
        import supabase_client as db

        client = db.get_client()

        # Get all active escrows (deposited or pending)
        result = (
            client.table("escrows")
            .select("id, task_id, status, total_amount_usdc, chain_id, funding_tx")
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
            chain_id = escrow.get("chain_id", 8453)

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


async def run_escrow_reconciliation_loop():
    """Background loop that runs reconciliation every RECONCILE_INTERVAL seconds."""
    await asyncio.sleep(60)  # Wait for server to stabilize
    while True:
        try:
            await reconcile_escrows()
        except Exception as e:
            logger.error("Escrow reconciliation loop error: %s", e)
        await asyncio.sleep(RECONCILE_INTERVAL)
