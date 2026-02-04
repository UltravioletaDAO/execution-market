"""
Advanced Escrow MCP Tools for Execution Market

Exposes the 5 Advanced Escrow flows to AI agents via MCP tools:
1. AUTHORIZE  - Lock bounty in escrow
2. RELEASE    - Pay worker
3. REFUND     - Return bounty to agent
4. CHARGE     - Instant payment (no escrow)
5. DISPUTE    - Post-release refund

Plus helper tools:
- recommend_strategy - AI-assisted strategy selection
- partial_release    - Proof-of-attempt flow
- status             - Query payment state

These tools wrap EMAdvancedEscrow (from the integration layer),
which in turn calls the uvd-x402-sdk AdvancedEscrowClient.
"""

import json
import logging
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)

# Try to import the integration layer
ADVANCED_ESCROW_AVAILABLE = False
_escrow_instance = None

try:
    from integrations.x402.advanced_escrow_integration import (
        EMAdvancedEscrow,
        PaymentStrategy,
        TaskPayment,
        get_advanced_escrow,
        ADVANCED_ESCROW_AVAILABLE as _SDK_AVAILABLE,
        DEPOSIT_LIMIT_USDC,
    )
    ADVANCED_ESCROW_AVAILABLE = _SDK_AVAILABLE
except ImportError:
    logger.warning("Advanced escrow integration not available")
    PaymentStrategy = None
    DEPOSIT_LIMIT_USDC = Decimal("100")


# ============== INPUT MODELS ==============


class EscrowRecommendInput(BaseModel):
    """Input for strategy recommendation."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
    )

    amount_usdc: float = Field(
        ...,
        description="Bounty amount in USDC",
        gt=0,
        le=10000,
    )
    worker_reputation: float = Field(
        default=0.0,
        description="Worker reputation score (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    external_dependency: bool = Field(
        default=False,
        description="Task depends on external factors (weather, events, etc.)",
    )
    requires_quality_review: bool = Field(
        default=False,
        description="Task requires quality assurance after delivery",
    )
    erc8004_score: Optional[float] = Field(
        default=None,
        description="On-chain ERC-8004 reputation score (0.0-1.0). Overrides worker_reputation if provided.",
        ge=0.0,
        le=1.0,
    )


class EscrowAuthorizeInput(BaseModel):
    """Input for escrow authorization (lock funds)."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
    )

    task_id: str = Field(
        ...,
        description="UUID of the task",
        min_length=1,
        max_length=255,
    )
    receiver: str = Field(
        ...,
        description="Worker wallet address (0x...)",
        min_length=42,
        max_length=42,
    )
    amount_usdc: float = Field(
        ...,
        description="Bounty amount in USDC. Current contract limit: $100.",
        gt=0,
        le=10000,
    )
    strategy: str = Field(
        default="escrow_capture",
        description="Payment strategy: escrow_capture, escrow_cancel, instant_payment, partial_payment, dispute_resolution",
    )
    tier: Optional[str] = Field(
        default=None,
        description="Override tier: micro, standard, premium, enterprise. Auto-detected from amount if not set.",
    )


class EscrowReleaseInput(BaseModel):
    """Input for releasing escrowed funds to worker."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
    )

    task_id: str = Field(
        ...,
        description="UUID of the task",
        min_length=1,
        max_length=255,
    )
    amount_usdc: Optional[float] = Field(
        default=None,
        description="Amount to release in USDC. Releases full bounty if not specified.",
        gt=0,
        le=10000,
    )


class EscrowRefundInput(BaseModel):
    """Input for refunding escrowed funds to agent."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
    )

    task_id: str = Field(
        ...,
        description="UUID of the task",
        min_length=1,
        max_length=255,
    )
    amount_usdc: Optional[float] = Field(
        default=None,
        description="Amount to refund in USDC. Refunds full bounty if not specified.",
        gt=0,
        le=10000,
    )


