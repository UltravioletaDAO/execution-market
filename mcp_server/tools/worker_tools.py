"""
Worker MCP Tools for Execution Market (NOW-011 to NOW-014)

Tools that workers use to interact with the Execution Market platform:
- em_apply_to_task: Worker applies to a task (NOW-011)
- em_submit_work: Worker submits evidence (NOW-012)
- em_get_my_tasks: Worker gets their assigned tasks (NOW-013)
- em_withdraw_earnings: Worker withdraws available balance (NOW-014)

These tools include:
1. Input validation via Pydantic models
2. Authorization checks (worker must be registered)
3. Status transitions (published -> accepted -> in_progress -> submitted)
4. Evidence schema validation
5. Earnings calculation with x402 integration
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


# ============== CONFIGURATION ==============


@dataclass
class WorkerToolsConfig:
    """Configuration for worker tools."""

    # Minimum withdrawal amount in USDC
    min_withdrawal_usdc: float = 5.0

    # Platform fee percentage (deducted on withdrawal)
    platform_fee_percent: float = 8.0

    # Gas estimate for withdrawals (in USDC)
    estimated_gas_usdc: float = 0.50

    # Maximum evidence fields per submission
    max_evidence_fields: int = 10

    # Enable x402 integration for real withdrawals
    x402_enabled: bool = False

    # Network for withdrawals
    network: str = "base"


# ============== STATUS TRANSITIONS ==============


# Valid status transitions for tasks
VALID_TRANSITIONS = {
    "published": ["accepted", "cancelled", "expired"],
    "accepted": ["in_progress", "published"],  # Can release back to published
    "in_progress": ["submitted", "accepted"],  # Can pause back to accepted
    "submitted": ["verifying", "completed", "disputed", "in_progress"],
    "verifying": ["completed", "disputed", "submitted"],
    "completed": [],  # Terminal state
    "disputed": ["completed", "cancelled"],  # Resolved by arbitration
    "expired": [],  # Terminal state
    "cancelled": [],  # Terminal state
}


def can_transition(current: str, target: str) -> bool:
    """Check if a status transition is valid."""
    return target in VALID_TRANSITIONS.get(current, [])


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


# ============== EVIDENCE VALIDATION ==============


class EvidenceValidationError(Exception):
    """Raised when evidence validation fails."""

    pass


def validate_evidence_schema(
    evidence: Dict[str, Any],
    required: List[str],
    optional: List[str],
) -> Dict[str, Any]:
    """
    Validate submitted evidence against task requirements.

    Args:
        evidence: Submitted evidence dictionary
        required: List of required evidence fields
        optional: List of optional evidence fields

    Returns:
        Validated and normalized evidence dict

    Raises:
        EvidenceValidationError: If validation fails
    """
    # Check for missing required fields
    missing = [r for r in required if r not in evidence]
    if missing:
        raise EvidenceValidationError(
            f"Missing required evidence: {', '.join(missing)}"
        )

    # Check for unknown fields
    all_allowed = set(required) | set(optional)
    unknown = [k for k in evidence.keys() if k not in all_allowed]
    if unknown:
        raise EvidenceValidationError(
            f"Unknown evidence fields: {', '.join(unknown)}. "
            f"Allowed: {', '.join(all_allowed)}"
        )

    # Validate individual evidence types
    validated = {}
    for key, value in evidence.items():
        validated[key] = _validate_evidence_value(key, value)

    return validated


def _validate_evidence_value(evidence_type: str, value: Any) -> Any:
    """Validate a single evidence value based on its type."""

    # Photo evidence
    if evidence_type in ("photo", "photo_geo", "screenshot"):
        if isinstance(value, str):
            # Should be IPFS hash or URL
            if not (
                value.startswith("ipfs://")
                or value.startswith("https://")
                or value.startswith("http://")
            ):
                raise EvidenceValidationError(
                    f"{evidence_type} must be an IPFS hash or URL"
                )
            return value
        elif isinstance(value, dict):
            # Can be {url: ..., metadata: ...}
            if "url" not in value:
                raise EvidenceValidationError(
                    f"{evidence_type} dict must have 'url' field"
                )
            return value
        else:
            raise EvidenceValidationError(
                f"{evidence_type} must be string URL or dict with 'url'"
            )

    # GPS coordinates
    if evidence_type == "gps":
        if not isinstance(value, dict):
            raise EvidenceValidationError("gps must be a dict with lat/lng")
        if "lat" not in value or "lng" not in value:
            raise EvidenceValidationError("gps must have 'lat' and 'lng' fields")
        lat, lng = value.get("lat"), value.get("lng")
        if not (-90 <= lat <= 90):
            raise EvidenceValidationError("latitude must be between -90 and 90")
        if not (-180 <= lng <= 180):
            raise EvidenceValidationError("longitude must be between -180 and 180")
        return value

    # Timestamp
    if evidence_type in ("timestamp", "timestamp_proof"):
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                return value
            except ValueError:
                raise EvidenceValidationError(
                    f"{evidence_type} must be ISO 8601 format"
                )
        elif isinstance(value, (int, float)):
            # Unix timestamp
            return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
        else:
            raise EvidenceValidationError(
                f"{evidence_type} must be ISO string or Unix timestamp"
            )

    # Text response
    if evidence_type == "text_response":
        if not isinstance(value, str):
            raise EvidenceValidationError("text_response must be a string")
        if len(value) > 10000:
            raise EvidenceValidationError("text_response max 10000 characters")
        return value

    # Document/receipt/signature
    if evidence_type in ("document", "receipt", "signature", "notarized"):
        if isinstance(value, str):
            return value  # URL or IPFS hash
        elif isinstance(value, dict):
            if "url" not in value and "file" not in value:
                raise EvidenceValidationError(
                    f"{evidence_type} must have 'url' or 'file' field"
                )
            return value
        else:
            raise EvidenceValidationError(f"{evidence_type} must be URL string or dict")

    # Video
    if evidence_type == "video":
        if isinstance(value, str):
            return value
        elif isinstance(value, dict):
            if "url" not in value:
                raise EvidenceValidationError("video must have 'url' field")
            return value
        else:
            raise EvidenceValidationError("video must be URL or dict with 'url'")

    # Measurement
    if evidence_type == "measurement":
        if isinstance(value, dict):
            if "value" not in value:
                raise EvidenceValidationError("measurement must have 'value'")
            return value
        elif isinstance(value, (int, float)):
            return {"value": value, "unit": "unknown"}
        else:
            raise EvidenceValidationError(
                "measurement must be number or dict with 'value'"
            )

    # Default: accept as-is
    return value


# ============== TOOL IMPLEMENTATIONS ==============


def register_worker_tools(
    mcp: FastMCP,
    db_module: Any,
    x402_client: Optional[Any] = None,
    config: Optional[WorkerToolsConfig] = None,
) -> None:
    """
    Register worker tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        db_module: Database module with async functions
        x402_client: Optional x402 client for real withdrawals
        config: Optional configuration
    """
    config = config or WorkerToolsConfig()

    # Import models here to avoid circular imports
    from models import (
        ApplyToTaskInput,
        SubmitWorkInput,
        GetMyTasksInput,
        WithdrawEarningsInput,
        ResponseFormat,
    )

    @mcp.tool(
        name="em_apply_to_task",
        annotations={
            "title": "Apply to Work on a Task",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_apply_to_task(params: ApplyToTaskInput) -> str:
        """
        Apply to work on a published task.

        Workers can browse available tasks and apply to work on them.
        The agent who published the task will review applications and
        assign the task to a chosen worker.

        Requirements:
        - Worker must be registered in the system
        - Task must be in 'published' status
        - Worker must meet minimum reputation requirements
        - Worker cannot have already applied to this task

        Args:
            params (ApplyToTaskInput): Validated input parameters containing:
                - task_id (str): UUID of the task to apply for
                - executor_id (str): Your executor ID
                - message (str): Optional message to the agent explaining qualifications

        Returns:
            str: Confirmation of application or error message.

        Status Flow:
            Task remains 'published' until agent assigns it.
            Worker's application goes into 'pending' status.
        """
        try:
            # Call database function which handles all validation
            result = await db_module.apply_to_task(
                task_id=params.task_id,
                executor_id=params.executor_id,
                message=params.message,
            )

            task = result["task"]
            executor = result["executor"]
            result.get("application", {})

            logger.info(f"Worker {params.executor_id} applied to task {params.task_id}")

            return f"""# Application Submitted

