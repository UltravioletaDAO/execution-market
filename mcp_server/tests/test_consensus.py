"""
Tests for the Validator Consensus System.

Tests NOW-180, NOW-181, NOW-182 requirements:
- 2-of-3 validator consensus
- Validator specialization
- Validator payments
"""
import pytest
from datetime import datetime, timedelta, UTC
import asyncio

from ..validation.consensus import (
    ValidatorSpecialization,
    Validator,
    ValidationVote,
    VoteDecision,
    ConsensusResult,
    ConsensusStatus,
    ConsensusConfig,
    ConsensusManager,
    ValidatorPool,
    determine_specialization_from_task_type,
    create_consensus_for_submission,
)


# ============== Fixtures ==============

@pytest.fixture
def config():
    """Standard test configuration."""
    return ConsensusConfig(
        required_validators=3,
        min_stake_usdc=100.0,
        min_reputation=60.0,
        min_accuracy=0.75,
        min_validations=50,
        consensus_threshold=2,
        voting_window_hours=24,
        validator_fee_min_pct=0.05,
        validator_fee_max_pct=0.10,
        safe_address="0x1234567890123456789012345678901234567890",
    )


@pytest.fixture
def sample_validators():
    """Create sample validators for testing."""
    return [
        Validator(
            id="validator_1",
            wallet="0xaaa",
            specializations={ValidatorSpecialization.PHOTOGRAPHY, ValidatorSpecialization.GENERAL},
            stake_amount=500.0,
            reputation_score=85.0,
            total_validations=200,
            accuracy_rate=0.92,
        ),
        Validator(
            id="validator_2",
            wallet="0xbbb",
            specializations={ValidatorSpecialization.PHOTOGRAPHY},
            stake_amount=300.0,
            reputation_score=75.0,
            total_validations=150,
            accuracy_rate=0.88,
        ),
        Validator(
            id="validator_3",
            wallet="0xccc",
            specializations={ValidatorSpecialization.DOCUMENT, ValidatorSpecialization.GENERAL},
            stake_amount=200.0,
            reputation_score=70.0,
            total_validations=100,
            accuracy_rate=0.80,
        ),
        Validator(
            id="validator_4",
            wallet="0xddd",
            specializations={ValidatorSpecialization.TECHNICAL},
            stake_amount=1000.0,
            reputation_score=90.0,
            total_validations=300,
            accuracy_rate=0.95,
        ),
        Validator(
            id="validator_5",
            wallet="0xeee",
            specializations={ValidatorSpecialization.GENERAL},
            stake_amount=150.0,
            reputation_score=65.0,
            total_validations=75,
            accuracy_rate=0.78,
        ),
    ]


@pytest.fixture
def validator_pool(config, sample_validators):
    """Create a validator pool with sample validators."""
    pool = ValidatorPool(config)
    for v in sample_validators:
        pool.register_validator(v)
    return pool


@pytest.fixture
def consensus_manager(config, validator_pool):
    """Create a consensus manager with the pool."""
    return ConsensusManager(config, validator_pool)


# ============== Validator Tests ==============

class TestValidator:
    """Tests for the Validator class."""

    def test_effective_score_calculation(self, sample_validators):
        """Test that effective score is calculated correctly."""
        validator = sample_validators[0]  # Best validator
        score = validator.effective_score

        # Should be positive and reasonable
        assert 0 < score <= 1.0

        # Better validators should have higher scores
        scores = [v.effective_score for v in sample_validators]
        assert scores[0] > scores[2]  # validator_1 > validator_3

    def test_inactive_validator_score_zero(self, sample_validators):
        """Inactive validators should have zero effective score."""
        validator = sample_validators[0]
        validator.is_active = False
        assert validator.effective_score == 0.0

    def test_slashed_validator_score_zero(self, sample_validators):
        """Slashed validators should have zero effective score."""
        validator = sample_validators[0]
        validator.is_slashed = True
        assert validator.effective_score == 0.0

    def test_can_validate_specialization(self, sample_validators):
        """Test specialization matching."""
        photo_validator = sample_validators[0]  # Has PHOTOGRAPHY + GENERAL
        doc_validator = sample_validators[2]    # Has DOCUMENT + GENERAL
        tech_validator = sample_validators[3]   # Has TECHNICAL only

        # Direct match
        assert photo_validator.can_validate(ValidatorSpecialization.PHOTOGRAPHY)
        assert doc_validator.can_validate(ValidatorSpecialization.DOCUMENT)
        assert tech_validator.can_validate(ValidatorSpecialization.TECHNICAL)

        # General fallback
        assert photo_validator.can_validate(ValidatorSpecialization.GENERAL)
        assert doc_validator.can_validate(ValidatorSpecialization.GENERAL)

        # Mismatch
        assert not tech_validator.can_validate(ValidatorSpecialization.PHOTOGRAPHY)
        assert not tech_validator.can_validate(ValidatorSpecialization.DOCUMENT)


