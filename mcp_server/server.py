#!/usr/bin/env python3
"""
Execution Market MCP Server - Universal Execution Layer

This MCP server allows AI agents to publish tasks for physical-world execution,
monitor submissions, and approve/reject completed work. Executors can be
humans today and robots tomorrow — the protocol is agnostic to what executes.

OpenAPI Metadata:
    Title: Execution Market Universal Execution Layer API
    Version: 1.0.0
    Description: Enable AI agents to delegate real-world tasks to executors
    Contact: ultravioletadao@gmail.com
    License: MIT
    Terms of Service: https://execution.market/terms

API Documentation:
    - API Reference: https://api.execution.market/docs
    - Integration Guide: https://github.com/ultravioleta-dao/execution-market/blob/main/docs/INTEGRATION.md
    - Webhooks Guide: https://github.com/ultravioleta-dao/execution-market/blob/main/docs/WEBHOOKS.md

Integrated Systems:
    - MCP Protocol: Tool invocation via SSE/HTTP (https://api.execution.market/mcp)
    - A2A Protocol: Agent discovery (/.well-known/agent.json)
    - Webhooks: HMAC-SHA256 signed real-time notifications
    - x402 Protocol: Payments and escrow via USDC on Base/Polygon/Optimism
    - Fee Management: 13% platform fee (12% EM + 1% x402r)

Authentication Methods:
    - API Key: X-API-Key header (em_sk_live_xxx)
    - Bearer Token: JWT in Authorization header
    - ERC-8004: Agent Registry identity token

Rate Limits by Tier:
    - Free: 10 req/min, 100 tasks/month
    - Builder: 100 req/min, 10,000 tasks/month
    - Enterprise: 1,000 req/min, unlimited

Available Tools:

Employer Tools (for AI Agents):
    - em_publish_task: Publish a new task for human execution
    - em_get_tasks: Get tasks (filtered by agent, status, category)
    - em_get_task: Get details of a specific task
    - em_check_submission: Check submission status for a task
    - em_approve_submission: Approve or reject a submission
    - em_cancel_task: Cancel a published task
    - em_assign_task: Assign a task to a specific worker
    - em_batch_create_tasks: Create multiple tasks at once
    - em_get_task_analytics: Get task analytics and metrics

Worker Tools (for Human Workers):
    - em_apply_to_task: Apply to work on a task
    - em_submit_work: Submit evidence of completed work
    - em_get_my_tasks: Get assigned tasks and earnings
    - em_withdraw_earnings: Withdraw available balance

Advanced Escrow Tools (PaymentOperator via SDK):
    - em_escrow_recommend_strategy: Get AI-recommended payment strategy
    - em_escrow_authorize: Lock bounty in escrow on-chain
    - em_escrow_release: Release escrowed funds to worker
    - em_escrow_refund: Refund escrowed funds to agent
    - em_escrow_charge: Instant payment without escrow
    - em_escrow_partial_release: Partial release + refund (proof of attempt)
    - em_escrow_dispute: Post-release refund (requires arbitration)
    - em_escrow_status: Query escrow payment state

Utility Tools:
    - em_get_fee_structure: Get platform fee rates by category
    - em_calculate_fee: Calculate fees for a potential task
    - em_server_status: Get server and integration status

Example Requests:

    Publish a task:
        {
            "agent_id": "0x1234...",
            "title": "Verify store hours",
            "instructions": "Visit store at 123 Main St...",
            "category": "physical_presence",
            "bounty_usd": 10.00,
            "deadline_hours": 24,
            "evidence_required": ["photo_geo", "text_response"]
        }

    Check submissions:
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "agent_id": "0x1234...",
            "response_format": "json"
        }

Error Codes:
    - INVALID_AGENT_ID: Agent ID format is invalid
    - TASK_NOT_FOUND: Task with given ID doesn't exist
    - NOT_AUTHORIZED: Not authorized for this action
    - TASK_ALREADY_ASSIGNED: Task already has a worker
    - INSUFFICIENT_REPUTATION: Worker doesn't meet minimum reputation
    - INVALID_EVIDENCE: Evidence doesn't match schema
    - RATE_LIMIT_EXCEEDED: Too many requests
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional

from mcp.server.fastmcp import FastMCP

# Core models
from models import (
    GetTasksInput,
    GetTaskInput,
    CheckSubmissionInput,
    GetArbiterVerdictInput,
    ResolveDisputeInput,
    ResponseFormat,
    TaskCategory,
)

# Database client
import supabase_client as db

# Modular tools
from tools.worker_tools import register_worker_tools, WorkerToolsConfig
from tools.agent_tools import register_agent_tools, AgentToolsConfig
from tools.escrow_tools import register_escrow_tools, ADVANCED_ESCROW_AVAILABLE
from tools.reputation_tools import register_reputation_tools
from tools.agent_executor_tools import (
    register_agent_executor_tools,
    AgentExecutorToolsConfig,
)
from tools.core_tools import register_core_tools
from integrations.x402.payment_dispatcher import (
    get_dispatcher as get_payment_dispatcher,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============== GLOBAL MANAGERS ==============


# Initialize x402 SDK (via facilitator — no direct contract calls)
x402_sdk: Optional[Any] = None
try:
    from integrations.x402.sdk_client import (
        get_sdk,
        SDK_AVAILABLE as X402_SDK_AVAILABLE,
    )

    if X402_SDK_AVAILABLE:
        x402_sdk = get_sdk()
        logger.info("x402 SDK initialized (facilitator: %s)", x402_sdk.facilitator_url)
    else:
        logger.warning("uvd-x402-sdk not installed, payments will be simulated")
except ImportError:
    X402_SDK_AVAILABLE = False
    logger.warning("x402 SDK client not available, payments will be simulated")

# Initialize fee manager (optional)
fee_manager: Optional[Any] = None
try:
    from payments.fees import FeeManager, calculate_platform_fee

    fee_manager = FeeManager(
        treasury_wallet=os.environ.get("EM_TREASURY_ADDRESS"),
    )
    logger.info("Fee manager initialized")
except ImportError:
    logger.warning("Fee manager not available")
    calculate_platform_fee = None

# Initialize WebSocket manager and handlers (optional)
ws_manager: Optional[Any] = None
ws_handlers: Optional[Any] = None
task_notifier: Optional[Any] = None  # Legacy compatibility
try:
    # Try new modular websocket package first
    from websocket import ws_manager as _ws_manager, handlers as _ws_handlers

    ws_manager = _ws_manager
    ws_handlers = _ws_handlers
    task_notifier = _ws_handlers  # Alias for backward compatibility
    logger.info("WebSocket manager and handlers initialized (new module)")
except ImportError:
    try:
        # Fall back to legacy websocket module
        from websocket import ws_manager as _ws_manager, task_notifier as _task_notifier

        ws_manager = _ws_manager
        task_notifier = _task_notifier
        logger.info("WebSocket manager initialized (legacy module)")
    except ImportError:
        logger.warning("WebSocket support not available")

# Initialize webhook registry (optional)
webhook_registry: Optional[Any] = None
try:
    from webhooks import (
        WebhookEventType,
        WebhookEvent,
        TaskPayload,
        SubmissionPayload,
        PaymentPayload,
        get_webhook_registry,
        send_webhook,
    )

    webhook_registry = get_webhook_registry()
    loaded = webhook_registry.load_from_database()
    logger.info(f"Webhook registry initialized ({loaded} webhooks loaded from DB)")
except ImportError:
    logger.warning("Webhook support not available")
    WebhookEventType = None
    WebhookEvent = None
    TaskPayload = None
    SubmissionPayload = None
    PaymentPayload = None
    send_webhook = None


# ============== MCP SERVER SETUP ==============


# OpenAPI/MCP Server Metadata
SERVER_INFO = {
    "name": "execution-market",
    "title": "Execution Market Universal Execution Layer",
    "description": "Enable AI agents to delegate real-world tasks to executors with gasless crypto payments",
    "version": "1.0.0",
    "contact": {
        "name": "Ultravioleta DAO",
        "url": "https://execution.market",
        "email": "ultravioletadao@gmail.com",
    },
    "license": {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
}

# Tool Tags for grouping in documentation
TOOL_TAGS = {
    "employer": {
        "name": "Employer Tools",
        "description": "Tools for AI agents to publish and manage tasks",
    },
    "worker": {
        "name": "Worker Tools",
        "description": "Tools for human workers to find and complete tasks",
    },
    "utility": {
        "name": "Utility Tools",
        "description": "Helper tools for fees, status, and calculations",
    },
}

# streamable_http_path="/" makes endpoint at mount root
# When mounted at /mcp, the full URL is /mcp/ (trailing slash required by Starlette)
mcp = FastMCP(
    SERVER_INFO["name"],
    streamable_http_path="/",
    host="0.0.0.0",
)


# Configure worker tools (NOW-011 to NOW-014)
worker_config = WorkerToolsConfig(
    min_withdrawal_usdc=float(os.environ.get("MIN_WITHDRAWAL_USDC", "5.0")),
    platform_fee_percent=float(os.environ.get("PLATFORM_FEE_PERCENT", "13.0")),
    x402_enabled=x402_sdk is not None,
)

# Register worker tools
register_worker_tools(mcp, db, x402_sdk, worker_config)

# Configure and register agent tools (NOW-015 to NOW-018)
agent_config = AgentToolsConfig(
    enable_eligibility_checks=True,
    max_batch_size=50,
    enable_notifications=True,
)
register_agent_tools(mcp, db)

# Register Advanced Escrow tools (PaymentOperator via SDK)
register_escrow_tools(mcp)

# Register Reputation & Identity tools (WS-4)
register_reputation_tools(mcp, db)

# A2A Agent Executor tools
register_agent_executor_tools(mcp, db, AgentExecutorToolsConfig())

# Core employer tools (em_publish_task, em_approve_submission, em_cancel_task)
_core_tools = register_core_tools(mcp, db, x402_sdk=x402_sdk, fee_manager=fee_manager)
em_publish_task = _core_tools["em_publish_task"]
em_approve_submission = _core_tools["em_approve_submission"]
em_cancel_task = _core_tools["em_cancel_task"]


# ============== CONSTANTS ==============


CHARACTER_LIMIT = 25000


# ============== FORMATTING HELPERS ==============

from utils.formatting import format_bounty, format_datetime  # noqa: E402
from utils.pii import truncate_wallet  # noqa: E402


def format_task_markdown(
    task: Dict[str, Any],
    escrow_info: Optional[Dict[str, Any]] = None,
    application_count: int = 0,
) -> str:
    """Format a task as markdown."""
    lines = [
        f"## {task['title']}",
        f"**ID**: `{task['id']}`",
        f"**Status**: {task['status'].upper()}",
        f"**Category**: {task['category'].replace('_', ' ').title()}",
        f"**Bounty**: {format_bounty(task['bounty_usd'])} {task.get('payment_token', 'USDC')} on {task.get('payment_network', 'base')}",
        f"**Deadline**: {format_datetime(task['deadline'])}",
        "",
        "### Instructions",
        task["instructions"],
        "",
        "### Evidence Required",
    ]

    schema = task.get("evidence_schema", {})
    for ev in schema.get("required", []):
        lines.append(f"- {ev.replace('_', ' ').title()} (required)")
    for ev in schema.get("optional", []):
        lines.append(f"- {ev.replace('_', ' ').title()} (optional)")

    if task.get("location_hint"):
        lines.extend(["", f"**Location**: {task['location_hint']}"])

    if task.get("min_reputation", 0) > 0:
        lines.append(f"**Min Reputation**: {task['min_reputation']}")

    executor = task.get("executor")
    if executor:
        lines.extend(
            [
                "",
                "### Executor",
                f"- **Name**: {executor.get('display_name', 'Unknown')}",
                f"- **Reputation**: {executor.get('reputation_score', 0)}",
            ]
        )

    if escrow_info:
        status = escrow_info.get("status", "unknown").upper()
        lines.extend(
            [
                "",
                "### Escrow",
                f"- **Status**: {status}",
            ]
        )
        if escrow_info.get("amount_usdc"):
            lines.append(f"- **Amount**: ${escrow_info['amount_usdc']} USDC")
        if escrow_info.get("tx_ref"):
            lines.append(f"- **TX**: `{escrow_info['tx_ref']}`")
        if escrow_info.get("network"):
            lines.append(f"- **Network**: {escrow_info['network']}")

    if application_count > 0:
        lines.append(f"\n**Applications**: {application_count} pending")

    lines.extend(
        [
            "",
            f"*Created: {format_datetime(task['created_at'])}*",
        ]
    )

    return "\n".join(lines)


def format_submission_markdown(submission: Dict[str, Any]) -> str:
    """Format a submission as markdown."""
    executor = submission.get("executor", {})

    lines = [
        f"## Submission `{submission['id'][:8]}...`",
        f"**Status**: {submission.get('agent_verdict', 'pending').upper()}",
        f"**Submitted**: {format_datetime(submission['submitted_at'])}",
        "",
        "### Executor",
        f"- **Name**: {executor.get('display_name', 'Unknown')}",
        f"- **Wallet**: `{executor.get('wallet_address', 'N/A')}`",
        f"- **Reputation**: {executor.get('reputation_score', 0)}",
        "",
        "### Evidence",
    ]

    evidence = submission.get("evidence", {})
    for key, value in evidence.items():
        if isinstance(value, dict):
            if "file" in value:
                lines.append(
                    f"- **{key}**: File uploaded ({value.get('filename', 'unknown')})"
                )
            elif "value" in value:
                lines.append(f"- **{key}**: {value['value']}")
        else:
            lines.append(f"- **{key}**: {value}")

    # Auto-check verification results
    if submission.get("auto_check_passed") is not None:
        passed = submission["auto_check_passed"]
        details = submission.get("auto_check_details") or {}
        score = details.get("score", 0)
        status_emoji = "PASS" if passed else "NEEDS REVIEW"
        lines.extend(
            [
                "",
                f"### Automated Verification: {status_emoji} (score: {score:.0%})",
            ]
        )
        checks = details.get("checks", [])
        for check in checks:
            check_icon = "PASS" if check.get("passed") else "FAIL"
            lines.append(
                f"- {check_icon} **{check.get('name', '?')}**: "
                f"{check.get('score', 0):.0%} — {check.get('reason', '')}"
            )
        warnings = details.get("warnings", [])
        for w in warnings:
            lines.append(f"- WARNING: {w}")

        phase = details.get("phase", "A")
        if phase == "A":
            lines.append(
                "- NOTE: Phase B (AI image analysis) pending"
                " — results will update automatically"
            )
        elif phase == "AB":
            lines.append("- Phase: AB (complete)")

        if score >= 0.95:
            lines.append("\nRECOMMENDATION: All checks passed. Safe to approve.")
        elif score >= 0.70:
            lines.append(
                "\nRECOMMENDATION: Most checks passed."
                " Review warnings before approving."
            )
        elif score >= 0.40:
            lines.append(
                "\nRECOMMENDATION: Several checks failed. Inspect evidence carefully."
            )
        else:
            lines.append(
                "\nRECOMMENDATION: Low score. Review each check before deciding."
            )

        if details.get("auto_approved"):
            lines.append(
                "\nAUTO-APPROVED: This submission was automatically"
                " approved by AI verification."
            )

    if submission.get("agent_notes"):
        lines.extend(["", f"**Agent Notes**: {submission['agent_notes']}"])

    return "\n".join(lines)


# ============== WEBHOOK DISPATCH HELPERS ==============


async def dispatch_task_webhook(
    event_type: str,
    task: Dict[str, Any],
    agent_id: str,
) -> None:
    """Dispatch webhook for task events."""
    if not webhook_registry or not WebhookEventType:
        return

    try:
        payload = TaskPayload(
            task_id=task["id"],
            title=task["title"],
            status=task["status"],
            category=task["category"],
            bounty_usd=task["bounty_usd"],
            agent_id=agent_id,
        )
        event = WebhookEvent(event_type=WebhookEventType(event_type), payload=payload)

        # Get webhooks subscribed to this event for this owner
        webhooks = webhook_registry.get_by_owner_and_event(
            agent_id, WebhookEventType(event_type)
        )
        for webhook in webhooks:
            result = await send_webhook(
                url=webhook.url,
                event=event,
                secret=webhook_registry.get_secret(webhook.webhook_id),
                webhook_id=webhook.webhook_id,
            )
            webhook_registry.record_delivery(
                webhook.webhook_id, result.status.value == "delivered"
            )
            logger.debug(f"Dispatched {event_type} webhook to {webhook.url}")
    except Exception as e:
        logger.error(f"Failed to dispatch task webhook: {e}")


async def dispatch_submission_webhook(
    event_type: str,
    submission: Dict[str, Any],
    task: Dict[str, Any],
    agent_id: str,
) -> None:
    """Dispatch webhook for submission events."""
    if not webhook_registry or not WebhookEventType:
        return

    try:
        payload = SubmissionPayload(
            submission_id=submission["id"],
            task_id=task["id"],
            executor_id=submission.get("executor_id", ""),
            status=submission.get("agent_verdict", "pending"),
            evidence_types=list(submission.get("evidence", {}).keys())
            if isinstance(submission.get("evidence"), dict)
            else [],
            submitted_at=submission.get("submitted_at"),
            reviewed_at=submission.get("reviewed_at"),
            reviewer_notes=submission.get("reviewer_notes"),
        )
        event = WebhookEvent(event_type=WebhookEventType(event_type), payload=payload)

        webhooks = webhook_registry.get_by_owner_and_event(
            agent_id, WebhookEventType(event_type)
        )
        for webhook in webhooks:
            result = await send_webhook(
                url=webhook.url,
                event=event,
                secret=webhook_registry.get_secret(webhook.webhook_id),
                webhook_id=webhook.webhook_id,
            )
            webhook_registry.record_delivery(
                webhook.webhook_id, result.status.value == "delivered"
            )
    except Exception as e:
        logger.error(f"Failed to dispatch submission webhook: {e}")


async def notify_task_created(task: Dict[str, Any]) -> None:
    """Notify via WebSocket about new task."""
    if ws_handlers:
        try:
            await ws_handlers.task_created(task)
        except Exception as e:
            logger.error(f"Failed to notify task created: {e}")
    elif task_notifier:
        # Legacy fallback
        try:
            await task_notifier.task_created(task)
        except Exception as e:
            logger.error(f"Failed to notify task created (legacy): {e}")


async def notify_task_cancelled(
    task: Dict[str, Any], reason: Optional[str] = None, refund_initiated: bool = False
) -> None:
    """Notify via WebSocket about task cancellation."""
    if ws_handlers:
        try:
            await ws_handlers.task_cancelled(task, reason, refund_initiated)
        except Exception as e:
            logger.error(f"Failed to notify task cancelled: {e}")


async def notify_application_received(
    application: Dict[str, Any], task: Dict[str, Any], worker: Dict[str, Any]
) -> None:
    """Notify via WebSocket about new worker application."""
    if ws_handlers:
        try:
            await ws_handlers.application_received(application, task, worker)
        except Exception as e:
            logger.error(f"Failed to notify application received: {e}")


async def notify_worker_assigned(task: Dict[str, Any], worker: Dict[str, Any]) -> None:
    """Notify via WebSocket about worker assignment."""
    if ws_handlers:
        try:
            await ws_handlers.worker_assigned(task, worker)
        except Exception as e:
            logger.error(f"Failed to notify worker assigned: {e}")


async def notify_submission_received(
    submission: Dict[str, Any], task: Dict[str, Any]
) -> None:
    """Notify via WebSocket about new submission."""
    if ws_handlers:
        try:
            await ws_handlers.submission_received(submission, task)
        except Exception as e:
            logger.error(f"Failed to notify submission received: {e}")


async def notify_submission_verdict(
    submission: Dict[str, Any],
    verdict: str,
    executor_id: str,
    task: Optional[Dict[str, Any]] = None,
) -> None:
    """Notify via WebSocket about submission verdict."""
    if ws_handlers and task:
        try:
            if verdict == "accepted":
                await ws_handlers.submission_approved(
                    submission, task, notes=submission.get("agent_notes")
                )
            else:
                await ws_handlers.submission_rejected(
                    submission,
                    task,
                    reason=submission.get("agent_notes", "Submission rejected"),
                    can_resubmit=(verdict == "more_info_requested"),
                )
        except Exception as e:
            logger.error(f"Failed to notify submission verdict: {e}")
    elif task_notifier:
        # Legacy fallback
        try:
            await task_notifier.submission_verdict(submission, verdict, executor_id)
        except Exception as e:
            logger.error(f"Failed to notify submission verdict (legacy): {e}")


async def notify_payment_released(
    payment: Dict[str, Any], task: Dict[str, Any], worker_id: str
) -> None:
    """Notify via WebSocket about payment release."""
    if ws_handlers:
        try:
            await ws_handlers.payment_released(payment, task, worker_id)
        except Exception as e:
            logger.error(f"Failed to notify payment released: {e}")


async def notify_payment_failed(
    task: Dict[str, Any], error_code: str, error_message: str
) -> None:
    """Notify via WebSocket about payment failure."""
    if ws_handlers:
        try:
            await ws_handlers.payment_failed(task, error_code, error_message)
        except Exception as e:
            logger.error(f"Failed to notify payment failed: {e}")


# ============== PAYMENT HELPERS ==============


def _resolve_mcp_payment_header(
    task_id: Optional[str], escrow_tx: Optional[str] = None
) -> Optional[str]:
    """Resolve the x402 payment header for a task.

    Checks tasks.escrow_tx first, then falls back to escrows.metadata.
    """
    # If escrow_tx already looks like a valid x402 header, use it
    if escrow_tx and (escrow_tx.startswith("x402:") or escrow_tx.startswith("eyJ")):
        return escrow_tx

    if not task_id:
        return None

    try:
        result = (
            db.client.table("escrows")
            .select("metadata")
            .eq("task_id", task_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            metadata = result.data[0].get("metadata", {})
            header = metadata.get("x_payment_header") or metadata.get("payment_header")
            if header:
                return header
    except Exception as e:
        logger.warning(f"Could not resolve payment header for task {task_id}: {e}")

    return escrow_tx


def _auto_register_agent_executor_mcp(wallet: str, agent_name: str = None):
    """Auto-register an agent as executor in the directory (non-blocking)."""
    wallet_lower = wallet.lower()
    try:
        existing = (
            db.client.table("executors")
            .select("id, display_name")
            .eq("wallet_address", wallet_lower)
            .eq("executor_type", "agent")
            .execute()
        )
        if existing.data:
            # Update display_name if agent_name is provided and current name is auto-generated
            row = existing.data[0]
            if agent_name and (
                not row.get("display_name") or row["display_name"].startswith("Agent ")
            ):
                db.client.table("executors").update({"display_name": agent_name}).eq(
                    "id", row["id"]
                ).execute()
            return
        display = agent_name or (
            f"Agent {wallet[:6]}...{wallet[-4:]}"
            if len(wallet) >= 10
            else f"Agent {wallet}"
        )
        db.client.table("executors").insert(
            {
                "wallet_address": wallet_lower,
                "executor_type": "agent",
                "display_name": display,
            }
        ).execute()
        logger.info(
            "Auto-registered agent executor (MCP): wallet=%s",
            truncate_wallet(wallet_lower),
        )
    except Exception as e:
        logger.warning("Auto-register agent executor (MCP) failed: %s", e)


# ============== MCP TOOLS ==============
# Core employer tools (em_publish_task, em_approve_submission, em_cancel_task)
# are registered via register_core_tools() above — see tools/core_tools.py


@mcp.tool(
    name="em_get_tasks",
    annotations={
        "title": "Get Tasks",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def em_get_tasks(params: GetTasksInput) -> str:
    """
    Get tasks from the Execution Market system with optional filters.

    Use this to monitor your published tasks or browse available tasks.

    Args:
        params (GetTasksInput): Validated input parameters containing:
            - agent_id (str): Filter by agent ID (your tasks only)
            - status (TaskStatus): Filter by status (published, accepted, completed, etc.)
            - category (TaskCategory): Filter by category
            - limit (int): Max results (1-100, default 20)
            - offset (int): Pagination offset (default 0)
            - response_format (ResponseFormat): markdown or json

    Returns:
        str: List of tasks in requested format.

    Examples:
        - Get my published tasks: agent_id="0x...", status="published"
        - Get all completed tasks: status="completed"
        - Browse physical tasks: category="physical_presence"
    """
    try:
        result = await db.get_tasks(
            agent_id=params.agent_id,
            status=params.status.value if params.status else None,
            category=params.category.value if params.category else None,
            limit=params.limit,
            offset=params.offset,
        )

        tasks = result["tasks"]
        total = result["total"]

        if not tasks:
            filters = []
            if params.agent_id:
                filters.append(f"agent_id={params.agent_id}")
            if params.status:
                filters.append(f"status={params.status.value}")
            if params.category:
                filters.append(f"category={params.category.value}")
            filter_str = ", ".join(filters) if filters else "no filters"
            return f"No tasks found ({filter_str})"

        if params.response_format == ResponseFormat.JSON:
            response = {
                "total": total,
                "count": len(tasks),
                "offset": params.offset,
                "has_more": result["has_more"],
                "tasks": tasks,
            }
            output = json.dumps(response, indent=2, default=str)
            if len(output) > CHARACTER_LIMIT:
                # Truncate tasks and re-serialize
                tasks = tasks[: len(tasks) // 2]
                response["tasks"] = tasks
                response["truncated"] = True
                response["truncation_message"] = (
                    "Response truncated. Use offset parameter for more results."
                )
                output = json.dumps(response, indent=2, default=str)
            return output

        # Markdown format
        lines = [
            f"# Tasks ({len(tasks)} of {total})",
            "",
        ]

        for task in tasks:
            lines.extend(
                [
                    f"## {task['title']}",
                    f"- **ID**: `{task['id']}`",
                    f"- **Status**: {task['status'].upper()}",
                    f"- **Bounty**: {format_bounty(task['bounty_usd'])}",
                    f"- **Deadline**: {format_datetime(task['deadline'])}",
                    "",
                ]
            )

        if result["has_more"]:
            lines.append(
                f"*{total - params.offset - len(tasks)} more tasks available. Use offset={params.offset + len(tasks)} to see more.*"
            )

        output = "\n".join(lines)
        if len(output) > CHARACTER_LIMIT:
            output = output[:CHARACTER_LIMIT] + "\n\n*[Response truncated]*"

        return output

    except Exception as e:
        return f"Error: Failed to get tasks - {str(e)}"


@mcp.tool(
    name="em_get_task",
    annotations={
        "title": "Get Task Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def em_get_task(params: GetTaskInput) -> str:
    """
    Get detailed information about a specific task.

    Args:
        params (GetTaskInput): Validated input parameters containing:
            - task_id (str): UUID of the task
            - response_format (ResponseFormat): markdown or json

    Returns:
        str: Task details in requested format.
    """
    try:
        task = await db.get_task(params.task_id)

        if not task:
            return f"Error: Task {params.task_id} not found"

        # Fetch real escrow status from escrows table
        escrow_info = None
        try:
            client = db.get_client()
            esc_row = (
                client.table("escrows")
                .select("status, funding_tx, total_amount_usdc, metadata")
                .eq("task_id", params.task_id)
                .limit(1)
                .execute()
            )
            if esc_row.data:
                esc = esc_row.data[0]
                escrow_info = {
                    "status": esc.get("status", "unknown"),
                    "amount_usdc": esc.get("total_amount_usdc"),
                    "tx_ref": esc.get("funding_tx", ""),
                    "network": (esc.get("metadata") or {}).get("network", ""),
                }
        except Exception:
            pass

        # Fetch application count
        applications = await db.get_applications_for_task(params.task_id)
        application_count = len(applications)

        if params.response_format == ResponseFormat.JSON:
            if escrow_info:
                task["escrow"] = escrow_info
            task["application_count"] = application_count
            return json.dumps(task, indent=2, default=str)

        return format_task_markdown(
            task,
            escrow_info=escrow_info,
            application_count=application_count,
        )

    except Exception as e:
        return f"Error: Failed to get task - {str(e)}"


@mcp.tool(
    name="em_check_submission",
    annotations={
        "title": "Check Task Submissions",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def em_check_submission(params: CheckSubmissionInput) -> str:
    """
    Check submissions for a task you published.

    Use this to see if a human has submitted evidence for your task.
    You can then use em_approve_submission to accept or reject.

    Args:
        params (CheckSubmissionInput): Validated input parameters containing:
            - task_id (str): UUID of the task
            - agent_id (str): Your agent ID (for authorization)
            - response_format (ResponseFormat): markdown or json

    Returns:
        str: Submission details or "No submissions yet".
    """
    try:
        # Verify ownership
        task = await db.get_task(params.task_id)
        if not task:
            return f"Error: Task {params.task_id} not found"
        if (task.get("agent_id") or "").lower() != (params.agent_id or "").lower():
            return "Error: Not authorized to view submissions for this task"

        submissions = await db.get_submissions_for_task(params.task_id)
        applications = await db.get_applications_for_task(params.task_id)

        if not submissions and not applications:
            return f"""# No Submissions Yet

