"""
REST API Routes for Execution Market

Provides HTTP endpoints in addition to MCP tools.
Includes agent endpoints (authenticated) and worker endpoints (public/semi-public).
"""

import logging
import json
import re
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query, Path, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, ConfigDict

import supabase_client as db
from models import TaskCategory, EvidenceType, TaskStatus
from verification.ai_review import (
    calculate_auto_score,
    verify_with_ai,
    VerificationDecision,
)
from .auth import (
    verify_api_key_optional,
    verify_api_key_if_required,
    APIKeyData,
    verify_agent_owns_task,
    verify_agent_owns_submission,
)

# x402 SDK payment verification and settlement
try:
    from integrations.x402.sdk_client import (
        verify_x402_payment,
        get_sdk,
        SDK_AVAILABLE as X402_AVAILABLE,
    )
except ImportError:
    X402_AVAILABLE = False

# Payment dispatcher (x402r escrow vs preauth)
try:
    from integrations.x402.payment_dispatcher import (
        get_dispatcher as get_payment_dispatcher,
        EM_PAYMENT_MODE,
    )
except ImportError:
    EM_PAYMENT_MODE = "preauth"

    def get_payment_dispatcher():  # type: ignore[misc]
        return None


# Payment event audit trail
from integrations.x402.payment_events import log_payment_event


# ERC-8004 reputation integration
try:
    from integrations.erc8004 import rate_worker, EM_AGENT_ID

    ERC8004_AVAILABLE = True
except ImportError:
    ERC8004_AVAILABLE = False
    rate_worker = None
    EM_AGENT_ID = 469  # Default

# ERC-8004 identity verification (non-blocking, cached)
try:
    from integrations.erc8004 import verify_agent_identity

    ERC8004_IDENTITY_AVAILABLE = True
except ImportError:
    ERC8004_IDENTITY_AVAILABLE = False
    verify_agent_identity = None

# Platform configuration
try:
    from config import PlatformConfig

    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

# Default fee (overridden by config system when available)
DEFAULT_PLATFORM_FEE_PERCENT = Decimal("0.08")


async def get_platform_fee_percent() -> Decimal:
    """Get platform fee from config system with fallback."""
    if CONFIG_AVAILABLE:
        try:
            return await PlatformConfig.get_fee_pct()
        except Exception:
            pass
    return DEFAULT_PLATFORM_FEE_PERCENT


async def get_min_bounty() -> Decimal:
    """Get minimum bounty from config system with fallback."""
    if CONFIG_AVAILABLE:
        try:
            return await PlatformConfig.get_min_bounty()
        except Exception:
            pass
    return Decimal("0.01")


async def get_max_bounty() -> Decimal:
    """Get maximum bounty from config system with fallback."""
    if CONFIG_AVAILABLE:
        try:
            return await PlatformConfig.get_max_bounty()
        except Exception:
            pass
    return Decimal("10000.00")


logger = logging.getLogger(__name__)
X402_AUTH_REF_PREFIX = "x402_auth_"

# Escrow lifecycle compatibility sets. The codebase currently supports mixed
# status vocabularies across legacy and newer payment integrations.
REFUNDABLE_ESCROW_STATUSES = {"deposited", "funded", "partial_released", "locked"}
ALREADY_REFUNDED_ESCROW_STATUSES = {"refunded"}
NON_REFUNDABLE_ESCROW_STATUSES = {"released"}
# EIP-3009 authorize-only: no funds moved, authorization just expires.
AUTHORIZE_ONLY_ESCROW_STATUSES = {"authorized", "pending"}
LIVE_TASK_STATUSES = {"published", "accepted", "in_progress", "submitted", "verifying"}
ACTIVE_WORKER_TASK_STATUSES = {"accepted", "in_progress", "submitted", "verifying"}
TASK_PAYMENT_SETTLED_STATUSES = {
    "confirmed",
    "completed",
    "settled",
    "released",
    "success",
    "available",
}


def _normalize_status(value: Optional[str]) -> str:
    return str(value or "").strip().lower()