# ============== ValidatorPool Tests ==============

class TestValidatorPool:
    """Tests for the ValidatorPool class."""

    def test_register_validator(self, config):
        """Test validator registration."""
        pool = ValidatorPool(config)

        good_validator = Validator(
            id="good",
            wallet="0x123",
            specializations={ValidatorSpecialization.GENERAL},
            stake_amount=200.0,
            reputation_score=70.0,
            total_validations=100,
            accuracy_rate=0.85,
        )

        assert pool.register_validator(good_validator)
        assert pool.get_validator("good") is not None

    def test_reject_underqualified_validator(self, config):
        """Test that underqualified validators are rejected."""
        pool = ValidatorPool(config)

        # Low stake
        bad_validator = Validator(
            id="poor",
            wallet="0x123",
            specializations={ValidatorSpecialization.GENERAL},
            stake_amount=10.0,  # Below min_stake_usdc
            reputation_score=70.0,
            total_validations=100,
            accuracy_rate=0.85,
        )

        assert not pool.register_validator(bad_validator)
        assert pool.get_validator("poor") is None

    def test_select_validators_by_specialization(self, validator_pool):
        """Test that validators are selected by specialization."""
        # Select photography validators
        selected = validator_pool.select_validators(
            submission_id="sub_1",
            specialization=ValidatorSpecialization.PHOTOGRAPHY,
            count=2
        )

        assert len(selected) == 2
        # All should be able to validate photography
        for v in selected:
            assert v.can_validate(ValidatorSpecialization.PHOTOGRAPHY)

    def test_select_validators_excludes_ids(self, validator_pool):
        """Test that excluded IDs are not selected."""
        selected = validator_pool.select_validators(
            submission_id="sub_2",
            specialization=ValidatorSpecialization.GENERAL,
            exclude_ids={"validator_1", "validator_2"},
            count=3
        )

        selected_ids = {v.id for v in selected}
        assert "validator_1" not in selected_ids
        assert "validator_2" not in selected_ids

    def test_slash_validator(self, validator_pool):
        """Test validator slashing."""
        initial_stake = validator_pool.get_validator("validator_1").stake_amount

        validator_pool.slash_validator(
            "validator_1",
            50.0,
            "Test slashing"
        )

        validator = validator_pool.get_validator("validator_1")
        assert validator.stake_amount == initial_stake - 50.0
        assert validator.disputes_lost == 1

    def test_deactivate_validator(self, validator_pool):
        """Test validator deactivation."""
        assert validator_pool.deactivate_validator("validator_1", "Inactive")

        validator = validator_pool.get_validator("validator_1")
        assert not validator.is_active
        assert validator.effective_score == 0.0


# ============== ConsensusManager Tests ==============

