"""Ring 2 Arbiter LLM Evaluation Lambda Handler.

Receives SQS messages from Ring 1 containing submissions that passed
PHOTINT verification and need a second-opinion LLM evaluation (the Arbiter).

Pipeline:
  1. Parse SQS record (submission_id, task_id, task, ring1_result)
  2. Idempotency check: skip if arbiter_verdict already set
  3. Master switch: skip if feature.arbiter_enabled is false
  4. Run ArbiterService.evaluate() (dual-ring consensus)
  5. Persist verdict to submissions.arbiter_* columns
  6. Handle INCONCLUSIVE -> create dispute for L2 human review
  7. PASS/FAIL -> write verdict only (payment release stays in ECS Phase 3)

Error handling:
  - Permanent errors: write to DB, return success (prevent SQS retry loop)
  - Transient errors: raise exception (SQS retries with backoff)

Secrets loaded at cold start from AWS Secrets Manager:
  - em/supabase  -> SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
  - em/openrouter -> OPENROUTER_API_KEY
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel("INFO")

# ── Build version (injected by CI via Dockerfile ARG) ────────────────────
_GIT_SHA = os.environ.get("GIT_SHA", "unknown")
_BUILD_TS = os.environ.get("BUILD_TIMESTAMP", "unknown")
logger.info("Ring 2 cold start: git_sha=%s build_timestamp=%s", _GIT_SHA[:7], _BUILD_TS)


# ---------------------------------------------------------------------------
# Cold start: load secrets once per Lambda container
# ---------------------------------------------------------------------------

_COLD_START_DONE = False


def _ensure_cold_start() -> None:
    """Load secrets and initialize clients on first invocation."""
    global _COLD_START_DONE
    if _COLD_START_DONE:
        return

    logger.info("Ring 2 Lambda cold start -- loading secrets")
    from supabase_helper import load_secrets

    load_secrets()
    _COLD_START_DONE = True
    logger.info("Ring 2 Lambda cold start complete")


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Process Ring 2 arbiter evaluation messages from SQS.

    Each SQS record contains a JSON body with:
        - submission_id: UUID of the submission
        - task_id: UUID of the task
        - task: denormalized task data (category, bounty, arbiter_mode, etc.)
        - ring1_result: Ring 1 PHOTINT result (score, passed, ai_semantic)
        - enqueued_at: ISO timestamp when the message was enqueued

    Returns:
        Lambda response with statusCode and processed count.
    """
    _ensure_cold_start()

    records = event.get("Records", [])
    logger.info("Ring 2 handler: received %d record(s)", len(records))

    processed = 0
    errors = 0

    for record in records:
        try:
            body = json.loads(record["body"])
            submission_id = body.get("submission_id", "")
            task_id = body.get("task_id", "")

            logger.info(
                "Ring 2: processing submission=%s task=%s",
                submission_id,
                task_id,
            )

            # Run the async evaluation in a sync Lambda context
            result = asyncio.get_event_loop().run_until_complete(_process_record(body))

            if result.get("skipped"):
                logger.info(
                    "Ring 2: submission=%s skipped -- reason=%s",
                    submission_id,
                    result.get("reason", "unknown"),
                )
            elif result.get("error"):
                logger.error(
                    "Ring 2: submission=%s permanent error -- %s",
                    submission_id,
                    result["error"],
                )
                errors += 1
            else:
                logger.info(
                    "Ring 2: submission=%s verdict=%s tier=%s score=%.3f",
                    submission_id,
                    result.get("verdict", "unknown"),
                    result.get("tier", "unknown"),
                    result.get("score", 0.0),
                )

            processed += 1

        except _TransientError:
            # Re-raise so SQS retries this record
            raise

        except Exception as e:
            # Permanent error: log, write to DB, return success to prevent
            # infinite SQS retry loop
            submission_id = "unknown"
            try:
                body = json.loads(record.get("body", "{}"))
                submission_id = body.get("submission_id", "unknown")
            except Exception:
                pass

            logger.exception(
                "Ring 2: permanent error processing submission=%s", submission_id
            )
            _write_permanent_error(submission_id, str(e))
            processed += 1
            errors += 1

    logger.info(
        "Ring 2 handler: processed=%d errors=%d total=%d",
        processed,
        errors,
        len(records),
    )
    return {
        "statusCode": 200,
        "body": json.dumps(
            {"processed": processed, "errors": errors, "total": len(records)}
        ),
    }


