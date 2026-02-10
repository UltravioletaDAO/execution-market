"""
Dispute Router Module

Routes disputes to appropriate resolution mechanisms:
- Auto-resolution for clear cases
- Safe Pool arbitration for complex cases
- Human escalation for edge cases
"""

import os
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class DisputeType(str, Enum):
    """Types of disputes."""

    QUALITY = "quality"  # Work quality not acceptable
    INCOMPLETE = "incomplete"  # Work partially done
    FRAUD = "fraud"  # Suspected fraud
    TIMING = "timing"  # Deadline issues
    PAYMENT = "payment"  # Payment not received
    SAFETY = "safety"  # Safety concerns
    COMMUNICATION = "communication"  # Communication breakdown


class DisputeStatus(str, Enum):
    """Dispute resolution status."""

    OPENED = "opened"
    REVIEWING = "reviewing"
    AWAITING_EVIDENCE = "awaiting_evidence"
    IN_ARBITRATION = "in_arbitration"
    RESOLVED = "resolved"
    APPEALED = "appealed"
    CLOSED = "closed"


class ResolutionOutcome(str, Enum):
    """Possible resolution outcomes."""

    WORKER_WINS = "worker_wins"  # Full payout to worker
    AGENT_WINS = "agent_wins"  # Refund to agent
    SPLIT = "split"  # Partial payout both
    DISMISSED = "dismissed"  # No action needed
    ESCALATED = "escalated"  # Needs human review


@dataclass
class Dispute:
    """Dispute record."""

    id: str
    task_id: str
    submission_id: str
    opened_by: str  # 'worker' or 'agent'
    opener_id: str
    dispute_type: DisputeType
    description: str
    evidence_urls: List[str] = field(default_factory=list)
    status: DisputeStatus = DisputeStatus.OPENED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    outcome: Optional[ResolutionOutcome] = None
    resolution_notes: Optional[str] = None
    arbitrator_id: Optional[str] = None
    worker_payout_pct: float = 0.0
    agent_refund_pct: float = 0.0


