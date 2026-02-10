#!/usr/bin/env python3
"""
Execution Market MCP Server - Human Execution Layer for AI Agents

This MCP server allows AI agents to publish tasks for human execution,
monitor submissions, and approve/reject completed work.

OpenAPI Metadata:
    Title: Execution Market Human Execution Layer API
    Version: 1.0.0
    Description: Enable AI agents to delegate real-world tasks to human workers
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
    - Fee Management: 6-8% platform fee by task category

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

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, Optional

from mcp.server.fastmcp import FastMCP

# Core models
from models import (
    PublishTaskInput,
    GetTasksInput,
    GetTaskInput,
    CheckSubmissionInput,
    ApproveSubmissionInput,
    CancelTaskInput,
    ResponseFormat,
    TaskCategory,
)

# Database client
import supabase_client as db

# Modular tools
from tools.worker_tools import register_worker_tools, WorkerToolsConfig
from tools.agent_tools import register_agent_tools, AgentToolsConfig
from tools.escrow_tools import register_escrow_tools, ADVANCED_ESCROW_AVAILABLE
from integrations.x402.payment_dispatcher import (
    get_dispatcher as get_payment_dispatcher,
)
from integrations.x402.payment_events import log_payment_event

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
    logger.info("Webhook registry initialized")
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
    "title": "Execution Market Human Execution Layer",
    "description": "Enable AI agents to delegate real-world tasks to human workers with crypto payments",
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

# Initialize the MCP server with metadata
# streamable_http_path="/" makes endpoint at mount root
# When mounted at /mcp, the full URL is /mcp/ (trailing slash required by Starlette)
mcp = FastMCP(
    SERVER_INFO["name"],
    streamable_http_path="/",
)


# Configure worker tools (NOW-011 to NOW-014)
worker_config = WorkerToolsConfig(
    min_withdrawal_usdc=float(os.environ.get("MIN_WITHDRAWAL_USDC", "5.0")),
    platform_fee_percent=float(os.environ.get("PLATFORM_FEE_PERCENT", "8.0")),
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


# ============== CONSTANTS ==============


CHARACTER_LIMIT = 25000


# ============== FORMATTING HELPERS ==============


def format_bounty(amount: float) -> str:
    """Format bounty amount as currency."""
    return f"${amount:.2f}"


def format_datetime(dt_str: str) -> str:
    """Format ISO datetime string for display."""
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return dt_str


def format_task_markdown(task: Dict[str, Any]) -> str:
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
            await send_webhook(
                url=webhook.url,
                event=event,
                secret=webhook_registry.get_secret(webhook.webhook_id),
                webhook_id=webhook.webhook_id,
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
            task_title=task["title"],
            verdict=submission.get("agent_verdict", "pending"),
            executor_id=submission.get("executor_id"),
        )
        event = WebhookEvent(event_type=WebhookEventType(event_type), payload=payload)

        webhooks = webhook_registry.get_by_owner_and_event(
            agent_id, WebhookEventType(event_type)
        )
        for webhook in webhooks:
            await send_webhook(
                url=webhook.url,
                event=event,
                secret=webhook_registry.get_secret(webhook.webhook_id),
                webhook_id=webhook.webhook_id,
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


# ============== MCP TOOLS ==============


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

    Examples:
        - "I need someone to verify a store is open" -> physical_presence category, photo evidence
        - "Get a quote from a local contractor" -> knowledge_access category, document evidence
        - "Sign this document in person" -> human_authority category, signature evidence
    """
    try:
        deadline = datetime.now(timezone.utc) + timedelta(hours=params.deadline_hours)

        # Calculate fees for the task if fee manager is available
        fee_breakdown = None
        if fee_manager:
            try:
                fee_breakdown = fee_manager.calculate_fee(
                    bounty=params.bounty_usd,
                    category=params.category,
                )
            except Exception as e:
                logger.warning(f"Could not calculate fees: {e}")

        task = await db.create_task(
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
        )

        # Authorize escrow via SDK (facilitator handles gas)
        escrow_info = None
        if ADVANCED_ESCROW_AVAILABLE:
            try:
                from integrations.x402.advanced_escrow_integration import (
                    authorize_task_bounty,
                )

                escrow_result = authorize_task_bounty(
                    task_id=task["id"],
                    receiver=params.agent_id,  # Receiver set at release time
                    amount_usdc=Decimal(str(params.bounty_usd)),
                )
                escrow_info = {
                    "escrow_id": task["id"],
                    "status": escrow_result.status
                    if hasattr(escrow_result, "status")
                    else "authorized",
                    "deposit_tx": getattr(escrow_result, "tx_hash", "") or "",
                }
                logger.info(f"Escrow authorized via SDK for task {task['id']}")
            except Exception as e:
                logger.warning(f"Could not authorize escrow via SDK: {e}")
        elif x402_sdk:
            # Fallback: record escrow intent without on-chain authorization
            escrow_info = {
                "escrow_id": task["id"],
                "status": "pending",
                "deposit_tx": "",
            }
            logger.info(f"Escrow recorded (SDK-only) for task {task['id']}")

        # Dispatch webhook
        if WebhookEventType:
            await dispatch_task_webhook("task_created", task, params.agent_id)

        # Notify via WebSocket
        await notify_task_created(task)

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

        response += """
The task is now visible to human executors. Use `em_get_task` with the task ID to monitor progress, or `em_check_submission` when a human submits evidence."""

        return response

    except Exception as e:
        return f"Error: Failed to publish task - {str(e)}"


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

        if params.response_format == ResponseFormat.JSON:
            # Include escrow info from task record (SDK-based flow stores in DB)
            if task.get("escrow_tx") or task.get("escrow_amount_usdc"):
                task["escrow"] = {
                    "status": "authorized" if task.get("escrow_tx") else "pending",
                    "amount_usdc": task.get("escrow_amount_usdc"),
                    "tx_ref": task.get("escrow_tx", ""),
                }
            return json.dumps(task, indent=2, default=str)

        return format_task_markdown(task)

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
        if task["agent_id"] != params.agent_id:
            return "Error: Not authorized to view submissions for this task"

        submissions = await db.get_submissions_for_task(params.task_id)

        if not submissions:
            return f"""# No Submissions Yet

**Task**: {task["title"]}
**Status**: {task["status"].upper()}

No human has submitted evidence yet. The task is {"still available" if task["status"] == "published" else "being worked on" if task["status"] in ["accepted", "in_progress"] else "in status: " + task["status"]}."""

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(
                {
                    "task_id": params.task_id,
                    "task_title": task["title"],
                    "task_status": task["status"],
                    "submission_count": len(submissions),
                    "submissions": submissions,
                },
                indent=2,
                default=str,
            )

        # Markdown format
        lines = [
            f"# Submissions for: {task['title']}",
            f"**Task Status**: {task['status'].upper()}",
            f"**Total Submissions**: {len(submissions)}",
            "",
        ]

        for sub in submissions:
            lines.append(format_submission_markdown(sub))
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"Error: Failed to check submissions - {str(e)}"


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
        submission = await db.update_submission(
            submission_id=params.submission_id,
            agent_id=params.agent_id,
            verdict=params.verdict.value,
            notes=params.notes,
        )

        # Get task for context
        task = await db.get_task(submission.get("task_id"))

        # Handle payment release on approval via SDK (facilitator pays gas)
        payment_info = None
        if params.verdict.value == "accepted" and task:
            worker_wallet = submission.get("executor", {}).get("wallet_address")
            if worker_wallet:
                # Try advanced escrow first (SDK-based), then basic SDK settle
                if ADVANCED_ESCROW_AVAILABLE:
                    try:
                        from integrations.x402.advanced_escrow_integration import (
                            release_to_worker,
                        )

                        result = release_to_worker(task_id=task["id"])
                        payment_info = {
                            "tx_hash": getattr(result, "transaction_hash", ""),
                            "success": getattr(result, "success", False),
                            "amount": task["bounty_usd"],
                        }
                        logger.info(
                            f"Payment released via advanced escrow for task {task['id']}"
                        )
                    except Exception as e:
                        logger.error(f"Advanced escrow release failed: {e}")

                if not payment_info and x402_sdk:
                    try:
                        # Resolve the x402 payment header from escrows table
                        payment_header = _resolve_mcp_payment_header(
                            task["id"], task.get("escrow_tx")
                        )
                        payment_info = await x402_sdk.settle_task_payment(
                            task_id=task["id"],
                            payment_header=payment_header or "",
                            worker_address=worker_wallet,
                            bounty_amount=Decimal(str(task["bounty_usd"])),
                        )
                        logger.info(
                            f"Payment settled via SDK for task {task['id']}: {payment_info}"
                        )
                    except Exception as e:
                        logger.error(f"SDK payment settlement failed: {e}")

                # Dispatch payment webhook
                if (
                    payment_info
                    and webhook_registry
                    and WebhookEventType
                    and PaymentPayload
                ):
                    try:
                        tx_hash = payment_info.get("tx_hash", "")
                        payload = PaymentPayload(
                            task_id=task["id"],
                            amount_usdc=task["bounty_usd"],
                            recipient=worker_wallet,
                            tx_hash=tx_hash,
                        )
                        event = WebhookEvent(
                            event_type=WebhookEventType.PAYMENT_RELEASED,
                            payload=payload,
                        )
                        webhooks = webhook_registry.get_by_owner_and_event(
                            params.agent_id, WebhookEventType.PAYMENT_RELEASED
                        )
                        for webhook in webhooks:
                            await send_webhook(
                                url=webhook.url,
                                event=event,
                                secret=webhook_registry.get_secret(webhook.webhook_id),
                                webhook_id=webhook.webhook_id,
                            )
                    except Exception as e:
                        logger.error(f"Failed to dispatch payment webhook: {e}")

        # Dispatch submission verdict webhook
        if task and WebhookEventType:
            event_type = (
                "submission_approved"
                if params.verdict.value == "accepted"
                else "submission_rejected"
            )
            await dispatch_submission_webhook(
                event_type, submission, task, params.agent_id
            )

        # Notify via WebSocket
        executor_id = submission.get("executor_id")
        if executor_id and task:
            await notify_submission_verdict(
                submission, params.verdict.value, executor_id, task
            )

        # Notify payment release if approved
        if params.verdict.value == "accepted" and payment_info and executor_id:
            await notify_payment_released(payment_info, task, executor_id)

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
                response += f"""

## Payment Details
- **Worker Payment**: ${payment_info.get("net_to_worker", payment_info.get("amount", 0)):.2f}
- **Platform Fee**: ${payment_info.get("platform_fee", 0):.2f}
- **Transaction**: `{str(tx_hash)[:16]}...`"""
        else:
            response += "\nThe executor has been notified of your decision."

        return response

    except Exception as e:
        return f"Error: Failed to update submission - {str(e)}"


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
    Cancel a task you published (only if still in 'published' status).

    Use this if you no longer need the task completed.
    Cannot cancel tasks that have already been accepted by an executor.

    Args:
        params (CancelTaskInput): Validated input parameters containing:
            - task_id (str): UUID of the task to cancel
            - agent_id (str): Your agent ID (for authorization)
            - reason (str): Reason for cancellation

    Returns:
        str: Confirmation of cancellation.
    """
    try:
        task = await db.cancel_task(params.task_id, params.agent_id)

        # Handle escrow refund via PaymentDispatcher (handles both x402r and preauth modes)
        refund_info = None
        try:
            dispatcher = get_payment_dispatcher()
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
                await log_payment_event(
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

        # Dispatch webhook
        if WebhookEventType:
            await dispatch_task_webhook("task_cancelled", task, params.agent_id)

        # Notify via WebSocket
        await notify_task_cancelled(task, params.reason, refund_info is not None)

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
