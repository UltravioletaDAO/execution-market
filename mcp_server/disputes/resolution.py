"""
Dispute Resolution Logic

Handles the mechanics of resolving disputes:
- Refund calculations
- Payment distribution
- Notifications to parties
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from .models import (
    Dispute,
    DisputeParty,
    DisputeResolution,
    ResolutionType,
)

if TYPE_CHECKING:
    from ..integrations.x402.escrow import EscrowManager

logger = logging.getLogger(__name__)


class ResolutionError(Exception):
    """Error during resolution execution."""

    pass


def calculate_refund_split(
    dispute: Dispute,
    worker_payout_pct: Optional[float] = None,
    base_worker_reputation: float = 0.5,
    base_agent_reputation: float = 0.5,
) -> Dict[str, Any]:
    """
    Calculate fair split of disputed funds.

    Uses multiple factors to determine split:
    1. Explicit percentage if provided
    2. Evidence strength (number of evidence items)
    3. Response completeness
    4. Historical reputation (if available)

    Args:
        dispute: The dispute to calculate split for
        worker_payout_pct: Explicit worker payout percentage (overrides calculation)
        base_worker_reputation: Worker's base reputation score (0-1)
        base_agent_reputation: Agent's base reputation score (0-1)

    Returns:
        Dict with split details:
        - worker_pct: Percentage to worker
        - agent_pct: Percentage to agent (refund)
        - worker_amount: Amount to worker in USD
        - agent_amount: Amount to agent in USD
        - calculation_details: How the split was determined
    """
    amount = dispute.amount_disputed

    # If explicit percentage provided, use it
    if worker_payout_pct is not None:
        worker_pct = Decimal(str(worker_payout_pct))
        agent_pct = Decimal("1.0") - worker_pct
        return {
            "worker_pct": float(worker_pct),
            "agent_pct": float(agent_pct),
            "worker_amount": float((amount * worker_pct).quantize(Decimal("0.01"))),
            "agent_amount": float((amount * agent_pct).quantize(Decimal("0.01"))),
            "calculation_details": {
                "method": "explicit",
                "worker_payout_pct": worker_payout_pct,
            },
        }

    # Calculate based on factors
    factors = {}
    score_worker = Decimal("0.5")  # Start at 50/50

    # Factor 1: Evidence strength
    worker_evidence = sum(1 for e in dispute.evidence if e.party == DisputeParty.WORKER)
    agent_evidence = sum(1 for e in dispute.evidence if e.party == DisputeParty.AGENT)
    total_evidence = worker_evidence + agent_evidence

    if total_evidence > 0:
        evidence_ratio = worker_evidence / total_evidence
        evidence_factor = Decimal(str((evidence_ratio - 0.5) * 0.2))  # Max +/- 10%
        score_worker += evidence_factor
        factors["evidence"] = {
            "worker_count": worker_evidence,
            "agent_count": agent_evidence,
            "factor": float(evidence_factor),
        }

    # Factor 2: Response completeness
    worker_responses = sum(
        1 for r in dispute.responses if r.responder_party == DisputeParty.WORKER
    )
    agent_responses = sum(
        1 for r in dispute.responses if r.responder_party == DisputeParty.AGENT
    )

    # If one party didn't respond, penalize them
    if worker_responses == 0 and agent_responses > 0:
        response_factor = Decimal("-0.15")  # -15% for not responding
        score_worker += response_factor
        factors["response_penalty"] = {
            "party": "worker",
            "factor": float(response_factor),
        }
    elif agent_responses == 0 and worker_responses > 0:
        response_factor = Decimal("0.15")  # +15% for agent not responding
        score_worker += response_factor
        factors["response_penalty"] = {
            "party": "agent",
            "factor": float(response_factor),
        }

    # Factor 3: Reputation
    rep_diff = base_worker_reputation - base_agent_reputation
    rep_factor = Decimal(str(rep_diff * 0.1))  # Max +/- 5%
    score_worker += rep_factor
    factors["reputation"] = {
        "worker_score": base_worker_reputation,
        "agent_score": base_agent_reputation,
        "factor": float(rep_factor),
    }

    # Clamp to valid range
    score_worker = max(Decimal("0.0"), min(Decimal("1.0"), score_worker))
    score_agent = Decimal("1.0") - score_worker

    # Round to 2 decimal places
    worker_pct = score_worker.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    agent_pct = score_agent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "worker_pct": float(worker_pct),
        "agent_pct": float(agent_pct),
        "worker_amount": float((amount * worker_pct).quantize(Decimal("0.01"))),
        "agent_amount": float((amount * agent_pct).quantize(Decimal("0.01"))),
        "calculation_details": {
            "method": "calculated",
            "factors": factors,
            "raw_worker_score": float(score_worker),
        },
    }


async def apply_resolution(
    dispute: Dispute,
    resolution: DisputeResolution,
    escrow_manager: "EscrowManager",
) -> List[str]:
    """
    Execute payment changes based on resolution.

    Handles the actual fund distribution:
    - Full worker: Release all remaining escrow to worker
    - Full agent: Refund all remaining escrow to agent
    - Split: Partial release to worker, partial refund to agent

    Args:
        dispute: The dispute being resolved
        resolution: Resolution details
        escrow_manager: EscrowManager for payment operations

    Returns:
        List of transaction hashes

    Raises:
        ResolutionError: If payment execution fails
    """
    tx_hashes = []

    if not dispute.task_id:
        raise ResolutionError("Dispute has no associated task_id")

    logger.info(
        "Applying resolution for dispute %s: %s, worker_pct=%.0f%%",
        dispute.id,
        resolution.resolution_type.value,
        float(resolution.worker_payout_pct * 100),
    )

    try:
        # Get worker wallet from dispute metadata or lookup
        worker_wallet = dispute.metadata.get("worker_wallet")

        if resolution.resolution_type == ResolutionType.FULL_WORKER:
            # Release all to worker
            if worker_wallet:
                tx_hash = await escrow_manager.resolve_dispute(
                    task_id=dispute.task_id,
                    winner="worker",
                    worker_wallet=worker_wallet,
                    worker_pct=1.0,
                )
                tx_hashes.append(tx_hash)
            else:
                logger.warning(
                    "No worker wallet for dispute %s, cannot release funds", dispute.id
                )

        elif resolution.resolution_type == ResolutionType.FULL_AGENT:
            # Refund all to agent
            tx_hash = await escrow_manager.resolve_dispute(
                task_id=dispute.task_id,
                winner="agent",
            )
            tx_hashes.append(tx_hash)

        elif resolution.resolution_type == ResolutionType.SPLIT:
            # Partial release to worker, rest refunded
            if worker_wallet:
                tx_hash = await escrow_manager.resolve_dispute(
                    task_id=dispute.task_id,
                    winner="worker",
                    worker_wallet=worker_wallet,
                    worker_pct=float(resolution.worker_payout_pct),
                )
                tx_hashes.append(tx_hash)
            else:
                # No worker wallet, just refund everything
                tx_hash = await escrow_manager.resolve_dispute(
                    task_id=dispute.task_id,
                    winner="agent",
                )
                tx_hashes.append(tx_hash)

        elif resolution.resolution_type == ResolutionType.DISMISSED:
            # Dismissed - typically refund to agent (no valid claim)
            tx_hash = await escrow_manager.resolve_dispute(
                task_id=dispute.task_id,
                winner="agent",
            )
            tx_hashes.append(tx_hash)

        elif resolution.resolution_type == ResolutionType.MUTUAL:
            # Mutual agreement - use the specified percentages
            if worker_wallet and resolution.worker_payout_pct > 0:
                tx_hash = await escrow_manager.resolve_dispute(
                    task_id=dispute.task_id,
                    winner="worker",
                    worker_wallet=worker_wallet,
                    worker_pct=float(resolution.worker_payout_pct),
                )
                tx_hashes.append(tx_hash)
            else:
                tx_hash = await escrow_manager.resolve_dispute(
                    task_id=dispute.task_id,
                    winner="agent",
                )
                tx_hashes.append(tx_hash)

        logger.info(
            "Resolution applied for dispute %s: %d transactions",
            dispute.id,
            len(tx_hashes),
        )

        return tx_hashes

    except Exception as e:
        logger.error(
            "Failed to apply resolution for dispute %s: %s",
            dispute.id,
            str(e),
        )
        raise ResolutionError(f"Failed to execute payment: {str(e)}") from e


async def notify_parties(
    dispute: Dispute,
    resolution: DisputeResolution,
    notification_service: Optional[Any] = None,
) -> Dict[str, bool]:
    """
    Send notifications to all parties about resolution.

    Args:
        dispute: The resolved dispute
        resolution: Resolution details
        notification_service: Service for sending notifications

    Returns:
        Dict mapping party_id to success status
    """
    results = {}

    # Build notification message

    worker_amount = float(dispute.amount_disputed * resolution.worker_payout_pct)
    agent_amount = float(dispute.amount_disputed * resolution.agent_refund_pct)

    notification = {
        "type": "dispute_resolved",
        "dispute_id": dispute.id,
        "task_id": dispute.task_id,
        "resolution_type": resolution.resolution_type.value,
        "winner": resolution.winner.value if resolution.winner else None,
        "worker_amount": worker_amount,
        "agent_amount": agent_amount,
        "notes": resolution.notes,
        "resolved_at": resolution.resolved_at.isoformat(),
    }

    # Notify initiator
    try:
        if notification_service:
            await notification_service.send(
                recipient_id=dispute.initiator_id,
                notification=notification,
            )
        results[dispute.initiator_id] = True
        logger.info(
            "Notification sent to initiator %s for dispute %s",
            dispute.initiator_id[:8] + "...",
            dispute.id,
        )
    except Exception as e:
        logger.warning(
            "Failed to notify initiator %s: %s",
            dispute.initiator_id[:8] + "...",
            str(e),
        )
        results[dispute.initiator_id] = False

    # Notify respondent
    try:
        if notification_service:
            await notification_service.send(
                recipient_id=dispute.respondent_id,
                notification=notification,
            )
        results[dispute.respondent_id] = True
        logger.info(
            "Notification sent to respondent %s for dispute %s",
            dispute.respondent_id[:8] + "...",
            dispute.id,
        )
    except Exception as e:
        logger.warning(
            "Failed to notify respondent %s: %s",
            dispute.respondent_id[:8] + "...",
            str(e),
        )
        results[dispute.respondent_id] = False

    return results


def determine_auto_resolution(
    dispute: Dispute,
    auto_resolve_threshold: Decimal = Decimal("10.00"),
) -> Optional[Dict[str, Any]]:
    """
    Determine if a dispute can be auto-resolved.

    Auto-resolution is attempted for:
    - Small disputes (below threshold)
    - Clear-cut cases with strong evidence imbalance
    - One party not responding within window

    Args:
        dispute: Dispute to evaluate
        auto_resolve_threshold: Max amount for auto-resolution

    Returns:
        Dict with resolution details if auto-resolvable, None otherwise
    """
    # Small disputes can be auto-resolved
    if dispute.amount_disputed <= auto_resolve_threshold:
        # Calculate split
        split = calculate_refund_split(dispute)

        # Only auto-resolve if there's a clear winner (>70%)
        if split["worker_pct"] >= 0.7:
            return {
                "can_auto_resolve": True,
                "winner": DisputeParty.WORKER,
                "worker_payout_pct": split["worker_pct"],
                "reason": "Small dispute auto-resolved: worker evidence stronger",
                "details": split["calculation_details"],
            }
        elif split["agent_pct"] >= 0.7:
            return {
                "can_auto_resolve": True,
                "winner": DisputeParty.AGENT,
                "worker_payout_pct": split["worker_pct"],
                "reason": "Small dispute auto-resolved: agent position stronger",
                "details": split["calculation_details"],
            }

    # Check for non-responsive party
    worker_responses = sum(
        1 for r in dispute.responses if r.responder_party == DisputeParty.WORKER
    )
    agent_responses = sum(
        1 for r in dispute.responses if r.responder_party == DisputeParty.AGENT
    )

    # If respondent didn't respond and deadline passed, auto-resolve for initiator
    if dispute.initiator_party == DisputeParty.WORKER and agent_responses == 0:
        return {
            "can_auto_resolve": True,
            "winner": DisputeParty.WORKER,
            "worker_payout_pct": 1.0,
            "reason": "Agent did not respond to dispute",
        }
    elif dispute.initiator_party == DisputeParty.AGENT and worker_responses == 0:
        return {
            "can_auto_resolve": True,
            "winner": DisputeParty.AGENT,
            "worker_payout_pct": 0.0,
            "reason": "Worker did not respond to dispute",
        }

    return None


def get_resolution_recommendations(dispute: Dispute) -> List[Dict[str, Any]]:
    """
    Get AI/heuristic-based resolution recommendations.

    Provides suggestions for human reviewers based on:
    - Evidence analysis
    - Party responses
    - Historical patterns

    Args:
        dispute: Dispute to analyze

    Returns:
        List of recommendation dicts with confidence scores
    """
    recommendations = []

    # Check for auto-resolution
    auto = determine_auto_resolution(dispute)
    if auto and auto.get("can_auto_resolve"):
        recommendations.append(
            {
                "action": "auto_resolve",
                "confidence": 0.8,
                "winner": auto["winner"].value if auto.get("winner") else None,
                "worker_payout_pct": auto.get("worker_payout_pct", 0.5),
                "reasoning": auto.get("reason", "Auto-resolution eligible"),
            }
        )

    # Calculate split recommendation
    split = calculate_refund_split(dispute)

    if split["worker_pct"] >= 0.6:
        recommendations.append(
            {
                "action": "favor_worker",
                "confidence": min(split["worker_pct"], 0.9),
                "winner": "worker",
                "worker_payout_pct": split["worker_pct"],
                "reasoning": "Evidence and factors favor worker",
                "details": split["calculation_details"],
            }
        )
    elif split["agent_pct"] >= 0.6:
        recommendations.append(
            {
                "action": "favor_agent",
                "confidence": min(split["agent_pct"], 0.9),
                "winner": "agent",
                "worker_payout_pct": split["worker_pct"],
                "reasoning": "Evidence and factors favor agent",
                "details": split["calculation_details"],
            }
        )
    else:
        recommendations.append(
            {
                "action": "split",
                "confidence": 0.6,
                "winner": None,
                "worker_payout_pct": 0.5,
                "reasoning": "No clear winner, recommend 50/50 split",
                "details": split["calculation_details"],
            }
        )

    # Check if escalation is recommended
    if dispute.amount_disputed >= Decimal("100.00"):
        recommendations.append(
            {
                "action": "escalate",
                "confidence": 0.7,
                "winner": None,
                "worker_payout_pct": None,
                "reasoning": f"High-value dispute (${float(dispute.amount_disputed):.2f}) - human review recommended",
            }
        )

    # Sort by confidence
    recommendations.sort(key=lambda x: x["confidence"], reverse=True)

    return recommendations