@dataclass
class ArbitrationVote:
    """Validator vote in arbitration."""

    validator_id: str
    outcome: ResolutionOutcome
    worker_payout_pct: float
    reasoning: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DisputeRouter:
    """
    Routes disputes to appropriate resolution mechanism.

    Routing logic:
    1. Auto-resolution for clear-cut cases
    2. AI-assisted for moderate complexity
    3. Safe Pool arbitration for complex cases
    4. Human escalation for edge cases
    """

    # Minimum stake for arbitration eligibility
    MIN_VALIDATOR_STAKE = 100  # USDC
    # Required validators for quorum
    QUORUM_SIZE = 3
    # Validator compensation (% of dispute amount)
    VALIDATOR_COMPENSATION_PCT = 0.05

    def __init__(
        self,
        safe_pool_address: Optional[str] = None,
        auto_resolution_enabled: bool = True,
    ):
        """
        Initialize dispute router.

        Args:
            safe_pool_address: Gnosis Safe address for arbitration
            auto_resolution_enabled: Allow auto-resolution for clear cases
        """
        self.safe_pool = safe_pool_address or os.getenv("SAFE_POOL_ADDRESS")
        self.auto_resolution_enabled = auto_resolution_enabled
        self._pending_arbitrations: Dict[str, List[ArbitrationVote]] = {}

    async def open_dispute(
        self,
        task_id: str,
        submission_id: str,
        opened_by: str,
        opener_id: str,
        dispute_type: DisputeType,
        description: str,
        evidence_urls: List[str] = None,
    ) -> Dispute:
        """
        Open a new dispute.

        Args:
            task_id: Task being disputed
            submission_id: Submission being disputed
            opened_by: 'worker' or 'agent'
            opener_id: ID of person opening dispute
            dispute_type: Type of dispute
            description: Dispute description
            evidence_urls: Supporting evidence

        Returns:
            Created Dispute
        """
        import uuid

        dispute = Dispute(
            id=str(uuid.uuid4()),
            task_id=task_id,
            submission_id=submission_id,
            opened_by=opened_by,
            opener_id=opener_id,
            dispute_type=dispute_type,
            description=description,
            evidence_urls=evidence_urls or [],
        )

        # Determine routing
        route = await self._determine_route(dispute)

        if route == "auto":
            return await self._auto_resolve(dispute)
        elif route == "ai":
            return await self._ai_resolve(dispute)
        elif route == "arbitration":
            return await self._route_to_arbitration(dispute)
        else:
            dispute.status = DisputeStatus.AWAITING_EVIDENCE
            return dispute

    async def submit_arbitration_vote(
        self,
        dispute_id: str,
        validator_id: str,
        outcome: ResolutionOutcome,
        worker_payout_pct: float,
        reasoning: str,
    ) -> Optional[Dispute]:
        """
        Submit validator vote for arbitration.

        Args:
            dispute_id: Dispute being voted on
            validator_id: Voting validator
            outcome: Proposed outcome
            worker_payout_pct: Proposed worker payout percentage
            reasoning: Explanation of vote

        Returns:
            Updated Dispute if quorum reached
        """
        vote = ArbitrationVote(
            validator_id=validator_id,
            outcome=outcome,
            worker_payout_pct=worker_payout_pct,
            reasoning=reasoning,
        )

        if dispute_id not in self._pending_arbitrations:
            self._pending_arbitrations[dispute_id] = []

        self._pending_arbitrations[dispute_id].append(vote)

        # Check for quorum
        votes = self._pending_arbitrations[dispute_id]
        if len(votes) >= self.QUORUM_SIZE:
            return await self._finalize_arbitration(dispute_id, votes)

        return None

    async def appeal_resolution(
        self,
        dispute_id: str,
        appealer_id: str,
        appeal_reason: str,
        new_evidence: List[str] = None,
    ) -> Dispute:
        """
        Appeal a dispute resolution.

        Args:
            dispute_id: Dispute being appealed
            appealer_id: Person appealing
            appeal_reason: Reason for appeal
            new_evidence: New evidence supporting appeal

        Returns:
            Updated Dispute
        """
        # In a real implementation, would fetch from database
        logger.info(f"Appeal filed for dispute {dispute_id} by {appealer_id}")

        # Reset for re-arbitration with new validators
        self._pending_arbitrations[dispute_id] = []

        # Return placeholder - would update database
        return Dispute(
            id=dispute_id,
            task_id="",
            submission_id="",
            opened_by="worker",
            opener_id=appealer_id,
            dispute_type=DisputeType.QUALITY,
            description=appeal_reason,
            status=DisputeStatus.APPEALED,
        )

    # Private methods

    async def _determine_route(self, dispute: Dispute) -> str:
        """Determine routing for dispute."""
        # Fraud always goes to human review
        if dispute.dispute_type == DisputeType.FRAUD:
            return "human"

        # Safety concerns go to human
        if dispute.dispute_type == DisputeType.SAFETY:
            return "human"

        # Clear timing issues can be auto-resolved
        if dispute.dispute_type == DisputeType.TIMING and self.auto_resolution_enabled:
            return "auto"

        # Most disputes go to arbitration
        if self.safe_pool:
            return "arbitration"

        return "ai"

    async def _auto_resolve(self, dispute: Dispute) -> Dispute:
        """Auto-resolve clear-cut disputes."""
        logger.info(f"Auto-resolving dispute {dispute.id}")

        # For timing disputes, check deadline data
        if dispute.dispute_type == DisputeType.TIMING:
            # Would check actual submission vs deadline
            # Placeholder: favor worker if close to deadline
            dispute.outcome = ResolutionOutcome.SPLIT
            dispute.worker_payout_pct = 0.7
            dispute.agent_refund_pct = 0.3

        dispute.status = DisputeStatus.RESOLVED
        dispute.resolved_at = datetime.now(timezone.utc)
        dispute.resolution_notes = "Auto-resolved based on objective data"

        return dispute

    async def _ai_resolve(self, dispute: Dispute) -> Dispute:
        """Use AI to help resolve dispute."""
        logger.info(f"AI-assisting dispute {dispute.id}")

        # Would call AI review with dispute context
        # For now, route to arbitration
        return await self._route_to_arbitration(dispute)

    async def _route_to_arbitration(self, dispute: Dispute) -> Dispute:
        """Route dispute to Safe Pool arbitration."""
        logger.info(f"Routing dispute {dispute.id} to arbitration")

        dispute.status = DisputeStatus.IN_ARBITRATION
        self._pending_arbitrations[dispute.id] = []

        # Would notify validators
        # Would create on-chain dispute record

        return dispute

    async def _finalize_arbitration(
        self, dispute_id: str, votes: List[ArbitrationVote]
    ) -> Dispute:
        """Finalize arbitration based on validator votes."""
        logger.info(f"Finalizing arbitration for {dispute_id} with {len(votes)} votes")

        # Count outcomes
        outcome_counts: Dict[ResolutionOutcome, int] = {}
        payout_sum = 0.0

        for vote in votes:
            outcome_counts[vote.outcome] = outcome_counts.get(vote.outcome, 0) + 1
            payout_sum += vote.worker_payout_pct

        # Determine winning outcome (majority)
        winning_outcome = max(outcome_counts, key=outcome_counts.get)
        avg_worker_payout = payout_sum / len(votes)

        # Create resolved dispute
        dispute = Dispute(
            id=dispute_id,
            task_id="",  # Would fetch from DB
            submission_id="",
            opened_by="worker",
            opener_id="",
            dispute_type=DisputeType.QUALITY,
            description="",
            status=DisputeStatus.RESOLVED,
            resolved_at=datetime.now(timezone.utc),
            outcome=winning_outcome,
            worker_payout_pct=avg_worker_payout,
            agent_refund_pct=1.0 - avg_worker_payout,
            resolution_notes=f"Arbitration resolved with {len(votes)} validator votes",
        )

        # Cleanup
        del self._pending_arbitrations[dispute_id]

        return dispute


# Utility functions


def calculate_validator_reward(dispute_amount: float, num_validators: int) -> float:
    """
    Calculate reward for each validator.

    Args:
        dispute_amount: Total amount in dispute
        num_validators: Number of validators who voted

    Returns:
        Reward per validator in USDC
    """
    total_reward = dispute_amount * DisputeRouter.VALIDATOR_COMPENSATION_PCT
    return total_reward / num_validators if num_validators > 0 else 0


def is_eligible_validator(
    tasks_completed: int, avg_rating: float, stake_amount: float
) -> bool:
    """
    Check if user is eligible to be a validator.

    Requirements:
    - >100 tasks completed
    - Rating >4.5
    - Minimum stake

    Args:
        tasks_completed: Number of completed tasks
        avg_rating: Average rating (0-5)
        stake_amount: Staked USDC

    Returns:
        True if eligible
    """
    return (
        tasks_completed >= 100
        and avg_rating >= 4.5
        and stake_amount >= DisputeRouter.MIN_VALIDATOR_STAKE
    )
