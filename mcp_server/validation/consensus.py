"""
Validator Consensus System (NOW-180, NOW-181, NOW-182)

2-of-3 consensus with Gnosis Safe fallback for dispute resolution.

Key features:
- Validator selection based on reputation, stake, and specialization
- 2-of-3 consensus for quick resolution
- Automatic Safe fallback when consensus fails
- Validator payment (5-10% of task bounty split among validators)
- Specialization matching (photography, document, technical, general)
"""
import logging
import uuid
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
import asyncio
import random

logger = logging.getLogger(__name__)


class ValidatorSpecialization(str, Enum):
    """Validator specializations for different task types."""
    PHOTOGRAPHY = "photography"   # Photo verification (EXIF, tampering, GenAI)
    DOCUMENT = "document"         # Document verification (receipts, forms)
    TECHNICAL = "technical"       # Technical tasks (code, data, measurements)
    GENERAL = "general"           # General-purpose validation


class VoteDecision(str, Enum):
    """Possible validator decisions."""
    APPROVE = "approve"           # Work meets requirements
    REJECT = "reject"             # Work does not meet requirements
    PARTIAL = "partial"           # Partial completion (with percentage)
    ABSTAIN = "abstain"           # Cannot make determination
    NEEDS_HUMAN = "needs_human"   # Requires human arbitration


class ConsensusStatus(str, Enum):
    """Status of a consensus round."""
    PENDING = "pending"           # Awaiting votes
    REACHED = "reached"           # Consensus achieved
    FAILED = "failed"             # No consensus, escalate to Safe
    EXPIRED = "expired"           # Voting window expired
    SAFE_FALLBACK = "safe_fallback"  # Escalated to Gnosis Safe


@dataclass
class Validator:
    """
    Represents a validator in the Execution Market network.

    Validators are experienced workers who can verify submissions
    and participate in consensus for disputed or high-value tasks.
    """
    id: str
    wallet: str
    specializations: Set[ValidatorSpecialization]
    stake_amount: float             # USDC staked
    reputation_score: float         # 0-100 Bayesian score
    total_validations: int          # Lifetime validations
    accuracy_rate: float            # 0.0-1.0 historical accuracy
    is_active: bool = True
    is_slashed: bool = False
    last_validation_at: Optional[datetime] = None

    # Performance metrics
    avg_response_time_hours: float = 24.0
    disputes_lost: int = 0
    consecutive_accurate: int = 0

    def __post_init__(self):
        if isinstance(self.specializations, list):
            self.specializations = set(self.specializations)

    @property
    def effective_score(self) -> float:
        """
        Calculate effective validator score for selection.

        Combines reputation, stake, accuracy, and activity.
        """
        if not self.is_active or self.is_slashed:
            return 0.0

        # Base from reputation (40%)
        reputation_factor = self.reputation_score / 100 * 0.4

        # Stake factor (30%) - log scale to prevent whale dominance
        import math
        stake_factor = min(1.0, math.log(self.stake_amount + 1) / 10) * 0.3

        # Accuracy factor (20%)
        accuracy_factor = self.accuracy_rate * 0.2

        # Experience factor (10%)
        experience_factor = min(1.0, self.total_validations / 500) * 0.1

        return reputation_factor + stake_factor + accuracy_factor + experience_factor

    def can_validate(self, required_specialization: ValidatorSpecialization) -> bool:
        """Check if validator can handle this specialization."""
        return (
            self.is_active and
            not self.is_slashed and
            (
                required_specialization in self.specializations or
                ValidatorSpecialization.GENERAL in self.specializations
            )
        )


@dataclass
class ValidationVote:
    """Individual validator vote on a submission."""
    validator_id: str
    submission_id: str
    decision: VoteDecision
    completion_percentage: float = 100.0  # 0-100, used for PARTIAL
    confidence: float = 1.0               # 0-1, validator confidence
    reasoning: str = ""
    evidence_notes: str = ""
    voted_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self):
        # Validate completion percentage
        if self.decision == VoteDecision.PARTIAL:
            self.completion_percentage = max(0, min(100, self.completion_percentage))
        elif self.decision == VoteDecision.APPROVE:
            self.completion_percentage = 100.0
        elif self.decision == VoteDecision.REJECT:
            self.completion_percentage = 0.0