# ---------------------------------------------------------------------------
# Custom exception for transient errors (SQS should retry)
# ---------------------------------------------------------------------------


class _TransientError(Exception):
    """Raised for transient failures that SQS should retry."""


# ---------------------------------------------------------------------------
# Core processing logic
# ---------------------------------------------------------------------------


async def _process_record(body: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single SQS record through the arbiter pipeline.

    Args:
        body: Parsed JSON body from the SQS message.

    Returns:
        Dict with processing outcome:
            - {"skipped": True, "reason": "..."} for idempotent/disabled skips
            - {"verdict": "...", "tier": "...", "score": 0.0} for success
            - {"error": "..."} for permanent errors written to DB
    """
    from supabase_helper import (
        get_submission,
        get_task,
        is_arbiter_enabled,
    )

    submission_id = body.get("submission_id", "")
    task_id = body.get("task_id", "")
    denormalized_task = body.get("task", {})
    ring1_result = body.get("ring1_result", {})
    _enqueued_at = body.get("enqueued_at", "")  # preserved for future metrics

    if not submission_id or not task_id:
        return {"error": "Missing submission_id or task_id in SQS message"}

    # ---- Step 1: Idempotency check ----
    logger.info("Ring 2 step 1: idempotency check for submission=%s", submission_id)
    submission = get_submission(submission_id)
    if submission is None:
        return {"error": f"Submission {submission_id} not found in DB"}

    if submission.get("arbiter_verdict") is not None:
        existing = submission["arbiter_verdict"]
        logger.info(
            "Ring 2: submission=%s already has arbiter_verdict=%s -- skipping",
            submission_id,
            existing,
        )
        return {"skipped": True, "reason": f"already_evaluated:{existing}"}

    # ---- Step 2: Master switch ----
    logger.info("Ring 2 step 2: checking master switch")
    if not is_arbiter_enabled():
        logger.info(
            "Ring 2: feature.arbiter_enabled=false -- skipping submission=%s",
            submission_id,
        )
        return {"skipped": True, "reason": "arbiter_disabled"}

    # ---- Step 3: Load task (prefer DB, fallback to denormalized) ----
    logger.info("Ring 2 step 3: loading task=%s", task_id)
    task = get_task(task_id)
    if task is None:
        if denormalized_task:
            logger.warning(
                "Ring 2: task %s not found in DB -- using denormalized copy",
                task_id,
            )
            task = denormalized_task
        else:
            return {"error": f"Task {task_id} not found in DB and no denormalized copy"}

    # Enrich submission with ring1_result if not already present
    if ring1_result:
        if not submission.get("ai_verification_result"):
            submission["ai_verification_result"] = ring1_result
        if (
            not submission.get("auto_check_details")
            and ring1_result.get("score") is not None
        ):
            submission["auto_check_details"] = {
                "score": ring1_result.get("score"),
                "passed": ring1_result.get("passed"),
            }

    # ---- Step 4: Run arbiter evaluation ----
    logger.info(
        "Ring 2 step 4: running ArbiterService.evaluate() for submission=%s "
        "category=%s bounty=%s",
        submission_id,
        task.get("category", "unknown"),
        task.get("bounty_usd", "0"),
    )

    try:
        from integrations.arbiter.service import ArbiterService

        arbiter = ArbiterService.from_defaults()
        verdict = await arbiter.evaluate(task=task, submission=submission)
    except Exception as e:
        error_msg = f"ArbiterService.evaluate() failed: {type(e).__name__}: {e}"
        logger.exception("Ring 2: %s", error_msg)
        _write_permanent_error(submission_id, error_msg)
        return {"error": error_msg}

    logger.info(
        "Ring 2 step 4 complete: verdict=%s tier=%s score=%.3f conf=%.2f "
        "cost=$%.4f latency=%dms",
        verdict.decision.value,
        verdict.tier.value,
        verdict.aggregate_score,
        verdict.confidence,
        verdict.cost_usd,
        verdict.latency_ms,
    )

    # ---- Step 5: Persist verdict to DB ----
    logger.info("Ring 2 step 5: persisting verdict for submission=%s", submission_id)

    persist_ok = _persist_verdict(submission_id, verdict)
    if not persist_ok:
        # DB write failure is transient -- SQS should retry
        raise _TransientError(
            f"Failed to persist verdict for submission {submission_id}"
        )

    # ---- Step 6: Handle verdict actions ----
    logger.info(
        "Ring 2 step 6: handling verdict action for submission=%s decision=%s",
        submission_id,
        verdict.decision.value,
    )

    from integrations.arbiter.types import ArbiterDecision

    if verdict.decision == ArbiterDecision.INCONCLUSIVE:
        _handle_inconclusive(verdict, task, submission)
    elif verdict.decision == ArbiterDecision.PASS:
        logger.info(
            "Ring 2: PASS verdict for submission=%s -- payment release "
            "deferred to ECS (Phase 3)",
            submission_id,
        )
    elif verdict.decision == ArbiterDecision.FAIL:
        logger.info(
            "Ring 2: FAIL verdict for submission=%s -- refund deferred "
            "to ECS (Phase 3)",
            submission_id,
        )
    elif verdict.decision == ArbiterDecision.SKIPPED:
        logger.info(
            "Ring 2: SKIPPED verdict for submission=%s -- reason=%s",
            submission_id,
            verdict.reason,
        )

    return {
        "verdict": verdict.decision.value,
        "tier": verdict.tier.value,
        "score": round(verdict.aggregate_score, 4),
        "confidence": round(verdict.confidence, 4),
        "cost_usd": round(verdict.cost_usd, 6),
        "latency_ms": verdict.latency_ms,
    }


# ---------------------------------------------------------------------------
# Verdict persistence
# ---------------------------------------------------------------------------


def _persist_verdict(
    submission_id: str,
    verdict: Any,
) -> bool:
    """Write the arbiter verdict to submissions.arbiter_* columns.

    This is the Lambda-side equivalent of processor._persist_verdict().
    It writes the same columns but uses the Lambda's Supabase helper
    instead of the ECS supabase_client module.

    Returns True on success, False on failure.
    """
    from supabase_helper import update_submission_verdict

    try:
        from integrations.arbiter.messages import extract_scoring_fields

        scoring = extract_scoring_fields(verdict)
    except Exception as e:
        logger.warning(
            "Failed to extract scoring fields for submission %s: %s -- "
            "persisting without enrichment",
            submission_id,
            e,
        )
        scoring = {}

    update_data = {
        "arbiter_verdict": verdict.decision.value,
        "arbiter_tier": verdict.tier.value,
        "arbiter_score": round(float(verdict.aggregate_score), 4),
        "arbiter_confidence": round(float(verdict.confidence), 4),
        "arbiter_evidence_hash": verdict.evidence_hash,
        "arbiter_commitment_hash": verdict.commitment_hash,
        "arbiter_verdict_data": {
            **verdict.to_dict(),
            "grade": scoring.get("grade"),
            "summary": scoring.get("summary"),
            "authenticity_score": scoring.get("authenticity_score"),
            "completion_score": scoring.get("completion_score"),
            "check_details": scoring.get("check_details"),
        },
        "arbiter_cost_usd": round(float(verdict.cost_usd), 6),
        "arbiter_latency_ms": int(verdict.latency_ms),
        "arbiter_evaluated_at": verdict.evaluated_at.isoformat(),
    }

    return update_submission_verdict(submission_id, update_data)


# ---------------------------------------------------------------------------
# INCONCLUSIVE -> L2 escalation
# ---------------------------------------------------------------------------


def _handle_inconclusive(
    verdict: Any,
    task: Dict[str, Any],
    submission: Dict[str, Any],
) -> None:
    """Create a dispute for L2 human arbiter review.

    Equivalent to escalation.escalate_to_human() but using the Lambda's
    Supabase helper for DB access.
    """
    from supabase_helper import create_dispute, mark_submission_disputed

    submission_id = submission.get("id", "")
    task_id = task.get("id", "")
    agent_id = task.get("agent_id", "")
    executor_id = (submission.get("executor") or {}).get("id")

    if not task_id or not submission_id:
        logger.error(
            "Cannot escalate: missing task_id=%s or submission_id=%s",
            task_id,
            submission_id,
        )
        return

    # Timeout for L2 human review (default 24h)
    timeout_hours = 24

    # Map verdict to dispute reason
    if verdict.disagreement and verdict.aggregate_score < 0.5:
        dispute_reason = "fake_evidence"
    elif verdict.aggregate_score < 0.5:
        dispute_reason = "poor_quality"
    else:
        dispute_reason = "other"

    description = (
        f"Auto-escalated by Ring 2 arbiter. Verdict: INCONCLUSIVE "
        f"(score={verdict.aggregate_score:.3f}, "
        f"confidence={verdict.confidence:.3f}, "
        f"tier={verdict.tier.value}). "
        f"Reason: {verdict.reason or 'mid-band score'}"
    )
    if verdict.disagreement:
        description += " [ring disagreement detected]"

    # Compute priority (1-10)
    bounty = float(task.get("bounty_usd", 0) or 0)
    priority = 5
    if bounty >= 10:
        priority += 3
    elif bounty >= 1:
        priority += 1
    if verdict.disagreement:
        priority += 1
    priority = min(10, max(1, priority))

    dispute_data = {
        "task_id": task_id,
        "submission_id": submission_id,
        "agent_id": agent_id,
        "executor_id": executor_id,
        "reason": dispute_reason,
        "description": description,
        "status": "open",
        "priority": priority,
        "disputed_amount_usdc": bounty,
        "escalation_tier": 2,
        "arbiter_verdict_data": verdict.to_dict(),
        "response_deadline": (
            datetime.now(timezone.utc) + timedelta(hours=timeout_hours)
        ).isoformat(),
        "metadata": {
            "source": "ring2_lambda_escalation",
            "ring2_disagreement": verdict.disagreement,
            "evidence_hash": verdict.evidence_hash,
            "commitment_hash": verdict.commitment_hash,
            "escalated_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    dispute = create_dispute(dispute_data)
    if dispute:
        dispute_id = dispute.get("id", "unknown")
        logger.info(
            "Ring 2: created L2 dispute %s for submission=%s (timeout=%dh)",
            dispute_id,
            submission_id,
            timeout_hours,
        )
        mark_submission_disputed(submission_id, dispute_id)
    else:
        logger.error(
            "Ring 2: failed to create dispute for submission=%s", submission_id
        )


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------


def _write_permanent_error(submission_id: str, error_msg: str) -> None:
    """Write a permanent error to the submission for ops visibility.

    Permanent errors (bad data, missing submission, code bugs) should NOT
    be retried by SQS. We write the error to DB and return success.
    """
    if not submission_id or submission_id == "unknown":
        return

    try:
        from supabase_helper import write_error_to_submission

        write_error_to_submission(submission_id, error_msg)
    except Exception as e:
        logger.error(
            "Failed to write permanent error for submission %s: %s",
            submission_id,
            e,
        )