**Task**: {task["title"]}
**Status**: {task["status"].upper()}

No human has submitted evidence yet and no one has applied. The task is {"still available" if task["status"] == "published" else "being worked on" if task["status"] in ["accepted", "in_progress"] else "in status: " + task["status"]}."""

        if not submissions and applications:
            # Workers have applied but not yet submitted evidence
            if params.response_format == ResponseFormat.JSON:
                return json.dumps(
                    {
                        "task_id": params.task_id,
                        "task_title": task["title"],
                        "task_status": task["status"],
                        "submission_count": 0,
                        "submissions": [],
                        "application_count": len(applications),
                        "applications": applications,
                    },
                    indent=2,
                    default=str,
                )

            lines = [
                f"# Applications for: {task['title']}",
                f"**Task Status**: {task['status'].upper()}",
                f"**Applications**: {len(applications)} worker(s) applied",
                "",
                "No evidence submitted yet, but workers have applied:",
                "",
            ]
            for app in applications:
                status = app.get("status", "pending")
                msg = app.get("message", "")
                wallet = app.get("wallet_address", "")
                name = app.get("display_name", "")
                worker_label = name if name else app.get("executor_id", "unknown")
                lines.append(f"- **Worker** {worker_label} — status: {status}")
                if wallet:
                    lines.append(f"  Wallet: `{wallet}`")
                if msg:
                    lines.append(f"  Message: {msg}")
            lines.append("")
            lines.append(
                "Use the dashboard or API to assign a worker, then they can submit evidence."
            )
            return "\n".join(lines)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(
                {
                    "task_id": params.task_id,
                    "task_title": task["title"],
                    "task_status": task["status"],
                    "submission_count": len(submissions),
                    "submissions": submissions,
                    "application_count": len(applications),
                    "applications": applications,
                },
                indent=2,
                default=str,
            )

        # Markdown format
        lines = [
            f"# Submissions for: {task['title']}",
            f"**Task Status**: {task['status'].upper()}",
            f"**Total Submissions**: {len(submissions)}",
        ]
        if applications:
            lines.append(f"**Applications**: {len(applications)}")
        lines.append("")

        for sub in submissions:
            lines.append(format_submission_markdown(sub))
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"Error: Failed to check submissions - {str(e)}"


# em_approve_submission and em_cancel_task are registered via register_core_tools()
# See tools/core_tools.py


@mcp.tool(
    name="em_get_arbiter_verdict",
    annotations={
        "title": "Get Ring 2 Arbiter Verdict",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def em_get_arbiter_verdict(params: GetArbiterVerdictInput) -> str:
    """
    Get the Ring 2 arbiter verdict for a task or submission.

    Returns the dual-inference verdict (PHOTINT + Arbiter) including decision,
    score, tier used, evidence hash, commitment hash, and dispute status if
    the submission was escalated to L2 human review.

    Only available for tasks that were created with arbiter_mode != "manual"
    and after Phase B verification has completed.

    Args:
        params (GetArbiterVerdictInput): Validated input containing:
            - task_id (str, optional): UUID of the task
            - submission_id (str, optional): UUID of the submission
            - response_format (ResponseFormat): markdown or json
            (at least one of task_id or submission_id must be provided)

    Returns:
        str: Arbiter verdict details or error message if not yet evaluated.
    """
    try:
        client = db.get_client()

        # Lookup the submission (by submission_id or latest submission for task)
        if params.submission_id:
            sub_result = (
                client.table("submissions")
                .select(
                    "id, task_id, arbiter_verdict, arbiter_tier, arbiter_score, "
                    "arbiter_confidence, arbiter_evidence_hash, arbiter_commitment_hash, "
                    "arbiter_verdict_data, arbiter_cost_usd, arbiter_latency_ms, "
                    "arbiter_evaluated_at"
                )
                .eq("id", params.submission_id)
                .limit(1)
                .execute()
            )
        else:
            sub_result = (
                client.table("submissions")
                .select(
                    "id, task_id, arbiter_verdict, arbiter_tier, arbiter_score, "
                    "arbiter_confidence, arbiter_evidence_hash, arbiter_commitment_hash, "
                    "arbiter_verdict_data, arbiter_cost_usd, arbiter_latency_ms, "
                    "arbiter_evaluated_at"
                )
                .eq("task_id", params.task_id)
                .order("submitted_at", desc=True)
                .limit(1)
                .execute()
            )

        if not sub_result.data:
            lookup = params.submission_id or f"task {params.task_id}"
            return f"Error: No submission found for {lookup}"

        sub = sub_result.data[0]

        if sub.get("arbiter_verdict") is None:
            return (
                f"# Arbiter Verdict Pending\n\n"
                f"**Submission**: `{sub['id']}`\n"
                f"**Status**: Not yet evaluated by Ring 2 arbiter.\n\n"
                f"Possible reasons:\n"
                f"- Task was created with `arbiter_mode=manual`\n"
                f"- Phase B (async AI verification) has not completed yet\n"
                f"- Arbiter master switch is disabled\n"
            )

        # Check for a dispute if the verdict was INCONCLUSIVE
        dispute_info = None
        if sub.get("arbiter_verdict") == "inconclusive":
            try:
                dispute_result = (
                    client.table("disputes")
                    .select("id, status, escalation_tier, resolved_at, winner")
                    .eq("submission_id", sub["id"])
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if dispute_result.data:
                    dispute_info = dispute_result.data[0]
            except Exception:
                pass

        if params.response_format == ResponseFormat.JSON:
            payload = {
                "submission_id": sub["id"],
                "task_id": sub["task_id"],
                "verdict": sub["arbiter_verdict"],
                "tier": sub.get("arbiter_tier"),
                "score": sub.get("arbiter_score"),
                "confidence": sub.get("arbiter_confidence"),
                "evidence_hash": sub.get("arbiter_evidence_hash"),
                "commitment_hash": sub.get("arbiter_commitment_hash"),
                "cost_usd": sub.get("arbiter_cost_usd"),
                "latency_ms": sub.get("arbiter_latency_ms"),
                "evaluated_at": sub.get("arbiter_evaluated_at"),
                "verdict_data": sub.get("arbiter_verdict_data"),
                "dispute": dispute_info,
            }
            return json.dumps(payload, indent=2, default=str)

        # Markdown format
        verdict = sub["arbiter_verdict"]
        emoji = {
            "pass": "APPROVED",
            "fail": "REJECTED",
            "inconclusive": "ESCALATED",
            "skipped": "SKIPPED",
        }.get(verdict, verdict.upper())

        lines = [
            "# Ring 2 Arbiter Verdict",
            "",
            f"**Submission**: `{sub['id']}`",
            f"**Task**: `{sub['task_id']}`",
            f"**Decision**: {emoji} ({verdict})",
            f"**Tier**: {sub.get('arbiter_tier', 'unknown')}",
            f"**Aggregate Score**: {sub.get('arbiter_score', 'n/a')}",
            f"**Confidence**: {sub.get('arbiter_confidence', 'n/a')}",
            f"**Evaluated At**: {sub.get('arbiter_evaluated_at', 'n/a')}",
            "",
            "## Cryptographic Audit Trail",
            f"- **Evidence hash**: `{sub.get('arbiter_evidence_hash', 'n/a')}`",
            f"- **Commitment hash**: `{sub.get('arbiter_commitment_hash', 'n/a')}`",
            "",
            "## Cost Metrics",
            f"- **LLM cost**: ${sub.get('arbiter_cost_usd', 0) or 0:.6f}",
            f"- **Latency**: {sub.get('arbiter_latency_ms', 0)} ms",
        ]

        # Ring breakdown if available
        verdict_data = sub.get("arbiter_verdict_data") or {}
        ring_scores = verdict_data.get("ring_scores") or []
        if ring_scores:
            lines.extend(["", "## Ring Breakdown"])
            for rs in ring_scores:
                lines.append(
                    f"- **{rs.get('ring', 'unknown')}** "
                    f"({rs.get('provider', '?')}/{rs.get('model', '?')}): "
                    f"score={rs.get('score', 'n/a')}, "
                    f"decision={rs.get('decision', 'n/a')}, "
                    f"confidence={rs.get('confidence', 'n/a')}"
                )

        reason = verdict_data.get("reason")
        if reason:
            lines.extend(["", "## Reason", reason])

        if verdict_data.get("disagreement"):
            lines.extend(
                [
                    "",
                    "WARNING: Ring disagreement detected -- escalated to L2 human review.",
                ]
            )

        if dispute_info:
            lines.extend(
                [
                    "",
                    "## Dispute Status",
                    f"- **Dispute ID**: `{dispute_info['id']}`",
                    f"- **Status**: {dispute_info.get('status', 'open')}",
                    f"- **Escalation tier**: {dispute_info.get('escalation_tier', 2)}",
                ]
            )
            if dispute_info.get("resolved_at"):
                lines.append(f"- **Resolved at**: {dispute_info['resolved_at']}")
                lines.append(f"- **Winner**: {dispute_info.get('winner', 'n/a')}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error: Failed to get arbiter verdict - {str(e)}"


@mcp.tool(
    name="em_resolve_dispute",
    annotations={
        "title": "Resolve a Dispute (L2 Human Arbiter)",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def em_resolve_dispute(params: ResolveDisputeInput) -> str:
    """
    Submit a resolution verdict on a Ring 2 escalated dispute.

    Who can call this:
        1. The publishing agent (always, for their own task disputes)
        2. Eligible human arbiters (reputation_score >= 80 AND
           tasks_completed >= 10 in the same category)

    Verdict options:
        - 'release': worker wins -> triggers Facilitator /settle
        - 'refund':  agent wins  -> triggers Facilitator /refund
        - 'split':   partial release + partial refund
                     (requires split_pct = agent's refund %, 0-100)

    Side effects:
        - Updates the dispute row (status, winner, resolution_type='manual',
          agent_refund_usdc, executor_payout_usdc)
        - Triggers the appropriate payment flow via existing Facilitator paths
        - Emits dispute.resolved event on the event bus
        - Destructive: moves funds on-chain (use carefully)

    Args:
        params (ResolveDisputeInput):
            - dispute_id (str): UUID of the dispute
            - verdict (str): 'release' | 'refund' | 'split'
            - reason (str): justification (5-2000 chars, stored in audit trail)
            - split_pct (float, optional): required for 'split' verdict (0-100)
            - response_format (ResponseFormat): markdown | json

    Returns:
        str: Success message with dispute ID, verdict, amounts, and triggered
             payment action, or error message.
    """
    try:
        # Lazy import to avoid circular deps + api.routers.disputes may
        # import supabase_client at module load time which we want deferred.
        from api.routers.disputes import (
            ResolveDisputeRequest,
            resolve_dispute as resolve_dispute_endpoint,
        )
        from api.auth import AgentAuth

        # Build a synthetic AgentAuth from env / platform config for MCP calls.
        # In production MCP tool calls flow through the same auth layer as
        # the REST API (via MCP Streamable HTTP), so this is only hit in
        # local test mode or from the mcp.tool wrapper.
        caller_agent_id = os.environ.get("EM_CALLER_AGENT_ID", "mcp-tool")
        auth = AgentAuth(
            agent_id=caller_agent_id,
            wallet_address=os.environ.get("EM_CALLER_WALLET"),
            auth_method="mcp_tool",
        )

        body = ResolveDisputeRequest(
            verdict=params.verdict,
            reason=params.reason,
            split_pct=params.split_pct,
        )

        result = await resolve_dispute_endpoint(
            dispute_id=params.dispute_id,
            body=body,
            auth=auth,
        )

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(result.model_dump(), indent=2, default=str)

        lines = [
            "# Dispute Resolved",
            "",
            f"**Dispute**: `{result.dispute_id}`",
            f"**Verdict**: {result.verdict.upper()}",
            f"**Agent refund**: ${result.agent_refund_usdc:.6f} USDC",
            f"**Executor payout**: ${result.executor_payout_usdc:.6f} USDC",
            f"**Resolved at**: {result.resolved_at}",
            f"**Action triggered**: {result.action_triggered or 'pending'}",
            "",
            "The dispute row is now marked as resolved. Payment dispatch runs",
            "asynchronously via the Facilitator -- check `payment_events` or",
            "`em_get_task` for the transaction hash.",
        ]
        return "\n".join(lines)

    except Exception as e:
        return f"Error: Failed to resolve dispute - {str(e)}"


@mcp.tool(
    name="em_get_payment_info",
    annotations={
        "title": "Get Payment Info for Task Approval",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def em_get_payment_info(task_id: str, submission_id: str) -> str:
    """
    Get payment details needed to approve a task submission (Fase 1 mode).

    External agents use this to get the exact addresses and amounts they need
    to sign 2 EIP-3009 authorizations: one for the worker and one for the
    platform fee.

    Args:
        task_id: UUID of the task
        submission_id: UUID of the submission to approve

    Returns:
        JSON with worker_address, treasury_address, bounty_amount, fee_amount,
        token details, and signing parameters.
    """
    try:
        from integrations.x402.sdk_client import (
            PLATFORM_FEE_PERCENT,
            EM_TREASURY,
            get_token_config,
        )

        task = await db.get_task(task_id)
        if not task:
            return json.dumps({"error": f"Task {task_id} not found"})

        # Get submission to find worker wallet
        result = await db.get_submissions(task_id)
        submission = None
        for s in result if isinstance(result, list) else [result]:
            if s.get("id") == submission_id:
                submission = s
                break

        if not submission:
            return json.dumps({"error": f"Submission {submission_id} not found"})

        worker_address = (submission.get("executor") or {}).get("wallet_address")
        if not worker_address:
            return json.dumps(
                {"error": "Worker wallet address not found on submission"}
            )

        bounty = Decimal(str(task.get("bounty_usd", 0)))
        platform_fee = (bounty * PLATFORM_FEE_PERCENT).quantize(Decimal("0.000001"))
        if Decimal("0") < platform_fee < Decimal("0.01"):
            platform_fee = Decimal("0.01")

        network = task.get("payment_network", "base")
        token = task.get("payment_token", "USDC")

        try:
            token_config = get_token_config(network, token)
        except ValueError as e:
            return json.dumps({"error": str(e)})

        return json.dumps(
            {
                "task_id": task_id,
                "submission_id": submission_id,
                "worker_address": worker_address,
                "treasury_address": EM_TREASURY,
                "bounty_amount": str(bounty),
                "fee_amount": str(platform_fee),
                "total_required": str(bounty + platform_fee),
                "network": network,
                "token": token,
                "token_address": token_config["address"],
                "token_decimals": token_config["decimals"],
                "valid_for_seconds": 3600,
                "instructions": (
                    "Sign 2 EIP-3009 TransferWithAuthorization messages: "
                    "1) agent->worker_address for bounty_amount, "
                    "2) agent->treasury_address for fee_amount. "
                    "Then call em_approve_submission with payment_auth_worker and payment_auth_fee."
                ),
            },
            indent=2,
        )

    except Exception as e:
        return json.dumps({"error": f"Failed to get payment info: {str(e)}"})


@mcp.tool(
    name="em_check_escrow_state",
    annotations={
        "title": "Check On-Chain Escrow State",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def em_check_escrow_state(task_id: str) -> str:
    """
    Query the on-chain escrow state for a task (Fase 2 mode only).

    Returns the current escrow state from the AuthCaptureEscrow contract:
    - capturableAmount: Funds available for release to worker
    - refundableAmount: Funds available for refund to agent
    - hasCollectedPayment: Whether initial deposit was collected

    Args:
        task_id: UUID of the task to check

    Returns:
        JSON with escrow state, or error if not in fase2 mode or no escrow found.
    """
    try:
        dispatcher = get_payment_dispatcher()
        if not dispatcher or dispatcher.get_mode() != "fase2":
            return json.dumps(
                {
                    "error": f"Escrow state query requires fase2 mode (current: {dispatcher.get_mode() if dispatcher else 'none'})",
                    "task_id": task_id,
                }
            )

        # Reconstruct PaymentInfo from DB
        pi, pi_meta = await dispatcher._reconstruct_fase2_state(task_id)
        if pi is None:
            return json.dumps(
                {
                    "error": f"No fase2 escrow found for task {task_id}",
                    "task_id": task_id,
                }
            )

        stored_network = pi_meta.get("network", "base")
        client = dispatcher._get_fase2_client(stored_network)

        # Query on-chain state (read-only, no gas)
        state = await asyncio.to_thread(client.query_escrow_state, pi)

        capturable = int(state.get("capturableAmount", 0))
        refundable = int(state.get("refundableAmount", 0))
        collected = state.get("hasCollectedPayment", False)

        return json.dumps(
            {
                "task_id": task_id,
                "network": stored_network,
                "escrow_state": {
                    "capturable_usdc": capturable / 1_000_000,
                    "refundable_usdc": refundable / 1_000_000,
                    "has_collected_payment": collected,
                    "capturable_atomic": capturable,
                    "refundable_atomic": refundable,
                },
                "operator": pi.operator,
                "salt": pi.salt[:18] + "...",
                "raw": state,
            },
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {"error": f"Failed to query escrow state: {str(e)}", "task_id": task_id}
        )


# ============== WORKER TOOLS ==============
# Worker tools (NOW-011 to NOW-014) are now registered via the worker_tools module
# See: tools/worker_tools.py for implementations of:
# - em_apply_to_task (NOW-011)
# - em_submit_work (NOW-012)
# - em_get_my_tasks (NOW-013)
# - em_withdraw_earnings (NOW-014)


# ============== EMPLOYER TOOLS (NOW-015 to NOW-018) ==============
# Enhanced agent tools are now registered via the agent_tools module
# See: tools/agent_tools.py for implementations of:
# - em_assign_task (NOW-015) - with eligibility checks
# - em_batch_create_tasks (NOW-017) - with atomic/best-effort modes
# - em_get_task_analytics (NOW-018) - with comprehensive metrics


# ============== UTILITY TOOLS ==============


@mcp.tool(
    name="em_get_fee_structure",
    annotations={
        "title": "Get Platform Fee Structure",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def em_get_fee_structure() -> str:
    """
    Get the current platform fee structure.

    Returns information about:
    - Fee rates by task category (6-8%)
    - Minimum and maximum limits
    - Treasury wallet address
    - Worker vs platform distribution

    Returns:
        str: Fee structure details in markdown format.
    """
    if not fee_manager:
        return (
            "Fee manager not available. Fee structure information cannot be retrieved."
        )

    try:
        structure = fee_manager.get_fee_structure()

        lines = [
            "# Platform Fee Structure",
            "",
            "## Fee Rates by Category",
        ]

        for cat_name, info in structure["rates_by_category"].items():
            lines.append(
                f"- **{cat_name.replace('_', ' ').title()}**: {info['rate_percent']:.1f}% "
                f"({info['description']})"
            )

        lines.extend(
            [
                "",
                "## Distribution",
                f"- **Worker Receives**: {structure['distribution']['worker_percent']} of bounty",
                f"- **Platform Fee**: {structure['distribution']['platform_percent']} of bounty",
                "",
                "## Limits",
                f"- **Minimum Fee**: ${structure['limits']['minimum_fee']:.2f}",
                f"- **Maximum Rate**: {structure['limits']['maximum_rate_percent']:.1f}%",
            ]
        )

        if structure["treasury_wallet"]:
            lines.append(
                f"\n**Treasury Wallet**: `{structure['treasury_wallet'][:10]}...`"
            )

        return "\n".join(lines)

    except Exception as e:
        return f"Error: Failed to get fee structure - {str(e)}"


@mcp.tool(
    name="em_calculate_fee",
    annotations={
        "title": "Calculate Task Fee",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def em_calculate_fee(
    bounty_usd: float,
    category: TaskCategory,
) -> str:
    """
    Calculate the fee breakdown for a potential task.

    Use this to preview how much workers will receive after platform fees.

    Args:
        bounty_usd: Bounty amount in USD
        category: Task category

    Returns:
        str: Fee breakdown details.
    """
    if not calculate_platform_fee:
        return "Fee calculation not available."

    try:
        breakdown = calculate_platform_fee(bounty_usd, category)

        return f"""# Fee Calculation

**Bounty**: ${bounty_usd:.2f}
**Category**: {category.value.replace("_", " ").title()}

## Breakdown
- **Worker Receives**: ${breakdown["worker_amount"]:.2f} ({breakdown["worker_percent"]:.1f}%)
- **Platform Fee**: ${breakdown["fee_amount"]:.2f} ({breakdown["fee_rate_percent"]:.1f}%)

*Fee rate for {category.value.replace("_", " ").title()} tasks: {breakdown["fee_rate_percent"]:.1f}%*"""

    except Exception as e:
        return f"Error: Failed to calculate fee - {str(e)}"


@mcp.tool(
    name="em_server_status",
    annotations={
        "title": "Get Server Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def em_server_status() -> str:
    """
    Get the current status of the Execution Market MCP server and its integrations.

    Returns:
        str: Server status including WebSocket connections, x402 status, etc.
    """
    try:
        ws_stats = {}
        if ws_manager:
            try:
                ws_stats = ws_manager.get_stats()
            except Exception:
                pass

        lines = [
            "# Execution Market MCP Server Status",
            "",
            f"**Timestamp**: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## WebSocket Server",
            f"- **Status**: {'Running' if ws_stats.get('running', False) else 'Not initialized'}",
            f"- **Active Connections**: {ws_stats.get('total_connections', 0)}",
            f"- **Unique Agents**: {ws_stats.get('unique_agents', 0)}",
            "",
            "## Integrations",
            f"- **x402 SDK**: {'Enabled' if x402_sdk else 'Disabled (simulated payments)'}",
            f"- **Advanced Escrow**: {'Enabled' if ADVANCED_ESCROW_AVAILABLE else 'Disabled (uvd-x402-sdk not installed)'}",
            f"- **Fee Manager**: {'Enabled' if fee_manager else 'Disabled'}",
            f"- **Webhook Registry**: {'Enabled' if webhook_registry else 'Disabled'}",
            "",
            "## Configuration",
            f"- **Min Withdrawal**: ${worker_config.min_withdrawal_usdc:.2f}",
            f"- **Platform Fee**: {worker_config.platform_fee_percent:.1f}%",
            f"- **Network**: {worker_config.network}",
        ]

        return "\n".join(lines)

    except Exception as e:
        return f"Error: Failed to get server status - {str(e)}"


# ============== MAIN ==============


if __name__ == "__main__":
    mcp.run()