class EscrowChargeInput(BaseModel):
    """Input for instant payment (no escrow)."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
    )

    task_id: str = Field(
        ...,
        description="UUID of the task",
        min_length=1,
        max_length=255,
    )
    receiver: str = Field(
        ...,
        description="Worker wallet address (0x...)",
        min_length=42,
        max_length=42,
    )
    amount_usdc: float = Field(
        ...,
        description="Payment amount in USDC",
        gt=0,
        le=10000,
    )
    tier: Optional[str] = Field(
        default=None,
        description="Override tier: micro, standard, premium, enterprise",
    )


class EscrowPartialReleaseInput(BaseModel):
    """Input for partial release + refund (proof of attempt)."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
    )

    task_id: str = Field(
        ...,
        description="UUID of the task",
        min_length=1,
        max_length=255,
    )
    release_percent: int = Field(
        default=15,
        description="Percentage to release to worker (1-99). Default 15% for proof-of-attempt.",
        ge=1,
        le=99,
    )


class EscrowDisputeInput(BaseModel):
    """Input for dispute (post-release refund)."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
    )

    task_id: str = Field(
        ...,
        description="UUID of the task",
        min_length=1,
        max_length=255,
    )
    amount_usdc: Optional[float] = Field(
        default=None,
        description="Amount to dispute in USDC. Disputes full bounty if not specified.",
        gt=0,
        le=10000,
    )


class EscrowStatusInput(BaseModel):
    """Input for querying payment status."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
    )

    task_id: str = Field(
        ...,
        description="UUID of the task",
        min_length=1,
        max_length=255,
    )


# ============== HELPERS ==============


STRATEGY_DESCRIPTIONS = {
    "escrow_capture": "Standard escrow: lock funds, then release to worker on approval",
    "escrow_cancel": "Cancellable escrow: lock funds, refund if task depends on external factors",
    "instant_payment": "Direct payment: no escrow, instant transfer to trusted workers",
    "partial_payment": "Partial escrow: release partial payment for proof-of-attempt, refund remainder",
    "dispute_resolution": "Arbiter escrow: keep funds locked, arbiter decides release or refund in-escrow",
}

TIER_INFO = {
    "micro": {"range": "$0-$5", "escrow_timeout": "24h", "dispute_window": "48h"},
    "standard": {"range": "$5-$50", "escrow_timeout": "72h", "dispute_window": "7 days"},
    "premium": {"range": "$50-$200", "escrow_timeout": "7 days", "dispute_window": "14 days"},
    "enterprise": {"range": "$200+", "escrow_timeout": "30 days", "dispute_window": "30 days"},
}


def _get_escrow():
    """Get or create the escrow instance. Raises if not available."""
    global _escrow_instance
    if not ADVANCED_ESCROW_AVAILABLE:
        raise RuntimeError(
            "Advanced Escrow not available. "
            "Ensure uvd-x402-sdk>=0.6.0 is installed and WALLET_PRIVATE_KEY is set."
        )
    if _escrow_instance is None:
        _escrow_instance = get_advanced_escrow()
    return _escrow_instance


def _format_task_payment(payment) -> str:
    """Format a TaskPayment as markdown."""
    lines = [
        f"- **Task ID**: `{payment.task_id}`",
        f"- **Strategy**: {payment.strategy.value if hasattr(payment.strategy, 'value') else payment.strategy}",
        f"- **Status**: {payment.status.upper()}",
        f"- **Amount**: ${payment.amount_usdc:.2f} USDC",
        f"- **Released**: ${payment.released_usdc:.2f} USDC",
        f"- **Refunded**: ${payment.refunded_usdc:.2f} USDC",
    ]
    if payment.tx_hashes:
        lines.append("- **Transactions**:")
        for tx in payment.tx_hashes:
            lines.append(f"  - `{tx[:20]}...`")
    return "\n".join(lines)


# ============== TOOL REGISTRATION ==============