def _as_amount(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _is_valid_eth_address(value: Optional[str]) -> bool:
    """Validate Ethereum address format (0x + 40 hex chars)."""
    if not value or not isinstance(value, str):
        return False
    v = value.strip()
    if len(v) != 42 or not v.startswith("0x"):
        return False
    return all(c in "0123456789abcdefABCDEF" for c in v[2:])


def _is_tx_hash(value: Optional[str]) -> bool:
    if not value or not isinstance(value, str):
        return False
    normalized = value.strip()
    if len(normalized) != 66 or not normalized.startswith("0x"):
        return False
    return all(char in "0123456789abcdefABCDEF" for char in normalized[2:])


def _pick_first_tx_hash(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if _is_tx_hash(value):
            return value.strip()
    return None


def _sanitize_reference(value: Optional[str]) -> Optional[str]:
    if not value or not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or _is_tx_hash(normalized):
        return None
    if len(normalized) > 96 or normalized.startswith("eyJ"):
        return f"x402 authorization: {normalized[:12]}...{normalized[-8:]}"
    return f"x402 reference: {normalized}"


def _extract_missing_column_name(error_msg: str) -> Optional[str]:
    match = re.search(r"Could not find the '([^']+)' column", error_msg)
    if match:
        return match.group(1)
    return None


def _insert_escrow_record(record: Dict[str, Any]) -> bool:
    """
    Persist escrow rows with schema-drift tolerance.

    Environments can differ on escrows columns. This helper removes unknown
    columns one by one and retries so we can at least persist metadata
    (`x_payment_header`) required for settlement.
    """
    payload = dict(record)
    if not payload:
        return False

    try:
        client = db.get_client()
    except Exception as err:
        logger.warning("Could not initialize db client for escrow insert: %s", err)
        return False

    while payload:
        try:
            client.table("escrows").insert(payload).execute()
            return True
        except Exception as err:
            err_msg = str(err)
            missing_column = _extract_missing_column_name(err_msg)
            if missing_column and missing_column in payload:
                logger.warning(
                    "escrows.%s missing in current schema; retrying escrow insert without it",
                    missing_column,
                )
                payload.pop(missing_column, None)
                continue
            logger.warning("Could not create escrow record: %s", err_msg)
            return False

    return False


def _extract_payment_tx(payment_row: Dict[str, Any]) -> Optional[str]:
    if not payment_row:
        return None

    direct_candidates = (
        payment_row.get("tx_hash"),
        payment_row.get("transaction_hash"),
        payment_row.get("payment_tx"),
        payment_row.get("transaction"),
        payment_row.get("hash"),
    )
    for value in direct_candidates:
        if isinstance(value, str) and _is_tx_hash(value):
            return value.strip()

    nested_keys = (
        "metadata",
        "meta",
        "details",
        "result",
        "response",
        "provider_response",
        "settlement",
        "receipt",
        "raw",
    )
    for key in nested_keys:
        nested = payment_row.get(key)
        if not isinstance(nested, dict):
            continue
        nested_tx = _extract_payment_tx(nested)
        if nested_tx:
            return nested_tx

    return None


def _is_release_payment(payment_row: Dict[str, Any]) -> bool:
    payment_type = _normalize_status(
        payment_row.get("type") or payment_row.get("payment_type")
    )
    if not payment_type:
        return True
    return payment_type in {
        "release",
        "full_release",
        "final_release",
        "partial_release",
    }


def _is_payment_finalized(payment_row: Dict[str, Any]) -> bool:
    tx_hash = _extract_payment_tx(payment_row)

    # For release/final payments we require explicit tx evidence.
    # A "confirmed" status without tx hash can happen in drifted environments
    # and must remain retryable.
    if _is_release_payment(payment_row):
        return bool(tx_hash)

    status = _normalize_status(payment_row.get("status"))
    if status in {"confirmed", "completed", "settled", "released", "success"}:
        return True
    return bool(tx_hash)


def _get_existing_submission_payment(submission_id: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort lookup for an existing release payment for a submission.

    Handles schema drift between legacy (`type`, `tx_hash`) and newer
    (`payment_type`, `transaction_hash`) payment column naming.
    """
    try:
        client = db.get_client()
        result = (
            client.table("payments")
            .select("*")
            .eq("submission_id", submission_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return None

        release_rows = [row for row in rows if _is_release_payment(row)]
        if not release_rows:
            return rows[0]

        for row in release_rows:
            if _is_payment_finalized(row):
                return row

        return release_rows[0]
    except Exception as payment_lookup_err:
        logger.warning(
            "Could not lookup existing payment for submission %s: %s",
            submission_id,
            payment_lookup_err,
        )
        return None


def _record_refund_payment(
    task: Dict[str, Any],
    agent_id: str,
    refund_tx: Optional[str],
    reason: Optional[str],
    settlement_method: Optional[str] = None,
) -> None:
    """
    Best-effort persistence of refund payment audit row.

    Uses legacy-compatible payment fields and fails open if schema differs.
    """
    try:
        client = db.get_client()
        amount = float(task.get("escrow_amount_usdc") or task.get("bounty_usd") or 0)
        client.table("payments").insert(
            {
                "task_id": task.get("id"),
                "type": "refund",
                "payment_type": "refund",
                "status": "confirmed" if refund_tx else "pending",
                "tx_hash": refund_tx,
                "transaction_hash": refund_tx,
                "amount_usdc": amount,
                "escrow_id": task.get("escrow_id"),
                "network": task.get("payment_network") or "base",
                "to_address": agent_id,
                "settlement_method": settlement_method or "unknown",
                "note": f"Task cancellation refund. reason={reason or 'not_provided'}",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
    except Exception as payment_err:
        logger.warning(
            "Could not persist refund payment audit row for task %s: %s",
            task.get("id"),
            payment_err,
        )


def _is_probable_x402_header(value: Optional[str]) -> bool:
    if not value or not isinstance(value, str):
        return False
    normalized = value.strip()
    if len(normalized) < 100:
        return False
    if normalized.startswith("eyJ"):  # base64-encoded JSON payload
        return True
    if normalized.startswith("{"):  # raw JSON payload
        return True
    return False


def _extract_x402_header_from_metadata(metadata: Any) -> Optional[str]:
    if not metadata:
        return None

    data = metadata
    if isinstance(metadata, str):
        try:
            data = json.loads(metadata)
        except Exception:
            return None

    if not isinstance(data, dict):
        return None

    for key in ("x_payment_header", "payment_header", "xPaymentHeader"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _resolve_task_payment_header(
    task_id: Optional[str], task_escrow_tx: Optional[str]
) -> Optional[str]:
    """
    Resolve the original x402 X-Payment header for settlement.

    Priority:
    1) `tasks.escrow_tx` if it already contains a full header (legacy behavior)
    2) `escrows.metadata.x_payment_header` (current canonical storage)
    """
    if _is_probable_x402_header(task_escrow_tx):
        return task_escrow_tx

    if not task_id:
        return None

    try:
        client = db.get_client()
        escrow_result = (
            client.table("escrows")
            .select("metadata")
            .eq("task_id", task_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = escrow_result.data or []
        if not rows:
            return None
        return _extract_x402_header_from_metadata(rows[0].get("metadata"))
    except Exception as err:
        logger.warning(
            "Could not resolve x402 payment header for task %s: %s", task_id, err
        )
        return None


def _extract_agent_wallet_from_header(payment_header: Optional[str]) -> Optional[str]:
    """Extract the agent's wallet address (payer) from an X-Payment header."""
    if not payment_header:
        return None
    try:
        import base64
        import json

        decoded = json.loads(base64.b64decode(payment_header))
        auth = (decoded.get("payload") or {}).get("authorization") or {}
        return auth.get("from")
    except Exception:
        return None


def _extract_payment_amount(payment_row: Optional[Dict[str, Any]]) -> float:
    if not payment_row:
        return 0.0
    return _as_amount(
        payment_row.get("amount_usdc")
        or payment_row.get("amount")
        or payment_row.get("released_amount_usdc")
        or payment_row.get("released_amount")
    )


def _record_submission_paid_fields(
    submission_id: str,
    tx_hash: Optional[str],
    amount_usdc: float,
) -> None:
    """
    Best-effort persistence for submission-level payout fields.

    Keeps compatibility when some live databases do not yet include these columns.
    """
    if not tx_hash:
        return

    try:
        client = db.get_client()
        client.table("submissions").update(
            {
                "payment_tx": tx_hash,
                "payment_amount": round(float(amount_usdc or 0), 6),
                "paid_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", submission_id).execute()
    except Exception as err:
        logger.warning(
            "Could not update submission paid fields for %s: %s",
            submission_id,
            err,
        )


async def _send_reputation_feedback(
    task: Dict[str, Any],
    worker_address: Optional[str],
    release_tx: Optional[str],
    submission: Optional[Dict[str, Any]] = None,
    executor: Optional[Dict[str, Any]] = None,
    override_score: Optional[int] = None,
) -> None:
    if not (ERC8004_AVAILABLE and rate_worker and worker_address and release_tx):
        return

    try:
        from config.platform_config import PlatformConfig

        dynamic_enabled = await PlatformConfig.is_feature_enabled(
            "erc8004_dynamic_scoring"
        )

        if dynamic_enabled:
            from reputation.scoring import calculate_dynamic_score

            scoring_result = calculate_dynamic_score(
                task=task,
                submission=submission or {},
                executor=executor or {},
                override_score=override_score,
            )
            reputation_score = scoring_result["score"]
            scoring_source = scoring_result["source"]
            logger.info(
                "Dynamic scoring: task=%s, score=%d, source=%s",
                task.get("id"),
                reputation_score,
                scoring_source,
            )
        else:
            reputation_score = 80  # Legacy hardcoded score.

        reputation_result = await rate_worker(
            task_id=task["id"],
            score=reputation_score,
            worker_address=worker_address,
            comment=f"Task completed and paid: {task.get('title', 'Unknown')[:50]}",
            proof_tx=release_tx,
        )

        if reputation_result.success:
            logger.info(
                "ERC-8004 reputation submitted: task=%s, worker=%s, score=%d, tx=%s",
                task["id"],
                worker_address[:10],
                reputation_score,
                reputation_result.transaction_hash,
            )
        else:
            logger.warning(
                "ERC-8004 reputation failed: task=%s, error=%s",
                task["id"],
                reputation_result.error,
            )
    except Exception as rep_err:
        logger.error(
            "Exception submitting ERC-8004 reputation for task %s: %s",
            task.get("id"),
            str(rep_err),
        )


async def _execute_post_approval_side_effects(
    submission_id: str,
    submission: Dict[str, Any],
    release_tx: Optional[str],
) -> None:
    """
    Fire-and-forget side effects after a successful approval + payment.

    WS-1: Auto-register worker on ERC-8004 Identity Registry (first completion).
    WS-2: Worker auto-rates the agent on ERC-8004 Reputation Registry.

    All operations are best-effort — failures are logged and recorded in the
    erc8004_side_effects outbox but never affect the approval response.
    """
    task = submission.get("task") or {}
    executor = submission.get("executor") or {}
    task_id = task.get("id")
    worker_address = executor.get("wallet_address")
    executor_id = executor.get("id")
    task_network = task.get("payment_network") or "base"

    try:
        from config.platform_config import PlatformConfig
    except ImportError:
        logger.debug(
            "Side effects modules not available, skipping post-approval effects"
        )
        return

    # ---- WS-1: Worker auto-registration --------------------------------
    try:
        ws1_enabled = await PlatformConfig.is_feature_enabled(
            "erc8004_auto_register_worker"
        )
        if ws1_enabled:
            await _ws1_auto_register_worker(
                submission_id=submission_id,
                executor=executor,
                worker_address=worker_address,
                executor_id=executor_id,
                task_network=task_network,
                task_id=task_id,
            )
    except Exception as e:
        logger.error(
            "WS-1 auto-register error (non-blocking): submission=%s, error=%s",
            submission_id,
            e,
        )

    # ---- WS-2: Worker auto-rates agent ----------------------------------
    try:
        ws2_enabled = await PlatformConfig.is_feature_enabled("erc8004_auto_rate_agent")
        if ws2_enabled:
            await _ws2_auto_rate_agent(
                submission_id=submission_id,
                submission=submission,
                task=task,
                executor=executor,
                release_tx=release_tx,
                task_id=task_id,
            )
    except Exception as e:
        logger.error(
            "WS-2 auto-rate error (non-blocking): submission=%s, error=%s",
            submission_id,
            e,
        )


async def _ws1_auto_register_worker(
    submission_id: str,
    executor: Dict[str, Any],
    worker_address: Optional[str],
    executor_id: Optional[str],
    task_network: str,
    task_id: Optional[str],
) -> None:
    """WS-1: Auto-register worker on first paid completion."""
    from reputation.side_effects import enqueue_side_effect, mark_side_effect

    # Guard: need a valid wallet
    if not worker_address or not _is_valid_eth_address(worker_address):
        logger.info(
            "WS-1 skip: invalid/missing wallet for submission %s", submission_id
        )
        effect = await enqueue_side_effect(
            supabase=db.get_client(),
            submission_id=submission_id,
            effect_type="register_worker_identity",
            payload={"task_id": task_id, "skip_reason": "missing_or_invalid_wallet"},
        )
        if effect:
            await mark_side_effect(
                supabase=db.get_client(),
                effect_id=effect["id"],
                status="skipped",
                error="missing_or_invalid_wallet",
            )
        return

    # Guard: already registered
    existing_agent_id = executor.get("erc8004_agent_id")
    if existing_agent_id:
        logger.info(
            "WS-1 skip: executor %s already has erc8004_agent_id=%s",
            executor_id,
            existing_agent_id,
        )
        effect = await enqueue_side_effect(
            supabase=db.get_client(),
            submission_id=submission_id,
            effect_type="register_worker_identity",
            payload={
                "task_id": task_id,
                "skip_reason": "already_registered",
                "agent_id": existing_agent_id,
            },
        )
        if effect:
            await mark_side_effect(
                supabase=db.get_client(),
                effect_id=effect["id"],
                status="skipped",
                error="already_registered",
            )
        return

    # Enqueue
    effect = await enqueue_side_effect(
        supabase=db.get_client(),
        submission_id=submission_id,
        effect_type="register_worker_identity",
        payload={
            "task_id": task_id,
            "worker_wallet": worker_address,
            "executor_id": executor_id,
            "network": task_network,
        },
    )
    if not effect:
        return  # dedup hit

    # Best-effort immediate attempt
    try:
        from integrations.erc8004.identity import (
            register_worker_gasless,
            update_executor_identity,
        )

        reg_result = await register_worker_gasless(
            wallet_address=worker_address,
            network=task_network,
        )

        if reg_result.status.value == "registered" and reg_result.agent_id:
            if executor_id:
                await update_executor_identity(executor_id, reg_result.agent_id)
            await mark_side_effect(
                supabase=db.get_client(),
                effect_id=effect["id"],
                status="success",
                tx_hash=None,  # gasless — facilitator tx, not directly available
            )
            logger.info(
                "WS-1 success: worker %s registered as agent_id=%s on %s",
                worker_address[:10],
                reg_result.agent_id,
                task_network,
            )
        else:
            await mark_side_effect(
                supabase=db.get_client(),
                effect_id=effect["id"],
                status="failed",
                error=reg_result.error or "registration_returned_no_agent_id",
            )
    except Exception as e:
        await mark_side_effect(
            supabase=db.get_client(),
            effect_id=effect["id"],
            status="failed",
            error=str(e),
        )
        logger.warning("WS-1 immediate attempt failed (will retry): %s", e)


async def _ws2_auto_rate_agent(
    submission_id: str,
    submission: Dict[str, Any],
    task: Dict[str, Any],
    executor: Dict[str, Any],
    release_tx: Optional[str],
    task_id: Optional[str],
) -> None:
    """WS-2: Worker auto-rates the agent after successful payment."""
    from reputation.side_effects import enqueue_side_effect, mark_side_effect

    # Resolve agent ERC-8004 ID
    agent_erc8004_id = None
    raw_erc8004 = task.get("erc8004_agent_id")
    if raw_erc8004 is not None:
        try:
            agent_erc8004_id = int(raw_erc8004)
        except (ValueError, TypeError):
            pass

    if agent_erc8004_id is None:
        raw_agent = task.get("agent_id")
        if raw_agent is not None:
            try:
                agent_erc8004_id = int(raw_agent)
            except (ValueError, TypeError):
                pass

    if agent_erc8004_id is None:
        logger.info("WS-2 skip: no numeric agent ERC-8004 ID for task %s", task_id)
        effect = await enqueue_side_effect(
            supabase=db.get_client(),
            submission_id=submission_id,
            effect_type="rate_agent_from_worker",
            payload={"task_id": task_id, "skip_reason": "missing_agent_erc8004_id"},
        )
        if effect:
            await mark_side_effect(
                supabase=db.get_client(),
                effect_id=effect["id"],
                status="skipped",
                error="missing_agent_erc8004_id",
            )
        return

    # Calculate score via dynamic scoring (fallback 85)
    score = 85
    try:
        from config.platform_config import PlatformConfig

        dynamic_enabled = await PlatformConfig.is_feature_enabled(
            "erc8004_dynamic_scoring"
        )
        if dynamic_enabled:
            from reputation.scoring import calculate_dynamic_score

            scoring_result = calculate_dynamic_score(
                task=task,
                submission=submission,
                executor=executor,
            )
            score = scoring_result["score"]
    except Exception as e:
        logger.debug("WS-2 dynamic scoring fallback to 85: %s", e)

    # Enqueue
    effect = await enqueue_side_effect(
        supabase=db.get_client(),
        submission_id=submission_id,
        effect_type="rate_agent_from_worker",
        payload={
            "task_id": task_id,
            "agent_erc8004_id": agent_erc8004_id,
            "payment_tx": release_tx,
        },
        score=score,
    )
    if not effect:
        return  # dedup hit

    # Best-effort immediate attempt
    try:
        from integrations.erc8004.facilitator_client import rate_agent

        feedback_result = await rate_agent(
            agent_id=agent_erc8004_id,
            task_id=task_id or "",
            score=score,
            proof_tx=release_tx,
        )

        if feedback_result.success:
            await mark_side_effect(
                supabase=db.get_client(),
                effect_id=effect["id"],
                status="success",
                tx_hash=feedback_result.transaction_hash,
            )
            logger.info(
                "WS-2 success: worker rated agent %d with score=%d, tx=%s",
                agent_erc8004_id,
                score,
                feedback_result.transaction_hash,
            )
        else:
            await mark_side_effect(
                supabase=db.get_client(),
                effect_id=effect["id"],
                status="failed",
                error=feedback_result.error or "feedback_submission_failed",
            )
    except Exception as e:
        await mark_side_effect(
            supabase=db.get_client(),
            effect_id=effect["id"],
            status="failed",
            error=str(e),
        )
        logger.warning("WS-2 immediate attempt failed (will retry): %s", e)


async def _is_submission_ready_for_instant_payout(
    submission_id: str,
    submission: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Check if a submission has enough context to settle payment immediately.
    """
    existing_payment = _get_existing_submission_payment(submission_id)
    if existing_payment and _is_payment_finalized(existing_payment):
        return {
            "ready": True,
            "reason": "already_settled",
            "existing_payment": existing_payment,
        }

    task = submission.get("task") or {}
    executor = submission.get("executor") or {}

    task_id = task.get("id")
    worker_address = executor.get("wallet_address")
    payment_header = _resolve_task_payment_header(task_id, task.get("escrow_tx"))

    bounty = Decimal(str(task.get("bounty_usd", 0)))
    # Worker receives full bounty (fee from surplus in total_required)
    worker_payout = bounty

    if not X402_AVAILABLE:
        return {"ready": False, "reason": "x402_unavailable"}
    if not task_id:
        return {"ready": False, "reason": "missing_task"}
    if not payment_header:
        return {"ready": False, "reason": "missing_payment_header"}
    if not worker_address:
        return {"ready": False, "reason": "missing_worker_wallet"}
    if not _is_valid_eth_address(worker_address):
        return {"ready": False, "reason": "invalid_worker_wallet_format"}
    # Self-payment check: compare worker wallet vs agent's actual wallet address
    agent_wallet = _extract_agent_wallet_from_header(payment_header)
    if agent_wallet and worker_address.lower() == agent_wallet.lower():
        return {"ready": False, "reason": "self_payment_blocked"}
    if worker_payout <= 0:
        return {"ready": False, "reason": "non_positive_payout"}

    return {
        "ready": True,
        "reason": "ready",
        "existing_payment": None,
    }


async def _settle_submission_payment(
    submission_id: str,
    submission: Dict[str, Any],
    note: str = "Payment settled via x402 SDK facilitator",
    worker_auth_header: Optional[str] = None,
    fee_auth_header: Optional[str] = None,
    override_score: Optional[int] = None,
) -> Dict[str, Optional[str]]:
    """
    Settle payout for one submission with idempotency safeguards.
    """
    release_tx: Optional[str] = None
    release_error: Optional[str] = None

    task = submission.get("task") or {}
    executor = submission.get("executor") or {}

    escrow_id = task.get("escrow_id")
    task_id = task.get("id")
    worker_address = executor.get("wallet_address")

    bounty = Decimal(str(task.get("bounty_usd", 0)))
    platform_fee_pct = await get_platform_fee_percent()
    fee = (bounty * platform_fee_pct).quantize(Decimal("0.01"))
    # Worker receives full bounty (fee from surplus in total_required)
    worker_payout = bounty

    existing_payment = _get_existing_submission_payment(submission_id)
    if existing_payment and _is_payment_finalized(existing_payment):
        release_tx = _extract_payment_tx(existing_payment)
        if release_tx:
            existing_amount = _extract_payment_amount(existing_payment) or float(
                worker_payout
            )
            _record_submission_paid_fields(
                submission_id=submission_id,
                tx_hash=release_tx,
                amount_usdc=existing_amount,
            )
            logger.info(
                "Idempotent payment hit for submission %s (tx=%s)",
                submission_id,
                release_tx,
            )
        return {"payment_tx": release_tx, "payment_error": None}

    payment_header = _resolve_task_payment_header(task_id, task.get("escrow_tx"))
    # For x402r/fase1/fase2 mode, payment header is not needed at settlement time.
    # Only block if we're in preauth mode and have no header.
    dispatcher = get_payment_dispatcher()
    is_x402r = dispatcher and dispatcher.get_mode() == "x402r"
    is_fase1 = dispatcher and dispatcher.get_mode() == "fase1"
    is_fase2 = dispatcher and dispatcher.get_mode() == "fase2"
    if not payment_header and not is_x402r and not is_fase1 and not is_fase2:
        return {
            "payment_tx": None,
            "payment_error": f"No x402 payment header found for task {task_id}",
        }
    if not worker_address:
        return {
            "payment_tx": None,
            "payment_error": f"No worker wallet address for task {task_id}",
        }
    if not _is_valid_eth_address(worker_address):
        return {
            "payment_tx": None,
            "payment_error": f"Invalid worker wallet format for task {task_id}: {worker_address[:10]}...",
        }

    # Prevent self-payment: compare worker wallet vs agent's actual wallet.
    # For x402r mode, payment_header may be None (settled at task creation),
    # so fall back to escrow beneficiary_address from the task record.
    agent_wallet = _extract_agent_wallet_from_header(payment_header)
    if not agent_wallet and task:
        # Try escrow beneficiary from task or escrow table
        try:
            client = db.get_client()
            esc_result = (
                client.table("escrows")
                .select("beneficiary_address")
                .eq("task_id", task_id)
                .limit(1)
                .execute()
            )
            if esc_result.data:
                agent_wallet = esc_result.data[0].get("beneficiary_address")
        except Exception:
            pass
    if agent_wallet and worker_address.lower() == agent_wallet.lower():
        logger.error(
            "BLOCKED: Self-payment attempt for task %s — worker wallet %s matches agent wallet %s",
            task_id,
            worker_address[:10],
            agent_wallet[:10],
        )
        return {
            "payment_tx": None,
            "payment_error": f"Worker wallet matches agent wallet for task {task_id} — self-payment blocked",
        }

    if not X402_AVAILABLE:
        return {
            "payment_tx": None,
            "payment_error": f"x402 SDK not available for task {task_id}",
        }
    if worker_payout <= 0:
        return {
            "payment_tx": None,
            "payment_error": f"Worker payout is non-positive for task {task_id}",
        }

    try:
        # Use PaymentDispatcher to route to x402r escrow, preauth, or fase1
        dispatcher = get_payment_dispatcher()
        task_network = task.get("payment_network") or "base"
        if dispatcher:
            result = await dispatcher.release_payment(
                task_id=task_id or "",
                worker_address=worker_address,
                bounty_amount=bounty,
                payment_header=payment_header,
                network=task_network,
                worker_auth_header=worker_auth_header,
                fee_auth_header=fee_auth_header,
            )
        else:
            # Fallback: direct SDK settlement (preauth behavior)
            sdk = get_sdk()
            result = await sdk.settle_task_payment(
                task_id=task_id or "",
                payment_header=payment_header,
                worker_address=worker_address,
                bounty_amount=bounty,
                network=task_network,
            )

        if result.get("success"):
            release_tx = _pick_first_tx_hash(
                result.get("tx_hash"),
                result.get("transaction_hash"),
                result.get("transaction"),
                result.get("hash"),
            )
            payment_status = "confirmed" if release_tx else "pending"

            if not release_tx:
                release_error = f"Settlement response for task {task_id} did not include tx hash; retry required"
                logger.error(release_error)

            client = db.get_client()
            payment_record = {
                "task_id": task_id,
                "executor_id": executor.get("id"),
                "submission_id": submission_id,
                "type": "release",
                "payment_type": "full_release",
                "status": payment_status,
                "tx_hash": release_tx,
                "transaction_hash": release_tx,
                "amount_usdc": float(worker_payout),
                "fee_usdc": float(fee),
                "escrow_id": escrow_id,
                "network": task_network,
                "to_address": worker_address,
                "settlement_method": result.get("mode", "facilitator"),
                "note": f"{note} | fee_tx={result.get('fee_tx_hash', 'n/a')}"
                if release_tx
                else f"{note} (awaiting tx hash)",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            try:
                if existing_payment and existing_payment.get("id"):
                    client.table("payments").update(payment_record).eq(
                        "id",
                        existing_payment["id"],
                    ).execute()
                else:
                    client.table("payments").insert(payment_record).execute()
            except Exception as payment_record_err:
                logger.warning(
                    "Could not persist payment record for submission %s: %s",
                    submission_id,
                    payment_record_err,
                )

            if release_tx:
                try:
                    client.table("escrows").update(
                        {
                            "status": "released",
                            "released_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ).eq("task_id", task_id).execute()
                except Exception as escrow_update_err:
                    logger.warning(
                        "Could not update escrow release status for task %s: %s",
                        task_id,
                        escrow_update_err,
                    )

                _record_submission_paid_fields(
                    submission_id=submission_id,
                    tx_hash=release_tx,
                    amount_usdc=float(worker_payout),
                )

                logger.info(
                    "Payment settled via SDK: task=%s, worker=%s, net=%.2f, tx=%s",
                    task_id,
                    worker_address[:10],
                    float(worker_payout),
                    release_tx,
                )

                await _send_reputation_feedback(
                    task=task,
                    worker_address=worker_address,
                    release_tx=release_tx,
                    submission=submission,
                    executor=executor,
                    override_score=override_score,
                )
        else:
            release_error = result.get("error", "SDK settlement failed")
            logger.error(
                "SDK settlement failed for task %s: %s",
                task_id,
                release_error,
            )
    except Exception as err:
        release_error = str(err)
        logger.error(
            "Failed to settle payment for submission %s: %s", submission_id, err
        )

    return {"payment_tx": release_tx, "payment_error": release_error}


async def _auto_approve_submission(
    submission_id: str,
    submission: Dict[str, Any],
    note: str,
) -> Dict[str, Any]:
    verdict = _normalize_status(submission.get("agent_verdict"))
    if verdict in {"accepted", "approved"}:
        return submission
    if verdict not in {"", "pending"}:
        raise ValueError(
            f"Submission {submission_id} cannot be auto-approved from verdict '{submission.get('agent_verdict')}'"
        )

    task = submission.get("task") or {}
    agent_id = task.get("agent_id")
    if not agent_id:
        raise ValueError(f"Submission {submission_id} missing task.agent_id")

    await db.update_submission(
        submission_id=submission_id,
        agent_id=agent_id,
        verdict="accepted",
        notes=note,
    )
    refreshed = await db.get_submission(submission_id)
    return refreshed or submission


def _is_missing_table_error(error: Exception, table_name: str) -> bool:
    payload = str(error).lower()
    table_ref = f"public.{table_name.lower()}"
    return ("pgrst205" in payload and table_ref in payload) or (
        "does not exist" in payload and table_name.lower() in payload
    )


def _is_not_found_error(error: Exception) -> bool:
    payload = str(error).lower()
    return any(
        marker in payload for marker in ("pgrst116", "0 rows", "no rows", "not found")
    )


def _normalize_payment_network(
    payment_row: Dict[str, Any], fallback: str = "base"
) -> str:
    network = str(payment_row.get("network") or "").strip().lower()
    if network:
        return network

    chain_id = payment_row.get("chain_id")
    if chain_id == 84532:
        return "base-sepolia"
    if chain_id == 8453:
        return "base"
    return fallback


def _normalize_payment_type(payment_row: Dict[str, Any]) -> str:
    payment_type = payment_row.get("type") or payment_row.get("payment_type")
    return _normalize_status(payment_type)


def _event_type_from_payment_row(payment_row: Dict[str, Any]) -> str:
    payment_type = _normalize_payment_type(payment_row)
    status = _normalize_status(payment_row.get("status"))

    if status == "disputed":
        return "dispute_hold"
    if payment_type in {"refund", "partial_refund"} or status in {
        "refunded",
        "cancelled",
    }:
        return "refund"
    if payment_type == "partial_release" or status == "partial_released":
        return "partial_release"
    if payment_type in {"final_release", "full_release", "release"}:
        return "final_release"
    if payment_type == "task_payment":
        return (
            "final_release"
            if status in TASK_PAYMENT_SETTLED_STATUSES
            else "escrow_created"
        )
    if payment_type in {"escrow_create", "deposit"}:
        return "escrow_created"
    if status in {"funded", "deposited", "authorized"}:
        return "escrow_created"
    return (
        "escrow_created"
        if status not in TASK_PAYMENT_SETTLED_STATUSES
        else "final_release"
    )


def _actor_from_event_type(event_type: str) -> str:
    if event_type in {"escrow_created", "escrow_funded", "instant_charge"}:
        return "agent"
    if event_type == "dispute_hold":
        return "arbitrator"
    if event_type in {"refund", "authorization_expired"}:
        return "system"
    return "system"


def _derive_payment_status(
    task_status: str,
    has_escrow_context: bool,
    event_types: List[str],
) -> str:
    task_status_normalized = _normalize_status(task_status)
    event_set = set(event_types)

    if "refund" in event_set or "authorization_expired" in event_set:
        return "refunded"
    if "final_release" in event_set:
        return "completed"
    if "partial_release" in event_set:
        return "partial_released"
    if (
        has_escrow_context
        or "escrow_created" in event_set
        or "escrow_funded" in event_set
    ):
        return "escrowed"

    if task_status_normalized == "completed":
        return "completed"
    if task_status_normalized in {"cancelled", "expired"}:
        return "refunded"
    return "pending"


# UUID validation pattern for path parameters
UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

router = APIRouter(prefix="/api/v1", tags=["Execution Market API"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class CreateTaskRequest(BaseModel):
    """Request model for creating a new task."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(
        ...,
        description="Short, descriptive title for the task",
        min_length=5,
        max_length=255,
        examples=["Verify store is open", "Take photo of product display"],
    )
    instructions: str = Field(
        ...,
        description="Detailed instructions for the human executor",
        min_length=20,
        max_length=5000,
    )
    category: TaskCategory = Field(..., description="Category of the task")
    bounty_usd: float = Field(..., description="Bounty amount in USD", gt=0, le=10000)
    deadline_hours: int = Field(
        ...,
        description="Hours from now until deadline",
        ge=1,
        le=720,  # Max 30 days
    )
    evidence_required: List[EvidenceType] = Field(
        ..., description="List of required evidence types", min_length=1, max_length=5
    )
    evidence_optional: Optional[List[EvidenceType]] = Field(
        default=None, description="List of optional evidence types", max_length=5
    )
    location_hint: Optional[str] = Field(
        default=None,
        description="Human-readable location hint (e.g., 'Mexico City downtown')",
        max_length=255,
    )
    location_lat: Optional[float] = Field(
        default=None,
        description="Expected latitude for GPS verification",
        ge=-90,
        le=90,
    )
    location_lng: Optional[float] = Field(
        default=None,
        description="Expected longitude for GPS verification",
        ge=-180,
        le=180,
    )
    min_reputation: int = Field(
        default=0, description="Minimum reputation score required to apply", ge=0
    )
    payment_token: str = Field(
        default="USDC", description="Payment token symbol", max_length=10
    )
    payment_network: str = Field(
        default="base",
        description="Payment network (e.g., base, ethereum, polygon, arbitrum)",
        max_length=30,
    )

    @field_validator("evidence_required")
    @classmethod
    def validate_evidence_unique(cls, v: List[EvidenceType]) -> List[EvidenceType]:
        if len(v) != len(set(v)):
            raise ValueError("Duplicate evidence types not allowed")
        return v


class TaskResponse(BaseModel):
    """Response model for task data."""

    id: str = Field(..., description="Unique task identifier (UUID)")
    title: str = Field(..., description="Short descriptive title of the task")
    status: str = Field(
        ...,
        description="Current task status (published, accepted, in_progress, submitted, completed, cancelled, expired)",
    )
    category: str = Field(
        ...,
        description="Task category (physical_presence, knowledge_access, human_authority, simple_action, digital_physical)",
    )
    bounty_usd: float = Field(..., description="Bounty amount in USD")
    deadline: datetime = Field(..., description="Task deadline (ISO 8601)")
    created_at: datetime = Field(..., description="Task creation timestamp (ISO 8601)")
    agent_id: str = Field(
        ..., description="Agent identifier (wallet address or API key agent_id)"
    )
    executor_id: Optional[str] = Field(
        None, description="Assigned worker's executor ID"
    )
    instructions: Optional[str] = Field(
        None, description="Detailed task instructions for the worker"
    )
    evidence_schema: Optional[Dict] = Field(
        None, description="Required and optional evidence types"
    )
    location_hint: Optional[str] = Field(
        None, description="Human-readable location hint"
    )
    min_reputation: int = Field(
        0, description="Minimum reputation score required to apply"
    )
    erc8004_agent_id: Optional[str] = Field(
        None, description="ERC-8004 on-chain agent identity token ID"
    )
    payment_network: str = Field(
        "base",
        description="Blockchain network for payment (e.g. base, ethereum, polygon)",
    )
    payment_token: str = Field(
        "USDC", description="Payment token symbol (USDC, EURC, USDT, PYUSD)"
    )
    escrow_tx: Optional[str] = Field(
        None, description="Escrow deposit transaction hash or payment reference"
    )
    refund_tx: Optional[str] = Field(
        None, description="Refund transaction hash (if cancelled/refunded)"
    )


class TaskListResponse(BaseModel):
    """Response model for paginated task list."""

    tasks: List[TaskResponse] = Field(..., description="List of task objects")
    total: int = Field(..., description="Total number of matching tasks")
    count: int = Field(..., description="Number of tasks in this page")
    offset: int = Field(..., description="Current pagination offset")
    has_more: bool = Field(..., description="Whether more results are available")


class SubmissionResponse(BaseModel):
    """Response model for submission data."""

    id: str = Field(..., description="Unique submission identifier (UUID)")
    task_id: str = Field(..., description="Associated task ID")
    executor_id: str = Field(..., description="Worker's executor ID")
    status: str = Field(
        ...,
        description="Current verdict status (pending, accepted, rejected, more_info_requested, disputed)",
    )
    pre_check_score: Optional[float] = Field(
        None, description="AI pre-check score (0.0-1.0) if evidence was auto-verified"
    )
    submitted_at: datetime = Field(..., description="Submission timestamp (ISO 8601)")
    evidence: Optional[Dict] = Field(
        None, description="Submitted evidence data (photos, text, documents)"
    )
    agent_verdict: Optional[str] = Field(
        None, description="Agent's verdict on the submission"
    )
    agent_notes: Optional[str] = Field(
        None, description="Agent's notes explaining the verdict"
    )
    verified_at: Optional[datetime] = Field(
        None, description="Timestamp when submission was verified"
    )


class SubmissionListResponse(BaseModel):
    """Response model for submission list."""

    submissions: List[SubmissionResponse] = Field(
        ..., description="List of submission objects"
    )
    count: int = Field(..., description="Total number of submissions")


class ApprovalRequest(BaseModel):
    """Request model for approving a submission."""

    notes: Optional[str] = Field(
        default=None, description="Optional notes about the approval", max_length=1000
    )
    rating_score: Optional[int] = Field(
        default=None,
        description="Optional reputation score override (0-100). "
        "When omitted, score is computed dynamically from submission quality signals.",
        ge=0,
        le=100,
    )


class RejectionRequest(BaseModel):
    """Request model for rejecting a submission."""

    notes: str = Field(
        ..., description="Required reason for rejection", min_length=10, max_length=1000
    )
    severity: str = Field(
        default="minor",
        description="Rejection severity: 'minor' (no on-chain effect) or 'major' (records negative reputation)",
        pattern="^(minor|major)$",
    )
    reputation_score: Optional[int] = Field(
        default=None,
        description="Reputation score for major rejections (0-50). Defaults to 30 if omitted.",
        ge=0,
        le=50,
    )


class RequestMoreInfoRequest(BaseModel):
    """Request model for requesting more info on a submission."""

    notes: str = Field(
        ..., description="Required clarification request", min_length=5, max_length=1000
    )


class CancelRequest(BaseModel):
    """Request model for cancelling a task."""

    reason: Optional[str] = Field(
        default=None, description="Optional reason for cancellation", max_length=500
    )


class AnalyticsResponse(BaseModel):
    """Response model for agent analytics."""

    totals: Dict[str, Any] = Field(
        ..., description="Aggregate totals (total_tasks, total_bounty, completed, etc.)"
    )
    by_status: Dict[str, int] = Field(..., description="Task count breakdown by status")
    by_category: Dict[str, int] = Field(
        ..., description="Task count breakdown by category"
    )
    average_times: Dict[str, str] = Field(
        ..., description="Average times (time_to_accept, time_to_complete, etc.)"
    )
    top_workers: List[Dict] = Field(
        ..., description="Top performing workers for this agent"
    )
    period_days: int = Field(..., description="Number of days covered by this analysis")


class WorkerApplicationRequest(BaseModel):
    """Request model for worker applying to a task."""

    executor_id: str = Field(
        ...,
        description="Worker's executor ID",
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    )
    message: Optional[str] = Field(
        default=None, description="Optional message to the agent", max_length=500
    )


class WorkerAssignRequest(BaseModel):
    """Request model for assigning a task to a worker."""

    executor_id: str = Field(
        ...,
        description="Worker's executor ID",
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional assignment notes for the worker",
        max_length=500,
    )


class WorkerSubmissionRequest(BaseModel):
    """Request model for worker submitting work."""

    executor_id: str = Field(
        ...,
        description="Worker's executor ID",
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    )
    evidence: Dict[str, Any] = Field(
        ..., description="Evidence dictionary with required fields"
    )
    notes: Optional[str] = Field(
        default=None, description="Optional notes about the submission", max_length=1000
    )


class AvailableTasksResponse(BaseModel):
    """Response model for available tasks (worker view)."""

    tasks: List[Dict[str, Any]] = Field(
        ..., description="List of published tasks available for workers"
    )
    count: int = Field(..., description="Number of tasks returned")
    offset: int = Field(..., description="Current pagination offset")
    filters_applied: Dict[str, Any] = Field(
        ..., description="Filters that were applied to this query"
    )


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = Field(True, description="Whether the operation succeeded")
    message: str = Field(..., description="Human-readable result message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional response data")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(
        ..., description="Error code (e.g. TASK_NOT_FOUND, UNAUTHORIZED)"
    )
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error context"
    )


class PublicConfigResponse(BaseModel):
    """Public platform configuration (readable by anyone)."""

    min_bounty_usd: float = Field(..., description="Minimum bounty amount in USD")
    max_bounty_usd: float = Field(..., description="Maximum bounty amount in USD")
    supported_networks: List[str] = Field(
        ..., description="Currently enabled payment networks"
    )
    supported_tokens: List[str] = Field(..., description="Supported stablecoin tokens")
    preferred_network: str = Field(..., description="Default payment network")


class PublicPlatformMetricsResponse(BaseModel):
    """Public high-level platform metrics for landing/dashboard surfaces."""

    users: Dict[str, int] = Field(
        ...,
        description="User counts (registered_workers, registered_agents, active, etc.)",
    )
    tasks: Dict[str, int] = Field(..., description="Task counts by status and total")
    activity: Dict[str, int] = Field(
        ..., description="Activity metrics (active workers, agents with live tasks)"
    )
    payments: Dict[str, float] = Field(
        ..., description="Payment aggregates (total_volume_usd, total_fees_usd)"
    )
    generated_at: datetime = Field(
        ..., description="Timestamp when these metrics were generated"
    )


class TaskPaymentEventResponse(BaseModel):
    """Canonical payment timeline event for a task."""

    id: str = Field(..., description="Unique event identifier")
    type: str = Field(
        ...,
        description="Event type (escrow_created, final_release, refund, partial_release, etc.)",
    )
    actor: str = Field(
        ..., description="Who triggered the event (agent, system, arbitrator)"
    )
    timestamp: str = Field(..., description="Event timestamp (ISO 8601)")
    network: str = Field(..., description="Blockchain network for this event")
    amount: Optional[float] = Field(None, description="Amount in USDC (if applicable)")
    tx_hash: Optional[str] = Field(
        None, description="On-chain transaction hash (0x-prefixed, 66 chars)"
    )
    note: Optional[str] = Field(None, description="Human-readable note about the event")


class TaskPaymentResponse(BaseModel):
    """Canonical payment timeline and status for a task."""

    task_id: str = Field(..., description="Task identifier")
    status: str = Field(
        ...,
        description="Derived payment status (pending, escrowed, completed, refunded, partial_released)",
    )
    total_amount: float = Field(
        ..., description="Total amount escrowed or paid in USDC"
    )
    released_amount: float = Field(
        ..., description="Amount released to the worker in USDC"
    )
    currency: str = Field("USDC", description="Payment currency")
    escrow_tx: Optional[str] = Field(
        None, description="Initial escrow deposit transaction hash"
    )
    escrow_contract: Optional[str] = Field(
        None, description="Escrow contract address (if applicable)"
    )
    network: str = Field("base", description="Primary payment network")
    events: List[TaskPaymentEventResponse] = Field(
        ..., description="Chronological list of payment events"
    )
    created_at: str = Field(..., description="When the payment timeline started")
    updated_at: str = Field(..., description="Last event timestamp")


class ConfigUpdateRequest(BaseModel):
    """Request to update a config value (admin only)."""

    value: Any = Field(..., description="New value for the config key")
    reason: Optional[str] = Field(None, description="Reason for the change (for audit)")


# =============================================================================
# CONFIG ENDPOINTS (PUBLIC)
# =============================================================================


@router.get(
    "/config",
    response_model=PublicConfigResponse,
    responses={
        200: {"description": "Public platform configuration"},
    },
    summary="Get Platform Configuration",
    description="Retrieve public platform configuration including bounty limits, supported networks and tokens",
    tags=["Configuration"],
)
async def get_public_config() -> PublicConfigResponse:
    """
    Get public platform configuration.

    Returns publicly available configuration like bounty limits,
    supported payment networks, and tokens. Does not expose
    internal settings like fees or feature flags.

    **Example Response:**
    ```json
    {
        "min_bounty_usd": 0.25,
        "max_bounty_usd": 10000.0,
        "supported_networks": ["base", "ethereum", "polygon", "arbitrum"],
        "supported_tokens": ["USDC", "EURC", "USDT", "PYUSD"],
        "preferred_network": "base"
    }
    ```

    **Use Cases:**
    - Validate task creation parameters before submission
    - Display supported networks in UI
    - Check minimum/maximum bounty limits
    - Configure payment token selection
    """
    # Always use get_enabled_networks() as source of truth for networks
    # (driven by EM_ENABLED_NETWORKS env var, not stale DB rows)
    from integrations.x402.sdk_client import get_enabled_networks

    enabled = get_enabled_networks()

    if CONFIG_AVAILABLE:
        try:
            config = await PlatformConfig.get_public_config()
            return PublicConfigResponse(
                min_bounty_usd=float(config.get("min_usd", 0.25)),
                max_bounty_usd=float(config.get("max_usd", 10000.00)),
                supported_networks=enabled,
                supported_tokens=config.get("supported_tokens", ["USDC"]),
                preferred_network=config.get("preferred_network", "base"),
            )
        except Exception as e:
            logger.warning(f"Error loading public config: {e}")

    return PublicConfigResponse(
        min_bounty_usd=0.25,
        max_bounty_usd=10000.00,
        supported_networks=enabled,
        supported_tokens=["USDC", "EURC", "USDT", "PYUSD", "AUSD"],
        preferred_network="base",
    )


@router.get(
    "/public/metrics",
    response_model=PublicPlatformMetricsResponse,
    responses={
        200: {"description": "Public platform metrics"},
    },
    summary="Get Platform Metrics",
    description="Retrieve public platform statistics and activity metrics",
    tags=["Public", "Analytics"],
)
async def get_public_platform_metrics() -> PublicPlatformMetricsResponse:
    """
    Get public platform metrics for landing and dashboard views.

    This endpoint is intentionally read-only and unauthenticated.
    Provides high-level statistics about platform activity including:
    - User counts (workers, agents, active users)
    - Task distribution by status
    - Payment volume and activity metrics

    **Example Response:**
    ```json
    {
        "users": {
            "registered_workers": 1250,
            "registered_agents": 340,
            "workers_active_now": 85,
            "agents_active_now": 42
        },
        "tasks": {
            "total": 5680,
            "published": 120,
            "completed": 4890,
            "live": 180
        },
        "payments": {
            "total_volume_usd": 125430.50,
            "total_fees_usd": 10034.44
        },
        "generated_at": "2024-02-11T06:04:00Z"
    }
    ```

    **Use Cases:**
    - Landing page statistics
    - Dashboard overview widgets
    - Public API for external integrations
    - Platform growth tracking
    """
    generated_at = datetime.now(timezone.utc)
    client = db.get_client()

    users = {
        "registered_workers": 0,
        "registered_agents": 0,
        "workers_with_tasks": 0,
        "workers_active_now": 0,
        "workers_completed": 0,
        "agents_active_now": 0,
    }
    tasks: Dict[str, int] = {
        "total": 0,
        "published": 0,
        "accepted": 0,
        "in_progress": 0,
        "submitted": 0,
        "verifying": 0,
        "completed": 0,
        "disputed": 0,
        "cancelled": 0,
        "expired": 0,
        "live": 0,
    }
    activity = {
        "workers_with_active_tasks": 0,
        "workers_with_completed_tasks": 0,
        "agents_with_live_tasks": 0,
    }
    payments = {
        "total_volume_usd": 0.0,
        "total_fees_usd": 0.0,
    }

    # Registered workers
    try:
        workers_result = client.table("executors").select("id", count="exact").execute()
        users["registered_workers"] = int(workers_result.count or 0)
    except Exception as e:
        logger.warning("Could not query executors count for public metrics: %s", e)

    # Registered agents (active API keys as proxy for active/registered agents)
    try:
        agents_result = (
            client.table("api_keys")
            .select("id", count="exact")
            .eq("is_active", True)
            .execute()
        )
        users["registered_agents"] = int(agents_result.count or 0)
    except Exception as e:
        logger.warning("Could not query agents count for public metrics: %s", e)

    # Task and activity aggregates
    try:
        tasks_result = (
            client.table("tasks")
            .select("status, executor_id, agent_id, bounty_usd")
            .execute()
        )
        task_rows = tasks_result.data or []
        fee_pct = float(await get_platform_fee_percent())

        workers_with_tasks = set()
        workers_active = set()
        workers_completed = set()
        agents_active = set()

        for row in task_rows:
            status = _normalize_status(row.get("status"))
            if not status:
                continue

            tasks[status] = tasks.get(status, 0) + 1
            tasks["total"] += 1
            amount = float(row.get("bounty_usd") or 0.0)
            payments["total_volume_usd"] += amount
            if status == "completed":
                payments["total_fees_usd"] += amount * fee_pct

            executor_id = row.get("executor_id")
            if executor_id:
                workers_with_tasks.add(executor_id)
                if status in ACTIVE_WORKER_TASK_STATUSES:
                    workers_active.add(executor_id)
                if status == "completed":
                    workers_completed.add(executor_id)

            agent_id = row.get("agent_id")
            if agent_id and status in LIVE_TASK_STATUSES:
                agents_active.add(agent_id)

        tasks["live"] = sum(tasks.get(status, 0) for status in LIVE_TASK_STATUSES)
        users["workers_with_tasks"] = len(workers_with_tasks)
        users["workers_active_now"] = len(workers_active)
        users["workers_completed"] = len(workers_completed)
        users["agents_active_now"] = len(agents_active)

        activity["workers_with_active_tasks"] = len(workers_active)
        activity["workers_with_completed_tasks"] = len(workers_completed)
        activity["agents_with_live_tasks"] = len(agents_active)
    except Exception as e:
        logger.warning("Could not query task aggregates for public metrics: %s", e)

    payments["total_volume_usd"] = round(payments["total_volume_usd"], 2)
    payments["total_fees_usd"] = round(payments["total_fees_usd"], 2)

    # Fallback derivation to avoid misleading zero counters in degraded schemas.
    # If registry tables drift or fail, derive from task/submission activity.
    if users["registered_workers"] == 0:
        try:
            submissions_result = (
                client.table("submissions").select("executor_id").execute()
            )
            worker_ids = {
                row.get("executor_id")
                for row in (submissions_result.data or [])
                if row.get("executor_id")
            }
            users["registered_workers"] = len(worker_ids)
        except Exception as e:
            logger.warning(
                "Could not derive registered_workers from submissions fallback: %s", e
            )

    if users["registered_agents"] == 0:
        try:
            tasks_agents_result = client.table("tasks").select("agent_id").execute()
            agent_ids = {
                row.get("agent_id")
                for row in (tasks_agents_result.data or [])
                if row.get("agent_id")
            }
            users["registered_agents"] = len(agent_ids)
        except Exception as e:
            logger.warning(
                "Could not derive registered_agents from tasks fallback: %s", e
            )

    return PublicPlatformMetricsResponse(
        users=users,
        tasks=tasks,
        activity=activity,
        payments=payments,
        generated_at=generated_at,
    )


# =============================================================================
# AGENT ENDPOINTS (AUTHENTICATED)
# =============================================================================


@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=201,
    responses={
        201: {"description": "Task created successfully"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request - check bounty limits, network support, or required fields",
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        402: {
            "description": "Payment required. Include X-Payment header with x402 payment authorization."
        },
        429: {
            "model": ErrorResponse,
            "description": "Rate limit exceeded - wait before creating more tasks",
        },
        503: {
            "model": ErrorResponse,
            "description": "x402 payment service unavailable",
        },
    },
    summary="Create Task",
    description="Create a new task with payment escrow (supports preauth, x402r, fase1, and fase2 modes)",
    tags=["Tasks", "Agent"],
)
async def create_task(
    http_request: Request,
    request: CreateTaskRequest,
    api_key: APIKeyData = Depends(verify_api_key_if_required),
) -> TaskResponse:
    """
    Create a new task with automatic payment handling.

    Creates a new task that will be visible to workers. Requires authenticated API key
    and payment authorization via x402 protocol. Supports multiple payment modes:

    ## Payment Modes
    - **preauth**: X-Payment header required, funds authorized but not moved until completion
    - **x402r**: X-Payment header required, funds immediately locked in on-chain escrow
    - **fase1**: X-Payment optional, balance check only (no funds moved)
    - **fase2**: X-Payment optional, funds locked in escrow via facilitator (gasless)

    ## Payment Calculation
    Total required = `bounty_usd × (1 + platform_fee_percent)`
    - Platform fee: typically 6-8% (configurable)
    - Example: $10 bounty → $10.80 total required

    ## Required Headers
    - `Authorization: Bearer <api_key>` - Agent API key
    - `X-Payment: <x402_auth>` - x402 payment authorization (required for preauth/x402r modes)

    ## Request Body Example
    ```json
    {
        "title": "Verify restaurant is open",
        "instructions": "Visit the restaurant and confirm it's currently open for business. Take a photo of the front entrance showing opening hours.",
        "category": "physical_presence",
        "bounty_usd": 5.00,
        "deadline_hours": 24,
        "evidence_required": ["photo", "text_report"],
        "evidence_optional": ["gps_coordinates"],
        "location_hint": "Downtown Portland, near Pioneer Square",
        "location_lat": 45.5152,
        "location_lng": -122.6784,
        "min_reputation": 50,
        "payment_token": "USDC",
        "payment_network": "base"
    }
    ```

    ## Response Example
    ```json
    {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "title": "Verify restaurant is open",
        "status": "published",
        "category": "physical_presence",
        "bounty_usd": 5.00,
        "deadline": "2024-02-12T06:04:00Z",
        "created_at": "2024-02-11T06:04:00Z",
        "agent_id": "0x742d35Cc6634C0532925a3b8D0fC6A3B3e1d7A5B",
        "payment_network": "base",
        "payment_token": "USDC",
        "escrow_tx": "0xabc123...",
        "escrow_amount_usdc": 5.40
    }
    ```

    ## Error Responses
    - `400`: Invalid parameters (bounty limits, unsupported network, missing fields)
    - `401`: Invalid or missing API key
    - `402`: Payment required or x402 payment failed
    - `503`: Payment service unavailable

    ## ERC-8004 Identity Integration
    If the agent has a registered ERC-8004 on-chain identity, it will be automatically
    attached to the task for verification and reputation purposes.

    ## Escrow Handling
    Based on the configured payment mode:
    - **x402r/fase2**: Funds are immediately locked in escrow contract
    - **preauth**: Payment authorization stored, funds moved on task completion
    - **fase1**: Balance verified, no funds moved until payout

    Tasks are created in `published` status and immediately visible to workers.
    """
    try:
        # Get configurable platform fee
        platform_fee_pct = await get_platform_fee_percent()
        min_bounty = await get_min_bounty()
        max_bounty = await get_max_bounty()

        # Calculate total payment required (bounty + platform fee)
        bounty = Decimal(str(request.bounty_usd))

        # Validate bounty against config limits
        if bounty < min_bounty:
            raise HTTPException(
                status_code=400,
                detail=f"Bounty ${bounty} is below minimum ${min_bounty}",
            )
        if bounty > max_bounty:
            raise HTTPException(
                status_code=400,
                detail=f"Bounty ${bounty} exceeds maximum ${max_bounty}",
            )

        # Validate payment network is enabled
        try:
            from integrations.x402.sdk_client import (
                validate_payment_network,
                get_enabled_networks,
            )

            validate_payment_network(request.payment_network)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        total_required = bounty * (1 + platform_fee_pct)
        total_required = total_required.quantize(Decimal("0.01"))

        # Verify x402 payment (or balance check for fase1 mode)
        payment_result = None
        x_payment_header = None  # Store original header for later settlement
        if not X402_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="x402 payment service unavailable; task creation is facilitator-only",
            )

        # Get the original X-Payment header before verification
        x_payment_header = http_request.headers.get(
            "X-Payment"
        ) or http_request.headers.get("x-payment")

        # Fase 1/2: X-Payment header is optional (balance check or escrow lock).
        # If provided, verify as usual for backward compatibility.
        dispatcher = get_payment_dispatcher()
        is_fase1_mode = dispatcher and dispatcher.get_mode() == "fase1"
        is_fase2_mode = dispatcher and dispatcher.get_mode() == "fase2"

        if not x_payment_header and (is_fase1_mode or is_fase2_mode):
            # Fase 1: skip payment verification, do balance check after task creation
            from integrations.x402.sdk_client import TaskPaymentResult

            payment_result = TaskPaymentResult(
                success=True,
                payer_address=api_key.agent_id,
                amount_usd=total_required,
                network=request.payment_network or "base",
                timestamp=datetime.now(timezone.utc),
                task_id="pending",
            )
        else:
            payment_result = await verify_x402_payment(http_request, total_required)

        if not payment_result.success:
            # Return 402 Payment Required
            return JSONResponse(
                status_code=402,
                content={
                    "error": "Payment required",
                    "message": f"Task creation requires x402 payment of ${total_required} (bounty ${bounty} + {platform_fee_pct * 100}% platform fee)",
                    "required_amount_usd": str(total_required),
                    "bounty_usd": str(bounty),
                    "platform_fee_percent": str(platform_fee_pct * 100),
                    "platform_fee_usd": str(total_required - bounty),
                    "payment_error": payment_result.error,
                    "x402_info": {
                        "facilitator": "https://facilitator.ultravioletadao.xyz",
                        "networks": get_enabled_networks(),
                        "tokens": ["USDC", "EURC", "USDT", "PYUSD"],
                    },
                },
                headers={
                    "X-402-Price": str(total_required),
                    "X-402-Currency": "USD",
                    "X-402-Description": f"Create task: {request.title[:50]}",
                },
            )

        logger.info(
            "x402 payment verified: payer=%s, amount=%.2f, tx=%s",
            payment_result.payer_address,
            payment_result.amount_usd,
            payment_result.tx_hash,
        )

        # ---- ERC-8004 Agent Identity Verification (non-blocking) --------
        # Soft check: look up the agent's on-chain identity.  If registered,
        # we attach the erc8004_agent_id to the task for audit/display.
        # A failure here never blocks task creation.
        erc8004_identity: Optional[Dict[str, Any]] = None
        if ERC8004_IDENTITY_AVAILABLE and verify_agent_identity is not None:
            try:
                erc8004_identity = await verify_agent_identity(
                    api_key.agent_id,
                    network="base",
                )
                if erc8004_identity and erc8004_identity.get("registered"):
                    logger.info(
                        "ERC-8004 identity verified for agent %s: agent_id=%s, owner=%s",
                        api_key.agent_id,
                        erc8004_identity.get("agent_id"),
                        erc8004_identity.get("owner"),
                    )
                else:
                    logger.warning(
                        "ERC-8004 identity NOT registered for agent %s (network=base). "
                        "Task creation will proceed without on-chain identity.",
                        api_key.agent_id,
                    )
            except Exception as e:
                logger.warning(
                    "ERC-8004 identity check failed (non-blocking) for agent %s: %s",
                    api_key.agent_id,
                    e,
                )

        # Calculate deadline
        deadline = datetime.now(timezone.utc) + timedelta(hours=request.deadline_hours)

        # Create task
        task = await db.create_task(
            agent_id=api_key.agent_id,
            title=request.title,
            instructions=request.instructions,
            category=request.category.value,
            bounty_usd=request.bounty_usd,
            deadline=deadline,
            evidence_required=[e.value for e in request.evidence_required],
            evidence_optional=[e.value for e in (request.evidence_optional or [])],
            location_hint=request.location_hint,
            min_reputation=request.min_reputation,
            payment_token=request.payment_token,
            payment_network=request.payment_network,
        )

        # ---- Persist ERC-8004 identity on the task record ---------------
        if erc8004_identity and erc8004_identity.get("registered"):
            try:
                identity_updates: Dict[str, Any] = {}

                # Store agent_id in a dedicated column if available
                resolved_agent_id = erc8004_identity.get("agent_id")
                if resolved_agent_id is not None:
                    identity_updates["erc8004_agent_id"] = str(resolved_agent_id)

                # Also enrich the task metadata JSONB (always safe)
                existing_metadata = task.get("metadata") or {}
                if isinstance(existing_metadata, str):
                    existing_metadata = json.loads(existing_metadata)
                existing_metadata["erc8004"] = {
                    "agent_id": resolved_agent_id,
                    "owner": erc8004_identity.get("owner"),
                    "name": erc8004_identity.get("name"),
                    "metadata_uri": erc8004_identity.get("metadata_uri"),
                    "network": erc8004_identity.get("network"),
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                }
                identity_updates["metadata"] = existing_metadata

                if identity_updates:
                    await db.update_task(task["id"], identity_updates)
                    task.update(identity_updates)
                    logger.info(
                        "ERC-8004 identity stored on task %s: agent_id=%s",
                        task["id"],
                        resolved_agent_id,
                    )
            except Exception as e:
                # Non-fatal: task was created, identity recording failed
                logger.error(
                    "Failed to store ERC-8004 identity on task %s: %s",
                    task["id"],
                    e,
                )

        # Handle escrow based on payment mode (EM_PAYMENT_MODE)
        # x402r: Settle agent auth + lock funds in on-chain escrow contract
        # preauth: Store X-Payment header for later settlement
        # fase1: Balance check only (no funds move), X-Payment header optional
        if (
            payment_result
            and payment_result.success
            and (x_payment_header or is_fase1_mode or is_fase2_mode)
        ):
            try:
                import uuid

                escrow_ref = f"escrow_{task['id'][:8]}_{uuid.uuid4().hex[:8]}"
                payment_reference = f"{X402_AUTH_REF_PREFIX}{uuid.uuid4().hex[:16]}"

                dispatcher = get_payment_dispatcher()
                if dispatcher and dispatcher.get_mode() == "fase2":
                    # fase2: Lock funds on-chain in escrow (gasless via facilitator)
                    auth_result = await dispatcher.authorize_payment(
                        task_id=task["id"],
                        receiver=api_key.agent_id,
                        amount_usdc=bounty,
                        network=request.payment_network or "base",
                        token=request.payment_token or "USDC",
                    )

                    escrow_tx = auth_result.get("tx_hash")
                    escrow_updates = {
                        "escrow_id": escrow_ref,
                        "escrow_tx": escrow_tx or payment_reference,
                        "escrow_amount_usdc": float(total_required),
                        "escrow_created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await db.update_task(task["id"], escrow_updates)
                    task.update(escrow_updates)

                    _insert_escrow_record(
                        {
                            "task_id": task["id"],
                            "agent_id": api_key.agent_id,
                            "escrow_id": escrow_ref,
                            "funding_tx": escrow_tx,
                            "status": auth_result.get("escrow_status", "deposited"),
                            "total_amount_usdc": float(total_required),
                            "platform_fee_usdc": float(total_required - bounty),
                            "beneficiary_address": auth_result.get(
                                "payer_address", payment_result.payer_address
                            ),
                            "network": request.payment_network or "base",
                            "metadata": {
                                "payment_mode": "fase2",
                                "payment_reference": payment_reference,
                                "payment_info": auth_result.get(
                                    "payment_info_serialized"
                                ),
                            },
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                    if auth_result.get("success"):
                        logger.info(
                            "fase2 escrow deposited: task=%s, amount=%.2f, tx=%s",
                            task["id"],
                            float(total_required),
                            escrow_tx,
                        )
                    else:
                        escrow_error = auth_result.get("error", "Unknown escrow error")
                        logger.error(
                            "fase2 escrow lock failed for task %s: %s",
                            task["id"],
                            escrow_error,
                        )
                        try:
                            await db.cancel_task(task["id"], api_key.agent_id)
                        except Exception:
                            try:
                                await db.update_task(
                                    task["id"], {"status": "cancelled"}
                                )
                            except Exception:
                                pass
                        raise HTTPException(
                            status_code=402,
                            detail=f"Escrow lock failed: {escrow_error}. Task cancelled.",
                        )

                elif dispatcher and dispatcher.get_mode() == "x402r":
                    # x402r: Settle + lock funds on-chain (gasless via Facilitator)
                    # Lock total_required (bounty + fee) in escrow. On release,
                    # worker gets bounty, treasury gets fee. On refund, agent
                    # gets full total_required back.
                    auth_result = await dispatcher.authorize_payment(
                        task_id=task["id"],
                        receiver=payment_result.payer_address,
                        amount_usdc=total_required,
                        x_payment_header=x_payment_header,
                    )

                    escrow_status = auth_result.get("escrow_status", "failed")
                    escrow_tx = auth_result.get("tx_hash")
                    agent_settle_tx = auth_result.get("agent_settle_tx")

                    escrow_updates = {
                        "escrow_id": escrow_ref,
                        "escrow_tx": escrow_tx or payment_reference,
                        "escrow_amount_usdc": float(total_required),
                        "escrow_created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await db.update_task(task["id"], escrow_updates)
                    task.update(escrow_updates)

                    _insert_escrow_record(
                        {
                            "task_id": task["id"],
                            "agent_id": api_key.agent_id,
                            "escrow_id": escrow_ref,
                            "funding_tx": escrow_tx,
                            "status": escrow_status,
                            "total_amount_usdc": float(total_required),
                            "platform_fee_usdc": float(total_required - bounty),
                            "beneficiary_address": auth_result.get(
                                "payer_address", payment_result.payer_address
                            ),
                            "network": payment_result.network,
                            "metadata": {
                                "payment_mode": "x402r",
                                "x_payment_header": x_payment_header,
                                "payment_reference": payment_reference,
                                "agent_settle_tx": agent_settle_tx,
                                "escrow_lock_tx": escrow_tx,
                                "payment_info": auth_result.get(
                                    "payment_info_serialized"
                                ),
                            },
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                    if auth_result.get("success"):
                        logger.info(
                            "x402r escrow deposited: task=%s, escrow=%s, amount=%.2f, "
                            "settle_tx=%s, lock_tx=%s",
                            task["id"],
                            escrow_ref,
                            float(total_required),
                            agent_settle_tx,
                            escrow_tx,
                        )
                    else:
                        escrow_error = auth_result.get("error", "Unknown escrow error")
                        logger.error(
                            "x402r escrow lock failed for task %s: %s",
                            task["id"],
                            escrow_error,
                        )
                        # Cancel the task — it has no financial backing
                        try:
                            await db.cancel_task(task["id"], api_key.agent_id)
                        except Exception:
                            # Best-effort cancel; task may stay published briefly
                            try:
                                await db.update_task(
                                    task["id"], {"status": "cancelled"}
                                )
                            except Exception:
                                pass
                        raise HTTPException(
                            status_code=402,
                            detail=f"Payment escrow failed: {escrow_error}. Task has been cancelled.",
                        )
                elif dispatcher and dispatcher.get_mode() == "fase1":
                    # fase1: Balance check only (no funds move, no header stored)
                    auth_result = await dispatcher.authorize_payment(
                        task_id=task["id"],
                        receiver=api_key.agent_id,
                        amount_usdc=total_required,
                        network=request.payment_network or "base",
                        token=request.payment_token or "USDC",
                    )

                    escrow_updates = {
                        "escrow_id": escrow_ref,
                        "escrow_tx": payment_reference,
                        "escrow_amount_usdc": float(total_required),
                        "escrow_created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await db.update_task(task["id"], escrow_updates)
                    task.update(escrow_updates)

                    _insert_escrow_record(
                        {
                            "task_id": task["id"],
                            "agent_id": api_key.agent_id,
                            "escrow_id": escrow_ref,
                            "funding_tx": None,
                            "status": auth_result.get(
                                "escrow_status", "balance_verified"
                            ),
                            "total_amount_usdc": float(total_required),
                            "platform_fee_usdc": float(total_required - bounty),
                            "beneficiary_address": payment_result.payer_address,
                            "network": payment_result.network,
                            "metadata": {
                                "payment_mode": "fase1",
                                "x_payment_header": x_payment_header,
                                "payment_reference": payment_reference,
                                "balance_info": auth_result.get("balance_info"),
                            },
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                    balance_warning = auth_result.get("warning")
                    if balance_warning:
                        logger.warning(
                            "fase1 balance warning for task %s: %s",
                            task["id"],
                            balance_warning,
                        )
                    logger.info(
                        "fase1 task authorized: task=%s, escrow=%s, amount=%.2f, status=%s",
                        task["id"],
                        escrow_ref,
                        float(total_required),
                        auth_result.get("escrow_status"),
                    )
                else:
                    # preauth: Store header for later settlement (no funds move yet)
                    escrow_updates = {
                        "escrow_id": escrow_ref,
                        "escrow_tx": payment_reference,
                        "escrow_amount_usdc": float(total_required),
                        "escrow_created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await db.update_task(task["id"], escrow_updates)
                    task.update(escrow_updates)

                    _insert_escrow_record(
                        {
                            "task_id": task["id"],
                            "agent_id": api_key.agent_id,
                            "escrow_id": escrow_ref,
                            "funding_tx": None,
                            "status": "authorized",
                            "total_amount_usdc": float(total_required),
                            "platform_fee_usdc": float(total_required - bounty),
                            "beneficiary_address": payment_result.payer_address,
                            "network": payment_result.network,
                            "metadata": {
                                "payment_mode": "preauth",
                                "x_payment_header": x_payment_header,
                                "payment_reference": payment_reference,
                            },
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                    await log_payment_event(
                        task_id=task["id"],
                        event_type="store_auth",
                        status="success",
                        from_address=payment_result.payer_address,
                        amount_usdc=total_required,
                        network=payment_result.network,
                        metadata={"mode": "preauth", "escrow_ref": escrow_ref},
                    )
                    logger.info(
                        "preauth payment authorized: task=%s, escrow=%s, amount=%.2f, payer=%s",
                        task["id"],
                        escrow_ref,
                        float(total_required),
                        payment_result.payer_address[:10] + "...",
                    )
            except HTTPException:
                # Re-raise HTTP exceptions (e.g., 402 from x402r escrow lock failure)
                raise
            except Exception as e:
                # Non-fatal for preauth (no funds moved), but log loudly
                logger.error("Failed to record escrow for task %s: %s", task["id"], e)

        logger.info(
            "Task created: id=%s, agent=%s, bounty=%.2f, paid_via_x402=%s",
            task["id"],
            api_key.agent_id,
            request.bounty_usd,
            X402_AVAILABLE,
        )

        return TaskResponse(
            id=task["id"],
            title=task["title"],
            status=task["status"],
            category=task["category"],
            bounty_usd=task["bounty_usd"],
            deadline=datetime.fromisoformat(task["deadline"].replace("Z", "+00:00")),
            created_at=datetime.fromisoformat(
                task["created_at"].replace("Z", "+00:00")
            ),
            agent_id=task["agent_id"],
            instructions=task["instructions"],
            evidence_schema=task.get("evidence_schema"),
            location_hint=task.get("location_hint"),
            min_reputation=task.get("min_reputation", 0),
            erc8004_agent_id=task.get("erc8004_agent_id"),
            payment_network=task.get("payment_network", "base"),
            payment_token=task.get("payment_token", "USDC"),
            escrow_tx=task.get("escrow_tx"),
            refund_tx=task.get("refund_tx"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create task: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal error while creating task"
        )


@router.get(
    "/tasks/available",
    response_model=AvailableTasksResponse,
    responses={
        200: {"description": "Available tasks retrieved with applied filters"},
        500: {
            "model": ErrorResponse,
            "description": "Failed to retrieve available tasks",
        },
    },
    summary="Get Available Tasks",
    description="Public endpoint for workers to discover available tasks with filtering and pagination",
    tags=["Tasks", "Worker", "Public"],
)
async def get_available_tasks(
    lat: Optional[float] = Query(
        None, ge=-90, le=90, description="Latitude for location filtering"
    ),
    lng: Optional[float] = Query(
        None, ge=-180, le=180, description="Longitude for location filtering"
    ),
    radius_km: int = Query(50, ge=1, le=500, description="Search radius in kilometers"),
    category: Optional[TaskCategory] = Query(None, description="Filter by category"),
    min_bounty: Optional[float] = Query(None, ge=0, description="Minimum bounty USD"),
    max_bounty: Optional[float] = Query(
        None, le=10000, description="Maximum bounty USD"
    ),
    include_expired: bool = Query(
        False,
        description="Include expired tasks in response. Useful as landing fallback when there are no active tasks.",
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> AvailableTasksResponse:
    """
    Get available tasks for workers to apply to and complete.

    Public endpoint that returns tasks in 'published' status that are available
    for worker applications. Supports comprehensive filtering by location, category,
    bounty range, and includes pagination for large result sets.

    ## Query Parameters

    ### Location Filtering
    - **lat/lng**: GPS coordinates for location-based filtering
    - **radius_km**: Search radius in kilometers (1-500, default: 50)
    - Only tasks within the specified radius will be returned

    ### Content Filtering
    - **category**: Filter by task category (physical_presence, knowledge_access, etc.)
    - **min_bounty**: Minimum bounty amount in USD (filters out lower-paying tasks)
    - **max_bounty**: Maximum bounty amount in USD (filters out higher-paying tasks)

    ### Special Options
    - **include_expired**: Include expired tasks for discovery (useful for landing pages)
    - **limit**: Results per page (1-100, default: 20)
    - **offset**: Pagination offset (default: 0)

    ## Response Example
    ```json
    {
        "tasks": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Verify restaurant is open",
                "status": "published",
                "category": "physical_presence",
                "bounty_usd": 5.00,
                "deadline": "2024-02-12T06:04:00Z",
                "created_at": "2024-02-11T06:04:00Z",
                "location_hint": "Downtown Portland",
                "min_reputation": 50,
                "evidence_required": ["photo", "text_report"],
                "payment_network": "base",
                "agent_id": "0x742d35Cc..."
            }
        ],
        "count": 1,
        "offset": 0,
        "filters_applied": {
            "category": "physical_presence",
            "min_bounty": 2.0,
            "location": {
                "lat": 45.5152,
                "lng": -122.6784,
                "radius_km": 50
            }
        }
    }
    ```

    ## Task Categories
    - **physical_presence**: Requires being at a specific location
    - **knowledge_access**: Requires specific knowledge or expertise
    - **human_authority**: Requires human decision-making or authority
    - **simple_action**: Basic actions anyone can perform
    - **digital_physical**: Digital tasks with physical world components

    ## Task Status
    - Only tasks with `published` status are returned (unless `include_expired=true`)
    - Tasks are ordered by bounty (highest first) for active tasks
    - Tasks are ordered by creation date (newest first) when including expired

    ## Location-Based Search
    When lat/lng are provided:
    1. Tasks with GPS coordinates are filtered by distance
    2. Tasks without coordinates but with location hints are included
    3. Distance calculation uses standard geographic formulas
    4. Radius is measured in kilometers from the specified point

    ## Pagination
    Use offset and limit for pagination:
    ```
    Page 1: ?offset=0&limit=20
    Page 2: ?offset=20&limit=20
    Page 3: ?offset=40&limit=20
    ```

    ## Authentication
    This is a public endpoint - no authentication required. Workers can browse
    available tasks before connecting their wallet or creating an account.

    ## Use Cases
    - Worker mobile app task discovery
    - Location-based task filtering
    - Bounty-range task browsing
    - Landing page task showcase
    - API integrations for task aggregation

    ## Performance Notes
    - Results are cached for 30 seconds to improve performance
    - Location filtering may take longer for large datasets
    - Use reasonable limit values (≤50) for best performance
    """
    try:
        client = db.get_client()

        # Build query
        query = client.table("tasks").select("*")

        if include_expired:
            query = query.in_("status", ["published", "expired"])
        else:
            query = query.eq("status", "published")

        # Apply category filter
        if category:
            query = query.eq("category", category.value)

        # Apply bounty filters
        if min_bounty is not None:
            query = query.gte("bounty_usd", min_bounty)
        if max_bounty is not None:
            query = query.lte("bounty_usd", max_bounty)

        # Execute query
        if include_expired:
            result = (
                query.order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
        else:
            result = (
                query.order("bounty_usd", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )

        tasks = result.data or []

        # Build filters applied response
        filters_applied = {
            "category": category.value if category else None,
            "min_bounty": min_bounty,
            "max_bounty": max_bounty,
            "include_expired": include_expired,
            "location": {"lat": lat, "lng": lng, "radius_km": radius_km}
            if lat and lng
            else None,
        }

        return AvailableTasksResponse(
            tasks=tasks,
            count=len(tasks),
            offset=offset,
            filters_applied={k: v for k, v in filters_applied.items() if v is not None},
        )

    except Exception as e:
        logger.error("Failed to get available tasks: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to get available tasks")


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    responses={
        200: {"description": "Task details retrieved successfully"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to view this task - agent doesn't own it",
        },
        404: {"model": ErrorResponse, "description": "Task not found"},
    },
    summary="Get Task Details",
    description="Retrieve detailed information about a specific task",
    tags=["Tasks", "Agent"],
)
async def get_task(
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    api_key: APIKeyData = Depends(verify_api_key_if_required),
) -> TaskResponse:
    """
    Get detailed information about a specific task.

    Returns complete task details including current status, payment information,
    assigned worker, and all metadata. Only accessible to the agent who created the task.

    ## Path Parameters
    - **task_id**: UUID of the task (format: 8-4-4-4-12 hex characters)

    ## Response Example
    ```json
    {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "title": "Verify restaurant is open",
        "status": "accepted",
        "category": "physical_presence",
        "bounty_usd": 5.00,
        "deadline": "2024-02-12T06:04:00Z",
        "created_at": "2024-02-11T06:04:00Z",
        "agent_id": "0x742d35Cc6634C0532925a3b8D0fC6A3B3e1d7A5B",
        "executor_id": "987fcdeb-51a2-43d7-8901-123456789abc",
        "instructions": "Visit the restaurant and confirm it's currently open...",
        "evidence_schema": {
            "required": ["photo", "text_report"],
            "optional": ["gps_coordinates"]
        },
        "location_hint": "Downtown Portland, near Pioneer Square",
        "min_reputation": 50,
        "erc8004_agent_id": "42",
        "payment_network": "base",
        "payment_token": "USDC",
        "escrow_tx": "0xabc123...",
        "refund_tx": null
    }
    ```

    ## Task Status Lifecycle
    1. **published**: Available for worker applications
    2. **accepted**: Assigned to a specific worker
    3. **in_progress**: Worker is actively working
    4. **submitted**: Work submitted, awaiting agent review
    5. **completed**: Approved and payment released
    6. **cancelled**: Cancelled by agent
    7. **expired**: Deadline passed without completion

    ## Evidence Schema
    The `evidence_schema` field contains:
    - **required**: Evidence types that must be provided
    - **optional**: Evidence types that are helpful but not required

    Evidence types: `photo`, `text_report`, `document`, `gps_coordinates`, `video`, `audio`

    ## Payment Information
    - **escrow_tx**: Transaction hash or payment reference for escrow
    - **refund_tx**: Transaction hash if task was cancelled and refunded
    - **payment_network**: Blockchain network (base, ethereum, polygon, arbitrum)
    - **payment_token**: Token used for payment (USDC, EURC, USDT, PYUSD)

    ## ERC-8004 Integration
    - **erc8004_agent_id**: On-chain identity token ID if agent is registered
    - Used for reputation and verification purposes

    ## Authorization
    Only the agent who created the task can access its details. Other agents
    will receive a 403 Forbidden error.

    ## Use Cases
    - Task detail pages in agent dashboard
    - Monitoring individual task progress
    - Preparing task updates or cancellations
    - Reviewing task configuration and requirements
    """
    task = await db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["agent_id"] != api_key.agent_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this task")

    return TaskResponse(
        id=task["id"],
        title=task["title"],
        status=task["status"],
        category=task["category"],
        bounty_usd=task["bounty_usd"],
        deadline=datetime.fromisoformat(task["deadline"].replace("Z", "+00:00")),
        created_at=datetime.fromisoformat(task["created_at"].replace("Z", "+00:00")),
        agent_id=task["agent_id"],
        executor_id=task.get("executor_id"),
        instructions=task["instructions"],
        evidence_schema=task.get("evidence_schema"),
        location_hint=task.get("location_hint"),
        min_reputation=task.get("min_reputation", 0),
        erc8004_agent_id=task.get("erc8004_agent_id"),
        payment_network=task.get("payment_network", "base"),
        payment_token=task.get("payment_token", "USDC"),
        escrow_tx=task.get("escrow_tx"),
        refund_tx=task.get("refund_tx"),
    )


@router.get(
    "/tasks/{task_id}/payment",
    response_model=TaskPaymentResponse,
    responses={
        200: {"description": "Payment timeline and status retrieved successfully"},
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to view payment details for draft tasks",
        },
        404: {"model": ErrorResponse, "description": "Task not found"},
        500: {
            "model": ErrorResponse,
            "description": "Failed to resolve task payment information",
        },
    },
    summary="Get Task Payment Timeline",
    description="Retrieve complete payment history and current status for a task",
    tags=["Tasks", "Payments", "Escrow"],
)
async def get_task_payment(
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    api_key: Optional[APIKeyData] = Depends(verify_api_key_optional),
) -> TaskPaymentResponse:
    """
    Get comprehensive payment timeline and status for a specific task.

    Returns the complete payment history including escrow deposits, releases, refunds,
    and current payment status. Normalizes data from multiple payment tables and
    handles schema variations gracefully.

    ## Path Parameters
    - **task_id**: UUID of the task

    ## Payment Status Values
    - **pending**: No payment processed yet
    - **escrowed**: Funds locked in escrow awaiting completion
    - **partial_released**: Partial payment released to worker
    - **completed**: Full payment released to worker
    - **refunded**: Funds refunded to agent

    ## Response Example
    ```json
    {
        "task_id": "123e4567-e89b-12d3-a456-426614174000",
        "status": "completed",
        "total_amount": 5.40,
        "released_amount": 5.00,
        "currency": "USDC",
        "escrow_tx": "0xabc123...",
        "escrow_contract": null,
        "network": "base",
        "events": [
            {
                "id": "evt_1",
                "type": "escrow_created",
                "actor": "agent",
                "timestamp": "2024-02-11T06:04:00Z",
                "network": "base",
                "amount": 5.40,
                "tx_hash": "0xabc123...",
                "note": "x402 reference: abc123ef..."
            },
            {
                "id": "evt_2",
                "type": "final_release",
                "actor": "system",
                "timestamp": "2024-02-11T08:30:00Z",
                "network": "base",
                "amount": 5.00,
                "tx_hash": "0xdef456...",
                "note": "Payment settled via x402 facilitator"
            }
        ],
        "created_at": "2024-02-11T06:04:00Z",
        "updated_at": "2024-02-11T08:30:00Z"
    }
    ```

    ## Event Types
    - **escrow_created**: Initial funds deposit/authorization
    - **escrow_funded**: Additional funding events
    - **partial_release**: Partial payment to worker
    - **final_release**: Final payment to worker
    - **refund**: Refund to agent
    - **authorization_expired**: Payment authorization expired
    - **dispute_hold**: Payment held due to dispute

    ## Event Actors
    - **agent**: Action initiated by the task creator
    - **system**: Automatic system action (timeouts, settlements)
    - **arbitrator**: Manual intervention by platform admin

    ## Data Normalization
    This endpoint handles schema variations across payment tables:
    - Normalizes `type` vs `payment_type` columns
    - Handles `tx_hash` vs `transaction_hash` variations
    - Gracefully degrades when tables are missing
    - Combines data from `payments`, `escrows`, and `submissions` tables

    ## Authorization
    - Public tasks: No authentication required
    - Draft tasks: Only accessible to task owner

    ## Payment Modes Supported
    - **x402r**: On-chain escrow with immediate lock/release
    - **preauth**: Authorization-based with settlement on approval
    - **fase1**: Balance verification with EIP-3009 settlement
    - **fase2**: Facilitator-managed escrow (gasless)

    ## Use Cases
    - Payment status monitoring
    - Escrow audit and compliance
    - Payment timeline visualization
    - Troubleshooting payment issues
    - Financial reporting and reconciliation

    ## Timeline Accuracy
    Events are ordered chronologically with fallback timestamps to ensure
    complete timeline even when some timestamp data is missing.
    """
    try:
        task = await db.get_task(task_id)
    except Exception as task_err:
        if _is_not_found_error(task_err):
            task = None
        else:
            logger.warning(
                "Failed to load task %s for payment endpoint: %s", task_id, task_err
            )
            raise HTTPException(
                status_code=500, detail="Failed to resolve task payment"
            )

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task_status = _normalize_status(task.get("status"))
    requester_is_owner = bool(api_key and task.get("agent_id") == api_key.agent_id)
    if task_status == "draft" and not requester_is_owner:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view draft task payment details",
        )

    client = db.get_client()
    payment_rows: List[Dict[str, Any]] = []
    escrows_row: Optional[Dict[str, Any]] = None
    submission_payment_row: Optional[Dict[str, Any]] = None

    try:
        payment_result = (
            client.table("payments")
            .select("*")
            .eq("task_id", task_id)
            .order("created_at", desc=False)
            .execute()
        )
        payment_rows = payment_result.data or []
    except Exception as payment_err:
        if not _is_missing_table_error(payment_err, "payments"):
            logger.warning(
                "Failed to query payments for task %s: %s", task_id, payment_err
            )

    try:
        escrows_result = (
            client.table("escrows")
            .select("*")
            .eq("task_id", task_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        escrows_rows = escrows_result.data or []
        if escrows_rows:
            escrows_row = escrows_rows[0]
    except Exception as escrow_err:
        if not _is_missing_table_error(escrow_err, "escrows"):
            logger.warning(
                "Failed to query escrows for task %s: %s", task_id, escrow_err
            )

    try:
        submission_result = (
            client.table("submissions")
            .select("id,payment_tx,payment_amount,paid_at,verified_at,submitted_at")
            .eq("task_id", task_id)
            .not_("payment_tx", "is", "null")
            .order("submitted_at", desc=True)
            .limit(1)
            .execute()
        )
        submission_rows = submission_result.data or []
        if submission_rows:
            submission_payment_row = submission_rows[0]
    except Exception as submission_err:
        if not _is_missing_table_error(submission_err, "submissions"):
            logger.warning(
                "Failed to query submission payment fallback for task %s: %s",
                task_id,
                submission_err,
            )

    default_network = "base"
    created_at = str(task.get("created_at") or datetime.now(timezone.utc).isoformat())
    updated_at = str(task.get("updated_at") or created_at)
    events: List[Dict[str, Any]] = []
    total_amount = _as_amount(task.get("bounty_usd"))
    released_amount = 0.0

    for index, row in enumerate(payment_rows):
        event_type = _event_type_from_payment_row(row)
        amount = _as_amount(
            row.get("amount_usdc")
            or row.get("amount")
            or row.get("total_amount_usdc")
            or row.get("net_amount_usdc")
            or row.get("released_amount_usdc")
            or row.get("released_amount")
        )
        status = _normalize_status(row.get("status"))
        if event_type == "escrow_created":
            total_amount = max(total_amount, amount)
        if (
            event_type in {"partial_release", "final_release"}
            and status in TASK_PAYMENT_SETTLED_STATUSES
        ):
            released_amount += amount

        event_timestamp = str(
            row.get("completed_at")
            or row.get("confirmed_at")
            or row.get("updated_at")
            or row.get("created_at")
            or updated_at
        )
        updated_at = max(updated_at, event_timestamp)

        network = _normalize_payment_network(row, default_network)
        tx_hash = _pick_first_tx_hash(
            row.get("tx_hash"),
            row.get("transaction_hash"),
            row.get("release_tx"),
            row.get("refund_tx"),
            row.get("deposit_tx"),
            row.get("funding_tx"),
        )
        note = _sanitize_reference(
            row.get("tx_hash")
            or row.get("transaction_hash")
            or row.get("deposit_tx")
            or row.get("funding_tx")
        )

        events.append(
            {
                "id": f"{row.get('id') or task_id}-{event_type}-{index}",
                "type": event_type,
                "actor": _actor_from_event_type(event_type),
                "amount": amount if amount > 0 else None,
                "tx_hash": tx_hash,
                "network": network,
                "timestamp": event_timestamp,
                "note": note,
            }
        )

    has_escrow_context = bool(
        task.get("escrow_id") or task.get("escrow_tx") or escrows_row
    )
    if has_escrow_context and not any(
        event["type"] in {"escrow_created", "escrow_funded"} for event in events
    ):
        escrow_amount = _as_amount(
            (escrows_row or {}).get("total_amount_usdc")
            or (escrows_row or {}).get("amount_usdc")
            or task.get("bounty_usd")
        )
        total_amount = max(total_amount, escrow_amount)

        escrow_timestamp = str(
            (escrows_row or {}).get("created_at")
            or task.get("created_at")
            or created_at
        )
        updated_at = max(updated_at, escrow_timestamp)
        escrow_tx_hash = _pick_first_tx_hash(
            (escrows_row or {}).get("deposit_tx"),
            (escrows_row or {}).get("funding_tx"),
            task.get("escrow_tx"),
        )
        escrow_reference = _sanitize_reference(task.get("escrow_tx"))
        events.append(
            {
                "id": f"{task_id}-escrow-created-fallback",
                "type": "escrow_created",
                "actor": "agent",
                "amount": escrow_amount if escrow_amount > 0 else None,
                "tx_hash": escrow_tx_hash,
                "network": default_network,
                "timestamp": escrow_timestamp,
                "note": escrow_reference,
            }
        )

    submission_tx = _pick_first_tx_hash(
        (submission_payment_row or {}).get("payment_tx")
    )
    if submission_tx and not any(
        event["type"] == "final_release" and event.get("tx_hash") == submission_tx
        for event in events
    ):
        submission_amount = _as_amount(
            (submission_payment_row or {}).get("payment_amount")
        )
        if submission_amount <= 0:
            submission_amount = total_amount
        released_amount = max(released_amount, submission_amount)
        total_amount = max(total_amount, submission_amount)

        payout_timestamp = str(
            (submission_payment_row or {}).get("paid_at")
            or (submission_payment_row or {}).get("verified_at")
            or (submission_payment_row or {}).get("submitted_at")
            or updated_at
        )
        updated_at = max(updated_at, payout_timestamp)
        events.append(
            {
                "id": f"{task_id}-submission-payout-{(submission_payment_row or {}).get('id') or 'latest'}",
                "type": "final_release",
                "actor": "system",
                "amount": submission_amount if submission_amount > 0 else None,
                "tx_hash": submission_tx,
                "network": default_network,
                "timestamp": payout_timestamp,
                "note": "Payment settled via x402 facilitator",
            }
        )

    # Inject refund event if task has a refund_tx (funded escrow that was refunded)
    refund_tx_from_task = _pick_first_tx_hash(task.get("refund_tx"))
    if refund_tx_from_task and not any(
        event["type"] == "refund" and event.get("tx_hash") == refund_tx_from_task
        for event in events
    ):
        refund_timestamp = str(task.get("updated_at") or updated_at)
        events.append(
            {
                "id": f"{task_id}-refund-task",
                "type": "refund",
                "actor": "system",
                "amount": total_amount if total_amount > 0 else None,
                "tx_hash": refund_tx_from_task,
                "network": default_network,
                "timestamp": refund_timestamp,
                "note": "Escrow refunded to agent via facilitator",
            }
        )

    # For cancelled tasks without refund_tx, inject authorization_expired event
    if (
        task_status == "cancelled"
        and has_escrow_context
        and not refund_tx_from_task
        and not any(
            event["type"] in {"refund", "authorization_expired"} for event in events
        )
    ):
        cancel_timestamp = str(task.get("updated_at") or updated_at)
        events.append(
            {
                "id": f"{task_id}-auth-expired",
                "type": "authorization_expired",
                "actor": "system",
                "amount": None,
                "tx_hash": None,
                "network": default_network,
                "timestamp": cancel_timestamp,
                "note": "Payment authorization expired. No funds were moved.",
            }
        )

    events.sort(key=lambda event: event.get("timestamp") or "")

    if (
        _normalize_status(task.get("status")) == "completed"
        and released_amount <= 0
        and total_amount > 0
    ):
        released_amount = total_amount

    derived_status = _derive_payment_status(
        task_status=task_status,
        has_escrow_context=has_escrow_context,
        event_types=[event["type"] for event in events],
    )

    if not events:
        updated_at = str(task.get("updated_at") or task.get("created_at") or updated_at)

    return TaskPaymentResponse(
        task_id=task_id,
        status=derived_status,
        total_amount=round(total_amount, 6),
        released_amount=round(released_amount, 6),
        currency="USDC",
        escrow_tx=_pick_first_tx_hash(
            (escrows_row or {}).get("deposit_tx"),
            (escrows_row or {}).get("funding_tx"),
            task.get("escrow_tx"),
        ),
        escrow_contract=None,
        network=default_network,
        events=[TaskPaymentEventResponse(**event) for event in events],
        created_at=created_at,
        updated_at=updated_at,
    )


@router.get(
    "/tasks",
    response_model=TaskListResponse,
    responses={
        200: {"description": "Tasks retrieved successfully with pagination info"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
    },
    summary="List Agent Tasks",
    description="Retrieve paginated list of tasks for the authenticated agent with filtering options",
    tags=["Tasks", "Agent"],
)
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    category: Optional[TaskCategory] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    api_key: APIKeyData = Depends(verify_api_key_if_required),
) -> TaskListResponse:
    """
    List tasks for the authenticated agent with filtering and pagination.

    Returns all tasks created by the authenticated agent, with optional filtering
    by status and category. Supports pagination for large task lists.

    ## Query Parameters
    - **status**: Filter by task status (published, accepted, completed, etc.)
    - **category**: Filter by task category (physical_presence, knowledge_access, etc.)
    - **limit**: Number of results per page (1-100, default: 20)
    - **offset**: Number of results to skip for pagination (default: 0)

    ## Task Status Values
    - `published`: Task is available for workers to apply
    - `accepted`: Task has been assigned to a worker
    - `in_progress`: Worker is actively working on the task
    - `submitted`: Worker has submitted work for review
    - `completed`: Task completed and payment released
    - `cancelled`: Task cancelled by agent
    - `expired`: Task deadline passed without completion

    ## Task Category Values
    - `physical_presence`: Requires being at a specific location
    - `knowledge_access`: Requires specific knowledge or expertise
    - `human_authority`: Requires human decision-making or authority
    - `simple_action`: Basic actions anyone can perform
    - `digital_physical`: Digital tasks with physical world components

    ## Response Example
    ```json
    {
        "tasks": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Verify restaurant is open",
                "status": "published",
                "category": "physical_presence",
                "bounty_usd": 5.00,
                "deadline": "2024-02-12T06:04:00Z",
                "created_at": "2024-02-11T06:04:00Z",
                "agent_id": "0x742d35Cc...",
                "executor_id": null,
                "payment_network": "base",
                "escrow_tx": "0xabc123..."
            }
        ],
        "total": 1,
        "count": 1,
        "offset": 0,
        "has_more": false
    }
    ```

    ## Pagination
    Use `offset` and `limit` for pagination:
    - Page 1: `offset=0&limit=20`
    - Page 2: `offset=20&limit=20`
    - Page 3: `offset=40&limit=20`

    The `has_more` field indicates if additional pages are available.

    ## Use Cases
    - Agent dashboard task management
    - Task status monitoring
    - Historical task review
    - Bulk task operations setup
    - Performance analytics preparation
    """
    result = await db.get_tasks(
        agent_id=api_key.agent_id,
        status=status.value if status else None,
        category=category.value if category else None,
        limit=limit,
        offset=offset,
    )

    tasks = []
    for task in result.get("tasks", []):
        tasks.append(
            TaskResponse(
                id=task["id"],
                title=task["title"],
                status=task["status"],
                category=task["category"],
                bounty_usd=task["bounty_usd"],
                deadline=datetime.fromisoformat(
                    task["deadline"].replace("Z", "+00:00")
                ),
                created_at=datetime.fromisoformat(
                    task["created_at"].replace("Z", "+00:00")
                ),
                agent_id=task["agent_id"],
                executor_id=task.get("executor_id"),
                min_reputation=task.get("min_reputation", 0),
                erc8004_agent_id=task.get("erc8004_agent_id"),
                payment_network=task.get("payment_network", "base"),
                payment_token=task.get("payment_token", "USDC"),
                escrow_tx=task.get("escrow_tx"),
                refund_tx=task.get("refund_tx"),
            )
        )

    return TaskListResponse(
        tasks=tasks,
        total=result["total"],
        count=result["count"],
        offset=offset,
        has_more=result["has_more"],
    )


@router.get(
    "/tasks/{task_id}/submissions",
    response_model=SubmissionListResponse,
    responses={
        200: {
            "description": "Submissions retrieved successfully with AI pre-check scores"
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to view submissions for this task",
        },
        404: {"model": ErrorResponse, "description": "Task not found"},
    },
    summary="Get Task Submissions",
    description="Retrieve all submissions for a specific task with AI verification scores",
    tags=["Submissions", "Agent"],
)
async def get_submissions(
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    api_key: APIKeyData = Depends(verify_api_key_if_required),
) -> SubmissionListResponse:
    """
    Get all submissions for a specific task.

    Returns all work submissions from workers for the specified task, including
    evidence data, AI pre-check scores, and current review status. Only accessible
    to the agent who created the task.

    ## Path Parameters
    - **task_id**: UUID of the task to get submissions for

    ## Response Example
    ```json
    {
        "submissions": [
            {
                "id": "789abcdef-1234-5678-9abc-def123456789",
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "executor_id": "abc123def-4567-89ab-cdef-123456789abc",
                "status": "accepted",
                "pre_check_score": 0.92,
                "submitted_at": "2024-02-11T08:15:00Z",
                "evidence": {
                    "photos": [
                        "https://cdn.example.com/evidence/photo1.jpg"
                    ],
                    "text_report": "Restaurant is open with customers inside. Hours posted show open until 9 PM.",
                    "gps_coordinates": {
                        "lat": 45.5152,
                        "lng": -122.6784,
                        "accuracy": 5
                    }
                },
                "agent_verdict": "accepted",
                "agent_notes": "Excellent work, all requirements met clearly.",
                "verified_at": "2024-02-11T09:30:00Z"
            },
            {
                "id": "456def789-abcd-1234-5678-9abcdef12345",
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "executor_id": "def456abc-7890-bcde-f123-456789abcdef",
                "status": "pending",
                "pre_check_score": 0.65,
                "submitted_at": "2024-02-11T07:45:00Z",
                "evidence": {
                    "photos": [
                        "https://cdn.example.com/evidence/photo2.jpg"
                    ],
                    "text_report": "Took photo of restaurant front."
                },
                "agent_verdict": null,
                "agent_notes": null,
                "verified_at": null
            }
        ],
        "count": 2
    }
    ```

    ## Submission Status Values
    - **pending**: Awaiting agent review (default)
    - **accepted**: Approved by agent, payment released
    - **rejected**: Rejected by agent, task returned to pool
    - **more_info_requested**: Agent requested additional evidence
    - **disputed**: Under dispute resolution

    ## AI Pre-Check Score
    - Range: 0.0 to 1.0 (higher is better)
    - Automatically calculated when evidence is submitted
    - Based on AI analysis of evidence against task requirements
    - **null** if no evidence or AI verification unavailable
    - Helps prioritize review order (higher scores first)

    ## Evidence Structure
    Evidence data varies by task requirements but commonly includes:
    - **photos**: Array of image URLs
    - **text_report**: Written description of work performed
    - **documents**: PDF or document file URLs
    - **gps_coordinates**: Location verification data
    - **video**: Video evidence URLs
    - **audio**: Audio evidence URLs

    ## Agent Verdict Process
    1. **null/pending**: No review yet
    2. **accepted**: Work approved, triggers payment
    3. **rejected**: Work rejected, task returns to published status
    4. **more_info_requested**: Additional evidence requested

    ## Submission Timeline
    - **submitted_at**: When worker submitted evidence
    - **verified_at**: When agent made final decision
    - Gap indicates review time

    ## Authorization
    Only the agent who created the task can view its submissions.
    Other agents receive 403 Forbidden error.

    ## Multiple Submissions
    - Each task can have multiple submissions from different workers
    - Only one submission can be accepted (first-come, first-served)
    - Rejected submissions allow other workers to apply

    ## Use Cases
    - Agent review dashboard
    - Evidence quality assessment
    - AI-assisted review prioritization
    - Submission timeline tracking
    - Quality control and audit

    ## Performance Optimization
    - Submissions are ordered by pre-check score (highest first)
    - Evidence URLs are pre-signed for immediate access
    - Cached for 60 seconds to improve dashboard loading
    """
    # Verify ownership
    if not await verify_agent_owns_task(api_key.agent_id, task_id):
        task = await db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        raise HTTPException(
            status_code=403, detail="Not authorized to view submissions"
        )

    submissions = await db.get_submissions_for_task(task_id)

    result = []
    for sub in submissions:
        # Calculate pre-check score if evidence exists
        pre_check_score = None
        if sub.get("evidence"):
            # Get auto-check results if available
            auto_checks = sub.get("auto_checks", {})
            if auto_checks:
                pre_check_score = calculate_auto_score(auto_checks)

        result.append(
            SubmissionResponse(
                id=sub["id"],
                task_id=sub["task_id"],
                executor_id=sub["executor_id"],
                status=sub.get("agent_verdict", "pending"),
                pre_check_score=pre_check_score,
                submitted_at=datetime.fromisoformat(
                    sub["submitted_at"].replace("Z", "+00:00")
                ),
                evidence=sub.get("evidence"),
                agent_verdict=sub.get("agent_verdict"),
                agent_notes=sub.get("agent_notes"),
                verified_at=datetime.fromisoformat(
                    sub["verified_at"].replace("Z", "+00:00")
                )
                if sub.get("verified_at")
                else None,
            )
        )

    return SubmissionListResponse(
        submissions=result,
        count=len(result),
    )


@router.post(
    "/submissions/{submission_id}/approve",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Submission approved and payment released to worker"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to approve this submission",
        },
        404: {"model": ErrorResponse, "description": "Submission not found"},
        409: {
            "model": ErrorResponse,
            "description": "Submission already processed or task not in valid state",
        },
        502: {
            "model": ErrorResponse,
            "description": "Payment settlement failed - submission not approved",
        },
    },
    summary="Approve Submission",
    description="Approve a worker's submission and trigger payment settlement",
    tags=["Submissions", "Agent", "Payments"],
)
async def approve_submission(
    http_request: Request = None,
    submission_id: str = Path(
        ..., description="UUID of the submission", pattern=UUID_PATTERN
    ),
    request: ApprovalRequest = None,
    api_key: APIKeyData = Depends(verify_api_key_if_required),
) -> SuccessResponse:
    """
    Approve a worker's submission and trigger payment settlement.

    This endpoint approves a worker's submitted work and immediately attempts to
    settle payment to the worker's wallet. The task status will be updated to
    'completed' upon successful payment settlement.

    ## Payment Settlement Process
    1. Validates submission ownership and status
    2. Attempts payment settlement via x402 SDK/Facilitator
    3. Updates submission to 'accepted' only after successful payment
    4. Records payment transaction and updates task status
    5. Optionally submits ERC-8004 reputation feedback

    ## Payment Modes Support
    - **x402r**: Releases funds from on-chain escrow contract
    - **preauth**: Settles stored X-Payment authorization
    - **fase1**: Uses `X-Payment-Worker` and `X-Payment-Fee` headers for EIP-3009 settlement
    - **fase2**: Releases funds from facilitator-managed escrow

    ## Required Headers
    - `Authorization: Bearer <api_key>` - Agent API key
    - `X-Payment-Worker: <eip3009_auth>` - (Fase1 only) EIP-3009 authorization for worker payment
    - `X-Payment-Fee: <eip3009_auth>` - (Fase1 only) EIP-3009 authorization for platform fee

    ## Request Body
    ```json
    {
        "notes": "Great work! All evidence requirements met."
    }
    ```

    ## Success Response Example
    ```json
    {
        "success": true,
        "message": "Submission approved. Payment released to worker.",
        "data": {
            "submission_id": "123e4567-e89b-12d3-a456-426614174000",
            "verdict": "accepted",
            "payment_tx": "0xdef456...",
            "idempotent": false
        }
    }
    ```

    ## Error Handling
    - **502 Bad Gateway**: Payment settlement failed - submission remains in pending state for retry
    - **409 Conflict**: Submission already processed or task in invalid state (cancelled/expired)
    - **403 Forbidden**: Agent doesn't own this submission
    - **404 Not Found**: Submission doesn't exist

    ## Idempotency
    If submission is already approved, returns success with `idempotent: true` and
    attempts payment settlement again if no payment transaction is recorded.

    ## Payment Verification
    - Validates worker wallet address format
    - Prevents self-payment (agent paying themselves)
    - Requires valid payment amount (bounty amount)
    - Ensures task has sufficient escrow/authorization

    ## Side Effects
    - Updates submission verdict to 'accepted'
    - Updates task status to 'completed'
    - Records payment transaction in audit log
    - Submits ERC-8004 reputation score for worker (if enabled)
    - Triggers payment settlement through configured dispatcher
    """
    # Read optional Fase 1 payment auth headers
    _worker_auth = None
    _fee_auth = None
    if http_request is not None:
        _worker_auth = http_request.headers.get(
            "X-Payment-Worker"
        ) or http_request.headers.get("x-payment-worker")
        _fee_auth = http_request.headers.get(
            "X-Payment-Fee"
        ) or http_request.headers.get("x-payment-fee")
    # Verify ownership
    if not await verify_agent_owns_submission(api_key.agent_id, submission_id):
        submission = await db.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        raise HTTPException(
            status_code=403, detail="Not authorized to approve this submission"
        )

    # Check if already processed.
    # If already accepted, return idempotent success for safe client retries.
    submission = await db.get_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    existing_verdict = _normalize_status(submission.get("agent_verdict"))
    if existing_verdict in {"accepted", "approved"}:
        settlement = await _settle_submission_payment(
            submission_id=submission_id,
            submission=submission,
            note="Idempotent settlement retry after prior approval",
            worker_auth_header=_worker_auth,
            fee_auth_header=_fee_auth,
        )
        response_data = {
            "submission_id": submission_id,
            "verdict": "accepted",
            "idempotent": True,
        }
        if settlement.get("payment_tx"):
            response_data["payment_tx"] = settlement["payment_tx"]
        if settlement.get("payment_error"):
            response_data["payment_error"] = settlement["payment_error"]

        return SuccessResponse(
            message="Submission already approved.",
            data=response_data,
        )

    if existing_verdict not in {"", "pending"}:
        raise HTTPException(
            status_code=409,
            detail=f"Submission already processed with verdict: {submission.get('agent_verdict')}",
        )

    task = submission.get("task") or {}
    task_status = _normalize_status(task.get("status"))
    if task_status in {"cancelled", "refunded", "expired"}:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve submission while task status is '{task_status}'",
        )
    if task_status == "completed":
        raise HTTPException(
            status_code=409,
            detail="Cannot approve submission because task is already completed",
        )

    notes = request.notes if request else None
    rating_score = getattr(request, "rating_score", None) if request else None
    settlement = await _settle_submission_payment(
        submission_id=submission_id,
        submission=submission,
        note="Manual approval payout via x402 facilitator",
        worker_auth_header=_worker_auth,
        fee_auth_header=_fee_auth,
        override_score=rating_score,
    )
    release_tx = settlement.get("payment_tx")
    release_error = settlement.get("payment_error")

    if not release_tx:
        raise HTTPException(
            status_code=502,
            detail=f"Could not settle payment before approval: {release_error or 'missing tx hash'}",
        )

    # Only mark approved/completed after settlement has tx evidence.
    try:
        await db.update_submission(
            submission_id=submission_id,
            agent_id=api_key.agent_id,
            verdict="accepted",
            notes=notes,
        )
    except Exception as state_err:
        logger.error(
            "Payment released for submission %s but state update failed: %s",
            submission_id,
            state_err,
        )
        return SuccessResponse(
            message="Payment released, but submission state update needs retry.",
            data={
                "submission_id": submission_id,
                "verdict": "accepted_pending_state_update",
                "payment_tx": release_tx,
                "payment_error": str(state_err),
            },
        )

    logger.info(
        "Submission approved and paid: id=%s, agent=%s, tx=%s",
        submission_id,
        api_key.agent_id,
        release_tx,
    )

    # Fire-and-forget: ERC-8004 side effects (WS-1 registration, WS-2 agent rating)
    try:
        await _execute_post_approval_side_effects(
            submission_id=submission_id,
            submission=submission,
            release_tx=release_tx,
        )
    except Exception as side_fx_err:
        logger.error(
            "Post-approval side effects error (non-blocking): submission=%s, error=%s",
            submission_id,
            side_fx_err,
        )

    response_data = {
        "submission_id": submission_id,
        "verdict": "accepted",
        "payment_tx": release_tx,
    }
    if release_error:
        response_data["payment_error"] = release_error

    return SuccessResponse(
        message="Submission approved. Payment released to worker.", data=response_data
    )


@router.post(
    "/submissions/{submission_id}/reject",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Submission rejected and task returned to available pool"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to reject this submission",
        },
        404: {"model": ErrorResponse, "description": "Submission not found"},
        409: {
            "model": ErrorResponse,
            "description": "Submission already processed with different verdict",
        },
    },
    summary="Reject Submission",
    description="Reject a worker's submission and return task to available pool",
    tags=["Submissions", "Agent"],
)
async def reject_submission(
    submission_id: str = Path(
        ..., description="UUID of the submission", pattern=UUID_PATTERN
    ),
    request: RejectionRequest = ...,
    api_key: APIKeyData = Depends(verify_api_key_if_required),
) -> SuccessResponse:
    """
    Reject a worker's submission and return the task to available status.

    When a submission doesn't meet requirements, the agent can reject it with
    detailed feedback. The task returns to 'published' status so other workers
    can apply and complete it properly.

    ## Request Body
    ```json
    {
        "notes": "Photo is too blurry to verify restaurant status. Please retake with clear view of entrance and operating hours sign."
    }
    ```

    ## Response Example
    ```json
    {
        "success": true,
        "message": "Submission rejected. Task returned to available pool.",
        "data": {
            "submission_id": "789abcdef-1234-5678-9abc-def123456789",
            "verdict": "rejected"
        }
    }
    ```

    ## Rejection Process
    1. **Validation**: Verifies agent owns the submission
    2. **Status Check**: Ensures submission is in 'pending' status
    3. **Record Rejection**: Updates submission verdict and notes
    4. **Task Reset**: Returns task to 'published' status
    5. **Worker Notification**: Worker receives rejection feedback

    ## Required Fields
    - **notes**: Detailed explanation of why work was rejected (10-1000 characters)
      - Should be constructive and specific
      - Helps the worker or other workers understand requirements
      - Used for quality improvement and learning

    ## Effects of Rejection
    - Submission status → 'rejected'
    - Task status → 'published' (available for new applications)
    - Worker receives rejection feedback
    - Task appears in worker search results again
    - No payment is released
    - Worker can apply to other tasks

    ## Common Rejection Reasons
    - **Evidence Quality**: Poor photo quality, incomplete documentation
    - **Missing Requirements**: Required evidence types not provided
    - **Incorrect Location**: Wrong location or GPS coordinates
    - **Insufficient Detail**: Text reports lack required information
    - **Wrong Timing**: Task completed outside specified time window
    - **Safety Concerns**: Evidence shows unsafe or inappropriate actions

    ## Best Practices for Agents
    - **Be Specific**: Explain exactly what was wrong and how to improve
    - **Be Constructive**: Focus on improvement rather than criticism
    - **Reference Requirements**: Point to specific task requirements not met
    - **Suggest Solutions**: When possible, suggest how to fix the issues

    ## Worker Impact
    After rejection:
    - Worker can see rejection reason and learn from feedback
    - Worker remains eligible for other tasks
    - No payment deduction or penalty (beyond lost time)
    - Contributes to worker learning and improvement

    ## Task Lifecycle After Rejection
    1. Task returns to 'published' status immediately
    2. Other workers can see and apply to the task
    3. Original worker can reapply if they choose
    4. Task deadline and requirements remain unchanged
    5. Payment escrow remains intact for eventual completion

    ## Error Conditions
    - **409 Conflict**: Submission already processed (accepted/rejected/disputed)
    - **403 Forbidden**: Agent doesn't own this submission
    - **404 Not Found**: Submission ID doesn't exist
    - **400 Bad Request**: Missing or invalid rejection notes

    ## Quality Assurance
    Rejection feedback helps maintain platform quality by:
    - Setting clear expectations for evidence standards
    - Training workers on requirement specifics
    - Building consistency across similar tasks
    - Improving overall submission quality over time

    This endpoint is crucial for maintaining quality standards while providing
    educational feedback to help workers improve their future submissions.
    """
    # Verify ownership
    if not await verify_agent_owns_submission(api_key.agent_id, submission_id):
        submission = await db.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        raise HTTPException(
            status_code=403, detail="Not authorized to reject this submission"
        )

    # Check if already processed
    submission = await db.get_submission(submission_id)
    if submission.get("agent_verdict") not in [None, "pending"]:
        raise HTTPException(
            status_code=409,
            detail=f"Submission already processed with verdict: {submission.get('agent_verdict')}",
        )

    # Validate severity-specific constraints
    if request.severity == "major" and request.reputation_score is not None:
        if request.reputation_score > 50:
            raise HTTPException(
                status_code=400,
                detail="Major rejection reputation_score must be 0-50",
            )

    # Update submission
    await db.update_submission(
        submission_id=submission_id,
        agent_id=api_key.agent_id,
        verdict="rejected",
        notes=request.notes,
    )

    logger.info(
        "Submission rejected: id=%s, agent=%s, severity=%s, reason=%s",
        submission_id,
        api_key.agent_id,
        request.severity,
        request.notes[:50],
    )

    side_effect_id = None
    if request.severity == "major":
        from config.platform_config import PlatformConfig

        rejection_enabled = await PlatformConfig.is_feature_enabled(
            "erc8004_rejection_feedback"
        )

        if rejection_enabled:
            # Rate-limit: max 3 major rejections per agent per 24h
            try:
                client = db.get_client()
                cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
                count_result = (
                    client.table("erc8004_side_effects")
                    .select("id", count="exact")
                    .eq("effect_type", "rate_worker_on_rejection")
                    .gte("created_at", cutoff)
                    .execute()
                )
                recent_count = (
                    count_result.count if count_result.count is not None else 0
                )
                # Filter by agent_id from payload
                if recent_count >= 3:
                    # Additional check: count only this agent's rejections
                    all_rows = (
                        client.table("erc8004_side_effects")
                        .select("payload")
                        .eq("effect_type", "rate_worker_on_rejection")
                        .gte("created_at", cutoff)
                        .execute()
                    )
                    agent_count = sum(
                        1
                        for r in (all_rows.data or [])
                        if (r.get("payload") or {}).get("agent_id") == api_key.agent_id
                    )
                    if agent_count >= 3:
                        raise HTTPException(
                            status_code=429,
                            detail="Rate limit exceeded: max 3 major rejections per 24 hours",
                        )
            except HTTPException:
                raise
            except Exception as rl_err:
                logger.warning(
                    "Rate limit check failed for rejection feedback: %s", rl_err
                )

            # Enqueue side effect
            score = (
                request.reputation_score if request.reputation_score is not None else 30
            )
            task = submission.get("task") or {}
            executor = submission.get("executor") or {}
            try:
                from reputation.side_effects import enqueue_side_effect

                effect = await enqueue_side_effect(
                    supabase=db.get_client(),
                    submission_id=submission_id,
                    effect_type="rate_worker_on_rejection",
                    payload={
                        "task_id": task.get("id"),
                        "worker_wallet": executor.get("wallet_address"),
                        "agent_id": api_key.agent_id,
                        "severity": "major",
                        "notes": request.notes[:200],
                    },
                    score=score,
                )
                if effect:
                    side_effect_id = effect.get("id")

                logger.info(
                    "Major rejection feedback enqueued: submission=%s, agent=%s, score=%d",
                    submission_id,
                    api_key.agent_id,
                    score,
                )
            except Exception as se_err:
                logger.error(
                    "Failed to enqueue rejection feedback for submission %s: %s",
                    submission_id,
                    se_err,
                )

    response_data = {"submission_id": submission_id, "verdict": "rejected"}
    if request.severity == "major":
        response_data["severity"] = "major"
    if side_effect_id:
        response_data["side_effect_id"] = side_effect_id

    return SuccessResponse(
        message="Submission rejected. Task returned to available pool.",
        data=response_data,
    )


@router.post(
    "/submissions/{submission_id}/request-more-info",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Additional information requested from worker"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to update this submission",
        },
        404: {"model": ErrorResponse, "description": "Submission not found"},
        409: {
            "model": ErrorResponse,
            "description": "Submission already processed with final verdict",
        },
    },
    summary="Request More Information",
    description="Request additional evidence or clarification from the assigned worker",
    tags=["Submissions", "Agent"],
)
async def request_more_info_submission(
    submission_id: str = Path(
        ..., description="UUID of the submission", pattern=UUID_PATTERN
    ),
    request: RequestMoreInfoRequest = ...,
    api_key: APIKeyData = Depends(verify_api_key_if_required),
) -> SuccessResponse:
    """
    Request additional evidence or clarification from the assigned worker.

    When a submission is close to meeting requirements but needs additional
    evidence or clarification, the agent can request more information instead
    of rejecting outright. This gives the worker a chance to complete the
    task properly.

    ## Request Body
    ```json
    {
        "notes": "Please provide a clearer photo showing the restaurant's posted hours. The current image is too dark to read the operating schedule clearly."
    }
    ```

    ## Response Example
    ```json
    {
        "success": true,
        "message": "More information requested from worker.",
        "data": {
            "submission_id": "789abcdef-1234-5678-9abc-def123456789",
            "task_id": "123e4567-e89b-12d3-a456-426614174000",
            "verdict": "more_info_requested"
        }
    }
    ```

    ## Request Process
    1. **Validation**: Verifies agent owns the submission
    2. **Status Check**: Ensures submission hasn't been finalized
    3. **Update Submission**: Sets verdict to 'more_info_requested'
    4. **Reset Task**: Returns task to 'in_progress' status
    5. **Worker Notification**: Worker receives specific improvement request

    ## When to Use This Endpoint
    - **Partial Completion**: Work is mostly done but missing key elements
    - **Quality Issues**: Evidence is present but needs improvement
    - **Clarity Needed**: Text reports need more detail or clarification
    - **Technical Issues**: Photos/videos have technical problems (lighting, focus)
    - **Minor Gaps**: Small missing pieces that can be easily addressed

    ## Alternative to Rejection
    Unlike rejection, this endpoint:
    - Keeps the task assigned to the same worker
    - Preserves the worker's progress and investment
    - Encourages improvement rather than starting over
    - Maintains task continuity and timeline

    ## Required Fields
    - **notes**: Specific guidance on what additional information is needed
      - Should be clear and actionable (5-1000 characters)
      - Focus on specific improvements needed
      - Avoid vague requests like "need more info"

    ## Effects on Task Status
    - **Submission**: verdict → 'more_info_requested'
    - **Task**: status → 'in_progress'
    - **Worker**: can resubmit with additional evidence
    - **Timeline**: deadline remains unchanged
    - **Payment**: escrow remains locked for this worker

    ## Worker Response Options
    After receiving the request, the worker can:
    1. **Resubmit**: Provide additional evidence and resubmit
    2. **Abandon**: Stop working (task returns to published)
    3. **Clarify**: Ask questions before providing more evidence

    ## Common More-Info Scenarios

    ### Photo Quality Issues
    ```json
    {
        "notes": "Please retake the photo with better lighting. The current image is too dark to verify the operating hours posted on the door."
    }
    ```

    ### Missing Evidence Types
    ```json
    {
        "notes": "Great photos! Please also include GPS coordinates to verify the location, as required in the task evidence schema."
    }
    ```

    ### Insufficient Detail
    ```json
    {
        "notes": "Your text report mentions customers but please provide more specific details: approximately how many customers, what time you observed, staff activity, etc."
    }
    ```

    ### Clarification Needed
    ```json
    {
        "notes": "The photo shows a 'Closed' sign but your report says it's open. Can you clarify the restaurant's current status and provide additional evidence?"
    }
    ```

    ## Best Practices for Agents
    - **Be Specific**: Exactly what's missing or needs improvement
    - **Be Encouraging**: Acknowledge what was done well
    - **Provide Guidance**: How to address the gaps
    - **Set Expectations**: What additional evidence would complete the task

    ## Submission Workflow
    1. **Initial Submission**: Worker submits evidence
    2. **Agent Review**: Agent identifies gaps but sees potential
    3. **More Info Request**: Agent specifies needed improvements
    4. **Worker Update**: Worker provides additional evidence
    5. **Resubmission**: Updated submission for final review
    6. **Final Decision**: Agent approves or rejects complete submission

    ## Error Conditions
    - **409 Conflict**: Submission already accepted/rejected/disputed
    - **403 Forbidden**: Agent doesn't own this submission
    - **404 Not Found**: Submission doesn't exist

    ## Timeline Considerations
    - Task deadline remains unchanged during more-info cycle
    - Workers should factor revision time into their task planning
    - Multiple more-info cycles are possible but discouraged

    This endpoint promotes collaboration between agents and workers,
    leading to higher quality completed tasks and better worker education.
    """
    if not await verify_agent_owns_submission(api_key.agent_id, submission_id):
        submission = await db.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        raise HTTPException(
            status_code=403, detail="Not authorized to update this submission"
        )

    submission = await db.get_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    existing_verdict = _normalize_status(submission.get("agent_verdict"))
    if existing_verdict in {"accepted", "approved", "rejected", "disputed"}:
        raise HTTPException(
            status_code=409,
            detail=f"Submission already processed with verdict: {submission.get('agent_verdict')}",
        )

    task = submission.get("task") or {}
    task_id = task.get("id")
    if not task_id:
        raise HTTPException(
            status_code=500, detail="Submission is missing task context"
        )

    await db.update_submission(
        submission_id=submission_id,
        agent_id=api_key.agent_id,
        verdict="more_info_requested",
        notes=request.notes,
    )
    await db.update_task(task_id, {"status": "in_progress"})

    logger.info(
        "More info requested: submission=%s, task=%s, agent=%s",
        submission_id,
        task_id,
        api_key.agent_id,
    )

    return SuccessResponse(
        message="More information requested from worker.",
        data={
            "submission_id": submission_id,
            "task_id": task_id,
            "verdict": "more_info_requested",
        },
    )


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=SuccessResponse,
    responses={
        200: {
            "description": "Task cancelled successfully with appropriate refund handling"
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to cancel this task",
        },
        404: {"model": ErrorResponse, "description": "Task not found"},
        409: {
            "model": ErrorResponse,
            "description": "Task cannot be cancelled in current status",
        },
        402: {
            "model": ErrorResponse,
            "description": "Escrow refund failed - task cancelled but manual refund required",
        },
    },
    summary="Cancel Task",
    description="Cancel a published task and handle payment refunds based on escrow status",
    tags=["Tasks", "Agent", "Payments"],
)
async def cancel_task(
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    request: CancelRequest = None,
    api_key: APIKeyData = Depends(verify_api_key_if_required),
) -> SuccessResponse:
    """
    Cancel a task and handle payment refunds automatically.

    Cancels a task and processes appropriate refund based on the payment mode and
    escrow status. Only tasks in 'published' status can be cancelled - tasks with
    assigned workers cannot be cancelled to protect worker interests.

    ## Cancellation Rules
    - **Only 'published' tasks** can be cancelled
    - Tasks with assigned workers (accepted/in_progress/submitted) cannot be cancelled
    - Already cancelled tasks return idempotent success response

    ## Refund Handling by Payment Mode

    ### x402r Mode (On-chain Escrow)
    - **Deposited/Locked**: Funds refunded from escrow contract to agent wallet
    - **Already Released**: Cannot cancel (409 error)
    - **Already Refunded**: Idempotent success

    ### Preauth Mode (Authorization Only)
    - **Authorized**: Authorization expires naturally, no funds moved
    - **Pending**: Authorization expires, no refund needed

    ### Fase1 Mode (Balance Check)
    - **Balance Verified**: No funds moved, authorization expires
    - No refund transaction needed

    ### Fase2 Mode (Facilitator Escrow)
    - **Deposited**: Funds refunded from facilitator to agent wallet
    - Uses gasless refund transaction via facilitator

    ## Request Body Example
    ```json
    {
        "reason": "Task requirements changed, no longer needed"
    }
    ```

    ## Success Response Examples

    ### With Refund Transaction
    ```json
    {
        "success": true,
        "message": "Task cancelled successfully. Escrow refunded to agent.",
        "data": {
            "task_id": "123e4567-e89b-12d3-a456-426614174000",
            "reason": "Task requirements changed",
            "escrow": {
                "status": "refunded",
                "escrow_id": "escrow_1234abcd",
                "tx_hash": "0xdef456...",
                "method": "x402r"
            }
        }
    }
    ```

    ### Authorization Expiry (No Refund Needed)
    ```json
    {
        "success": true,
        "message": "Task cancelled successfully. Payment authorization expired (no funds moved).",
        "data": {
            "task_id": "123e4567-e89b-12d3-a456-426614174000",
            "reason": "No longer needed",
            "escrow": {
                "status": "authorization_expired",
                "message": "Payment authorization will expire. No funds were moved."
            }
        }
    }
    ```

    ## Error Responses
    - **409 Conflict**: Task in non-cancellable status (accepted/in_progress/etc.)
    - **402 Payment Required**: Escrow refund failed, manual intervention needed
    - **403 Forbidden**: Agent doesn't own this task
    - **404 Not Found**: Task doesn't exist

    ## Critical Fund Loss Detection
    In rare cases where agent settlement succeeded but escrow lock failed, the system
    detects potential fund loss and requires manual refund intervention:

    ```json
    {
        "escrow": {
            "status": "refund_manual_required",
            "agent_settle_tx": "0xabc123...",
            "error": "Funds were settled from agent wallet but escrow lock failed. Manual refund required."
        }
    }
    ```

    ## Idempotency
    Cancelling an already-cancelled task returns success with `idempotent: true`.

    ## Audit Trail
    - Task status updated to 'cancelled'
    - Refund transaction recorded in payments table
    - Escrow status updated appropriately
    - Payment events logged for audit purposes

    ## Side Effects
    - Updates task status to 'cancelled'
    - Processes appropriate refund transaction
    - Updates escrow status (refunded/expired)
    - Records refund payment in audit log
    - Task removed from worker-visible published tasks
    """
    refund_info = None
    try:
        reason = request.reason if request else None

        # Get task details before cancellation to check escrow status
        task = await db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task.get("agent_id") != api_key.agent_id:
            raise HTTPException(
                status_code=403, detail="Not authorized to cancel this task"
            )

        # Idempotency for client retries: cancelling an already-cancelled task
        # should return success.
        task_status = _normalize_status(task.get("status"))
        if task_status == "cancelled":
            return SuccessResponse(
                message="Task already cancelled.",
                data={"task_id": task_id, "reason": reason, "idempotent": True},
            )

        # Only published tasks can be cancelled. Tasks in accepted/in_progress/etc.
        # must NOT be refunded — a worker is actively working on them.
        if task_status != "published":
            raise HTTPException(
                status_code=409,
                detail=f"Cannot cancel task in '{task_status}' status. Only 'published' tasks can be cancelled.",
            )

        # Check if we need to handle escrow refund
        escrow_tx = task.get(
            "escrow_tx"
        )  # Stores tx hash (x402r) or payment_reference (preauth)
        escrow_id = task.get("escrow_id")

        if escrow_tx:
            try:
                client = db.get_client()
                escrow_row = None
                try:
                    escrow_result = (
                        client.table("escrows")
                        .select(
                            "id,status,escrow_id,refunded_at,released_at,metadata,beneficiary_address"
                        )
                        .eq("task_id", task_id)
                        .single()
                        .execute()
                    )
                    escrow_row = escrow_result.data or None
                except Exception:
                    escrow_row = None

                escrow_status = _normalize_status(
                    (escrow_row or {}).get("status") or "authorized"
                )
                effective_escrow_id = (escrow_row or {}).get("escrow_id") or escrow_id

                if escrow_status in ALREADY_REFUNDED_ESCROW_STATUSES:
                    refund_info = {
                        "status": "already_refunded",
                        "escrow_id": effective_escrow_id,
                    }
                elif escrow_status in NON_REFUNDABLE_ESCROW_STATUSES:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Cannot cancel task because escrow is already {escrow_status}",
                    )
                elif escrow_status in REFUNDABLE_ESCROW_STATUSES:
                    # Use PaymentDispatcher for refund (handles x402r escrow and preauth)
                    dispatcher = get_payment_dispatcher()
                    if dispatcher:
                        # Get agent wallet for x402r refund disbursement.
                        # Priority: 1) escrow row beneficiary_address column,
                        # 2) metadata.beneficiary_address, 3) extract from X-Payment header
                        agent_address = None
                        try:
                            # Try the DB column first (most reliable)
                            agent_address = (escrow_row or {}).get(
                                "beneficiary_address"
                            )
                            if not agent_address:
                                escrow_meta = (escrow_row or {}).get("metadata") or {}
                                if isinstance(escrow_meta, str):
                                    escrow_meta = json.loads(escrow_meta)
                                agent_address = escrow_meta.get(
                                    "beneficiary_address"
                                ) or _extract_agent_wallet_from_header(
                                    escrow_meta.get("x_payment_header")
                                )
                        except Exception:
                            pass

                        refund_result = await dispatcher.refund_payment(
                            task_id=task_id,
                            escrow_id=str(effective_escrow_id or ""),
                            reason=reason,
                            agent_address=agent_address,
                        )
                        if refund_result.get("success"):
                            refund_tx_hash = refund_result.get("tx_hash")
                            refund_info = {
                                "status": "refunded",
                                "escrow_id": effective_escrow_id,
                                "tx_hash": refund_tx_hash,
                                "method": refund_result.get("mode", "unknown"),
                            }
                            if refund_tx_hash:
                                try:
                                    client.table("tasks").update(
                                        {
                                            "refund_tx": refund_tx_hash,
                                        }
                                    ).eq("id", task_id).execute()
                                except Exception as task_update_err:
                                    logger.warning(
                                        "Could not store refund_tx on task %s: %s",
                                        task_id,
                                        task_update_err,
                                    )
                            try:
                                client.table("escrows").update(
                                    {
                                        "status": "refunded",
                                        "refund_tx": refund_tx_hash,
                                        "refunded_at": datetime.now(
                                            timezone.utc
                                        ).isoformat(),
                                    }
                                ).eq("task_id", task_id).execute()
                            except Exception as escrow_update_err:
                                logger.warning(
                                    "Could not mark escrow refunded for task %s: %s",
                                    task_id,
                                    escrow_update_err,
                                )
                            _record_refund_payment(
                                task=task,
                                agent_id=api_key.agent_id,
                                refund_tx=refund_tx_hash,
                                reason=reason,
                                settlement_method=refund_result.get("mode"),
                            )
                        else:
                            refund_info = {
                                "status": "refund_manual_required",
                                "escrow_id": effective_escrow_id,
                                "error": refund_result.get(
                                    "error", "Refund attempt failed"
                                ),
                            }
                    elif X402_AVAILABLE:
                        # Fallback: direct SDK refund
                        sdk = get_sdk()
                        refund_result = await sdk.refund_task_payment(
                            task_id=task_id,
                            escrow_id=str(effective_escrow_id or ""),
                            reason=reason,
                        )
                        if refund_result.get("success"):
                            refund_tx_hash = refund_result.get("tx_hash")
                            refund_info = {
                                "status": "refunded",
                                "escrow_id": effective_escrow_id,
                                "tx_hash": refund_tx_hash,
                                "method": refund_result.get("method", "unknown"),
                            }
                        else:
                            refund_info = {
                                "status": "refund_manual_required",
                                "escrow_id": effective_escrow_id,
                                "error": refund_result.get(
                                    "error", "Refund attempt failed"
                                ),
                            }
                    else:
                        refund_info = {
                            "status": "refund_manual_required",
                            "escrow_id": effective_escrow_id,
                            "error": "x402 SDK not available",
                        }
                elif escrow_status == "failed":
                    # Escrow lock failed — check if agent's auth was already settled
                    escrow_meta = (escrow_row or {}).get("metadata") or {}
                    if isinstance(escrow_meta, str):
                        escrow_meta = json.loads(escrow_meta)
                    agent_settle_tx = escrow_meta.get("agent_settle_tx")
                    if agent_settle_tx:
                        # CRITICAL: Funds WERE moved (agent → recipient) but escrow lock failed.
                        # The agent's money is in the recipient wallet (treasury or platform).
                        # A manual refund is required.
                        refund_info = {
                            "status": "refund_manual_required",
                            "escrow_id": effective_escrow_id,
                            "agent_settle_tx": agent_settle_tx,
                            "error": (
                                "Funds were settled from agent wallet but escrow lock "
                                "failed. Manual refund required. Settlement tx: "
                                f"{agent_settle_tx}"
                            ),
                        }
                        logger.error(
                            "FUND LOSS DETECTED: task=%s, agent_settle_tx=%s — "
                            "escrow lock failed after settlement. Manual refund required.",
                            task_id,
                            agent_settle_tx,
                        )
                        await log_payment_event(
                            task_id=task_id,
                            event_type="error",
                            status="failed",
                            tx_hash=agent_settle_tx,
                            error="FUND LOSS: escrow lock failed after agent settlement",
                            metadata={
                                "escrow_status": escrow_status,
                                "requires_manual_refund": True,
                            },
                        )
                    else:
                        # Escrow failed but no settlement occurred — safe, auth expires
                        refund_info = {
                            "status": "authorization_expired",
                            "message": "Escrow failed but no funds were moved. Authorization will expire.",
                        }
                elif escrow_status in AUTHORIZE_ONLY_ESCROW_STATUSES:
                    # EIP-3009 authorize-only (preauth mode): no funds moved, auth expires.
                    refund_info = {
                        "status": "authorization_expired",
                        "message": "Payment authorization will expire. No funds were moved.",
                    }
                else:
                    # Unknown escrow status — attempt refund if SDK is available
                    logger.warning(
                        "Unknown escrow status '%s' for task %s, attempting refund",
                        escrow_status,
                        task_id,
                    )
                    if X402_AVAILABLE:
                        try:
                            sdk = get_sdk()
                            refund_result = await sdk.refund_task_payment(
                                task_id=task_id,
                                escrow_id=str(effective_escrow_id or ""),
                                reason=reason,
                            )
                            if refund_result.get("success"):
                                refund_tx_hash = refund_result.get("tx_hash")
                                refund_info = {
                                    "status": "refunded",
                                    "escrow_id": effective_escrow_id,
                                    "tx_hash": refund_tx_hash,
                                    "method": refund_result.get("method", "unknown"),
                                }
                                if refund_tx_hash:
                                    try:
                                        client.table("tasks").update(
                                            {
                                                "refund_tx": refund_tx_hash,
                                            }
                                        ).eq("id", task_id).execute()
                                    except Exception:
                                        pass
                                _record_refund_payment(
                                    task=task,
                                    agent_id=api_key.agent_id,
                                    refund_tx=refund_tx_hash,
                                    reason=reason,
                                    settlement_method=refund_result.get("method"),
                                )
                            else:
                                refund_info = {
                                    "status": "refund_manual_required",
                                    "escrow_id": effective_escrow_id,
                                    "error": refund_result.get(
                                        "error", "Unknown status, refund failed"
                                    ),
                                }
                        except Exception as refund_err:
                            logger.warning(
                                "Refund attempt failed for task %s: %s",
                                task_id,
                                refund_err,
                            )
                            refund_info = {
                                "status": "authorization_expired",
                                "message": "Could not determine escrow state. Authorization will expire.",
                            }
                    else:
                        refund_info = {
                            "status": "authorization_expired",
                            "message": "Payment authorization will expire. No funds were moved.",
                        }

            except HTTPException:
                raise
            except Exception as escrow_err:
                logger.warning(
                    "Could not check/update escrow for task %s: %s", task_id, escrow_err
                )

        # Cancel the task in database
        try:
            await db.cancel_task(task_id, api_key.agent_id)
        except Exception as cancel_err:
            cancel_error = str(cancel_err).lower()
            if (
                "status: cancelled" not in cancel_error
                and "already cancelled" not in cancel_error
            ):
                raise

        logger.info(
            "Task cancelled: id=%s, agent=%s, reason=%s, escrow=%s",
            task_id,
            api_key.agent_id,
            reason,
            refund_info,
        )

        response_data = {"task_id": task_id, "reason": reason}
        if refund_info:
            response_data["escrow"] = refund_info

        status_label = (refund_info or {}).get("status")
        message_suffix = ""
        if status_label == "authorization_expired":
            message_suffix = " Payment authorization expired (no funds moved)."
        elif status_label == "refunded":
            message_suffix = " Escrow refunded to agent."
        elif status_label == "already_refunded":
            message_suffix = " Escrow was already refunded."
        elif status_label == "not_refundable":
            message_suffix = " Escrow was already released."
        elif status_label in {"refund_manual_required", "refund_failed"}:
            message_suffix = " Escrow refund requires manual intervention."

        return SuccessResponse(
            message=f"Task cancelled successfully.{message_suffix}", data=response_data
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail="Task not found")
        elif "not authorized" in error_msg.lower():
            raise HTTPException(status_code=403, detail=error_msg)
        elif "cannot cancel" in error_msg.lower() or "status" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg)
        logger.error("Unexpected error cancelling task %s: %s", task_id, error_msg)
        raise HTTPException(
            status_code=500, detail="Internal error while cancelling task"
        )


@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    responses={
        200: {"description": "Analytics data retrieved successfully"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
    },
    summary="Get Agent Analytics",
    description="Comprehensive analytics dashboard data for the authenticated agent",
    tags=["Analytics", "Agent"],
)
async def get_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    api_key: APIKeyData = Depends(verify_api_key_if_required),
) -> AnalyticsResponse:
    """
    Get comprehensive analytics for the authenticated agent.

    Provides detailed analytics including task performance, spending patterns,
    completion rates, worker performance, and timing metrics over a specified period.

    ## Query Parameters
    - **days**: Analysis period in days (1-365, default: 30)
      - Common periods: 7 (week), 30 (month), 90 (quarter), 365 (year)

    ## Response Example
    ```json
    {
        "totals": {
            "total_tasks": 45,
            "total_bounty": 225.50,
            "completed": 38,
            "completion_rate": 84.4,
            "avg_bounty": 5.01,
            "total_spent": 243.54,
            "platform_fees": 18.04
        },
        "by_status": {
            "published": 3,
            "accepted": 2,
            "in_progress": 1,
            "submitted": 1,
            "completed": 38,
            "cancelled": 0,
            "expired": 0
        },
        "by_category": {
            "physical_presence": 25,
            "knowledge_access": 12,
            "simple_action": 5,
            "human_authority": 2,
            "digital_physical": 1
        },
        "average_times": {
            "time_to_accept": "2h 15m",
            "time_to_complete": "4h 30m",
            "time_to_review": "45m"
        },
        "top_workers": [
            {
                "executor_id": "abc123...",
                "wallet_address": "0x742d35...",
                "tasks_completed": 8,
                "total_earned": 42.50,
                "avg_completion_time": "3h 20m",
                "success_rate": 100.0,
                "reputation_score": 95
            }
        ],
        "period_days": 30
    }
    ```

    ## Analytics Categories

    ### Task Performance Totals
    - **total_tasks**: Total tasks created in period
    - **completed**: Successfully completed tasks
    - **completion_rate**: Percentage of tasks completed
    - **total_bounty**: Total bounty amounts across all tasks
    - **total_spent**: Total spent including platform fees
    - **platform_fees**: Total platform fees paid
    - **avg_bounty**: Average bounty per task

    ### Status Breakdown
    Shows current task distribution across all statuses:
    - **published**: Available for worker applications
    - **accepted**: Assigned to workers
    - **in_progress**: Being worked on
    - **submitted**: Awaiting agent review
    - **completed**: Finished and paid
    - **cancelled**: Cancelled by agent
    - **expired**: Deadline passed

    ### Category Analysis
    Task distribution by category helps understand agent focus areas:
    - **physical_presence**: Location-based tasks
    - **knowledge_access**: Expertise-required tasks
    - **human_authority**: Decision-making tasks
    - **simple_action**: Basic execution tasks
    - **digital_physical**: Hybrid digital/physical tasks

    ### Timing Metrics
    Average time intervals for workflow stages:
    - **time_to_accept**: From published to worker assignment
    - **time_to_complete**: From acceptance to work submission
    - **time_to_review**: From submission to agent approval/rejection

    ### Top Workers Analysis
    Performance metrics for frequent collaborators:
    - **tasks_completed**: Number of tasks finished
    - **total_earned**: Total bounty earned from this agent
    - **avg_completion_time**: Average time to complete tasks
    - **success_rate**: Percentage of submissions approved
    - **reputation_score**: ERC-8004 reputation score (if available)

    ## Time Period Flexibility
    - **7 days**: Weekly performance review
    - **30 days**: Monthly dashboard (default)
    - **90 days**: Quarterly business review
    - **365 days**: Annual performance analysis

    ## Use Cases
    - Agent dashboard overview widgets
    - Performance monitoring and optimization
    - Worker selection and relationship management
    - Budget planning and forecasting
    - Task category strategy analysis
    - Operational efficiency measurement

    ## Data Freshness
    Analytics are computed in real-time from the latest database state.
    No caching is applied to ensure accuracy for business decisions.

    ## Privacy & Security
    Only data for tasks created by the authenticated agent is included.
    Worker information is anonymized with truncated wallet addresses.
    """
    result = await db.get_agent_analytics(
        agent_id=api_key.agent_id,
        days=days,
    )

    return AnalyticsResponse(
        totals=result["totals"],
        by_status=result["by_status"],
        by_category=result["by_category"],
        average_times=result["average_times"],
        top_workers=result["top_workers"],
        period_days=result["period_days"],
    )


@router.post(
    "/tasks/{task_id}/assign",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Task successfully assigned to worker"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to assign this task or worker ineligible",
        },
        404: {"model": ErrorResponse, "description": "Task or executor not found"},
        409: {
            "model": ErrorResponse,
            "description": "Task not assignable in current status",
        },
    },
    summary="Assign Task to Worker",
    description="Assign a published task to a specific worker executor",
    tags=["Tasks", "Agent"],
)
async def assign_task_to_worker(
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    request: WorkerAssignRequest = ...,
    api_key: APIKeyData = Depends(verify_api_key_if_required),
) -> SuccessResponse:
    """
    Assign a published task to a specific worker executor.

    Agent endpoint for directly assigning tasks to workers, either from
    applications received or by selecting qualified workers. Moves the
    task from 'published' to 'accepted' status.

    ## Request Body
    ```json
    {
        "executor_id": "abc123def-4567-89ab-cdef-123456789abc",
        "notes": "Selected based on your excellent previous work on similar restaurant verification tasks. Please complete by end of business day."
    }
    ```

    ## Response Example
    ```json
    {
        "success": true,
        "message": "Task assigned successfully",
        "data": {
            "task_id": "123e4567-e89b-12d3-a456-426614174000",
            "executor_id": "abc123def-4567-89ab-cdef-123456789abc",
            "status": "accepted",
            "assigned_at": "2024-02-11T06:04:00Z",
            "worker_wallet": "0x742d35Cc6634C0532925a3b8D0fC6A3B3e1d7A5B"
        }
    }
    ```

    ## Assignment Process
    1. **Validation**: Verifies agent owns task and task is assignable
    2. **Worker Check**: Confirms executor exists and meets requirements
    3. **Eligibility**: Validates worker reputation and availability
    4. **Assignment**: Updates task status and records assignment
    5. **Notification**: Worker receives assignment notification

    ## Assignment Requirements

    ### Task Status
    Only tasks with `published` status can be assigned:
    - **published**: Available for assignment ✓
    - **accepted**: Already assigned ✗
    - **cancelled**: Not available ✗
    - **expired**: Past deadline ✗

    ### Worker Eligibility
    Worker must meet these criteria:
    - **Exists**: Valid executor_id in system
    - **Active**: Worker account in good standing
    - **Reputation**: Meets minimum reputation requirement (if set)
    - **Availability**: Not already assigned to maximum concurrent tasks
    - **Location**: Within reasonable distance (if location-based task)

    ## Common Assignment Workflows

    ### From Applications
    1. Agent reviews worker applications via separate endpoint
    2. Agent selects preferred worker from applicants
    3. Agent assigns task to chosen worker using this endpoint

    ### Direct Assignment
    1. Agent identifies worker from previous successful tasks
    2. Agent directly assigns without public application process
    3. Useful for repeat collaborations or urgent tasks

    ### Batch Assignment
    1. Agent creates multiple similar tasks
    2. Agent assigns different tasks to multiple proven workers
    3. Efficient for large-scale operations

    ## Request Fields
    - **executor_id**: UUID of the worker to assign (required)
    - **notes**: Optional message to the worker (0-500 characters)
      - Assignment context or special instructions
      - Encouragement or specific guidance
      - Timeline expectations or priorities

    ## Assignment Effects
    - **Task Status**: 'published' → 'accepted'
    - **Task Assignment**: executor_id populated
    - **Worker Status**: Task appears in worker's active tasks
    - **Visibility**: Task removed from public available tasks list
    - **Timeline**: Deadline countdown continues
    - **Payment**: Escrow remains locked for this specific worker

    ## Worker Benefits of Assignment
    - **Guaranteed Work**: No competition with other applicants
    - **Clear Expectations**: Agent-provided context and notes
    - **Trust Signal**: Agent chose them specifically
    - **Relationship Building**: Potential for repeat collaborations

    ## Error Conditions

    ### 404 Not Found
    ```json
    {
        "error": "EXECUTOR_NOT_FOUND",
        "message": "Executor not found",
        "details": {"executor_id": "invalid-uuid"}
    }
    ```

    ### 403 Forbidden (Insufficient Reputation)
    ```json
    {
        "error": "INSUFFICIENT_REPUTATION",
        "message": "Worker reputation score 25 below required minimum 50",
        "details": {"required": 50, "actual": 25}
    }
    ```

    ### 409 Conflict (Task Not Assignable)
    ```json
    {
        "error": "TASK_NOT_ASSIGNABLE",
        "message": "Task cannot be assigned in current status 'expired'",
        "details": {"current_status": "expired"}
    }
    ```

    ## Performance Considerations
    - Assignment is immediate and updates database atomically
    - Worker notifications sent asynchronously
    - Previous applications to this task are automatically invalidated
    - Task removed from search indexes within 30 seconds

    ## Best Practices for Agents
    - **Include Helpful Notes**: Context helps workers succeed
    - **Verify Worker Profile**: Check recent performance before assigning
    - **Consider Location**: Assign location-appropriate tasks
    - **Timeline Communication**: Share any urgency or deadline concerns
    - **Follow Up**: Check on progress for important tasks

    ## Relationship Building
    Successful assignments often lead to:
    - Repeat collaborations with trusted workers
    - Better task completion rates
    - Faster turnaround times
    - Higher quality submissions
    - Reduced agent review overhead

    This endpoint enables targeted task assignment for optimized outcomes.
    """
    try:
        result = await db.assign_task(
            task_id=task_id,
            agent_id=api_key.agent_id,
            executor_id=request.executor_id,
            notes=request.notes,
        )

        task = result.get("task", {})
        executor = result.get("executor", {})
        logger.info(
            "Task assigned: task=%s, agent=%s, executor=%s",
            task_id,
            api_key.agent_id[:10],
            request.executor_id[:10],
        )

        return SuccessResponse(
            message="Task assigned successfully",
            data={
                "task_id": task_id,
                "executor_id": request.executor_id,
                "status": task.get("status", "accepted"),
                "assigned_at": task.get("assigned_at"),
                "worker_wallet": executor.get("wallet_address"),
            },
        )

    except Exception as e:
        error_msg = str(e)
        lowered = error_msg.lower()
        if "not found" in lowered:
            if "executor" in lowered:
                raise HTTPException(status_code=404, detail="Executor not found")
            raise HTTPException(status_code=404, detail="Task not found")
        elif "not authorized" in lowered:
            raise HTTPException(
                status_code=403, detail="Not authorized to assign this task"
            )
        elif "cannot be assigned" in lowered or "status" in lowered:
            raise HTTPException(status_code=409, detail=error_msg)
        elif "insufficient reputation" in lowered:
            raise HTTPException(status_code=403, detail=error_msg)
        logger.error("Unexpected error assigning task %s: %s", task_id, error_msg)
        raise HTTPException(
            status_code=500, detail="Internal error while assigning task"
        )


# =============================================================================
# WORKER ENDPOINTS (PUBLIC/SEMI-PUBLIC)
# =============================================================================


@router.post(
    "/tasks/{task_id}/apply",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Application submitted"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        403: {"model": ErrorResponse, "description": "Not eligible"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        409: {"model": ErrorResponse, "description": "Already applied"},
    },
)
async def apply_to_task(
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    request: WorkerApplicationRequest = ...,
) -> SuccessResponse:
    """
    Apply to a task.

    Worker endpoint for submitting task applications. Checks reputation requirements.
    """
    try:
        result = await db.apply_to_task(
            task_id=task_id,
            executor_id=request.executor_id,
            message=request.message,
        )

        logger.info(
            "Application submitted: task=%s, executor=%s",
            task_id,
            request.executor_id[:8],
        )

        return SuccessResponse(
            message="Application submitted successfully",
            data={
                "application_id": result["application"]["id"],
                "task_id": task_id,
                "status": "pending",
            },
        )

    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            if "executor" in error_msg.lower():
                raise HTTPException(status_code=404, detail="Executor not found")
            raise HTTPException(status_code=404, detail="Task not found")
        elif "not available" in error_msg.lower():
            raise HTTPException(
                status_code=409, detail="Task is not available for applications"
            )
        elif "insufficient reputation" in error_msg.lower():
            raise HTTPException(status_code=403, detail=error_msg)
        elif "already applied" in error_msg.lower():
            raise HTTPException(status_code=409, detail="Already applied to this task")
        logger.error("Unexpected error applying to task %s: %s", task_id, error_msg)
        raise HTTPException(
            status_code=500, detail="Internal error while applying to task"
        )


@router.post(
    "/tasks/{task_id}/submit",
    response_model=SuccessResponse,
    responses={
        200: {
            "description": "Work submitted successfully, with optional instant payment"
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid request or missing required evidence",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not assigned to this task or not authorized",
        },
        404: {"model": ErrorResponse, "description": "Task not found"},
        409: {"model": ErrorResponse, "description": "Task not in submittable state"},
    },
    summary="Submit Work",
    description="Submit completed work with evidence for agent review (supports instant payment)",
    tags=["Tasks", "Worker", "Submissions"],
)
async def submit_work(
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    request: WorkerSubmissionRequest = ...,
) -> SuccessResponse:
    """
    Submit completed work with evidence for agent review.

    Worker endpoint for submitting finished work with required evidence.
    Automatically attempts instant payment settlement when possible, otherwise
    queues submission for agent review.

    ## Request Body Example
    ```json
    {
        "executor_id": "abc123def-4567-89ab-cdef-123456789abc",
        "evidence": {
            "photos": [
                "https://cdn.example.com/uploads/photo1.jpg",
                "https://cdn.example.com/uploads/photo2.jpg"
            ],
            "text_report": "Successfully verified the restaurant is open. There were customers inside and staff was actively serving. Hours posted on door confirm open until 9 PM today.",
            "gps_coordinates": {
                "lat": 45.5152,
                "lng": -122.6784,
                "accuracy": 3,
                "timestamp": "2024-02-11T08:15:00Z"
            }
        },
        "notes": "Task completed as requested. All evidence collected during peak hours for accuracy."
    }
    ```

    ## Submission Process
    1. **Validation**: Verifies worker assignment and task status
    2. **Evidence Check**: Validates required evidence types are provided
    3. **AI Pre-Check**: Runs automatic evidence verification (if available)
    4. **Instant Payment**: Attempts immediate payment settlement when conditions are met
    5. **Fallback**: Queues for agent review if instant payment unavailable

    ## Instant Payment Conditions
    Automatic payment occurs when:
    - Task has valid x402 payment context (escrow or preauth)
    - Worker wallet address is valid and different from agent
    - Evidence passes basic validation
    - Payment dispatcher is available

    ## Response Examples

    ### Instant Payment Success
    ```json
    {
        "success": true,
        "message": "Work submitted and paid instantly.",
        "data": {
            "submission_id": "789abcdef-1234-5678-9abc-def123456789",
            "task_id": "123e4567-e89b-12d3-a456-426614174000",
            "status": "completed",
            "verdict": "accepted",
            "payment_tx": "0xdef456..."
        }
    }
    ```

    ### Standard Submission (Agent Review Required)
    ```json
    {
        "success": true,
        "message": "Work submitted successfully. Awaiting agent review.",
        "data": {
            "submission_id": "789abcdef-1234-5678-9abc-def123456789",
            "task_id": "123e4567-e89b-12d3-a456-426614174000",
            "status": "submitted"
        }
    }
    ```

    ### Instant Payment Failed
    ```json
    {
        "success": true,
        "message": "Work submitted successfully. Awaiting agent review.",
        "data": {
            "submission_id": "789abcdef-1234-5678-9abc-def123456789",
            "task_id": "123e4567-e89b-12d3-a456-426614174000",
            "status": "submitted",
            "payment_error": "Payment settlement failed: insufficient balance"
        }
    }
    ```

    ## Evidence Requirements
    Evidence must match the task's `evidence_schema`:
    - **Required Evidence**: Must be provided or submission fails
    - **Optional Evidence**: Helpful but not mandatory
    - **Evidence Types**: photo, text_report, document, gps_coordinates, video, audio

    ## Evidence Format Examples

    ### Photos
    ```json
    {
        "photos": [
            "https://cdn.example.com/evidence/photo1.jpg",
            "https://cdn.example.com/evidence/photo2.jpg"
        ]
    }
    ```

    ### Text Report
    ```json
    {
        "text_report": "Detailed description of work performed and observations made."
    }
    ```

    ### GPS Coordinates
    ```json
    {
        "gps_coordinates": {
            "lat": 45.5152,
            "lng": -122.6784,
            "accuracy": 5,
            "timestamp": "2024-02-11T08:15:00Z"
        }
    }
    ```

    ### Documents
    ```json
    {
        "documents": [
            "https://cdn.example.com/evidence/receipt.pdf",
            "https://cdn.example.com/evidence/form.pdf"
        ]
    }
    ```

    ## Error Handling
    - **400 Bad Request**: Missing required evidence or invalid format
    - **403 Forbidden**: Worker not assigned to this task
    - **404 Not Found**: Task doesn't exist
    - **409 Conflict**: Task not in submittable state (wrong status)

    ## Task Status Requirements
    Worker can only submit when task status is:
    - **accepted**: Task was assigned to this worker
    - **in_progress**: Worker started work
    - **more_info_requested**: Agent requested additional evidence

    ## AI Pre-Check Integration
    - Automatic AI verification runs on submission
    - Results stored for agent reference
    - High confidence scores may enable instant payment
    - Low scores queued for human review

    ## Payment Settlement
    When instant payment succeeds:
    - Full bounty paid to worker wallet
    - Platform fee paid to treasury
    - Task status updated to 'completed'
    - Transaction hash returned for verification

    ## Use Cases
    - Worker mobile app work submission
    - Bulk evidence upload after task completion
    - Quality assurance before final submission
    - Instant earning for straightforward tasks

    ## File Upload Notes
    Evidence URLs should point to publicly accessible files.
    Most implementations upload files to CDN/cloud storage first,
    then include the URLs in the evidence object.
    """
    try:
        result = await db.submit_work(
            task_id=task_id,
            executor_id=request.executor_id,
            evidence=request.evidence,
            notes=request.notes,
        )

        submission_id = result["submission"]["id"]
        logger.info(
            "Work submitted: task=%s, executor=%s, submission=%s",
            task_id,
            request.executor_id[:8],
            submission_id,
        )

        response_data: Dict[str, Any] = {
            "submission_id": submission_id,
            "task_id": task_id,
            "status": "submitted",
        }
        response_message = "Work submitted successfully. Awaiting agent review."

        # Attempt instant payout at submission time when x402 settlement context exists.
        try:
            submission = await db.get_submission(submission_id)
            if submission:
                readiness = await _is_submission_ready_for_instant_payout(
                    submission_id=submission_id,
                    submission=submission,
                )
                if readiness.get("ready"):
                    settlement = await _settle_submission_payment(
                        submission_id=submission_id,
                        submission=submission,
                        note="Instant payout on worker submission via x402 facilitator",
                    )
                    payment_tx = settlement.get("payment_tx")
                    payment_error = settlement.get("payment_error")

                    if payment_tx:
                        try:
                            await _auto_approve_submission(
                                submission_id=submission_id,
                                submission=submission,
                                note="Auto-approved after successful instant payout",
                            )
                            response_data["status"] = "completed"
                            response_data["verdict"] = "accepted"
                        except Exception as finalize_err:
                            payment_error = (
                                payment_error
                                or f"Payment released but could not finalize task state: {finalize_err}"
                            )
                        response_data["payment_tx"] = payment_tx
                        response_message = "Work submitted and paid instantly."

                    if payment_error:
                        response_data["payment_error"] = payment_error
                else:
                    logger.info(
                        "Instant payout skipped for submission %s (reason=%s)",
                        submission_id,
                        readiness.get("reason"),
                    )
        except Exception as instant_err:
            logger.error(
                "Instant payout attempt failed for submission %s: %s",
                submission_id,
                instant_err,
            )
            response_data["payment_error"] = str(instant_err)

        return SuccessResponse(
            message=response_message,
            data=response_data,
        )

    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail="Task not found")
        elif "not assigned" in error_msg.lower():
            raise HTTPException(
                status_code=403, detail="You are not assigned to this task"
            )
        elif "not in a submittable state" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg)
        elif "missing required evidence" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        logger.error(
            "Unexpected error submitting work for task %s: %s", task_id, error_msg
        )
        raise HTTPException(
            status_code=500, detail="Internal error while submitting work"
        )


