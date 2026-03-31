"""
Core MCP Tools for Execution Market (Employer Tools)

Tools that AI agents use to publish, manage, and review tasks:
- em_publish_task: Publish a new task for human execution
- em_approve_submission: Approve or reject a submission
- em_cancel_task: Cancel a published task

Extracted from server.py following the register_*_tools() pattern.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


@dataclass
class CoreToolsConfig:
    """Configuration for core employer tools."""

    character_limit: int = 25000


def register_core_tools(
    mcp: FastMCP,
    db_module: Any,
    x402_sdk: Optional[Any] = None,
    fee_manager: Optional[Any] = None,
    config: Optional[CoreToolsConfig] = None,
) -> dict:
    """
    Register core employer tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        db_module: Database module (supabase_client)
        x402_sdk: Optional x402 SDK client
        fee_manager: Optional FeeManager instance
        config: Optional configuration

    Returns:
        Dict mapping tool names to their async callables (for re-export).
    """
    config = config or CoreToolsConfig()

    # Store in mutable container so tests can patch server.db and it takes effect
    _ctx = {"db": db_module, "x402_sdk": x402_sdk, "fee_manager": fee_manager}

    # Lazy imports to avoid circular dependencies
    from models import (
        PublishTaskInput,
        ApproveSubmissionInput,
        CancelTaskInput,
    )
    from utils.formatting import format_bounty, format_datetime

    def _get_db():
        """Get db module — allows test patching via server.db."""
        try:
            import server as srv

            return srv.db
        except (ImportError, AttributeError):
            return _ctx["db"]

    def _get_x402_sdk():
        try:
            import server as srv

            return srv.x402_sdk
        except (ImportError, AttributeError):
            return _ctx["x402_sdk"]

    def _get_fee_manager():
        try:
            import server as srv

            return srv.fee_manager
        except (ImportError, AttributeError):
            return _ctx["fee_manager"]

    # ------------------------------------------------------------------ #
    # Helpers that access server-level singletons via lazy import
    # ------------------------------------------------------------------ #

    def _get_payment_dispatcher():
        try:
            from integrations.x402.payment_dispatcher import get_dispatcher

            return get_dispatcher()
        except ImportError:
            return None

    def _get_advanced_escrow_available():
        try:
            from tools.escrow_tools import ADVANCED_ESCROW_AVAILABLE

            return ADVANCED_ESCROW_AVAILABLE
        except ImportError:
            return False

    async def _dispatch_task_webhook(event_type: str, task: Dict, agent_id: str):
        """Delegate to server module's webhook dispatcher."""
        try:
            import server as srv

            await srv.dispatch_task_webhook(event_type, task, agent_id)
        except Exception as e:
            logger.debug("Webhook dispatch skipped: %s", e)

    async def _dispatch_submission_webhook(
        event_type: str, submission: Dict, task: Dict, agent_id: str
    ):
        try:
            import server as srv

            await srv.dispatch_submission_webhook(
                event_type, submission, task, agent_id
            )
        except Exception as e:
            logger.debug("Webhook dispatch skipped: %s", e)

    async def _notify_task_created(task: Dict):
        try:
            import server as srv

            await srv.notify_task_created(task)
        except Exception as e:
            logger.debug("WS notify skipped: %s", e)

    async def _notify_task_cancelled(task: Dict, reason: Optional[str], refund: bool):
        try:
            import server as srv

            await srv.notify_task_cancelled(task, reason, refund)
        except Exception as e:
            logger.debug("WS notify skipped: %s", e)

    async def _notify_submission_verdict(
        submission: Dict, verdict: str, executor_id: str, task: Optional[Dict]
    ):
        try:
            import server as srv

            await srv.notify_submission_verdict(submission, verdict, executor_id, task)
        except Exception as e:
            logger.debug("WS notify skipped: %s", e)

    async def _notify_payment_released(payment_info: Dict, task: Dict, worker_id: str):
        try:
            import server as srv

            await srv.notify_payment_released(payment_info, task, worker_id)
        except Exception as e:
            logger.debug("WS notify skipped: %s", e)

    async def _log_payment_event(**kwargs):
        try:
            from integrations.x402.payment_events import log_payment_event

            await log_payment_event(**kwargs)
        except Exception as e:
            logger.debug("Payment event log skipped: %s", e)

    def _resolve_mcp_payment_header(
        task_id: Optional[str], escrow_tx: Optional[str] = None
    ) -> Optional[str]:
        try:
            import server as srv

            return srv._resolve_mcp_payment_header(task_id, escrow_tx)
        except Exception:
            return escrow_tx

    def _auto_register_agent_executor_mcp(wallet: str, agent_name: str = None):
        try:
            import server as srv

            srv._auto_register_agent_executor_mcp(wallet, agent_name=agent_name)
        except Exception as e:
            logger.debug("Auto-register skipped: %s", e)

    # ------------------------------------------------------------------ #
    # em_publish_task
    # ------------------------------------------------------------------ #

    @mcp.tool(
        name="em_publish_task",
        annotations={
            "title": "Publish Task for Human Execution",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_publish_task(params: PublishTaskInput) -> str:
        """
        Publish a new task for human execution in the Execution Market.

        This tool creates a task that human executors can browse, accept, and complete.
        Tasks require evidence of completion which the agent can later verify.

        Args:
            params (PublishTaskInput): Validated input parameters containing:
                - agent_id (str): Your agent identifier (wallet or ERC-8004 ID)
                - title (str): Short task title (5-255 chars)
                - instructions (str): Detailed instructions (20-5000 chars)
                - category (TaskCategory): Task category
                - bounty_usd (float): Payment amount in USD (0-10000)
                - deadline_hours (int): Hours until deadline (1-720)
                - evidence_required (List[EvidenceType]): Required evidence types
                - evidence_optional (List[EvidenceType]): Optional evidence types
                - location_hint (str): Location description
                - min_reputation (int): Minimum executor reputation
                - payment_token (str): Payment token symbol (default: USDC)
                - payment_network (str): Payment network (default: base)

        Returns:
            str: Success message with task ID and details, or error message.
        """
        try:
            deadline = datetime.now(timezone.utc) + timedelta(
                hours=params.deadline_hours
            )

            # Calculate fees
            fee_breakdown = None
            if _get_fee_manager():
                try:
                    fee_breakdown = _get_fee_manager().calculate_fee(
                        bounty=params.bounty_usd,
                        category=params.category,
                    )
                except Exception as e:
                    logger.warning("Could not calculate fees: %s", e)

            # Auto-geocode location_hint
            _loc_lat = params.location_lat
            _loc_lng = params.location_lng
            _loc_radius = params.location_radius_km
            if params.location_hint and (_loc_lat is None or _loc_lng is None):
                try:
                    from integrations.geocoding import geocode_location

                    geo = await geocode_location(params.location_hint)
                    if geo:
                        _loc_lat = geo.lat
                        _loc_lng = geo.lng
                        _loc_radius = geo.radius_km
                        logger.info(
                            "[MCP] Auto-geocoded '%s' -> (%s, %s) radius=%skm",
                            params.location_hint,
                            geo.lat,
                            geo.lng,
                            geo.radius_km,
                        )
                except Exception as e:
                    logger.warning(
                        "[MCP] Geocoding failed for '%s': %s", params.location_hint, e
                    )

            task = await _get_db().create_task(
                agent_id=params.agent_id,
                title=params.title,
                instructions=params.instructions,
                category=params.category.value,
                bounty_usd=params.bounty_usd,
                deadline=deadline,
                evidence_required=[e.value for e in params.evidence_required],
                evidence_optional=[e.value for e in params.evidence_optional]
                if params.evidence_optional
                else None,
                location_hint=params.location_hint,
                min_reputation=params.min_reputation or 0,
                payment_token=params.payment_token or "USDC",
                payment_network=params.payment_network or "base",
                location_lat=_loc_lat,
                location_lng=_loc_lng,
                location_radius_km=_loc_radius,
                skill_version=params.skill_version,
            )

            # Payment authorization via dispatcher
            escrow_info = None
            balance_warning = None
            dispatcher = _get_payment_dispatcher()
            ADVANCED_ESCROW_AVAILABLE = _get_advanced_escrow_available()
            if dispatcher:
                try:
                    mode = dispatcher.get_mode()
                    if mode == "fase2":
                        auth_result = await dispatcher.authorize_payment(
                            task_id=task["id"],
                            receiver=params.agent_id,
                            amount_usdc=Decimal(str(params.bounty_usd)),
                            network=params.payment_network or "base",
                            token=params.payment_token or "USDC",
                        )
                        escrow_info = {
                            "escrow_id": task["id"],
                            "status": auth_result.get("escrow_status", "deposited"),
                            "deposit_tx": auth_result.get("tx_hash") or "",
                        }
                        if auth_result.get("success") and auth_result.get(
                            "payment_info_serialized"
                        ):
                            try:
                                import supabase_client as sdb

                                sdb_client = sdb.get_client()
                                total_locked = Decimal(
                                    str(params.bounty_usd)
                                ) * Decimal("1.08")
                                sdb_client.table("escrows").upsert(
                                    {
                                        "task_id": task["id"],
                                        "status": "deposited",
                                        "total_amount_usdc": float(total_locked),
                                        "beneficiary_address": auth_result.get(
                                            "payer_address", ""
                                        ),
                                        "metadata": {
                                            "payment_info": auth_result[
                                                "payment_info_serialized"
                                            ],
                                        },
                                    },
                                    on_conflict="task_id",
                                ).execute()
                            except Exception as db_err:
                                logger.warning(
                                    "Failed to store fase2 escrow metadata for task %s: %s",
                                    task["id"],
                                    db_err,
                                )
                        if not auth_result.get("success"):
                            balance_warning = (
                                f"Escrow lock failed: {auth_result.get('error', 'unknown')}. "
                                "Task created but funds are NOT locked."
                            )
                    elif mode == "fase1":
                        total_check = Decimal(str(params.bounty_usd)) * Decimal("1.08")
                        auth_result = await dispatcher.authorize_payment(
                            task_id=task["id"],
                            receiver=params.agent_id,
                            amount_usdc=total_check,
                            network=params.payment_network or "base",
                            token=params.payment_token or "USDC",
                        )
                        escrow_info = {
                            "escrow_id": task["id"],
                            "status": auth_result.get(
                                "escrow_status", "balance_verified"
                            ),
                            "deposit_tx": "",
                        }
                        if auth_result.get("warning"):
                            balance_warning = auth_result["warning"]
                    elif ADVANCED_ESCROW_AVAILABLE:
                        from integrations.x402.advanced_escrow_integration import (
                            authorize_task_bounty,
                        )

                        escrow_result = authorize_task_bounty(
                            task_id=task["id"],
                            receiver=params.agent_id,
                            amount_usdc=Decimal(str(params.bounty_usd)),
                        )
                        escrow_info = {
                            "escrow_id": task["id"],
                            "status": escrow_result.status
                            if hasattr(escrow_result, "status")
                            else "authorized",
                            "deposit_tx": getattr(escrow_result, "tx_hash", "") or "",
                        }
                    else:
                        escrow_info = {
                            "escrow_id": task["id"],
                            "status": "pending",
                            "deposit_tx": "",
                        }
                except Exception as e:
                    logger.warning(
                        "Payment authorization failed for task %s: %s", task["id"], e
                    )
            elif _get_x402_sdk():
                escrow_info = {
                    "escrow_id": task["id"],
                    "status": "pending",
                    "deposit_tx": "",
                }
                logger.info("Escrow recorded (SDK-only) for task %s", task["id"])

            # Auto-register agent in executor directory
            try:
                _auto_register_agent_executor_mcp(
                    params.agent_id, agent_name=params.agent_name
                )
            except Exception as e:
                logger.warning(
                    "Auto-register agent executor failed (non-blocking): %s", e
                )

            # Lifecycle checkpoint: task created via MCP
            try:
                from audit.checkpoint_updater import init_checkpoint

                await init_checkpoint(
                    task["id"],
                    skill_version=params.skill_version,
                    network=params.payment_network or "base",
                    token=params.payment_token or "USDC",
                    bounty_usdc=params.bounty_usd,
                )
            except Exception:
                pass  # Non-blocking

            # Dispatch webhook
            await _dispatch_task_webhook("task_created", task, params.agent_id)

            # Event Bus publish (coexists with legacy — Strangler Fig)
            try:
                from events import get_event_bus, EMEvent, EventSource

                await get_event_bus().publish(
                    EMEvent(
                        event_type="task.created",
                        task_id=task["id"],
                        source=EventSource.MCP_TOOL,
                        payload={
                            "task_id": task["id"],
                            "title": task["title"],
                            "category": task["category"],
                            "bounty_usd": task.get("bounty_usd", 0),
                            "agent_id": params.agent_id,
                            "status": task["status"],
                            "payment_network": task.get("payment_network", "base"),
                        },
                    )
                )
            except Exception:
                pass

            # Notify via WebSocket
            await _notify_task_created(task)

            response = f"""# Task Published Successfully

**Task ID**: `{task["id"]}`
**Title**: {task["title"]}
**Bounty**: {format_bounty(params.bounty_usd)} {params.payment_token or "USDC"}
**Deadline**: {format_datetime(deadline.isoformat())}
**Status**: PUBLISHED
"""

            if fee_breakdown:
                response += f"""
## Fee Breakdown
- **Worker Receives**: {format_bounty(float(fee_breakdown.worker_amount))} ({100 - float(fee_breakdown.fee_rate) * 100:.0f}%)
- **Platform Fee**: {format_bounty(float(fee_breakdown.fee_amount))} ({float(fee_breakdown.fee_rate) * 100:.0f}%)
"""

            if escrow_info:
                response += f"""
## Escrow
- **Escrow ID**: `{escrow_info.get("escrow_id", "N/A")}`
- **Status**: {escrow_info.get("status", "deposited").upper()}
- **Tx**: `{escrow_info.get("deposit_tx", "N/A")[:16]}...`
"""

            if balance_warning:
                response += f"""
## Balance Warning
{balance_warning}
"""

            response += """
The task is now visible to human executors. Use `em_get_task` with the task ID to monitor progress, or `em_check_submission` when a human submits evidence."""

            return response

        except Exception as e:
            return f"Error: Failed to publish task - {str(e)}"

    # ------------------------------------------------------------------ #
    # em_approve_submission
    # ------------------------------------------------------------------ #

    @mcp.tool(
        name="em_approve_submission",
        annotations={
            "title": "Approve or Reject Submission",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_approve_submission(params: ApproveSubmissionInput) -> str:
        """
        Approve or reject a submission from a human executor.

        Use this after reviewing the evidence submitted by a human.
        - "accepted": Task is complete, payment will be released
        - "disputed": Opens a dispute (evidence insufficient)
        - "more_info_requested": Ask for additional evidence

        Args:
            params (ApproveSubmissionInput): Validated input parameters containing:
                - submission_id (str): UUID of the submission
                - agent_id (str): Your agent ID (for authorization)
                - verdict (SubmissionVerdict): accepted, disputed, or more_info_requested
                - notes (str): Explanation of your verdict

        Returns:
            str: Confirmation of the verdict.
        """
        try:
            # Fetch submission without changing verdict yet (pay-before-mark pattern)
            submission = await _get_db().get_submission(params.submission_id)
            if not submission:
                return f"Error: Submission {params.submission_id} not found"

            # Verify ownership
            task = submission.get("task")
            if (
                not task
                or (task.get("agent_id") or "").lower()
                != (params.agent_id or "").lower()
            ):
                return "Error: Not authorized to update this submission"

            task_id = task.get("id") if task else None
            if task_id:
                task = await _get_db().get_task(task_id) or task

            # Handle payment release on approval via PaymentDispatcher
            # IMPORTANT: Pay BEFORE marking accepted — if payment fails, don't change verdict
            payment_info = None
            if params.verdict.value == "accepted" and task:
                worker_wallet = submission.get("executor", {}).get("wallet_address")
                if worker_wallet:
                    try:
                        dispatcher = _get_payment_dispatcher()
                        if dispatcher:
                            payment_header = None
                            if dispatcher.get_mode() == "preauth":
                                payment_header = _resolve_mcp_payment_header(
                                    task["id"], task.get("escrow_tx")
                                )

                            payment_info = await dispatcher.release_payment(
                                task_id=task["id"],
                                worker_address=worker_wallet,
                                bounty_amount=Decimal(str(task["bounty_usd"])),
                                payment_header=payment_header,
                                network=task.get("payment_network"),
                                token=task.get("payment_token", "USDC"),
                                worker_auth_header=params.payment_auth_worker,
                                fee_auth_header=params.payment_auth_fee,
                            )
                            logger.info(
                                "Payment released via dispatcher (%s) for task %s: success=%s",
                                dispatcher.get_mode(),
                                task["id"],
                                payment_info.get("success"),
                            )
                            # Update escrow row status for fase2/x402r
                            if payment_info.get("success") and payment_info.get(
                                "mode"
                            ) in ("fase2", "x402r"):
                                try:
                                    import supabase_client as sdb

                                    sdb_client = sdb.get_client()
                                    sdb_client.table("escrows").update(
                                        {"status": "released"}
                                    ).eq("task_id", task["id"]).execute()
                                except Exception as db_err:
                                    logger.warning(
                                        "Failed to update escrow status for task %s: %s",
                                        task["id"],
                                        db_err,
                                    )
                        elif _get_x402_sdk():
                            payment_header = _resolve_mcp_payment_header(
                                task["id"], task.get("escrow_tx")
                            )
                            payment_info = await _get_x402_sdk().settle_task_payment(
                                task_id=task["id"],
                                payment_header=payment_header or "",
                                worker_address=worker_wallet,
                                bounty_amount=Decimal(str(task["bounty_usd"])),
                            )
                    except Exception as e:
                        logger.error(
                            "Payment settlement failed for task %s: %s", task["id"], e
                        )

                    # Dispatch payment webhook
                    try:
                        import server as srv

                        if (
                            payment_info
                            and srv.webhook_registry
                            and srv.WebhookEventType
                            and srv.PaymentPayload
                        ):
                            tx_hash = payment_info.get("tx_hash", "")
                            payload = srv.PaymentPayload(
                                task_id=task["id"],
                                amount_usdc=task["bounty_usd"],
                                recipient=worker_wallet,
                                tx_hash=tx_hash,
                            )
                            event = srv.WebhookEvent(
                                event_type=srv.WebhookEventType.PAYMENT_RELEASED,
                                payload=payload,
                            )
                            webhooks = srv.webhook_registry.get_by_owner_and_event(
                                params.agent_id, srv.WebhookEventType.PAYMENT_RELEASED
                            )
                            for webhook in webhooks:
                                await srv.send_webhook(
                                    url=webhook.url,
                                    event=event,
                                    secret=srv.webhook_registry.get_secret(
                                        webhook.webhook_id
                                    ),
                                    webhook_id=webhook.webhook_id,
                                )
                    except Exception as e:
                        logger.error("Failed to dispatch payment webhook: %s", e)

            # For accepted verdict, require successful payment before marking
            if params.verdict.value == "accepted" and task:
                if not payment_info or not payment_info.get("success"):
                    error_detail = (payment_info or {}).get(
                        "error", "Payment settlement failed"
                    )
                    return f"Error: Payment failed — submission NOT approved. Detail: {error_detail}"

            # NOW mark the verdict in DB (payment succeeded or verdict is not accepted)
            submission = await _get_db().update_submission(
                submission_id=params.submission_id,
                agent_id=params.agent_id,
                verdict=params.verdict.value,
                notes=params.notes,
            )

            # Dispatch submission verdict webhook
            if task:
                event_type = (
                    "submission_approved"
                    if params.verdict.value == "accepted"
                    else "submission_rejected"
                )
                await _dispatch_submission_webhook(
                    event_type, submission, task, params.agent_id
                )

            # Event Bus publish (coexists with legacy — Strangler Fig)
            if task:
                try:
                    from events import get_event_bus, EMEvent, EventSource

                    eb_event_type = (
                        "submission.approved"
                        if params.verdict.value == "accepted"
                        else "submission.rejected"
                    )
                    eb_payload = {
                        "task_id": task["id"],
                        "submission_id": params.submission_id,
                        "verdict": params.verdict.value,
                        "bounty_usd": task.get("bounty_usd", 0),
                        "agent_id": params.agent_id,
                    }
                    if payment_info and payment_info.get("tx_hash"):
                        eb_payload["tx_hash"] = payment_info["tx_hash"]
                        eb_payload["amount_usd"] = payment_info.get("amount_usd", 0)
                        eb_payload["chain"] = payment_info.get("chain", "base")
                    await get_event_bus().publish(
                        EMEvent(
                            event_type=eb_event_type,
                            task_id=task["id"],
                            source=EventSource.MCP_TOOL,
                            payload=eb_payload,
                        )
                    )
                except Exception:
                    pass

            # Notify via WebSocket
            executor_id = submission.get("executor_id")
            if executor_id and task:
                await _notify_submission_verdict(
                    submission, params.verdict.value, executor_id, task
                )

            # Notify payment release if approved
            if params.verdict.value == "accepted" and payment_info and executor_id:
                await _notify_payment_released(payment_info, task, executor_id)

            # ── Lifecycle Checkpoints (non-blocking) ──
            if task and params.verdict.value == "accepted":
                try:
                    from audit.checkpoint_updater import (
                        mark_approved,
                        mark_payment_released,
                    )

                    await mark_approved(task["id"])
                    if payment_info and payment_info.get("success"):
                        await mark_payment_released(
                            task["id"],
                            tx_hash=payment_info.get("tx_hash"),
                            worker_amount=payment_info.get("net_to_worker")
                            or payment_info.get("amount"),
                            fee_amount=payment_info.get("platform_fee"),
                        )
                except Exception:
                    pass  # Non-blocking

            verdict_display = {
                "accepted": "APPROVED",
                "disputed": "DISPUTED",
                "more_info_requested": "MORE INFO REQUESTED",
            }

            response = f"""# Submission {verdict_display.get(params.verdict.value, params.verdict.value.upper())}

**Submission ID**: `{params.submission_id}`
**Verdict**: {params.verdict.value}
{f"**Notes**: {params.notes}" if params.notes else ""}
"""

            if params.verdict.value == "accepted":
                response += """
The task has been marked as completed and the executor will receive payment."""
                if payment_info:
                    tx_hash = payment_info.get("tx_hash", "N/A")
                    if isinstance(tx_hash, list):
                        tx_hash = tx_hash[0] if tx_hash else "N/A"
                    worker_amount = (
                        payment_info.get("net_to_worker")
                        or payment_info.get("amount")
                        or 0
                    )
                    fee_amount = payment_info.get("platform_fee") or 0
                    task_network = (
                        (task.get("payment_network") or "base") if task else "base"
                    )
                    from api.routers._helpers import _build_explorer_url

                    tx_hash_str = str(tx_hash)
                    explorer_url = _build_explorer_url(tx_hash_str, task_network)
                    response += f"""

## Payment Details
- **Network**: {task_network}
- **Worker Payment**: ${float(worker_amount):.2f}
- **Platform Fee**: ${float(fee_amount):.2f}
- **Transaction**: `{tx_hash_str}`"""
                    if explorer_url:
                        response += f"\n- **Explorer**: {explorer_url}"
            else:
                response += "\nThe executor has been notified of your decision."

            return response

        except Exception as e:
            return f"Error: Failed to update submission - {str(e)}"

    # ------------------------------------------------------------------ #
    # em_cancel_task
    # ------------------------------------------------------------------ #

    @mcp.tool(
        name="em_cancel_task",
        annotations={
            "title": "Cancel Published Task",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_cancel_task(params: CancelTaskInput) -> str:
        """
        Cancel a task you published (only if still in 'published' or 'accepted' status).

        Use this if you no longer need the task completed.

        Args:
            params (CancelTaskInput): Validated input parameters containing:
                - task_id (str): UUID of the task to cancel
                - agent_id (str): Your agent ID (for authorization)
                - reason (str): Reason for cancellation

        Returns:
            str: Confirmation of cancellation.
        """
        try:
            # Status guard: verify task is in a cancellable state before proceeding
            task_check = await _get_db().get_task(params.task_id)
            if not task_check:
                return f"Error: Task {params.task_id} not found"
            if (task_check.get("agent_id") or "").lower() != (
                params.agent_id or ""
            ).lower():
                return "Error: Not authorized to cancel this task"

            task_status = task_check.get("status", "")
            cancellable_statuses = {"published", "accepted"}
            if task_status not in cancellable_statuses:
                return (
                    f"Error: Cannot cancel task with status '{task_status}'. "
                    f"Only tasks in {sorted(cancellable_statuses)} can be cancelled."
                )
            if task_status == "accepted":
                escrow_mode = os.environ.get("EM_ESCROW_MODE", "platform_release")
                if escrow_mode != "direct_release":
                    return (
                        "Error: Cannot cancel accepted task in platform_release escrow mode. "
                        "Only direct_release mode supports cancelling accepted tasks."
                    )

            task = await _get_db().cancel_task(params.task_id, params.agent_id)

            # Handle escrow refund via PaymentDispatcher
            refund_info = None
            try:
                dispatcher = _get_payment_dispatcher()
                refund_result = await dispatcher.refund_payment(
                    task_id=params.task_id,
                    reason=params.reason,
                )
                if refund_result.get("success"):
                    refund_info = {
                        "amount_refunded": task.get("bounty_usd", 0),
                        "tx_hash": refund_result.get("tx_hash", ""),
                        "success": True,
                        "status": refund_result.get("status", "refunded"),
                    }
                    await _log_payment_event(
                        task_id=params.task_id,
                        event_type="cancel",
                        status="success",
                        tx_hash=refund_result.get("tx_hash", ""),
                        metadata={
                            "mode": refund_result.get("mode"),
                            "refund_status": refund_result.get("status"),
                            "reason": params.reason,
                            "source": "em_cancel_task",
                        },
                    )
                    # Update escrow row status for fase2/x402r
                    if refund_result.get("mode") in ("fase2", "x402r"):
                        try:
                            import supabase_client as sdb

                            sdb_client = sdb.get_client()
                            sdb_client.table("escrows").update(
                                {"status": "refunded"}
                            ).eq("task_id", params.task_id).execute()
                        except Exception as db_err:
                            logger.warning(
                                "Failed to update escrow status for task %s: %s",
                                params.task_id,
                                db_err,
                            )
                    logger.info(
                        "Payment refunded via PaymentDispatcher for task %s (mode=%s, status=%s)",
                        params.task_id,
                        refund_result.get("mode"),
                        refund_result.get("status"),
                    )
                else:
                    logger.warning(
                        "PaymentDispatcher refund returned non-success for task %s: %s",
                        params.task_id,
                        refund_result.get("error"),
                    )
            except Exception as e:
                logger.warning("Could not refund payment via PaymentDispatcher: %s", e)

            # ── Lifecycle Checkpoints (non-blocking) ──
            try:
                from audit.checkpoint_updater import mark_cancelled, mark_refunded

                await mark_cancelled(params.task_id)
                if refund_info and refund_info.get("success"):
                    await mark_refunded(
                        params.task_id, tx_hash=refund_info.get("tx_hash")
                    )
            except Exception:
                pass  # Non-blocking

            # Dispatch webhook
            await _dispatch_task_webhook("task_cancelled", task, params.agent_id)

            # Event Bus publish (coexists with legacy — Strangler Fig)
            try:
                from events import get_event_bus, EMEvent, EventSource

                await get_event_bus().publish(
                    EMEvent(
                        event_type="task.cancelled",
                        task_id=params.task_id,
                        source=EventSource.MCP_TOOL,
                        payload={
                            "task_id": params.task_id,
                            "title": task.get("title", ""),
                            "agent_id": params.agent_id,
                            "reason": params.reason or "",
                            "refund_initiated": refund_info is not None,
                        },
                    )
                )
            except Exception:
                pass

            # Notify via WebSocket
            await _notify_task_cancelled(task, params.reason, refund_info is not None)

            response = f"""# Task Cancelled

**Task ID**: `{params.task_id}`
**Title**: {task["title"]}
**Status**: CANCELLED
{f"**Reason**: {params.reason}" if params.reason else ""}

The task is no longer available for human executors."""

            if refund_info:
                response += f"""

## Refund
- **Amount Refunded**: ${refund_info.get("amount_refunded", 0):.2f}
- **Transaction**: `{refund_info.get("tx_hash", "N/A")[:16]}...`"""

            return response

        except Exception as e:
            return f"Error: Failed to cancel task - {str(e)}"

    # Return references for re-export (tests import these from server module)
    return {
        "em_publish_task": em_publish_task,
        "em_approve_submission": em_approve_submission,
        "em_cancel_task": em_cancel_task,
    }