def register_escrow_tools(mcp):
    """
    Register Advanced Escrow MCP tools with the server.

    Args:
        mcp: FastMCP server instance
    """

    # ------------------------------------------------------------------
    # Tool 1: Recommend Strategy (read-only)
    # ------------------------------------------------------------------

    @mcp.tool(
        name="em_escrow_recommend_strategy",
        annotations={
            "title": "Recommend Escrow Payment Strategy",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def em_escrow_recommend_strategy(params: EscrowRecommendInput) -> str:
        """
        Recommend the best payment strategy for a task based on its parameters.

        Uses the Execution Market Agent Decision Tree to select the optimal payment flow.
        When ERC-8004 on-chain reputation is available, it takes precedence.

        Decision logic:
        - High reputation (>90%) + micro amount (<$5) -> instant_payment
        - External dependency (weather, events) -> escrow_cancel
        - Quality review needed + high value (>=$50) -> dispute_resolution
        - Low reputation (<50%) + high value (>=$50) -> dispute_resolution
        - Default -> escrow_capture

        Args:
            params: Amount, reputation, and task characteristics

        Returns:
            Recommended strategy with explanation and tier timings.
        """
        if not ADVANCED_ESCROW_AVAILABLE:
            return (
                "# Advanced Escrow Not Available\n\n"
                "The uvd-x402-sdk is not installed or WALLET_PRIVATE_KEY is not set.\n"
                "Install: `pip install uvd-x402-sdk>=0.6.0`"
            )

        try:
            escrow = _get_escrow()
            strategy = escrow.recommend_strategy(
                amount_usdc=Decimal(str(params.amount_usdc)),
                worker_reputation=params.worker_reputation,
                external_dependency=params.external_dependency,
                requires_quality_review=params.requires_quality_review,
                erc8004_score=params.erc8004_score,
            )

            # Determine tier
            amount = Decimal(str(params.amount_usdc))
            if amount < 5:
                tier = "micro"
            elif amount < 50:
                tier = "standard"
            elif amount < 200:
                tier = "premium"
            else:
                tier = "enterprise"

            tier_data = TIER_INFO[tier]

            lines = [
                "# Recommended Payment Strategy",
                "",
                f"**Strategy**: `{strategy.value}`",
                f"**Description**: {STRATEGY_DESCRIPTIONS.get(strategy.value, 'N/A')}",
                "",
                "## Task Parameters",
                f"- **Amount**: ${params.amount_usdc:.2f} USDC",
                f"- **Tier**: {tier} ({tier_data['range']})",
                f"- **Worker Reputation**: {params.worker_reputation:.2f}",
            ]

            if params.erc8004_score is not None:
                lines.append(f"- **ERC-8004 Score**: {params.erc8004_score:.2f} (on-chain, takes precedence)")

            lines.extend([
                f"- **External Dependency**: {'Yes' if params.external_dependency else 'No'}",
                f"- **Quality Review**: {'Yes' if params.requires_quality_review else 'No'}",
                "",
                "## Tier Timings",
                f"- **Escrow Timeout**: {tier_data['escrow_timeout']}",
                f"- **Dispute Window**: {tier_data['dispute_window']}",
                "",
                "## Available Strategies",
            ])

            for name, desc in STRATEGY_DESCRIPTIONS.items():
                marker = " **(recommended)**" if name == strategy.value else ""
                lines.append(f"- `{name}`: {desc}{marker}")

            # Deposit limit warning
            if params.amount_usdc > float(DEPOSIT_LIMIT_USDC):
                lines.extend([
                    "",
                    f"## Deposit Limit Warning",
                    f"Amount ${params.amount_usdc:.2f} exceeds the current contract limit of ${DEPOSIT_LIMIT_USDC}.",
                    "The transaction will fail on-chain. Reduce the bounty or contact the protocol team.",
                ])

            # Note about dispute_resolution strategy
            if strategy.value == "dispute_resolution":
                lines.extend([
                    "",
                    "## Dispute Resolution Note",
                    "This strategy keeps funds **in escrow** until an arbiter decides.",
                    "Do NOT release funds until quality is verified.",
                    "- If quality OK: `em_escrow_release`",
                    "- If quality fails: `em_escrow_refund` (funds guaranteed in escrow)",
                    "",
                    "Post-release refund (`em_escrow_dispute`) is not available in production.",
                ])

            lines.extend([
                "",
                "## Next Step",
                f"Call `em_escrow_authorize` with strategy=`{strategy.value}` to lock the bounty.",
            ])

            return "\n".join(lines)

        except Exception as e:
            logger.error("Error recommending strategy: %s", e)
            return f"Error: Failed to recommend strategy - {e}"

    # ------------------------------------------------------------------
    # Tool 2: Authorize (lock funds in escrow)
    # ------------------------------------------------------------------

    @mcp.tool(
        name="em_escrow_authorize",
        annotations={
            "title": "Lock Bounty in Escrow",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_escrow_authorize(params: EscrowAuthorizeInput) -> str:
        """
        Lock a task bounty in escrow via the PaymentOperator contract.

        This is the first step for escrow-based payment strategies.
        Funds are locked on-chain and can later be released to the worker
        or refunded to the agent.

        The on-chain flow: Agent USDC -> PaymentOperator.authorize() -> Escrow contract

        Args:
            params: task_id, receiver wallet, amount, strategy, optional tier override

        Returns:
            Authorization result with transaction hash and payment info.
        """
        try:
            # Check deposit limit
            if params.amount_usdc > float(DEPOSIT_LIMIT_USDC):
                return f"""# Amount Exceeds Contract Deposit Limit

**Task ID**: `{params.task_id}`
**Requested**: ${params.amount_usdc:.2f} USDC
**Contract Limit**: ${DEPOSIT_LIMIT_USDC} USDC

The PaymentOperator contract currently enforces a ${DEPOSIT_LIMIT_USDC} deposit limit.
This transaction will fail on-chain.

Options:
1. Reduce the bounty to ${DEPOSIT_LIMIT_USDC} or less
2. Split into multiple smaller escrows
3. Contact the protocol team to raise the limit"""

            escrow = _get_escrow()
            strategy = PaymentStrategy(params.strategy)

            payment = escrow.authorize_task(
                task_id=params.task_id,
                receiver=params.receiver,
                amount_usdc=Decimal(str(params.amount_usdc)),
                strategy=strategy,
                tier=params.tier,
            )

            if payment.status == "failed":
                error_msg = ""
                if payment.authorization:
                    error_msg = getattr(payment.authorization, 'error', 'Unknown error')
                return f"""# Escrow Authorization Failed

**Task ID**: `{params.task_id}`
**Amount**: ${params.amount_usdc:.2f} USDC
**Error**: {error_msg}

Check that:
1. Wallet has sufficient USDC balance
2. USDC spending is approved for the PaymentOperator contract
3. Amount is within contract deposit limit (${DEPOSIT_LIMIT_USDC})
4. RPC endpoint is responsive"""

            lines = [
                "# Escrow Authorized",
                "",
                _format_task_payment(payment),
                "",
                "## Next Steps",
            ]

            if strategy == PaymentStrategy.ESCROW_CAPTURE:
                lines.append("- When task is approved: call `em_escrow_release`")
                lines.append("- If task is cancelled: call `em_escrow_refund`")
            elif strategy == PaymentStrategy.ESCROW_CANCEL:
                lines.append("- If conditions are met: call `em_escrow_release`")
                lines.append("- If conditions fail: call `em_escrow_refund`")
            elif strategy == PaymentStrategy.PARTIAL_PAYMENT:
                lines.append("- For proof-of-attempt: call `em_escrow_partial_release`")
            elif strategy == PaymentStrategy.DISPUTE_RESOLUTION:
                lines.append("- Arbiter reviews work quality")
                lines.append("- If approved: call `em_escrow_release`")
                lines.append("- If rejected: call `em_escrow_refund` (funds still in escrow)")

            return "\n".join(lines)

        except Exception as e:
            logger.error("Error authorizing escrow for task %s: %s", params.task_id, e)
            return f"Error: Failed to authorize escrow - {e}"

    # ------------------------------------------------------------------
    # Tool 3: Release (pay worker)
    # ------------------------------------------------------------------

    @mcp.tool(
        name="em_escrow_release",
        annotations={
            "title": "Release Escrow to Worker",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_escrow_release(params: EscrowReleaseInput) -> str:
        """
        Release escrowed funds to the worker after task approval.

        The on-chain flow: Escrow contract -> PaymentOperator.release() -> Worker USDC

        This is an irreversible operation. Once released, funds go directly
        to the worker's wallet. For dispute resolution after release,
        use em_escrow_dispute.

        Args:
            params: task_id, optional amount (defaults to full bounty)

        Returns:
            Transaction result with hash and gas used.
        """
        try:
            escrow = _get_escrow()
            amount = Decimal(str(params.amount_usdc)) if params.amount_usdc else None

            result = escrow.release_to_worker(
                task_id=params.task_id,
                amount_usdc=amount,
            )

            if not result.success:
                return f"""# Release Failed

**Task ID**: `{params.task_id}`
**Error**: {result.error}

Check that:
1. Task was previously authorized (call `em_escrow_status` to verify)
2. Escrow has not already been released or refunded
3. Facilitator wallet has gas funds"""

            payment = escrow.get_task_payment(params.task_id)
            released = params.amount_usdc or (float(payment.amount_usdc) if payment else 0)

            return f"""# Payment Released to Worker

**Task ID**: `{params.task_id}`
**Amount Released**: ${released:.2f} USDC
**Transaction**: `{result.transaction_hash}`
**Gas Used**: {result.gas_used}

The worker has received the payment. Task payment is complete."""

        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            logger.error("Error releasing escrow for task %s: %s", params.task_id, e)
            return f"Error: Failed to release escrow - {e}"

    # ------------------------------------------------------------------
    # Tool 4: Refund (return to agent)
    # ------------------------------------------------------------------

    @mcp.tool(
        name="em_escrow_refund",
        annotations={
            "title": "Refund Escrow to Agent",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_escrow_refund(params: EscrowRefundInput) -> str:
        """
        Refund escrowed funds back to the agent (cancel task).

        The on-chain flow: Escrow contract -> PaymentOperator.refundInEscrow() -> Agent USDC

        Use this when a task is cancelled before completion.
        Only works if funds are still in escrow (not yet released).

        Args:
            params: task_id, optional amount (defaults to full bounty)

        Returns:
            Transaction result with hash and gas used.
        """
        try:
            escrow = _get_escrow()
            amount = Decimal(str(params.amount_usdc)) if params.amount_usdc else None

            result = escrow.refund_to_agent(
                task_id=params.task_id,
                amount_usdc=amount,
            )

            if not result.success:
                return f"""# Refund Failed

**Task ID**: `{params.task_id}`
**Error**: {result.error}

Check that:
1. Task was previously authorized (call `em_escrow_status` to verify)
2. Escrow has not already been released
3. Escrow timeout has not expired"""

            payment = escrow.get_task_payment(params.task_id)
            refunded = params.amount_usdc or (float(payment.amount_usdc) if payment else 0)

            return f"""# Escrow Refunded to Agent

**Task ID**: `{params.task_id}`
**Amount Refunded**: ${refunded:.2f} USDC
**Transaction**: `{result.transaction_hash}`
**Gas Used**: {result.gas_used}

The bounty has been returned to the agent's wallet."""

        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            logger.error("Error refunding escrow for task %s: %s", params.task_id, e)
            return f"Error: Failed to refund escrow - {e}"

    # ------------------------------------------------------------------
    # Tool 5: Charge (instant payment, no escrow)
    # ------------------------------------------------------------------

    @mcp.tool(
        name="em_escrow_charge",
        annotations={
            "title": "Instant Payment to Worker",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_escrow_charge(params: EscrowChargeInput) -> str:
        """
        Make an instant payment to a worker without escrow.

        The on-chain flow: Agent USDC -> PaymentOperator.charge() -> Worker USDC (direct)

        Best for:
        - Micro-tasks under $5
        - Trusted workers with >90% reputation
        - Time-sensitive payments

        This is a single-step operation. Funds go directly to the worker.

        Args:
            params: task_id, receiver wallet, amount, optional tier

        Returns:
            Transaction result with hash and confirmation.
        """
        try:
            # Check deposit limit
            if params.amount_usdc > float(DEPOSIT_LIMIT_USDC):
                return f"""# Amount Exceeds Contract Deposit Limit

**Task ID**: `{params.task_id}`
**Requested**: ${params.amount_usdc:.2f} USDC
**Contract Limit**: ${DEPOSIT_LIMIT_USDC} USDC

The PaymentOperator contract currently enforces a ${DEPOSIT_LIMIT_USDC} deposit limit.
Reduce the amount or contact the protocol team to raise the limit."""

            escrow = _get_escrow()

            payment = escrow.charge_instant(
                task_id=params.task_id,
                receiver=params.receiver,
                amount_usdc=Decimal(str(params.amount_usdc)),
                tier=params.tier,
            )

            if payment.status == "failed":
                return f"""# Instant Payment Failed

**Task ID**: `{params.task_id}`
**Receiver**: `{params.receiver}`
**Amount**: ${params.amount_usdc:.2f} USDC

Check that:
1. Wallet has sufficient USDC balance
2. USDC spending is approved for the PaymentOperator contract
3. Amount is within contract deposit limit (${DEPOSIT_LIMIT_USDC})
4. Receiver address is valid"""

            return f"""# Instant Payment Sent

{_format_task_payment(payment)}

Payment was sent directly to the worker without escrow.
This transaction is final and cannot be reversed through the escrow system."""

        except Exception as e:
            logger.error("Error charging instant payment for task %s: %s", params.task_id, e)
            return f"Error: Failed to send instant payment - {e}"

    # ------------------------------------------------------------------
    # Tool 6: Partial Release (proof of attempt)
    # ------------------------------------------------------------------

    @mcp.tool(
        name="em_escrow_partial_release",
        annotations={
            "title": "Partial Release + Refund (Proof of Attempt)",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_escrow_partial_release(params: EscrowPartialReleaseInput) -> str:
        """
        Release a partial payment for proof-of-attempt and refund the remainder.

        This is a two-step operation:
        1. Release X% to the worker (reward for attempting the task)
        2. Refund (100-X)% to the agent

        Common use case: Worker attempted the task but couldn't fully complete it.
        Default is 15% release for proof-of-attempt.

        Args:
            params: task_id, release_percent (1-99, default 15%)

        Returns:
            Both transaction results with amounts.
        """
        try:
            escrow = _get_escrow()

            result = escrow.partial_release_and_refund(
                task_id=params.task_id,
                release_percent=params.release_percent,
            )

            if not result.get("success"):
                error = result.get("error", "Unknown error")
                return f"""# Partial Release Failed

**Task ID**: `{params.task_id}`
**Release %**: {params.release_percent}%
**Error**: {error}

Check that the task was authorized and escrow is still active."""

            lines = [
                "# Partial Release Complete",
                "",
                f"**Task ID**: `{params.task_id}`",
                f"**Split**: {params.release_percent}% to worker / {100 - params.release_percent}% refunded",
                "",
                "## Worker Payment",
                f"- **Amount**: ${result.get('released_usdc', '0')} USDC",
            ]

            release_result = result.get("release_result")
            if release_result:
                lines.append(f"- **Transaction**: `{release_result.transaction_hash}`")
                lines.append(f"- **Gas Used**: {release_result.gas_used}")

            lines.extend(["", "## Agent Refund"])

            if result.get("warning"):
                lines.append(f"- **Warning**: {result['warning']}")
            else:
                lines.append(f"- **Amount**: ${result.get('refunded_usdc', '0')} USDC")
                refund_result = result.get("refund_result")
                if refund_result:
                    lines.append(f"- **Transaction**: `{refund_result.transaction_hash}`")
                    lines.append(f"- **Gas Used**: {refund_result.gas_used}")

            return "\n".join(lines)

        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            logger.error("Error in partial release for task %s: %s", params.task_id, e)
            return f"Error: Failed partial release - {e}"

    # ------------------------------------------------------------------
    # Tool 7: Dispute (post-release refund)
    # ------------------------------------------------------------------

    @mcp.tool(
        name="em_escrow_dispute",
        annotations={
            "title": "Initiate Dispute (Post-Release Refund)",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_escrow_dispute(params: EscrowDisputeInput) -> str:
        """
        Initiate a post-release dispute refund.

        WARNING: NOT FUNCTIONAL IN PRODUCTION. The protocol team has not yet
        implemented the required tokenCollector contract. This tool will fail.

        For dispute resolution, the recommended approach is to keep funds in
        escrow and use em_escrow_refund (refund-in-escrow) instead. This
        guarantees funds are available and under arbiter control.

        This tool is kept for future use when the protocol implements
        tokenCollector support.

        Args:
            params: task_id, optional amount to dispute

        Returns:
            Dispute result (will fail - tokenCollector not implemented).
        """
        # Return clear guidance instead of attempting a doomed transaction
        return f"""# Dispute (Post-Release Refund) - Not Available

**Task ID**: `{params.task_id}`

Post-release refunds (`refundPostEscrow`) are NOT functional in production.
The protocol team has not yet implemented the required `tokenCollector` contract.

## Recommended Alternative

Use **in-escrow dispute resolution** instead:

1. **Keep funds in escrow** (do NOT release until quality is verified)
2. If quality is acceptable: `em_escrow_release`
3. If quality is unacceptable: `em_escrow_refund` (funds guaranteed available)

This is safer because funds remain under arbiter control while in escrow,
vs post-escrow which relies on merchant goodwill.

## When Will This Work?

The protocol team will implement `tokenCollector` in a future release.
Once available, this tool will allow refunds after funds have been released."""

    # ------------------------------------------------------------------
    # Tool 8: Status (read-only)
    # ------------------------------------------------------------------

    @mcp.tool(
        name="em_escrow_status",
        annotations={
            "title": "Get Escrow Payment Status",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def em_escrow_status(params: EscrowStatusInput) -> str:
        """
        Get the current escrow payment status for a task.

        Returns the payment state including:
        - Authorization status
        - Amount locked, released, and refunded
        - Transaction hashes
        - Current payment strategy

        Args:
            params: task_id

        Returns:
            Payment status details or "not found" if task has no escrow.
        """
        if not ADVANCED_ESCROW_AVAILABLE:
            return (
                "# Advanced Escrow Not Available\n\n"
                "The uvd-x402-sdk is not installed or WALLET_PRIVATE_KEY is not set."
            )

        try:
            escrow = _get_escrow()
            payment = escrow.get_task_payment(params.task_id)

            if not payment:
                return f"""# No Escrow Found

**Task ID**: `{params.task_id}`

No escrow payment found for this task. Either:
1. The task has not been authorized yet (call `em_escrow_authorize`)
2. The escrow was created in a different server session
3. The task uses a different payment method"""

            remaining = payment.amount_usdc - payment.released_usdc - payment.refunded_usdc

            lines = [
                "# Escrow Payment Status",
                "",
                _format_task_payment(payment),
                "",
                "## Balance",
                f"- **Remaining in escrow**: ${remaining:.2f} USDC",
            ]

            # Suggest next action based on status
            if payment.status == "authorized":
                lines.extend([
                    "",
                    "## Available Actions",
                    "- `em_escrow_release` - Pay the worker",
                    "- `em_escrow_refund` - Cancel and refund",
                    "- `em_escrow_partial_release` - Partial payment",
                ])
            elif payment.status == "released":
                lines.extend([
                    "",
                    "Payment has been released to the worker.",
                    "Post-release dispute is not available in production (tokenCollector not implemented).",
                ])
            elif payment.status in ("refunded", "charged", "partial_released"):
                lines.extend(["", "Payment is complete. No further actions available."])

            return "\n".join(lines)

        except Exception as e:
            logger.error("Error getting escrow status for task %s: %s", params.task_id, e)
            return f"Error: Failed to get escrow status - {e}"

    logger.info(
        "Advanced Escrow tools registered: "
        "em_escrow_recommend_strategy, em_escrow_authorize, "
        "em_escrow_release, em_escrow_refund, em_escrow_charge, "
        "em_escrow_partial_release, em_escrow_dispute, em_escrow_status"
    )


# ============== EXPORTS ==============


__all__ = [
    # Registration
    "register_escrow_tools",
    # Availability flag
    "ADVANCED_ESCROW_AVAILABLE",
    # Input models
    "EscrowRecommendInput",
    "EscrowAuthorizeInput",
    "EscrowReleaseInput",
    "EscrowRefundInput",
    "EscrowChargeInput",
    "EscrowPartialReleaseInput",
    "EscrowDisputeInput",
    "EscrowStatusInput",
]