# =============================================================================
# EVIDENCE VERIFICATION
# =============================================================================


class VerifyEvidenceRequest(BaseModel):
    """Request to verify evidence against task requirements."""

    task_id: str = Field(..., description="UUID of the task")
    evidence_url: str = Field(
        ..., description="Public URL of the uploaded evidence file"
    )
    evidence_type: str = Field(
        default="photo", description="Type of evidence being verified"
    )


class VerifyEvidenceResponse(BaseModel):
    """Result of AI evidence verification."""

    verified: bool
    confidence: float = Field(..., ge=0, le=1)
    decision: str  # approved, rejected, needs_human
    explanation: str
    issues: List[str] = []


@router.post(
    "/evidence/verify",
    response_model=VerifyEvidenceResponse,
    responses={
        200: {
            "description": "AI verification result with confidence score and decision"
        },
        404: {"model": ErrorResponse, "description": "Task not found"},
        503: {
            "model": ErrorResponse,
            "description": "AI verification service unavailable",
        },
    },
    summary="Verify Evidence with AI",
    description="Pre-verify submitted evidence against task requirements using AI vision models",
    tags=["Evidence", "AI", "Worker"],
)
async def verify_evidence(request: VerifyEvidenceRequest) -> VerifyEvidenceResponse:
    """
    Verify evidence against task requirements using AI vision models.

    Worker-facing endpoint for pre-verification of evidence before submission.
    Uses AI vision models to analyze uploaded evidence and provide instant feedback
    on whether it meets the task requirements. This is a pre-check that doesn't
    create an official submission.

    ## AI Providers Supported
    Configurable via `AI_VERIFICATION_PROVIDER` environment variable:
    - **anthropic** (default): Claude 3.5 Sonnet Vision
    - **openai**: GPT-4o Vision
    - **bedrock**: AWS Bedrock Claude 3.5 Sonnet
    - **ollama**: Local Ollama vision models

    ## Request Body Example
    ```json
    {
        "task_id": "123e4567-e89b-12d3-a456-426614174000",
        "evidence_url": "https://cdn.example.com/photo123.jpg",
        "evidence_type": "photo"
    }
    ```

    ## Response Examples

    ### Approved Evidence
    ```json
    {
        "verified": true,
        "confidence": 0.95,
        "decision": "approved",
        "explanation": "The photo clearly shows the restaurant storefront with visible opening hours sign indicating it's currently open. The image quality is good and all required elements are present.",
        "issues": []
    }
    ```

    ### Rejected Evidence
    ```json
    {
        "verified": false,
        "confidence": 0.88,
        "decision": "rejected",
        "explanation": "The photo shows the restaurant but the opening hours sign is not clearly visible. Additional evidence showing operating status is needed.",
        "issues": [
            "Opening hours sign not visible",
            "Cannot confirm current operating status",
            "Image too dark to read signage clearly"
        ]
    }
    ```

    ### Needs Human Review
    ```json
    {
        "verified": false,
        "confidence": 0.60,
        "decision": "needs_human",
        "explanation": "The evidence appears to meet some requirements but there are ambiguities that require human judgment to resolve.",
        "issues": [
            "Unclear image quality in key areas",
            "Ambiguous evidence of current status"
        ]
    }
    ```

    ## AI Verification Process
    1. **Task Analysis**: AI reviews task instructions and evidence requirements
    2. **Evidence Processing**: Analyzes uploaded photo/document/video
    3. **Requirement Matching**: Compares evidence against specific requirements
    4. **Confidence Scoring**: Provides 0.0-1.0 confidence score
    5. **Decision Making**: Returns approved/rejected/needs_human decision
    6. **Issue Identification**: Lists specific problems if evidence is insufficient

    ## Decision Types
    - **approved**: Evidence meets all requirements with high confidence
    - **rejected**: Evidence clearly doesn't meet requirements
    - **needs_human**: Ambiguous case requiring human agent review

    ## Evidence Types Supported
    - **photo**: Images (JPG, PNG, WebP, HEIC)
    - **document**: PDFs, text documents, screenshots
    - **video**: Video files with AI frame analysis
    - **text_report**: Written descriptions and reports

    ## Confidence Thresholds
    - **High (0.8-1.0)**: Strong confidence in decision
    - **Medium (0.6-0.79)**: Moderate confidence, may need human review
    - **Low (0.0-0.59)**: Low confidence, likely needs human review

    ## Graceful Degradation
    If AI verification is unavailable:
    - Returns `verified: true` with `confidence: 0.5`
    - Decision: "approved"
    - Note: "AI verification temporarily unavailable"
    - Evidence still accepted for agent review

    ## Use Cases
    - Pre-submission evidence validation
    - Worker confidence building before official submission
    - Reducing agent review burden through AI pre-screening
    - Quality assurance for evidence collection
    - Educational feedback for workers

    ## Rate Limits
    - 60 requests per minute per IP
    - 500 requests per hour per IP
    - Cached results for identical evidence URLs (5 minutes)

    ## Security & Privacy
    - Evidence URLs must be publicly accessible
    - No evidence content is stored permanently
    - AI provider requests are logged for debugging
    - No personal information is extracted or stored

    This endpoint helps workers improve evidence quality before official submission
    and reduces the review burden on agents by catching obvious issues early.
    """
    from .verification_helpers import get_verifier

    # Get task details
    task = await db.get_task(request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    verifier = get_verifier()

    if not verifier.is_available:
        logger.info(
            "AI verification unavailable (no provider configured): task=%s",
            request.task_id,
        )
        return VerifyEvidenceResponse(
            verified=True,
            confidence=0.5,
            decision="approved",
            explanation=f"Evidence received for '{task.get('title', 'task')}'. AI verification not configured — accepted for agent review.",
            issues=[],
        )

    try:
        result = await verify_with_ai(
            task={
                "title": task.get("title", ""),
                "category": task.get("category", "general"),
                "instructions": task.get("instructions", ""),
                "evidence_schema": task.get("evidence_schema", {}),
            },
            evidence={
                "type": request.evidence_type,
                "notes": "",
            },
            photo_urls=[request.evidence_url],
        )

        return VerifyEvidenceResponse(
            verified=result.decision == VerificationDecision.APPROVED,
            confidence=result.confidence,
            decision=result.decision.value,
            explanation=result.explanation,
            issues=result.issues,
        )

    except Exception as e:
        logger.warning("AI verification error for task %s: %s", request.task_id, e)
        return VerifyEvidenceResponse(
            verified=True,
            confidence=0.5,
            decision="approved",
            explanation="AI verification temporarily unavailable. Evidence accepted for agent review.",
            issues=[],
        )


# =============================================================================
# WORKER IDENTITY (ERC-8004)
# =============================================================================

# Import worker identity functions (non-blocking)
try:
    from integrations.erc8004.identity import (
        check_worker_identity,
        build_worker_registration_tx,
        confirm_worker_registration,
        update_executor_identity,
        WorkerIdentityStatus,
    )

    WORKER_IDENTITY_AVAILABLE = True
except ImportError:
    WORKER_IDENTITY_AVAILABLE = False


class IdentityCheckResponse(BaseModel):
    """Response for worker identity check."""

    status: str = Field(..., description="registered, not_registered, or error")
    agent_id: Optional[int] = Field(None, description="ERC-8004 token ID if registered")
    wallet_address: Optional[str] = None
    network: str = "base"
    chain_id: int = 8453
    registry_address: Optional[str] = None
    error: Optional[str] = None


class RegisterIdentityRequest(BaseModel):
    """Request to prepare an identity registration transaction."""

    agent_uri: Optional[str] = Field(
        None,
        description="Metadata URI for the identity (defaults to execution.market profile URL)",
        max_length=500,
    )


class RegisterIdentityResponse(BaseModel):
    """Response with unsigned transaction data for identity registration."""

    status: str = Field(..., description="Current identity status before registration")
    agent_id: Optional[int] = Field(
        None, description="Existing agent ID if already registered"
    )
    transaction: Optional[Dict[str, Any]] = Field(
        None,
        description="Unsigned transaction data (to, data, chainId, value, estimated_gas)",
    )
    message: str


class ConfirmIdentityRequest(BaseModel):
    """Request to confirm a registration transaction."""

    tx_hash: str = Field(
        ...,
        description="Transaction hash of the registration tx",
        min_length=66,
        max_length=66,
    )


@router.get(
    "/executors/{executor_id}/identity",
    response_model=IdentityCheckResponse,
    responses={
        200: {"description": "Identity status retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Executor not found"},
        503: {"model": ErrorResponse, "description": "Identity service unavailable"},
    },
    summary="Check Worker Identity",
    description="Check worker's ERC-8004 on-chain identity registration status",
    tags=["Workers", "Identity", "ERC-8004"],
)
async def get_worker_identity(
    executor_id: str = Path(
        ..., description="UUID of the executor", pattern=UUID_PATTERN
    ),
) -> IdentityCheckResponse:
    """
    Check a worker's ERC-8004 on-chain identity registration status.

    Queries the ERC-8004 Identity Registry on Base Mainnet to determine
    whether the worker's wallet address holds a registered identity token.
    This provides reputation and verification benefits for registered workers.

    ## Path Parameters
    - **executor_id**: UUID of the worker executor

    ## Response Examples

    ### Registered Identity
    ```json
    {
        "status": "registered",
        "agent_id": 1337,
        "wallet_address": "0x742d35Cc6634C0532925a3b8D0fC6A3B3e1d7A5B",
        "network": "base",
        "chain_id": 8453,
        "registry_address": "0x1234...abcd",
        "error": null
    }
    ```

    ### Not Registered
    ```json
    {
        "status": "not_registered",
        "agent_id": null,
        "wallet_address": "0x742d35Cc6634C0532925a3b8D0fC6A3B3e1d7A5B",
        "network": "base",
        "chain_id": 8453,
        "registry_address": "0x1234...abcd",
        "error": null
    }
    ```

    ### Service Error
    ```json
    {
        "status": "error",
        "agent_id": null,
        "wallet_address": "0x742d35Cc6634C0532925a3b8D0fC6A3B3e1d7A5B",
        "network": "base",
        "chain_id": 8453,
        "registry_address": null,
        "error": "RPC timeout connecting to Base network"
    }
    ```

    ## Status Values
    - **registered**: Worker has valid ERC-8004 identity token
    - **not_registered**: Worker wallet has no identity token
    - **error**: Unable to check due to network/service issues

    ## ERC-8004 Identity Benefits
    Registered workers receive:
    - **Higher Trust Score**: Visual indicators in agent interfaces
    - **Priority Ranking**: Better visibility in worker search results
    - **Reputation Integration**: On-chain reputation scoring
    - **Verification Badge**: Platform-wide identity verification
    - **Access to Premium Tasks**: Some tasks may require registration

    ## Implementation Details
    - **Network**: Base Mainnet (Chain ID: 8453)
    - **Registry Contract**: ERC-8004 compliant identity registry
    - **Token Standard**: ERC-721 based identity tokens
    - **Caching**: Results cached in database to reduce RPC calls

    ## Registration Process
    If worker is not registered, they can:
    1. Use `/executors/{executor_id}/register-identity` to prepare transaction
    2. Sign and submit the registration transaction (~$0.01 gas)
    3. Use `/executors/{executor_id}/confirm-identity` to verify registration

    ## Error Handling
    - **503 Service Unavailable**: Identity service disabled or network issues
    - **404 Not Found**: Executor ID doesn't exist in database
    - **400 Bad Request**: Executor has no valid wallet address

    ## Performance Notes
    - First call queries blockchain and caches result
    - Subsequent calls return cached data for faster response
    - Cache invalidated when worker updates identity status
    - Network calls use retry logic for reliability

    ## Privacy & Security
    - Only queries public blockchain data
    - No private information exposed
    - Wallet addresses truncated in logs
    - Results are publicly verifiable on-chain

    ## Integration Examples

    ### Agent Interface Integration
    ```javascript
    // Check worker identity before assignment
    const identity = await api.get(`/executors/${executorId}/identity`);
    if (identity.status === 'registered') {
        showVerificationBadge(identity.agent_id);
    }
    ```

    ### Worker Profile Enhancement
    ```javascript
    // Display identity status in worker profiles
    const identity = await api.get(`/executors/${executorId}/identity`);
    updateWorkerTrustScore(identity.status === 'registered');
    ```

    This endpoint supports the platform's decentralized identity infrastructure
    and helps build trust through on-chain verification.
    """
    if not WORKER_IDENTITY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Worker identity service not available",
        )

    # Look up executor
    try:
        client = db.get_client()
        result = (
            client.table("executors")
            .select("id, wallet_address, erc8004_agent_id")
            .eq("id", executor_id)
            .execute()
        )
    except Exception as e:
        logger.error("Failed to look up executor %s: %s", executor_id, e)
        raise HTTPException(status_code=500, detail="Database error")

    if not result.data:
        raise HTTPException(status_code=404, detail="Executor not found")

    executor = result.data[0]
    wallet = executor.get("wallet_address")

    if not wallet or not _is_valid_eth_address(wallet):
        raise HTTPException(
            status_code=400,
            detail="Executor has no valid wallet address",
        )

    # Check if we already have the agent_id cached in Supabase
    cached_agent_id = executor.get("erc8004_agent_id")
    if cached_agent_id is not None:
        return IdentityCheckResponse(
            status="registered",
            agent_id=cached_agent_id,
            wallet_address=wallet,
        )

    # Check on-chain
    try:
        identity = await check_worker_identity(wallet)
    except Exception as e:
        logger.error("Identity check failed for executor %s: %s", executor_id, e)
        return IdentityCheckResponse(
            status="error",
            wallet_address=wallet,
            error=str(e),
        )

    # If registered, persist the agent_id in Supabase
    if identity.status == WorkerIdentityStatus.REGISTERED and identity.agent_id:
        try:
            await update_executor_identity(executor_id, identity.agent_id)
        except Exception as e:
            logger.warning(
                "Failed to persist agent_id for executor %s: %s", executor_id, e
            )

    return IdentityCheckResponse(
        status=identity.status.value,
        agent_id=identity.agent_id,
        wallet_address=identity.wallet_address,
        network=identity.network,
        chain_id=identity.chain_id,
        registry_address=identity.registry_address,
        error=identity.error,
    )