**Task**: {task["title"]}
**Task ID**: `{task["id"]}`
**Bounty**: {format_bounty(task["bounty_usd"])} {task.get("payment_token", "USDC")}
**Deadline**: {format_datetime(task["deadline"])}

**Your Profile**:
- **Executor ID**: `{executor.get("id", params.executor_id)}`
- **Reputation**: {executor.get("reputation_score", 0)}
- **Tasks Completed**: {executor.get("tasks_completed", 0)}

Your application has been submitted. The agent will review applications
and assign the task to a worker.

{f"**Your Message**: {params.message}" if params.message else ""}

## Next Steps
1. Wait for the agent to review your application
2. If assigned, you'll be notified
3. Use `em_get_my_tasks` to check your application status"""

        except Exception as e:
            logger.error(f"Failed to apply to task: {e}")
            return f"Error: Failed to apply - {str(e)}"

    @mcp.tool(
        name="em_submit_work",
        annotations={
            "title": "Submit Completed Work",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_submit_work(params: SubmitWorkInput) -> str:
        """
        Submit completed work with evidence for an assigned task.

        After completing a task, use this to submit your evidence for review.
        The agent will verify your submission and release payment if approved.

        Requirements:
        - You must be assigned to this task
        - Task must be in 'accepted' or 'in_progress' status
        - Evidence must match the task's evidence_schema
        - All required evidence fields must be provided

        Args:
            params (SubmitWorkInput): Validated input parameters containing:
                - task_id (str): UUID of the task
                - executor_id (str): Your executor ID
                - evidence (dict): Evidence matching the task's requirements
                - notes (str): Optional notes about the submission

        Returns:
            str: Confirmation of submission or error message.

        Status Flow:
            accepted/in_progress -> submitted -> verifying -> completed

        Evidence Format Examples:
            Photo task:
                {"photo": "ipfs://Qm...", "gps": {"lat": 25.76, "lng": -80.19}}

            Document task:
                {"document": "https://storage.../doc.pdf", "timestamp": "2026-01-25T10:30:00Z"}

            Observation task:
                {"text_response": "Store is open, 5 people in line", "photo": "ipfs://..."}
        """
        try:
            # Get task first to validate evidence schema
            task = await db_module.get_task(params.task_id)
            if not task:
                return f"Error: Task {params.task_id} not found"

            # Validate evidence against schema
            schema = task.get("evidence_schema", {})
            required = schema.get("required", [])
            optional = schema.get("optional", [])

            try:
                validated_evidence = validate_evidence_schema(
                    params.evidence,
                    required,
                    optional,
                )
            except EvidenceValidationError as e:
                return f"""# Evidence Validation Failed