@dataclass
class ConsensusResult:
    """Result of a consensus round."""
    submission_id: str
    status: ConsensusStatus
    final_decision: Optional[VoteDecision]
    completion_percentage: float
    votes: List[ValidationVote]
    quorum_reached: bool
    agreement_ratio: float           # 0-1, how much validators agreed
    total_validator_payment: float   # USDC to distribute
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolved_at: Optional[datetime] = None
    safe_tx_hash: Optional[str] = None  # If escalated to Safe

    @property
    def approvals(self) -> int:
        return sum(1 for v in self.votes if v.decision == VoteDecision.APPROVE)

    @property
    def rejections(self) -> int:
        return sum(1 for v in self.votes if v.decision == VoteDecision.REJECT)

    @property
    def partials(self) -> int:
        return sum(1 for v in self.votes if v.decision == VoteDecision.PARTIAL)


@dataclass
class ConsensusConfig:
    """Configuration for consensus system."""
    # Validator selection
    required_validators: int = 3
    min_stake_usdc: float = 100.0
    min_reputation: float = 60.0
    min_accuracy: float = 0.75
    min_validations: int = 50

    # Consensus rules
    consensus_threshold: int = 2      # 2 of 3 must agree
    voting_window_hours: int = 24     # Time to collect votes

    # Payments (NOW-182)
    validator_fee_min_pct: float = 0.05  # 5% minimum
    validator_fee_max_pct: float = 0.10  # 10% maximum

    # High-value task threshold
    high_value_threshold_usd: float = 100.0

    # Slashing
    slash_on_wrong_vote: bool = True
    slash_percentage: float = 0.05   # 5% of stake

    # Safe fallback
    safe_address: Optional[str] = None
    safe_threshold: int = 2          # 2-of-3 Safe signers