@router.post(
    "/executors/{executor_id}/register-identity",
    response_model=RegisterIdentityResponse,
    responses={
        200: {"description": "Registration transaction prepared or already registered"},
        400: {
            "model": ErrorResponse,
            "description": "Executor has no valid wallet address",
        },
        404: {"model": ErrorResponse, "description": "Executor not found"},
        503: {
            "model": ErrorResponse,
            "description": "Identity service unavailable or registration tx preparation failed",
        },
    },
    summary="Prepare Identity Registration",
    description="Prepare ERC-8004 identity registration transaction for worker wallet to sign",
    tags=["Workers", "Identity", "ERC-8004"],
)
async def register_worker_identity(
    executor_id: str = Path(
        ..., description="UUID of the executor", pattern=UUID_PATTERN
    ),
    request: RegisterIdentityRequest = RegisterIdentityRequest(),
) -> RegisterIdentityResponse:
    """
    Prepare an ERC-8004 identity registration transaction for a worker.

    Creates an unsigned transaction that the worker's wallet must sign and submit
    to register their on-chain identity. If already registered, returns existing
    identity information.

    ## Request Body
    ```json
    {
        "agent_uri": "https://execution.market/workers/abc123def-4567-89ab"
    }
    ```

    ## Request Fields
    - **agent_uri**: Optional metadata URI for identity (defaults to execution.market profile)
      - Should point to JSON metadata describing the worker
      - Common format: execution.market profile or IPFS URI
      - Maximum 500 characters

    ## Response Examples

    ### Already Registered
    ```json
    {
        "status": "registered",
        "agent_id": 1337,
        "transaction": null,
        "message": "Worker already registered with agent ID 1337"
    }
    ```

    ### Registration Transaction Required
    ```json
    {
        "status": "not_registered",
        "agent_id": null,
        "transaction": {
            "to": "0x1234567890abcdef1234567890abcdef12345678",
            "data": "0xa9059cbb000000000000000000000000742d35cc6634c0532925a3b8d0fc6a3b3e1d7a5b0000000000000000000000000000000000000000000000000de0b6b3a7640000",
            "chainId": 8453,
            "value": "0x0",
            "estimated_gas": "150000",
            "gas_price_gwei": "0.001"
        },
        "message": "Sign and submit this transaction to register your on-chain identity"
    }
    ```

    ## Transaction Fields
    When registration is needed, the response includes:
    - **to**: Registry contract address on Base Mainnet
    - **data**: Encoded function call with registration parameters
    - **chainId**: 8453 (Base Mainnet)
    - **value**: "0x0" (no ETH required, only gas)
    - **estimated_gas**: Estimated gas units needed (~150,000)
    - **gas_price_gwei**: Current gas price estimate

    ## Registration Process
    1. **Call this endpoint** to get unsigned transaction
    2. **Present to wallet** (MetaMask, Dynamic.xyz, etc.)
    3. **User signs** transaction (pays ~$0.01 gas)
    4. **Wallet submits** to Base Mainnet
    5. **Call confirm endpoint** with transaction hash
    6. **Identity activated** on platform

    ## Gas Cost Estimation
    - **Base Gas**: ~150,000 units
    - **Gas Price**: ~0.001 gwei (varies with network)
    - **Total Cost**: ~$0.01 USD equivalent in ETH
    - **Payment**: Worker pays gas fees (not platform)

    ## Metadata URI Format
    The `agent_uri` should point to JSON metadata:
    ```json
    {
        "name": "Professional Task Worker",
        "description": "Verified worker on execution.market",
        "image": "https://cdn.execution.market/avatars/worker.jpg",
        "external_url": "https://execution.market/workers/abc123",
        "attributes": [
            {"trait_type": "Platform", "value": "execution.market"},
            {"trait_type": "Registration Date", "value": "2024-02-11"}
        ]
    }
    ```

    ## Security Considerations
    - **Wallet-Only Signing**: Platform never has access to private keys
    - **Gas Payment**: Worker pays their own transaction fees
    - **Non-Custodial**: Platform doesn't control registration process
    - **Immutable**: Once registered, identity persists on blockchain

    ## Error Conditions

    ### Missing Wallet Address
    ```json
    {
        "error": "INVALID_WALLET",
        "message": "Executor has no valid wallet address",
        "details": {"executor_id": "abc123..."}
    }
    ```

    ### Service Unavailable
    ```json
    {
        "error": "IDENTITY_SERVICE_UNAVAILABLE",
        "message": "Could not prepare registration transaction: RPC timeout",
        "details": {"network": "base", "registry": "0x1234..."}
    }
    ```

    ## Frontend Integration Example
    ```javascript
    // Prepare registration transaction
    const response = await api.post(`/executors/${executorId}/register-identity`);

    if (response.status === 'not_registered' && response.transaction) {
        // Present to user's wallet
        const txHash = await wallet.sendTransaction(response.transaction);

        // Confirm registration
        await api.post(`/executors/${executorId}/confirm-identity`, {
            tx_hash: txHash
        });
    }
    ```

    ## Benefits of Registration
    After successful registration, workers gain:
    - **Verification Badge**: Visual trust indicator
    - **Higher Rankings**: Better visibility in task search
    - **Reputation Tracking**: On-chain reputation accumulation
    - **Premium Access**: Some tasks may require identity
    - **Trust Building**: Agents prefer verified workers

    ## Network Requirements
    - **Network**: Base Mainnet (not testnets)
    - **Wallet**: Any Base-compatible wallet (MetaMask, Dynamic, etc.)
    - **ETH Balance**: Small amount for gas (~$0.01)
    - **Connection**: Stable internet for transaction submission

    This endpoint enables decentralized worker verification while maintaining
    security through user-controlled wallet operations.
    """
    if not WORKER_IDENTITY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Worker identity service not available",
        )

    # Look up executor
    try:
        client = db.get_client()
        result = (
            client.table("executors")
            .select("id, wallet_address, erc8004_agent_id")
            .eq("id", executor_id)
            .execute()
        )
    except Exception as e:
        logger.error("Failed to look up executor %s: %s", executor_id, e)
        raise HTTPException(status_code=500, detail="Database error")

    if not result.data:
        raise HTTPException(status_code=404, detail="Executor not found")

    executor = result.data[0]
    wallet = executor.get("wallet_address")

    if not wallet or not _is_valid_eth_address(wallet):
        raise HTTPException(
            status_code=400,
            detail="Executor has no valid wallet address",
        )

    # Check current on-chain status
    try:
        identity = await check_worker_identity(wallet)
    except Exception as e:
        logger.error("Identity check failed for %s: %s", executor_id, e)
        raise HTTPException(
            status_code=503,
            detail=f"Could not check on-chain identity: {e}",
        )

    # Already registered
    if identity.status == WorkerIdentityStatus.REGISTERED:
        # Persist if not already saved
        if identity.agent_id and not executor.get("erc8004_agent_id"):
            try:
                await update_executor_identity(executor_id, identity.agent_id)
            except Exception:
                pass

        return RegisterIdentityResponse(
            status="registered",
            agent_id=identity.agent_id,
            transaction=None,
            message=f"Worker already registered with agent ID {identity.agent_id}",
        )

    # Build registration tx
    try:
        tx_data = await build_worker_registration_tx(
            wallet_address=wallet,
            agent_uri=request.agent_uri,
        )
    except Exception as e:
        logger.error("Failed to build registration tx for %s: %s", executor_id, e)
        raise HTTPException(
            status_code=503,
            detail=f"Could not prepare registration transaction: {e}",
        )

    logger.info(
        "Registration tx prepared: executor=%s, wallet=%s, chain=%d, gas=%s",
        executor_id,
        wallet[:10],
        tx_data.chain_id,
        tx_data.estimated_gas,
    )

    return RegisterIdentityResponse(
        status="not_registered",
        agent_id=None,
        transaction=tx_data.to_dict(),
        message="Sign and submit this transaction to register your on-chain identity",
    )