**Error**: {str(e)}

## Required Evidence
{chr(10).join(f"- {r}" for r in required) if required else "None"}

## Optional Evidence
{chr(10).join(f"- {o}" for o in optional) if optional else "None"}

Please resubmit with the correct evidence fields."""

            # Submit to database
            result = await db_module.submit_work(
                task_id=params.task_id,
                executor_id=params.executor_id,
                evidence=validated_evidence,
                notes=params.notes,
            )

            submission = result["submission"]
            task = result["task"]

            logger.info(
                f"Worker {params.executor_id} submitted work for task {params.task_id}"
            )

            return f"""# Work Submitted Successfully

**Task**: {task["title"]}
**Submission ID**: `{submission["id"]}`
**Status**: Awaiting Agent Review

Your evidence has been submitted. The agent will review and either:
- **Approve**: You'll receive {format_bounty(task["bounty_usd"])} {task.get("payment_token", "USDC")}
- **Request More Info**: You'll need to provide additional evidence
- **Dispute**: Your submission will go to arbitration

## Evidence Submitted
```json
{json.dumps(validated_evidence, indent=2)}
```

{f"**Notes**: {params.notes}" if params.notes else ""}

## What Happens Next
1. Agent reviews your submission
2. If approved, payment is released to your available balance
3. Use `em_withdraw_earnings` to withdraw to your wallet"""

        except Exception as e:
            logger.error(f"Failed to submit work: {e}")
            return f"Error: Failed to submit work - {str(e)}"

    @mcp.tool(
        name="em_get_my_tasks",
        annotations={
            "title": "Get My Tasks and Applications",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def em_get_my_tasks(params: GetMyTasksInput) -> str:
        """
        Get your assigned tasks, pending applications, and recent submissions.

        Use this to see:
        - Tasks assigned to you (in progress)
        - Pending applications waiting for agent approval
        - Recent submissions and their verdict status
        - Summary of your activity

        Args:
            params (GetMyTasksInput): Validated input parameters containing:
                - executor_id (str): Your executor ID
                - status (TaskStatus): Optional filter by task status
                - include_applications (bool): Include pending applications (default: True)
                - limit (int): Max results (default: 20)
                - response_format (ResponseFormat): markdown or json

        Returns:
            str: Your tasks and applications in requested format.
        """
        try:
            result = await db_module.get_executor_tasks(
                executor_id=params.executor_id,
                status=params.status.value if params.status else None,
                include_applications=params.include_applications,
                limit=params.limit,
            )

            if params.response_format == ResponseFormat.JSON:
                return json.dumps(result, indent=2, default=str)

            # Markdown format
            totals = result["totals"]
            lines = [
                "# My Tasks",
                "",
                "## Summary",
                f"- **Assigned Tasks**: {totals['assigned']}",
                f"- **Pending Applications**: {totals['pending_applications']}",
                f"- **Recent Submissions**: {totals['submissions']}",
                "",
            ]

            # Assigned tasks (most important)
            if result["assigned_tasks"]:
                lines.extend(["## Active Tasks", ""])
                for task in result["assigned_tasks"]:
                    status_icon = {
                        "accepted": "[ASSIGNED]",
                        "in_progress": "[IN PROGRESS]",
                        "submitted": "[SUBMITTED]",
                    }.get(task["status"], f"[{task['status'].upper()}]")

                    lines.extend(
                        [
                            f"### {status_icon} {task['title']}",
                            f"- **ID**: `{task['id']}`",
                            f"- **Bounty**: {format_bounty(task['bounty_usd'])}",
                            f"- **Deadline**: {format_datetime(task['deadline'])}",
                            f"- **Status**: {task['status']}",
                            "",
                        ]
                    )
            else:
                lines.extend(
                    [
                        "## Active Tasks",
                        "*No tasks currently assigned to you.*",
                        "",
                    ]
                )

            # Pending applications
            if result["applications"]:
                lines.extend(["## Pending Applications", ""])
                for app in result["applications"]:
                    task = app.get("task", {})
                    lines.append(
                        f"- **{task.get('title', 'Unknown')}** - "
                        f"{format_bounty(task.get('bounty_usd', 0))} - "
                        f"Applied {format_datetime(app.get('created_at'))}"
                    )
                lines.append("")

            # Recent submissions
            if result["recent_submissions"]:
                lines.extend(["## Recent Submissions", ""])
                for sub in result["recent_submissions"]:
                    task = sub.get("task", {})
                    verdict = sub.get("agent_verdict", "pending")
                    verdict_display = {
                        "accepted": "[APPROVED]",
                        "disputed": "[DISPUTED]",
                        "pending": "[PENDING]",
                        "more_info_requested": "[MORE INFO]",
                    }.get(verdict, f"[{verdict.upper()}]")

                    lines.append(
                        f"- {verdict_display} **{task.get('title', 'Unknown')}** - "
                        f"{format_datetime(sub.get('submitted_at'))}"
                    )
                lines.append("")

            # Help text if empty
            if not any(
                [
                    result["assigned_tasks"],
                    result["applications"],
                    result["recent_submissions"],
                ]
            ):
                lines.extend(
                    [
                        "## Getting Started",
                        "*No tasks or applications found.*",
                        "",
                        "To get started:",
                        "1. Browse available tasks with `em_get_tasks`",
                        "2. Apply to tasks that match your skills",
                        "3. Complete assigned tasks and submit evidence",
                        "",
                    ]
                )

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Failed to get tasks: {e}")
            return f"Error: Failed to get tasks - {str(e)}"

    @mcp.tool(
        name="em_withdraw_earnings",
        annotations={
            "title": "Withdraw Earnings",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_withdraw_earnings(params: WithdrawEarningsInput) -> str:
        """
        Withdraw your available earnings to your wallet.

        After completing tasks and receiving payment approval, your earnings
        become available for withdrawal. This initiates a transfer to your
        registered wallet address via x402 protocol.

        Requirements:
        - Minimum withdrawal: $5.00 USDC
        - Must have available balance
        - Wallet address must be registered or provided

        Args:
            params (WithdrawEarningsInput): Validated input parameters containing:
                - executor_id (str): Your executor ID
                - amount_usdc (float): Amount to withdraw (None = all available)
                - destination_address (str): Optional different wallet address

        Returns:
            str: Withdrawal confirmation with transaction details, or error message.

        Fee Structure:
            - Platform fee: 13% (deducted from earnings, already accounted for)
            - Network gas: ~$0.50 (deducted from withdrawal amount)

        Networks:
            - Withdrawals are processed on Base network
            - USDC contract: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
        """
        try:
            # Get earnings summary
            earnings = await db_module.get_executor_earnings(params.executor_id)

            available = earnings.get("available", 0.0)
            pending = earnings.get("pending", 0.0)
            total_earned = earnings.get("total_earned", 0.0)

            # Check minimum balance
            if available < config.min_withdrawal_usdc:
                return f"""# Insufficient Balance