class ValidatorPool:
    """
    Manages the pool of validators and selection logic.

    Selection criteria:
    1. Must meet minimum requirements (stake, reputation, accuracy)
    2. Must have matching specialization
    3. Not recently validated same submitter (conflict prevention)
    4. Weighted by effective score
    """

    def __init__(self, config: ConsensusConfig):
        self.config = config
        self._validators: Dict[str, Validator] = {}
        self._recent_assignments: Dict[str, List[str]] = {}  # submission_id -> validator_ids

    def register_validator(self, validator: Validator) -> bool:
        """
        Register a new validator.

        Args:
            validator: Validator to register

        Returns:
            True if registration successful
        """
        if not self._meets_requirements(validator):
            logger.warning(f"Validator {validator.id} does not meet requirements")
            return False

        self._validators[validator.id] = validator
        logger.info(f"Registered validator {validator.id} with score {validator.effective_score:.2f}")
        return True

    def update_validator(self, validator_id: str, updates: Dict[str, Any]) -> Optional[Validator]:
        """Update validator attributes."""
        if validator_id not in self._validators:
            return None

        validator = self._validators[validator_id]
        for key, value in updates.items():
            if hasattr(validator, key):
                setattr(validator, key, value)

        return validator

    def deactivate_validator(self, validator_id: str, reason: str = "") -> bool:
        """Deactivate a validator."""
        if validator_id in self._validators:
            self._validators[validator_id].is_active = False
            logger.info(f"Deactivated validator {validator_id}: {reason}")
            return True
        return False

    def slash_validator(self, validator_id: str, amount: float, reason: str) -> bool:
        """
        Slash a validator's stake.

        Args:
            validator_id: Validator to slash
            amount: Amount to slash
            reason: Reason for slashing

        Returns:
            True if slashing successful
        """
        if validator_id not in self._validators:
            return False

        validator = self._validators[validator_id]
        validator.stake_amount = max(0, validator.stake_amount - amount)
        validator.disputes_lost += 1
        validator.consecutive_accurate = 0

        # Mark as slashed if stake too low
        if validator.stake_amount < self.config.min_stake_usdc:
            validator.is_slashed = True

        logger.warning(f"Slashed validator {validator_id} by {amount} USDC: {reason}")
        return True

    def select_validators(
        self,
        submission_id: str,
        specialization: ValidatorSpecialization,
        exclude_ids: Set[str] = None,
        count: int = None
    ) -> List[Validator]:
        """
        Select validators for a submission.

        Uses weighted random selection based on effective score.

        Args:
            submission_id: Submission to validate
            specialization: Required specialization
            exclude_ids: Validator IDs to exclude (e.g., previous submitter)
            count: Number of validators (default from config)

        Returns:
            List of selected validators
        """
        count = count or self.config.required_validators
        exclude_ids = exclude_ids or set()

        # Get eligible validators
        eligible = [
            v for v in self._validators.values()
            if (
                v.can_validate(specialization) and
                v.id not in exclude_ids and
                self._meets_requirements(v)
            )
        ]

        if len(eligible) < count:
            logger.warning(
                f"Only {len(eligible)} eligible validators for {specialization}, "
                f"need {count}"
            )
            # Return what we have
            return eligible

        # Weighted selection by effective score
        weights = [v.effective_score for v in eligible]
        total_weight = sum(weights)

        if total_weight == 0:
            # Fallback to uniform random
            return random.sample(eligible, count)

        # Normalize weights
        weights = [w / total_weight for w in weights]

        # Select without replacement
        selected = []
        remaining = list(zip(eligible, weights))

        for _ in range(count):
            if not remaining:
                break

            # Weighted random choice
            validators, probs = zip(*remaining)
            chosen = random.choices(validators, weights=probs, k=1)[0]
            selected.append(chosen)

            # Remove from remaining
            remaining = [(v, w) for v, w in remaining if v.id != chosen.id]

            # Renormalize
            if remaining:
                total = sum(w for _, w in remaining)
                remaining = [(v, w/total) for v, w in remaining]

        # Track assignment
        self._recent_assignments[submission_id] = [v.id for v in selected]

        logger.info(
            f"Selected validators for {submission_id}: "
            f"{[v.id for v in selected]}"
        )

        return selected

    def get_validator(self, validator_id: str) -> Optional[Validator]:
        """Get validator by ID."""
        return self._validators.get(validator_id)

    def get_active_validators(self) -> List[Validator]:
        """Get all active validators."""
        return [v for v in self._validators.values() if v.is_active and not v.is_slashed]

    def get_validators_by_specialization(
        self,
        specialization: ValidatorSpecialization
    ) -> List[Validator]:
        """Get validators with specific specialization."""
        return [
            v for v in self.get_active_validators()
            if v.can_validate(specialization)
        ]

    def _meets_requirements(self, validator: Validator) -> bool:
        """Check if validator meets minimum requirements."""
        return (
            validator.stake_amount >= self.config.min_stake_usdc and
            validator.reputation_score >= self.config.min_reputation and
            validator.accuracy_rate >= self.config.min_accuracy and
            validator.total_validations >= self.config.min_validations
        )