class TestConsensusManager:
    """Tests for the ConsensusManager class."""

    @pytest.mark.asyncio
    async def test_start_consensus(self, consensus_manager):
        """Test starting a consensus round."""
        result = await consensus_manager.start_consensus(
            submission_id="sub_test_1",
            task_bounty_usd=50.0,
            specialization=ValidatorSpecialization.PHOTOGRAPHY,
        )

        assert result.submission_id == "sub_test_1"
        assert result.status == ConsensusStatus.PENDING
        assert result.total_validator_payment > 0
        assert len(result.votes) == 0

    @pytest.mark.asyncio
    async def test_submit_vote(self, consensus_manager):
        """Test submitting a validator vote."""
        # Start consensus
        await consensus_manager.start_consensus(
            submission_id="sub_vote_1",
            task_bounty_usd=50.0,
            specialization=ValidatorSpecialization.PHOTOGRAPHY,
        )

        # Submit vote
        result = await consensus_manager.submit_vote(
            submission_id="sub_vote_1",
            validator_id="validator_1",
            decision=VoteDecision.APPROVE,
            reasoning="Good quality work"
        )

        assert len(result.votes) == 1
        assert result.votes[0].validator_id == "validator_1"
        assert result.votes[0].decision == VoteDecision.APPROVE

    @pytest.mark.asyncio
    async def test_consensus_reached_with_2_of_3(self, consensus_manager):
        """Test that consensus is reached with 2 of 3 agreeing votes."""
        # Start consensus
        await consensus_manager.start_consensus(
            submission_id="sub_consensus_1",
            task_bounty_usd=100.0,
            specialization=ValidatorSpecialization.GENERAL,
        )

        # First vote: APPROVE
        await consensus_manager.submit_vote(
            submission_id="sub_consensus_1",
            validator_id="validator_1",
            decision=VoteDecision.APPROVE,
        )

        # Second vote: APPROVE -> Should reach consensus
        result = await consensus_manager.submit_vote(
            submission_id="sub_consensus_1",
            validator_id="validator_3",
            decision=VoteDecision.APPROVE,
        )

        assert result.status == ConsensusStatus.REACHED
        assert result.final_decision == VoteDecision.APPROVE
        assert result.quorum_reached is True
        assert result.agreement_ratio >= 2/3

    @pytest.mark.asyncio
    async def test_no_consensus_escalates_to_safe(self, consensus_manager):
        """Test that no consensus escalates to Safe."""
        # Start consensus
        await consensus_manager.start_consensus(
            submission_id="sub_no_consensus",
            task_bounty_usd=100.0,
            specialization=ValidatorSpecialization.GENERAL,
        )

        # Three different votes
        await consensus_manager.submit_vote(
            submission_id="sub_no_consensus",
            validator_id="validator_1",
            decision=VoteDecision.APPROVE,
        )
        await consensus_manager.submit_vote(
            submission_id="sub_no_consensus",
            validator_id="validator_3",
            decision=VoteDecision.REJECT,
        )
        result = await consensus_manager.submit_vote(
            submission_id="sub_no_consensus",
            validator_id="validator_5",
            decision=VoteDecision.PARTIAL,
            completion_percentage=50.0,
        )

        # Should escalate to Safe
        assert result.status == ConsensusStatus.SAFE_FALLBACK
        assert result.safe_tx_hash is not None

    @pytest.mark.asyncio
    async def test_duplicate_vote_rejected(self, consensus_manager):
        """Test that duplicate votes are rejected."""
        await consensus_manager.start_consensus(
            submission_id="sub_dup",
            task_bounty_usd=50.0,
            specialization=ValidatorSpecialization.GENERAL,
        )

        # First vote
        await consensus_manager.submit_vote(
            submission_id="sub_dup",
            validator_id="validator_1",
            decision=VoteDecision.APPROVE,
        )

        # Duplicate vote should raise
        with pytest.raises(ValueError, match="already voted"):
            await consensus_manager.submit_vote(
                submission_id="sub_dup",
                validator_id="validator_1",
                decision=VoteDecision.REJECT,
            )

    @pytest.mark.asyncio
    async def test_payment_distribution(self, consensus_manager):
        """Test validator payment distribution."""
        # Start and complete consensus
        await consensus_manager.start_consensus(
            submission_id="sub_payment",
            task_bounty_usd=100.0,
            specialization=ValidatorSpecialization.GENERAL,
        )

        await consensus_manager.submit_vote(
            submission_id="sub_payment",
            validator_id="validator_1",
            decision=VoteDecision.APPROVE,
        )
        await consensus_manager.submit_vote(
            submission_id="sub_payment",
            validator_id="validator_3",
            decision=VoteDecision.APPROVE,
        )

        # Get payments
        payments = await consensus_manager.distribute_payments("sub_payment")

        assert len(payments) == 2
        assert all(amount > 0 for amount in payments.values())

        # Total should match validator payment pool
        result = await consensus_manager.get_consensus_status("sub_payment")
        total_distributed = sum(payments.values())
        assert abs(total_distributed - result.total_validator_payment) < 0.01


# ============== Specialization Tests ==============

class TestSpecializationMapping:
    """Tests for task type to specialization mapping."""

    def test_photography_tasks(self):
        """Test photography task types."""
        assert determine_specialization_from_task_type("photo") == ValidatorSpecialization.PHOTOGRAPHY
        assert determine_specialization_from_task_type("photo_geo") == ValidatorSpecialization.PHOTOGRAPHY
        assert determine_specialization_from_task_type("store_check") == ValidatorSpecialization.PHOTOGRAPHY

    def test_document_tasks(self):
        """Test document task types."""
        assert determine_specialization_from_task_type("document") == ValidatorSpecialization.DOCUMENT
        assert determine_specialization_from_task_type("receipt") == ValidatorSpecialization.DOCUMENT
        assert determine_specialization_from_task_type("notarized") == ValidatorSpecialization.DOCUMENT

    def test_technical_tasks(self):
        """Test technical task types."""
        assert determine_specialization_from_task_type("measurement") == ValidatorSpecialization.TECHNICAL
        assert determine_specialization_from_task_type("code_review") == ValidatorSpecialization.TECHNICAL

    def test_general_fallback(self):
        """Test that unknown types fall back to GENERAL."""
        assert determine_specialization_from_task_type("unknown") == ValidatorSpecialization.GENERAL
        assert determine_specialization_from_task_type("random_task") == ValidatorSpecialization.GENERAL