**Available**: {format_bounty(available)}
**Pending**: {format_bounty(pending)}
**Minimum Withdrawal**: {format_bounty(config.min_withdrawal_usdc)}

You need at least {format_bounty(config.min_withdrawal_usdc)} to withdraw.
Complete more tasks to reach the minimum.

## Earnings Summary
- **Total Earned**: {format_bounty(total_earned)}
- **Available for Withdrawal**: {format_bounty(available)}
- **Pending Approval**: {format_bounty(pending)}"""

            # Determine withdrawal amount
            withdraw_amount = params.amount_usdc or available
            if withdraw_amount > available:
                return f"""# Insufficient Balance

**Requested**: {format_bounty(withdraw_amount)}
**Available**: {format_bounty(available)}

You cannot withdraw more than your available balance."""

            if withdraw_amount < config.min_withdrawal_usdc:
                return f"""# Below Minimum

**Requested**: {format_bounty(withdraw_amount)}
**Minimum**: {format_bounty(config.min_withdrawal_usdc)}

Minimum withdrawal is {format_bounty(config.min_withdrawal_usdc)}."""

            # Get executor wallet
            executor = await db_module.get_executor_stats(params.executor_id)
            if not executor:
                return "Error: Executor not found. Please register first."

            destination = params.destination_address or executor.get("wallet_address")
            if not destination:
                return """Error: No wallet address registered.