class ConsensusManager:
    """
    Manages the 2-of-3 validator consensus process.

    Flow:
    1. Submission received
    2. Select 3 validators based on specialization and score
    3. Collect votes within window
    4. If 2+ agree -> consensus reached
    5. If no consensus -> escalate to Gnosis Safe
    6. Distribute validator payments
    """

    def __init__(
        self,
        config: Optional[ConsensusConfig] = None,
        validator_pool: Optional[ValidatorPool] = None
    ):
        self.config = config or ConsensusConfig()
        self.pool = validator_pool or ValidatorPool(self.config)

        # Active consensus rounds
        self._rounds: Dict[str, ConsensusResult] = {}
        self._vote_deadlines: Dict[str, datetime] = {}

    async def start_consensus(
        self,
        submission_id: str,
        task_bounty_usd: float,
        specialization: ValidatorSpecialization,
        exclude_validator_ids: Set[str] = None
    ) -> ConsensusResult:
        """
        Start a new consensus round for a submission.

        Args:
            submission_id: Submission to validate
            task_bounty_usd: Task bounty for payment calculation
            specialization: Required validator specialization
            exclude_validator_ids: IDs to exclude (e.g., worker's own validator ID)

        Returns:
            Initial ConsensusResult
        """
        # Calculate validator payment (5-10% based on task value)
        fee_pct = self._calculate_fee_percentage(task_bounty_usd)
        total_payment = task_bounty_usd * fee_pct

        # Select validators
        validators = self.pool.select_validators(
            submission_id=submission_id,
            specialization=specialization,
            exclude_ids=exclude_validator_ids
        )

        if not validators:
            logger.error(f"No validators available for {submission_id}")
            return ConsensusResult(
                submission_id=submission_id,
                status=ConsensusStatus.FAILED,
                final_decision=None,
                completion_percentage=0,
                votes=[],
                quorum_reached=False,
                agreement_ratio=0,
                total_validator_payment=total_payment
            )

        # Create consensus round
        result = ConsensusResult(
            submission_id=submission_id,
            status=ConsensusStatus.PENDING,
            final_decision=None,
            completion_percentage=0,
            votes=[],
            quorum_reached=False,
            agreement_ratio=0,
            total_validator_payment=total_payment
        )

        self._rounds[submission_id] = result
        self._vote_deadlines[submission_id] = (
            datetime.now(UTC) + timedelta(hours=self.config.voting_window_hours)
        )

        logger.info(
            f"Started consensus for {submission_id} with {len(validators)} validators, "
            f"payment pool: ${total_payment:.2f}"
        )

        return result

    async def submit_vote(
        self,
        submission_id: str,
        validator_id: str,
        decision: VoteDecision,
        completion_percentage: float = 100.0,
        confidence: float = 1.0,
        reasoning: str = "",
        evidence_notes: str = ""
    ) -> ConsensusResult:
        """
        Submit a validator vote.

        Args:
            submission_id: Submission being voted on
            validator_id: Voting validator
            decision: Vote decision
            completion_percentage: For PARTIAL votes
            confidence: Validator confidence (0-1)
            reasoning: Explanation of vote
            evidence_notes: Notes about evidence review

        Returns:
            Updated ConsensusResult
        """
        if submission_id not in self._rounds:
            raise ValueError(f"No active consensus for {submission_id}")

        # Validate the validator
        validator = self.pool.get_validator(validator_id)
        if not validator:
            raise ValueError(f"Unknown validator: {validator_id}")

        if not validator.is_active or validator.is_slashed:
            raise ValueError(f"Validator {validator_id} is not active")

        # Check deadline
        if datetime.now(UTC) > self._vote_deadlines[submission_id]:
            return await self._handle_expired(submission_id)

        # Check for duplicate vote
        result = self._rounds[submission_id]
        if any(v.validator_id == validator_id for v in result.votes):
            raise ValueError(f"Validator {validator_id} already voted")

        # Create vote
        vote = ValidationVote(
            validator_id=validator_id,
            submission_id=submission_id,
            decision=decision,
            completion_percentage=completion_percentage,
            confidence=confidence,
            reasoning=reasoning,
            evidence_notes=evidence_notes
        )

        result.votes.append(vote)

        # Update validator stats
        validator.last_validation_at = datetime.now(UTC)
        validator.total_validations += 1

        logger.info(
            f"Vote received for {submission_id} from {validator_id}: "
            f"{decision.value} ({completion_percentage}%)"
        )

        # Check for consensus
        return await self._check_consensus(submission_id)

    async def get_consensus_status(self, submission_id: str) -> Optional[ConsensusResult]:
        """Get current status of a consensus round."""
        return self._rounds.get(submission_id)

    async def finalize_consensus(
        self,
        submission_id: str,
        force: bool = False
    ) -> ConsensusResult:
        """
        Finalize a consensus round.

        Called when:
        - Consensus is reached
        - Voting window expires
        - Manual force (admin)

        Args:
            submission_id: Submission to finalize
            force: Force finalization even if pending

        Returns:
            Final ConsensusResult
        """
        if submission_id not in self._rounds:
            raise ValueError(f"No consensus round for {submission_id}")

        result = self._rounds[submission_id]

        if result.status in (ConsensusStatus.REACHED, ConsensusStatus.SAFE_FALLBACK):
            return result  # Already finalized

        # Check if should escalate to Safe
        if result.status == ConsensusStatus.FAILED or (
            force and result.status == ConsensusStatus.PENDING
        ):
            return await self._escalate_to_safe(submission_id)

        return result

    async def distribute_payments(
        self,
        submission_id: str
    ) -> Dict[str, float]:
        """
        Calculate and return payment distribution for validators.

        Payments are split based on:
        - Equal base share
        - Bonus for correct consensus vote

        Args:
            submission_id: Completed consensus round

        Returns:
            Dict of validator_id -> payment amount
        """
        if submission_id not in self._rounds:
            return {}

        result = self._rounds[submission_id]

        if result.status not in (ConsensusStatus.REACHED, ConsensusStatus.SAFE_FALLBACK):
            return {}

        payments: Dict[str, float] = {}
        total = result.total_validator_payment
        num_validators = len(result.votes)

        if num_validators == 0:
            return payments

        base_share = total * 0.7 / num_validators  # 70% split equally
        bonus_pool = total * 0.3  # 30% for accuracy bonus

        # Determine which votes were "correct"
        correct_decision = result.final_decision
        correct_voters = [
            v for v in result.votes
            if v.decision == correct_decision
        ]

        for vote in result.votes:
            payment = base_share

            # Bonus for correct vote
            if vote.decision == correct_decision and correct_voters:
                payment += bonus_pool / len(correct_voters)

            payments[vote.validator_id] = round(payment, 4)

            # Update validator accuracy
            validator = self.pool.get_validator(vote.validator_id)
            if validator:
                was_correct = vote.decision == correct_decision
                self._update_validator_accuracy(validator, was_correct)

        logger.info(f"Payment distribution for {submission_id}: {payments}")

        return payments

    # Private methods

    def _calculate_fee_percentage(self, task_bounty_usd: float) -> float:
        """
        Calculate validator fee percentage based on task value.

        Higher value tasks get lower percentage (but higher absolute amount).
        """
        if task_bounty_usd >= self.config.high_value_threshold_usd:
            return self.config.validator_fee_min_pct

        # Linear interpolation between min and max
        ratio = task_bounty_usd / self.config.high_value_threshold_usd
        return (
            self.config.validator_fee_max_pct -
            (self.config.validator_fee_max_pct - self.config.validator_fee_min_pct) * ratio
        )

    async def _check_consensus(self, submission_id: str) -> ConsensusResult:
        """Check if consensus has been reached."""
        result = self._rounds[submission_id]

        # Count votes by decision
        vote_counts: Dict[VoteDecision, int] = {}
        for vote in result.votes:
            vote_counts[vote.decision] = vote_counts.get(vote.decision, 0) + 1

        # Check for consensus (2 of 3 agree)
        for decision, count in vote_counts.items():
            if count >= self.config.consensus_threshold:
                # Consensus reached!
                result.status = ConsensusStatus.REACHED
                result.final_decision = decision
                result.quorum_reached = True
                result.resolved_at = datetime.now(UTC)

                # Calculate completion percentage (average of agreeing votes)
                agreeing_votes = [v for v in result.votes if v.decision == decision]
                result.completion_percentage = sum(
                    v.completion_percentage for v in agreeing_votes
                ) / len(agreeing_votes)

                # Calculate agreement ratio
                result.agreement_ratio = count / len(result.votes)

                logger.info(
                    f"Consensus reached for {submission_id}: {decision.value} "
                    f"({result.completion_percentage}%)"
                )

                return result

        # Check if all votes received but no consensus
        if len(result.votes) >= self.config.required_validators:
            logger.warning(f"No consensus for {submission_id}, escalating to Safe")
            return await self._escalate_to_safe(submission_id)

        # Still waiting for votes
        return result

    async def _handle_expired(self, submission_id: str) -> ConsensusResult:
        """Handle expired voting window."""
        result = self._rounds[submission_id]

        if result.status != ConsensusStatus.PENDING:
            return result

        result.status = ConsensusStatus.EXPIRED

        # If we have some votes, try to reach consensus with what we have
        if len(result.votes) >= 2:
            return await self._check_consensus(submission_id)

        # Not enough votes, escalate
        return await self._escalate_to_safe(submission_id)

    async def _escalate_to_safe(self, submission_id: str) -> ConsensusResult:
        """
        Escalate to Gnosis Safe for final decision.

        This happens when:
        - No validator consensus
        - Insufficient votes
        - High-stakes disputes
        """
        result = self._rounds[submission_id]
        result.status = ConsensusStatus.SAFE_FALLBACK

        if not self.config.safe_address:
            logger.error(f"No Safe address configured for fallback: {submission_id}")
            result.status = ConsensusStatus.FAILED
            return result

        # In production: create Safe transaction for human arbitration
        # This would create a multi-sig proposal for Safe owners to vote

        logger.info(
            f"Escalated {submission_id} to Safe {self.config.safe_address} "
            f"for arbitration"
        )

        # Placeholder for Safe tx hash
        result.safe_tx_hash = f"safe_pending_{submission_id}"

        return result

    def _update_validator_accuracy(self, validator: Validator, was_correct: bool):
        """Update validator accuracy after consensus resolution."""
        # Exponential moving average
        alpha = 0.1  # Learning rate
        validator.accuracy_rate = (
            alpha * (1.0 if was_correct else 0.0) +
            (1 - alpha) * validator.accuracy_rate
        )

        if was_correct:
            validator.consecutive_accurate += 1
        else:
            validator.consecutive_accurate = 0

            # Slash if configured and wrong
            if self.config.slash_on_wrong_vote:
                slash_amount = validator.stake_amount * self.config.slash_percentage
                self.pool.slash_validator(
                    validator.id,
                    slash_amount,
                    "Incorrect consensus vote"
                )


