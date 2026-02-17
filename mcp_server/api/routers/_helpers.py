"""
Shared helper functions for Execution Market API routes.

Extracted from the monolithic routes.py for maintainability.
Contains payment, escrow, reputation, and utility helpers.
"""

import logging
import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any

import supabase_client as db

# x402 SDK payment verification and settlement (re-exported to sub-routers)
try:
    from integrations.x402.sdk_client import (
        verify_x402_payment,  # noqa: F401
        get_sdk,  # noqa: F401
        SDK_AVAILABLE as X402_AVAILABLE,
    )
except ImportError:
    X402_AVAILABLE = False

    def verify_x402_payment(*args, **kwargs):  # type: ignore[misc]
        return None

    def get_sdk():  # type: ignore[misc]
        return None


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


# Payment event audit trail (re-exported to sub-routers)
from integrations.x402.payment_events import log_payment_event  # noqa: F401


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
DEFAULT_PLATFORM_FEE_PERCENT = Decimal("0.13")


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
# Trustless direct_release: escrow not yet locked (waiting for assignment).
PENDING_ASSIGNMENT_ESCROW_STATUSES = {"pending_assignment"}
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

    All operations are best-effort -- failures are logged and recorded in the
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

    # ---- WS-3: Gas dust for worker on-chain reputation -------------------
    try:
        ws3_enabled = await PlatformConfig.is_feature_enabled("gas_dust_auto_fund")
        if ws3_enabled and worker_address and executor_id:
            from integrations.gas_dust import fund_worker_gas_dust

            tx_hash = await fund_worker_gas_dust(
                wallet_address=worker_address,
                executor_id=executor_id,
            )
            if tx_hash:
                logger.info(
                    "WS-3 gas dust funded: submission=%s, worker=%s, tx=%s",
                    submission_id,
                    worker_address[:10],
                    tx_hash[:16],
                )
    except Exception as e:
        logger.error(
            "WS-3 gas dust error (non-blocking): submission=%s, error=%s",
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

    # Guard 1: DB check -- fast path
    existing_agent_id = executor.get("erc8004_agent_id")
    if existing_agent_id:
        logger.info(
            "WS-1 skip: executor %s already has erc8004_agent_id=%s (DB)",
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
                "source": "database",
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

    # Guard 2: On-chain check -- verify wallet holds ERC-8004 NFT directly
    try:
        from integrations.erc8004.identity import (
            check_worker_identity,
            update_executor_identity,
        )

        onchain_result = await check_worker_identity(worker_address)
        if onchain_result.status.value == "registered" and onchain_result.agent_id:
            logger.info(
                "WS-1 skip: wallet %s already holds ERC-8004 NFT agent_id=%s (on-chain)",
                worker_address[:10],
                onchain_result.agent_id,
            )
            # Sync DB with on-chain truth
            if executor_id:
                await update_executor_identity(executor_id, onchain_result.agent_id)

            effect = await enqueue_side_effect(
                supabase=db.get_client(),
                submission_id=submission_id,
                effect_type="register_worker_identity",
                payload={
                    "task_id": task_id,
                    "skip_reason": "already_registered",
                    "agent_id": onchain_result.agent_id,
                    "source": "on_chain",
                },
            )
            if effect:
                await mark_side_effect(
                    supabase=db.get_client(),
                    effect_id=effect["id"],
                    status="skipped",
                    error="already_registered_on_chain",
                )
            return
    except Exception as e:
        # Non-blocking: if on-chain check fails, proceed to registration attempt
        logger.warning(
            "WS-1: on-chain identity check failed (proceeding): wallet=%s, error=%s",
            worker_address[:10],
            e,
        )

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
                tx_hash=None,  # gasless -- facilitator tx, not directly available
            )
            logger.info(
                "WS-1 success: worker %s registered as agent_id=%s on %s",
                worker_address[:10],
                reg_result.agent_id,
                task_network,
            )
        else:
            err = reg_result.error or "registration_returned_no_agent_id"
            # Permanent errors: skip instead of retrying forever
            err_lower = err.lower()
            is_permanent = any(
                s in err_lower
                for s in (
                    "already registered",
                    "already exists",
                    "duplicate",
                    "invalid",
                )
            )
            await mark_side_effect(
                supabase=db.get_client(),
                effect_id=effect["id"],
                status="skipped" if is_permanent else "failed",
                error=err,
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
        # Fallback: use platform's own ERC-8004 agent ID (EM_AGENT_ID env var)
        try:
            agent_erc8004_id = EM_AGENT_ID
            logger.info(
                "WS-2: task %s missing erc8004_agent_id, using platform EM_AGENT_ID=%d",
                task_id,
                agent_erc8004_id,
            )
        except Exception:
            logger.info("WS-2 skip: no numeric agent ERC-8004 ID for task %s", task_id)
            effect = await enqueue_side_effect(
                supabase=db.get_client(),
                submission_id=submission_id,
                effect_type="rate_agent_from_worker",
                payload={
                    "task_id": task_id,
                    "skip_reason": "missing_agent_erc8004_id",
                },
            )
            if effect:
                await mark_side_effect(
                    supabase=db.get_client(),
                    effect_id=effect["id"],
                    status="skipped",
                    error="missing_agent_erc8004_id",
                )
            return

    # Guard: verify agent exists on-chain before sending feedback
    try:
        from integrations.erc8004.identity import verify_agent_identity

        agent_identity = await verify_agent_identity(
            str(agent_erc8004_id), network=task.get("payment_network", "base")
        )
        if not agent_identity.get("registered"):
            logger.warning(
                "WS-2 skip: agent %d not found on-chain for task %s",
                agent_erc8004_id,
                task_id,
            )
            effect = await enqueue_side_effect(
                supabase=db.get_client(),
                submission_id=submission_id,
                effect_type="rate_agent_from_worker",
                payload={
                    "task_id": task_id,
                    "skip_reason": "agent_not_found_on_chain",
                    "agent_id": agent_erc8004_id,
                },
            )
            if effect:
                await mark_side_effect(
                    supabase=db.get_client(),
                    effect_id=effect["id"],
                    status="skipped",
                    error="agent_not_found_on_chain",
                )
            return
    except Exception as e:
        # Non-blocking: if on-chain check fails, proceed anyway
        logger.warning(
            "WS-2: on-chain agent check failed (proceeding): agent=%d, error=%s",
            agent_erc8004_id,
            e,
        )

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
            err = feedback_result.error or "feedback_submission_failed"
            # Permanent errors: skip instead of retrying forever
            err_lower = err.lower()
            is_permanent = any(
                s in err_lower
                for s in (
                    "not found",
                    "404",
                    "not exist",
                    "invalid agent",
                    "self-feedback",
                )
            )
            await mark_side_effect(
                supabase=db.get_client(),
                effect_id=effect["id"],
                status="skipped" if is_permanent else "failed",
                error=err,
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
    result: Optional[Dict[str, Any]] = None

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
            "BLOCKED: Self-payment attempt for task %s -- worker wallet %s matches agent wallet %s",
            task_id,
            worker_address[:10],
            agent_wallet[:10],
        )
        return {
            "payment_tx": None,
            "payment_error": f"Worker wallet matches agent wallet for task {task_id} -- self-payment blocked",
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

        # Check if this task uses trustless direct_release escrow
        is_direct_release_task = False
        if dispatcher and task_id:
            try:
                client = db.get_client()
                esc_check = (
                    client.table("escrows")
                    .select("metadata")
                    .eq("task_id", task_id)
                    .limit(1)
                    .execute()
                )
                if esc_check.data:
                    esc_meta = esc_check.data[0].get("metadata") or {}
                    if isinstance(esc_meta, str):
                        esc_meta = json.loads(esc_meta)
                    is_direct_release_task = (
                        esc_meta.get("escrow_mode") == "direct_release"
                    )
            except Exception:
                pass

        if dispatcher and is_direct_release_task:
            # Trustless: 1-TX release directly to worker from escrow
            result = await dispatcher.release_direct_to_worker(
                task_id=task_id or "",
                network=task_network,
            )
        elif dispatcher:
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

    ret: Dict[str, Any] = {"payment_tx": release_tx, "payment_error": release_error}
    if result:
        if result.get("fee_tx_hash"):
            ret["fee_tx"] = result["fee_tx_hash"]
        if result.get("fee_distribute_tx"):
            ret["fee_distribute_tx"] = result["fee_distribute_tx"]
        if result.get("escrow_release_tx"):
            ret["escrow_release_tx"] = result["escrow_release_tx"]
        if result.get("mode"):
            ret["payment_mode"] = result["mode"]
        if result.get("platform_fee") is not None:
            ret["platform_fee_usdc"] = float(result["platform_fee"])
        if result.get("worker_net") is not None:
            ret["worker_net_usdc"] = float(result["worker_net"])
        if result.get("gross_amount") is not None:
            ret["gross_amount_usdc"] = float(result["gross_amount"])
    return ret


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

# Human-readable labels for transaction event types (Spanish)
_TX_EVENT_LABELS: Dict[str, str] = {
    "balance_check": "Verificacion de Balance",
    "escrow_authorize": "Deposito Escrow",
    "escrow_release": "Liberacion Escrow",
    "escrow_refund": "Reembolso Escrow",
    "settle": "Liquidacion",
    "settle_worker_direct": "Pago Directo al Worker",
    "settle_fee_direct": "Fee de Plataforma",
    "disburse_worker": "Pago al Worker",
    "disburse_fee": "Fee Plataforma",
    "fee_collect": "Cobro de Fee",
    "refund": "Reembolso al Agente",
    "cancel": "Cancelacion",
    "verify": "Verificacion",
    "store_auth": "Autorizacion Almacenada",
    "error": "Error de Pago",
    "reputation_agent_rates_worker": "Agente Califica Worker",
    "reputation_worker_rates_agent": "Worker Califica Agente",
}

# Explorer URL templates per network
_EXPLORER_TX_URLS: Dict[str, str] = {
    "base": "https://basescan.org/tx/",
    "ethereum": "https://etherscan.io/tx/",
    "polygon": "https://polygonscan.com/tx/",
    "arbitrum": "https://arbiscan.io/tx/",
    "celo": "https://celoscan.io/tx/",
    "avalanche": "https://snowtrace.io/tx/",
    "optimism": "https://optimistic.etherscan.io/tx/",
    "monad": "https://explorer.monad.xyz/tx/",
    "base-sepolia": "https://sepolia.basescan.org/tx/",
    "sepolia": "https://sepolia.etherscan.io/tx/",
}


def _build_explorer_url(
    tx_hash: Optional[str], network: Optional[str]
) -> Optional[str]:
    if not tx_hash:
        return None
    net = (network or "base").lower()
    base_url = _EXPLORER_TX_URLS.get(net, _EXPLORER_TX_URLS["base"])
    h = tx_hash if tx_hash.startswith("0x") else f"0x{tx_hash}"
    return f"{base_url}{h}"