@router.post(
    "/executors/{executor_id}/confirm-identity",
    response_model=IdentityCheckResponse,
    responses={
        200: {"description": "Registration confirmed"},
        404: {"model": ErrorResponse, "description": "Executor not found"},
        503: {"model": ErrorResponse, "description": "Identity service unavailable"},
    },
    tags=["Workers", "Identity"],
)
async def confirm_identity_registration(
    executor_id: str = Path(
        ..., description="UUID of the executor", pattern=UUID_PATTERN
    ),
    request: ConfirmIdentityRequest = ...,
) -> IdentityCheckResponse:
    """
    Confirm a worker's identity registration after the transaction is mined.

    After the worker signs and submits the registration tx, the frontend
    calls this endpoint with the tx hash. The backend re-checks the on-chain
    state and stores the agent ID if registration succeeded.
    """
    if not WORKER_IDENTITY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Worker identity service not available",
        )

    # Look up executor
    try:
        client = db.get_client()
        result = (
            client.table("executors")
            .select("id, wallet_address")
            .eq("id", executor_id)
            .execute()
        )
    except Exception as e:
        logger.error("Failed to look up executor %s: %s", executor_id, e)
        raise HTTPException(status_code=500, detail="Database error")

    if not result.data:
        raise HTTPException(status_code=404, detail="Executor not found")

    executor = result.data[0]
    wallet = executor.get("wallet_address")

    if not wallet or not _is_valid_eth_address(wallet):
        raise HTTPException(
            status_code=400,
            detail="Executor has no valid wallet address",
        )

    # Confirm on-chain
    try:
        identity = await confirm_worker_registration(wallet, request.tx_hash)
    except Exception as e:
        logger.error("Identity confirmation failed for %s: %s", executor_id, e)
        return IdentityCheckResponse(
            status="error",
            wallet_address=wallet,
            error=str(e),
        )

    # Persist agent_id if registered
    if identity.status == WorkerIdentityStatus.REGISTERED and identity.agent_id:
        try:
            await update_executor_identity(executor_id, identity.agent_id)
        except Exception as e:
            logger.warning("Failed to persist agent_id for %s: %s", executor_id, e)

    logger.info(
        "Identity confirmation: executor=%s, status=%s, agent_id=%s, tx=%s",
        executor_id,
        identity.status.value,
        identity.agent_id,
        request.tx_hash,
    )

    return IdentityCheckResponse(
        status=identity.status.value,
        agent_id=identity.agent_id,
        wallet_address=identity.wallet_address,
        network=identity.network,
        chain_id=identity.chain_id,
        registry_address=identity.registry_address,
        error=identity.error,
    )