# Convenience functions

def determine_specialization_from_task_type(task_type: str) -> ValidatorSpecialization:
    """
    Map task type to validator specialization.

    Args:
        task_type: Execution Market task type

    Returns:
        Appropriate ValidatorSpecialization
    """
    photography_tasks = {
        "photo", "photo_geo", "photo_verification", "visual_inspection",
        "store_check", "location_verification"
    }
    document_tasks = {
        "document", "receipt", "form", "notarized", "signature",
        "document_verification"
    }
    technical_tasks = {
        "measurement", "data_collection", "technical", "code_review",
        "quality_check"
    }

    task_type_lower = task_type.lower()

    if task_type_lower in photography_tasks:
        return ValidatorSpecialization.PHOTOGRAPHY
    elif task_type_lower in document_tasks:
        return ValidatorSpecialization.DOCUMENT
    elif task_type_lower in technical_tasks:
        return ValidatorSpecialization.TECHNICAL
    else:
        return ValidatorSpecialization.GENERAL


async def create_consensus_for_submission(
    submission_id: str,
    task_bounty_usd: float,
    task_type: str,
    worker_id: str,
    config: Optional[ConsensusConfig] = None
) -> ConsensusResult:
    """
    Convenience function to create a consensus round.

    Args:
        submission_id: Submission to validate
        task_bounty_usd: Task bounty
        task_type: Task type for specialization
        worker_id: Worker who submitted (to exclude from validators)
        config: Optional custom config

    Returns:
        ConsensusResult for the new round
    """
    manager = ConsensusManager(config)
    specialization = determine_specialization_from_task_type(task_type)

    return await manager.start_consensus(
        submission_id=submission_id,
        task_bounty_usd=task_bounty_usd,
        specialization=specialization,
        exclude_validator_ids={worker_id}
    )