Please update your profile with a wallet address before withdrawing.
You can also provide a destination_address parameter."""

            # Calculate fees
            gas_fee = config.estimated_gas_usdc
            net_amount = withdraw_amount - gas_fee

            if net_amount <= 0:
                return f"""# Withdrawal Too Small

**Amount**: {format_bounty(withdraw_amount)}
**Gas Fee**: ~{format_bounty(gas_fee)}
**Net Amount**: {format_bounty(net_amount)}

Withdrawal amount must cover gas fees. Try withdrawing more."""

            # Process withdrawal
            if config.x402_enabled and x402_client:
                # Real withdrawal via x402
                try:
                    payment_result = await x402_client.send_payment(
                        to_address=destination,
                        amount_usdc=net_amount,
                        memo=f"Execution Market withdrawal for executor {params.executor_id[:8]}",
                    )

                    if payment_result.success:
                        # Record the withdrawal in database
                        # await db_module.record_withdrawal(...)

                        return f"""# Withdrawal Successful

**Amount**: {format_bounty(withdraw_amount)}
**Gas Fee**: {format_bounty(gas_fee)}
**Net Received**: {format_bounty(net_amount)}
**Destination**: `{destination}`
**Network**: Base
**Transaction**: `{payment_result.tx_hash}`

View on BaseScan: https://basescan.org/tx/{payment_result.tx_hash}

**Remaining Balance**: {format_bounty(available - withdraw_amount)}"""
                    else:
                        return f"""# Withdrawal Failed

**Error**: {payment_result.error}

Please try again later or contact support if the issue persists."""

                except Exception as e:
                    logger.error(f"x402 withdrawal failed: {e}")
                    return f"Error: Withdrawal failed - {str(e)}"

            else:
                # Simulated withdrawal (x402 not configured)
                logger.info(
                    f"Simulated withdrawal: {withdraw_amount} USDC to {destination}"
                )

                return f"""# Withdrawal Initiated

**Amount**: {format_bounty(withdraw_amount)}
**Estimated Gas**: ~{format_bounty(gas_fee)}
**Net Amount**: ~{format_bounty(net_amount)}
**Destination**: `{destination}`
**Network**: Base

Your withdrawal is being processed via x402 protocol.
Estimated arrival: 1-5 minutes

**Remaining Balance**: ~{format_bounty(available - withdraw_amount)}

## Fee Breakdown
- Gas fees are deducted from the withdrawal amount
- Platform fees (13%) were already deducted when earnings were credited

*Note: This is a simulated response. Configure x402_client for real withdrawals.*"""

        except Exception as e:
            logger.error(f"Failed to process withdrawal: {e}")
            return f"Error: Failed to process withdrawal - {str(e)}"

    logger.info("Worker tools registered successfully")


# ============== STANDALONE REGISTRATION ==============


def create_worker_tools_standalone(
    db_module: Any,
    x402_client: Optional[Any] = None,
    config: Optional[WorkerToolsConfig] = None,
) -> FastMCP:
    """
    Create a standalone MCP server with only worker tools.

    Useful for testing or running worker tools as a separate service.

    Args:
        db_module: Database module with async functions
        x402_client: Optional x402 client for real withdrawals
        config: Optional configuration

    Returns:
        FastMCP server instance with worker tools registered
    """
    mcp = FastMCP("em_worker_tools")
    register_worker_tools(mcp, db_module, x402_client, config)
    return mcp