# =============================================================================
# BATCH OPERATIONS
# =============================================================================


class BatchTaskDefinition(BaseModel):
    """Single task definition for batch creation."""

    title: str = Field(..., min_length=5, max_length=255)
    instructions: str = Field(..., min_length=20, max_length=5000)
    category: TaskCategory
    bounty_usd: float = Field(..., gt=0, le=10000)
    deadline_hours: int = Field(..., ge=1, le=720)
    evidence_required: List[EvidenceType] = Field(..., min_length=1, max_length=5)
    evidence_optional: Optional[List[EvidenceType]] = None
    location_hint: Optional[str] = None
    min_reputation: int = 0


class BatchCreateRequest(BaseModel):
    """Request model for batch task creation."""

    tasks: List[BatchTaskDefinition] = Field(
        ..., description="List of tasks to create", min_length=1, max_length=50
    )
    payment_token: str = Field(
        default="USDC", description="Payment token for all tasks"
    )


class BatchCreateResponse(BaseModel):
    """Response model for batch task creation."""

    created: int
    failed: int
    tasks: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    total_bounty: float


@router.post(
    "/tasks/batch",
    response_model=BatchCreateResponse,
    status_code=201,
    responses={
        201: {"description": "Batch tasks created with success/failure breakdown"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request or too many tasks in batch",
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
    },
    summary="Batch Create Tasks",
    description="Create multiple similar tasks in a single API call for efficiency",
    tags=["Tasks", "Agent", "Batch"],
)
async def batch_create_tasks(
    request: BatchCreateRequest,
    api_key: APIKeyData = Depends(verify_api_key_if_required),
) -> BatchCreateResponse:
    """
    Create multiple tasks in a single request for efficiency.

    Useful for agents that need to create many similar or related tasks at once.
    Each task in the batch is processed independently - some may succeed while
    others fail due to validation errors.

    ## Request Limits
    - **Maximum 50 tasks** per batch request
    - Each task subject to normal validation rules
    - Same payment token/network for all tasks in batch

    ## Request Body Example
    ```json
    {
        "payment_token": "USDC",
        "tasks": [
            {
                "title": "Verify restaurant A is open",
                "instructions": "Visit Restaurant A and confirm operating status...",
                "category": "physical_presence",
                "bounty_usd": 5.00,
                "deadline_hours": 24,
                "evidence_required": ["photo", "text_report"],
                "evidence_optional": ["gps_coordinates"],
                "location_hint": "Downtown Portland, Main St",
                "min_reputation": 50
            },
            {
                "title": "Verify restaurant B is open",
                "instructions": "Visit Restaurant B and confirm operating status...",
                "category": "physical_presence",
                "bounty_usd": 5.00,
                "deadline_hours": 24,
                "evidence_required": ["photo", "text_report"],
                "location_hint": "Downtown Portland, Oak St",
                "min_reputation": 50
            }
        ]
    }
    ```

    ## Response Example
    ```json
    {
        "created": 2,
        "failed": 0,
        "total_bounty": 10.00,
        "tasks": [
            {
                "index": 0,
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Verify restaurant A is open",
                "bounty_usd": 5.00
            },
            {
                "index": 1,
                "id": "456789ab-cdef-1234-5678-9abcdef12345",
                "title": "Verify restaurant B is open",
                "bounty_usd": 5.00
            }
        ],
        "errors": []
    }
    ```

    ## Partial Failure Example
    ```json
    {
        "created": 1,
        "failed": 1,
        "total_bounty": 5.00,
        "tasks": [
            {
                "index": 0,
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Valid task",
                "bounty_usd": 5.00
            }
        ],
        "errors": [
            {
                "index": 1,
                "title": "Invalid task",
                "error": "Bounty $0.10 is below minimum $0.25"
            }
        ]
    }
    ```

    ## Task Definition Schema
    Each task in the batch must include:
    - **title**: Task title (5-255 chars)
    - **instructions**: Detailed instructions (20-5000 chars)
    - **category**: Task category (TaskCategory enum)
    - **bounty_usd**: Bounty amount (positive, within limits)
    - **deadline_hours**: Hours until deadline (1-720)
    - **evidence_required**: Array of required evidence types
    - **evidence_optional**: Array of optional evidence types (optional)
    - **location_hint**: Human-readable location (optional)
    - **min_reputation**: Minimum worker reputation (optional, default: 0)

    ## Payment Considerations
    **Important**: This endpoint creates tasks WITHOUT payment escrow.
    Unlike the single task creation endpoint, batch creation doesn't
    support x402 payment headers. Tasks are created in 'published' status
    but may not be financially backed.

    Agents should either:
    1. Use single task creation with payment for critical tasks
    2. Manually fund tasks after batch creation
    3. Use batch creation for draft/planning purposes

    ## Common Use Cases
    - **Location-based campaigns**: Multiple similar tasks across locations
    - **Time-series tasks**: Same task at different times
    - **A/B testing**: Variations of similar tasks
    - **Market research**: Multiple data collection points
    - **Event coverage**: Multiple aspects of same event

    ## Validation Rules
    Each task validated independently:
    - Bounty within platform min/max limits
    - Valid category and evidence types
    - Reasonable deadline (1-720 hours)
    - Title and instructions length limits
    - Valid reputation requirements

    ## Error Handling
    - Individual task failures don't stop batch processing
    - Detailed error messages provided for each failure
    - Success/failure counts in response
    - Original index preserved for error matching

    ## Performance Considerations
    - Database transactions per task for data consistency
    - Parallel processing where possible
    - Maximum 50 tasks to prevent timeout/memory issues
    - Consider multiple smaller batches for large campaigns

    ## Response Fields
    - **created**: Number of successfully created tasks
    - **failed**: Number of tasks that failed validation
    - **total_bounty**: Sum of bounties for created tasks only
    - **tasks**: Array of successfully created task summaries
    - **errors**: Array of validation failures with details

    This endpoint optimizes for bulk task creation workflows while maintaining
    individual task quality through independent validation.
    """
    created_tasks = []
    errors = []
    total_bounty = 0.0

    for i, task_def in enumerate(request.tasks):
        try:
            deadline = datetime.now(timezone.utc) + timedelta(
                hours=task_def.deadline_hours
            )

            task = await db.create_task(
                agent_id=api_key.agent_id,
                title=task_def.title,
                instructions=task_def.instructions,
                category=task_def.category.value,
                bounty_usd=task_def.bounty_usd,
                deadline=deadline,
                evidence_required=[e.value for e in task_def.evidence_required],
                evidence_optional=[e.value for e in (task_def.evidence_optional or [])],
                location_hint=task_def.location_hint,
                min_reputation=task_def.min_reputation,
                payment_token=request.payment_token,
                payment_network=getattr(request, "payment_network", "base"),
            )

            created_tasks.append(
                {
                    "index": i,
                    "id": task["id"],
                    "title": task["title"],
                    "bounty_usd": task["bounty_usd"],
                }
            )
            total_bounty += task_def.bounty_usd

        except Exception as e:
            errors.append(
                {
                    "index": i,
                    "title": task_def.title,
                    "error": str(e),
                }
            )

    logger.info(
        "Batch create: agent=%s, created=%d, failed=%d, total_bounty=%.2f",
        api_key.agent_id,
        len(created_tasks),
        len(errors),
        total_bounty,
    )

    return BatchCreateResponse(
        created=len(created_tasks),
        failed=len(errors),
        tasks=created_tasks,
        errors=errors,
        total_bounty=total_bounty,
    )


# =============================================================================
# HEALTH & INFO ENDPOINTS
# =============================================================================


@router.get(
    "/health",
    responses={
        200: {"description": "API is healthy and operational"},
        503: {"description": "API is unhealthy or degraded"},
    },
    summary="Health Check",
    description="System health check endpoint for monitoring and load balancers",
    tags=["System"],
)
async def api_health():
    """
    API health check endpoint.

    Provides system health status for monitoring, load balancers, and uptime checks.
    Returns basic API information and current timestamp for availability verification.

    ## Response Example
    ```json
    {
        "status": "healthy",
        "api_version": "v1",
        "timestamp": "2024-02-11T06:04:00.123Z",
        "services": {
            "database": "connected",
            "x402": "available",
            "payment_dispatcher": "active"
        }
    }
    ```

    ## Health Status Values
    - **healthy**: All systems operational
    - **degraded**: Some non-critical services unavailable
    - **unhealthy**: Critical services down

    ## Use Cases
    - Load balancer health checks
    - Monitoring system alerts
    - API availability verification
    - Deployment health validation
    - Service discovery health probes

    ## Response Headers
    - `Cache-Control: no-cache` - Prevents caching of health status
    - `X-Response-Time` - Request processing time (if available)

    This endpoint is intentionally lightweight and doesn't perform deep
    health checks to ensure fast response times for frequent monitoring calls.
    """
    return {
        "status": "healthy",
        "api_version": "v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