# ============== ValidationVote Tests ==============

class TestValidationVote:
    """Tests for ValidationVote class."""

    def test_approve_sets_100_percent(self):
        """Test that APPROVE sets 100% completion."""
        vote = ValidationVote(
            validator_id="v1",
            submission_id="s1",
            decision=VoteDecision.APPROVE,
            completion_percentage=50.0,  # Should be ignored
        )
        assert vote.completion_percentage == 100.0

    def test_reject_sets_0_percent(self):
        """Test that REJECT sets 0% completion."""
        vote = ValidationVote(
            validator_id="v1",
            submission_id="s1",
            decision=VoteDecision.REJECT,
            completion_percentage=50.0,  # Should be ignored
        )
        assert vote.completion_percentage == 0.0

    def test_partial_respects_percentage(self):
        """Test that PARTIAL uses the provided percentage."""
        vote = ValidationVote(
            validator_id="v1",
            submission_id="s1",
            decision=VoteDecision.PARTIAL,
            completion_percentage=65.0,
        )
        assert vote.completion_percentage == 65.0

    def test_partial_clamps_percentage(self):
        """Test that PARTIAL clamps percentage to 0-100."""
        vote_high = ValidationVote(
            validator_id="v1",
            submission_id="s1",
            decision=VoteDecision.PARTIAL,
            completion_percentage=150.0,
        )
        assert vote_high.completion_percentage == 100.0

        vote_low = ValidationVote(
            validator_id="v1",
            submission_id="s1",
            decision=VoteDecision.PARTIAL,
            completion_percentage=-20.0,
        )
        assert vote_low.completion_percentage == 0.0


# ============== Integration Tests ==============

class TestConsensusIntegration:
    """Integration tests for the full consensus flow."""

    @pytest.mark.asyncio
    async def test_full_approval_flow(self, consensus_manager):
        """Test complete approval flow from start to payment."""
        submission_id = "integration_approve"

        # 1. Start consensus
        result = await consensus_manager.start_consensus(
            submission_id=submission_id,
            task_bounty_usd=75.0,
            specialization=ValidatorSpecialization.PHOTOGRAPHY,
            exclude_validator_ids={"worker_123"}
        )
        assert result.status == ConsensusStatus.PENDING

        # 2. Collect votes
        await consensus_manager.submit_vote(
            submission_id=submission_id,
            validator_id="validator_1",
            decision=VoteDecision.APPROVE,
            reasoning="Photo quality excellent"
        )

        result = await consensus_manager.submit_vote(
            submission_id=submission_id,
            validator_id="validator_2",
            decision=VoteDecision.APPROVE,
            reasoning="All requirements met"
        )

        # 3. Verify consensus
        assert result.status == ConsensusStatus.REACHED
        assert result.final_decision == VoteDecision.APPROVE
        assert result.completion_percentage == 100.0

        # 4. Distribute payments
        payments = await consensus_manager.distribute_payments(submission_id)
        assert len(payments) == 2
        assert sum(payments.values()) > 0

    @pytest.mark.asyncio
    async def test_partial_completion_flow(self, consensus_manager):
        """Test partial completion consensus."""
        submission_id = "integration_partial"

        await consensus_manager.start_consensus(
            submission_id=submission_id,
            task_bounty_usd=100.0,
            specialization=ValidatorSpecialization.DOCUMENT,
        )

        # Two validators agree on partial
        await consensus_manager.submit_vote(
            submission_id=submission_id,
            validator_id="validator_3",
            decision=VoteDecision.PARTIAL,
            completion_percentage=60.0,
        )

        result = await consensus_manager.submit_vote(
            submission_id=submission_id,
            validator_id="validator_5",
            decision=VoteDecision.PARTIAL,
            completion_percentage=70.0,
        )

        assert result.status == ConsensusStatus.REACHED
        assert result.final_decision == VoteDecision.PARTIAL
        # Average of 60 and 70
        assert result.completion_percentage == 65.0

    @pytest.mark.asyncio
    async def test_convenience_function(self, config):
        """Test the create_consensus_for_submission convenience function."""
        result = await create_consensus_for_submission(
            submission_id="convenience_test",
            task_bounty_usd=50.0,
            task_type="photo_verification",
            worker_id="worker_456",
            config=config
        )

        # Should fail gracefully with no registered validators in new manager
        assert result is not None
        # Status depends on available validators
        assert result.submission_id == "convenience_test"
