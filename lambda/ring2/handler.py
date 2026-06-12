"""Ring 2 Arbiter LLM Evaluation Lambda Handler.

Receives SQS messages from Ring 1 containing submissions that passed
PHOTINT verification and need a second-opinion LLM evaluation (the Arbiter).

Pipeline:
  1. Parse SQS record (submission_id, task_id, task, ring1_result)
  2. Idempotency check: skip if arbiter_verdict already set
  3. Master switch: skip if feature.arbiter_enabled is false
  4. Run ArbiterService.evaluate() (dual-ring consensus)
  5. Persist verdict to submissions.arbiter_* columns
  6. INCONCLUSIVE -> advisory only: verdict + recommendation stored, NO
     dispute creation, agent_verdict untouched (INC-2026-04-22 / C-13)
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
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel("INFO")

# Suppress httpx INFO logs — full request URLs leaked the Gemini API key to
# CloudWatch via Ring 1 (C-01). Lambdas never load logging_config.py.
logging.getLogger("httpx").setLevel(logging.WARNING)

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

    Also responds to ``{"action": "version"}`` for deploy verification.

    Returns:
        Lambda response with statusCode and processed count.
    """
    # ── Version probe (direct invoke, not SQS) ──────────────────────
    if event.get("action") == "version":
        return {
            "component": "ring2-worker",
            "git_sha": _GIT_SHA,
            "git_sha_short": _GIT_SHA[:7] if _GIT_SHA != "unknown" else "unknown",
            "build_timestamp": _BUILD_TS,
        }

    # ── OpenRouter credit canary (direct invoke via EventBridge) ────
    if event.get("action") == "openrouter_credit":
        return _openrouter_credit_check()

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
        emit_verification_event,
        get_submission,
        get_task,
        is_arbiter_enabled,
    )

    submission_id = body.get("submission_id", "")
    task_id = body.get("task_id", "")
    denormalized_task = body.get("task", {})
    ring1_result = body.get("ring1_result", {})
    _enqueued_at = body.get("enqueued_at", "")  # preserved for future metrics

    def _emit(step: str, status: str, detail: dict | None = None) -> None:
        try:
            emit_verification_event(submission_id, 2, step, status, detail)
        except Exception:
            pass  # cosmetic, never block pipeline

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
    _emit("tier_routing", "running")
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
        _emit("llm_primary", "running")
        verdict = await arbiter.evaluate(task=task, submission=submission)
    except Exception as e:
        error_msg = f"ArbiterService.evaluate() failed: {type(e).__name__}: {e}"
        logger.exception("Ring 2: %s", error_msg)
        _emit("llm_primary", "failed", {"error": str(e)[:200]})
        _write_permanent_error(submission_id, error_msg)
        return {"error": error_msg}

    _emit(
        "llm_primary",
        "complete",
        {"verdict": verdict.decision.value, "score": round(verdict.aggregate_score, 3)},
    )

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
        # INC-2026-04-22 (C-13): the arbiter is ADVISORY, never authoritative.
        # The verdict + recommendation were already persisted in step 5; the
        # publisher decides approve vs dispute via explicit API. We must NOT
        # create a dispute nor touch agent_verdict here (the original fix
        # only covered the ECS path — this Lambda kept auto-disputing).
        logger.info(
            "Ring 2: INCONCLUSIVE verdict for submission=%s -- stored as "
            "advisory (score=%.3f), publisher decides",
            submission_id,
            verdict.aggregate_score,
        )
        _emit(
            "ring2_inconclusive",
            "complete",
            {
                "advisory": True,
                "score": round(verdict.aggregate_score, 3),
                "recommendation": verdict.reason or "mid-band score",
                "disagreement": bool(verdict.disagreement),
            },
        )
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

    _emit(
        "ring2_complete",
        "complete",
        {
            "verdict": verdict.decision.value,
            "tier": verdict.tier.value,
            "score": round(verdict.aggregate_score, 3),
        },
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
# OpenRouter credit canary (U-39)
# ---------------------------------------------------------------------------


def _openrouter_credit_check() -> Dict[str, Any]:
    """Query OpenRouter's key endpoint and emit remaining credit to CloudWatch.

    Invoked hourly by an EventBridge rule with {"action": "openrouter_credit"}.
    Ring 2 dies silently when the OpenRouter balance hits $0 — the
    EM/Ring2 OpenRouterCreditsRemaining metric feeds a < $10 alarm.
    """
    _ensure_cold_start()
    import boto3
    import httpx

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.error("openrouter_credit: OPENROUTER_API_KEY not configured")
        return {"error": "OPENROUTER_API_KEY not configured"}

    headers = {"Authorization": f"Bearer {api_key}"}

    # Account credits are what actually run out (U-39: "$27.55 of $80
    # remaining"). The /key endpoint only exposes a per-KEY spend limit,
    # which is null on this account — so it never produced a metric.
    remaining = None
    total_credits = None
    total_usage = None
    try:
        resp = httpx.get(
            "https://openrouter.ai/api/v1/credits", headers=headers, timeout=15.0
        )
        resp.raise_for_status()
        credits = resp.json().get("data", {})
        total_credits = float(credits.get("total_credits", 0.0) or 0.0)
        total_usage = float(credits.get("total_usage", 0.0) or 0.0)
        remaining = total_credits - total_usage
    except Exception as e:
        logger.warning("openrouter_credit: /credits failed (%s), trying /key", e)

    # Fallback: per-key limit when the credits endpoint is unavailable.
    if remaining is None:
        resp = httpx.get(
            "https://openrouter.ai/api/v1/key", headers=headers, timeout=15.0
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        limit = data.get("limit")
        usage = float(data.get("usage", 0.0) or 0.0)
        if limit is not None:
            remaining = float(limit) - usage

    result: Dict[str, Any] = {
        "total_credits_usd": total_credits,
        "total_usage_usd": total_usage,
        "remaining_usd": round(remaining, 4) if remaining is not None else None,
        "metric_emitted": False,
    }

    if remaining is not None:
        boto3.client("cloudwatch").put_metric_data(
            Namespace="EM/Ring2",
            MetricData=[
                {
                    "MetricName": "OpenRouterCreditsRemaining",
                    "Value": remaining,
                    "Unit": "None",
                }
            ],
        )
        result["metric_emitted"] = True

    logger.info(
        "openrouter_credit: remaining=%s credits=%s usage=%s",
        result["remaining_usd"],
        total_credits,
        total_usage,
    )
    return result


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
